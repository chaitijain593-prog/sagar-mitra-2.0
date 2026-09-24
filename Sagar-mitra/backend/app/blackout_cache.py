"""HTTP wrapper with a bounded in-memory last-success cache.

Cached payloads stay in RAM: API requests never create cache files that can
trigger frontend file watchers. A stale in-process payload is used only for
connection and timeout failures.
"""
import hashlib
import json
import threading
from collections import OrderedDict
from typing import Any, Dict, Optional

import requests

_MAX_CACHE_ENTRIES = 256
_memory_cache: OrderedDict[str, dict] = OrderedDict()
_cache_lock = threading.RLock()


def _cache_key(url: str, params: Optional[Dict[str, Any]]) -> str:
    key = url + "?" + json.dumps(params or {}, sort_keys=True)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def cached_get(url: str, params: Optional[Dict[str, Any]] = None, timeout: int = 10) -> dict:
    """Return live JSON, or an in-memory stale response after network loss."""
    key = _cache_key(url, params)
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        with _cache_lock:
            _memory_cache[key] = data
            _memory_cache.move_to_end(key)
            while len(_memory_cache) > _MAX_CACHE_ENTRIES:
                _memory_cache.popitem(last=False)
        return data
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        with _cache_lock:
            stale = _memory_cache.get(key)
        if stale is not None:
            return {**stale, "_blackout_stale": True}
        raise