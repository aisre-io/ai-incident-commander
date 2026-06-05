import json
from app.models.schemas import ClusteredEvent, RootCauseResult
from app.integrations.github import GitHubClient
from app.integrations.deepseek import DeepSeekClient
from app.config import get_model_for, should_escalate_to_pro, TASK
from app.utils.logger import logger


def _try_parse_confidence(text: str) -> float | None:
    try:
        data = json.loads(text)
        return float(data.get("confidence", 0))
    except (json.JSONDecodeError, ValueError, TypeError):
        import re
        m = re.search(r'"confidence"\s*:\s*([\d.]+)', text)
        if m:
            return float(m.group(1))
        return None


class RCAInvestigationAgent:
    def __init__(self):
        self.github = GitHubClient()
        self._flash_llm = DeepSeekClient(model=get_model_for("rca"))
        self._pro_llm = DeepSeekClient(model=get_model_for("rca_pro"))

    async def _call(self, llm: DeepSeekClient, event: ClusteredEvent, commits: list, deep: bool = False) -> tuple[str, float]:
        system = (
            "You are an expert SRE root cause analysis engineer.\n\n"
            "Analysis method:\n"
            "1. Read the error logs first — they tell you what actually broke\n"
            "2. Cross-reference with alerts to confirm the affected service\n"
            "3. Scan recent commits — identify the change most likely related to the failure\n"
            "4. Synthesize: what is the causal chain from commit → system behavior → alert?\n\n"
            "Output in JSON format with fields: root_cause, confidence (0-1), fix_suggestion, suspect_commit (if any), supporting_evidence."
        )

        user = f"""
Alert:
- Title: {event.title}
- Service: {event.service}
- Severity: {event.severity}
- Description: {event.alerts[0].description if event.alerts else 'N/A'}

Recent commits analyzed: {len(commits)}
"""

        output = await llm.chat(system=system, user=user)
        confidence = _try_parse_confidence(output) or 0.0
        return output or "Analysis completed but LLM returned no output", confidence

    async def run(self, event: ClusteredEvent) -> RootCauseResult:
        model_used = "flash"
        logger.info(f"RCA investigation for event {event.event_id} starting with Flash")

        commits = await self.github.get_recent_commits()
        llm_output, confidence = await self._call(self._flash_llm, event, commits)

        if should_escalate_to_pro(confidence, "rca"):
            logger.info(f"Flash confidence={confidence:.2f} < 0.7, escalating to Pro for event {event.event_id}")
            pro_output, pro_confidence = await self._call(self._pro_llm, event, commits, deep=True)
            if pro_confidence > confidence:
                llm_output, confidence = pro_output, pro_confidence
                model_used = "pro"

        logger.info(f"RCA complete for event {event.event_id} using {model_used}, confidence={confidence:.2f}")

        return RootCauseResult(
            event_id=event.event_id,
            root_cause=llm_output or "Analysis completed but LLM returned no output",
            confidence=confidence,
            fix_suggestion=f"Investigate recent changes to the service",
            supporting_evidence=f"Alert: {event.title}\nService: {event.service}\nModel: {model_used}\nLLM Analysis: {llm_output or 'N/A'}",
        )
