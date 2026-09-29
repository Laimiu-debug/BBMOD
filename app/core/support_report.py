"""A small, user-reviewable support report; no automatic transmission."""
import os
from datetime import datetime, timezone
from pathlib import Path
import platform
import re
from .version import VERSION

MAX_REPORT_CHARS = 60_000


def _bounded(text, limit):
    marker = '\n[内容过长，后续已省略]'
    return text if len(text) <= limit else text[:limit - len(marker)] + marker


def _log_excerpt(ctx):
    from .gamelog import iter_rows
    folder = ctx.log_dir()
    path = folder / 'log.html' if folder else None
    if not path or not path.is_file():
        return '未找到游戏 log.html。'
    try:
        stamp = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec='seconds')
        with path.open('rb') as stream:
            stream.seek(0, 2)
            start = max(0, stream.tell() - 2 * 1024 * 1024)
            stream.seek(start)
            raw = stream.read(2 * 1024 * 1024)
        rows = iter_rows(raw.decode('utf-8-sig', errors='replace'))
        # Keep recent failures and their surrounding call-stack/context lines,
        # even when ordinary debug output follows them.
        errors = [i for i, row in enumerate(rows) if row.level in ('error', 'critical')][-12:]
        indexes = set(range(max(0, len(rows) - 40), len(rows)))
        for index in errors:
            indexes.update(range(max(0, index - 3), min(len(rows), index + 9)))
        lines = [f'日志修改时间（UTC）：{stamp}']
        if start:
            lines.append('仅读取日志末尾 2 MB。')
        lines.extend(_bounded(str(rows[i]), 2000) for i in sorted(indexes))
        if not rows:
            lines.append('未解析到日志记录。')
        return _bounded('\n'.join(lines), 24_000)
    except OSError as exc:
        return '读取日志失败：' + str(exc)


def redact(text, paths=()):
    for path in sorted({str(p) for p in paths if p}, key=len, reverse=True):
        text = re.sub(re.escape(path), '[本地路径]', text, flags=re.IGNORECASE)
        text = re.sub(re.escape(path.replace('\\', '/')), '[本地路径]', text, flags=re.IGNORECASE)
    text = re.sub(r'[A-Za-z]:[\\/][^\r\n<>"|]*', '[本地路径]', text)
    text = re.sub(r'\\\\[^\s<>"|]+', '[网络路径]', text)
    text = re.sub(r'/(?:home|Users|tmp)/[^\s<>"|]+', '[本地路径]', text)
    text = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[邮箱]', text)
    text = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[IP]', text)
    return text


def build_report(ctx, report):
    game = ctx.game
    lines = [f'BBMOD 诊断报告 · {VERSION}', f'游戏版本：{game.version if game else "未选择游戏"}']
    lines.extend([f'生成时间（UTC）：{datetime.now(timezone.utc).isoformat(timespec="seconds")}',
                  f'操作系统：{platform.system()} {platform.release()}', '\n诊断结果：'])
    if report is None:
        lines.append('诊断尚未完成。')
    else:
        lines.append(f'错误 {report.error_count} · 警告 {report.warning_count} · 共 {len(report.issues)} 条')
        for issue in report.sorted()[:50]:
            lines.append(f'[{issue.severity}] {issue.source}: {issue.title}\n{issue.detail[:1500]}\n建议：{issue.fix or "查看说明"}')
        if len(report.issues) > 50:
            lines.append('其余诊断项已省略。')
        if not report.issues:
            lines.append('本次静态检查未发现问题；不等同于全部 MOD 实机兼容。')
    diagnosis = _bounded('\n'.join(lines[2:]), 16_000)
    mods = ctx.mm.scan() if ctx.mm else []
    mod_lines = [f'MOD：{len(mods)} 个（按文件名加载）']
    for mod in mods[:200]:
        info = mod.info
        identity = f'{info.package_name} {info.package_version}（{info.package_id}）' if info.package_id else ''
        registrations = ', '.join(f'{r.mod_id} v{r.version}' for r in info.registrations)
        mod_lines.append(f'{"启用" if mod.enabled else "禁用"} · {mod.path.name} · {identity} · {registrations or "未识别注册信息"}')
    if len(mods) > 200:
        mod_lines.append('其余 MOD 已省略。')
    body = diagnosis + '\n\n近期游戏日志：\n' + _log_excerpt(ctx) + '\n\n' + _bounded('\n'.join(mod_lines), 16_000)
    paths = [Path.home(), os.environ.get('APPDATA'), game.root if game else None, ctx.log_dir()]
    # A four-part game version resembles an IPv4 address; keep its trusted label.
    return _bounded('\n'.join(lines[:2]) + '\n' + redact(body, paths), MAX_REPORT_CHARS)
