from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


class AlertPayload(BaseModel):
    source: str
    alert_id: str
    title: str
    description: str
    severity: str
    service: str
    timestamp: datetime
    raw: dict[str, Any] = {}


class ClusteredEvent(BaseModel):
    event_id: str
    alerts: list[AlertPayload]
    title: str
    severity: str
    service: str
    alert_count: int
    first_seen: datetime
    last_seen: datetime


class RootCauseResult(BaseModel):
    event_id: str
    root_cause: str
    confidence: float = Field(ge=0, le=1)
    suspect_commit: Optional[str] = None
    suspect_file: Optional[str] = None
    suspect_line: Optional[int] = None
    similar_incidents: list[str] = []
    runbook_refs: list[str] = []
    fix_suggestion: str
    supporting_evidence: str


class IncidentReport(BaseModel):
    event_id: str
    title: str
    severity: str
    service: str
    root_cause: RootCauseResult
    alert_count: int
    first_seen: datetime
    report_generated_at: datetime = Field(default_factory=datetime.utcnow)
    confidence_score: float = Field(ge=0, le=1)
    status: str = "investigated"


class SlackNotification(BaseModel):
    channel: str
    report: IncidentReport
    oncall_person: Optional[str] = None
