import pytest
from datetime import datetime
from app.models.schemas import AlertPayload, ClusteredEvent, RootCauseResult, IncidentReport


@pytest.fixture
def sample_alert() -> AlertPayload:
    return AlertPayload(
        source="pagerduty",
        alert_id="alert-001",
        title="High CPU on api-gateway",
        description="CPU > 90% for 5 minutes on api-gateway instance i-123",
        severity="critical",
        service="api-gateway",
        timestamp=datetime.utcnow(),
        raw={"instance": "i-123", "region": "us-east-1"},
    )


@pytest.fixture
def sample_event(sample_alert) -> ClusteredEvent:
    return ClusteredEvent(
        event_id="evt-001",
        alerts=[sample_alert],
        title="CPU spike on api-gateway",
        severity="critical",
        service="api-gateway",
        alert_count=1,
        first_seen=datetime.utcnow(),
        last_seen=datetime.utcnow(),
    )


@pytest.fixture
def sample_rca() -> RootCauseResult:
    return RootCauseResult(
        event_id="evt-001",
        root_cause="Null pointer in UserService.java:82 introduced by commit abc123",
        confidence=0.92,
        suspect_commit="abc123def456",
        suspect_file="UserService.java",
        suspect_line=82,
        fix_suggestion="Add null guard before calling user.getName()",
        supporting_evidence="Stack trace shows NullPointerException at UserService.java:82",
    )


@pytest.fixture
def sample_report(sample_event, sample_rca) -> IncidentReport:
    return IncidentReport(
        event_id=sample_event.event_id,
        title=sample_event.title,
        severity=sample_event.severity,
        service=sample_event.service,
        root_cause=sample_rca,
        alert_count=sample_event.alert_count,
        first_seen=sample_event.first_seen,
        confidence_score=sample_rca.confidence,
    )
