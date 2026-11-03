"""Config flow and options flow tests."""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.zabbix_notify.const import CONF_TOKEN, CONF_WEBHOOK_ID, DOMAIN


async def test_user_flow_creates_webhook_and_token(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Main Zabbix"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Main Zabbix"
    assert result["data"][CONF_WEBHOOK_ID]
    assert len(result["data"][CONF_TOKEN]) >= 32
    await hass.async_block_till_done()

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_two_sources_get_different_credentials(hass):
    data = []
    for name in ("A", "B"):
        flow = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(flow["flow_id"], {"name": name})
        data.append(result["data"])
    await hass.async_block_till_done()
    assert data[0][CONF_WEBHOOK_ID] != data[1][CONF_WEBHOOK_ID]
    assert data[0][CONF_TOKEN] != data[1][CONF_TOKEN]
    for entry in hass.config_entries.async_entries(DOMAIN):
        await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_options_flow_shows_credentials_and_can_rotate_token(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Zabbix",
        data={CONF_WEBHOOK_ID: "whoptions0123456", CONF_TOKEN: "old-token"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["description_placeholders"]["token"] == "old-token"
    assert "whoptions0123456" in result["description_placeholders"]["webhook_url"]

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "language": "de",
            "use_notification_center": False,
            "persistent_notification": True,
            "link_to_zabbix": False,
            "notify_problem": ["mobile_app_phone"],
            "notify_update": [],
            "notify_resolved": [],
            "regenerate_token": True,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    assert entry.options["language"] == "de"
    assert entry.options["notify_problem"] == ["mobile_app_phone"]
    assert "regenerate_token" not in entry.options
    assert entry.data[CONF_TOKEN] != "old-token"

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def _options_entry(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Zabbix",
        data={CONF_WEBHOOK_ID: "whicon0123456789", CONF_TOKEN: "tok"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _options_input(icon: str, **extra) -> dict:
    return {
        "language": "auto",
        "use_notification_center": True,
        "persistent_notification": True,
        "link_to_zabbix": True,
        "icon": icon,
        "notify_problem": [],
        "notify_update": [],
        "notify_resolved": [],
        "regenerate_token": False,
        **extra,
    }


async def test_options_icon_is_saved_and_trimmed(hass):
    entry = await _options_entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], _options_input("  /local/zabbix.png ")
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options["icon"] == "/local/zabbix.png"
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_options_invalid_icon_shows_error_and_keeps_token(hass):
    entry = await _options_entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], _options_input("javascript:alert(1)", regenerate_token=True)
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"icon": "invalid_icon"}
    # nothing was saved or rotated by the failed submit
    assert "icon" not in entry.options
    assert entry.data[CONF_TOKEN] == "tok"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], _options_input("")
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
