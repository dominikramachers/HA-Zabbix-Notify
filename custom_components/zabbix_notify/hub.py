"""Core logic: receives Zabbix events, tracks open problems and delivers notifications."""

from __future__ import annotations

from datetime import datetime
import hmac
import logging
from typing import TYPE_CHECKING, Any

from aiohttp import web
import voluptuous as vol

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CENTER_CATEGORY,
    CENTER_DOMAINS,
    CENTER_SERVICE,
    CENTER_TYPE_IDS,
    CONF_TOKEN,
    CONF_WEBHOOK_ID,
    DOMAIN,
    EVENT_ZABBIX,
    KIND_PROBLEM,
    KIND_RESOLVED,
    KIND_TEST,
    KIND_UPDATE,
    MAX_RESOLVED_MEMORY,
    OPT_ICON,
    OPT_LANGUAGE,
    OPT_LINK,
    OPT_NOTIFY_PROBLEM,
    OPT_NOTIFY_RESOLVED,
    OPT_NOTIFY_UPDATE,
    OPT_PERSISTENT,
    OPT_USE_CENTER,
    OPT_ZABBIX_URL,
    SAVE_DELAY,
    SEVERITY_KEYS,
    STORAGE_VERSION,
    TOKEN_HEADER,
    URGENT_SEVERITY,
    VERSION,
)
from .payload import ZabbixEvent, parse_event
from .texts import (
    build_message,
    event_link,
    normalize_base_url,
    problems_link,
    resolve_language,
    type_name,
    zabbix_link,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

_NOTIFY_OPTION = {
    KIND_PROBLEM: OPT_NOTIFY_PROBLEM,
    KIND_UPDATE: OPT_NOTIFY_UPDATE,
    KIND_RESOLVED: OPT_NOTIFY_RESOLVED,
}


def _acknowledged(update_action: str, previous: bool) -> bool:
    """Acknowledgement state after an update event (Zabbix reports actions in English)."""
    actions = {part.strip().lower() for part in update_action.split(",")}
    if "unacknowledged" in actions:
        return False
    if "acknowledged" in actions:
        return True
    return previous


class ZabbixHub:
    """State and behaviour of one configured Zabbix source."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.signal = f"{DOMAIN}_update_{entry.entry_id}"
        self.open: dict[str, dict[str, Any]] = {}
        self._resolved: dict[str, str] = {}
        self.last_received: datetime | None = None
        # Frontend address last announced by Zabbix ({$ZABBIX.URL} of the media type)
        self._announced_url = ""
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )

    # ------------------------------------------------------------ properties

    @property
    def webhook_id(self) -> str:
        return self.entry.data[CONF_WEBHOOK_ID]

    @property
    def token(self) -> str:
        return self.entry.data[CONF_TOKEN]

    @property
    def open_count(self) -> int:
        return len(self.open)

    @property
    def base_url(self) -> str:
        """Zabbix frontend address: the configured one, else the one Zabbix announced."""
        return normalize_base_url(self._opt(OPT_ZABBIX_URL, "")) or self._announced_url

    @property
    def problems_url(self) -> str | None:
        return problems_link(self.base_url)

    def problem_url(self, problem: dict[str, Any]) -> str | None:
        """Link to one open problem in the Zabbix frontend."""
        return event_link(
            self.base_url, problem.get("trigger_id", ""), problem.get("event_id", "")
        )

    def _opt(self, key: str, default: Any) -> Any:
        return self.entry.options.get(key, default)

    def _tag(self, event: ZabbixEvent) -> str:
        """Stable tag per problem, unique per Zabbix source."""
        return f"zabbix:{self.webhook_id[:8]}:{event.event_id}"

    # --------------------------------------------------------------- storage

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self.open = dict(data.get("open", {}))
        self._resolved = dict(data.get("resolved", {}))
        last = data.get("last_received")
        self.last_received = dt_util.parse_datetime(last) if last else None
        self._announced_url = normalize_base_url(data.get("zabbix_url"))

    def _dump(self) -> dict[str, Any]:
        return {
            "open": self.open,
            "resolved": self._resolved,
            "last_received": self.last_received.isoformat() if self.last_received else None,
            "zabbix_url": self._announced_url,
        }

    async def async_save(self) -> None:
        await self._store.async_save(self._dump())

    def _schedule_save(self) -> None:
        self._store.async_delay_save(self._dump, SAVE_DELAY)

    # --------------------------------------------------------------- webhook

    def _authorized(self, request: web.Request) -> bool:
        supplied = request.headers.get(TOKEN_HEADER, "")
        if not supplied:
            auth = request.headers.get("Authorization", "")
            if auth.lower().startswith("bearer "):
                supplied = auth[7:].strip()
        return bool(supplied) and hmac.compare_digest(
            supplied.encode(), self.token.encode()
        )

    async def async_handle_webhook(
        self, hass: HomeAssistant, webhook_id: str, request: web.Request
    ) -> web.Response:
        """Handle one POST from the Zabbix media type."""
        if not self._authorized(request):
            _LOGGER.warning(
                "Rejected Zabbix webhook call from %s: missing or wrong token",
                request.remote,
            )
            return web.json_response({"ok": False, "error": "unauthorized"}, status=401)
        try:
            data = await request.json()
        except ValueError:
            return web.json_response({"ok": False, "error": "invalid_json"}, status=400)
        try:
            event = parse_event(data)
        except vol.Invalid as err:
            _LOGGER.warning("Rejected invalid Zabbix payload: %s", err)
            return web.json_response(
                {"ok": False, "error": "invalid_payload", "detail": str(err)}, status=400
            )
        try:
            result = await self.async_handle(event)
        except Exception:  # noqa: BLE001 - report as 500 so Zabbix retries
            _LOGGER.exception("Delivering Zabbix event %s failed", event.event_id)
            return web.json_response({"ok": False, "error": "delivery_failed"}, status=500)
        return web.json_response(
            {"ok": True, "source": "ha-zabbix-notify", "version": VERSION, **result}
        )

    # --------------------------------------------------------------- handling

    async def async_handle(self, event: ZabbixEvent) -> dict[str, Any]:
        """Apply an event to the tracked state and deliver notifications."""
        self.last_received = dt_util.utcnow()

        if event.kind == KIND_TEST:
            self._schedule_save()
            async_dispatcher_send(self.hass, self.signal)
            return {"kind": KIND_TEST}

        # Zabbix may process alerts in parallel; ignore problem/update events
        # that arrive after the recovery of the same problem.
        if event.kind in (KIND_PROBLEM, KIND_UPDATE) and event.event_id in self._resolved:
            _LOGGER.debug("Ignoring stale %s for resolved event %s", event.kind, event.event_id)
            return {"kind": event.kind, "ignored": "stale"}

        if announced := normalize_base_url(event.zabbix_url):
            self._announced_url = announced

        now = dt_util.utcnow().isoformat()
        if event.kind == KIND_RESOLVED:
            self.open.pop(event.event_id, None)
            self._resolved[event.event_id] = now
            while len(self._resolved) > MAX_RESOLVED_MEMORY:
                self._resolved.pop(next(iter(self._resolved)))
        else:
            previous = self.open.get(event.event_id, {})
            self.open[event.event_id] = {
                "event_id": event.event_id,
                "trigger_id": event.trigger_id or previous.get("trigger_id", ""),
                "host": event.host or previous.get("host", ""),
                "name": event.name or previous.get("name", ""),
                "severity": event.severity,
                "opdata": event.opdata or previous.get("opdata", ""),
                "acknowledged": _acknowledged(
                    event.update_action, bool(previous.get("acknowledged", False))
                ),
                "since": previous.get("since", now),
            }

        self.hass.bus.async_fire(
            EVENT_ZABBIX,
            {
                "entry_id": self.entry.entry_id,
                "kind": event.kind,
                "event_id": event.event_id,
                "host": event.host,
                "name": event.name,
                "severity": event.severity,
                "severity_name": SEVERITY_KEYS[event.severity],
                "opdata": event.opdata,
                "update_action": event.update_action,
                "update_message": event.update_message,
                "tags": event.tags,
                "url": zabbix_link(event, self._opt(OPT_ZABBIX_URL, "")),
            },
        )

        try:
            await self._async_deliver(event)
        finally:
            self._schedule_save()
            async_dispatcher_send(self.hass, self.signal)
        return {"kind": event.kind, "open_problems": self.open_count}

    def dismiss(self, event_id: str) -> bool:
        """Forget an open problem without a recovery event (silent, nothing is sent).

        For problems whose recovery never reached Home Assistant, for example because
        Zabbix was unable to deliver it or the trigger was disabled in Zabbix.
        """
        problem = self.open.pop(event_id, None)
        if problem is None:
            return False
        self._resolved[event_id] = dt_util.utcnow().isoformat()
        while len(self._resolved) > MAX_RESOLVED_MEMORY:
            self._resolved.pop(next(iter(self._resolved)))
        if self._opt(OPT_PERSISTENT, True):
            persistent_notification.async_dismiss(
                self.hass, f"{DOMAIN}_{self.webhook_id[:8]}_{event_id}"
            )
        self._schedule_save()
        async_dispatcher_send(self.hass, self.signal)
        return True

    # --------------------------------------------------------------- delivery

    def _center_domain(self) -> str | None:
        """Domain of the installed notification center (new name first), if any."""
        if not self._opt(OPT_USE_CENTER, True):
            return None
        return next(
            (d for d in CENTER_DOMAINS if self.hass.services.has_service(d, CENTER_SERVICE)),
            None,
        )

    async def _async_deliver(self, event: ZabbixEvent) -> None:
        lang = resolve_language(self._opt(OPT_LANGUAGE, "auto"), self.hass.config.language)
        title, message = build_message(event, lang)
        link = (
            zabbix_link(event, self._opt(OPT_ZABBIX_URL, ""))
            if self._opt(OPT_LINK, True)
            else None
        )

        if center := self._center_domain():
            await self._async_send_center(center, event, lang, title, message, link)
            return

        if self._opt(OPT_PERSISTENT, True):
            notification_id = f"{DOMAIN}_{self.webhook_id[:8]}_{event.event_id}"
            if event.kind == KIND_RESOLVED:
                persistent_notification.async_dismiss(self.hass, notification_id)
            else:
                persistent_notification.async_create(
                    self.hass, message, title=title, notification_id=notification_id
                )

        await self._async_send_notify(event, title, message, link)

    async def _async_send_center(
        self, center: str, event: ZabbixEvent, lang: str, title: str, message: str, link: str | None
    ) -> None:
        """Hand over to the notification center; recipients are managed there."""
        base: dict[str, Any] = {
            "type": CENTER_TYPE_IDS[event.kind],
            "message": message,
            "title": title,
            "tag": self._tag(event),
            "push": True,
        }
        if link:
            base["link"] = link
        extended = {
            **base,
            "type_name": type_name(event.kind, lang),
            "category": CENTER_CATEGORY,
        }
        # An empty type_icon resets the type to the icon of its category.
        full = {**extended, "type_icon": str(self._opt(OPT_ICON, "") or "").strip()}
        # Older notification centers do not know the optional fields: try the
        # richest payload first and fall back step by step.
        attempts = (full, extended, base)
        for index, payload in enumerate(attempts):
            try:
                await self.hass.services.async_call(
                    center, CENTER_SERVICE, payload, blocking=True
                )
            except vol.Invalid:
                if index == len(attempts) - 1:
                    raise
            else:
                return

    async def _async_send_notify(
        self, event: ZabbixEvent, title: str, message: str, link: str | None
    ) -> None:
        """Standalone mode: push to the notify services chosen in the options."""
        services = self._opt(_NOTIFY_OPTION[event.kind], [])
        if not services:
            return
        data: dict[str, Any] = {"tag": self._tag(event)}
        if link:
            data["url"] = link
            data["clickAction"] = link
        if event.kind == KIND_PROBLEM and event.severity >= URGENT_SEVERITY:
            data["push"] = {"interruption-level": "time-sensitive"}
            data["ttl"] = 0
            data["priority"] = "high"
        for service in services:
            name = service.removeprefix("notify.")
            try:
                await self.hass.services.async_call(
                    "notify",
                    name,
                    {"title": title, "message": message, "data": data},
                    blocking=True,
                )
            except HomeAssistantError as err:
                _LOGGER.warning("Sending to notify.%s failed: %s", name, err)
