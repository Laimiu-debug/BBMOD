// Test builds only: save the game's rendered framebuffer before presentation.
// This copies pixels; it does not redraw or replace any part of the picture.
#ifdef BBMOD_CAPTURE
namespace diagnostic {
using Swap = BOOL(WINAPI*)(HDC);
Swap realSwap = nullptr;
ULONGLONG started = 0;
unsigned saved = 0;
std::wstring destination;
std::wstring requestPath;
ULONGLONG polled = 0;
BOOL WINAPI swap(HDC dc) {
    unsigned requested = 0;
    auto now = GetTickCount64();
    if (!requestPath.empty() && now-polled >= 250) {
        polled = now;
        FILE* request = nullptr;
        if (!_wfopen_s(&request,requestPath.c_str(),L"rb") && request) {
            if (fscanf_s(request,"%u",&requested) != 1 || requested>32) requested=0;
            fclose(request);
        }
    } else if (requestPath.empty() && saved < 3 && now-started >= 90000 + saved*5000) requested=saved+1;
    if (requested > saved && wglGetCurrentContext()) {
        GLint viewport[4]{}, alignment=0, buffer=0;
        glGetIntegerv(GL_VIEWPORT,viewport);
        int w=viewport[2],h=viewport[3];
        if (w>=800 && h>=600 && w<=8192 && h<=8192) {
            std::vector<Byte> pixels(static_cast<size_t>(w)*h*4);
            glGetIntegerv(GL_PACK_ALIGNMENT,&alignment); glGetIntegerv(GL_READ_BUFFER,&buffer);
            glPixelStorei(GL_PACK_ALIGNMENT,1); glReadBuffer(GL_BACK);
            glReadPixels(viewport[0],viewport[1],w,h,0x80e1,GL_UNSIGNED_BYTE,pixels.data());
            glPixelStorei(GL_PACK_ALIGNMENT,alignment); glReadBuffer(buffer);
            BITMAPFILEHEADER fh{}; fh.bfType=0x4d42;
            fh.bfOffBits=sizeof(fh)+sizeof(BITMAPINFOHEADER); fh.bfSize=fh.bfOffBits+static_cast<DWORD>(pixels.size());
            BITMAPINFOHEADER ih{}; ih.biSize=sizeof(ih); ih.biWidth=w; ih.biHeight=h; ih.biPlanes=1; ih.biBitCount=32; ih.biSizeImage=static_cast<DWORD>(pixels.size());
            FILE* f=nullptr; auto path=destination+L"-"+std::to_wstring(requested)+L".bmp";
            if (!_wfopen_s(&f,path.c_str(),L"wb") && f) { fwrite(&fh,sizeof(fh),1,f); fwrite(&ih,sizeof(ih),1,f); fwrite(pixels.data(),1,pixels.size(),f); fclose(f); log("Diagnostic framebuffer captured."); }
            saved=requested;
        }
    }
    return realSwap(dc);
}
void install() {
    destination=env(L"BBMOD_CAPTURE_PATH"); if(destination.empty()) return;
    requestPath=env(L"BBMOD_CAPTURE_REQUEST");
    auto proc=GetProcAddress(GetModuleHandleW(L"gdi32.dll"),"SwapBuffers");
    if(proc && MH_CreateHook(proc,reinterpret_cast<LPVOID>(&swap),reinterpret_cast<LPVOID*>(&realSwap))==MH_OK) {
        started=GetTickCount64(); log("Diagnostic capture is waiting for stable gameplay.");
    }
}
}
#endif
