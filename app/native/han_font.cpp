// BBMOD's independent UTF-8 map font adapter, for original Steam 1.5.2.3.
// Field offsets were verified against the user's executable. Game strings,
// scripts, fonts, saves and on-disk executable bytes are never rewritten here.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>
#include <GL/gl.h>
#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <vector>
#include "vendor/minhook/include/MinHook.h"
#include "place_display.h"
#include "place_session.h"

static_assert(sizeof(void*) == 4, "The game requires a 32-bit adapter");
namespace {
using Byte = unsigned char;
constexpr size_t TEXT_SIZE = 0xa0, FONT_SIZE = 0x1458;
constexpr DWORD CALC_RVA = 0x1611a0, QUEUE_RVA = 0x1612c0, DRAW_RVA = 0x161350;
using Calc = void(__thiscall*)(void*);
using Queue = void(__thiscall*)(void*, void*);
using Draw = void(__thiscall*)(void*, void*, void*);
Calc originalCalc = nullptr;
Queue originalQueue = nullptr;
Draw originalDraw = nullptr;
using GetRoot = int(__cdecl*)(void*);
GetRoot originalGetRoot = nullptr;
std::unique_ptr<bbmod::PlaceSession> placeSession;
bbmod::PlaceDictionary placeNames;
std::string placeToken;
std::atomic<bool> placeSessionPublished{false};
std::wstring fontFile, logFile;
std::recursive_mutex mutex;
uint64_t tick = 0;
size_t cachedBytes = 0;
std::vector<GLuint> retiredTextures;

template<class T> T& at(void* ptr, size_t offset) { return *reinterpret_cast<T*>(static_cast<Byte*>(ptr) + offset); }
void log(const char* s) {
    FILE* f = nullptr;
    if (!_wfopen_s(&f, logFile.c_str(), L"ab") && f) { fputs(s, f); fputs("\n", f); fclose(f); }
}
std::wstring env(const wchar_t* name) {
    wchar_t value[32768]{};
    auto n = GetEnvironmentVariableW(name, value, 32768);
    return n && n < 32768 ? std::wstring(value, n) : std::wstring();
}
bool supportedExecutable() {
    wchar_t path[32768]{}; GetModuleFileNameW(nullptr, path, 32768);
    HANDLE f = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (f == INVALID_HANDLE_VALUE) return false;
    BCRYPT_ALG_HANDLE alg = nullptr; BCRYPT_HASH_HANDLE hash = nullptr;
    bool okay = BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM, nullptr, 0) == 0;
    if (okay) okay = BCryptCreateHash(alg, &hash, nullptr, 0, nullptr, 0, 0) == 0;
    Byte block[65536]; DWORD count;
    while (okay && ReadFile(f, block, sizeof(block), &count, nullptr) && count) okay = BCryptHashData(hash, block, count, 0) == 0;
    Byte digest[32]{};
    if (okay) okay = BCryptFinishHash(hash, digest, 32, 0) == 0;
    if (hash) BCryptDestroyHash(hash); if (alg) BCryptCloseAlgorithmProvider(alg, 0); CloseHandle(f);
    char hex[65]{}; for (int i = 0; i < 32; ++i) sprintf_s(hex + i*2, 3, "%02x", digest[i]);
    return okay && !strcmp(hex, "345126b48b57719e71c80cd21b778f1a0bfda52295cc136ce3895ef43bbafd6a");
}
bool loadPlaceNames() {
    auto path = env(L"BBMOD_PLACE_NAMES_PATH"), expected = env(L"BBMOD_PLACE_NAMES_SHA256");
    if (path.empty() && expected.empty()) return true; // Older packages use the font adapter only.
    if (path.empty() || expected.size() != 64 || expected.find_first_not_of(L"0123456789abcdef") != std::wstring::npos) return false;
    FILE* file = nullptr;
    if (_wfopen_s(&file, path.c_str(), L"rb") || !file) return false;
    std::string raw;
    char block[65536]; size_t count;
    while ((count = fread(block, 1, sizeof(block), file)) != 0 && raw.size() <= 4*1024*1024) raw.append(block, count);
    bool okay = !ferror(file) && raw.size() <= 4*1024*1024;
    fclose(file);
    if (!okay || !MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, raw.data(), static_cast<int>(raw.size()), nullptr, 0)) return false;
    BCRYPT_ALG_HANDLE alg = nullptr; BCRYPT_HASH_HANDLE hash = nullptr;
    okay = BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM, nullptr, 0) == 0;
    if (okay) okay = BCryptCreateHash(alg, &hash, nullptr, 0, nullptr, 0, 0) == 0;
    if (okay) okay = BCryptHashData(hash, reinterpret_cast<Byte*>(raw.data()), static_cast<ULONG>(raw.size()), 0) == 0;
    Byte digest[32]{};
    if (okay) okay = BCryptFinishHash(hash, digest, 32, 0) == 0;
    if (hash) BCryptDestroyHash(hash); if (alg) BCryptCloseAlgorithmProvider(alg, 0);
    char hex[65]{}; for (int i=0; i<32; ++i) sprintf_s(hex+i*2, 3, "%02x", digest[i]);
    if (!okay || !std::equal(expected.begin(), expected.end(), hex) || !placeNames.load(raw)) return false;
    placeToken = std::string("zh-CN:") + hex;
    return true;
}
int __cdecl getRoot(void* vm) {
    const int result = originalGetRoot(vm);
    if (result == 1 && placeSession->publish(vm, placeToken) && !placeSessionPublished.exchange(true)) {
        log("Chinese place display session published to the running VM. Save names remain English.");
    }
    return result;
}
bool readText(void* text, std::string& value, std::wstring& wide) {
    const auto length = at<uint32_t>(text, 0x54), capacity = at<uint32_t>(text, 0x58);
    if (!length || length > 4096 || capacity < length || !at<void*>(text, 0x40)) return false;
    const char* chars = capacity < 16 ? static_cast<char*>(text) + 0x44 : at<const char*>(text, 0x44);
    if (!chars) return false;
    value.assign(chars, length);
    if (placeSessionPublished.load()) value = placeNames.translate(value);
    if (std::none_of(value.begin(), value.end(), [](unsigned char c) { return c >= 128; })) return false;
    int n = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()), nullptr, 0);
    if (!n) return false;
    wide.resize(n);
    MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()), wide.data(), n);
    return true;
}
struct Entry {
    std::array<Byte, FONT_SIZE> font{};
    std::string aliases;
    std::vector<Byte> pixels;
    int width = 0, height = 0;
    GLuint texture = 0;
    uint64_t used = 0;
};
std::map<std::string, std::shared_ptr<Entry>> cache;

