import hashlib
import json
import time
from typing import Any, Optional
from app.models.schemas import ClusteredEvent, RootCauseResult
from app.utils.logger import logger


class ContentHashCache:
    def __init__(self, ttl_seconds: int = 3600):
        self._store: dict[str, tuple[float, Any]] = {}
        self._ttl = ttl_seconds

    def _hash(self, event: ClusteredEvent) -> str:
        raw = {
            "service": event.service,
            "title": event.title,
            "alerts": [
                {
                    "title": a.title,
                    "severity": a.severity,
                    "description": a.description,
                    "service": a.service,
                }
                for a in (event.alerts or [])
            ],
        }
        return hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()

    def get(self, event: ClusteredEvent) -> Optional[RootCauseResult]:
        key = self._hash(event)
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, value = entry
        if time.time() - ts > self._ttl:
            del self._store[key]
            return None
        logger.info(f"Cache hit for event {event.event_id} (key={key[:12]}...)")
        return value

    def set(self, event: ClusteredEvent, result: RootCauseResult):
        key = self._hash(event)
        self._store[key] = (time.time(), result)
        logger.debug(f"Cached result for event {event.event_id} (key={key[:12]}...)")

    def invalidate(self, event: ClusteredEvent):
        key = self._hash(event)
        self._store.pop(key, None)

    @property
    def size(self) -> int:
        return len(self._store)

    @property
    def stats(self) -> dict:
        return {"entries": len(self._store), "ttl_seconds": self._ttl}


cache = ContentHashCache(ttl_seconds=3600)
