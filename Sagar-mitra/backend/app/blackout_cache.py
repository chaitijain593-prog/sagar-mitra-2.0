"""
Sagar Mitra / ORCA - Blackout Mode (stale-cache network wrapper)
===================================================================
Vessels lose connectivity at sea. `cached_get` wraps requests.get: on a
successful response it persists the JSON body to static/offline_cache/ (a
filename hashed from the request URL+params) and returns the parsed JSON.
On ConnectionError/Timeout it falls back to the last-saved JSON for that
same URL+params, so tools keep answering (with stale data) instead of
raising through to the user mid-blackout.
"""
import hashlib
import json
import os
from typing import Any, Dict, Optional

import requests

CACHE_DIR = os.environ.get("SAGAR_MITRA_OFFLINE_CACHE_DIR", "./static/offline_cache")


def _cache_path(url: str, params: Optional[Dict[str, Any]]) -> str:
    key = url + "?" + json.dumps(params or {}, sort_keys=True)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, f"{digest}.json")


def cached_get(url: str, params: Optional[Dict[str, Any]] = None, timeout: int = 10) -> dict:
    """Drop-in for `requests.get(url, params=params, timeout=timeout).json()`.

    Returns the live JSON on success (and caches it), or the last cached
    JSON for this exact URL+params on ConnectionError/Timeout. Raises
    requests.exceptions.RequestException for other failures (bad status,
    etc.) or if no cache exists yet for a failed request.
    """
    path = _cache_path(url, params)
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return data
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                stale = json.load(f)
            stale["_blackout_stale"] = True
            return stale
        raise
