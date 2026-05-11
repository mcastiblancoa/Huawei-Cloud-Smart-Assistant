import hashlib
import json
import time
import threading
from typing import Any

from config.logging import get_logger

logger = get_logger("cloud.cache")


class CloudCache:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, ttl: int = 30, max_entries: int = 200):
        self._ttl = ttl
        self._max = max_entries
        self._store: dict[str, tuple[Any, float]] = {}

    @classmethod
    def instance(cls, ttl: int = 30, max_entries: int = 200) -> "CloudCache":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(ttl=ttl, max_entries=max_entries)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    @staticmethod
    def make_key(service: str, operation: str, params: dict | None = None) -> str:
        raw = f"{service}:{operation}:{json.dumps(params or {}, sort_keys=True, separators=(',', ':'))}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, ts = entry
        if time.time() - ts > self._ttl:
            del self._store[key]
            return None
        logger.debug("Cache hit", extra={"structured_extra": {"key": key[:12]}})
        return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if len(self._store) >= self._max:
                oldest_key = min(self._store, key=lambda k: self._store[k][1])
                del self._store[oldest_key]
            self._store[key] = (value, time.time())

    def invalidate(self, service: str = "") -> None:
        if not service:
            with self._lock:
                self._store.clear()
            return
        with self._lock:
            keys_to_remove = [k for k in list(self._store.keys())]
            for k in keys_to_remove:
                del self._store[k]

    def invalidate_key(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    @property
    def size(self) -> int:
        return len(self._store)
