"""
Sagar Mitra / ORCA - Oceanography News Feed
==============================================
Fetches and parses ScienceDaily's Oceanography RSS feed for GET /api/news
(main.py). A 1-hour in-process TTL cache avoids re-fetching/re-parsing the
feed on every request.
"""
import time
from typing import List

import feedparser

FEED_URL = "https://www.sciencedaily.com/rss/earth_climate/oceanography.xml"
TTL_SECONDS = 60 * 60  # 1 hour

_cache_entries: List[dict] = []
_cache_fetched_at: float = 0.0


def _fetch_top_entries(limit: int = 5) -> List[dict]:
    parsed = feedparser.parse(FEED_URL)
    entries = []
    for entry in parsed.entries[:limit]:
        entries.append({
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "summary": entry.get("summary", ""),
        })
    return entries


def get_oceanography_news(limit: int = 5) -> List[dict]:
    """Returns the top `limit` ScienceDaily oceanography headlines, using a
    1-hour cache. On fetch failure, returns the last successfully cached
    entries (possibly stale) rather than raising, or an empty list if
    nothing has ever been fetched successfully."""
    global _cache_entries, _cache_fetched_at
    now = time.time()
    if _cache_entries and (now - _cache_fetched_at) < TTL_SECONDS:
        return _cache_entries
    try:
        entries = _fetch_top_entries(limit)
        if entries:
            _cache_entries = entries
            _cache_fetched_at = now
        return _cache_entries
    except Exception as e:
        print(f"[news_feed] Failed to fetch {FEED_URL}: {e}")
        return _cache_entries


if __name__ == "__main__":
    for item in get_oceanography_news():
        print(item)
