// Launch the user's original executable and load only our local font adapter.
// 32-bit helper: remote addresses therefore use the target process's ABI.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string>
#include <cstdio>
int wmain(int argc, wchar_t** argv) {
    if (argc != 5) { fwprintf(stderr,L"需要游戏路径、字体适配器、字体和日志路径。\n"); return 2; }
    SetEnvironmentVariableW(L"BBMOD_FONT_PATH", argv[3]);
    SetEnvironmentVariableW(L"BBMOD_FONT_LOG", argv[4]);
    SetEnvironmentVariableW(L"SteamAppId", L"365360");
    SetEnvironmentVariableW(L"SteamGameId", L"365360");
    std::wstring key = L"Local\\BBMOD_Font_" + std::to_wstring(GetCurrentProcessId()) + L"_" + std::to_wstring(GetTickCount64());
    auto readyName = key + L"_ready", failedName = key + L"_failed";
    HANDLE ready = CreateEventW(nullptr, TRUE, FALSE, readyName.c_str());
    HANDLE failed = CreateEventW(nullptr, TRUE, FALSE, failedName.c_str());
    if (!ready || !failed) return 4;
    SetEnvironmentVariableW(L"BBMOD_FONT_READY", readyName.c_str());
    SetEnvironmentVariableW(L"BBMOD_FONT_FAILED", failedName.c_str());
    std::wstring exe = argv[1], command = L"\"" + exe + L"\"";
    auto folder = exe.substr(0, exe.find_last_of(L"\\/"));
    STARTUPINFOW startup{}; startup.cb=sizeof(startup);
    PROCESS_INFORMATION process{};
    if (!CreateProcessW(exe.c_str(),command.data(),nullptr,nullptr,FALSE,CREATE_SUSPENDED,nullptr,folder.c_str(),&startup,&process)) return 3;
    const size_t size = (wcslen(argv[2])+1)*sizeof(wchar_t);
    void* remote=VirtualAllocEx(process.hProcess,nullptr,size,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    bool okay=remote && WriteProcessMemory(process.hProcess,remote,argv[2],size,nullptr);
    HANDLE loader=nullptr;
    if (okay) loader=CreateRemoteThread(process.hProcess,nullptr,0,reinterpret_cast<LPTHREAD_START_ROUTINE>(GetProcAddress(GetModuleHandleW(L"kernel32.dll"),"LoadLibraryW")),remote,0,nullptr);
    // DLL initialization creates a worker; legitimate startup must run before
    // its format-checked hooks can become active.
    ResumeThread(process.hThread);
    DWORD module=0;
    if (loader) {
        okay = WaitForSingleObject(loader,15000)==WAIT_OBJECT_0 && GetExitCodeThread(loader,&module) && module;
        CloseHandle(loader);
    } else okay=false;
    if (remote && okay) VirtualFreeEx(process.hProcess,remote,0,MEM_RELEASE);
    if (okay) {
        HANDLE events[] = { ready, failed, process.hProcess };
        okay = WaitForMultipleObjects(3, events, FALSE, 35000) == WAIT_OBJECT_0;
    }
    CloseHandle(ready); CloseHandle(failed);
    if (!okay) { TerminateProcess(process.hProcess,7); fwprintf(stderr,L"中文显示组件未能加载，本次启动已停止。\n"); }
    if (okay) printf("%lu\n",process.dwProcessId);
    CloseHandle(process.hThread);CloseHandle(process.hProcess);return okay?0:7;
}
