"""Migration keeps user data and custom sources while using the new official site."""
import io
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from core import settings as settings_module
from core.online_catalog import site_origin
from core.seedgen.library import SeedLibrary
from core.seedgen import sharing
from core.site_config import SITE_ORIGIN, canonical_site_origin, canonical_site_url, same_site
from test_seed_history import record


@pytest.mark.parametrize('origin,expected', [
    ('https://bbmod.site', SITE_ORIGIN),
    (' https://BBMOD.SITE/ ', SITE_ORIGIN),
    ('https://bbmod.vercel.app', SITE_ORIGIN),
    ('https://custom.example', 'https://custom.example'),
    ('http://127.0.0.1:8765', 'http://127.0.0.1:8765'),
    ('https://bbmod.site.evil', 'https://bbmod.site.evil'),
])
def test_settings_migrate_only_known_official_source(tmp_path, monkeypatch, origin, expected):
    monkeypatch.setattr(settings_module, '_settings_dir', lambda: tmp_path)
    payload = {'online_catalog_url': origin, 'game_path': 'unchanged', 'seed_traits': {'required': ['trait.huge']}}
    path = tmp_path / 'settings.json'
    path.write_text(json.dumps(payload), encoding='utf-8')
    settings = settings_module.Settings()
    assert settings.get('online_catalog_url') == expected
    assert settings.get('game_path') == 'unchanged'
    assert settings.get('seed_traits') == payload['seed_traits']
    settings.set('font_size', 13)
    assert json.loads(path.read_text(encoding='utf-8')) == {**payload, 'online_catalog_url': expected, 'font_size': 13}


@pytest.mark.parametrize('origin', [
    'https://bbmod.site@evil.example', 'https://user@bbmod.site',
    'https://bbmod.site:8443', 'http://bbmod.site',
    'https://bbmod.site/api/private/', 'https://bbmod.site/?token=private',
])
def test_similar_and_private_sources_do_not_gain_official_identity(origin):
    assert canonical_site_origin(origin) == origin
    assert not same_site(origin, SITE_ORIGIN)


def test_old_seed_history_link_moves_without_resharing_or_clearing_cooldown(tmp_path):
    library = SeedLibrary(tmp_path / 'seeds.sqlite3')
    seed = record()
    path = '/seeds/01234567-89ab-cdef-0123-456789abcdef/'
    library.mark_shared(seed, 'https://bbmod.site' + path)
    library.defer_sharing(3600, 'server cooldown')
    reopened = SeedLibrary(library.path)
    assert reopened.shared_url(seed) == SITE_ORIGIN + path
    assert reopened.all() == [seed]
    assert reopened.share_cooldown()[0] > 3500
    assert canonical_site_url('https://custom.example' + path) == 'https://custom.example' + path


def test_seed_publish_with_saved_official_origin_requests_only_new_site():
    requests = []
    path = '/seeds/01234567-89ab-cdef-0123-456789abcdef/'
    def opened(request, **kwargs):
        requests.append(request.full_url)
        return io.BytesIO(json.dumps({'page_path': path, 'created': False}).encode())
    with patch.object(sharing, 'build_opener', return_value=SimpleNamespace(open=opened)):
        receipt = sharing.publish_seed(record(), origin='https://bbmod.site')
        default = sharing.publish_seed(record())
    assert requests == [SITE_ORIGIN + '/api/v1/seeds/'] * 2
    assert receipt.url == default.url == SITE_ORIGIN + path
    assert site_origin('https://bbmod.site') == SITE_ORIGIN
