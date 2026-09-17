"""Render all four real Qt pages at desktop and compact sizes without game writes."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow, apply_dark_palette
from ui.workers import Worker
from core.seedgen.log_watcher import SeedResult


def main() -> None:
    output = Path(__file__).resolve().parents[1] / "build/review"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bbmod-ui-check-") as temporary:
        assert Path(temporary).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
        os.environ["APPDATA"] = temporary
        app = QApplication([])
        apply_dark_palette(app)
        window = MainWindow()
        window.show()
        window.select_page(1)
        started = time.monotonic()
        report = []

        def capture() -> None:
            if any(worker.isRunning() for worker in window.findChildren(Worker)):
                if time.monotonic() - started > 45:
                    raise TimeoutError("界面加载超时")
                QTimer.singleShot(200, capture)
                return
            for width, height in ((1360, 880), (1080, 720)):
                window.resize(width, height)
                for index, name in enumerate(("camp", "armory", "workshop", "expedition")):
                    window.select_page(index)
                    app.processEvents()
                    assert (window.width(), window.height()) == (width, height)
                    if name == "expedition":
                        hint = window.seedgen.attr_hint
                        assert hint.height() >= hint.heightForWidth(hint.width()), "筛选条件说明被截断"
                    filename = f"{name}-{width}.png"
                    assert window.grab().save(str(output / filename))
                    report.append({"page": name, "requested": [width, height],
                        "actual": [window.width(), window.height()], "image": filename})
            # Explicit demo records are only injected in this temporary QA process.
            # They are never shipped as discovered game seeds or saved to the user's profile.
            page = window.seedgen
            demo = SeedResult("DEMOSEED01", 1200, origin="scenario.militia", done=True, lines=[
                "TeamInfo: 0.83 Melee:3",
                "CharInfo: 0 Melee:0.9 MeleeSkill:60(95)3 MeleeDefense:5(30)1",
                "CharInfo: 1 Melee:0.8 MeleeSkill:60(90)2 MeleeDefense:8(38)2",
                "CharInfo: 2 Melee:0.8 MeleeSkill:60(90)2 MeleeDefense:2(27)1",
                "SettlementInfo: Port:7 CityPort:2 Settlements:22",
                "NamedInfo: Armor:2 Helmet:3 Sum:12(1)",
            ])
            page.results = [demo]
            page.bro_count.setValue(3)
            page._append_result(demo)
            page.table.selectRow(0)
            page.click_copy.setChecked(True)
            page.progress_label.setText("演示数据 · 仅作界面验证，非已验证的游戏种子")
            page.note_edit.setText("路线备注示例：抵达北港后向东寻找营地")
            page._note_changed(page.note_edit.text())
            window.select_page(3)
            for width, height in ((1360, 880), (1080, 720)):
                window.resize(width, height)
                app.processEvents()
                assert (window.width(), window.height()) == (width, height)
                filename = f"expedition-demo-{width}.png"
                assert window.grab().save(str(output / filename))
                report.append({"page": "expedition", "demo": True, "image": filename,
                    "requested": [width, height], "actual": [window.width(), window.height()]})
            page.filter_tabs.setCurrentIndex(1)
            app.processEvents()
            assert window.grab().save(str(output / "expedition-map-1080.png"))
            page.filter_tabs.setCurrentIndex(0)
            page.rule_mode.setCurrentIndex(page.rule_mode.findData("score"))
            app.processEvents()
            assert window.grab().save(str(output / "expedition-score-1080.png"))
            (output / "ui-check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False))
            app.quit()

        QTimer.singleShot(200, capture)
        app.exec()


if __name__ == "__main__":
    main()
