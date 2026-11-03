/*
 * Zabbix Notify dashboard (sidebar panel).
 *
 * Plain web component without dependencies. It reads the "open problems" sensor of
 * every configured Zabbix source and shows the problem list, affected hosts and links
 * to Zabbix. All colours come from Home Assistant theme variables, so light and dark
 * mode (and custom themes) apply automatically.
 */

const LOGO_URL = new URL("zabbix.png", import.meta.url).href;

const SEVERITIES = [
  "not_classified",
  "information",
  "warning",
  "average",
  "high",
  "disaster",
];

// Standard Zabbix severity colours.
const SEVERITY_COLORS = {
  not_classified: "#97AAB3",
  information: "#7499FF",
  warning: "#FFC859",
  average: "#FFA059",
  high: "#E97659",
  disaster: "#E45959",
};

const TEXTS = {
  de: {
    title: "Zabbix",
    open_problems: "Offene Probleme",
    hosts: "Betroffene Hosts",
    last_event: "Letztes Ereignis",
    never: "noch keins",
    all_good: "Alles in Ordnung",
    highest: "Höchster Schweregrad: {severity}",
    none_title: "Keine offenen Probleme",
    none_text: "Zabbix meldet aktuell nichts.",
    open_zabbix: "Zabbix öffnen",
    open_problems_zabbix: "Alle Probleme in Zabbix",
    open_event: "In Zabbix öffnen",
    all: "Alle",
    since: "seit {time}",
    just_now: "gerade eben",
    ago: "vor {time}",
    acknowledged: "Bestätigt",
    dismiss: "Als erledigt entfernen",
    dismiss_ask: "Nur aus Home Assistant entfernen? In Zabbix ändert sich nichts.",
    dismiss_yes: "Entfernen",
    dismiss_no: "Abbrechen",
    dismiss_failed: "Entfernen fehlgeschlagen: {error}",
    more: "und {n} weitere Probleme – alle in Zabbix ansehen",
    no_source_title: "Keine Zabbix-Quelle gefunden",
    no_source_text:
      "Richte die Integration „Zabbix Notify“ ein oder lade sie neu, damit hier Probleme erscheinen.",
    unavailable: "Der Sensor ist gerade nicht verfügbar.",
    d: "Tag",
    ds: "Tage",
    h: "Std.",
    min: "Min.",
    severity: {
      not_classified: "Nicht klassifiziert",
      information: "Information",
      warning: "Warnung",
      average: "Durchschnitt",
      high: "Hoch",
      disaster: "Katastrophe",
    },
  },
  en: {
    title: "Zabbix",
    open_problems: "Open problems",
    hosts: "Affected hosts",
    last_event: "Last event",
    never: "none yet",
    all_good: "All clear",
    highest: "Highest severity: {severity}",
    none_title: "No open problems",
    none_text: "Zabbix currently reports nothing.",
    open_zabbix: "Open Zabbix",
    open_problems_zabbix: "All problems in Zabbix",
    open_event: "Open in Zabbix",
    all: "All",
    since: "for {time}",
    just_now: "just now",
    ago: "{time} ago",
    acknowledged: "Acknowledged",
    dismiss: "Remove as resolved",
    dismiss_ask: "Remove from Home Assistant only? Nothing changes in Zabbix.",
    dismiss_yes: "Remove",
    dismiss_no: "Cancel",
    dismiss_failed: "Removing failed: {error}",
    more: "and {n} more problems – view all in Zabbix",
    no_source_title: "No Zabbix source found",
    no_source_text:
      "Set up or reload the “Zabbix Notify” integration so that problems show up here.",
    unavailable: "The sensor is currently unavailable.",
    d: "day",
    ds: "days",
    h: "h",
    min: "min",
    severity: {
      not_classified: "Not classified",
      information: "Information",
      warning: "Warning",
      average: "Average",
      high: "High",
      disaster: "Disaster",
    },
  },
};

const ICONS = {
  open: "mdi:open-in-new",
  close: "mdi:close",
  check: "mdi:check-circle",
  alert: "mdi:alert-circle-outline",
  server: "mdi:server",
  clock: "mdi:clock-outline",
  ack: "mdi:check",
};

