import pytest
from unittest.mock import patch, AsyncMock
from app.integrations.tdengine import TDengineClient


@pytest.fixture
def td():
    return TDengineClient()


@pytest.mark.asyncio
async def test_health_check_ok(td):
    with patch("httpx.AsyncClient") as mock:
        instance = mock.return_value.__aenter__.return_value
        instance.post = AsyncMock(return_value=AsyncMock(status_code=200))
        assert await td.health_check() is True


@pytest.mark.asyncio
async def test_health_check_fail(td):
    with patch("httpx.AsyncClient") as mock:
        instance = mock.return_value.__aenter__.return_value
        instance.post = AsyncMock(side_effect=Exception("conn refused"))
        assert await td.health_check() is False


@pytest.mark.asyncio
async def test_query_returns_rows(td):
    with patch("httpx.AsyncClient") as mock:
        instance = mock.return_value.__aenter__.return_value
        instance.post = AsyncMock(return_value=AsyncMock(
            status_code=200,
            json=lambda: {
                "code": 0,
                "column_meta": [["ts", 9, 8], ["metric_name", 10, 64], ["metric_value", 6, 0]],
                "data": [["2026-06-18T10:00:00", "cpu", 85.0], ["2026-06-18T10:01:00", "mem", 72.0]],
                "rows": 2,
            },
        ))
        td._ready = True
        rows = await td.query("SELECT * FROM metrics LIMIT 2")
        assert len(rows) == 2
        assert rows[0]["metric_name"] == "cpu"
        assert rows[0]["metric_value"] == 85.0
        assert rows[1]["metric_name"] == "mem"


@pytest.mark.asyncio
async def test_store_incident_sql(td):
    with patch("httpx.AsyncClient") as mock:
        instance = mock.return_value.__aenter__.return_value
        instance.post = AsyncMock(return_value=AsyncMock(status_code=200))
        await td.store_incident("evt-001", "CPU spike", "critical", "api-gateway", 5, 0.92)
        calls = instance.post.call_args_list
        assert len(calls) >= 2
        last_sql = calls[-1].kwargs.get("content", "")
        assert "INSERT" in last_sql
        assert "evt-001" in last_sql


@pytest.mark.asyncio
async def test_execute_create_db(td):
    with patch("httpx.AsyncClient") as mock:
        instance = mock.return_value.__aenter__.return_value
        instance.post = AsyncMock(return_value=AsyncMock(status_code=200))
        ok = await td.execute("CREATE DATABASE IF NOT EXISTS test")
        assert ok is True


@pytest.mark.asyncio
async def test_execute_failure(td):
    with patch("httpx.AsyncClient") as mock:
        instance = mock.return_value.__aenter__.return_value
        instance.post = AsyncMock(return_value=AsyncMock(status_code=500))
        ok = await td.execute("BROKEN SQL")
        assert ok is False


@pytest.mark.asyncio
async def test_query_metrics_empty(td):
    with patch("httpx.AsyncClient") as mock:
        instance = mock.return_value.__aenter__.return_value
        instance.post = AsyncMock(return_value=AsyncMock(
            status_code=200,
            json=lambda: {"code": 0, "column_meta": [], "data": [], "rows": 0},
        ))
        td._ready = True
        rows = await td.query_metrics("api-gateway")
        assert rows == []
