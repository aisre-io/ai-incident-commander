import httpx
from app.config import get_settings
from app.utils.logger import logger

TDENGINE_REST_PATH = "/rest/sql"

class TDengineClient:
    def __init__(self):
        self._settings = get_settings()
        self._base_url = f"http://{self._settings.tdengine_host}:{self._settings.tdengine_port}"
        self._auth = (self._settings.tdengine_user, self._settings.tdengine_password)
        self._db = self._settings.tdengine_database
        self._ready = False

    async def _ensure_db(self) -> bool:
        if self._ready:
            return True
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.post(
                    f"{self._base_url}{TDENGINE_REST_PATH}",
                    auth=self._auth,
                    content=f"CREATE DATABASE IF NOT EXISTS {self._db}",
                )
                if r.status_code != 200:
                    logger.warning(f"TDengine DB init failed: {r.status_code}")
                    return False
                r2 = await c.post(
                    f"{self._base_url}{TDENGINE_REST_PATH}",
                    auth=self._auth,
                    content=f"CREATE STABLE IF NOT EXISTS {self._db}.incidents (ts TIMESTAMP, event_id VARCHAR(64), title VARCHAR(255), severity VARCHAR(32), service VARCHAR(128), alert_count INT, confidence DOUBLE) TAGS (source VARCHAR(64))",
                )
                if r2.status_code != 200:
                    logger.warning(f"TDengine incidents table init: {r2.status_code}")
                    return False
                r3 = await c.post(
                    f"{self._base_url}{TDENGINE_REST_PATH}",
                    auth=self._auth,
                    content=f"CREATE STABLE IF NOT EXISTS {self._db}.metrics (ts TIMESTAMP, metric_name VARCHAR(64), metric_value DOUBLE) TAGS (service VARCHAR(128))",
                )
                if r3.status_code != 200:
                    logger.warning(f"TDengine metrics table init: {r3.status_code}")
                    return False
                self._ready = True
                logger.info(f"TDengine connected: {self._base_url}/{self._db}")
                return True
        except Exception as e:
            logger.warning(f"TDengine connection failed: {e}")
            return False

    async def execute(self, sql: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.post(
                    f"{self._base_url}{TDENGINE_REST_PATH}/{self._db}",
                    auth=self._auth,
                    content=sql,
                )
                return r.status_code == 200
        except Exception as e:
            logger.warning(f"TDengine execute failed: {e}")
            return False

    async def query(self, sql: str) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.post(
                    f"{self._base_url}{TDENGINE_REST_PATH}/{self._db}",
                    auth=self._auth,
                    content=sql,
                )
                if r.status_code != 200:
                    return []
                data = r.json()
                if data.get("code") != 0:
                    return []
                cols = [col[0] for col in data.get("column_meta", [])]
                return [dict(zip(cols, row)) for row in data.get("data", [])]
        except Exception as e:
            logger.warning(f"TDengine query failed: {e}")
            return []

    async def store_incident(self, event_id: str, title: str, severity: str, service: str, alert_count: int, confidence: float = 0.0):
        if not await self._ensure_db():
            return
        sql = f"INSERT INTO {self._db}.incidents USING {self._db}.incidents TAGS ('rca') VALUES (NOW, '{event_id}', '{title.replace(chr(39), chr(39)+chr(39))}', '{severity}', '{service}', {alert_count}, {confidence})"
        await self.execute(sql)

    async def query_metrics(self, service: str, minutes_back: int = 60) -> list[dict]:
        if not await self._ensure_db():
            return []
        sql = f"SELECT ts, metric_name, metric_value FROM {self._db}.metrics WHERE service = '{service}' AND ts >= NOW - {minutes_back}m ORDER BY ts DESC LIMIT 100"
        return await self.query(sql)

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.post(
                    f"{self._base_url}{TDENGINE_REST_PATH}",
                    auth=self._auth,
                    content="SELECT SERVER_VERSION()",
                )
                return r.status_code == 200
        except Exception:
            return False
