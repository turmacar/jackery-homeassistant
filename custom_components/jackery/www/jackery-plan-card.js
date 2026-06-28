/**
 * Jackery Plan Card — Custom Lovelace card for managing
 * charge/discharge plans on the Jackery Smart Transfer Switch.
 *
 * Reads plan data from a sensor entity's attributes and provides
 * create, toggle, and delete via jackery.create_plan / update_plan / delete_plan services.
 */

const DAY_LABELS = ["M", "T", "W", "T", "F", "S", "S"];
const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

class JackeryPlanCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._showForm = false;
    this._formData = { type: 2, start_time: "14:00", end_time: "19:00", days: "1111111" };
  }

  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    const prev = this._hass;
    this._hass = hass;
    // Only re-render when our entity's state object actually changes.
    const entityId = this._resolveEntity();
    if (entityId && prev) {
      if (prev.states[entityId] === hass.states[entityId]) return;
    }
    this._render();
  }

  _resolveEntity() {
    if (this._config.entity) return this._config.entity;
    if (!this._hass) return null;
    const match = Object.keys(this._hass.states).find(
      k => k.includes("transfer_switch") && k.includes("scheduled_plans")
    );
    return match || null;
  }

  _getPlans() {
    if (!this._hass) return [];
    const entityId = this._resolveEntity();
    if (!entityId) return [];
    const state = this._hass.states[entityId];
    if (!state) return [];
    const attrs = state.attributes;
    const count = attrs.plan_count || 0;
    const plans = [];
    for (let i = 1; i <= count; i++) {
      plans.push({
        pid: attrs[`plan_${i}_pid`] || "",
        name: attrs[`plan_${i}_name`] || "",
        enabled: attrs[`plan_${i}_enabled`] || false,
        type: attrs[`plan_${i}_type`] || "Discharge",
        start: attrs[`plan_${i}_start`] || "",
        end: attrs[`plan_${i}_end`] || "",
        days: attrs[`plan_${i}_days`] || "",
      });
    }
    return plans;
  }

  _timeToPercent(timeStr) {
    const [h, m] = timeStr.split(":").map(Number);
    return ((h * 60 + m) / 1440) * 100;
  }

  _renderTimebar(plan) {
    const start = this._timeToPercent(plan.start);
    const end = this._timeToPercent(plan.end);
    const color = plan.type === "Charge" ? "#4CAF50" : "#FF9800";
    const width = end > start ? end - start : 100 - start + end;
    // For overnight spans we'd need two bars, but keep simple for now
    const barStyle = end > start
      ? `left:${start}%;width:${width}%`
      : `left:${start}%;width:${100 - start}%`;
    return `
      <div class="timebar">
        <div class="timebar-fill" style="${barStyle};background:${color}"></div>
        ${end <= start ? `<div class="timebar-fill" style="left:0%;width:${end}%;background:${color}"></div>` : ""}
      </div>
    `;
  }

  _renderDayChips(daysLabel) {
    // daysLabel is like "Mon, Tue, Wed" or "Daily" or "Weekdays"
    const activeDays = new Set();
    if (daysLabel === "Daily") {
      DAY_NAMES.forEach((_, i) => activeDays.add(i));
    } else if (daysLabel === "Weekdays") {
      [0, 1, 2, 3, 4].forEach(i => activeDays.add(i));
    } else if (daysLabel === "Weekends") {
      [5, 6].forEach(i => activeDays.add(i));
    } else {
      daysLabel.split(",").map(s => s.trim()).forEach(name => {
        const idx = DAY_NAMES.indexOf(name);
        if (idx >= 0) activeDays.add(idx);
      });
    }
    return DAY_LABELS.map((label, i) =>
      `<span class="day-chip ${activeDays.has(i) ? "active" : ""}">${label}</span>`
    ).join("");
  }

  async _togglePlan(pid, currentlyEnabled) {
    try {
      console.log("[jackery-plan-card] toggle", pid, !currentlyEnabled);
      await this._hass.callService("jackery", "update_plan", {
        plan_id: pid,
        enabled: !currentlyEnabled,
      });
      console.log("[jackery-plan-card] toggle success");
    } catch(e) { console.error("[jackery-plan-card] toggle error", e); }
  }

  async _deletePlan(pid) {
    try {
      console.log("[jackery-plan-card] delete", pid);
      await this._hass.callService("jackery", "delete_plan", {
        plan_id: pid,
      });
      console.log("[jackery-plan-card] delete success");
    } catch(e) { console.error("[jackery-plan-card] delete error", e); }
  }

  async _createPlan() {
    const f = this._formData;
    try {
      console.log("[jackery-plan-card] create", f);
      await this._hass.callService("jackery", "create_plan", {
        type: parseInt(f.type),
        start_time: f.start_time,
        end_time: f.end_time,
        days: f.days,
        enabled: true,
      });
      console.log("[jackery-plan-card] create success");
    } catch(e) { console.error("[jackery-plan-card] create error", e); }
    this._showForm = false;
    this._render();
  }

  _render() {
    if (!this.shadowRoot) return;
    const plans = this._getPlans();
    const title = this._config.title || "Charging Plans";

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          font-family: var(--primary-font-family, Roboto, sans-serif);
        }
        ha-card {
          padding: 16px;
        }
        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }
        .header h2 {
          margin: 0;
          font-size: 1.1em;
          font-weight: 500;
          color: var(--primary-text-color);
        }
        .add-btn {
          background: var(--primary-color);
          color: var(--text-primary-color, #fff);
          border: none;
          border-radius: 20px;
          padding: 6px 16px;
          cursor: pointer;
          font-size: 0.85em;
          font-weight: 500;
        }
        .add-btn:hover { opacity: 0.85; }
        .plan {
          background: var(--card-background-color, var(--secondary-background-color));
          border: 1px solid var(--divider-color, #e0e0e0);
          border-radius: 12px;
          padding: 12px;
          margin-bottom: 10px;
        }
        .plan-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .plan-info {
          flex: 1;
        }
        .plan-type {
          font-weight: 500;
          font-size: 0.95em;
          color: var(--primary-text-color);
        }
        .plan-type .icon { margin-right: 4px; }
        .plan-type.charge { color: #4CAF50; }
        .plan-type.discharge { color: #FF9800; }
        .plan-time {
          font-size: 0.85em;
          color: var(--secondary-text-color);
          margin-top: 2px;
        }
        .plan-actions {
          display: flex;
          align-items: center;
          gap: 4px;
        }
        .plan-actions button {
          background: none;
          border: none;
          cursor: pointer;
          padding: 4px;
          border-radius: 50%;
          color: var(--secondary-text-color);
          font-size: 1.1em;
          line-height: 1;
        }
        .plan-actions button:hover {
          background: var(--divider-color, #e0e0e0);
        }
        .toggle {
          width: 40px;
          height: 22px;
          border-radius: 11px;
          border: none;
          cursor: pointer;
          position: relative;
          transition: background 0.2s;
          padding: 0;
        }
        .toggle.on { background: var(--primary-color, #03a9f4); }
        .toggle.off { background: var(--disabled-text-color, #bdbdbd); }
        .toggle::after {
          content: "";
          position: absolute;
          top: 2px;
          width: 18px;
          height: 18px;
          border-radius: 50%;
          background: white;
          transition: left 0.2s;
        }
        .toggle.on::after { left: 20px; }
        .toggle.off::after { left: 2px; }
        .timebar {
          height: 6px;
          background: var(--divider-color, #e0e0e0);
          border-radius: 3px;
          margin: 8px 0 6px;
          position: relative;
          overflow: hidden;
        }
        .timebar-fill {
          position: absolute;
          top: 0;
          height: 100%;
          border-radius: 3px;
        }
        .day-chips {
          display: flex;
          gap: 3px;
        }
        .day-chip {
          width: 22px;
          height: 22px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.7em;
          font-weight: 600;
          background: var(--divider-color, #e0e0e0);
          color: var(--secondary-text-color);
        }
        .day-chip.active {
          background: var(--primary-color, #03a9f4);
          color: var(--text-primary-color, #fff);
        }
        .no-plans {
          text-align: center;
          color: var(--secondary-text-color);
          padding: 24px 0;
          font-size: 0.9em;
        }
        .delete-btn { color: var(--error-color, #db4437) !important; }
        /* Form */
        .form {
          border: 1px solid var(--divider-color, #e0e0e0);
          border-radius: 12px;
          padding: 16px;
          margin-top: 10px;
        }
        .form h3 {
          margin: 0 0 12px;
          font-size: 0.95em;
          font-weight: 500;
          color: var(--primary-text-color);
        }
        .form-row {
          display: flex;
          align-items: center;
          margin-bottom: 10px;
          gap: 10px;
        }
        .form-row label {
          min-width: 50px;
          font-size: 0.85em;
          color: var(--secondary-text-color);
        }
        .form-row select, .form-row input {
          flex: 1;
          padding: 6px 8px;
          border: 1px solid var(--divider-color, #e0e0e0);
          border-radius: 8px;
          background: var(--card-background-color, #fff);
          color: var(--primary-text-color);
          font-size: 0.9em;
        }
        .form-days {
          display: flex;
          gap: 4px;
          margin-bottom: 12px;
        }
        .form-day {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.8em;
          font-weight: 600;
          border: 2px solid var(--divider-color, #e0e0e0);
          background: none;
          color: var(--secondary-text-color);
          cursor: pointer;
        }
        .form-day.active {
          border-color: var(--primary-color, #03a9f4);
          background: var(--primary-color, #03a9f4);
          color: var(--text-primary-color, #fff);
        }
        .form-actions {
          display: flex;
          justify-content: flex-end;
          gap: 8px;
        }
        .form-actions button {
          padding: 8px 20px;
          border: none;
          border-radius: 8px;
          cursor: pointer;
          font-size: 0.85em;
          font-weight: 500;
        }
        .btn-cancel {
          background: var(--divider-color, #e0e0e0);
          color: var(--primary-text-color);
        }
        .btn-save {
          background: var(--primary-color, #03a9f4);
          color: var(--text-primary-color, #fff);
        }
      </style>
      <ha-card>
        <div class="header">
          <h2>${title}</h2>
          <button class="add-btn" id="add-btn">+ Add</button>
        </div>
        ${plans.length === 0 && !this._showForm
          ? '<div class="no-plans">No plans configured</div>'
          : plans.map((p, i) => `
            <div class="plan">
              <div class="plan-row">
                <div class="plan-info">
                  <div class="plan-type ${p.type.toLowerCase()}">
                    <span class="icon">${p.type === "Charge" ? "🔋" : "⚡"}</span>
                    ${p.type}
                  </div>
                  <div class="plan-time">${p.start} → ${p.end}</div>
                </div>
                <div class="plan-actions">
                  <button class="toggle ${p.enabled ? "on" : "off"}" data-toggle="${i}"></button>
                  <button class="delete-btn" data-delete="${i}" title="Delete">🗑️</button>
                </div>
              </div>
              ${this._renderTimebar(p)}
              <div class="day-chips">${this._renderDayChips(p.days)}</div>
            </div>
          `).join("")
        }
        ${this._showForm ? this._renderForm() : ""}
      </ha-card>
    `;

    // Bind events
    this.shadowRoot.getElementById("add-btn")?.addEventListener("click", () => {
      this._showForm = !this._showForm;
      this._formData = { type: 2, start_time: "14:00", end_time: "19:00", days: "1111111" };
      this._render();
    });

    this.shadowRoot.querySelectorAll("[data-toggle]").forEach(btn => {
      btn.addEventListener("click", () => {
        const idx = parseInt(btn.dataset.toggle);
        const plan = this._getPlans()[idx];
        if (plan) this._togglePlan(plan.pid, plan.enabled);
      });
    });

    this.shadowRoot.querySelectorAll("[data-delete]").forEach(btn => {
      btn.addEventListener("click", () => {
        const idx = parseInt(btn.dataset.delete);
        const plan = this._getPlans()[idx];
        if (plan && confirm(`Delete ${plan.name}?`)) this._deletePlan(plan.pid);
      });
    });

    // Form events
    this.shadowRoot.getElementById("form-type")?.addEventListener("change", e => {
      this._formData.type = e.target.value;
    });
    this.shadowRoot.getElementById("form-start")?.addEventListener("change", e => {
      this._formData.start_time = e.target.value;
    });
    this.shadowRoot.getElementById("form-end")?.addEventListener("change", e => {
      this._formData.end_time = e.target.value;
    });
    this.shadowRoot.querySelectorAll("[data-day]").forEach(btn => {
      btn.addEventListener("click", () => {
        const idx = parseInt(btn.dataset.day);
        const days = this._formData.days.split("");
        days[idx] = days[idx] === "1" ? "0" : "1";
        this._formData.days = days.join("");
        this._render();
      });
    });
    this.shadowRoot.getElementById("form-cancel")?.addEventListener("click", () => {
      this._showForm = false;
      this._render();
    });
    this.shadowRoot.getElementById("form-save")?.addEventListener("click", () => {
      this._createPlan();
    });
  }

  _renderForm() {
    const f = this._formData;
    const dayBits = f.days.split("");
    return `
      <div class="form">
        <h3>New Plan</h3>
        <div class="form-row">
          <label>Type</label>
          <select id="form-type">
            <option value="1" ${f.type == 1 ? "selected" : ""}>Charge</option>
            <option value="2" ${f.type == 2 ? "selected" : ""}>Discharge</option>
          </select>
        </div>
        <div class="form-row">
          <label>Start</label>
          <input type="time" id="form-start" value="${f.start_time}">
        </div>
        <div class="form-row">
          <label>End</label>
          <input type="time" id="form-end" value="${f.end_time}">
        </div>
        <div class="form-days">
          ${DAY_LABELS.map((label, i) =>
            `<button class="form-day ${dayBits[i] === "1" ? "active" : ""}" data-day="${i}">${label}</button>`
          ).join("")}
        </div>
        <div class="form-actions">
          <button class="btn-cancel" id="form-cancel">Cancel</button>
          <button class="btn-save" id="form-save">Save</button>
        </div>
      </div>
    `;
  }

  getCardSize() {
    return 3;
  }

  static getStubConfig() {
    return {};
  }
}

customElements.define("jackery-plan-card", JackeryPlanCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "jackery-plan-card",
  name: "Jackery Plan Card",
  description: "Manage charge/discharge plans for the Jackery Smart Transfer Switch",
});
