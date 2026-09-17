"""Reproduce redirected Documents, converted TXT, and chunked live game output.

All game/process operations are mocked. This suite never starts Battle Brothers.
"""
import html
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from core import game as game_mod
from core.game import GameInfo
from core.gamelog import IncrementalLogReader, iter_rows
from core.seedgen.config_emitter import CampaignConfig
from core.seedgen.log_watcher import import_seed_log
from core.seedgen.orchestrator import SeedGenOrchestrator, StopLimits
from core.seedgen.presentation import format_seed


def html_rows(*lines):
    return "".join('<div class="row info"><div class="entry-container"><div class="time">12:34:56</div>'
        '<div class="tag">SQ</div><div class="text">' + html.escape(line) + '</div></div></div>' for line in lines)


# Faithful to the screenshot's TXT structure: empty lines replace CRLF records.
SCREENSHOT_TXT = """Seed: NPIKXYFANW LoopIdx:548 BroOutputType:0 Origin:scenario.cultists
TeamInfo: 0.601027 Melee:1 Range:0 Guard:0 Throw:0 Leader:1 Duel:0 Polearm:0 Initiative:0 Useless:2
CharInfo: 0 Leader:0.837847 Hitpoints:50(85)0 Bravery:55(103)3 Stamina:100(137)1 MeleeSkill:53(77)0 RangedSkill:37(64)0
Trait: trait.cultist_fanatic trait.iron_jaw
CharInfo: 1 Useless:0.371996 Hitpoints:50(85)1 Bravery:60(91)0 Stamina:101(131)0 MeleeSkill:47(70)0 RangedSkill:39(67)0
Trait: trait.cultist_fanatic trait.cocky
CharInfo: 2 Useless:0.429922 Hitpoints:55(86)0 Bravery:53(82)0 Stamina:103(141)1 MeleeSkill:51(73)1 RangedSkill:32(60)0
Trait: trait.cultist_fanatic trait.huge
CharInfo: 3 Melee:0.764344 Hitpoints:57(88)0 Bravery:61(94)0 Stamina:94(131)0 MeleeSkill:57(91)3 RangedSkill:42(73)0
Trait: trait.cultist_fanatic trait.sure_footing trait.fearless

Seed: RAQWVMQRVU LoopIdx:12303 BroOutputType:0 Origin:scenario.cultists
TeamInfo: 0.59699 Melee:1 Range:0 Guard:0 Throw:0 Leader:1 Duel:0 Polearm:0 Initiative:0 Useless:2
CharInfo: 0 Useless:0.498445 Hitpoints:60(100)2 Bravery:55(93)2 Stamina:93(122)0 MeleeSkill:53(70)0 RangedSkill:42(77)3
Trait: trait.cultist_fanatic trait.dexterous

"""


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "utf-16"])
def test_screenshot_txt_import_produces_chinese_records(tmp_path, encoding):
    path = tmp_path / "log.txt"
    path.write_text(SCREENSHOT_TXT, encoding=encoding)
    results = import_seed_log(path)
    assert [r.seed for r in results] == ["NPIKXYFANW", "RAQWVMQRVU"]
    assert all(r.done for r in results)
    detail = format_seed(results[0])
    assert "兄弟4 · 近战：" in detail and "近战命中 57→91（3星）" in detail
    assert "达夫库尔狂信徒" in detail
    assert "Trait:" not in detail and "CharInfo:" not in detail and "TeamInfo:" not in detail
    assert "trait." not in detail and "不是属性值、百分比或胜率" in detail


def test_html_formatting_and_escaped_nested_text_are_preserved():
    document = '''<div id='x' class='info row'>
      <div class='entry-container'> <div class='time'>12:34:56</div>
      <div class='tag'>SQ</div><div class='text'><span>中文 &amp; &lt;原文&gt;</span></div></div></div>'''
    rows = iter_rows(document)
    assert len(rows) == 1 and rows[0].text == "中文 & <原文>"


@pytest.mark.parametrize("suffix", [".html", ".txt"])
def test_live_split_writes_deliver_each_row_once_without_damaged_unicode(tmp_path, suffix):
    path = tmp_path / ("log" + suffix)
    body = html_rows("兄弟：稳健", "CRLF") if suffix == ".html" else "兄弟：稳健\n\n"
    reader = IncrementalLogReader(path)
    received = []
    with path.open("wb") as stream:
        for byte in body.encode():
            stream.write(bytes([byte]))
            stream.flush()
            received += reader.read_new()
    assert [row.text for row in received] == ["兄弟：稳健", "CRLF" if suffix == ".html" else ""]
    assert reader.read_new() == []


