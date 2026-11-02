#!/usr/bin/env python3
"""Generate zabbix/media_type_home_assistant.yaml from ha_notify_webhook.js.

Run from the repository root:  python zabbix/build_media_type.py
"""

from __future__ import annotations

from pathlib import Path
import textwrap

HERE = Path(__file__).resolve().parent

# (parameter name, Zabbix macro)
PARAMETERS = [
    ("url", "{$HA_NOTIFY_URL}"),
    ("token", "{$HA_NOTIFY_TOKEN}"),
    ("http_proxy", "{$HA_NOTIFY_PROXY}"),
    ("zabbix_url", "{$ZABBIX.URL}"),
    ("event_source", "{EVENT.SOURCE}"),
    ("event_value", "{EVENT.VALUE}"),
    ("event_update_status", "{EVENT.UPDATE.STATUS}"),
    ("event_id", "{EVENT.ID}"),
    ("trigger_id", "{TRIGGER.ID}"),
    ("event_name", "{EVENT.NAME}"),
    ("event_nseverity", "{EVENT.NSEVERITY}"),
    ("host_name", "{HOST.NAME}"),
    ("event_opdata", "{EVENT.OPDATA}"),
    ("event_update_action", "{EVENT.UPDATE.ACTION}"),
    ("event_update_message", "{EVENT.UPDATE.MESSAGE}"),
    ("event_update_user", "{USER.FULLNAME}"),
    ("event_age", "{EVENT.AGE}"),
    ("event_duration", "{EVENT.DURATION}"),
    ("event_time", "{EVENT.DATE} {EVENT.TIME}"),
    ("event_tagsjson", "{EVENT.TAGSJSON}"),
]

DESCRIPTION = (
    "Sends problem, update and recovery events to the Zabbix Notify "
    "integration in Home Assistant. https://github.com/dominikramachers/HA-Zabbix-Notify"
)


def build() -> str:
    script = (HERE / "ha_notify_webhook.js").read_text(encoding="utf-8").rstrip("\n")
    lines = [
        "zabbix_export:",
        "  version: '7.0'",
        "  media_types:",
        "    - name: 'Home Assistant (Zabbix Notify)'",
        "      type: WEBHOOK",
        "      parameters:",
    ]
    for name, macro in PARAMETERS:
        lines.append(f"        - name: {name}")
        lines.append(f"          value: '{macro}'")
    lines.append("      script: |")
    lines.append(textwrap.indent(script, " " * 8))
    lines.append("      timeout: 30s")
    lines.append(f"      description: '{DESCRIPTION}'")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    target = HERE / "media_type_home_assistant.yaml"
    target.write_text(build(), encoding="utf-8")
    print(f"wrote {target}")
