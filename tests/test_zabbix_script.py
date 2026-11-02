"""Tests for the Zabbix media type script, run through Node with a mocked runtime."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / "tests" / "script_harness.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

OK_RESPONSE = json.dumps({"ok": True, "source": "ha-zabbix-notify"})

BASE = {
    "url": "http://ha.example:8123/api/webhook/abc",
    "token": "secret-token",
    "http_proxy": "{$HA_NOTIFY_PROXY}",
    "zabbix_url": "https://zabbix.example",
    "event_source": "0",
    "event_value": "1",
    "event_update_status": "0",
    "event_id": "1001",
    "trigger_id": "77",
    "event_name": "High CPU on srv01",
    "event_nseverity": "4",
    "host_name": "srv01",
    "event_opdata": "load: 9.1",
    "event_update_action": "{EVENT.UPDATE.ACTION}",
    "event_update_message": "{EVENT.UPDATE.MESSAGE}",
    "event_update_user": "{USER.FULLNAME}",
    "event_age": "1m",
    "event_duration": "*UNKNOWN*",
    "event_time": "2026.11.02 10:00:00",
    "event_tagsjson": '[{"tag":"scope","value":"capacity"}]',
}


def run_script(params: dict, response: str = OK_RESPONSE, status: int = 200) -> dict:
    out = subprocess.run(
        ["node", str(HARNESS), json.dumps(params), response, str(status)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout)


def test_problem_payload():
    result = run_script(BASE)
    assert result["error"] is None
    request = result["request"]
    assert request["url"] == BASE["url"]
    assert "X-Zabbix-Notify-Token: secret-token" in request["headers"]
    assert request["proxy"] is None  # unresolved macro must not become a proxy
    body = request["body"]
    assert body["kind"] == "problem"
    assert body["event_id"] == "1001"
    assert body["host"] == "srv01"
    assert body["severity"] == "4"
    assert body["opdata"] == "load: 9.1"
    assert body["update_action"] == ""  # unresolved macro dropped
    assert body["duration"] == ""  # *UNKNOWN* dropped
    assert body["tags"] == [{"tag": "scope", "value": "capacity"}]


def test_update_and_resolved_kinds():
    update = {**BASE, "event_update_status": "1", "event_update_action": "acknowledged"}
    assert run_script(update)["request"]["body"]["kind"] == "update"
    resolved = {**BASE, "event_value": "0", "event_duration": "5m 2s"}
    body = run_script(resolved)["request"]["body"]
    assert body["kind"] == "resolved"
    assert body["duration"] == "5m 2s"


def test_test_dialog_sends_test_kind():
    params = {**BASE, "event_id": "{EVENT.ID}"}
    assert run_script(params)["request"]["body"] == {"version": 1, "kind": "test"}


def test_unsupported_event_source():
    result = run_script({**BASE, "event_source": "1"})
    assert "Unsupported event source" in result["error"]
    assert result["request"]["url"] is None


def test_missing_settings_are_reported():
    assert "url" in run_script({**BASE, "url": "{$HA_NOTIFY_URL}"})["error"]
    assert "token" in run_script({**BASE, "token": "{$HA_NOTIFY_TOKEN}"})["error"]


def test_http_error_fails():
    result = run_script(BASE, response="denied", status=401)
    assert "HTTP 401" in result["error"]


def test_empty_200_means_wrong_webhook_id():
    result = run_script(BASE, response="", status=200)
    assert "webhook ID" in result["error"]


def test_proxy_is_used_when_set():
    result = run_script({**BASE, "http_proxy": "http://proxy.example:3128"})
    assert result["request"]["proxy"] == "http://proxy.example:3128"


def test_yaml_matches_script_file():
    """The importable media type must embed the current script."""
    data = yaml.safe_load((ROOT / "zabbix" / "media_type_home_assistant.yaml").read_text())
    media = data["zabbix_export"]["media_types"][0]
    script = (ROOT / "zabbix" / "ha_notify_webhook.js").read_text()
    assert media["type"] == "WEBHOOK"
    assert media["script"].rstrip("\n") == script.rstrip("\n")
    names = [p["name"] for p in media["parameters"]]
    assert len(names) == len(set(names))
    assert {"url", "token", "event_id", "event_value", "event_update_status"} <= set(names)
