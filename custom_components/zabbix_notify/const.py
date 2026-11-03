"""Constants for Zabbix Notify."""

from __future__ import annotations

DOMAIN = "zabbix_notify"
VERSION = "0.1.2"

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

# Optional bridge to the DORALAB notification center (doralab_notify)
CENTER_DOMAIN = "doralab_notify"
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
MAX_ATTRIBUTE_PROBLEMS = 20
