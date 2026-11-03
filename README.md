# Zabbix Notify for Home Assistant

[Deutsche Version](README.de.md)

Receive Zabbix **problem, update and recovery events** in Home Assistant through a webhook media type.
Zabbix decides *what* is reported (hosts, severities, tags), Home Assistant decides *who* gets it and *how*.

- One notification **per problem**: the same entry is updated when the problem is acknowledged, changed or resolved
- Works on its own: persistent notifications, optional push to chosen `notify` services, sensors and a bus event for your automations
- Optional bridge to the **Enhanced Notify notification center** (`enhanced_notify`): the three Zabbix types appear there on the first event, and you pick the recipients per type. Nobody gets a push until you select people.
- Webhook secured with a token, one webhook per Zabbix server, German and English texts
- Includes a ready-to-import Zabbix media type (no external dependencies)

## How it works

```
Zabbix action ──► media type "Home Assistant (Zabbix Notify)" ──POST JSON──► HA webhook
                                                                              │
                          ┌───────────────────────────────────────────────────┤
                          ▼                                                   ▼
              enhanced_notify (if installed)                  persistent notification / notify services
                 types: zabbix_problem · zabbix_update · zabbix_resolved
```

| Zabbix event | Notification type | Behaviour |
|---|---|---|
| Problem created | `zabbix_problem` | new entry, title `High: srv01` |
| Problem updated (acknowledged, commented, severity changed, ...) | `zabbix_update` | same entry updated, marked unread again |
| Problem resolved | `zabbix_resolved` | same entry updated; without the notification center the persistent notification is dismissed |

## Requirements

- Home Assistant 2025.1 or newer
- A Zabbix server that can reach Home Assistant over HTTP(S) (a VPN is fine). The media type uses the Zabbix 7.0 export format, which newer versions can import.

## Installation

**HACS:** HACS → ⋮ → *Custom repositories* → add `https://github.com/dominikramachers/HA-Zabbix-Notify` as category *Integration* → install → restart Home Assistant.

**Manual:** copy `custom_components/zabbix_notify` into your `config/custom_components` folder and restart.

