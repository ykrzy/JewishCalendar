import { LitElement, html, css } from "https://unpkg.com/lit-element@3.0.2/lit-element.js?module";
import { HDate, HebrewCalendar, Location } from "https://cdn.skypack.dev/@hebcal/core";

class HebrewJewishCalendarCard extends LitElement {
  static get properties() {
    return {
      hass: {},
      config: {},
      currentView: { type: String },  // 'month', 'week', 'day'
      anchor: { type: Object },       // HDate reference point for current view
      days: { type: Array },          // Calendar data for current period
    };
  }

  setConfig(cfg) {
    this.config = { 
      show_header: true, 
      default_view: 'month',
      ...cfg 
    };
    this.currentView = this.config.default_view;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.anchor) {
      // First render → set anchor to today
      const today = new Date();
      const hToday = new HDate(today);
      this.anchor = hToday;
      this._buildCurrentView();
    }
  }

  /* ───────── Navigation Helpers ───────── */
  _getAnchorForView(hdate, view) {
    const d = hdate.clone();
    switch (view) {
      case 'month':
        // Anchor to Rosh Chodesh (1st of Hebrew month)
        while (d.day > 1) d.setDate(d.day - 1);
        return d;
      case 'week':
        // Anchor to Sunday of current week
        const greg = d.greg();
        const sunday = new Date(greg);
        sunday.setDate(greg.getDate() - greg.getDay());
        return new HDate(sunday);
      case 'day':
        // Anchor is the day itself
        return d;
      default:
        return d;
    }
  }

  _navigate(direction) {
    const temp = this.anchor.clone();
    switch (this.currentView) {
      case 'month':
        temp.setMonth(temp.month + direction);
        this.anchor = this._getAnchorForView(temp, 'month');
        break;
      case 'week':
        const greg = temp.greg();
        greg.setDate(greg.getDate() + (direction * 7));
        this.anchor = this._getAnchorForView(new HDate(greg), 'week');
        break;
      case 'day':
        const dayGreg = temp.greg();
        dayGreg.setDate(dayGreg.getDate() + direction);
        this.anchor = new HDate(dayGreg);
        break;
    }
    this._buildCurrentView();
  }

  _switchView(newView) {
    this.currentView = newView;
    this.anchor = this._getAnchorForView(this.anchor, newView);
    this._buildCurrentView();
  }

  _buildCurrentView() {
    switch (this.currentView) {
      case 'month':
        this._buildMonth();
        break;
      case 'week':
        this._buildWeek();
        break;
      case 'day':
        this._buildDay();
        break;
    }
  }

  /* ───────── Data Building Methods ───────── */
  _buildMonth() {
    const days = [];
    let hd = this.anchor.clone();
    const month = hd.month;
    
    while (hd.month === month) {
      days.push(this._buildDayData(hd));
      hd = hd.next();
    }
    this.days = days;
  }

  _buildWeek() {
    const days = [];
    let current = this.anchor.clone();
    
    // Build 7 days starting from anchor (Sunday)
    for (let i = 0; i < 7; i++) {
      days.push(this._buildDayData(current));
      current = current.next();
    }
    this.days = days;
  }

  _buildDay() {
    this.days = [this._buildDayData(this.anchor)];
  }

  _buildDayData(hdate) {
    const loc = new Location(
      this._hass.config.location_name || "HA",
      this._hass.config.latitude,
      this._hass.config.longitude,
      this._hass.config.time_zone,
      0
    );

    const greg = hdate.greg();
    const cal = new HebrewCalendar(hdate);
    const holidays = cal.holidays().map(h => h.render("he"));
    const parasha = cal.getLeyning({ israel: true })?.parsha || "";
    const z = HebrewCalendar.getZmanim({ date: greg, location: loc });
    
    return {
      hd: hdate.renderGematriya(),
      hdate: hdate,
      greg: greg,
      gregDay: greg.getDate(),
      gregMonth: greg.toLocaleDateString('he-IL', { month: 'long' }),
      gregYear: greg.getFullYear(),
      weekday: greg.toLocaleDateString('he-IL', { weekday: 'long' }),
      parasha,
      holidays,
      candle: z?.candle_lighting ? z.candle_lighting.toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"}) : "",
      havdalah: z?.havdalah ? z.havdalah.toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"}) : "",
    };
  }

  /* ───────── Rendering Helpers ───────── */
  _getTitle() {
    switch (this.currentView) {
      case 'month':
        return `${this.anchor.monthName()} ${this.anchor.year}`;
      case 'week':
        const weekEnd = this.anchor.clone();
        weekEnd.greg().setDate(weekEnd.greg().getDate() + 6);
        return `${this.anchor.renderGematriya()} - ${weekEnd.renderGematriya()}`;
      case 'day':
        return `${this.anchor.renderGematriya()} • ${this.days[0]?.weekday}`;
      default:
        return '';
    }
  }

  _renderMonthView() {
    const weeks = this._getWeeksForMonth();
    return html`
      <table class="month-table">
        <thead>
          <tr>
            ${['א', 'ב', 'ג', 'ד', 'ה', 'ו', 'ש'].map(day => 
              html`<th>${day}</th>`
            )}
          </tr>
        </thead>
        <tbody>
          ${weeks.map(week => html`
            <tr>
              ${week.map(day => day 
                ? html`<td class="day-cell" @click=${() => this._goToDay(day.hdate)}>
                    <div class="day-number">${day.hd.split(" ")[0]}</div>
                    <div class="greg-number">${day.gregDay}</div>
                    ${day.holidays.map(h => html`<div class="holiday">${h}</div>`)}
                    ${day.parasha ? html`<div class="parasha">${day.parasha}</div>` : ''}
                    ${day.candle ? html`<div class="time candle">🕯 ${day.candle}</div>` : ''}
                    ${day.havdalah ? html`<div class="time havdalah">⭐ ${day.havdalah}</div>` : ''}
                  </td>`
                : html`<td class="empty-cell"></td>`
              )}
            </tr>
          `)}
        </tbody>
      </table>
    `;
  }

  _renderWeekView() {
    return html`
      <div class="week-view">
        ${this.days.map(day => html`
          <div class="week-day" @click=${() => this._goToDay(day.hdate)}>
            <div class="week-day-header">
              <div class="weekday">${day.weekday}</div>
              <div class="dates">
                <span class="hebrew-date">${day.hd}</span>
                <span class="greg-date">${day.gregDay}/${day.greg.getMonth() + 1}</span>
              </div>
            </div>
            <div class="week-day-content">
              ${day.holidays.map(h => html`<div class="holiday">${h}</div>`)}
              ${day.parasha ? html`<div class="parasha">${day.parasha}</div>` : ''}
              ${day.candle ? html`<div class="time candle">🕯 ${day.candle}</div>` : ''}
              ${day.havdalah ? html`<div class="time havdalah">⭐ ${day.havdalah}</div>` : ''}
            </div>
          </div>
        `)}
      </div>
    `;
  }

  _renderDayView() {
    const day = this.days[0];
    if (!day) return html`<div>No data</div>`;
    
    return html`
      <div class="day-view">
        <div class="day-header">
          <h2>${day.weekday}</h2>
          <div class="dates">
            <div class="hebrew-date">${day.hd}</div>
            <div class="greg-date">${day.gregDay} ${day.gregMonth} ${day.gregYear}</div>
          </div>
        </div>
        
        <div class="day-content">
          ${day.holidays.length > 0 ? html`
            <div class="section">
              <h3>חגים ומועדים</h3>
              ${day.holidays.map(h => html`<div class="holiday large">${h}</div>`)}
            </div>
          ` : ''}
          
          ${day.parasha ? html`
            <div class="section">
              <h3>פרשת השבוע</h3>
              <div class="parasha large">${day.parasha}</div>
            </div>
          ` : ''}
          
          ${day.candle || day.havdalah ? html`
            <div class="section">
              <h3>זמנים</h3>
              ${day.candle ? html`<div class="time large candle">🕯 הדלקת נרות: ${day.candle}</div>` : ''}
              ${day.havdalah ? html`<div class="time large havdalah">⭐ הבדלה: ${day.havdalah}</div>` : ''}
            </div>
          ` : ''}
        </div>
      </div>
    `;
  }

  _getWeeksForMonth() {
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

  _goToDay(hdate) {
    this.anchor = hdate;
    this.currentView = 'day';
    this._buildCurrentView();
  }

  /* ───────── Main Render ───────── */
  render() {
    if (!this.days) return html`<ha-card><div class="loading">Loading…</div></ha-card>`;

    return html`
      <ha-card>
        ${this.config.show_header ? html`
          <div class="header">
            <div class="nav-section">
              <button class="nav-btn" @click=${() => this._navigate(-1)}>❮</button>
              <span class="title">${this._getTitle()}</span>
              <button class="nav-btn" @click=${() => this._navigate(1)}>❯</button>
            </div>
            
            <div class="view-switcher">
              <button class="view-btn ${this.currentView === 'day' ? 'active' : ''}" 
                      @click=${() => this._switchView('day')}>יום</button>
              <button class="view-btn ${this.currentView === 'week' ? 'active' : ''}" 
                      @click=${() => this._switchView('week')}>שבוע</button>
              <button class="view-btn ${this.currentView === 'month' ? 'active' : ''}" 
                      @click=${() => this._switchView('month')}>חודש</button>
            </div>
          </div>
        ` : ''}

        <div class="content">
          ${this.currentView === 'month' ? this._renderMonthView() : ''}
          ${this.currentView === 'week' ? this._renderWeekView() : ''}
          ${this.currentView === 'day' ? this._renderDayView() : ''}
        </div>
      </ha-card>
    `;
  }

  static get styles() {
    return css`
      :host { 
        display: block; 
        direction: rtl; 
        font-family: 'Arial', sans-serif;
      }
      
      ha-card { 
        padding: 0; 
        overflow: hidden;
      }
      
      .loading { 
        padding: 1rem; 
        text-align: center;
      }

      /* Header Styles */
      .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem;
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
        background: var(--primary-background-color);
      }

      .nav-section {
        display: flex;
        align-items: center;
        gap: 1rem;
      }

      .nav-btn {
        background: none;
        border: none;
        font-size: 1.2rem;
        cursor: pointer;
        padding: 0.5rem;
        border-radius: 50%;
        transition: background-color 0.2s;
      }

      .nav-btn:hover {
        background: var(--secondary-background-color, #f5f5f5);
      }

      .title {
        font-weight: 600;
        font-size: 1.1rem;
        min-width: 200px;
        text-align: center;
      }

      .view-switcher {
        display: flex;
        gap: 0.5rem;
      }

      .view-btn {
        padding: 0.5rem 1rem;
        border: 1px solid var(--divider-color, #e0e0e0);
        background: var(--card-background-color);
        cursor: pointer;
        border-radius: 4px;
        font-size: 0.9rem;
        transition: all 0.2s;
      }

      .view-btn:hover {
        background: var(--secondary-background-color, #f5f5f5);
      }

      .view-btn.active {
        background: var(--primary-color);
        color: var(--text-primary-color);
        border-color: var(--primary-color);
      }

      .content {
        padding: 1rem;
      }

      /* Month View Styles */
      .month-table {
        width: 100%;
        border-collapse: collapse;
      }

      .month-table th {
        padding: 0.5rem;
        background: var(--secondary-background-color, #f5f5f5);
        font-weight: 600;
        border: 1px solid var(--divider-color, #e0e0e0);
      }

      .day-cell {
        width: 14.28%;
        min-height: 5rem;
        border: 1px solid var(--divider-color, #e0e0e0);
        vertical-align: top;
        padding: 0.25rem;
        cursor: pointer;
        transition: background-color 0.2s;
      }

      .day-cell:hover {
        background: var(--secondary-background-color, #f5f5f5);
      }

      .empty-cell {
        background: var(--secondary-background-color, #fafafa);
        opacity: 0.4;
        width: 14.28%;
        min-height: 5rem;
        border: 1px solid var(--divider-color, #e0e0e0);
      }

      .day-number {
        font-weight: 600;
        font-size: 0.9rem;
        color: var(--primary-text-color);
      }

      .greg-number {
        font-size: 0.7rem;
        color: var(--secondary-text-color);
        margin-bottom: 0.25rem;
      }

      /* Week View Styles */
      .week-view {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 1rem;
      }

      .week-day {
        border: 1px solid var(--divider-color, #e0e0e0);
        border-radius: 8px;
        padding: 1rem;
        cursor: pointer;
        transition: all 0.2s;
        min-height: 8rem;
      }

      .week-day:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
      }

      .week-day-header {
        margin-bottom: 0.5rem;
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
        padding-bottom: 0.5rem;
      }

      .weekday {
        font-weight: 600;
        color: var(--primary-color);
      }

      .dates {
        display: flex;
        justify-content: space-between;
        font-size: 0.8rem;
        margin-top: 0.25rem;
      }

      /* Day View Styles */
      .day-view {
        max-width: 600px;
        margin: 0 auto;
      }

      .day-header {
        text-align: center;
        margin-bottom: 2rem;
        padding: 1rem;
        background: var(--secondary-background-color, #f5f5f5);
        border-radius: 8px;
      }

      .day-header h2 {
        margin: 0 0 1rem 0;
        color: var(--primary-color);
      }

      .day-header .dates {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
      }

      .hebrew-date {
        font-size: 1.2rem;
        font-weight: 600;
      }

      .greg-date {
        color: var(--secondary-text-color);
      }

      .section {
        margin-bottom: 1.5rem;
        padding: 1rem;
        border: 1px solid var(--divider-color, #e0e0e0);
        border-radius: 8px;
      }

      .section h3 {
        margin: 0 0 1rem 0;
        color: var(--primary-color);
        font-size: 1.1rem;
      }

      /* Content Styles */
      .holiday {
        color: var(--error-color, red);
        font-size: 0.7rem;
        padding: 0.1rem 0;
        font-weight: 500;
      }

      .holiday.large {
        font-size: 1rem;
        padding: 0.5rem 0;
      }

      .parasha {
        color: var(--secondary-text-color, #555);
        font-size: 0.7rem;
        padding: 0.1rem 0;
        font-style: italic;
      }

      .parasha.large {
        font-size: 1rem;
        padding: 0.5rem 0;
      }

      .time {
        color: var(--primary-color);
        font-size: 0.65rem;
        padding: 0.1rem 0;
      }

      .time.large {
        font-size: 0.9rem;
        padding: 0.5rem 0;
      }

      .candle {
        background: linear-gradient(45deg, #ffd700, #ffec8b);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }

      .havdalah {
        background: linear-gradient(45deg, #4a90e2, #7bb3f0);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }

      /* Responsive Design */
      @media (max-width: 768px) {
        .header {
          flex-direction: column;
          gap: 1rem;
        }

        .week-view {
          grid-template-columns: 1fr;
        }

        .view-switcher {
          width: 100%;
          justify-content: center;
        }

        .nav-section {
          width: 100%;
          justify-content: center;
        }
      }
    `;
  }
}

customElements.define("hebrew-jewish-calendar-card", HebrewJewishCalendarCard);