std::shared_ptr<Entry> build(void* originFont, const std::wstring& wide) {
    float lineHeight = at<float>(originFont, 0x1454);
    if (!std::isfinite(lineHeight) || lineHeight < 5 || lineHeight > 512) return {};
    // Rasterize at twice the logical size so small serif details survive the
    // game's zoom. Keep its original line height, placement and label color.
    constexpr int rasterScale = 2;
    const int cellHeight = static_cast<int>(std::ceil(lineHeight)) * rasterScale;
    HDC dc = CreateCompatibleDC(nullptr);
    if (!dc) return {};
    HFONT font = CreateFontW(-(cellHeight - 4*rasterScale), 0, 0, 0, FW_SEMIBOLD, FALSE, FALSE, FALSE,
        DEFAULT_CHARSET, OUT_TT_PRECIS, CLIP_DEFAULT_PRECIS, ANTIALIASED_QUALITY, DEFAULT_PITCH, L"Noto Serif SC SemiBold");
    HGDIOBJ oldFont = SelectObject(dc, font);
    TEXTMETRICW metrics{}; GetTextMetricsW(dc, &metrics);
    MAT2 identity{}; identity.eM11.value = identity.eM22.value = 1;
    GLYPHMETRICS ideograph{};
    int textTop = (cellHeight - metrics.tmHeight)/2;
    if (GetGlyphOutlineW(dc, L'国', GGO_METRICS, &ideograph, 0, nullptr, &identity) != GDI_ERROR) {
        textTop = (cellHeight - static_cast<int>(ideograph.gmBlackBoxY))/2 -
                  (metrics.tmAscent - ideograph.gmptGlyphOrigin.y);
    }
    std::map<wchar_t, unsigned char> codes;
    std::map<wchar_t, int> widths;
    unsigned next = 1; int sumWidth = 0;
    for (wchar_t ch : wide) {
        if (ch == L'\n' || ch == L'\r' || codes.count(ch)) continue;
        if (next == 10 || next == 13) ++next;
        if (next > 255) { SelectObject(dc, oldFont); DeleteObject(font); DeleteDC(dc); return {}; }
        codes[ch] = static_cast<unsigned char>(next++);
        SIZE size{}; GetTextExtentPoint32W(dc, &ch, 1, &size);
        widths[ch] = std::max(1, static_cast<int>(size.cx) + 2*rasterScale);
        sumWidth += widths[ch] + 2*rasterScale;
    }
    auto result = std::make_shared<Entry>();
    memcpy(result->font.data(), originFont, FONT_SIZE);
    memset(result->font.data() + 0x54, 0, 0x1400);
    result->width = 64;
    while (result->width < std::min(1024, std::max(64, sumWidth))) result->width *= 2;
    int x = 1, y = 0;
    std::map<wchar_t, std::pair<int,int>> positions;
    for (auto [ch, code] : codes) {
        if (x + widths[ch] >= result->width) { x = 1; y += cellHeight + 2*rasterScale; }
        positions[ch] = {x, y}; x += widths[ch] + 2*rasterScale;
    }
    result->height = 32; while (result->height < y + cellHeight + 2) result->height *= 2;
    BITMAPINFO info{}; info.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    info.bmiHeader.biWidth = result->width; info.bmiHeader.biHeight = -result->height;
    info.bmiHeader.biPlanes = 1; info.bmiHeader.biBitCount = 32; info.bmiHeader.biCompression = BI_RGB;
    void* bits = nullptr; HBITMAP bitmap = CreateDIBSection(dc, &info, DIB_RGB_COLORS, &bits, nullptr, 0);
    if (!bitmap || !bits) { SelectObject(dc, oldFont); DeleteObject(font); DeleteDC(dc); return {}; }
    HGDIOBJ oldBitmap = SelectObject(dc, bitmap);
    const size_t byteCount = static_cast<size_t>(result->width) * result->height * 4;
    memset(bits, 0, byteCount); SetBkMode(dc, TRANSPARENT); SetTextColor(dc, RGB(255,255,255));
    for (auto [ch, code] : codes) {
        auto [cx, cy] = positions[ch]; TextOutW(dc, cx + rasterScale, cy + textTop, &ch, 1);
        float* uv = reinterpret_cast<float*>(result->font.data() + 0x54 + code*16);
        uv[0] = float(cx)/result->width; uv[1] = float(cx + widths[ch])/result->width;
        uv[2] = float(cy + cellHeight)/result->height; uv[3] = float(cy)/result->height;
        at<float>(result->font.data(), 0x1054 + code*4) = float(widths[ch])/rasterScale;
    }
    GdiFlush(); result->pixels.resize(byteCount);
    auto coverage = [&](int px, int py) -> unsigned {
        if (px < 0 || py < 0 || px >= result->width || py >= result->height) return 0;
        return static_cast<Byte*>(bits)[(static_cast<size_t>(py)*result->width + px)*4 + 1];
    };
    for (int py = 0; py < result->height; ++py) for (int px = 0; px < result->width; ++px) {
        const unsigned ink = coverage(px, py);
        unsigned edge = 0;
        for (int dy=-rasterScale; dy<=rasterScale; ++dy) for (int dx=-rasterScale; dx<=rasterScale; ++dx) {
            if (dx*dx+dy*dy<=rasterScale*rasterScale) edge=std::max(edge,coverage(px+dx,py+dy));
        }
        // Straight-alpha white ink over a fine dark outline. Pixels outside
        // the glyph and its outline stay fully transparent; no label plaque.
        const unsigned stroke = edge*3/4;
        const unsigned alpha = ink + stroke*(255-ink)/255;
        const Byte color = alpha ? static_cast<Byte>(ink*255/alpha) : 0;
        const size_t i = (static_cast<size_t>(py)*result->width + px)*4;
        result->pixels[i] = result->pixels[i+1] = result->pixels[i+2] = color;
        result->pixels[i+3] = static_cast<Byte>(alpha);
    }
    SelectObject(dc, oldBitmap); SelectObject(dc, oldFont); DeleteObject(bitmap); DeleteObject(font); DeleteDC(dc);
    for (wchar_t ch : wide) {
        if (ch == L'\r') continue;
        result->aliases += ch == L'\n' ? '\n' : char(codes[ch]);
    }
    at<int>(result->font.data(), 0x30) = result->width;
    at<int>(result->font.data(), 0x34) = result->height;
    at<int>(result->font.data(), 0x38) = 4;
    at<float>(result->font.data(), 0x1454) = lineHeight;
    return result;
}
std::shared_ptr<Entry> get(void* text) {
    std::string value; std::wstring wide;
    if (!readText(text, value, wide)) return {};
    void* font = at<void*>(text, 0x40);
    auto key = value + '\0' + std::to_string(reinterpret_cast<uintptr_t>(font)) + '/' + std::to_string(at<float>(font, 0x1454));
    std::lock_guard<std::recursive_mutex> lock(mutex);
    ++tick;
    auto found = cache.find(key);
    if (found != cache.end()) { found->second->used = tick; return found->second; }
    auto entry = build(font, wide); if (!entry) return {};
    entry->used = tick; cachedBytes += entry->pixels.size();
    if (cache.size() > 2048 || cachedBytes > 128*1024*1024) {
        for (auto it = cache.begin(); it != cache.end();) {
            if (it->second.use_count() == 1 && tick - it->second->used > 8192) {
                cachedBytes -= it->second->pixels.size();
                if (it->second->texture) retiredTextures.push_back(it->second->texture);
                it = cache.erase(it);
            } else ++it;
        }
    }
    cache.emplace(std::move(key), entry); return entry;
}
bool upload(Entry& e) {
    std::lock_guard<std::recursive_mutex> lock(mutex);
    if (e.texture) return true;
    if (!wglGetCurrentContext()) return false;
    GLint binding = 0; glGetIntegerv(GL_TEXTURE_BINDING_2D, &binding);
    glGenTextures(1, &e.texture); glBindTexture(GL_TEXTURE_2D, e.texture);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, 0x812f);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, 0x812f);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, e.width, e.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, e.pixels.data());
    glBindTexture(GL_TEXTURE_2D, binding); at<GLuint>(e.font.data(), 0x2c) = e.texture;
    for (GLuint texture : retiredTextures) glDeleteTextures(1, &texture);
    retiredTextures.clear(); return e.texture != 0;
}
std::array<Byte, TEXT_SIZE> proxy(void* text, Entry& e) {
    std::array<Byte, TEXT_SIZE> copy{}; memcpy(copy.data(), text, TEXT_SIZE);
    at<void*>(copy.data(), 0x40) = e.font.data();
    at<const char*>(copy.data(), 0x44) = e.aliases.c_str();
    at<uint32_t>(copy.data(), 0x54) = static_cast<uint32_t>(e.aliases.size());
    at<uint32_t>(copy.data(), 0x58) = std::max<uint32_t>(16, static_cast<uint32_t>(e.aliases.size()));
    // In this verified executable +0x9c enables the rectangular background
    // brush (+0x80). Disable it on the render proxy only; the original label
    // object, visibility, interactions and save data remain unchanged.
    at<Byte>(copy.data(), 0x9c) = 0;
    return copy;
}
void __fastcall calc(void* text, void*) {
    auto e = get(text); if (!e) { originalCalc(text); return; }
    static std::once_flag reported;
    std::call_once(reported, [] { log("Chinese label bounds calculated."); });
    auto copy = proxy(text, *e); originalCalc(copy.data());
    memcpy(static_cast<Byte*>(text)+0x5c, copy.data()+0x5c, 24);
}
void __fastcall queue(void* text, void*, void* list) {
    auto e = get(text); if (!e || !upload(*e)) { originalQueue(text, list); return; }
    auto copy = proxy(text, *e); originalQueue(copy.data(), list);
}
void __fastcall draw(void* text, void*, void* a, void* b) {
    auto e = get(text); if (!e || !e->texture) { originalDraw(text, a, b); return; }
    static std::once_flag reported;
    std::call_once(reported, [] { log("Chinese label rendered with its own glyph atlas."); });
    auto copy = proxy(text, *e); originalDraw(copy.data(), a, b);
}
#include "diagnostic_capture.h"
struct PreviewTitle { const wchar_t* text; bool applied; };
BOOL CALLBACK setPreviewTitle(HWND window, LPARAM value) {
    DWORD processId=0; GetWindowThreadProcessId(window,&processId);
    if(processId!=GetCurrentProcessId() || !IsWindowVisible(window)) return TRUE;
    wchar_t current[256]{}; GetWindowTextW(window,current,256);
    if(!wcsstr(current,L"Battle Brothers")) return TRUE;
    auto request=reinterpret_cast<PreviewTitle*>(value);
    request->applied=SetWindowTextW(window,request->text)!=FALSE;
    return request->applied ? FALSE : TRUE;
}
DWORD WINAPI previewTitleWorker(void*) {
    auto title=env(L"BBMOD_PREVIEW_TITLE");
    if(title.empty()) return 0;
    PreviewTitle request{title.c_str(),false};
    for(int i=0;i<150 && !request.applied;++i) {
        EnumWindows(setPreviewTitle,reinterpret_cast<LPARAM>(&request));
        if(!request.applied) Sleep(200);
    }
    return 0;
}
DWORD signalResult(DWORD code) {
    auto name = env(code ? L"BBMOD_FONT_FAILED" : L"BBMOD_FONT_READY");
    if (!name.empty()) {
        HANDLE event = OpenEventW(EVENT_MODIFY_STATE, FALSE, name.c_str());
        if (event) { SetEvent(event); CloseHandle(event); }
    }
    return code;
}
DWORD WINAPI initialize(void*) {
    fontFile = env(L"BBMOD_FONT_PATH"); logFile = env(L"BBMOD_FONT_LOG");
    if (logFile.empty()) return signalResult(1);
    if (!supportedExecutable()) { log("Unsupported executable: adapter not installed."); return signalResult(2); }
    if (!loadPlaceNames()) { log("Place dictionary validation failed. No hooks installed."); return signalResult(8); }
    if (fontFile.empty() || !AddFontResourceExW(fontFile.c_str(), FR_PRIVATE, nullptr)) { log("Cannot load independent Chinese font."); return signalResult(3); }
    Byte* base = reinterpret_cast<Byte*>(GetModuleHandleW(nullptr));
    // The legitimate game startup loads its executable before the adapter hooks.
    const Byte calcSignature[] = {0x83,0x79,0x40,0x00};
    const Byte drawSignature[] = {0x55,0x8b,0xec,0x83,0xe4,0xf8};
    const Byte queueSignature[] = {0x55,0x8b,0xec,0x51,0x56,0x8b,0xf1};
    bool ready = false;
    for (int i = 0; i < 120; ++i) {
        if (!memcmp(base+CALC_RVA,calcSignature,sizeof(calcSignature)) && !memcmp(base+DRAW_RVA,drawSignature,sizeof(drawSignature)) && !memcmp(base+QUEUE_RVA,queueSignature,sizeof(queueSignature)) &&
            (placeToken.empty() || bbmod::sessionSignatures(base))) { ready = true; break; }
        Sleep(250);
    }
    if (!ready || MH_Initialize()!=MH_OK) { log("Font hook preflight failed."); return signalResult(4); }
    if (MH_CreateHook(base+CALC_RVA, reinterpret_cast<LPVOID>(&calc), reinterpret_cast<LPVOID*>(&originalCalc)) != MH_OK ||
        MH_CreateHook(base+QUEUE_RVA, reinterpret_cast<LPVOID>(&queue), reinterpret_cast<LPVOID*>(&originalQueue)) != MH_OK ||
        MH_CreateHook(base+DRAW_RVA, reinterpret_cast<LPVOID>(&draw), reinterpret_cast<LPVOID*>(&originalDraw)) != MH_OK) {
        MH_Uninitialize(); log("Font hooks were not applied."); return signalResult(5);
    }
    if (!placeToken.empty()) {
        placeSession = std::make_unique<bbmod::PlaceSession>(base);
        if (MH_CreateHook(base+bbmod::GET_ROOT_RVA, reinterpret_cast<LPVOID>(&getRoot), reinterpret_cast<LPVOID*>(&originalGetRoot)) != MH_OK) {
            MH_Uninitialize(); log("Place session hook was not applied."); return signalResult(9);
        }
    }
#ifdef BBMOD_CAPTURE
    diagnostic::install();
#endif
    if (MH_EnableHook(MH_ALL_HOOKS)!=MH_OK) { MH_DisableHook(MH_ALL_HOOKS); log("Font hook activation failed."); return signalResult(6); }
    if(!env(L"BBMOD_PREVIEW_TITLE").empty()) {
        HANDLE titleThread=CreateThread(nullptr,0,previewTitleWorker,nullptr,0,nullptr);
        if(titleThread) CloseHandle(titleThread);
    }
    log("BBMOD native Chinese font ready. Original strings are retained."); return signalResult(0);
}
}
BOOL WINAPI DllMain(HINSTANCE module, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(module);
        HANDLE thread = CreateThread(nullptr, 0, initialize, nullptr, 0, nullptr);
        if (thread) CloseHandle(thread);
    }
    return TRUE;
}