def test_bounded_reads_never_skip_or_replay_bytes(tmp_path):
    path = tmp_path / "log.txt"
    path.write_text("a\n", encoding="utf-8")
    reader = IncrementalLogReader(path)
    reader.CHUNK_SIZE = 4
    path.write_text("one\ntwo\nthree\n", encoding="utf-8")
    rows = []
    while reader.offset < path.stat().st_size:
        rows += reader.read_new()
    assert [row.text for row in rows] == ["one", "two", "three"]
    assert reader.offset == path.stat().st_size and reader.read_new() == []


def test_append_between_size_check_and_read_uses_actual_position(tmp_path):
    path = tmp_path / "log.txt"
    path.write_text("one\n", encoding="utf-8")
    reader = IncrementalLogReader(path)
    original_open = Path.open
    class GrowingFile:
        def __enter__(self):
            self.stream = original_open(path, "rb")
            return self
        def __exit__(self, *args):
            self.stream.close()
        def seek(self, *args):
            return self.stream.seek(*args)
        def tell(self):
            return self.stream.tell()
        def read(self, size):
            if size == reader.CHUNK_SIZE:
                with original_open(path, "ab") as writer:
                    writer.write(b"two\n")
            return self.stream.read(size)
    with patch.object(Path, "open", return_value=GrowingFile()):
        assert [row.text for row in reader.read_new()] == ["one", "two"]
    assert reader.read_new() == []


def test_rewritten_log_larger_than_old_offset_is_reread(tmp_path):
    path = tmp_path / "log.html"
    path.write_text(html_rows("OLD"), encoding="utf-8")
    reader = IncrementalLogReader(path)
    assert reader.read_new()[0].text == "OLD"
    generation = reader.generation
    path.write_text(html_rows("NEWER LONGER RECORD"), encoding="utf-8")
    assert reader.read_new()[0].text == "NEWER LONGER RECORD"
    assert reader.generation > generation and reader.read_new() == []


def test_unterminated_txt_tail_is_retained_and_marked_partial(tmp_path):
    path = tmp_path / "log.txt"
    path.write_text(SCREENSHOT_TXT.rstrip(), encoding="utf-8")
    records = import_seed_log(path)
    assert len(records) == 2 and records[0].done and not records[1].done
    assert "trait.dexterous" in records[1].lines[-1]
    assert "记录未完整" in format_seed(records[1])


def test_import_deduplicates_repeated_blocks(tmp_path):
    path = tmp_path / "log.txt"
    path.write_text(SCREENSHOT_TXT * 2, encoding="utf-8")
    assert len(import_seed_log(path)) == 2
    with pytest.raises(FileNotFoundError):
        import_seed_log(tmp_path / "missing.txt")


def test_windows_known_documents_and_reported_write_path_are_both_candidates(tmp_path, monkeypatch):
    redirected = tmp_path / "custom-documents"
    log_folder = redirected / "Battle Brothers"
    log_folder.mkdir(parents=True)
    reported = tmp_path / "保存 & 日志"
    reported.mkdir()
    (log_folder / "log.html").write_text(html_rows(f"Using write path: {reported}"), encoding="utf-8")
    monkeypatch.setattr(game_mod, "documents_path", lambda: redirected)
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "profile")
    for name in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        monkeypatch.delenv(name, raising=False)
    assert log_folder in game_mod.find_log_write_paths()
    assert reported in game_mod.find_log_write_paths()
    assert game_mod.find_log_write_path() == log_folder


@pytest.fixture
def live_session(tmp_path, monkeypatch):
    game = GameInfo(tmp_path / "game", tmp_path / "game/win32/BattleBrothers.exe", "1.5.2.3", tmp_path / "game/data")
    stale, active = tmp_path / "Documents", tmp_path / "redirected-documents"
    stale.mkdir()
    active.mkdir()
    (stale / "log.html").write_text(html_rows("BBMODSeedSession: old", "Seed: OLDSEED000 LoopIdx:999999", "CRLF"))
    monkeypatch.setattr(game_mod, "find_log_write_paths", lambda preferred=None: [stale, active])
    monkeypatch.setattr(game_mod, "launch_game", lambda *args, **kw: True)
    monkeypatch.setattr(game_mod, "is_game_running", lambda: False)
    session = SeedGenOrchestrator(game, tmp_path / "payload")
    session.state.stage = "prepared"
    session.files = SimpleNamespace(restore=lambda: 2, root=tmp_path, preserved=[])
    session.mm = SimpleNamespace(_audit=lambda *args: None)
    session._campaign = CampaignConfig(origin="scenario.cultists")
    assert session.launch()
    return session, active / "log.html"


