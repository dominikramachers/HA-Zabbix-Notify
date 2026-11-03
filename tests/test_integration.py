"""Integration tests: webhook, state tracking, delivery paths, persistence."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import voluptuous as vol
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_mock_service,
)

from homeassistant.core import HomeAssistant

from custom_components.zabbix_notify.const import (
    CONF_TOKEN,
    CONF_WEBHOOK_ID,
    DOMAIN,
    EVENT_ZABBIX,
    OPT_NOTIFY_PROBLEM,
    TOKEN_HEADER,
)

WEBHOOK_ID = "whtest0123456789"
TOKEN = "unit-test-token"
OPEN_SENSOR = "sensor.zabbix_open_problems"
LAST_SENSOR = "sensor.zabbix_last_event_received"


def payload(kind: str = "problem", **overrides) -> dict:
    data = {
        "version": 1,
        "kind": kind,
        "event_id": "1001",
        "trigger_id": "77",
        "event_name": "High CPU on srv01",
        "host": "srv01",
        "severity": "4",
        "opdata": "load: 9.1",
        "zabbix_url": "https://zabbix.example",
    }
    data.update(overrides)
    return data


@pytest.fixture
async def setup(hass: HomeAssistant):
    """Return a factory that sets up the integration and unloads it afterwards."""
    entries: list[MockConfigEntry] = []

    async def _setup(options: dict | None = None) -> MockConfigEntry:
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Zabbix",
            data={CONF_WEBHOOK_ID: WEBHOOK_ID, CONF_TOKEN: TOKEN},
            options=options or {},
        )
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        entries.append(entry)
        return entry

    yield _setup
    for entry in entries:
        await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def post(client, data, token: str | None = TOKEN):
    headers = {TOKEN_HEADER: token} if token else {}
    return await client.post(f"/api/webhook/{WEBHOOK_ID}", json=data, headers=headers)


async def test_rejects_missing_and_wrong_token(hass, hass_client_no_auth, setup):
    await setup()
    client = await hass_client_no_auth()
    assert (await post(client, payload(), token=None)).status == 401
    assert (await post(client, payload(), token="wrong")).status == 401
    assert hass.states.get(OPEN_SENSOR).state == "0"


async def test_bearer_token_is_accepted(hass, hass_client_no_auth, setup):
    await setup()
    client = await hass_client_no_auth()
    response = await client.post(
        f"/api/webhook/{WEBHOOK_ID}",
        json=payload(),
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert response.status == 200


async def test_invalid_input(hass, hass_client_no_auth, setup):
    await setup()
    client = await hass_client_no_auth()
    bad_json = await client.post(
        f"/api/webhook/{WEBHOOK_ID}", data="{not json", headers={TOKEN_HEADER: TOKEN}
    )
    assert bad_json.status == 400
    assert (await post(client, {"kind": "problem"})).status == 400  # no event_id
    assert (await post(client, [1, 2])).status == 400


async def test_lifecycle_standalone(hass, hass_client_no_auth, setup):
    """Problem, update, recovery without a notification center."""
    await setup()
    client = await hass_client_no_auth()
    events = async_capture_events(hass, EVENT_ZABBIX)

    with patch(
        "custom_components.zabbix_notify.hub.persistent_notification"
    ) as persistent:
        response = await post(client, payload())
        assert response.status == 200
        body = await response.json()
        assert body["ok"] is True and body["open_problems"] == 1
        await hass.async_block_till_done()

        state = hass.states.get(OPEN_SENSOR)
        assert state.state == "1"
        assert state.attributes["by_severity"]["high"] == 1
        assert state.attributes["problems"][0]["host"] == "srv01"
        persistent.async_create.assert_called_once()
        assert persistent.async_create.call_args.kwargs["title"] == "High: srv01"
        notification_id = persistent.async_create.call_args.kwargs["notification_id"]

        await post(
            client,
            payload("update", update_action="acknowledged", update_user="Dominik"),
        )
        await post(client, payload("resolved", duration="5m"))
        await hass.async_block_till_done()

        assert hass.states.get(OPEN_SENSOR).state == "0"
        persistent.async_dismiss.assert_called_once_with(hass, notification_id)

        # A late problem event for an already resolved problem is ignored.
        late = await post(client, payload())
        assert (await late.json())["ignored"] == "stale"
        assert hass.states.get(OPEN_SENSOR).state == "0"

    assert [e.data["kind"] for e in events] == ["problem", "update", "resolved"]
    assert events[0].data["severity_name"] == "high"
    assert events[0].data["url"].endswith("tr_events.php?triggerid=77&eventid=1001")
    assert hass.states.get(LAST_SENSOR).state != "unknown"


async def test_center_bridge_falls_back_to_former_domain(hass, hass_client_no_auth, setup):
    """Notification center 0.3.x (doralab_notify) is still used while it is the only one."""
    calls = async_mock_service(hass, "doralab_notify", "send")
    await setup()
    client = await hass_client_no_auth()
    await post(client, payload())
    await hass.async_block_till_done()
    assert [c.data["type"] for c in calls] == ["zabbix_problem"]


async def test_center_bridge_prefers_new_domain(hass, hass_client_no_auth, setup):
    """If both are present (during the switch), only Enhanced Notify gets the message."""
    old = async_mock_service(hass, "doralab_notify", "send")
    new = async_mock_service(hass, "enhanced_notify", "send")
    await setup()
    client = await hass_client_no_auth()
    await post(client, payload())
    await hass.async_block_till_done()
    assert len(new) == 1 and old == []


async def test_center_bridge(hass, hass_client_no_auth, setup):
    """With enhanced_notify present, one entry per problem is kept via the tag."""
    calls = async_mock_service(hass, "enhanced_notify", "send")
    await setup()
    client = await hass_client_no_auth()

    with patch(
        "custom_components.zabbix_notify.hub.persistent_notification"
    ) as persistent:
        await post(client, payload())
        await post(client, payload("update", update_action="acknowledged"))
        await post(client, payload("resolved"))
        await hass.async_block_till_done()
        persistent.async_create.assert_not_called()

    assert [c.data["type"] for c in calls] == [
        "zabbix_problem",
        "zabbix_update",
        "zabbix_resolved",
    ]
    assert len({c.data["tag"] for c in calls}) == 1
    first = calls[0].data
    assert first["tag"] == f"zabbix:{WEBHOOK_ID[:8]}:1001"
    assert first["push"] is True
    assert first["category"] == "system"
    assert first["type_name"] == "Zabbix: Problem"
    assert first["type_icon"] == ""  # no icon chosen: category icon
    assert first["title"] == "High: srv01"
    assert first["link"].startswith("https://zabbix.example/tr_events.php")


async def test_center_bridge_falls_back_for_older_center(hass, hass_client_no_auth, setup):
    strict = vol.Schema(
        {
            vol.Required("type"): str,
            vol.Required("message"): str,
            vol.Optional("title"): str,
            vol.Optional("tag"): str,
            vol.Optional("link"): str,
            vol.Optional("push"): bool,
        }
    )
    calls = async_mock_service(hass, "enhanced_notify", "send", schema=strict)
    await setup()
    client = await hass_client_no_auth()
    assert (await post(client, payload())).status == 200
    assert len(calls) == 1
    assert "category" not in calls[0].data and "type_name" not in calls[0].data


async def test_center_gets_icon_from_option(hass, hass_client_no_auth, setup):
    calls = async_mock_service(hass, "enhanced_notify", "send")
    await setup({"icon": "/local/zabbix.png"})
    client = await hass_client_no_auth()
    await post(client, payload())
    await post(client, payload("resolved"))
    await hass.async_block_till_done()
    assert [c.data["type_icon"] for c in calls] == ["/local/zabbix.png", "/local/zabbix.png"]


async def test_center_without_icon_support_still_gets_name_and_category(
    hass, hass_client_no_auth, setup
):
    """A center that knows type_name/category but not type_icon keeps getting those."""
    middle = vol.Schema(
        {
            vol.Required("type"): str,
            vol.Required("message"): str,
            vol.Optional("title"): str,
            vol.Optional("tag"): str,
            vol.Optional("link"): str,
            vol.Optional("push"): bool,
            vol.Optional("category"): str,
            vol.Optional("type_name"): str,
        }
    )
    calls = async_mock_service(hass, "enhanced_notify", "send", schema=middle)
    await setup({"icon": "/local/zabbix.png"})
    client = await hass_client_no_auth()
    assert (await post(client, payload())).status == 200
    assert len(calls) == 1
    assert calls[0].data["type_name"] == "Zabbix: Problem"
    assert calls[0].data["category"] == "system"
    assert "type_icon" not in calls[0].data


async def test_center_can_be_disabled(hass, hass_client_no_auth, setup):
    calls = async_mock_service(hass, "enhanced_notify", "send")
    await setup({"use_notification_center": False})
    client = await hass_client_no_auth()
    with patch("custom_components.zabbix_notify.hub.persistent_notification") as persistent:
        await post(client, payload())
        persistent.async_create.assert_called_once()
    assert calls == []


async def test_notify_services_standalone(hass, hass_client_no_auth, setup):
    pushes = async_mock_service(hass, "notify", "mobile_app_test")
    await setup({OPT_NOTIFY_PROBLEM: ["notify.mobile_app_test"], "persistent_notification": False})
    client = await hass_client_no_auth()

    await post(client, payload(severity="4"))
    await post(client, payload("resolved"))  # no services chosen for resolved
    await hass.async_block_till_done()

    assert len(pushes) == 1
    data = pushes[0].data
    assert data["title"] == "High: srv01"
    assert data["data"]["tag"] == f"zabbix:{WEBHOOK_ID[:8]}:1001"
    assert data["data"]["push"] == {"interruption-level": "time-sensitive"}

    pushes.clear()
    await post(client, payload(event_id="2002", severity="2"))
    assert "push" not in pushes[0].data["data"]


async def test_test_event_creates_nothing(hass, hass_client_no_auth, setup):
    calls = async_mock_service(hass, "enhanced_notify", "send")
    await setup()
    client = await hass_client_no_auth()
    assert hass.states.get(LAST_SENSOR).state == "unknown"

    response = await post(client, {"version": 1, "kind": "test"})
    assert response.status == 200
    await hass.async_block_till_done()

    assert calls == []
    assert hass.states.get(OPEN_SENSOR).state == "0"
    assert hass.states.get(LAST_SENSOR).state != "unknown"


async def test_state_survives_reload(hass, hass_client_no_auth, setup):
    entry = await setup({"persistent_notification": False})
    client = await hass_client_no_auth()
    await post(client, payload())
    await post(client, payload(event_id="2002", host="srv02"))
    await post(client, payload("resolved", event_id="2002"))
    await hass.async_block_till_done()
    assert hass.states.get(OPEN_SENSOR).state == "1"

    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(OPEN_SENSOR).state == "1"

    # The resolved problem is remembered, so a stale duplicate is still ignored.
    client = await hass_client_no_auth()
    late = await post(client, payload(event_id="2002", host="srv02"))
    assert (await late.json())["ignored"] == "stale"
