"""Constants for Zabbix Notify."""

from __future__ import annotations

DOMAIN = "zabbix_notify"
VERSION = "0.2.0"

# Config entry data
CONF_WEBHOOK_ID = "webhook_id"
CONF_TOKEN = "token"

# Options
OPT_LANGUAGE = "language"
OPT_USE_CENTER = "use_notification_center"
OPT_PERSISTENT = "persistent_notification"
OPT_LINK = "link_to_zabbix"
OPT_ICON = "icon"
OPT_NOTIFY_PROBLEM = "notify_problem"
OPT_NOTIFY_UPDATE = "notify_update"
OPT_NOTIFY_RESOLVED = "notify_resolved"
OPT_REGENERATE = "regenerate_token"
OPT_SHOW_PANEL = "show_dashboard"
OPT_ZABBIX_URL = "zabbix_url"

# Event kinds (computed by the Zabbix media type script)
KIND_PROBLEM = "problem"
KIND_UPDATE = "update"
KIND_RESOLVED = "resolved"
KIND_TEST = "test"
KINDS = (KIND_PROBLEM, KIND_UPDATE, KIND_RESOLVED, KIND_TEST)

# Home Assistant bus event fired for every accepted Zabbix event
EVENT_ZABBIX = "zabbix_notify_event"

# Authentication header expected on every webhook call
TOKEN_HEADER = "X-Zabbix-Notify-Token"

# Zabbix severities 0..5
SEVERITY_KEYS = (
    "not_classified",
    "information",
    "warning",
    "average",
    "high",
    "disaster",
)
# From this severity on, push notifications are marked as time-sensitive
URGENT_SEVERITY = 4

# Optional bridge to the notification center Enhanced Notify (enhanced_notify).
# Its predecessor "DORALAB Notify" (doralab_notify, up to 0.3.x) is still found as a fallback.
CENTER_DOMAINS = ("enhanced_notify", "doralab_notify")
CENTER_SERVICE = "send"
CENTER_CATEGORY = "system"
CENTER_TYPE_IDS = {
    KIND_PROBLEM: "zabbix_problem",
    KIND_UPDATE: "zabbix_update",
    KIND_RESOLVED: "zabbix_resolved",
}

STORAGE_VERSION = 1
SAVE_DELAY = 5
MAX_RESOLVED_MEMORY = 200
MAX_ATTRIBUTE_PROBLEMS = 50

# Sidebar dashboard (custom panel served by the integration)
PANEL_URL_PATH = "zabbix-notify"
PANEL_ELEMENT = "zabbix-notify-panel"
PANEL_ICON = "mdi:monitor-dashboard"
STATIC_URL = "/zabbix_notify_static"
PANEL_SCRIPT = "zabbix-notify-panel.js"

# Service to drop a problem whose recovery was never received
SERVICE_DISMISS = "dismiss_problem"
ATTR_ENTRY_ID = "entry_id"
ATTR_EVENT_ID = "event_id"
