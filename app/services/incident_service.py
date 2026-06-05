from app.models.schemas import AlertPayload, ClusteredEvent, IncidentReport
from typing import Optional
from datetime import datetime, timedelta
import uuid


class IncidentService:
    def __init__(self):
        self._events: dict[str, ClusteredEvent] = {}
        self._reports: dict[str, IncidentReport] = {}

    async def process_alert(self, alert: AlertPayload) -> ClusteredEvent:
        existing = self._find_matching_event(alert)
        if existing:
            existing.alerts.append(alert)
            existing.last_seen = alert.timestamp
            existing.alert_count += 1
            return existing

        event = ClusteredEvent(
            event_id=str(uuid.uuid4()),
            alerts=[alert],
            title=alert.title,
            severity=alert.severity,
            service=alert.service,
            alert_count=1,
            first_seen=alert.timestamp,
            last_seen=alert.timestamp,
        )
        self._events[event.event_id] = event
        return event

    def _find_matching_event(self, alert: AlertPayload) -> Optional[ClusteredEvent]:
        window = timedelta(minutes=5)
        for event in self._events.values():
            if event.service == alert.service and abs((event.last_seen - alert.timestamp).total_seconds()) < window.total_seconds():
                return event
        return None

    def get_event(self, event_id: str) -> Optional[ClusteredEvent]:
        return self._events.get(event_id)

    def save_report(self, report: IncidentReport):
        self._reports[report.event_id] = report
