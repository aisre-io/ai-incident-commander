from slack_bolt import App
from app.config import get_settings
from app.models.schemas import IncidentReport
from app.utils.logger import logger

_slack_app: App | None = None


def get_slack_app() -> App | None:
    global _slack_app
    if _slack_app is not None:
        return _slack_app

    settings = get_settings()
    if not settings.slack_bot_token or not settings.slack_signing_secret:
        logger.warning("Slack credentials not configured, Slack bot disabled")
        return None

    _slack_app = App(token=settings.slack_bot_token, signing_secret=settings.slack_signing_secret)

    @_slack_app.event("app_mention")
    def handle_mention(event, say):
        logger.info(f"Slack mention: {event.get('text', '')}")
        say("Hello! I'm AI Incident Commander. Send me an alert and I'll analyze the root cause.")

    @_slack_app.event("message")
    def handle_message(event, say):
        text = event.get("text", "")
        if "root cause" in text.lower() or "rca" in text.lower():
            say("Analyzing... I'll be back with a root cause report shortly.")

    return _slack_app


class SlackNotifier:
    """Slack implementation of the Notifier protocol. Backed by Bolt App.client.chat_postMessage."""

    @property
    def name(self) -> str:
        return "slack"

    async def health_check(self) -> bool:
        return self._get_app() is not None

    async def send_report(self, report: IncidentReport) -> bool:
        app = self._get_app()
        if not app:
            logger.warning("Slack not configured, skipping notification")
            return False

        blocks = _build_report_blocks(report)
        try:
            app.client.chat_postMessage(
                channel="#incidents",
                text=f"Incident Report: {report.title}",
                blocks=blocks,
            )
            logger.info(f"Incident report posted to Slack for event {report.event_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to post to Slack: {e}")
            raise

    def _get_app(self) -> App | None:
        return get_slack_app()


async def post_incident_report(report: IncidentReport) -> bool:
    """Backward-compatible wrapper. Prefer get_notifier().send_report(report) in new code."""
    return await SlackNotifier().send_report(report)


def _build_report_blocks(report: IncidentReport) -> list[dict]:
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Incident Report: {report.title}", "emoji": True},
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Service:* {report.service}"},
                {"type": "mrkdwn", "text": f"*Severity:* {report.severity}"},
                {"type": "mrkdwn", "text": f"*Alert Count:* {report.alert_count}"},
                {"type": "mrkdwn", "text": f"*Confidence:* {report.confidence_score * 100:.0f}%"},
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Root Cause:*\n{report.root_cause.root_cause}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Fix Suggestion:*\n{report.root_cause.fix_suggestion}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Evidence:*\n{report.root_cause.supporting_evidence}"},
        },
    ]

    if report.root_cause.suspect_commit:
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"Suspect commit: `{report.root_cause.suspect_commit}`"}],
        })

    return blocks
