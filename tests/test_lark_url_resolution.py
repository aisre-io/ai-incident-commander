"""Regression tests for Lark webhook URL resolution.

Covers the bug where pasting the full Feishu webhook URL (as copied from
group settings) would be re-prefixed, producing a malformed double-prefixed
URL like ``https://open.feishu.cn/open-apis/bot/v2/hook/https://open.feishu.cn/...``.

These tests guard against that bug returning.
"""
import pytest

from app.integrations.lark_bot import _resolve_webhook_url


_LARK_CN_BASE = "https://open.feishu.cn/open-apis/bot/v2/hook"
_LARK_INTL_BASE = "https://open.larksuite.com/open-apis/bot/v2/hook"


class TestBareToken:
    """User pastes only the token portion (less common but supported)."""

    def test_cn_bare_token(self):
        url = _resolve_webhook_url(_LARK_CN_BASE, "tok-abc")
        assert url == f"{_LARK_CN_BASE}/tok-abc"

    def test_intl_bare_token(self):
        url = _resolve_webhook_url(_LARK_INTL_BASE, "tok-xyz")
        assert url == f"{_LARK_INTL_BASE}/tok-xyz"

    def test_uuid_bare_token(self):
        uuid = "51b2a635-d461-4eec-9d41-c96db32e0e8d"
        url = _resolve_webhook_url(_LARK_CN_BASE, uuid)
        assert url == f"{_LARK_CN_BASE}/{uuid}"


class TestFullUrl:
    """User pastes the full webhook URL as copied from Feishu group settings (the common case)."""

    def test_cn_full_url_passes_through_unchanged(self):
        full = "https://open.feishu.cn/open-apis/bot/v2/hook/51b2a635-d461-4eec-9d41-c96db32e0e8d"
        url = _resolve_webhook_url(_LARK_CN_BASE, full)
        assert url == full
        # The bug would have produced a double-prefixed URL — assert that did NOT happen.
        assert not url.startswith(f"{_LARK_CN_BASE}/{_LARK_CN_BASE}")

    def test_intl_full_url_passes_through_unchanged(self):
        full = "https://open.larksuite.com/open-apis/bot/v2/hook/some-intl-token"
        url = _resolve_webhook_url(_LARK_INTL_BASE, full)
        assert url == full

    def test_full_url_with_cross_region_base_does_not_double_prefix(self):
        """Even if user pastes intl URL but region is CN (mismatch), must not concatenate."""
        intl_url = "https://open.larksuite.com/open-apis/bot/v2/hook/abc"
        url = _resolve_webhook_url(_LARK_CN_BASE, intl_url)
        assert url == intl_url


class TestWhitespace:
    def test_strips_leading_trailing_whitespace(self):
        url = _resolve_webhook_url(_LARK_CN_BASE, "  tok-ws  \n")
        assert url == f"{_LARK_CN_BASE}/tok-ws"

    def test_strips_whitespace_around_full_url(self):
        full = "https://open.feishu.cn/open-apis/bot/v2/hook/x"
        url = _resolve_webhook_url(_LARK_CN_BASE, f"  {full}  ")
        assert url == full


class TestProtocolVariants:
    def test_http_full_url_also_passes_through(self):
        # In dev, some users may have http (not https) URLs.
        url = _resolve_webhook_url(_LARK_CN_BASE, "http://example.com/hook/x")
        assert url == "http://example.com/hook/x"

    def test_url_with_extra_path_segments(self):
        # Future-proof: if Lark adds a path segment, the full URL still wins.
        weird = "https://open.feishu.cn/open-apis/bot/v2/hook/extra/path/tok"
        url = _resolve_webhook_url(_LARK_CN_BASE, weird)
        assert url == weird


class TestRegressionBugShape:
    """The exact malformed URL we saw in the bug report must never appear."""

    def test_buggy_double_prefix_shape_rejected(self):
        full = "https://open.feishu.cn/open-apis/bot/v2/hook/abc-token"
        result = _resolve_webhook_url(_LARK_CN_BASE, full)
        # Buggy output would be: https://open.feishu.cn/open-apis/bot/v2/hook/https://open.feishu.cn/open-apis/bot/v2/hook/abc-token
        assert result.count("https://") == 1
        assert "open-apis/bot/v2/hook/https" not in result
