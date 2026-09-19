"""One explicit, bounded anonymous upload; no log files or machine data are sent."""
import json
import re
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener

from ..online_catalog import NoRedirect, site_origin
from .protocol import share_payload

PUBLIC_SITE = "https://bbmod.site"


class UploadError(ValueError):
    def __init__(self, message, *, status=None, retry_after=None, retryable=False):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after
        self.retryable = retryable


@dataclass(frozen=True)
class ShareReceipt:
    url: str
    created: bool


def _retry_after(value):
    if not value:
        return None
    try:
        if value.strip().isdigit():
            return int(value.strip())
        return max(0, parsedate_to_datetime(value).timestamp() - time.time())
    except (ValueError, TypeError, OverflowError):
        return None


def publish_seed(result, note="", origin=PUBLIC_SITE):
    origin = site_origin(origin)
    parts = urlsplit(origin)
    if parts.scheme != "https" and parts.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("分享网站必须使用 HTTPS")
    request = Request(origin + "/api/v1/seeds/", method="POST",
        data=json.dumps(share_payload(result, note), ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": "BBMOD-Seeds/1", "X-BBMOD-Seed-Share": "1"})
    try:
        with build_opener(NoRedirect()).open(request, timeout=20) as response:
            raw = response.read(8193)
    except HTTPError as error:
        try:
            data = json.loads(error.read(8192))
            message = data.get("error", "") if isinstance(data, dict) else ""
        except (ValueError, UnicodeError):
            message = ""
        if not isinstance(message, str):
            message = ""
        retry_after = _retry_after(error.headers.get('Retry-After')) if error.headers else None
        # Older servers return a full-hour cooldown. Do not retry around it.
        if error.code == 429 and retry_after is None:
            retry_after = 3600
        raise UploadError(f"{message[:500] or '网站暂时无法接收分享'}（HTTP {error.code}）",
            status=error.code, retry_after=retry_after,
            retryable=error.code in {408, 425, 429, 500, 502, 503, 504}) from error
    except (URLError, OSError) as error:
        raise UploadError(f"连接分享网站失败：{error}", retryable=True) from error
    if len(raw) > 8192:
        raise UploadError("网站返回内容过大，请稍后重试", retryable=True)
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError) as error:
        raise UploadError("网站未返回有效回执，请稍后重试", retryable=True) from error
    path = data.get("page_path") if isinstance(data, dict) else None
    if not isinstance(path, str) or not re.fullmatch(r"/seeds/[0-9a-f-]{36}/", path):
        raise UploadError("网站未返回有效的分享链接，请稍后重试", retryable=True)
    if type(data.get('created')) is not bool:
        raise UploadError("网站回执缺少分享状态，请稍后重试", retryable=True)
    return ShareReceipt(origin + path, data['created'])


def upload_seed(result, note="", origin=PUBLIC_SITE):
    """Compatibility entry point for callers which only need the link."""
    return publish_seed(result, note, origin).url
