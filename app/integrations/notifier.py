from typing import Protocol, runtime_checkable
from app.models.schemas import IncidentReport


@runtime_checkable
class Notifier(Protocol):
    """Notification channel abstraction for incident reports.

    Implementations: SlackNotifier, LarkNotifier, ConsoleNotifier.
    Selected at runtime via notifier_factory based on NOTIFIER_TYPE setting.
    """

    @property
    def name(self) -> str:
        """Stable identifier (e.g. 'slack', 'lark', 'console')."""
        ...

    async def send_report(self, report: IncidentReport) -> bool:
        """Publish the report to the channel. Returns True on success, False on graceful skip (e.g. not configured). Raises on transport errors."""
        ...

    async def health_check(self) -> bool:
        """Whether the channel is currently usable (configured + reachable)."""
        ...
