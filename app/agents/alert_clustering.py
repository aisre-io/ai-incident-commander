from app.models.schemas import ClusteredEvent
from app.integrations.deepseek import DeepSeekClient
from app.config import get_model_for
from app.utils.logger import logger


class AlertClusteringAgent:
    def __init__(self):
        self.llm = DeepSeekClient(model=get_model_for("clustering"))

    async def run(self, event: ClusteredEvent) -> ClusteredEvent:
        logger.info(f"Alert clustering for {event.service} using {self.llm._model}")

        if not event.alerts:
            return event

        system_prompt = (
            "You are an alert clustering specialist. "
            "Analyze the following alerts and determine if they belong to the same incident. "
            "Output a concise cluster summary."
        )

        alert_summary = "\n".join(
            f"[{a.severity}] {a.title}" for a in event.alerts
        )

        user_prompt = f"Service: {event.service}\nAlerts ({event.alert_count}):\n{alert_summary}"

        analysis = await self.llm.chat(system=system_prompt, user=user_prompt)
        if analysis:
            event.title = analysis.split("\n")[0] if "\n" in analysis else analysis

        return event
