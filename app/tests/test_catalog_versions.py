import io
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from core.catalog_versions import identify_release_versions, public_release_links
from core.site_config import SITE_ORIGIN


WORK = '00000000-0000-0000-0000-000000000001'
RELEASES = [f'00000000-0000-0000-0000-{number:012d}' for number in range(2, 7)]


def item():
    return {'id': WORK, 'sha256': 'b' * 64, 'version': '0.28.14', 'page_path': f'/mods/{WORK}/'}


def history(entries):
    return '<section class="history">' + ''.join(
        f'<h3>v{version}</h3><a href="{link}">下载</a>' for version, link in entries) + '</section>'


def download(index=0):
    return f'/files/{RELEASES[index]}/download/'


class HeadResponse:
    def __init__(self, digest, status=200):
        self.headers = {'X-Checksum-SHA256': digest}
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, *_):
        pytest.fail('HEAD identity checks must never download the archive body')

    read1 = read


def test_history_links_are_limited_to_same_site_and_history_section():
    foreign = ['https://foreign.example' + download(), '//foreign.example' + download(),
               download() + '?token=secret', download() + '#section',
               'https://user:pass@bbmod.com' + download(), 'https://@bbmod.com' + download(),
               'javascript:alert(1)', 'https://[broken', '/other/download/']
    entries = [(f'0.28.{number}', link) for number, link in enumerate(foreign)]
    entries += [('0.28.12', download()), ('0.28.11', SITE_ORIGIN + download(1)),
                ('0.28.10', '//bbmod.com' + download(2))]
    document = '<h3>v9.9.9</h3><a href="' + download(3) + '">outside</a>' + history(entries)
    assert public_release_links(document, SITE_ORIGIN) == [
        ('0.28.12', SITE_ORIGIN + download()),
        ('0.28.11', SITE_ORIGIN + download(1)),
        ('0.28.10', SITE_ORIGIN + download(2))]


def test_missing_history_and_control_character_versions_are_ignored():
    assert public_release_links('<h3>v1.0</h3>', SITE_ORIGIN) == []
    assert public_release_links(history([('1.0&#10;evil', download())]), SITE_ORIGIN) == []


@pytest.mark.parametrize('digest,known', [('b' * 64, {}), ('a' * 64, {'a' * 64: '0.28.12'})])
def test_known_release_never_requests_page_or_download_headers(monkeypatch, digest, known):
    request, opener = Mock(), Mock()
    monkeypatch.setattr('core.catalog_versions._request', request)
    monkeypatch.setattr('core.catalog_versions.build_opener', opener)
    versions = identify_release_versions(SITE_ORIGIN, item(), digest, known)
    assert versions['b' * 64] == '0.28.14'
    assert digest in versions
    request.assert_not_called()
    opener.assert_not_called()


def test_history_identification_uses_head_checksum_without_reading_zip(monkeypatch):
    request = Mock(return_value=io.BytesIO(history([
        ('0.28.14', download()), ('0.28.12', download(1)), ('0.28.11', download(2))]).encode()))
    open_head = Mock(return_value=HeadResponse('a' * 64))
    monkeypatch.setattr('core.catalog_versions._request', request)
    monkeypatch.setattr('core.catalog_versions.build_opener', lambda *_: SimpleNamespace(open=open_head))
    versions = identify_release_versions(SITE_ORIGIN, item(), 'a' * 64)
    assert versions == {'b' * 64: '0.28.14', 'a' * 64: '0.28.12'}
    request.assert_called_once_with(SITE_ORIGIN + item()['page_path'])
    assert open_head.call_count == 1
    head = open_head.call_args.args[0]
    assert head.get_method() == 'HEAD' and head.full_url == SITE_ORIGIN + download(1)


@pytest.mark.parametrize('sha,status', [('bad', 200), ('A' * 64, 200), ('a' * 64, 503)])
def test_invalid_checksum_or_unsuccessful_head_is_not_accepted(monkeypatch, sha, status):
    monkeypatch.setattr('core.catalog_versions._request', lambda _: io.BytesIO(history([('0.28.12', download())]).encode()))
    monkeypatch.setattr('core.catalog_versions.build_opener',
                        lambda *_: SimpleNamespace(open=lambda *args, **kwargs: HeadResponse(sha, status)))
    assert identify_release_versions(SITE_ORIGIN, item(), 'a' * 64) == {'b' * 64: '0.28.14'}


def test_history_header_budget_limits_network_requests(monkeypatch):
    document = history([(f'0.28.{12 - number}', download(number)) for number in range(4)])
    monkeypatch.setattr('core.catalog_versions._request', lambda _: io.BytesIO(document.encode()))
    open_head = Mock(return_value=HeadResponse('c' * 64))
    monkeypatch.setattr('core.catalog_versions.build_opener', lambda *_: SimpleNamespace(open=open_head))
    identify_release_versions(SITE_ORIGIN, item(), 'a' * 64, max_headers=2)
    assert open_head.call_count == 2
    assert all(call.args[0].get_method() == 'HEAD' for call in open_head.call_args_list)


def test_oversized_history_page_is_rejected_before_heads(monkeypatch):
    monkeypatch.setattr('core.catalog_versions._request', lambda _: io.BytesIO(b'x' * (1024 * 1024 + 1)))
    opener = Mock()
    monkeypatch.setattr('core.catalog_versions.build_opener', opener)
    with pytest.raises(ValueError, match='超过限制'):
        identify_release_versions(SITE_ORIGIN, item(), 'a' * 64)
    opener.assert_not_called()


def test_history_read_deadline_is_enforced_without_sleep(monkeypatch):
    monkeypatch.setattr('core.catalog_versions._request', lambda _: io.BytesIO(b'<html>history</html>'))
    monkeypatch.setattr('core.catalog_versions.time.monotonic', Mock(side_effect=[0, 13]))
    with pytest.raises(ValueError, match='超过限制'):
        identify_release_versions(SITE_ORIGIN, item(), 'a' * 64, max_seconds=12)
