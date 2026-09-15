"""M2 验收脚本：对本机真实环境跑完整诊断，检查两个坏 mod 与基座告警是否被报出。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import game, gamelog
from core.diagnostics import diagnose
from core.modinfo import analyze_zip

LABEL = {"error": "✗错误", "warning": "⚠警告", "info": "ℹ提示"}


def main() -> None:
    g = game.locate_game()
    assert g, "未找到游戏"
    installed = [analyze_zip(z) for z in sorted(g.data_dir.glob("*.zip"))]
    print(f"游戏: {g.root}  版本: {g.version}  已装 zip: {len(installed)}\n")

    rows = gamelog.load_log(game.find_log_write_path() / "log.html") if game.find_log_write_path() else []
    print(f"上次会话日志行数: {len(rows)}\n")

    report = diagnose(g, installed, rows)
    print(f"共 {len(report.issues)} 条（错误 {report.error_count} / 警告 {report.warning_count}）\n")
    cur = None
    for issue in report.sorted():
        if issue.source != cur:
            cur = issue.source
            print(f"\n--- {cur} ---")
        print(f"  [{LABEL[issue.severity]}] {issue.title}")
        if issue.detail:
            print(f"        {issue.detail[:150]}")
        if issue.fix:
            print(f"        → 修复: {issue.fix}")


if __name__ == "__main__":
    main()
