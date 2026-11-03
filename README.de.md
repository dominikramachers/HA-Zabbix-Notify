# Zabbix Notify für Home Assistant

[English version](README.md)

Empfängt **Problem-, Änderungs- und Behoben-Ereignisse** von Zabbix über einen Webhook-Media-Type in Home Assistant.
Zabbix entscheidet, *was* gemeldet wird (Hosts, Schweregrade, Tags). Home Assistant entscheidet, *wer* es bekommt und *wie*.

- Eine Meldung **pro Problem**: derselbe Eintrag wird aktualisiert, wenn das Problem bestätigt, geändert oder behoben wird
- Funktioniert eigenständig: Home-Assistant-Benachrichtigungen, optionaler Push an gewählte `notify`-Dienste, Sensoren und ein Bus-Event für Automationen
- Optionale Anbindung an die **DORALAB-Benachrichtigungszentrale** (`doralab_notify`): Die drei Zabbix-Typen erscheinen dort beim ersten Ereignis, die Empfänger wählst du pro Typ. Solange niemand ausgewählt ist, bekommt niemand einen Push.
- Webhook per Token gesichert, ein Webhook pro Zabbix-Server, Texte auf Deutsch und Englisch
- Enthält einen fertig importierbaren Zabbix-Media-Type (keine externen Abhängigkeiten)

## Funktionsweise

| Zabbix-Ereignis | Meldungstyp | Verhalten |
|---|---|---|
| Problem entsteht | `zabbix_problem` | neuer Eintrag, Titel z. B. `Hoch: srv01` |
| Problem geändert (bestätigt, kommentiert, Schweregrad geändert, ...) | `zabbix_update` | derselbe Eintrag wird aktualisiert und wieder ungelesen |
| Problem behoben | `zabbix_resolved` | derselbe Eintrag wird aktualisiert; ohne Benachrichtigungszentrale wird die HA-Benachrichtigung entfernt |

## Voraussetzungen

- Home Assistant 2025.1 oder neuer
- Ein Zabbix-Server, der Home Assistant per HTTP(S) erreicht (ein VPN genügt). Der Media Type nutzt das Exportformat von Zabbix 7.0, das neuere Versionen importieren können.

## Installation

**HACS:** HACS → ⋮ → *Benutzerdefinierte Repositories* → `https://github.com/dominikramachers/HA-Zabbix-Notify` als Kategorie *Integration* hinzufügen → installieren → Home Assistant neu starten.

**Manuell:** `custom_components/zabbix_notify` nach `config/custom_components` kopieren und neu starten.

