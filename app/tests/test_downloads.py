"""Exercise real HTTP disconnects and resumption without touching player files."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import threading
from unittest.mock import patch
from urllib.parse import urlsplit

import pytest

from core import downloads


@pytest.mark.parametrize('mode', ['resume', 'ignore_range', 'bad_range', 'bad_total', 'blocked', 'corrupt', 'unavailable'])
def test_interrupted_http_download(tmp_path, mode):
    data = bytes(range(256)) * 1024
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            calls.append(self.headers.get('Range'))
            if len(calls) == 1:
                self.send_response(200)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data[:65536])
                self.close_connection = True
                return
            if mode in {'blocked', 'unavailable'}:
                self.send_error(404 if mode == 'blocked' else 503)
                return
            offset = int(self.headers['Range'].removeprefix('bytes=').removesuffix('-'))
            self.send_response(200 if mode == 'ignore_range' else 206)
            if mode == 'ignore_range':
                offset = 0
            else:
                start = offset + (mode == 'bad_range')
                total = len(data) + (mode == 'bad_total')
                self.send_header('Content-Range', f'bytes {start}-{len(data) - 1}/{total}')
            self.send_header('Content-Length', str(len(data) - offset))
            self.end_headers()
            body = data[offset:]
            if mode == 'corrupt':
                body = b'x' * len(body)
            self.wfile.write(body)

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        target = tmp_path / 'file.zip'
        progress = []
        with patch.object(downloads, '_pause'):
            def run():
                downloads.download_verified(f'http://127.0.0.1:{server.server_port}/file', target,
                    size=len(data), sha256=hashlib.sha256(data).hexdigest(), progress=progress.append)
            if mode in {'resume', 'ignore_range'}:
                run()
                assert target.read_bytes() == data
                assert '下载完成' in progress[-1]
            else:
                with pytest.raises(ValueError):
                    run()
        assert calls[0] is None
        assert calls[1] == 'bytes=65536-'
        assert len(calls) == (downloads.MAX_RETRIES + 1 if mode == 'unavailable' else 2)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_healthy_slow_transfer_has_no_three_minute_cutoff(tmp_path):
    data = b'slow network' * 100

    class Slow(io.BytesIO):
        status = 200
        headers = {}

        def read1(self, _):
            return super().read(100)

    with patch.object(downloads, '_request', return_value=Slow(data)), patch.object(
            downloads.time, 'monotonic', side_effect=[n * 200 for n in range(30)]):
        target = tmp_path / 'slow.zip'
        downloads.download_verified('https://example.invalid/file', target,
            size=len(data), sha256=hashlib.sha256(data).hexdigest())
    assert target.read_bytes() == data


def test_cancel_during_retry_never_opens_another_connection(tmp_path):
    cancel = threading.Event()
    with patch.object(downloads, '_request', side_effect=TimeoutError) as request:
        with pytest.raises(ValueError, match='已取消'):
            downloads.download_verified('https://example.invalid/file', tmp_path / 'cancel.zip',
                size=10, sha256='a' * 64, cancelled=cancel.is_set, progress=lambda _: cancel.set())
    assert request.call_count == 1


def test_disk_error_is_not_retried(tmp_path):
    target = tmp_path / 'file'
    with patch.object(downloads, '_request') as request, patch('pathlib.Path.open', side_effect=OSError('disk full')):
        with pytest.raises(OSError, match='disk full'):
            downloads.download_verified('https://example.invalid/file', target, size=10, sha256='a' * 64)
    request.assert_not_called()


def test_old_official_download_uses_new_site_and_retries_with_same_hash(tmp_path):
    url = 'https://bbmod.site/files/ba29edd4-f68d-4cce-9024-e2f1056d774d/download/'
    data = b'checked content'
    response = io.BytesIO(data)
    response.status, response.headers = 200, {}
    with patch.object(downloads, '_request', side_effect=[TimeoutError(), response]) as request, patch.object(downloads, '_pause'):
        target = tmp_path / 'file'
        downloads.download_verified(url, target, size=len(data), sha256=hashlib.sha256(data).hexdigest())
    assert [call.args for call in request.call_args_list] == [
        ('https://bbmod.com' + urlsplit(url).path, 0)] * 2
    assert target.read_bytes() == data


@pytest.mark.parametrize('url', [
    'https://custom.example/files/ba29edd4-f68d-4cce-9024-e2f1056d774d/download/',
    'https://bbmod.site/api/private/', 'https://bbmod.site.evil/files/x/download/',
    'https://bbmod.site:8443/files/ba29edd4-f68d-4cce-9024-e2f1056d774d/download/',
    'https://bbmod.site/files/ba29edd4-f68d-4cce-9024-e2f1056d774d/download/?token=private'])
def test_other_routes_never_switch_sources(url):
    assert downloads.canonical_download_url(url) == url
