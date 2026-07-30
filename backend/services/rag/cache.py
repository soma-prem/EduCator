import json
import logging
import os
import threading
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = int(os.getenv("RAG_CACHE_TTL_SECONDS", "300") or 300)
_REDIS_URL = os.getenv("REDIS_URL", "").strip()

_local_cache: Dict[str, Dict[str, Any]] = {}
_cache_lock = threading.Lock()

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None


def _build_cache_key(key: str) -> str:
    return f"rag_cache:{key}"


def _redis_available() -> bool:
    return bool(redis and _REDIS_URL)


def _get_redis_client() -> Optional[Any]:
    if not _redis_available():
        return None
    try:
        client = redis.from_url(_REDIS_URL, decode_responses=True)
        client.ping()
        return client
    except Exception as exc:
        logger.warning("Redis cache unavailable: %s", exc)
        return None


def _normalize_value(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def get_cache(key: str) -> Optional[Any]:
    full_key = _build_cache_key(key)
    client = _get_redis_client()
    if client:
        try:
            cached = client.get(full_key)
            if cached is None:
                return None
            return json.loads(cached)
        except Exception as exc:
            logger.warning("Redis cache read failed for %s: %s", full_key, exc)
            return None

    with _cache_lock:
        entry = _local_cache.get(full_key)
        if not entry:
            return None
        if time.time() >= entry["expires_at"]:
            del _local_cache[full_key]
            return None
        return entry["value"]


def set_cache(key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
    full_key = _build_cache_key(key)
    ttl = ttl_seconds if ttl_seconds is not None else _CACHE_TTL_SECONDS
    client = _get_redis_client()
    if client:
        try:
            client.set(full_key, _normalize_value(value), ex=ttl)
            return
        except Exception as exc:
            logger.warning("Redis cache write failed for %s: %s", full_key, exc)

    with _cache_lock:
        _local_cache[full_key] = {
            "expires_at": time.time() + ttl,
            "value": value,
        }


def invalidate_cache(key: str) -> None:
    full_key = _build_cache_key(key)
    client = _get_redis_client()
    if client:
        try:
            client.delete(full_key)
            return
        except Exception as exc:
            logger.warning("Redis cache delete failed for %s: %s", full_key, exc)

    with _cache_lock:
        _local_cache.pop(full_key, None)


def invalidate_document_cache(document_id: str) -> None:
    if not document_id:
        return
    client = _get_redis_client()
    if client:
        try:
            for key in client.scan_iter(match="rag_cache:*"):
                client.delete(key)
        except Exception as exc:
            logger.warning("Redis cache document invalidation failed for %s: %s", document_id, exc)
        return

    with _cache_lock:
        keys_to_remove = [key for key in _local_cache if key.startswith("rag_cache:")]
        for key in keys_to_remove:
            _local_cache.pop(key, None)
