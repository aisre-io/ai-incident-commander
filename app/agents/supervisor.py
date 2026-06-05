from app.models.schemas import ClusteredEvent, IncidentReport, RootCauseResult
from app.agents.alert_clustering import AlertClusteringAgent
from app.agents.rca_investigation import RCAInvestigationAgent
from app.agents.synthesis import SynthesisAgent
from app.services.cache_service import cache
from app.utils.logger import logger


class SupervisorAgent:
    def __init__(self):
        self.clustering_agent = AlertClusteringAgent()
        self.rca_agent = RCAInvestigationAgent()
        self.synthesis_agent = SynthesisAgent()

    async def run(self, event: ClusteredEvent) -> IncidentReport:
        logger.info(f"Supervisor: processing event {event.event_id}")

        cached = cache.get(event)
        if cached:
            logger.info(f"Supervisor: using cached RCA for {event.event_id}")
            return await self.synthesis_agent.run(event, cached)

        clustered = await self.clustering_agent.run(event)

        rca_result: RootCauseResult = await self.rca_agent.run(clustered)

        cache.set(event, rca_result)

        report = await self.synthesis_agent.run(clustered, rca_result)

        logger.info(f"Supervisor: report generated for {event.event_id}, confidence={report.confidence_score}")
        return report
