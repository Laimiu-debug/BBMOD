// Standalone x86 harness: contains no game code and never starts the game.
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>
#include "../native/place_display.h"
#include "../native/place_session.h"
// Link the actual rendering adapter into this test EXE. DllMain is never an
// EXE entry point; no hooks, graphics context or game process are started.
#include "../native/han_font.cpp"

struct Object { uint32_t type, value; };
struct VM {
    unsigned char prefix[0x18]{};
    Object* stack;
    int size, capacity, top, stackbase;
    uint32_t frameField;
    Object root;
};
static_assert(offsetof(VM, root) == 0x30, "VM layout");
static_assert(sizeof(Object) == 8 && sizeof(void*) == 4, "x86 object size");
std::vector<std::string> pushed;
std::string published;
int popCalls=0, slotCalls=0;
bool failSlot=false;
extern "C" void __cdecl fakePushC(VM* vm, const char* text, int length) {
    assert(length == -1 && text && vm->top < vm->size);
    pushed.emplace_back(text);
    vm->stack[vm->top++] = {0x08000010, 0x12345678};
}
extern "C" int __cdecl fakeSlotC(VM* vm, int index, int isStatic) {
    assert(index == -3 && isStatic == 0 && vm->top >= 3);
    assert(vm->stack[vm->top-3].type == vm->root.type);
    assert(vm->stack[vm->top-3].value == vm->root.value);
    assert(pushed[pushed.size()-2] == "BBMODPlaceDisplaySession");
    ++slotCalls;
    if (failSlot) return -1;
    published = pushed.back();
    vm->top -= 2;
    return 0;
}
__declspec(naked) void fakePush() {
    __asm {
        mov eax, [esp+4]
        push eax
        push edx
        push ecx
        call fakePushC
        add esp, 12
        ret
    }
}
__declspec(naked) int fakeSlot() {
    __asm {
        mov eax, [esp+4]
        push eax
        push edx
        push ecx
        call fakeSlotC
        add esp, 12
        ret
    }
}
void __fastcall fakePop(VM* vm, void*, int count) {
    assert(count == 2);
    vm->top -= count;
    ++popCalls;
}

