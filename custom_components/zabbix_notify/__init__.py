"""Zabbix Notify: receive Zabbix problem events in Home Assistant via webhook."""

from __future__ import annotations

import logging

from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_WEBHOOK_ID
from .hub import ZabbixHub

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]

type ZabbixConfigEntry = ConfigEntry[ZabbixHub]


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
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ZabbixConfigEntry) -> bool:
    """Unload a source and persist its state."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        webhook.async_unregister(hass, entry.data[CONF_WEBHOOK_ID])
        await entry.runtime_data.async_save()
    return unloaded


async def _async_reload(hass: HomeAssistant, entry: ZabbixConfigEntry) -> None:
    """Reload after options or token changes."""
    await hass.config_entries.async_reload(entry.entry_id)
