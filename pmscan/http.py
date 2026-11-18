"""Tiny HTTP helper: JSON GET with gzip, a user agent, and retry/backoff. Standard library only."""

from __future__ import annotations

import gzip
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Mapping, Sequence

USER_AGENT = "pmscan/0.1 (+https://github.com)"
RETRY_STATUS = {429, 500, 502, 503, 504}


class HttpError(RuntimeError):
    pass


def _read(url: str, timeout: float, data: bytes | None = None) -> bytes:
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/csv;q=0.9, */*;q=0.5",
            # Polymarket serves large /events pages gzip-only.
            "Accept-Encoding": "gzip",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        if resp.headers.get("Content-Encoding", "").lower() == "gzip":
            body = gzip.decompress(body)
        return body


def get(url: str, params: Mapping[str, Any] | Sequence[tuple[str, Any]] | None = None, *,
        timeout: float = 30.0, retries: int = 6, backoff: float = 0.75, data: bytes | None = None) -> bytes:
    if params:
        pairs = params.items() if isinstance(params, Mapping) else params
        clean = [(k, v) for k, v in pairs if v is not None and v != ""]
        url = f"{url}?{urllib.parse.urlencode(clean)}"
    last: Exception | None = None
    for attempt in range(retries):
        try:
            return _read(url, timeout, data)
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in RETRY_STATUS:
                raise HttpError(f"HTTP {e.code} for {url}") from e
            retry_after = e.headers.get("Retry-After") if e.headers else None
            wait = float(retry_after) if retry_after and retry_after.isdigit() else backoff * (2 ** attempt)
            time.sleep(min(wait, 20))
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = e
            time.sleep(min(backoff * (2 ** attempt), 20))
    raise HttpError(f"Giving up on {url}: {last}")


def get_json(url: str, params: Mapping[str, Any] | None = None, **kw) -> Any:
    return json.loads(get(url, params, **kw))


def post_json(url: str, payload: Any, **kw) -> Any:
    return json.loads(get(url, data=json.dumps(payload).encode(), **kw))
