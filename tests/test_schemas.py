"""Schema validation tests — catch regressions in model shapes or required fields."""
import pytest
from datetime import datetime
from pydantic import ValidationError
from app.models.schemas import AlertPayload, ClusteredEvent, RootCauseResult, IncidentReport


class TestAlertPayload:
    def test_valid_alert(self, sample_alert):
        assert sample_alert.source == "pagerduty"
        assert sample_alert.severity == "critical"

    def test_minimal_alert(self):
        a = AlertPayload(
            source="test",
            alert_id="id",
            title="t",
            description="d",
            severity="info",
            service="svc",
            timestamp=datetime.utcnow(),
            raw={},
        )
        assert a.source == "test"

    def test_missing_field_fails(self):
        with pytest.raises(ValidationError):
            AlertPayload()  # type: ignore


class TestClusteredEvent:
    def test_valid_event(self, sample_event):
        assert sample_event.alert_count >= 1
        assert len(sample_event.alerts) == sample_event.alert_count

    def test_auto_fields(self, sample_alert):
        e = ClusteredEvent(
            event_id="e1",
            alerts=[sample_alert],
            title="t",
            severity="critical",
            service="svc",
            alert_count=1,
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
        )
        assert e.event_id == "e1"


class TestRootCauseResult:
    def test_valid_rca(self, sample_rca):
        assert 0 <= sample_rca.confidence <= 1
        assert sample_rca.suspect_commit is not None

    def test_confidence_bounds(self, sample_rca):
        for val in [-0.1, 1.5]:
            with pytest.raises(ValidationError):
                RootCauseResult(
                    event_id="e1",
                    root_cause="x",
                    confidence=val,
                    fix_suggestion="x",
                    supporting_evidence="x",
                )

    def test_rca_without_optional_fields(self):
        r = RootCauseResult(
            event_id="e1",
            root_cause="disk full",
            confidence=0.8,
            fix_suggestion="clean up disk",
            supporting_evidence="disk usage 100%",
        )
        assert r.suspect_commit is None
        assert r.suspect_line is None


class TestIncidentReport:
    def test_valid_report(self, sample_report):
        assert sample_report.report_generated_at is not None
        assert sample_report.status == "investigated"

    def test_status_default(self, sample_report):
        assert sample_report.status == "investigated"

    def test_custom_status(self, sample_report):
        sample_report.status = "resolved"
        assert sample_report.status == "resolved"


class TestModelRouting:
    def test_rca_now_uses_flash_by_default(self):
        from app.config import get_model_for
        assert get_model_for("rca") == "deepseek-v4-flash"

    def test_rca_pro_available_for_escalation(self):
        from app.config import get_model_for
        assert get_model_for("rca_pro") == "deepseek-v4-pro"

    def test_flash_tasks(self):
        from app.config import get_model_for
        for task in ["clustering", "extraction", "synthesis", "quick"]:
            assert get_model_for(task) == "deepseek-v4-flash"

    def test_escalation_threshold(self):
        from app.config import should_escalate_to_pro
        assert should_escalate_to_pro(0.5) is True
        assert should_escalate_to_pro(0.8) is False
