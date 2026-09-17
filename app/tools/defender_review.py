"""Prepare local review evidence without extracting or executing native helpers.

Only reads Defender status/history, source files and an existing PyInstaller
archive. Does not submit files, restore quarantine, change protection, build an
executable, or launch the game. Run after the user authorizes local diagnosis.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from PyInstaller.archive.readers import CArchiveReader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.native_font import component_paths
from core.version import VERSION

SUBMISSION_URL = 'https://www.microsoft.com/en-us/wdsi/filesubmission'
COMPONENTS = ('bbmod_launch.exe', 'bbmod_han.dll')

# Static command: no paths or user-controlled text are interpolated into shell
# code. Only include records mentioning our component filenames.
DEFENDER_QUERY = r'''
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$bbmodDetections = @(Get-MpThreatDetection | Where-Object {
    ($_.Resources -join "`n") -match '(?i)(?:\\|/)(?:bbmod_launch\.exe|bbmod_han\.dll)(?:$|[;\s])'
})
$bbmodThreatIds = @($bbmodDetections | Select-Object -ExpandProperty ThreatID -Unique)
$bbmodThreats = @(Get-MpThreat | Where-Object { $_.ThreatID -in $bbmodThreatIds } |
    Select-Object ThreatID, ThreatName, IsActive)
$bbmodStatus = Get-MpComputerStatus | Select-Object AMProductVersion, AntivirusSignatureVersion,
    AntivirusSignatureLastUpdated, AntivirusEnabled, RealTimeProtectionEnabled
[ordered]@{
    status = $bbmodStatus
    threats = $bbmodThreats
    detections = @($bbmodDetections | Select-Object ThreatID, DetectionID, InitialDetectionTime,
        LastThreatStatusChangeTime, ActionSuccess, Resources)
} | ConvertTo-Json -Depth 6 -Compress
'''


def digest_file(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inspect_archive(executable: Path) -> dict:
    archive = CArchiveReader(str(executable))
    names = {key.replace('\\', '/'): key for key in archive.toc}
    components = {}
    for filename in COMPONENTS:
        entry = 'native/bin/' + filename
        if entry not in names:
            components[filename] = {'present': False}
            continue
        # Inspect bytes in memory only. Never restore a quarantined helper to disk.
        raw = archive.extract(names[entry])
        components[filename] = {'present': True, 'size': len(raw),
                                'sha256': hashlib.sha256(raw).hexdigest()}
    return {'path': str(executable), 'size': executable.stat().st_size,
            'sha256': digest_file(executable), 'components': components}


def defender_evidence() -> dict:
    if sys.platform != 'win32':
        return {'available': False, 'reason': 'Windows Defender history is only available on Windows.'}
    shell = Path(os.environ.get('SystemRoot', r'C:\Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    try:
        result = subprocess.run([str(shell), '-NoProfile', '-NonInteractive', '-Command', DEFENDER_QUERY],
            capture_output=True, timeout=30, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            return {'available': False, 'reason': result.stderr.decode('utf-8', errors='replace').strip()}
        return {'available': True, **json.loads(result.stdout.decode('utf-8-sig'))}
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        return {'available': False, 'reason': str(error)}


def submission_text(archive: dict) -> str:
    return f'''Please review a detection affecting BBMOD, an open-source local mod manager and independent Chinese localization for Battle Brothers on Windows.
Project: https://github.com/Laimiu-debug/BBMOD
Observed detection: Behavior:Win32/DefenseEvasion.A!ml
Detected component: bbmod_launch.exe
Existing distribution EXE SHA256: {archive['sha256']}
Contained launcher SHA256: {archive['components'].get('bbmod_launch.exe', {}).get('sha256', 'not present')}

The launcher creates the user-selected BattleBrothers.exe process suspended, writes the path of the bundled bbmod_han.dll using VirtualAllocEx/WriteProcessMemory, starts LoadLibraryW via CreateRemoteThread, then resumes startup. The DLL uses MinHook for Chinese glyph rendering and a process-local language marker. This behavior is present in our source; it is not being concealed. Canonical English place names and save data are intended to remain unchanged. Failed initialization can terminate this newly created game process.

Defender quarantined the launcher during local use/build attempts on 2026-09-17. Ordinary UI translations use game scripts; map labels require the native adapter. Release work is paused. We have not restored quarantine or changed Defender protection. Please determine whether this is an expected detection or false positive and advise on remediation. Source review and offline tests are not being presented as antivirus clearance. The supplied distribution contains the helper; it has not been extracted back to disk for this report.
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True, help='Existing distribution to inspect; it will not run.')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    executable = args.exe.resolve(strict=True)
    app_dir = Path(__file__).resolve().parents[1]
    report = {'created_utc': datetime.now(timezone.utc).isoformat(), 'source_version': VERSION,
              'submission_url': SUBMISSION_URL, 'submission_status': 'not_submitted',
              'archive': inspect_archive(executable), 'defender': defender_evidence(),
              'current_components': {name: {'path': str(path), 'present': path.is_file(),
                                           'sha256': digest_file(path) if path.is_file() else None}
                                     for name, path in component_paths().items()},
              'source_sha256': {name: digest_file(app_dir/name) for name in (
                  'native/launch_game.cpp', 'native/han_font.cpp', 'native/place_session.h',
                  'native/place_display.h', 'core/native_font.py')},
              'native_helper_extracted': False, 'game_started': False,
              'protection_changed': False, 'antivirus_clearance': 'pending'}
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output/'evidence.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (output/'submission-en.txt').write_text(submission_text(report['archive']), encoding='utf-8')
    (output/'README.md').write_text(
        '# BBMOD 中文地名组件复核资料\n\n'
        '状态：**本地资料已准备，尚未向微软提交，也没有获得误报确认。**\n\n'
        f'- [微软官方提交入口]({SUBMISSION_URL})，选择 Software developer。\n'
        '- `submission-en.txt`：可填写在“Additional information”的英文说明。\n'
        '- `evidence.json`：只读收集的组件清单、源码及既有 EXE 校验值、相关 Defender 检测记录。\n'
        '- 如提交页面需要文件，可选择下面的既有发行 EXE；其中包含旧启动组件，无需从隔离区恢复。\n\n'
        f'既有发行文件：`{executable}`\n\n'
        f'SHA256：`{report["archive"]["sha256"]}`\n\n'
        '提交前核对页面要求、账号和资料内容。证据 JSON 包含本机路径；未自动上传任何文件。'
        '“ActionSuccess”表示隔离操作成功，“IsActive=false”表示该条威胁已处理，都不代表文件通过安全审查。'
        '此资料生成过程未启动游戏、未解压可执行组件、未改变防护设置。\n', encoding='utf-8')
    print(json.dumps({'output': str(output), 'defender_history_available': report['defender']['available'],
                      'existing_exe_sha256': report['archive']['sha256'], 'submission_status': 'not_submitted'}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
