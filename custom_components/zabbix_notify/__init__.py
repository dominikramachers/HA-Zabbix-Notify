"""Zabbix Notify: receive Zabbix problem events in Home Assistant via webhook."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_ENTRY_ID,
    ATTR_EVENT_ID,
    CONF_WEBHOOK_ID,
    DOMAIN,
    OPT_SHOW_PANEL,
    SERVICE_DISMISS,
)
from .hub import ZabbixHub
from .panel import async_set_panel

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type ZabbixConfigEntry = ConfigEntry[ZabbixHub]

DISMISS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_EVENT_ID): cv.string,
        vol.Optional(ATTR_ENTRY_ID): cv.string,
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the integration-wide services."""

    async def _dismiss(call: ServiceCall) -> None:
        event_id = call.data[ATTR_EVENT_ID].strip()
        entry_id = call.data.get(ATTR_ENTRY_ID)
        hubs = [
            entry.runtime_data
            for entry in hass.config_entries.async_loaded_entries(DOMAIN)
            if entry_id in (None, entry.entry_id)
        ]
        if not hubs:
            raise ServiceValidationError(
                "No loaded Zabbix Notify source matches",
                translation_domain=DOMAIN,
                translation_key="no_source",
            )
        if not any(hub.dismiss(event_id) for hub in hubs):
            raise ServiceValidationError(
                f"No open problem with event ID {event_id}",
                translation_domain=DOMAIN,
                translation_key="unknown_problem",
                translation_placeholders={"event_id": event_id},
            )

    async_register_admin_service(
        hass, DOMAIN, SERVICE_DISMISS, _dismiss, schema=DISMISS_SCHEMA
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ZabbixConfigEntry) -> bool:
    """Set up one Zabbix source: restore state, register the webhook, add sensors."""
    hub = ZabbixHub(hass, entry)
    await hub.async_load()
    entry.runtime_data = hub

    webhook.async_register(
        hass,
        "zabbix_notify",
        entry.title,
        entry.data[CONF_WEBHOOK_ID],
        hub.async_handle_webhook,
        allowed_methods=["POST"],
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_set_panel(hass, entry.entry_id, entry.options.get(OPT_SHOW_PANEL, True))
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ZabbixConfigEntry) -> bool:
    """Unload a source and persist its state."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        webhook.async_unregister(hass, entry.data[CONF_WEBHOOK_ID])
        await entry.runtime_data.async_save()
        await async_set_panel(hass, entry.entry_id, False)
    return unloaded


async def _async_reload(hass: HomeAssistant, entry: ZabbixConfigEntry) -> None:
    """Reload after options or token changes."""
    await hass.config_entries.async_reload(entry.entry_id)
