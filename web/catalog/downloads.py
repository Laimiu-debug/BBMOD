"""Authorize in Django, then let the private gateway stream large MOD files."""
from pathlib import Path
from urllib.parse import quote

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.http import FileResponse, Http404, HttpResponse
from django.utils.http import content_disposition_header


def mod_file_response(request, field, *, filename, size=None, sha256=None, cover=False):
    try:
        root = Path(settings.MEDIA_ROOT).resolve()
        path = Path(field.path)
        relative = path.relative_to(root)
        if (not relative.parts or '..' in relative.parts or path.is_symlink()
                or path.resolve() != path or not path.is_file()):
            raise Http404
        actual_size = path.stat().st_size
        if size is not None and actual_size != size:
            raise Http404
        content_type = 'image/webp' if cover else 'application/zip'
        if settings.MOD_DOWNLOAD_ACCEL:
            response = HttpResponse(content_type=content_type)
            response['X-Accel-Redirect'] = '/_mods/' + quote(relative.as_posix(), safe='/')
        elif request.method == 'HEAD':
            response = HttpResponse(content_type=content_type)
        else:
            response = FileResponse(field.open('rb'), content_type=content_type)
    except (OSError, ValueError, SuspiciousFileOperation):
        raise Http404
    response['Content-Disposition'] = content_disposition_header(not cover, filename)
    response['Content-Length'] = actual_size
    response['Cache-Control'] = 'private, no-store'
    if sha256:
        response['X-Checksum-SHA256'] = sha256
    return response
