"""Exercise real Qt networking against an isolated local HTTP fixture."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from dataclasses import replace
import hashlib
import json
import threading
import time

import pytest
from PySide6.QtWidgets import QApplication
from urllib.parse import urlsplit

from core.app_updates import RELEASES_URL
from ui.update_service import UpdateService, DIRECT_API_URL
from test_app_updates import parsed, release_row, settings_at, site_row


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def network(app, tmp_path, monkeypatch):
    response = {'code': 200, 'body': json.dumps([release_row('v999.0.0', preview=False)]).encode(), 'redirect': None, 'requests': []}
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if response.get('handler'):
                response['handler'](self)
                return
            content = response.get('routes', {}).get(self.path, response)
            self.send_response(content['code'])
            if content.get('redirect'): self.send_header('Location', content['redirect'])
            self.send_header('Content-Length', str(len(content['body'])))
            self.end_headers()
            try: self.wfile.write(content['body'])
            except (BrokenPipeError, ConnectionResetError): pass
        def log_message(self, *_args): pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True);thread.start()
    service = UpdateService(settings_at(tmp_path), automatic=False)
    original = service._request
    def request(url):
        response['requests'].append(url)
        return original(f'http://127.0.0.1:{server.server_port}' + urlsplit(url).path)
    monkeypatch.setattr(service, '_request', request)
    yield service, response
    service.shutdown();app.processEvents()
    server.shutdown();server.server_close();thread.join(timeout=2)


def wait_idle(app, service):
    deadline = time.monotonic() + 5
    while service.busy and time.monotonic() < deadline:
        app.processEvents();time.sleep(0.005)
    assert not service.busy


def test_real_check_and_hash_verified_download(app, network):
    service, response = network
    service.check();wait_idle(app, service)
    assert service.latest().tag == 'v999.0.0'
    assert service.preferences['last_check']
    assert '发现新版本' in service.status
    response['body'] = b'MZ-new'
    service.download(service.latest());wait_idle(app, service)
    assert service.downloaded.read_bytes() == b'MZ-new'
    assert not list(service.folder.rglob('*.part'))


@pytest.mark.parametrize('code,body,expected', [(429, b'limited', '限制'), (500, b'error', '失败'), (200, b'not json', '无效')])
def test_failed_check_is_not_reported_as_current(app, network, code, body, expected):
    service, response = network
    response.update(code=code, body=body)
    service.check();wait_idle(app, service)
    assert expected in service.status
    assert not service.preferences.get('last_check') and not service.releases


@pytest.mark.parametrize('body', [b'MZ-bad', b'MZ-too-large', b'MZ'])
def test_corrupt_downloads_are_discarded(app, network, body):
    service, response = network
    response['body'] = body
    service.download(parsed());wait_idle(app, service)
    assert service.downloaded is None
    assert not list(service.folder.rglob('*.part'))


def test_cancel_and_untrusted_redirect(app, network):
    service, response = network
    service.download(parsed());service.cancel();wait_idle(app, service)
    assert service.downloaded is None and '取消' in service.status
    response.update(code=302, body=b'', redirect='https://example.org/BBMOD.exe')
    service.download(parsed());wait_idle(app, service)
    assert service.downloaded is None and '跳转' in service.status


def test_official_first_and_fallback_only_after_failure(app, network):
    from core.app_updates import SITE_API_URL, API_URL
    service, response = network
    response['body'] = json.dumps({'schema_version': 1, 'releases': [site_row()]}).encode()
    service.check();wait_idle(app, service)
    assert response['requests'] == [DIRECT_API_URL]
    assert service.latest().download_url.startswith('https://bbmod.com/')
    response['requests'].clear()
    response['body'] = json.dumps([release_row('v999.0.0', preview=False)]).encode()
    service.check();wait_idle(app, service)
    assert response['requests'] == [DIRECT_API_URL, SITE_API_URL, API_URL]
    assert service.latest().tag == 'v999.0.0'


def test_github_recovers_without_false_completion_or_old_host_requests(app, network):
    from core.app_updates import SITE_API_URL, API_URL
    service, response = network
    response['routes'] = {
        '/api/v1/desktop/releases/': {'code': 503, 'body': b'unavailable'},
        urlsplit(API_URL).path: {
            'code': 200, 'body': json.dumps([release_row('v999.0.0', preview=False)]).encode()},
    }
    states = []
    service.changed.connect(lambda: states.append(service.busy))
    service.check(); wait_idle(app, service)
    assert response['requests'] == [DIRECT_API_URL, SITE_API_URL, API_URL]
    assert service.latest().tag == 'v999.0.0'
    assert service._source == 'github'
    assert states == ['check', 'check', 'check', '']


def test_cancel_check_does_not_try_another_source(app, network):
    from core.app_updates import SITE_API_URL
    service, response = network
    service.check(); service.cancel(); wait_idle(app, service)
    assert response['requests'] == [DIRECT_API_URL]
    assert '取消' in service.status and not service.preferences.get('last_check')


def test_local_record_failure_does_not_retry_network(app, network, monkeypatch):
    from core.app_updates import SITE_API_URL
    service, response = network
    response['body'] = json.dumps({'schema_version': 1, 'releases': [site_row()]}).encode()
    def fail(*args):
        raise OSError('disk full')
    monkeypatch.setattr(service.settings, 'set', fail)
    service.check(); wait_idle(app, service)
    assert response['requests'] == [DIRECT_API_URL]
    assert '记录未保存' in service.status
    assert not service.preferences.get('last_check')


@pytest.mark.parametrize('mode', ['resume', 'ignore_range', 'bad_range', 'bad_total', 'corrupt', 'withdrawn'])
def test_interrupted_update_switches_route_and_resumes_only_verified_range(app, network, mode):
    service, response = network
    data = b'MZ' + bytes(range(256)) * 1024
    release = replace(parsed(), download_url='https://bbmod.com/downloads/windows/01234567-89ab-cdef-0123-456789abcdef/',
                      size=len(data), sha256=hashlib.sha256(data).hexdigest())
    calls = []
    def handler(request):
        calls.append((request.path, request.headers.get('Range')))
        if len(calls) == 1:
            request.send_response(200)
            request.send_header('Content-Length', str(len(data)))
            request.end_headers()
            request.wfile.write(data[:65536])
            request.close_connection = True
            return
        if mode == 'withdrawn':
            request.send_error(404)
            return
        offset = int(request.headers['Range'][6:-1])
        request.send_response(200 if mode == 'ignore_range' else 206)
        if mode == 'ignore_range':
            offset = 0
        else:
            request.send_header('Content-Range', f'bytes {offset + (mode == "bad_range")}-{len(data)-1}/{len(data) + (mode == "bad_total")}')
        request.send_header('Content-Length', str(len(data)-offset))
        request.end_headers()
        try:
            request.wfile.write(b'x' * (len(data)-offset) if mode == 'corrupt' else data[offset:])
        except (BrokenPipeError, ConnectionResetError):
            pass
    response['handler'] = handler
    service.download(release); wait_idle(app, service)
    assert calls == [('/bbmod' + urlsplit(release.download_url).path, None),
                     (urlsplit(release.download_url).path, 'bytes=65536-')]
    if mode in {'resume', 'ignore_range'}:
        assert service.downloaded.read_bytes() == data
    else:
        assert service.downloaded is None
    assert not list(service.folder.rglob('*.part'))


def test_cancel_waiting_retry_does_not_reconnect(app, network):
    service, response = network
    response.update(code=503, body=b'busy')
    service.download(parsed())
    deadline = time.monotonic()+3
    while not service._retry_timer.isActive() and time.monotonic() < deadline:
        app.processEvents();time.sleep(.005)
    assert service._retry_timer.isActive()
    service.cancel();wait_idle(app, service)
    assert len(response['requests']) == 1
    assert '取消' in service.status and service.downloaded is None
    assert not service._retry_timer.isActive() and not list(service.folder.rglob('*.part'))


def test_official_metadata_recovers_from_direct_route_failure(app, network):
    from core.app_updates import SITE_API_URL
    service, response = network
    response['routes'] = {
        '/bbmod/api/v1/desktop/releases/': {'code': 503, 'body': b'busy'},
        '/api/v1/desktop/releases/': {'code': 200, 'body': json.dumps({'schema_version':1, 'releases':[site_row()]}).encode()},
    }
    service.check();wait_idle(app,service)
    assert response['requests'] == [DIRECT_API_URL,SITE_API_URL]
    assert service.latest().download_url.startswith('https://bbmod.com/')
