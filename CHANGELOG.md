# Changelog

## 0.2.0

- New **Zabbix dashboard** in the sidebar (admins), shipped with the integration, no setup. Shows open problems by severity, affected hosts, last event, links to the Zabbix frontend and to each problem, a severity filter and one tab per Zabbix source. Colours follow the Home Assistant theme. Can be switched off with *Show dashboard in the sidebar*.
- New option *Zabbix address*: base URL used for the links; empty uses the address Zabbix announces.
- New service `zabbix_notify.dismiss_problem` (and a ✕ button in the dashboard) to remove a problem whose recovery never arrived, for example when the trigger was disabled in Zabbix. Nothing is sent, and a late duplicate is ignored.
- The integration now shows the Zabbix logo instead of a bell.
- The open-problems sensor has more attributes (`affected_hosts`, `zabbix_url`, `problems_url`; per problem `trigger_id`, `acknowledged`, `since`, `url`) and holds up to 50 problems. The large attributes are excluded from the recorder.
- Internal version constant and manifest version are in sync again.

## 0.1.3

- The notification center was renamed from *DORALAB Notify* (`doralab_notify`) to **Enhanced Notify** (`enhanced_notify`). The bridge uses `enhanced_notify.send` and still falls back to `doralab_notify.send`, so nothing breaks while you switch. No settings need to change.

## 0.1.2

- New option *Icon of the notifications*: shows an icon name or an image (for example `/local/zabbix.png`) for the Zabbix types in the DORALAB notification center instead of the category icon. Needs notification center 0.3.0-beta.3 or newer, older versions ignore it.

## 0.1.1

- Fix: the Zabbix media type import now contains message templates for problem, recovery and update. Without them Zabbix refused to send ("No message defined for media type").

## 0.1.0

- First version: webhook endpoint with token, problem / update / resolved events, one notification per problem
- Optional bridge to the DORALAB notification center (types appear on the first event, no push recipients by default)
- Standalone delivery via persistent notifications and chosen `notify` services
- Sensors for open problems and last event received, `zabbix_notify_event` bus event
- Importable Zabbix webhook media type
