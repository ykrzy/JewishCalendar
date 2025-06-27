import { LitElement, html, css } from "https://unpkg.com/lit-element@3.0.2/lit-element.js?module";

class HebrewMonthView extends LitElement {
  static get properties() {
    return {
      hass: {},           // HA object (injected)
      config: {},
      month: { type: Object },
      rosh:   { type: String },   // ISO of current Rosh Chodesh
    };
  }

  setConfig(cfg) {
    if (!cfg.entity) throw new Error("'entity' is required");
    this.config = { show_header: true, ...cfg };
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.config) return;

    const stateObj = hass.states[this.config.entity];
    if (!stateObj) return;

    // Current month payload from sensor attribute
    const month = stateObj.attributes.month;
    if (month) {
      this.month = month;
      this.rosh = stateObj.state;   // ISO string
    }
  }

  /* ─────────── helpers ─────────── */
  _navigate(dir) {
    // dir = +1 (next) or -1 (prev)
    const refISO = dir > 0 ? this.month.days[this.month.days.length - 1].greg
                           : this.month.days[0].greg;
    const ref = new Date(refISO);
    ref.setDate(ref.getDate() + dir);     // move one day fwd/back
    const target = ref.toISOString().split("T")[0];

    this._hass.callService("jewish_calendar_plus", "navigate", {
      rosh_chodesh: target,
    });
  }

  _weeks() {
    if (!this.month) return [];
    const rows = [];
    let row = [];
    const firstWeekday = new Date(this.month.days[0].greg).getDay(); // 0=Sun

    // pad front
    for (let i = 0; i < firstWeekday; i++) row.push(null);

    this.month.days.forEach((d) => {
      row.push(d);
      if (row.length === 7) {
        rows.push(row);
        row = [];
      }
    });
    while (row.length && row.length < 7) row.push(null);
    if (row.length) rows.push(row);
    return rows;
  }

  render() {
    if (!this.month) return html`<ha-card><div class="loading">Loading…</div></ha-card>`;

    return html`
      <ha-card>
        ${this.config.show_header
          ? html`<div class="hdr">
              <button @click=${() => this._navigate(-1)} title="חודש קודם">❮</button>
              <span>${this.month.title}</span>
              <button @click=${() => this._navigate(1)} title="חודש הבא">❯</button>
            </div>`
          : ""}

        <table>
          ${this._weeks().map(
            (w) => html`<tr>
              ${w.map((d) =>
                d
                  ? html`<td>
                      <div class="num">${d.hd.split(" ")[0]}</div>
                      ${d.holiday ? html`<div class="holiday">${d.holiday}</div>` : ""}
                      ${d.parasha ? html`<div class="parasha">${d.parasha}</div>` : ""}
                    </td>`
                  : html`<td class="empty"></td>`
              )}
            </tr>`
          )}
        </table>
      </ha-card>`;
  }

  static get styles() {
    return css`
      :host { direction: rtl; display:block; }
      ha-card { padding:0; }
      .hdr { display:flex; align-items:center; justify-content:center; gap:1rem; font-weight:600; padding:0.5rem 0; }
      .hdr button { background:none; border:none; font-size:1.2rem; cursor:pointer; }
      table { width:100%; border-collapse: collapse; }
      td { width:14.28%; border:1px solid var(--divider-color, #e0e0e0); min-height:4rem; vertical-align:top; position:relative; }
      .num { font-size:0.85rem; padding:0.25rem; }
      .holiday { color:var(--error-color, red); font-size:0.7rem; padding:0 0.2rem; }
      .parasha { color:var(--secondary-text-color, #555); font-size:0.7rem; padding:0 0.2rem; }
      .empty { background:var(--secondary-background-color, #fafafa); opacity:0.4; }
      .loading { padding:1rem; }
    `;
  }
}

customElements.define("hebrew-month-view", HebrewMonthView);
