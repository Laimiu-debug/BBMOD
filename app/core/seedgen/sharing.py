"""One explicit, bounded anonymous upload; no log files or machine data are sent."""
import json
import re
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener

from ..online_catalog import NoRedirect, site_origin
from .protocol import share_payload

PUBLIC_SITE = "https://bbmod.site"


def upload_seed(result, note="", origin=PUBLIC_SITE):
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
            message = json.loads(error.read(8192)).get("error", "")
        except (ValueError, UnicodeError):
            message = ""
        raise ValueError(message or f"网站暂时无法接收分享（HTTP {error.code}），种子仍保存在本机。") from error
    if len(raw) > 8192:
        raise ValueError("网站返回内容过大")
    data = json.loads(raw)
    path = data.get("page_path") if isinstance(data, dict) else None
    if not isinstance(path, str) or not re.fullmatch(r"/seeds/[0-9a-f-]{36}/", path):
        raise ValueError("网站未返回有效的分享链接，请稍后重试")
    return origin + path
