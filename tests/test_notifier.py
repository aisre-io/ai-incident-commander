import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.integrations.notifier import Notifier
from app.integrations.lark_bot import LarkNotifier, _build_card_payload
from app.integrations.notifier_factory import (
    get_notifier,
    reset_notifier_cache,
    ConsoleNotifier,
)
from app.integrations.slack_bot import SlackNotifier
from app.config import get_settings


@pytest.fixture(autouse=True)
def _reset_factory_cache():
    reset_notifier_cache()
    yield
    reset_notifier_cache()


class TestProtocolConformance:
    def test_lark_is_notifier(self):
        assert isinstance(LarkNotifier(), Notifier)

    def test_slack_is_notifier(self):
        assert isinstance(SlackNotifier(), Notifier)

    def test_console_is_notifier(self):
        assert isinstance(ConsoleNotifier(), Notifier)

    def test_names_are_stable(self):
        assert LarkNotifier().name == "lark"
        assert SlackNotifier().name == "slack"
        assert ConsoleNotifier().name == "console"


class TestLarkCardPayload:
    def test_card_has_required_structure(self, sample_report):
        settings = get_settings()
        payload = _build_card_payload(sample_report, settings)

        assert payload["msg_type"] == "interactive"
        assert "card" in payload
        card = payload["card"]
        assert "header" in card
        assert "title" in card["header"]
        assert sample_report.title in card["header"]["title"]["content"]
        assert isinstance(card["elements"], list)
        assert len(card["elements"]) >= 4

    def test_critical_severity_uses_red_color(self, sample_report):
        sample_report.severity = "critical"
        settings = get_settings()
        payload = _build_card_payload(sample_report, settings)
        assert payload["card"]["header"]["template"] == "red"

    def test_warning_severity_uses_yellow(self, sample_report):
        sample_report.severity = "warning"
        settings = get_settings()
        payload = _build_card_payload(sample_report, settings)
        assert payload["card"]["header"]["template"] == "yellow"

    def test_unknown_severity_defaults_to_blue(self, sample_report):
        sample_report.severity = "weird"
        settings = get_settings()
        payload = _build_card_payload(sample_report, settings)
        assert payload["card"]["header"]["template"] == "blue"

    def test_suspect_commit_renders_as_note(self, sample_report):
        settings = get_settings()
        payload = _build_card_payload(sample_report, settings)
        elements = payload["card"]["elements"]
        notes = [e for e in elements if e.get("tag") == "note"]
        assert len(notes) == 1
        assert sample_report.root_cause.suspect_commit in notes[0]["elements"][0]["content"]

    def test_no_suspect_commit_omits_note(self, sample_report):
        sample_report.root_cause.suspect_commit = None
        settings = get_settings()
        payload = _build_card_payload(sample_report, settings)
        notes = [e for e in payload["card"]["elements"] if e.get("tag") == "note"]
        assert notes == []


class TestLarkNotifierSend:
    @pytest.mark.asyncio
    async def test_returns_false_when_webhook_url_missing(self, sample_report, monkeypatch):
        monkeypatch.setattr(get_settings(), "lark_webhook_url", "")
        result = await LarkNotifier().send_report(sample_report)
        assert result is False

    @pytest.mark.asyncio
    async def test_posts_to_cn_endpoint_by_default(self, sample_report, monkeypatch):
        monkeypatch.setattr(get_settings(), "lark_webhook_url", "tok-abc")
        monkeypatch.setattr(get_settings(), "lark_region", "cn")

        with patch("app.integrations.lark_bot.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {"code": 0, "msg": "success"}
            mock_client.post.return_value = resp
            mock_client_cls.return_value = mock_client

            result = await LarkNotifier().send_report(sample_report)

        assert result is True
        call = mock_client.post.call_args
        assert call.args[0].startswith("https://open.feishu.cn/open-apis/bot/v2/hook/tok-abc")

    @pytest.mark.asyncio
    async def test_posts_to_intl_endpoint_when_configured(self, sample_report, monkeypatch):
        monkeypatch.setattr(get_settings(), "lark_webhook_url", "tok-xyz")
        monkeypatch.setattr(get_settings(), "lark_region", "intl")

        with patch("app.integrations.lark_bot.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {"code": 0, "msg": "success"}
            mock_client.post.return_value = resp
            mock_client_cls.return_value = mock_client

            await LarkNotifier().send_report(sample_report)

        call = mock_client.post.call_args
        assert call.args[0].startswith("https://open.larksuite.com/open-apis/bot/v2/hook/tok-xyz")

    @pytest.mark.asyncio
    async def test_raises_on_lark_business_error(self, sample_report, monkeypatch):
        monkeypatch.setattr(get_settings(), "lark_webhook_url", "tok-err")

        with patch("app.integrations.lark_bot.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {"code": 99991663, "msg": "invalid token"}
            mock_client.post.return_value = resp
            mock_client_cls.return_value = mock_client

            with pytest.raises(RuntimeError, match="invalid token"):
                await LarkNotifier().send_report(sample_report)

    @pytest.mark.asyncio
    async def test_health_check_reflects_url_config(self, monkeypatch):
        monkeypatch.setattr(get_settings(), "lark_webhook_url", "")
        assert await LarkNotifier().health_check() is False
        monkeypatch.setattr(get_settings(), "lark_webhook_url", "tok-set")
        assert await LarkNotifier().health_check() is True


class TestFactory:
    def test_lark_is_default(self, monkeypatch):
        monkeypatch.setattr(get_settings(), "notifier_type", "lark")
        assert get_notifier().name == "lark"

    def test_returns_slack(self, monkeypatch):
        monkeypatch.setattr(get_settings(), "notifier_type", "slack")
        assert get_notifier().name == "slack"

    def test_returns_console(self, monkeypatch):
        monkeypatch.setattr(get_settings(), "notifier_type", "console")
        assert get_notifier().name == "console"

    def test_unknown_falls_back_to_console(self, monkeypatch):
        monkeypatch.setattr(get_settings(), "notifier_type", "weird-channel")
        assert get_notifier().name == "console"

    def test_singleton_caching(self, monkeypatch):
        monkeypatch.setattr(get_settings(), "notifier_type", "lark")
        n1 = get_notifier()
        n2 = get_notifier()
        assert n1 is n2

    def test_reset_clears_cache(self, monkeypatch):
        monkeypatch.setattr(get_settings(), "notifier_type", "lark")
        n1 = get_notifier()
        reset_notifier_cache()
        monkeypatch.setattr(get_settings(), "notifier_type", "console")
        assert get_notifier().name == "console"


class TestConsoleNotifier:
    @pytest.mark.asyncio
    async def test_always_healthy(self, sample_report):
        assert await ConsoleNotifier().health_check() is True
        assert await ConsoleNotifier().send_report(sample_report) is True
