"""Unit tests for payload parsing and message texts (no Home Assistant needed)."""

from __future__ import annotations

import pytest
import voluptuous as vol

from custom_components.zabbix_notify.payload import ZabbixEvent, parse_event
from custom_components.zabbix_notify.texts import (
    build_message,
    resolve_language,
    severity_name,
    type_name,
    zabbix_link,
)


def test_parse_minimal_and_defaults():
    event = parse_event({"kind": "problem", "event_id": 12})
    assert event.event_id == "12"
    assert event.severity == 0
    assert event.tags == []


def test_parse_cleans_values():
    event = parse_event(
        {
            "kind": "update",
            "event_id": "5",
            "severity": "9",
            "duration": "*UNKNOWN*",
            "tags": [{"tag": "a", "value": 1}, {"nope": True}, "x"],
        }
    )
    assert event.severity == 5  # clamped
    assert event.duration == ""
    assert event.tags == [{"tag": "a", "value": "1"}]


@pytest.mark.parametrize(
    "data",
    [
        [],
        {"event_id": "1"},
        {"kind": "bogus", "event_id": "1"},
        {"kind": "problem"},  # event_id missing
    ],
)
def test_parse_rejects_invalid(data):
    with pytest.raises(vol.Invalid):
        parse_event(data)


def test_test_kind_needs_no_event_id():
    assert parse_event({"kind": "test"}).kind == "test"


def test_resolve_language():
    assert resolve_language("de", "en") == "de"
    assert resolve_language("auto", "de-AT") == "de"
    assert resolve_language(None, "fr") == "en"


def test_severity_names():
    assert severity_name(4, "de") == "Hoch"
    assert severity_name(5, "en") == "Disaster"
    assert severity_name(99, "en") == "Disaster"


def test_problem_text_german():
    event = ZabbixEvent(
        kind="problem", event_id="1", name="CPU hoch", host="srv01", severity=4,
        opdata="Last: 9.1",
    )
    title, message = build_message(event, "de")
    assert title == "Hoch: srv01"
    assert message == "CPU hoch\nLast: 9.1"


def test_update_text_translates_actions():
    event = ZabbixEvent(
        kind="update", event_id="1", name="CPU high", host="srv01",
        update_action="acknowledged, changed severity from Average to High",
        update_user="Dominik", update_message="Looking into it",
    )
    title, message = build_message(event, "de")
    assert title == "Aktualisiert: srv01"
    assert message.splitlines() == [
        "CPU high",
        "Bestätigt, Schweregrad von Durchschnitt auf Hoch geändert von Dominik",
        "Kommentar: Looking into it",
    ]
    _, english = build_message(event, "en")
    assert "Acknowledged, Severity changed from Average to High by Dominik" in english


def test_unknown_action_passes_through():
    event = ZabbixEvent(kind="update", event_id="1", name="x", host="h", update_action="moved to mars")
    _, message = build_message(event, "de")
    assert "Moved to mars" in message


def test_resolved_text():
    event = ZabbixEvent(kind="resolved", event_id="1", name="CPU high", host="srv01", duration="5m")
    assert build_message(event, "en") == ("Resolved: srv01", "CPU high\nDuration: 5m")
    assert build_message(event, "de")[0] == "Behoben: srv01"


def test_missing_host_still_gives_title():
    event = ZabbixEvent(kind="resolved", event_id="1", name="x")
    assert build_message(event, "de")[0] == "Behoben"


def test_type_names():
    assert type_name("update", "de") == "Zabbix: Problem aktualisiert"
    assert type_name("resolved", "en") == "Zabbix: Problem resolved"


def test_zabbix_link():
    event = ZabbixEvent(
        kind="problem", event_id="9", trigger_id="3", zabbix_url="https://z.example/"
    )
    assert zabbix_link(event) == "https://z.example/tr_events.php?triggerid=3&eventid=9"
    event.trigger_id = ""
    assert zabbix_link(event) == "https://z.example/zabbix.php?action=problem.view"
    event.zabbix_url = "not a url"
    assert zabbix_link(event) is None
