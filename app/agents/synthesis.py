from app.models.schemas import ClusteredEvent, RootCauseResult, IncidentReport
from app.utils.logger import logger


class SynthesisAgent:
    async def run(self, event: ClusteredEvent, rca: RootCauseResult) -> IncidentReport:
        logger.info(f"Synthesis for event {event.event_id}")

        report = IncidentReport(
            event_id=event.event_id,
            title=event.title,
            severity=event.severity,
            service=event.service,
            root_cause=rca,
            alert_count=event.alert_count,
            first_seen=event.first_seen,
            confidence_score=rca.confidence,
        )

        return report
