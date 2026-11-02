"""Config and options flow for Zabbix Notify."""

from __future__ import annotations

import secrets
from typing import Any

import voluptuous as vol

from homeassistant.components import webhook
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from . import ZabbixConfigEntry
from .const import (
    CONF_TOKEN,
    CONF_WEBHOOK_ID,
    DOMAIN,
    OPT_LANGUAGE,
    OPT_LINK,
    OPT_NOTIFY_PROBLEM,
    OPT_NOTIFY_RESOLVED,
    OPT_NOTIFY_UPDATE,
    OPT_PERSISTENT,
    OPT_REGENERATE,
    OPT_USE_CENTER,
    TOKEN_HEADER,
)

_IGNORED_NOTIFY_SERVICES = {"notify", "persistent_notification", "send_message"}


def webhook_url(hass: HomeAssistant, webhook_id: str) -> str:
    """Full webhook URL (internal address preferred), or just the path if unknown."""
    path = webhook.async_generate_path(webhook_id)
    try:
        base = get_url(hass, prefer_external=False, allow_cloud=False)
    except NoURLAvailableError:
        return path
    return f"{base}{path}"


def _notify_services(hass: HomeAssistant, current: list[str]) -> list[str]:
    available = {
        name
        for name in hass.services.async_services_for_domain("notify")
        if name not in _IGNORED_NOTIFY_SERVICES
    }
    return sorted(available | set(current))


class ZabbixNotifyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create a Zabbix source (one webhook per Zabbix server)."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            webhook_id = webhook.async_generate_id()
            token = secrets.token_urlsafe(32)
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={CONF_WEBHOOK_ID: webhook_id, CONF_TOKEN: token},
                description_placeholders={
                    "webhook_url": webhook_url(self.hass, webhook_id),
                    "token": token,
                    "header": TOKEN_HEADER,
                },
            )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_NAME, default="Zabbix"): str}),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ZabbixConfigEntry) -> OptionsFlow:
        return ZabbixNotifyOptionsFlow()


class ZabbixNotifyOptionsFlow(OptionsFlow):
    """Delivery options, plus access to the webhook URL and token."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self.config_entry
        if user_input is not None:
            if user_input.pop(OPT_REGENERATE, False):
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, CONF_TOKEN: secrets.token_urlsafe(32)}
                )
            return self.async_create_entry(data=user_input)

        options = entry.options

        def notify_selector(key: str) -> SelectSelector:
            current = list(options.get(key, []))
            return SelectSelector(
                SelectSelectorConfig(
                    options=_notify_services(self.hass, current),
                    multiple=True,
                    custom_value=True,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            )

        schema = vol.Schema(
            {
                vol.Optional(
                    OPT_LANGUAGE, default=options.get(OPT_LANGUAGE, "auto")
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=["auto", "de", "en"],
                        translation_key="language",
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    OPT_USE_CENTER, default=options.get(OPT_USE_CENTER, True)
                ): bool,
                vol.Optional(
                    OPT_PERSISTENT, default=options.get(OPT_PERSISTENT, True)
                ): bool,
                vol.Optional(OPT_LINK, default=options.get(OPT_LINK, True)): bool,
                vol.Optional(
                    OPT_NOTIFY_PROBLEM, default=list(options.get(OPT_NOTIFY_PROBLEM, []))
                ): notify_selector(OPT_NOTIFY_PROBLEM),
                vol.Optional(
                    OPT_NOTIFY_UPDATE, default=list(options.get(OPT_NOTIFY_UPDATE, []))
                ): notify_selector(OPT_NOTIFY_UPDATE),
                vol.Optional(
                    OPT_NOTIFY_RESOLVED, default=list(options.get(OPT_NOTIFY_RESOLVED, []))
                ): notify_selector(OPT_NOTIFY_RESOLVED),
                vol.Optional(OPT_REGENERATE, default=False): bool,
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={
                "webhook_url": webhook_url(self.hass, entry.data[CONF_WEBHOOK_ID]),
                "token": entry.data[CONF_TOKEN],
                "header": TOKEN_HEADER,
            },
        )
