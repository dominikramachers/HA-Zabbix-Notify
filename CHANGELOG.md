# Changelog

## 0.1.0

- First version: webhook endpoint with token, problem / update / resolved events, one notification per problem
- Optional bridge to the DORALAB notification center (types appear on the first event, no push recipients by default)
- Standalone delivery via persistent notifications and chosen `notify` services
- Sensors for open problems and last event received, `zabbix_notify_event` bus event
- Importable Zabbix webhook media type
