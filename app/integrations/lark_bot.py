import httpx
from app.config import get_settings
from app.models.schemas import IncidentReport
from app.utils.logger import logger

_LARK_CN_URL = "https://open.feishu.cn/open-apis/bot/v2/hook"
_LARK_INTL_URL = "https://open.larksuite.com/open-apis/bot/v2/hook"

_SEVERITY_TO_COLOR = {
    "critical": "red",
    "high": "orange",
    "warning": "yellow",
    "info": "blue",
    "low": "green",
}


class LarkNotifier:
    """Feishu/Lark custom bot webhook implementation of the Notifier protocol.

    Uses incoming-webhook (no App registration required, no OAuth, no ngrok).
    Setup:
      1. In Feishu/Lark group: Settings -> Bots -> Add Bot -> Custom Bot
      2. Copy the webhook URL (contains the verification token)
      3. Set LARK_WEBHOOK_URL in .env
    """

    @property
    def name(self) -> str:
        return "lark"

    async def health_check(self) -> bool:
        settings = get_settings()
        return bool(settings.lark_webhook_url)

    async def send_report(self, report: IncidentReport) -> bool:
        settings = get_settings()
        if not settings.lark_webhook_url:
            logger.warning("Lark webhook URL not configured, skipping notification")
            return False

        payload = _build_card_payload(report, settings)
        base = _LARK_INTL_URL if settings.lark_region == "intl" else _LARK_CN_URL
        url = _resolve_webhook_url(base, settings.lark_webhook_url)
        logger.debug(f"Lark POST -> {url}")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                body = resp.json()
                if body.get("code") and body.get("code") != 0:
                    logger.error(f"Lark webhook returned error: {body}")
                    raise RuntimeError(f"Lark error: {body.get('msg', 'unknown')}")
                logger.info(f"Incident report posted to Lark for event {report.event_id}")
                return True
        except httpx.HTTPStatusError as e:
            logger.error(f"Lark HTTP error {e.response.status_code}: {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Lark request failed: {e}")
            raise


def _resolve_webhook_url(base: str, raw: str) -> str:
    """Accept either a bare token (e.g. ``abc-xyz``) or a full URL.

    Pasting the full URL from Feishu/Lark group settings is the common
    path, so we detect that case and strip the base prefix instead of
    prepending it (which would produce a malformed double-prefixed URL).
    """
    raw = raw.strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    return f"{base}/{raw}"


def _build_card_payload(report: IncidentReport, settings) -> dict:
    color = _SEVERITY_TO_COLOR.get(report.severity.lower(), "blue")
    title = f"Incident Report: {report.title}"

    fields = [
        {"is_short": True, "text": {"tag": "lark_md", "content": f"**Service**\n{report.service}"}},
        {"is_short": True, "text": {"tag": "lark_md", "content": f"**Severity**\n{report.severity}"}},
        {"is_short": True, "text": {"tag": "lark_md", "content": f"**Alert Count**\n{report.alert_count}"}},
        {"is_short": True, "text": {"tag": "lark_md", "content": f"**Confidence**\n{report.confidence_score * 100:.0f}%"}},
    ]

    elements: list[dict] = [{"tag": "div", "fields": fields}, {"tag": "hr"}]
    elements.append({"tag": "div", "text": {"tag": "lark_md", "content": f"**Root Cause**\n{report.root_cause.root_cause}"}})
    elements.append({"tag": "div", "text": {"tag": "lark_md", "content": f"**Fix Suggestion**\n{report.root_cause.fix_suggestion}"}})
    elements.append({"tag": "div", "text": {"tag": "lark_md", "content": f"**Evidence**\n{report.root_cause.supporting_evidence}"}})

    if report.root_cause.suspect_commit:
        elements.append({"tag": "note", "elements": [{"tag": "plain_text", "content": f"Suspect commit: {report.root_cause.suspect_commit}"}]})

    card: dict = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": color,
        },
        "elements": elements,
    }
    return {"msg_type": "interactive", "card": card}