int main(int argc, char** argv) {
    assert(argc == 3);
    std::ifstream input(argv[1], std::ios::binary);
    assert(input.good());
    std::string raw((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    bbmod::PlaceDictionary dictionary;
    assert(dictionary.load(raw));
    size_t start=raw.find('\n')+1, checked=0;
    while (start < raw.size()) {
        size_t tab=raw.find('\t',start), end=raw.find('\n',start);
        std::string original=raw.substr(start,tab-start), translated=raw.substr(tab+1,end-tab-1);
        assert(dictionary.translate(original) == translated);
        assert(dictionary.translate(original+" (12)") == translated+" (12)");
        assert(dictionary.translate(original+" (x)") == original+" (x)");
        assert(dictionary.translate("prefix_"+original) == "prefix_"+original);
        ++checked; start=end+1;
    }
    assert(checked == dictionary.size() && checked > 2196);
    assert(dictionary.translate("Wiesendorf") == "维森多夫");
    assert(dictionary.translate("Black Monolith") == "黑色巨石");
    assert(dictionary.translate("") == "");
    for (auto invalid : {"", "BBMOD-PLACE-DISPLAY-1\n", "BBMOD-PLACE-DISPLAY-1\nx\t\n",
                        "BBMOD-PLACE-DISPLAY-1\nx\ty\nx\tz\n", "BBMOD-PLACE-DISPLAY-1\nx\ty"}) {
        assert(!dictionary.load(invalid));
        assert(dictionary.size() == checked);
    }
    BCRYPT_ALG_HANDLE algorithm=nullptr;
    assert(BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,nullptr,0)==0);
    unsigned char digest[32]{};
    assert(BCryptHash(algorithm,nullptr,0,reinterpret_cast<unsigned char*>(raw.data()),static_cast<ULONG>(raw.size()),digest,32)==0);
    BCryptCloseAlgorithmProvider(algorithm,0);
    char hash[65]{};
    for(int i=0;i<32;++i)sprintf_s(hash+i*2,3,"%02x",digest[i]);
    assert(SetEnvironmentVariableA("BBMOD_PLACE_NAMES_PATH",argv[1]));
    assert(SetEnvironmentVariableA("BBMOD_PLACE_NAMES_SHA256",hash));
    assert(loadPlaceNames() && placeToken==std::string("zh-CN:")+hash);
    assert(SetEnvironmentVariableA("BBMOD_PLACE_NAMES_SHA256",std::string(64,'0').c_str()));
    assert(!loadPlaceNames());
    assert(SetEnvironmentVariableA("BBMOD_PLACE_NAMES_SHA256",hash));
    assert(loadPlaceNames());
    std::string canonical="Wiesendorf", display;
    std::wstring glyphs;
    std::array<Byte,TEXT_SIZE> original{};
    at<void*>(original.data(),0x40)=original.data();
    at<const char*>(original.data(),0x44)=canonical.c_str();
    at<uint32_t>(original.data(),0x54)=static_cast<uint32_t>(canonical.size());
    at<uint32_t>(original.data(),0x58)=16;
    at<Byte>(original.data(),0x9c)=1;
    const auto originalBytes=original;
    assert(!readText(original.data(),display,glyphs));
    placeSessionPublished.store(true);
    assert(readText(original.data(),display,glyphs) && display=="维森多夫" && glyphs==L"维森多夫");
    Entry glyphEntry;glyphEntry.aliases="glyphs";
    auto rendered=proxy(original.data(),glyphEntry);
    assert(at<Byte>(rendered.data(),0x9c)==0 && at<Byte>(original.data(),0x9c)==1);
    assert(original==originalBytes && canonical=="Wiesendorf");
    placeSessionPublished.store(false);
    assert(!readText(original.data(),display,glyphs));
    std::ifstream mappedInput(argv[2], std::ios::binary);
    assert(mappedInput.good());
    std::vector<unsigned char> mapped((std::istreambuf_iterator<char>(mappedInput)), std::istreambuf_iterator<char>());
    assert(mapped.size() > bbmod::GET_ROOT_RVA + 0x100);
    assert(bbmod::sessionSignatures(mapped.data()));
    mapped[bbmod::GET_ROOT_RVA] ^= 1;
    assert(!bbmod::sessionSignatures(mapped.data()));
    bbmod::PlaceSession bridge(&fakePush, &fakeSlot, &fakePop);
    Object stack[8]{};
    VM vm{}; vm.stack=stack; vm.size=vm.capacity=8; vm.top=2; vm.stackbase=1;
    vm.root={0x0a000020,0x11223344}; stack[0]={0x05000002,13}; stack[1]=vm.root;
    const std::string token = "zh-CN:"+std::string(64,'a');
    uintptr_t before, after;
    __asm mov before, esp
    for (int i=0; i<10000; ++i) {
        assert(bridge.publish(&vm, token));
        assert(vm.top == 2 && published == token && !memcmp(&stack[1],&vm.root,8));
        assert(stack[0].type == 0x05000002 && stack[0].value == 13);
    }
    __asm mov after, esp
    assert(before == after && popCalls == 0 && slotCalls == 10000);
    failSlot=true;
    assert(!bridge.publish(&vm, token) && vm.top == 2 && popCalls == 1);
    failSlot=false;
    int calls=slotCalls;
    assert(!bridge.publish(&vm, ""));
    vm.size=3; assert(!bridge.publish(&vm, token)); vm.size=8;
    stack[1].type=0; assert(!bridge.publish(&vm, token)); stack[1]=vm.root;
    assert(slotCalls == calls && vm.top == 2);
    // A later VM/root receives its own marker too; there is no pointer cache.
    Object secondStack[4]{};
    VM second=vm; second.stack=secondStack; second.size=second.capacity=4;
    second.root.value=0x55667788; secondStack[1]=second.root;
    assert(bridge.publish(&second, token) && second.top == 2);
    __asm mov after, esp
    assert(before == after);
    printf("BBMOD_NATIVE_PLACE_PASS entries=%zu repeated_vm_calls=10000 error_cleanup=passed render_proxy=passed dictionary_hash=passed\n",checked);
    return 0;
}
