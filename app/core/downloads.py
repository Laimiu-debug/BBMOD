"""Bounded reconnects and verified range resumption for large hosted packages."""
import hashlib
import re
import time
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

IDLE_TIMEOUT = 20
MAX_RETRIES = 4


def fallback_url(url):
    """Only official public MOD routes may fail over to our existing HTTPS origin."""
    parts = urlsplit(url)
    identity = r'[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}'
    path = rf'(?:/files/{identity}/download/|/api/v1/profiles/{identity}/files/[a-f0-9]{{64}}/)'
    if (parts.scheme == 'https' and parts.netloc == 'bbmod.site' and not parts.query
            and not parts.fragment and re.fullmatch(path, parts.path)):
        return 'https://gongpro.cn/bbmod-origin' + parts.path
    return url


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('下载地址发生重定向，请刷新网站目录后重试。')


def _request(url, offset):
    headers = {'User-Agent': 'BBMOD-Download/1', 'Accept-Encoding': 'identity'}
    if offset:
        headers['Range'] = f'bytes={offset}-'
    return build_opener(NoRedirect()).open(Request(url, headers=headers), timeout=IDLE_TIMEOUT)


def _check_cancel(cancelled):
    if cancelled():
        raise ValueError('下载已取消。')


def _pause(seconds, cancelled):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        _check_cancel(cancelled)
        time.sleep(min(0.1, max(0, until - time.monotonic())))


class InterruptedDownload(Exception):
    pass


def download_verified(url, destination, *, size, sha256, cancelled=lambda: False, progress=lambda _: None):
    """Resume only validated ranges; a healthy slow transfer has no total-time cutoff.

    Reconnects stay within this operation. Nothing is installed until size and hash
    match, and unsuccessful temporary files are removed by the caller.
    """
    count, digest, reported = 0, hashlib.sha256(), 0.0
    with destination.open('wb') as output:
        for attempt in range(MAX_RETRIES + 1):
            _check_cancel(cancelled)
            try:
                try:
                    response = _request(fallback_url(url) if attempt else url, count)
                except HTTPError as error:
                    error.close()
                    if error.code not in {408, 429, 500, 502, 503, 504}:
                        raise ValueError(f'网站拒绝下载（HTTP {error.code}），请刷新目录后重试。') from error
                    raise InterruptedDownload from error
                except (OSError, URLError, HTTPException) as error:
                    raise InterruptedDownload from error
                with response:
                    _check_cancel(cancelled)
                    if response.headers.get('Content-Encoding', 'identity').lower() != 'identity':
                        raise ValueError('下载响应编码无效。')
                    status = response.status
                    if status == 206:
                        match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', response.headers.get('Content-Range', ''))
                        if not match or tuple(map(int, match.groups())) != (count, size - 1, size):
                            raise ValueError('网站返回了错误的续传位置，已停止下载。')
                    elif status == 200:
                        # Older/custom servers may ignore Range. Never append a full body.
                        output.seek(0)
                        output.truncate()
                        count, digest = 0, hashlib.sha256()
                    else:
                        raise ValueError(f'下载响应无效（HTTP {status}）。')
                    length = response.headers.get('Content-Length')
                    if length is not None and (not length.isdigit() or int(length) != size - count):
                        raise ValueError('下载大小与目录不一致。')
                    while True:
                        _check_cancel(cancelled)
                        try:
                            block = response.read1(128 * 1024)
                        except (OSError, HTTPException) as error:
                            raise InterruptedDownload from error
                        if not block:
                            break
                        _check_cancel(cancelled)
                        if count + len(block) > size:
                            raise ValueError('下载大小与目录不一致。')
                        output.write(block)
                        digest.update(block)
                        count += len(block)
                        now = time.monotonic()
                        if now - reported >= 0.2 or count == size:
                            progress(f'正在下载：{count / 1024**2:.1f} / {size / 1024**2:.1f} MB（{count * 100 // size}%）')
                            reported = now
                    if count != size:
                        raise InterruptedDownload
                    if digest.hexdigest() != sha256:
                        raise ValueError('下载校验失败，文件未安装。请刷新目录后重试。')
                    progress('下载完成，正在校验压缩包…')
                    return
            except InterruptedDownload as error:
                _check_cancel(cancelled)
                if attempt == MAX_RETRIES:
                    raise ValueError('下载连接多次中断或超时，请检查网络后重试；本机 MOD 未更改。') from error
                route = '切换备用直连，' if attempt == 0 and fallback_url(url) != url else ''
                progress(f'连接中断，{route}正在重试 / 续传（{attempt + 1}/{MAX_RETRIES}，已下载 {count / 1024**2:.1f} MB）…')
                _pause(min(2 ** attempt, 4), cancelled)
