from types import SimpleNamespace
from pathlib import Path
import pytest
from PySide6.QtCore import QPoint, QRect, QSize
from PySide6.QtWidgets import QApplication
from ui.global_hotkey import GlobalHotkey, parse_shortcut
from ui.inspector_page import tooltip_position, tooltip_regions
from ui.game_foreground import GameForeground, map_tooltip_bounds


@pytest.mark.parametrize('value,vk', [('Ctrl+Shift+Q', 81), ('Alt+5', 53), ('F8', 0x77), ('Ctrl+Space', 0x20), ('Ctrl+Left', 0x25)])
def test_custom_hotkeys(value, vk):
    assert parse_shortcut(value)[2] == vk


@pytest.mark.parametrize('value', ['', 'Ctrl+K, Ctrl+P', 'A', 'Shift+A', 'F12', 'Meta+A', 'Ctrl+Num+1'])
def test_reserved_or_unsafe_hotkeys(value):
    with pytest.raises(ValueError): parse_shortcut(value)


def test_conflict_preserves_previous_binding():
    app = QApplication.instance() or QApplication([])
    key = GlobalHotkey()
    calls = []
    key.api = SimpleNamespace(RegisterHotKey=lambda *args: args[-1] != ord('Q'),
                              UnregisterHotKey=lambda *args: calls.append(args))
    try:
        key.set_shortcut('Ctrl+Alt+D'); first = key.identifier
        with pytest.raises(ValueError): key.set_shortcut('Ctrl+Alt+Q')
        assert key.current == 'Ctrl+Alt+D' and key.registered and key.identifier == first and not calls
        key.set_shortcut('F8')
        assert key.current == 'F8' and key.identifier != first and len(calls) == 1
    finally: key.shutdown()


@pytest.mark.parametrize('point', [QPoint(10, 10), QPoint(1910, 1000), QPoint(-1900, 10), QPoint(-10, 1000)])
def test_follow_cursor_screen_edges_and_negative_monitors(point):
    bounds = QRect(0 if point.x() >= 0 else -1920, 0, 1920, 1040)
    size = QSize(420, 620)
    rect = QRect(tooltip_position(point, size, bounds), size)
    assert bounds.contains(rect) and not rect.contains(point)


def test_foreground_does_not_match_unrelated_apps():
    foreground = GameForeground()
    assert not foreground(None)
    assert not foreground(SimpleNamespace(exe=Path('Z:/not-a-game.exe')))


@pytest.mark.parametrize('blocked', [QRect(0,0,400,500), QRect(600,100,400,700), QRect(1300,200,600,700), QRect(-30,-40,1500,1700)])
def test_available_regions_never_cover_native_tooltip(blocked):
    bounds = QRect(0,0,1920,1080)
    for region in tooltip_regions(bounds, blocked):
        assert bounds.contains(region) and not region.intersects(blocked.adjusted(-9,-9,9,9))
    assert not tooltip_regions(bounds, bounds)


@pytest.mark.parametrize('scale', [1, 1.25, 1.5, 2])
def test_native_bounds_map_css_pixels_window_offset_and_dpi(scale):
    origin = SimpleNamespace(x=-1920, y=80)
    cursor = SimpleNamespace(x=-1620, y=380)
    logical = QPoint(-1280, 300)
    result = map_tooltip_bounds([100,100,200,400,1280,720], origin, (2560,1440), cursor, logical, scale)
    expected = QRect(round(-1280-100/scale), round(300-100/scale), round(400/scale), round(800/scale))
    assert abs(result.left()-expected.left()) <= 1 and abs(result.top()-expected.top()) <= 1
    assert abs(result.width()-expected.width()) <= 1 and abs(result.height()-expected.height()) <= 1