def test_follows_matching_session_in_second_directory_before_search_ends(live_session):
    session, path = live_session
    assert session.poll() == ([], [])
    assert session.log_path is None and not session.results
    path.write_text(html_rows("BBMODSeedSession: " + session._session_id,
        "BBMODSeedStart: generating scenario.cultists", *SCREENSHOT_TXT.splitlines(), "CRLF"), encoding="utf-8")
    # HTML blank text is not the TXT delimiter: first block is partial here.
    records, _ = session.poll()
    assert len(records) == 2 and session.log_path == path
    assert records[0].combat_difficulty == 1 and records[1].done
    assert session.poll() == ([], []) and len(session.results) == 2


def test_live_replacement_requires_session_marker_again(live_session):
    session, path = live_session
    path.write_text(html_rows("BBMODSeedSession: " + session._session_id,
        "Seed: CURRENT000 LoopIdx:2", "CRLF"), encoding="utf-8")
    assert len(session.poll()[0]) == 1
    path.write_text(html_rows("BBMODSeedSession: foreign-session", "Seed: FOREIGN000 LoopIdx:999999", "CRLF") * 4, encoding="utf-8")
    assert session.poll()[0] == [] and session.log_path is None
    assert len(session.results) == 1


def test_foreign_session_appended_to_same_file_never_leaks_results(live_session):
    session, path = live_session
    path.write_text(html_rows("BBMODSeedSession: " + session._session_id,
        "Seed: CURRENT000 LoopIdx:2", "CRLF", "BBMODSeedSession: foreign",
        "Seed: FOREIGN000 LoopIdx:3", "CRLF"), encoding="utf-8")
    assert [r.seed for r in session.poll()[0]] == ["CURRENT000"]
    assert session.log_path is None
    assert session.poll() == ([], [])


def test_stop_drains_last_complete_record_and_preserves_unfinished_tail(live_session):
    session, path = live_session
    path.write_text(html_rows("BBMODSeedSession: " + session._session_id,
        "Seed: COMPLETE00 LoopIdx:1", "TeamInfo: 0.9", "CRLF",
        "Seed: PARTIAL000 LoopIdx:2", "CharInfo: 0 Melee:0.8 MeleeSkill:60(90)3"), encoding="utf-8")
    assert session.results == []
    assert session.stop_and_restore() == 2
    assert [(r.seed, r.done) for r in session.results] == [("COMPLETE00", True), ("PARTIAL000", False)]
    assert session.state.stage == "restored"


def test_stop_limits_use_received_complete_results_and_elapsed_time(live_session):
    session, path = live_session
    # At this start time, subtracting the deadline rounds just below 60.
    session._started_at = 4.1
    session.limits = StopLimits(hits=2, minutes=10)
    path.write_text(html_rows("BBMODSeedSession: " + session._session_id,
        "LoopIdx: 4000(987) 0.9", "Seed: COMPLETE00 LoopIdx:1", "CRLF",
        "Seed: NEXT000000 LoopIdx:2"), encoding="utf-8")
    session.poll()
    with patch("core.seedgen.orchestrator.time.monotonic", return_value=session._started_at + 599):
        assert session.stop_reason == ""  # 987 is pre-map progress, not real hits.
    with path.open("a", encoding="utf-8") as stream:
        stream.write(html_rows("CRLF"))
    session.poll()
    assert "2 条" in session.stop_reason
    session.limits = StopLimits(minutes=1)
    with patch("core.seedgen.orchestrator.time.monotonic", return_value=session._started_at + 59.999):
        assert session.stop_reason == ""
    with patch("core.seedgen.orchestrator.time.monotonic", return_value=session._started_at + 60):
        assert "1 分钟" in session.stop_reason
    session.limits = StopLimits()
    with patch("core.seedgen.orchestrator.time.monotonic", return_value=session._started_at + 999999):
        assert session.stop_reason == ""
    for value in (-1, 1.5, True, "2"):
        with pytest.raises(ValueError):
            StopLimits(hits=value)


def test_world_and_item_details_have_chinese_labels_and_correct_percentages(tmp_path):
    path = tmp_path / "log.txt"
    path.write_text("""Seed: WORLD00000 LoopIdx:5
SettlementInfo: Settlements:22 Port:7 CityPort:2
BuildInfo: Armorsmith:3 Weaponsmith:4
LairInfo: Old Ruins(Undead) 120 Nordholz 12-upper_left
ItemInfo(TwoHanded): weapon.named_sword(RegularDamage:90%|DirectDamageAdd:40%) Stamina:-12 MinDamage:90 MaxDamage:120 ArmorDamage:1.4 DirectDamage:0.4 ChanceToHitHead:25
CRLF
""", encoding="utf-8")
    text = format_seed(import_seed_log(path)[0])
    assert "聚落 22；港口 7" in text and "铠甲匠 3；武器匠 4" in text
    assert "Old Ruins（亡灵）" in text and "最近聚落 Nordholz" in text and "方位 西北" in text
    assert "破甲效率 140%" in text and "无视护甲比例 40%" in text
    assert "命中头部几率 25%" in text and "ItemInfo" not in text
