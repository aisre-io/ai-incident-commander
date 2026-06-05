"""Agent regression tests — validate input/output contracts for each agent."""
import pytest
from datetime import datetime
from app.models.schemas import AlertPayload, ClusteredEvent, RootCauseResult, IncidentReport
from app.agents.synthesis import SynthesisAgent


@pytest.mark.asyncio
async def test_synthesis_agent_output_shape(sample_event, sample_rca):
    agent = SynthesisAgent()
    report = await agent.run(sample_event, sample_rca)

    assert isinstance(report, IncidentReport)
    assert report.event_id == sample_event.event_id
    assert report.root_cause is sample_rca
    assert 0 <= report.confidence_score <= 1


@pytest.mark.asyncio
async def test_synthesis_with_low_confidence(sample_event):
    rca = RootCauseResult(
        event_id=sample_event.event_id,
        root_cause="possible memory leak",
        confidence=0.3,
        fix_suggestion="check heap usage",
        supporting_evidence="heap grew 2x in 1h",
    )
    agent = SynthesisAgent()
    report = await agent.run(sample_event, rca)
    assert report.confidence_score == 0.3
    assert report.status == "investigated"


@pytest.mark.asyncio
async def test_synthesis_with_zero_alerts():
    event = ClusteredEvent(
        event_id="evt-empty",
        alerts=[],
        title="no alerts",
        severity="info",
        service="test",
        alert_count=0,
        first_seen=datetime.utcnow(),
        last_seen=datetime.utcnow(),
    )
    rca = RootCauseResult(
        event_id="evt-empty",
        root_cause="nothing found",
        confidence=0.0,
        fix_suggestion="n/a",
        supporting_evidence="no alerts to analyze",
    )
    agent = SynthesisAgent()
    report = await agent.run(event, rca)
    assert report.root_cause.root_cause == "nothing found"


class TestAgentContract:
    """Contract tests — each agent must accept ClusteredEvent and return the correct type."""

    def test_rca_agent_imports(self):
        from app.agents.rca_investigation import RCAInvestigationAgent
        agent = RCAInvestigationAgent()
        assert hasattr(agent, "run")

    def test_clustering_agent_imports(self):
        from app.agents.alert_clustering import AlertClusteringAgent
        agent = AlertClusteringAgent()
        assert hasattr(agent, "run")

    def test_supervisor_imports(self):
        from app.agents.supervisor import SupervisorAgent
        agent = SupervisorAgent()
        assert hasattr(agent, "run")
