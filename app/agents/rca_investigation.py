import json
from typing import Optional
from app.models.schemas import ClusteredEvent, RootCauseResult
from app.integrations.github import GitHubClient
from app.integrations.deepseek import DeepSeekClient
from app.integrations.tdengine import TDengineClient
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
    def __init__(self, tdengine: Optional[TDengineClient] = None):
        self.github = GitHubClient()
        self._td = tdengine
        self._flash_llm = DeepSeekClient(model=get_model_for("rca"))
        self._pro_llm = DeepSeekClient(model=get_model_for("rca_pro"))

    async def _fetch_tdengine_evidence(self, service: str) -> str:
        if not self._td:
            return ""
        try:
            metrics = await self._td.query_metrics(service, minutes_back=120)
            if not metrics:
                return ""
            lines = [f"  [{m['ts']}] {m['metric_name']} = {m['metric_value']}" for m in metrics[:20]]
            return "TDengine metrics around incident time:\n" + "\n".join(lines)
        except Exception as e:
            logger.warning(f"TDengine metrics query skipped: {e}")
            return ""

    async def _call(self, llm: DeepSeekClient, event: ClusteredEvent, commits: list, td_evidence: str = "", deep: bool = False) -> tuple[str, float]:
        system = (
            "You are an expert SRE root cause analysis engineer.\n\n"
            "Analysis method:\n"
            "1. Read the error logs first — they tell you what actually broke\n"
            "2. Cross-reference with alerts to confirm the affected service\n"
            "3. Scan recent commits — identify the change most likely related to the failure\n"
            "4. If available, review time-series metrics (CPU, memory, disk, latency) for anomaly patterns\n"
            "5. Synthesize: what is the causal chain from commit → system behavior → alert?\n\n"
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

        if td_evidence:
            user += f"\n{td_evidence}\n"

        output = await llm.chat(system=system, user=user)
        confidence = _try_parse_confidence(output) or 0.0
        return output or "Analysis completed but LLM returned no output", confidence

    async def run(self, event: ClusteredEvent) -> RootCauseResult:
        model_used = "flash"
        logger.info(f"RCA investigation for event {event.event_id} starting with Flash")

        commits = await self.github.get_recent_commits()

        td_evidence = await self._fetch_tdengine_evidence(event.service)

        llm_output, confidence = await self._call(self._flash_llm, event, commits, td_evidence)

        if should_escalate_to_pro(confidence, "rca"):
            logger.info(f"Flash confidence={confidence:.2f} < 0.7, escalating to Pro for event {event.event_id}")
            pro_output, pro_confidence = await self._call(self._pro_llm, event, commits, td_evidence, deep=True)
            if pro_confidence > confidence:
                llm_output, confidence = pro_output, pro_confidence
                model_used = "pro"

        logger.info(f"RCA complete for event {event.event_id} using {model_used}, confidence={confidence:.2f}")

        evidence_parts = [f"Alert: {event.title}", f"Service: {event.service}", f"Model: {model_used}"]
        if td_evidence:
            evidence_parts.append(f"TDengine metrics: {len(td_evidence.split(chr(10)))} data points")
        evidence_parts.append(f"LLM Analysis: {llm_output or 'N/A'}")

        return RootCauseResult(
            event_id=event.event_id,
            root_cause=llm_output or "Analysis completed but LLM returned no output",
            confidence=confidence,
            fix_suggestion=f"Investigate recent changes to the service",
            supporting_evidence="\n".join(evidence_parts),
        )