**Zusammen mit der Benachrichtigungszentrale:** Beide sind getrennte Integrationen und werden unabhängig voneinander installiert, in beliebiger Reihenfolge. [DORALAB Notify](https://github.com/dominikramachers/ha-enhanced-notify) (`doralab_notify`) ebenfalls über HACS installieren und beide unter *Geräte & Dienste* hinzufügen. Zabbix Notify erkennt die Benachrichtigungszentrale bei jedem Ereignis neu, es muss also nichts verknüpft werden, und es funktioniert weiter, falls die Zentrale später entfernt wird.

## Einrichtung

### 1. Home Assistant

1. *Einstellungen → Geräte & Dienste → Integration hinzufügen → Zabbix Notify*, Namen eingeben.
2. **Webhook-URL** und **Token** kopieren, die angezeigt werden. Du findest sie später unter *Konfigurieren* wieder.

Verwende eine Adresse von Home Assistant, die dein Zabbix-Server erreicht. Die angezeigte URL nutzt deine interne URL, ersetze den Host, falls Zabbix anders verbindet. Nutze ein gültiges Zertifikat oder reines HTTP in einem vertrauenswürdigen Netz, denn das Zabbix-Skript kann die Zertifikatsprüfung nicht abschalten.

### 2. Zabbix

1. **Media Type importieren:** *Alerts → Media types → Import* → `zabbix/media_type_home_assistant.yaml`.
2. **Makros anlegen** (*Administration → Macros*):

   | Makro | Wert |
   |---|---|
   | `{$HA_NOTIFY_URL}` | die Webhook-URL aus Schritt 1 |
   | `{$HA_NOTIFY_TOKEN}` | das Token, Typ *Secret text* |
   | `{$ZABBIX.URL}` | Adresse deines Zabbix-Frontends, z. B. `https://zabbix.example.com` (für den Link in der Meldung) |
   | `{$HA_NOTIFY_PROXY}` | optionaler HTTP-Proxy, sonst nicht definieren |

3. **Technischen Benutzer anlegen** (*Users → Users*), z. B. `ha-notify`:
   - seine Benutzergruppe braucht mindestens **Lesezugriff** auf die zu meldenden Hostgruppen (Zabbix benachrichtigt nur über Hosts, die der Benutzer sehen darf)
   - Media hinzufügen: Typ *Home Assistant (Zabbix Notify)*, *Send to* beliebiger Text (z. B. `homeassistant`), **alle Schweregrade aktiv**, Zeitraum `1-7,00:00-24:00`
4. **Action konfigurieren** (*Alerts → Actions → Trigger actions*): *Operations*, *Recovery operations* **und** *Update operations* nutzen, jeweils *Send message* an den Benutzer `ha-notify` über diesen Media Type. *Custom message* bleibt aus. Der Media Type baut seinen eigenen Text, aber Zabbix versendet nur, wenn für jede Ereignisart eine Nachrichtenvorlage existiert ("No message defined for media type"). Der Import enthält diese Vorlagen. Wer den Media Type von Hand anlegt, ergänzt auf dem Reiter *Message templates* Vorlagen für *Problem*, *Problem recovery* und *Problem update* (beliebiger Text). Filter (Schweregrad, Hostgruppen, Tags, Wartung) kommen in die Bedingungen der Action.
5. **Testen:** Media Type öffnen, *Test* drücken. Antwort sollte `OK: test` sein, und der Sensor *Letztes Ereignis empfangen* in Home Assistant aktualisiert sich. Der Test erzeugt keine Meldung.

Tipp: *Attempts* des Media Types auf 5 und das Wiederholungsintervall auf 30 s setzen, damit kurze Neustarts von Home Assistant keine Ereignisse kosten. *Concurrent sessions* auf 1 lassen, um die Reihenfolge der Ereignisse zu erhalten.

Wer den Media Type lieber von Hand anlegt, nimmt das Skript `zabbix/ha_notify_webhook.js` und die Parameter aus `zabbix/build_media_type.py`.

### 3. Empfänger festlegen

**Mit der DORALAB-Benachrichtigungszentrale:** Nach dem ersten Ereignis erscheinen dort *Zabbix: Problem*, *Zabbix: Problem aktualisiert* und *Zabbix: Problem behoben*. In der Übersicht wählst du pro Typ die Personen und den Push-Modus. Standard ist niemand.

**Ohne sie:** In der Integration *Konfigurieren* öffnen und pro Ereignisart `notify`-Dienste wählen (z. B. `mobile_app_mein_handy`). Leer bedeutet kein Push. Probleme ab Schweregrad Hoch werden als zeitkritisch gesendet.

## Optionen

| Option | Bedeutung |
|---|---|
| Sprache der Texte | automatisch (Sprache von Home Assistant), Deutsch oder Englisch |
| DORALAB-Benachrichtigungszentrale nutzen | Anbindung an/aus (nur aktiv, wenn `doralab_notify.send` existiert) |
| Home-Assistant-Benachrichtigungen anzeigen | wenn keine Benachrichtigungszentrale genutzt wird |
| Link zu Zabbix | fügt einen Link zum Problem im Zabbix-Frontend hinzu |
| Push-Dienste je Ereignisart | wird ohne Benachrichtigungszentrale verwendet |
| Neues Token erzeugen | macht das alte Token ungültig |

## Entitäten und Ereignisse

- `sensor.<name>_offene_probleme`: Anzahl offener Probleme, Attribute `by_severity` und `problems` (bis 20)
- `sensor.<name>_letztes_ereignis_empfangen`: Zeitpunkt des letzten Aufrufs von Zabbix (Diagnose)
- Ereignis `zabbix_notify_event` mit `kind` (`problem`, `update`, `resolved`), `event_id`, `host`, `name`, `severity` (0-5), `severity_name`, `opdata`, `update_action`, `update_message`, `tags`, `url`

Offene Probleme leitet die Integration aus den empfangenen Ereignissen ab. Ereignisse, die Zabbix während eines Home-Assistant-Ausfalls nach allen Wiederholungen nicht zustellen konnte, fehlen, dann kann der Zähler von Zabbix abweichen.

## Fehlersuche

| Symptom | Ursache |
|---|---|
| Zabbix meldet `HTTP 401` | Token falsch oder fehlt (`{$HA_NOTIFY_TOKEN}`) |
| `Unexpected response, check the webhook ID` | Home Assistant antwortet auf unbekannte Webhook-IDs mit leerem `200`; ID in `{$HA_NOTIFY_URL}` prüfen |
| `Parameter "url" is empty` | Makro nicht definiert oder nur an einem Host statt global |
| Nichts kommt an, kein Fehler | Benutzer-Media inaktiv oder Schweregrad nicht angehakt, Benutzer ohne Lesezugriff auf die Hostgruppe, oder *Recovery/Update operations* fehlen in der Action. *Reports → Action log* prüfen. |
| Probleme kommen an, Änderungen und Behoben nicht | *Recovery operations* und *Update operations* in der Action ergänzen |

## Entwicklung

```bash
python -m venv venv
venv/bin/pip install pytest-homeassistant-custom-component pyyaml
venv/bin/pytest
python zabbix/build_media_type.py   # YAML nach Änderung des Skripts neu erzeugen
```

Die Skript-Tests brauchen Node.js (ohne Node werden sie übersprungen).

## Lizenz

MIT, siehe [LICENSE](LICENSE). Nicht mit Zabbix SIA verbunden.
