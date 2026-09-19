"""Explicit, cancellable seed sharing; each receipt is saved before advancing."""
from dataclasses import dataclass, field
from threading import Event
import math

from .protocol import seed_key, share_payload
from .sharing import publish_seed, UploadError


@dataclass
class ShareReport:
    total: int
    created: int = 0
    existing: int = 0
    invalid: int = 0
    failed: int = 0
    stopped: bool = False
    paused: bool = False
    links: list = field(default_factory=list)
    issues: list = field(default_factory=list)

    @property
    def completed(self):
        return self.created + self.existing + self.invalid + self.failed

    @property
    def remaining(self):
        return self.total - self.completed


class SeedShareQueue:
    INTERVAL = 2
    RETRY_DELAYS = (5, 15, 45)

    def __init__(self, library, items, *, upload=publish_seed, progress=lambda value: None):
        # Snapshot explicit input. Seeds discovered later are never auto-published.
        self.items = list({seed_key(result): (result, note) for result, note in items}.values())
        self.library, self.upload, self.progress = library, upload, progress
        self.cancelled = Event()
        self.report = ShareReport(len(self.items))

    def cancel(self):
        self.cancelled.set()

    def _status(self, message, **extra):
        self.progress(dict(total=self.report.total, completed=self.report.completed,
            created=self.report.created, existing=self.report.existing,
            invalid=self.report.invalid, failed=self.report.failed, message=message, **extra))

    def _wait(self):
        while not self.cancelled.is_set():
            seconds, reason = self.library.share_cooldown()
            if seconds <= 0:
                return True
            remaining = math.ceil(seconds)
            self._status(f'{reason} · {remaining // 60:02d}:{remaining % 60:02d} 后继续', waiting=True)
            self.cancelled.wait(min(seconds, 1))
        return False

    def run(self):
        for result, note in self.items:
            if self.cancelled.is_set():
                break
            url = self.library.shared_url(result)
            if url:
                self.report.existing += 1
                self.report.links.append((result.seed, url))
                self._status(f'{result.seed} 已分享，沿用原链接')
                continue
            try:
                share_payload(result, note)
            except ValueError as error:
                self.report.invalid += 1
                self.report.issues.append(f'{result.seed}：已跳过，{error}')
                self._status(f'{result.seed} 资料不完整或不符合要求，已跳过')
                continue
            # A disk failure must not turn into an untracked public upload.
            self.library.save(result)
            for attempt in range(len(self.RETRY_DELAYS) + 1):
                if not self._wait() or self.cancelled.is_set():
                    break
                self._status(f'正在上传 {result.seed}' + (f' · 第 {attempt} 次重试' if attempt else ''))
                # Persist pacing before the request, including interrupted requests.
                self.library.defer_sharing(self.INTERVAL)
                try:
                    receipt = self.upload(result, note)
                except UploadError as error:
                    if error.retryable:
                        delay = max(error.retry_after or 0, self.RETRY_DELAYS[min(attempt, len(self.RETRY_DELAYS)-1)])
                        self.library.defer_sharing(delay, str(error))
                        if attempt < len(self.RETRY_DELAYS):
                            continue
                    self.report.failed += 1
                    self.report.issues.append(f'{result.seed}：{error}')
                    # Outages and access errors apply to the whole queue. Avoid
                    # sending hundreds of doomed requests; the next click resumes.
                    self.report.paused = error.retryable or error.status in {401, 403}
                    self._status(f'{result.seed} 分享未完成：{error}')
                    break
                except ValueError as error:
                    self.report.failed += 1
                    self.report.issues.append(f'{result.seed}：{error}')
                    self._status(f'{result.seed} 分享未完成：{error}')
                    break
                else:
                    if receipt.created:
                        self.report.created += 1
                    else:
                        self.report.existing += 1
                    self.report.links.append((result.seed, receipt.url))
                    # Finish saving an in-flight success even after Stop is clicked.
                    try:
                        self.library.mark_shared(result, receipt.url)
                    except Exception as error:
                        self.report.issues.append(f'{result.seed} 已公开，但本地分享状态保存失败：{error}；链接：{receipt.url}')
                        self.report.paused = True
                    self._status(f'{result.seed} ' + ('已分享' if receipt.created else '网站已有，沿用原链接'))
                    break
            if self.report.paused:
                break
        self.report.stopped = self.cancelled.is_set()
        return self.report
