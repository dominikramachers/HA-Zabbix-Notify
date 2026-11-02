"""Human-readable notification texts (German and English) and link building."""

from __future__ import annotations

import re

from .const import KIND_PROBLEM, KIND_RESOLVED, KIND_UPDATE
from .payload import ZabbixEvent

SEVERITY_NAMES: dict[str, tuple[str, ...]] = {
    "en": ("Not classified", "Information", "Warning", "Average", "High", "Disaster"),
    "de": (
        "Nicht klassifiziert",
        "Information",
        "Warnung",
        "Durchschnitt",
        "Hoch",
        "Katastrophe",
    ),
}

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "title_problem": "{severity}: {host}",
        "title_update": "Updated: {host}",
        "title_resolved": "Resolved: {host}",
        "type_problem": "Zabbix: Problem",
        "type_update": "Zabbix: Problem updated",
        "type_resolved": "Zabbix: Problem resolved",
        "by": "by {user}",
        "comment": "Comment: {comment}",
        "duration": "Duration: {duration}",
        "severity_changed": "Severity changed from {old} to {new}",
    },
    "de": {
        "title_problem": "{severity}: {host}",
        "title_update": "Aktualisiert: {host}",
        "title_resolved": "Behoben: {host}",
        "type_problem": "Zabbix: Problem",
        "type_update": "Zabbix: Problem aktualisiert",
        "type_resolved": "Zabbix: Problem behoben",
        "by": "von {user}",
        "comment": "Kommentar: {comment}",
        "duration": "Dauer: {duration}",
        "severity_changed": "Schweregrad von {old} auf {new} geändert",
    },
}

# Zabbix writes {EVENT.UPDATE.ACTION} in the frontend language of the server.
# Known English phrases are translated; anything else is passed through.
_ACTIONS: dict[str, dict[str, str]] = {
    "en": {},
    "de": {
        "acknowledged": "Bestätigt",
        "unacknowledged": "Bestätigung aufgehoben",
        "commented": "Kommentiert",
        "closed": "Manuell geschlossen",
        "suppressed": "Unterdrückt",
        "unsuppressed": "Unterdrückung aufgehoben",
        "converted to cause": "In Ursache umgewandelt",
        "converted to symptom": "In Symptom umgewandelt",
    },
}

_SEVERITY_CHANGE = re.compile(
    r"^changed severity from (?P<old>.+?) to (?P<new>.+)$", re.IGNORECASE
)


def resolve_language(option: str | None, ha_language: str | None) -> str:
    """Pick the text language: explicit option, else Home Assistant's language."""
    if option in ("de", "en"):
        return option
    return "de" if (ha_language or "").lower().startswith("de") else "en"


def severity_name(severity: int, lang: str) -> str:
    """Localized name of a Zabbix severity (0..5)."""
    names = SEVERITY_NAMES[lang]
    return names[max(0, min(len(names) - 1, severity))]


def _localize_severity(name: str, lang: str) -> str:
    """Translate an English severity name coming from Zabbix, if known."""
    for index, english in enumerate(SEVERITY_NAMES["en"]):
        if english.lower() == name.strip().lower():
            return SEVERITY_NAMES[lang][index]
    return name.strip()


def _translate_action(part: str, lang: str) -> str:
    part = part.strip()
    match = _SEVERITY_CHANGE.match(part)
    if match:
        return STRINGS[lang]["severity_changed"].format(
            old=_localize_severity(match["old"], lang),
            new=_localize_severity(match["new"], lang),
        )
    return _ACTIONS[lang].get(part.lower(), part[:1].upper() + part[1:])


def type_name(kind: str, lang: str) -> str:
    """Display name for the notification type of an event kind."""
    return STRINGS[lang][f"type_{kind}"]


def build_message(event: ZabbixEvent, lang: str) -> tuple[str, str]:
    """Return (title, message) for an event."""
    strings = STRINGS[lang]
    host = event.host
    if event.kind == KIND_PROBLEM:
        severity = severity_name(event.severity, lang)
        title = strings["title_problem"].format(severity=severity, host=host)
        if not host:
            title = severity
        lines = [event.name or severity]
        if event.opdata:
            lines.append(event.opdata)
    elif event.kind == KIND_UPDATE:
        title = strings["title_update"].format(host=host) if host else strings["title_update"].split(":")[0]
        lines = [event.name]
        actions = [_translate_action(p, lang) for p in event.update_action.split(",") if p.strip()]
        if actions:
            summary = ", ".join(actions)
            if event.update_user:
                summary += " " + strings["by"].format(user=event.update_user)
            lines.append(summary)
        if event.update_message:
            lines.append(strings["comment"].format(comment=event.update_message))
    elif event.kind == KIND_RESOLVED:
        title = strings["title_resolved"].format(host=host) if host else strings["title_resolved"].split(":")[0]
        lines = [event.name]
        if event.duration:
            lines.append(strings["duration"].format(duration=event.duration))
    else:
        raise ValueError(f"no text for event kind {event.kind!r}")
    return title, "\n".join(line for line in lines if line)


def zabbix_link(event: ZabbixEvent) -> str | None:
    """Deep link to the event in the Zabbix frontend, if the base URL is known."""
    base = event.zabbix_url.rstrip("/")
    if not base.lower().startswith(("http://", "https://")):
        return None
    if event.trigger_id and event.event_id:
        return f"{base}/tr_events.php?triggerid={event.trigger_id}&eventid={event.event_id}"
    return f"{base}/zabbix.php?action=problem.view"
