"""Unit tests for the icon option validation."""

from __future__ import annotations

import pytest

from custom_components.zabbix_notify.icons import is_valid_icon


@pytest.mark.parametrize(
    "value",
    ["", "   ", "mdi:server", "/local/zabbix.png", "https://example.org/z.png", "data:image/png;base64,iVBORw0KGgo="],
)
def test_valid(value):
    assert is_valid_icon(value)


@pytest.mark.parametrize(
    "value",
    ["javascript:alert(1)", "//evil.example/x.png", "data:text/html;base64,AAAA", "<img>", "not an icon", "/" + "x" * 20001],
)
def test_invalid(value):
    assert not is_valid_icon(value)