const CSS = `
:host {
  display: block;
  min-height: 100%;
  box-sizing: border-box;
  background: var(--primary-background-color);
  color: var(--primary-text-color);
  --zx-radius: var(--ha-card-border-radius, 18px);
  --zx-card: var(--ha-card-background, var(--card-background-color, #fff));
  --zx-border: var(--ha-card-border-color, var(--divider-color, rgba(127, 127, 127, 0.25)));
  --zx-border-width: var(--ha-card-border-width, 1px);
  --zx-shadow: var(--ha-card-box-shadow, var(--dl-shadow, 0 1px 4px rgba(0, 0, 0, 0.06)));
  --zx-muted: var(--secondary-text-color);
  --zx-ok: var(--success-color, #43a047);
  --zx-accent: var(--primary-color, #03a9f4);
}
* { box-sizing: border-box; }
.bar {
  position: sticky; top: 0; z-index: 2;
  display: flex; align-items: center; gap: 12px;
  height: var(--header-height, 56px); padding: 0 16px;
  background: var(--app-header-background-color, var(--primary-color));
  color: var(--app-header-text-color, var(--text-primary-color, #fff));
}
.bar img { width: 28px; height: 28px; border-radius: 7px; display: block; }
.bar h1 { margin: 0; font-size: 20px; font-weight: 500; line-height: 1; }
.bar .source { margin-left: auto; opacity: 0.8; font-size: 14px; }
main { max-width: 1200px; margin: 0 auto; padding: 16px; display: grid; gap: 16px; }
.card {
  background: var(--zx-card);
  border: var(--zx-border-width) solid var(--zx-border);
  border-radius: var(--zx-radius);
  box-shadow: var(--zx-shadow);
}
.tabs { display: flex; flex-wrap: wrap; gap: 8px; }
.tab, .chip {
  font: inherit; color: inherit; cursor: pointer;
  border: 1px solid var(--zx-border); background: var(--zx-card);
  border-radius: 999px; padding: 6px 14px; line-height: 1.2;
  display: inline-flex; align-items: center; gap: 8px;
}
.tab[aria-pressed="true"], .chip[aria-pressed="true"] {
  background: color-mix(in srgb, var(--zx-accent) 16%, var(--zx-card));
  border-color: var(--zx-accent);
}
.chip .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--c, var(--zx-muted)); }
.chip .n { font-variant-numeric: tabular-nums; color: var(--zx-muted); }
button:focus-visible, a:focus-visible { outline: 2px solid var(--zx-accent); outline-offset: 2px; }

.kpis { display: grid; gap: 16px; grid-template-columns: repeat(4, minmax(0, 1fr)); }
.kpi { position: relative; padding: 16px 18px 16px 22px; overflow: hidden; min-width: 0; }
.kpi::before {
  content: ""; position: absolute; inset: 0 auto 0 0; width: 6px;
  background: var(--c, var(--zx-muted));
}
.kpi .label {
  display: flex; align-items: center; gap: 6px;
  color: var(--zx-muted); font-size: 13px; letter-spacing: 0.02em;
}
.kpi .label ha-icon { --mdc-icon-size: 18px; }
.kpi .value {
  font-size: 34px; font-weight: 600; line-height: 1.15; margin-top: 6px;
  font-variant-numeric: tabular-nums;
}
.kpi .value.text { font-size: 22px; line-height: 1.4; margin-top: 8px; }
.kpi .note { color: var(--zx-muted); font-size: 13px; margin-top: 4px; overflow-wrap: anywhere; }
.kpi.links { display: flex; flex-direction: column; gap: 8px; justify-content: center; }
.btn {
  font: inherit; text-decoration: none; cursor: pointer; text-align: center;
  display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  padding: 9px 14px; border-radius: 10px; border: 1px solid var(--zx-border);
  color: var(--primary-text-color); background: transparent;
}
.btn.primary { background: var(--zx-accent); border-color: var(--zx-accent); color: var(--text-primary-color, #fff); }
.btn ha-icon { --mdc-icon-size: 18px; }
.btn:hover { filter: brightness(0.96); }

.filters { display: flex; flex-wrap: wrap; gap: 8px; }

.list { list-style: none; margin: 0; padding: 0; overflow: hidden; }
.row {
  position: relative; display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 12px;
  padding: 14px 16px 14px 22px; align-items: start;
  background: color-mix(in srgb, var(--c) 7%, transparent);
}
.row + .row { border-top: 1px solid var(--zx-border); }
.row::before { content: ""; position: absolute; inset: 0 auto 0 0; width: 6px; background: var(--c); }
.top { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 10px; font-size: 13px; }
.pill {
  display: inline-flex; align-items: center; gap: 6px; padding: 2px 10px; border-radius: 999px;
  background: color-mix(in srgb, var(--c) 24%, transparent); font-weight: 600;
}
.pill i { width: 8px; height: 8px; border-radius: 50%; background: var(--c); }
.host { display: inline-flex; align-items: center; gap: 4px; color: var(--primary-text-color); }
.host ha-icon { --mdc-icon-size: 16px; color: var(--zx-muted); }
.age { color: var(--zx-muted); margin-left: auto; white-space: nowrap; font-variant-numeric: tabular-nums; }
.name { font-weight: 600; font-size: 15px; margin-top: 6px; overflow-wrap: anywhere; }
.sub { color: var(--zx-muted); font-size: 13px; margin-top: 4px; display: flex; flex-wrap: wrap; gap: 4px 12px; overflow-wrap: anywhere; }
.ack { display: inline-flex; align-items: center; gap: 4px; color: var(--zx-ok); }
.ack ha-icon { --mdc-icon-size: 15px; }
.actions { display: flex; align-items: center; gap: 4px; }
.icon-btn {
  display: inline-flex; align-items: center; justify-content: center; cursor: pointer;
  width: 36px; height: 36px; border-radius: 50%; border: none; background: transparent;
  color: var(--zx-muted); text-decoration: none; padding: 0;
}
.icon-btn:hover { background: color-mix(in srgb, var(--primary-text-color) 8%, transparent); color: var(--primary-text-color); }
.confirm { display: flex; align-items: center; gap: 8px; font-size: 13px; flex-wrap: wrap; justify-content: flex-end; max-width: 280px; }
.confirm .btn { padding: 6px 12px; font-size: 13px; }
.confirm .btn.danger { background: var(--error-color, #db4437); border-color: var(--error-color, #db4437); color: #fff; }
.more { padding: 12px 22px; border-top: 1px solid var(--zx-border); font-size: 14px; }
.more a { color: var(--zx-accent); }

.state { padding: 36px 20px; text-align: center; }
.state .badge {
  width: 64px; height: 64px; border-radius: 50%; margin: 0 auto 12px;
  display: grid; place-items: center;
  background: color-mix(in srgb, var(--c, var(--zx-ok)) 18%, transparent); color: var(--c, var(--zx-ok));
}
.state .badge ha-icon { --mdc-icon-size: 34px; }
.state h2 { margin: 0 0 4px; font-size: 20px; font-weight: 600; }
.state p { margin: 0; color: var(--zx-muted); }

@media (max-width: 900px) {
  .kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .kpi.first { grid-column: 1 / -1; }
  .kpi.links { grid-column: 1 / -1; flex-direction: row; flex-wrap: wrap; }
  .kpi.links .btn { flex: 1 1 180px; }
}
@media (max-width: 560px) {
  main { padding: 12px; gap: 12px; }
  .row { padding-right: 8px; gap: 4px; }
  .row .actions { flex-direction: column; align-items: flex-end; }
  .age { margin-left: 0; }
  .confirm { max-width: 190px; justify-content: flex-start; }
}
@media (prefers-reduced-motion: no-preference) {
  .btn, .icon-btn, .tab, .chip { transition: background-color 0.15s, filter 0.15s; }
}
`;

