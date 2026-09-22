"""
Sagar Mitra / ORCA - Oceanography News Feed
==============================================
Fetches and parses ScienceDaily's Oceanography RSS feed for GET /api/news
(main.py). A 1-hour in-process TTL cache avoids re-fetching/re-parsing the
feed on every request.
"""
import time
from typing import List, Optional

import feedparser

FEED_URL = "https://www.sciencedaily.com/rss/earth_climate/oceanography.xml"
TTL_SECONDS = 60 * 60  # 1 hour

# Ocean domain taxonomy: keyword lists checked (case-insensitively) against
# each article's title+summary at ingest to produce a `domains` tag array.
# Keys are the slugs used by GET /api/news's `?domain=` filter and by
# GET /api/news/domains (frontend domain-selector source of truth).
DOMAIN_TAXONOMY: dict[str, List[str]] = {
    "climate": ["climate", "warming", "co2", "carbon", "greenhouse", "emission"],
    "marine-life": ["fish", "coral", "species", "whale", "shark", "reef", "biodiversity", "marine life", "ecosystem"],
    "weather-hazards": ["storm", "cyclone", "hurricane", "flood", "tsunami", "wave", "hazard", "typhoon"],
    "pollution": ["plastic", "pollution", "oil spill", "contaminant", "microplastic", "waste"],
    "research": ["study", "researchers", "scientists", "discovery", "survey", "data", "study finds"],
}

_cache_entries: List[dict] = []
_cache_fetched_at: float = 0.0


def _tag_domains(title: str, summary: str) -> List[str]:
    text = f"{title} {summary}".lower()
    return [domain for domain, keywords in DOMAIN_TAXONOMY.items() if any(kw in text for kw in keywords)]


def _fetch_top_entries(limit: int = 5) -> List[dict]:
    parsed = feedparser.parse(FEED_URL)
    entries = []
    for entry in parsed.entries[:limit]:
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        entries.append({
            "title": title,
            "link": entry.get("link", ""),
            "summary": summary,
            "domains": _tag_domains(title, summary),
        })
    return entries


def get_oceanography_news(limit: int = 5, domain: Optional[str] = None) -> List[dict]:
    """Returns the top `limit` ScienceDaily oceanography headlines, tagged
    with `domains` (see DOMAIN_TAXONOMY), using a 1-hour cache. On fetch
    failure, returns the last successfully cached entries (possibly stale)
    rather than raising, or an empty list if nothing has ever been fetched
    successfully.

    `domain`: if given, only entries whose `domains` array contains this
    slug are returned (case-insensitive); unrecognized/empty domain values
    return the full, unfiltered set rather than an empty list.
    """
    global _cache_entries, _cache_fetched_at
    now = time.time()
    if _cache_entries and (now - _cache_fetched_at) < TTL_SECONDS:
        entries = _cache_entries
    else:
        try:
            fetched = _fetch_top_entries(limit)
            if fetched:
                _cache_entries = fetched
                _cache_fetched_at = now
        except Exception as e:
            print(f"[news_feed] Failed to fetch {FEED_URL}: {e}")
        entries = _cache_entries

    if domain:
        domain_slug = domain.strip().lower()
        if domain_slug in DOMAIN_TAXONOMY:
            entries = [e for e in entries if domain_slug in e.get("domains", [])]
    return entries


if __name__ == "__main__":
    for item in get_oceanography_news():
        print(item)
