"""Content hash cache tests — verify cache hit/miss/invalidation behavior."""
import time
import pytest
from datetime import datetime
from app.models.schemas import AlertPayload, ClusteredEvent, RootCauseResult
from app.services.cache_service import ContentHashCache


@pytest.fixture
def cache():
    return ContentHashCache(ttl_seconds=3600)


@pytest.fixture
def event_a():
    return ClusteredEvent(
        event_id="evt-a",
        alerts=[AlertPayload(
            source="pd", alert_id="a1", title="CPU high", description="cpu>90",
            severity="critical", service="api", timestamp=datetime.utcnow(), raw={},
        )],
        title="cpu spike", severity="critical", service="api",
        alert_count=1, first_seen=datetime.utcnow(), last_seen=datetime.utcnow(),
    )


@pytest.fixture
def event_b():
    return ClusteredEvent(
        event_id="evt-b",
        alerts=[AlertPayload(
            source="pd", alert_id="b1", title="OOM", description="memory>95",
            severity="critical", service="worker", timestamp=datetime.utcnow(), raw={},
        )],
        title="memory spike", severity="critical", service="worker",
        alert_count=1, first_seen=datetime.utcnow(), last_seen=datetime.utcnow(),
    )


@pytest.fixture
def rca_result(event_a):
    return RootCauseResult(
        event_id=event_a.event_id,
        root_cause="null pointer in WorkerService.java:42",
        confidence=0.9,
        fix_suggestion="add null guard",
        supporting_evidence="stack trace from worker-1",
    )


class TestContentHashCache:
    def test_miss_on_empty_cache(self, cache, event_a):
        assert cache.get(event_a) is None

    def test_hit_after_set(self, cache, event_a, rca_result):
        cache.set(event_a, rca_result)
        result = cache.get(event_a)
        assert result is not None
        assert result.root_cause == rca_result.root_cause
        assert result.confidence == 0.9

    def test_miss_for_different_event(self, cache, event_a, event_b, rca_result):
        cache.set(event_a, rca_result)
        assert cache.get(event_b) is None

    def test_invalidation(self, cache, event_a, rca_result):
        cache.set(event_a, rca_result)
        cache.invalidate(event_a)
        assert cache.get(event_a) is None

    def test_ttl_expiry(self, event_a, rca_result):
        cache = ContentHashCache(ttl_seconds=0)
        cache.set(event_a, rca_result)
        time.sleep(0.01)
        assert cache.get(event_a) is None

    def test_cache_stats(self, cache, event_a, rca_result):
        assert cache.stats["entries"] == 0
        cache.set(event_a, rca_result)
        assert cache.stats["entries"] == 1

    def test_same_content_same_hash(self, cache, rca_result):
        a1 = ClusteredEvent(
            event_id="x", alerts=[AlertPayload(
                source="pd", alert_id="1", title="err", description="err",
                severity="critical", service="api", timestamp=datetime(2024, 1, 1), raw={},
            )],
            title="err", severity="critical", service="api",
            alert_count=1, first_seen=datetime.utcnow(), last_seen=datetime.utcnow(),
        )
        a2 = ClusteredEvent(
            event_id="y", alerts=[AlertPayload(
                source="pd", alert_id="2", title="err", description="err",
                severity="critical", service="api", timestamp=datetime(2024, 1, 1), raw={},
            )],
            title="err", severity="critical", service="api",
            alert_count=1, first_seen=datetime.utcnow(), last_seen=datetime.utcnow(),
        )
        cache.set(a1, rca_result)
        assert cache.get(a2) is not None  # same alert content = same hash