const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch],
  );

// Only plain web links may end up in a href.
const safeUrl = (value) => (/^https?:\/\//i.test(value || "") ? value : null);

const icon = (name) => `<ha-icon icon="${name}"></ha-icon>`;

class ZabbixNotifyPanel extends HTMLElement {
  constructor() {
    super();
    this._hass = undefined;
    this._narrow = false;
    this._source = undefined; // entity_id of the selected source
    this._filter = undefined; // severity key
    this._confirm = undefined; // event_id waiting for confirmation
    this._signature = "";
    this._timer = undefined;
    this.attachShadow({ mode: "open" });
    this.shadowRoot.innerHTML = `
      <style>${CSS}</style>
      <div class="bar">
        <ha-menu-button></ha-menu-button>
        <img src="${LOGO_URL}" alt="">
        <h1></h1>
        <span class="source"></span>
      </div>
      <main></main>`;
    this._menu = this.shadowRoot.querySelector("ha-menu-button");
    this._main = this.shadowRoot.querySelector("main");
    this.shadowRoot.addEventListener("click", (ev) => this._onClick(ev));
  }

  set hass(hass) {
    this._hass = hass;
    if (this._menu) this._menu.hass = hass;
    this._update();
  }

  set narrow(narrow) {
    this._narrow = narrow;
    if (this._menu) this._menu.narrow = narrow;
    this._update();
  }

  // Provided by Home Assistant for panels, unused here.
  set panel(_panel) {}
  set route(_route) {}

  connectedCallback() {
    this._timer = window.setInterval(() => this._tick(), 20000);
    this._update(true);
  }

  disconnectedCallback() {
    window.clearInterval(this._timer);
    this._timer = undefined;
  }

  // ------------------------------------------------------------------ data

  get _lang() {
    const code = this._hass?.locale?.language || this._hass?.language || "en";
    return code.toLowerCase().startsWith("de") ? "de" : "en";
  }

  get _t() {
    return TEXTS[this._lang];
  }

  _fmt(text, values) {
    return text.replace(/\{(\w+)\}/g, (_, key) => values[key]);
  }

  /** Every configured Zabbix source, found through its "open problems" sensor. */
  _sources() {
    const hass = this._hass;
    if (!hass) return [];
    const registry = hass.entities || {};
    let ids = Object.keys(registry).filter(
      (id) =>
        registry[id].platform === "zabbix_notify" &&
        registry[id].translation_key === "open_problems" &&
        hass.states[id],
    );
    if (!ids.length) {
      // Fallback if the entity registry is not exposed: recognise the sensor by its attributes.
      ids = Object.keys(hass.states).filter(
        (id) =>
          id.startsWith("sensor.") &&
          hass.states[id].attributes.by_severity &&
          Array.isArray(hass.states[id].attributes.problems),
      );
    }
    return ids.sort().map((id) => {
      const device = hass.devices?.[registry[id]?.device_id];
      const lastId = Object.keys(registry).find(
        (other) =>
          registry[other].platform === "zabbix_notify" &&
          registry[other].translation_key === "last_received" &&
          registry[other].device_id === registry[id]?.device_id,
      );
      return {
        id,
        title:
          device?.name_by_user || device?.name || hass.states[id].attributes.friendly_name || id,
        state: hass.states[id],
        last: lastId ? hass.states[lastId] : undefined,
      };
    });
  }

  _selected(sources) {
    return sources.find((s) => s.id === this._source) || sources[0];
  }

  // ------------------------------------------------------------- rendering

  _update(force = false) {
    if (!this._hass || !this.isConnected) return;
    const sources = this._sources();
    const current = this._selected(sources);
    const signature = JSON.stringify([
      this._lang,
      this._narrow,
      this._filter,
      this._confirm,
      current?.id,
      sources.map((s) => [s.id, s.title, s.state.last_updated, s.last?.state]),
    ]);
    if (!force && signature === this._signature) return;
    this._signature = signature;
    this._render(sources, current);
  }

  _render(sources, current) {
    const t = this._t;
    const root = this.shadowRoot;
    const focusKey = root.activeElement?.dataset?.key;

    root.querySelector("h1").textContent = t.title;
    root.querySelector(".source").textContent = sources.length > 1 && current ? current.title : "";
    this._menu.hidden = !this._narrow;

    if (!current) {
      this._main.innerHTML = `<div class="card state" style="--c: var(--zx-muted)">
        <div class="badge">${icon(ICONS.alert)}</div>
        <h2>${esc(t.no_source_title)}</h2><p>${esc(t.no_source_text)}</p></div>`;
      return;
    }

    const state = current.state;
    const attrs = state.attributes;
    const unavailable = state.state === "unavailable" || state.state === "unknown";
    const total = unavailable ? 0 : Number(state.state) || 0;
    const problems = Array.isArray(attrs.problems) ? attrs.problems : [];
    const bySeverity = attrs.by_severity || {};
    const hosts = Array.isArray(attrs.affected_hosts) ? attrs.affected_hosts : [];
    const baseUrl = safeUrl(attrs.zabbix_url);
    const problemsUrl = safeUrl(attrs.problems_url);

    const highest = [...SEVERITIES].reverse().find((key) => bySeverity[key] > 0);
    const color = total && highest ? SEVERITY_COLORS[highest] : "var(--zx-ok)";

    const visible = this._filter ? problems.filter((p) => p.severity === this._filter) : problems;
    const hidden = Math.max(0, total - problems.length);

    const tabs =
      sources.length > 1
        ? `<div class="tabs" role="group">${sources
            .map(
              (s) =>
                `<button class="tab" data-key="tab-${esc(s.id)}" data-source="${esc(s.id)}" aria-pressed="${
                  s.id === current.id
                }">${esc(s.title)}</button>`,
            )
            .join("")}</div>`
        : "";

    const chips = total
      ? `<div class="filters" role="group">
          <button class="chip" data-key="chip-all" data-filter="" aria-pressed="${!this._filter}">
            ${esc(t.all)} <span class="n">${total}</span></button>
          ${SEVERITIES.filter((key) => bySeverity[key] > 0)
            .reverse()
            .map(
              (key) => `<button class="chip" data-key="chip-${key}" data-filter="${key}"
                aria-pressed="${this._filter === key}" style="--c: ${SEVERITY_COLORS[key]}">
                <span class="dot"></span>${esc(t.severity[key])}
                <span class="n">${bySeverity[key]}</span></button>`,
            )
            .join("")}
        </div>`
      : "";

    const lastText = current.last?.state && !["unknown", "unavailable"].includes(current.last.state)
      ? `<span data-ago="${esc(current.last.state)}">${esc(this._ago(current.last.state))}</span>`
      : esc(t.never);

    const links = `<div class="card kpi links" style="--c: var(--zx-accent)">
        ${
          baseUrl
            ? `<a class="btn primary" href="${esc(baseUrl)}" target="_blank" rel="noopener noreferrer">${icon(
                ICONS.open,
              )}${esc(t.open_zabbix)}</a>`
            : ""
        }
        ${
          problemsUrl
            ? `<a class="btn" href="${esc(problemsUrl)}" target="_blank" rel="noopener noreferrer">${icon(
                ICONS.alert,
              )}${esc(t.open_problems_zabbix)}</a>`
            : ""
        }
      </div>`;

    let body;
    if (unavailable) {
      body = `<div class="card state" style="--c: var(--zx-muted)"><div class="badge">${icon(
        ICONS.alert,
      )}</div><h2>${esc(t.unavailable)}</h2></div>`;
    } else if (!total) {
      body = `<div class="card state"><div class="badge">${icon(ICONS.check)}</div>
        <h2>${esc(t.none_title)}</h2><p>${esc(t.none_text)}</p></div>`;
    } else {
      body = `<ul class="card list">${visible.map((p) => this._row(p)).join("")}${
        !this._filter && hidden
          ? `<li class="more">${esc(this._fmt(t.more, { n: hidden }))}${
              problemsUrl
                ? ` <a href="${esc(problemsUrl)}" target="_blank" rel="noopener noreferrer">→</a>`
                : ""
            }</li>`
          : ""
      }</ul>`;
    }

    this._main.innerHTML = `${tabs}
      <section class="kpis">
        <div class="card kpi first" style="--c: ${color}">
          <div class="label">${icon(ICONS.alert)}${esc(t.open_problems)}</div>
          <div class="value">${total}</div>
          <div class="note">${esc(
            total && highest
              ? this._fmt(t.highest, { severity: t.severity[highest] })
              : t.all_good,
          )}</div>
        </div>
        <div class="card kpi" style="--c: ${hosts.length ? color : "var(--zx-ok)"}">
          <div class="label">${icon(ICONS.server)}${esc(t.hosts)}</div>
          <div class="value">${hosts.length}</div>
          <div class="note">${esc(hosts.slice(0, 4).join(", "))}${hosts.length > 4 ? " …" : ""}</div>
        </div>
        <div class="card kpi" style="--c: var(--zx-muted)">
          <div class="label">${icon(ICONS.clock)}${esc(t.last_event)}</div>
          <div class="value text">${lastText}</div>
        </div>
        ${links}
      </section>
      ${chips}
      ${body}`;

    if (focusKey) this.shadowRoot.querySelector(`[data-key="${CSS_ESCAPE(focusKey)}"]`)?.focus();
  }

  _row(problem) {
    const t = this._t;
    const key = SEVERITIES.includes(problem.severity) ? problem.severity : "not_classified";
    const url = safeUrl(problem.url);
    const confirming = this._confirm === problem.event_id;
    const actions = confirming
      ? `<div class="confirm"><span>${esc(t.dismiss_ask)}</span>
          <button class="btn" data-key="no-${esc(problem.event_id)}" data-cancel>${esc(t.dismiss_no)}</button>
          <button class="btn danger" data-key="yes-${esc(problem.event_id)}" data-dismiss="${esc(
            problem.event_id,
          )}">${esc(t.dismiss_yes)}</button></div>`
      : `${
          url
            ? `<a class="icon-btn" href="${esc(url)}" target="_blank" rel="noopener noreferrer"
                title="${esc(t.open_event)}" aria-label="${esc(t.open_event)}">${icon(ICONS.open)}</a>`
            : ""
        }<button class="icon-btn" data-key="ask-${esc(problem.event_id)}" data-ask="${esc(
          problem.event_id,
        )}" title="${esc(t.dismiss)}" aria-label="${esc(t.dismiss)}">${icon(ICONS.close)}</button>`;
    return `<li class="row" style="--c: ${SEVERITY_COLORS[key]}">
      <div>
        <div class="top">
          <span class="pill"><i></i>${esc(t.severity[key])}</span>
          ${
            problem.host
              ? `<span class="host">${icon(ICONS.server)}${esc(problem.host)}</span>`
              : ""
          }
          ${
            problem.since
              ? `<span class="age" data-since="${esc(problem.since)}">${esc(this._since(problem.since))}</span>`
              : ""
          }
        </div>
        <div class="name">${esc(problem.name || "–")}</div>
        ${
          problem.opdata || problem.acknowledged
            ? `<div class="sub">${problem.opdata ? `<span>${esc(problem.opdata)}</span>` : ""}${
                problem.acknowledged
                  ? `<span class="ack">${icon(ICONS.ack)}${esc(t.acknowledged)}</span>`
                  : ""
              }</div>`
            : ""
        }
      </div>
      <div class="actions">${actions}</div>
    </li>`;
  }

  // ------------------------------------------------------------------ time

  _duration(ms) {
    const t = this._t;
    const minutes = Math.max(0, Math.floor(ms / 60000));
    if (minutes < 1) return null;
    const days = Math.floor(minutes / 1440);
    const hours = Math.floor((minutes % 1440) / 60);
    const mins = minutes % 60;
    if (days) return `${days} ${days === 1 ? t.d : t.ds}${hours ? ` ${hours} ${t.h}` : ""}`;
    if (hours) return `${hours} ${t.h}${mins ? ` ${mins} ${t.min}` : ""}`;
    return `${mins} ${t.min}`;
  }

  _since(iso) {
    const time = this._duration(Date.now() - new Date(iso).getTime());
    return time ? this._fmt(this._t.since, { time }) : this._t.just_now;
  }

  _ago(iso) {
    const time = this._duration(Date.now() - new Date(iso).getTime());
    return time ? this._fmt(this._t.ago, { time }) : this._t.just_now;
  }

  /** Keep the relative times fresh without rebuilding the list. */
  _tick() {
    this.shadowRoot.querySelectorAll("[data-since]").forEach((el) => {
      el.textContent = this._since(el.dataset.since);
    });
    this.shadowRoot.querySelectorAll("[data-ago]").forEach((el) => {
      el.textContent = this._ago(el.dataset.ago);
    });
  }

  // ---------------------------------------------------------------- events

  _onClick(ev) {
    const target = ev.target.closest("[data-source],[data-filter],[data-ask],[data-cancel],[data-dismiss]");
    if (!target) return;
    const data = target.dataset;
    if (data.source !== undefined) {
      this._source = data.source;
      this._filter = undefined;
      this._confirm = undefined;
    } else if (data.filter !== undefined) {
      this._filter = data.filter && data.filter !== this._filter ? data.filter : undefined;
    } else if (data.ask !== undefined) {
      this._confirm = data.ask;
    } else if (data.cancel !== undefined) {
      this._confirm = undefined;
    } else if (data.dismiss !== undefined) {
      this._dismiss(data.dismiss);
      return;
    }
    this._update();
  }

  async _dismiss(eventId) {
    const current = this._selected(this._sources());
    this._confirm = undefined;
    try {
      await this._hass.callService("zabbix_notify", "dismiss_problem", {
        event_id: eventId,
        entry_id: current?.state.attributes.entry_id,
      });
    } catch (err) {
      window.alert(this._fmt(this._t.dismiss_failed, { error: err?.message || err }));
    }
    this._update(true);
  }
}

// CSS.escape is available in every browser that runs Home Assistant.
const CSS_ESCAPE = (value) => (window.CSS?.escape ? window.CSS.escape(value) : value);

if (!customElements.get("zabbix-notify-panel")) {
  customElements.define("zabbix-notify-panel", ZabbixNotifyPanel);
}
