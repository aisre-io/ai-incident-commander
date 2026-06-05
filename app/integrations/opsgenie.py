import httpx
from app.config import get_settings
from app.utils.logger import logger


class OpsgenieClient:
    def __init__(self):
        settings = get_settings()
        self._api_key = settings.opsgenie_api_key
        self._base_url = "https://api.opsgenie.com/v2"

    async def get_alert(self, alert_id: str) -> dict | None:
        if not self._api_key:
            return None
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base_url}/alerts/{alert_id}",
                headers={"Authorization": f"GenieKey {self._api_key}"},
            )
            resp.raise_for_status()
            return resp.json().get("data")
