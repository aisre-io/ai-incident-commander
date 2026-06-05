import httpx
from app.config import get_settings
from app.utils.logger import logger


class PagerDutyClient:
    def __init__(self):
        settings = get_settings()
        self._api_key = settings.pagerduty_api_key
        self._base_url = "https://api.pagerduty.com"

    async def get_oncall(self, schedule_id: str) -> str | None:
        if not self._api_key:
            return None
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base_url}/schedules/{schedule_id}/users",
                headers={"Authorization": f"Token token={self._api_key}", "Accept": "application/vnd.pagerduty+json;version=2"},
            )
            resp.raise_for_status()
            data = resp.json()
            users = data.get("users", [])
            return users[0]["email"] if users else None
