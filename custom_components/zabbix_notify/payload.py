"""Parsing and validation of the JSON payload sent by the Zabbix media type."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import voluptuous as vol

from .const import KIND_TEST, KINDS

_UNKNOWN = "*UNKNOWN*"


def _text(limit: int):
    """Return a validator that turns any value into a trimmed, length-limited string."""

    def validate(value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        if text == _UNKNOWN:
            return ""
        return text[:limit]

    return validate


def _severity(value: Any) -> int:
    """Clamp a severity into 0..5, falling back to 0 for anything unusable."""
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return 0
    return max(0, min(5, number))


def _tags(value: Any) -> list[dict[str, str]]:
    """Keep only well-formed tag objects."""
    if not isinstance(value, list):
        return []
    tags: list[dict[str, str]] = []
    for item in value[:50]:
        if isinstance(item, dict) and item.get("tag"):
            tags.append(
                {"tag": _text(255)(item["tag"]), "value": _text(255)(item.get("value"))}
            )
    return tags


PAYLOAD_SCHEMA = vol.Schema(
    {
        vol.Required("kind"): vol.In(KINDS),
        vol.Optional("event_id", default=""): _text(64),
        vol.Optional("trigger_id", default=""): _text(64),
        vol.Optional("event_name", default=""): _text(1000),
        vol.Optional("host", default=""): _text(255),
        vol.Optional("severity", default=0): _severity,
        vol.Optional("opdata", default=""): _text(1000),
        vol.Optional("update_action", default=""): _text(500),
        vol.Optional("update_message", default=""): _text(2000),
        vol.Optional("update_user", default=""): _text(255),
        vol.Optional("duration", default=""): _text(100),
        vol.Optional("age", default=""): _text(100),
        vol.Optional("event_time", default=""): _text(100),
        vol.Optional("zabbix_url", default=""): _text(500),
        vol.Optional("tags", default=list): _tags,
    },
    extra=vol.ALLOW_EXTRA,
)


@dataclass(slots=True)
class ZabbixEvent:
    """One validated Zabbix event."""

    kind: str
    event_id: str = ""
    trigger_id: str = ""
    name: str = ""
    host: str = ""
    severity: int = 0
    opdata: str = ""
    update_action: str = ""
    update_message: str = ""
    update_user: str = ""
    duration: str = ""
    age: str = ""
    event_time: str = ""
    zabbix_url: str = ""
    tags: list[dict[str, str]] = field(default_factory=list)


def parse_event(data: Any) -> ZabbixEvent:
    """Validate a raw payload and return a ZabbixEvent (raises vol.Invalid)."""
    if not isinstance(data, dict):
        raise vol.Invalid("payload must be a JSON object")
    validated = PAYLOAD_SCHEMA(data)
    if validated["kind"] != KIND_TEST and not validated["event_id"]:
        raise vol.Invalid("event_id is required")
    return ZabbixEvent(
        kind=validated["kind"],
        event_id=validated["event_id"],
        trigger_id=validated["trigger_id"],
        name=validated["event_name"],
        host=validated["host"],
        severity=validated["severity"],
        opdata=validated["opdata"],
        update_action=validated["update_action"],
        update_message=validated["update_message"],
        update_user=validated["update_user"],
        duration=validated["duration"],
        age=validated["age"],
        event_time=validated["event_time"],
        zabbix_url=validated["zabbix_url"],
        tags=validated["tags"],
    )
