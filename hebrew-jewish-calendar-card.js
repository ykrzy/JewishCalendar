import { LitElement, html, css } from "https://unpkg.com/lit-element@3.0.2/lit-element.js?module";
import { HDate, HebrewCalendar, Location } from "https://cdn.skypack.dev/@hebcal/core";

class HebrewJewishCalendarCard extends LitElement {
  static get properties() {
    return {
      hass: {},
      config: {},
      anchor: { type: Object },    // HDate of Rosh Chodesh in view
      days:   { type: Array },     // [{hdate, greg, parasha, candle, havdalah, holiday}]
    };
  }

  setConfig(cfg) {
    this.config = { show_header: true, ...cfg };
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.anchor) {
      // First render → build current month
      const today = new Date();
      const hToday = new HDate(today);
      this.anchor = this._roshChodesh(hToday);
      this._buildMonth();
    }
  }

  /* ───────── helpers ───────── */
  _roshChodesh(hdate) {
    const d = hdate.clone();
    while (d.day > 1) d.setDate(d.day - 1);
    return d;
  }

  _nextMonthAnchor(dir) {
    const temp = this.anchor.clone();
    if (dir > 0) {
      temp.setMonth(temp.month + 1);
    } else {
      temp.setMonth(temp.month - 1);
    }
    return this._roshChodesh(temp);
  }

  _buildMonth() {
    const loc = new Location(
      this._hass.config.location_name || "HA",
      this._hass.config.latitude,
      this._hass.config.longitude,
      this._hass.config.time_zone,
      0
    );

    const days = [];
    let hd = this.anchor.clone();
    const month = hd.month;
    while (hd.month === month) {
      const greg = hd.greg();
      const cal = new HebrewCalendar(hd);   // fetch holidays/parasha
      const holiday = cal.holidays().map(h => h.render("he"))[0] || "";
      const parasha = cal.getLeyning({ israel: true })?.parsha || "";
      const z = HebrewCalendar.getZmanim({ date: greg, location: loc });
      const candle = z?.candle_lighting ? z.candle_lighting.toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"}) : "";
      const havdalah = z?.havdalah ? z.havdalah.toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"}) : "";
      days.push({ hd: hd.renderGematriya(), greg, parasha, holiday, candle, havdalah });
      hd = hd.next();
    }
    this.days = days;
  }

  _weeks() {
    const weeks = [];
    let row = [];
    if (!this.days?.length) return weeks;

    const firstWeekday = this.days[0].greg.getDay(); // 0=Sun
    for (let i = 0; i < firstWeekday; i++) row.push(null);

    this.days.forEach(d => {
      row.push(d);
      if (row.length === 7) {
        weeks.push(row);
        row = [];
      }
    });
    while (row.length && row.length < 7) row.push(null);
    if (row.length) weeks.push(row);
    return weeks;
  }

  _nav(dir) {          // dir +1 / -1
    this.anchor = this._nextMonthAnchor(dir);
    this._buildMonth();
  }

  /* ───────── render ───────── */
  render() {
    if (!this.days) return html`<ha-card><div class="loading">Loading…</div></ha-card>`;

    const title = `${this.anchor.monthName()} ${this.anchor.year}`;
    return html`
      <ha-card>
        ${this.config.show_header
          ? html`<div class="hdr">
              <button @click=${() => this._nav(-1)}>❮</button>
              <span>${title}</span>
              <button @click=${() => this._nav(1)}>❯</button>
            </div>`
          : ""}

        <table>
          ${this._weeks().map(week => html`<tr>
            ${week.map(d => d
              ? html`<td>
                  <div class="num">${d.hd.split(" ")[0]}</div>
                  ${d.holiday ? html`<div class="holiday">${d.holiday}</div>` : ""}
                  ${d.parasha ? html`<div class="parasha">${d.parasha}</div>` : ""}
                  ${d.candle ? html`<div class="candle">🕯 ${d.candle}</div>` : ""}
                  ${d.havdalah ? html`<div class="hav">⭐ ${d.havdalah}</div>` : ""}
                </td>`
              : html`<td class="empty"></td>`)}
          </tr>`)}
        </table>
      </ha-card>`;
  }

  static get styles() {
    return css`
      :host { display:block; direction: rtl; }
      ha-card { padding:0; }
      .hdr { display:flex; justify-content:center; align-items:center; gap:1rem; font-weight:600; padding:0.5rem 0; }
      .hdr button { background:none; border:none; font-size:1.2rem; cursor:pointer; }

      table { width:100%; border-collapse:collapse; }
      td { width:14.28%; min-height:4rem; border:1px solid var(--divider-color, #e0e0e0); vertical-align:top; }
      .num { font-size:0.8rem; padding:0.25rem; }
      .holiday { color:var(--error-color, red); font-size:0.7rem; padding:0 0.2rem; }
      .parasha { color:var(--secondary-text-color, #555); font-size:0.7rem; padding:0 0.2rem; }
      .candle, .hav { color:var(--primary-color); font-size:0.65rem; padding:0 0.2rem; }
      .empty { background:var(--secondary-background-color,#fafafa); opacity:0.4; }
      .loading { padding:1rem; }
    `;
  }
}

customElements.define("hebrew-jewish-calendar-card", HebrewJewishCalendarCard);
