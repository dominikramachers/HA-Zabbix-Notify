"""Sidebar dashboard: a custom panel that ships with the integration.

The panel is a plain web component (``frontend/zabbix-notify-panel.js``) that reads the
open-problems sensor of every configured source, so it needs no dashboard resources and
no helper cards, and it follows the Home Assistant theme through CSS variables.
"""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    PANEL_ELEMENT,
    PANEL_ICON,
    PANEL_SCRIPT,
    PANEL_URL_PATH,
    STATIC_URL,
    VERSION,
)

_FRONTEND_DIR = Path(__file__).parent / "frontend"
_KEY_STATIC = "static_registered"
_KEY_PANEL = "panel_registered"
_KEY_WANTED = "panel_entries"


def _store(hass: HomeAssistant) -> dict:
    return hass.data.setdefault(DOMAIN, {})


async def async_set_panel(hass: HomeAssistant, entry_id: str, wanted: bool) -> None:
    """Say whether a source wants the sidebar dashboard; the panel exists while any does."""
    store = _store(hass)
    entries: set[str] = store.setdefault(_KEY_WANTED, set())
    if wanted:
        entries.add(entry_id)
    else:
        entries.discard(entry_id)

    if entries and not store.get(_KEY_PANEL):
        if not store.get(_KEY_STATIC):
            await hass.http.async_register_static_paths(
                [StaticPathConfig(STATIC_URL, str(_FRONTEND_DIR), cache_headers=False)]
            )
            store[_KEY_STATIC] = True
        await panel_custom.async_register_panel(
            hass,
            frontend_url_path=PANEL_URL_PATH,
            webcomponent_name=PANEL_ELEMENT,
            module_url=f"{STATIC_URL}/{PANEL_SCRIPT}?v={VERSION}",
            sidebar_title="Zabbix",
            sidebar_icon=PANEL_ICON,
            require_admin=True,
            embed_iframe=False,
        )
        store[_KEY_PANEL] = True
    elif not entries and store.get(_KEY_PANEL):
        frontend.async_remove_panel(hass, PANEL_URL_PATH)
        store[_KEY_PANEL] = False
