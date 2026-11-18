from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional

Progress = Callable[[str], None]


@dataclass
class Filters:
    min_prob: float = 0.96
    max_prob: float = 0.999
    max_days: float = 90
    min_volume: float = 1000
    now: datetime = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.now is None:
            self.now = datetime.now(timezone.utc)

    def in_band(self, ask: Optional[float]) -> bool:
        return ask is not None and self.min_prob <= ask <= self.max_prob


def num(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parse_time(v: Any) -> Optional[datetime]:
    if not v:
        return None
    s = str(v).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        try:
            dt = datetime.fromisoformat(s[:10])
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def json_list(v: Any) -> list:
    if isinstance(v, list):
        return v
    if isinstance(v, str) and v.startswith("["):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            return []
    return []


CATEGORIES = ["Politics", "Crypto", "Sports", "Economy", "Weather", "Culture", "Tech", "Other"]

_CATEGORY_WORDS = [
    ("Sports", ("sports", "soccer", "football", "nfl", "nba", "nhl", "mlb", "tennis", "esports", "cricket",
                "golf", "ufc", "mma", "basketball", "baseball", "hockey", "f1", "formula 1", "boxing")),
    ("Crypto", ("crypto", "bitcoin", "ethereum", "solana", "xrp", "dogecoin")),
    ("Weather", ("weather", "climate", "climate and weather", "temperature", "hurricane")),
    ("Economy", ("economy", "economics", "fed", "inflation", "financials", "finance", "commodities",
                 "companies", "business", "stocks", "earnings", "ipo", "rates")),
    ("Politics", ("politics", "elections", "election", "geopolitics", "world", "trump", "congress", "government")),
    ("Tech", ("tech", "science and technology", "ai", "science", "space")),
    ("Culture", ("culture", "entertainment", "mentions", "social", "pop culture", "music", "movies",
                 "awards", "tweets", "celebrities")),
]


_TITLE_HINTS = [
    ("Weather", ("snow", "rain", "temperature", "temp in", "hurricane", "tornado", "weather", "°")),
    ("Crypto", ("bitcoin", "ethereum", "btc", "eth ", "solana", "xrp", "crypto")),
    ("Economy", ("fed ", "interest rate", "cpi", "gdp", "unemployment", "s&p", "nasdaq", "gas price", "oil")),
]


def normalize_category(labels, title: str = "") -> str:
    """Map venue tags/categories onto a small fixed set of tabs. First match in priority order wins;
    falls back to keywords in the title."""
    lowered = [str(l).strip().lower() for l in labels if l]
    for cat, words in _CATEGORY_WORDS:
        if any(l in words for l in lowered):
            return cat
    t = title.lower()
    for cat, words in _TITLE_HINTS:
        if any(w in t for w in words):
            return cat
    return "Other"
