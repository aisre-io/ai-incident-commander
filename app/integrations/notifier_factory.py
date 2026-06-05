from typing import Optional
from app.config import get_settings
from app.integrations.notifier import Notifier
from app.utils.logger import logger

_cached_notifier: Optional[Notifier] = None


class ConsoleNotifier:
    """Stdout fallback for local dev and tests. Always available, never raises."""

    @property
    def name(self) -> str:
        return "console"

    async def health_check(self) -> bool:
        return True

    async def send_report(self, report) -> bool:
        logger.info(
            f"[CONSOLE NOTIFIER] Incident {report.event_id} | "
            f"service={report.service} severity={report.severity} "
            f"confidence={report.confidence_score:.2f}"
        )
        logger.info(f"  Root cause: {report.root_cause.root_cause}")
        return True


def get_notifier() -> Notifier:
    """Return the configured Notifier (cached singleton).

    NOTIFIER_TYPE values: 'lark' (default), 'slack', 'console'.
    """
    global _cached_notifier
    if _cached_notifier is not None:
        return _cached_notifier

    settings = get_settings()
    notifier_type = (settings.notifier_type or "lark").lower()

    if notifier_type == "slack":
        from app.integrations.slack_bot import SlackNotifier
        _cached_notifier = SlackNotifier()
    elif notifier_type == "lark":
        from app.integrations.lark_bot import LarkNotifier
        _cached_notifier = LarkNotifier()
    elif notifier_type == "console":
        _cached_notifier = ConsoleNotifier()
    else:
        logger.warning(f"Unknown NOTIFIER_TYPE={notifier_type!r}, falling back to console")
        _cached_notifier = ConsoleNotifier()

    logger.info(f"Notifier initialized: {_cached_notifier.name}")
    return _cached_notifier


def reset_notifier_cache() -> None:
    """Test helper. Re-read settings on next get_notifier() call."""
    global _cached_notifier
    _cached_notifier = None
