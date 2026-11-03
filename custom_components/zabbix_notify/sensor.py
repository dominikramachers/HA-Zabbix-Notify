"""Sensors: number of open Zabbix problems and time of the last received event."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ZabbixConfigEntry
from .const import DOMAIN, MAX_ATTRIBUTE_PROBLEMS, SEVERITY_KEYS
from .hub import ZabbixHub


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZabbixConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub = entry.runtime_data
    async_add_entities([OpenProblemsSensor(hub), LastReceivedSensor(hub)])


class _ZabbixSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hub: ZabbixHub, key: str) -> None:
        self._hub = hub
        self._attr_translation_key = key
        self._attr_unique_id = f"{hub.entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, hub.entry.entry_id)},
            name=hub.entry.title,
            manufacturer="Zabbix",
            model="Webhook media type",
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._hub.signal, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()


class OpenProblemsSensor(_ZabbixSensor):
    """Problems that are currently open according to the received events."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "problems"
    _attr_icon = "mdi:alert-circle-outline"
    # The list is large and only useful live; keep it out of the recorder database.
    _unrecorded_attributes = frozenset(
        {"problems", "zabbix_url", "problems_url", "affected_hosts"}
    )

    def __init__(self, hub: ZabbixHub) -> None:
        super().__init__(hub, "open_problems")

    @property
    def native_value(self) -> int:
        return self._hub.open_count

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        problems = sorted(
            self._hub.open.values(),
            key=lambda p: (p.get("severity", 0), p.get("since", "")),
            reverse=True,
        )
        counts = Counter(p.get("severity", 0) for p in problems)
        hosts = sorted({p.get("host", "") for p in problems if p.get("host")})
        return {
            "entry_id": self._hub.entry.entry_id,
            "by_severity": {key: counts.get(i, 0) for i, key in enumerate(SEVERITY_KEYS)},
            "affected_hosts": hosts,
            "zabbix_url": self._hub.base_url or None,
            "problems_url": self._hub.problems_url,
            "problems": [
                {
                    "event_id": p["event_id"],
                    "trigger_id": p.get("trigger_id", ""),
                    "host": p.get("host", ""),
                    "name": p.get("name", "")[:300],
                    "severity": SEVERITY_KEYS[p.get("severity", 0)],
                    "opdata": p.get("opdata", "")[:200],
                    "acknowledged": bool(p.get("acknowledged", False)),
                    "since": p.get("since"),
                    "url": self._hub.problem_url(p),
                }
                for p in problems[:MAX_ATTRIBUTE_PROBLEMS]
            ],
        }


class LastReceivedSensor(_ZabbixSensor):
    """When Home Assistant last heard from Zabbix (also set by the Test button)."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hub: ZabbixHub) -> None:
        super().__init__(hub, "last_received")

    @property
    def native_value(self) -> datetime | None:
        return self._hub.last_received