**Together with the notification center:** the two are separate integrations and are installed independently, in any order. Install [Enhanced Notify](https://github.com/dominikramachers/ha-enhanced-notify) (`enhanced_notify`, formerly *DORALAB Notify*) the same way via HACS and add both under *Devices & services*. Zabbix Notify detects the notification center on every event, so nothing needs to be linked, and it keeps working if the notification center is removed later.

## Setup

### 1. Home Assistant

1. *Settings → Devices & services → Add integration → Zabbix Notify*, enter a name.
2. Copy the **webhook URL** and the **token** that are shown. You can display them again later under *Configure*.

Use an address of Home Assistant that your Zabbix server can reach. The shown URL uses your internal URL; replace the host if Zabbix connects differently. Use a valid certificate or plain HTTP inside a trusted network, since the Zabbix script cannot skip certificate checks.

### 2. Zabbix

1. **Import the media type:** *Alerts → Media types → Import* → `zabbix/media_type_home_assistant.yaml`.
2. **Define macros** (*Administration → Macros*):

   | Macro | Value |
   |---|---|
   | `{$HA_NOTIFY_URL}` | the webhook URL from step 1 |
   | `{$HA_NOTIFY_TOKEN}` | the token, type *Secret text* |
   | `{$ZABBIX.URL}` | address of your Zabbix frontend, e.g. `https://zabbix.example.com` (used for the link in notifications) |
   | `{$HA_NOTIFY_PROXY}` | optional HTTP proxy, leave undefined if not needed |

3. **Create a technical user** (*Users → Users*), e.g. `ha-notify`:
   - its user group needs at least **Read** permission on the host groups you want to report (Zabbix only notifies about hosts the user may see)
   - add a media entry: type *Home Assistant (Zabbix Notify)*, *Send to* any text (e.g. `homeassistant`), **all severities ticked**, active period `1-7,00:00-24:00`
4. **Configure an action** (*Alerts → Actions → Trigger actions*): use *Operations*, *Recovery operations* **and** *Update operations*, each with *Send message* to the user `ha-notify` via this media type. Leave *Custom message* off. The media type builds its own text, but Zabbix refuses to send without a message template per event kind ("No message defined for media type"). The import contains these templates. If you created the media type by hand, add *Problem*, *Problem recovery* and *Problem update* templates on its *Message templates* tab (any text works). Put your filters (severity, host groups, tags, maintenance) into the action conditions.
5. **Test:** open the media type, press *Test*. It should answer `OK: test`, and the sensor *Last event received* in Home Assistant updates. The test does not create a notification.

Tip: set *Attempts* of the media type to 5 and the retry interval to 30 s so short Home Assistant restarts do not lose events. Keep *Concurrent sessions* at 1 to preserve the order of events.

If you prefer to create the media type by hand, use the script `zabbix/ha_notify_webhook.js` and the parameters listed in `zabbix/build_media_type.py`.

### 3. Choose who gets notified

**With the Enhanced Notify notification center:** after the first event the types *Zabbix: Problem*, *Zabbix: Problem updated* and *Zabbix: Problem resolved* appear in the notification center. Open its overview and select the people and the push mode per type. The default is nobody.

**Without it:** open *Configure* on the integration and pick `notify` services per event kind (for example `mobile_app_my_phone`). Empty means no push. Problems of severity High and above are sent as time-sensitive.

### Icon in the notification center

Automatically created types get the icon of their category (a gear for *System*). Under *Configure* you can set an **icon** instead: an icon name such as `mdi:server`, or an image. For an image, copy a square PNG to `config/www/` of Home Assistant (for example `config/www/zabbix.png`) and enter `/local/zabbix.png`. The image is shown in the notification list and in the admin overview, and a changed option also applies to the already existing types after the next event. Empty means the category icon. This needs notification center 0.3.0-beta.3 or newer; older versions ignore the option.

The repository does not ship the Zabbix logo, because it is a trademark of Zabbix SIA. Use the logo you are allowed to use yourself.

## Options

| Option | Meaning |
|---|---|
| Text language | automatic (Home Assistant language), German or English |
| Use the Enhanced Notify notification center | bridge on/off (only active when `enhanced_notify.send` or the former `doralab_notify.send` exists) |
| Show Home Assistant notifications | persistent notifications when no notification center is used |
| Link to Zabbix | adds a link to the problem in the Zabbix frontend |
| Icon of the notifications | icon of the three Zabbix types in the notification center, see below |
| Push services per kind | used without the notification center |
| Generate a new token | invalidates the old token |

## Entities and events

- `sensor.<name>_open_problems`: number of open problems, attributes `by_severity` and `problems` (up to 20)
- `sensor.<name>_last_event_received`: timestamp of the last call from Zabbix (diagnostic)
- Event `zabbix_notify_event` with `kind` (`problem`, `update`, `resolved`), `event_id`, `host`, `name`, `severity` (0-5), `severity_name`, `opdata`, `update_action`, `update_message`, `tags`, `url`

```yaml
triggers:
  - trigger: event
    event_type: zabbix_notify_event
    event_data:
      kind: problem
      severity_name: disaster
actions:
  - action: light.turn_on
    target: { entity_id: light.hallway }
    data: { color_name: red }
```

Open problems are derived from the events Home Assistant has received. Events that Zabbix could not deliver while Home Assistant was down are lost after the retries, so the counter can differ from Zabbix in that case.

## Troubleshooting

| Symptom | Cause |
|---|---|
| Zabbix reports `HTTP 401` | wrong or missing token (`{$HA_NOTIFY_TOKEN}`) |
| `Unexpected response, check the webhook ID` | Home Assistant answers unknown webhook IDs with an empty `200`; check the ID in `{$HA_NOTIFY_URL}` |
| `Parameter "url" is empty` | the macro is not defined, or defined on a host instead of globally |
| Nothing arrives, no error | user media inactive or a severity not ticked, user lacks Read permission on the host group, or *Recovery/Update operations* are missing in the action. Check *Reports → Action log*. |
| Problems arrive but no update or resolve | add *Recovery operations* and *Update operations* to the action |

## Development

```bash
python -m venv venv
venv/bin/pip install pytest-homeassistant-custom-component pyyaml
venv/bin/pytest
python zabbix/build_media_type.py   # regenerate the YAML after editing the script
```

The script tests need Node.js (they are skipped without it).

## License

MIT, see [LICENSE](LICENSE). Not affiliated with Zabbix SIA.
