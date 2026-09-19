from core.appearance import Appearance, normalize_appearance


def test_invalid_font_settings_keep_a_readable_size():
    for value in (None, [], 'invalid', {'font_size': True}, {'font_size': 'huge'}, {'font_size': float('inf')}):
        assert normalize_appearance(value) == Appearance()
    assert normalize_appearance({'font_size': 999}).font_size == 18
    assert normalize_appearance({'font_size': -4}).font_size == 10


def test_font_names_and_other_preferences_remain_independent():
    data = {'font_family': '  Microsoft YaHei UI ', 'font_size': 14, 'game_path': 'unchanged'}
    assert normalize_appearance(data) == Appearance('Microsoft YaHei UI', 14)
    assert data['game_path'] == 'unchanged'
    assert normalize_appearance({'font_family': 'bad\nfont'}).font_family == ''
    assert normalize_appearance({'font_family': ['unexpected']}).font_family == ''
