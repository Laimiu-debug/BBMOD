from django.conf import settings
from django.core.files.uploadhandler import FileUploadHandler, StopUpload
from django.http import HttpResponse
from django.shortcuts import redirect


class BoundedUploadHandler(FileUploadHandler):
    total = 0
    def receive_data_chunk(self, raw_data, start):
        self.total += len(raw_data)
        if self.total > settings.MAX_MOD_BYTES + 6 * 1024 * 1024:
            raise StopUpload(connection_reset=True)
        return raw_data
    def file_complete(self, file_size):
        return None


class AccountMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        request.upload_handlers.insert(0, BoundedUploadHandler(request))
        if int(request.META.get('CONTENT_LENGTH') or 0) > settings.MAX_MOD_BYTES + 8 * 1024 * 1024:
            return HttpResponse('上传文件超过大小限制。', status=413)
        if request.user.is_authenticated and request.path.startswith(('/workshop/', '/manage/')):
            profile = getattr(request.user, 'author_profile', None)
            if profile and profile.must_change_password:
                return redirect('password_change')
        return self.get_response(request)


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        response = self.get_response(request)
        response['Content-Security-Policy'] = "default-src 'self'; img-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        response['Referrer-Policy'] = 'same-origin'
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        if request.path.startswith(('/workshop/', '/manage/', '/login/', '/password/')):
            response['Cache-Control'] = 'no-store'
        return response
