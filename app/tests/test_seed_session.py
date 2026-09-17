import hashlib
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from core.game import GameInfo
from core.paths import resource_path
from core.seedgen.config_emitter import SeedGenConfig
from core.seedgen.orchestrator import SeedGenOrchestrator
from core.seedgen.session import FileSession


def signature(directory):
    return {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in directory.rglob("*") if p.is_file()}


@pytest.fixture
def game(tmp_path):
    root = tmp_path / "game"
    data = root / "data"
    (data / "seed_generator").mkdir(parents=True)
    (data / "data_001.dat").write_bytes(b"OFFICIAL ARCHIVE MUST NOT CHANGE")
    (data / "seed_generator/config_common.nut").write_bytes(b"USER ORIGINAL SETTINGS")
    with zipfile.ZipFile(data / "user_mod.zip", "w") as archive:
        archive.writestr("scripts/user.nut", "user mod")
    with patch("core.seedgen.orchestrator.game_mod.is_game_running", return_value=False), patch(
            "core.seedgen.orchestrator.game_mod.check_base_archive", return_value=None):
        yield GameInfo(root, root / "win32/BattleBrothers.exe", "1.5.2.3", data)


def orchestrator(game):
    return SeedGenOrchestrator(game, resource_path("seedgen/payload"))


def test_roundtrip_restores_original_configs_and_mods(game):
    before = signature(game.data_dir)
    session = orchestrator(game)
    session.prepare(SeedGenConfig())
    assert (game.root / "bbmod_seedgen_session/session.json").is_file()
    assert not (game.data_dir / "user_mod.zip").exists()
    assert session.stop_and_restore() == 1
    assert signature(game.data_dir) == before
    assert not session.files.active


def test_restarted_session_has_no_residual_injected_files(game):
    before = signature(game.data_dir)
    interrupted = orchestrator(game)
    interrupted.prepare(SeedGenConfig())
    restarted = orchestrator(game)
    warnings = restarted.prepare(SeedGenConfig())
    assert any("未结束会话" in warning for warning in warnings)
    restarted.stop_and_restore()
    assert signature(game.data_dir) == before


def test_partial_injection_error_restores_every_original(game):
    before = signature(game.data_dir)
    original_write = Path.write_bytes
    def fail_one(path, data):
        if path == game.data_dir / "scripts/!mods_preload/mod_seed_generator.nut":
            original_write(path, b"partial write")
            raise OSError("simulated disk failure")
        return original_write(path, data)
    with patch.object(Path, "write_bytes", fail_one):
        with pytest.raises(OSError, match="disk failure"):
            orchestrator(game).prepare(SeedGenConfig())
    assert signature(game.data_dir) == before


def test_concurrent_user_edit_is_preserved_before_restore(game):
    before = signature(game.data_dir)
    session = orchestrator(game)
    session.prepare(SeedGenConfig())
    (game.data_dir / "seed_generator/config_common.nut").write_bytes(b"edited during session")
    session.stop_and_restore()
    assert signature(game.data_dir) == before
    assert session.files.preserved[0].read_bytes() == b"edited during session"


def test_tampered_backup_stops_restore_and_keeps_journal(game):
    session = orchestrator(game)
    session.prepare(SeedGenConfig())
    (session.files.root / "originals/user_mod.zip").write_bytes(b"broken backup")
    with pytest.raises(RuntimeError, match="校验失败"):
        session.stop_and_restore()
    assert session.files.active


def test_file_session_rejects_paths_outside_game_and_official_archives(game):
    session = FileSession(game.root)
    for name in ("../escape.zip", "data_001.dat", "C:/escape", "/absolute"):
        with pytest.raises(ValueError):
            session.begin({name: b"should never be written"})
