// Pinned 32-bit Steam 1.5.2.3 Squirrel ABI. See place_session_abi.md.
// The compiler's internal register convention is NOT MSVC __fastcall.
#pragma once
#include <cstdint>
#include <cstring>
#include <string>

namespace bbmod {
constexpr uint32_t GET_ROOT_RVA = 0x19f070, PUSH_STRING_RVA = 0x185ca0,
                   NEW_SLOT_RVA = 0x1870f0, POP_RVA = 0x190910;
inline bool sessionSignatures(const unsigned char* base) {
    const unsigned char root[] = {0x55,0x8b,0xec,0x8b,0x55,0x08,0x56,0x57,0x8b,0x4a,0x24};
    const unsigned char push[] = {0x55,0x8b,0xec,0x6a,0xff};
    const unsigned char pushRegisters[] = {0x8b,0xf9,0x85,0xd2};
    const unsigned char slot[] = {0x55,0x8b,0xec,0x53,0x56,0x8b,0xf1,0x57,0x8b,0x7e,0x24,0x8b,0xc7,0x8b,0x5e,0x28};
    const unsigned char pop[] = {0x55,0x8b,0xec,0x56,0x8b,0x75,0x08,0x57,0x8b,0xf9,0x85,0xf6};
    const unsigned char popReturn[] = {0xc2,0x04,0x00};
    return !memcmp(base + GET_ROOT_RVA, root, sizeof(root)) &&
           !memcmp(base + PUSH_STRING_RVA, push, sizeof(push)) &&
           !memcmp(base + PUSH_STRING_RVA + 0x24, pushRegisters, sizeof(pushRegisters)) &&
           !memcmp(base + NEW_SLOT_RVA, slot, sizeof(slot)) &&
           !memcmp(base + POP_RVA, pop, sizeof(pop)) &&
           !memcmp(base + POP_RVA + 0x49, popReturn, sizeof(popReturn));
}
class PlaceSession {
    void *pushAddress, *slotAddress, *popAddress;
    template<class T> static T& field(void* vm, size_t offset) {
        return *reinterpret_cast<T*>(static_cast<unsigned char*>(vm) + offset);
    }
    void pushString(void* vm, const char* value) const {
        void* address = pushAddress;
        __asm {
            mov ecx, vm
            mov edx, value
            push -1
            mov eax, address
            call eax
            add esp, 4
        }
    }
    int newSlot(void* vm) const {
        void* address = slotAddress;
        int result;
        __asm {
            mov ecx, vm
            mov edx, -3
            push 0
            mov eax, address
            call eax
            add esp, 4
            mov result, eax
        }
        return result;
    }
public:
    PlaceSession(void* push, void* slot, void* pop): pushAddress(push), slotAddress(slot), popAddress(pop) {}
    explicit PlaceSession(unsigned char* base): PlaceSession(base + PUSH_STRING_RVA, base + NEW_SLOT_RVA, base + POP_RVA) {}
    bool publish(void* vm, const std::string& token) const {
        if (!vm || token.empty()) return false;
        const int top = field<int>(vm, 0x24), size = field<int>(vm, 0x1c), stackbase = field<int>(vm, 0x28);
        auto stack = field<uint32_t*>(vm, 0x18);
        // Only initialized VM slots may be used. Never resize native stack
        // storage or infer capacity from an unrelated process/VM instance.
        if (!stack || top < 1 || size < 3 || top > size - 2 || stackbase < 0 || stackbase >= top ||
            field<uint32_t>(vm, 0x30) != 0x0a000020 ||
            stack[(top - 1)*2] != 0x0a000020 || stack[(top - 1)*2 + 1] != field<uint32_t>(vm, 0x34)) return false;
        pushString(vm, "BBMODPlaceDisplaySession");
        pushString(vm, token.c_str());
        const int status = newSlot(vm);
        const int after = field<int>(vm, 0x24);
        if (after > top && after <= top + 2) {
            using Pop = void(__thiscall*)(void*, int);
            reinterpret_cast<Pop>(popAddress)(vm, after - top);
        }
        return status >= 0 && after == top;
    }
};
}
