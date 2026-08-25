/**
 * CadenceGuard · Pump Health Monitor — Customer Dashboard Controller
 * Plain-English, actionable information for pump maintenance teams.
 */

(function () {
  'use strict';

  /* ─── Config ──────────────────────────────────────────────────────────── */
  const ALERT_LEVELS = {
    Normal:   { cls: 'normal',   dotCls: 'dot-normal',   chipCls: 'chip-normal',   label: 'Healthy',         labelCls: 'label-normal',   headline: 'HEALTHY',    sublabel: 'Operating within normal parameters' },
    Watch:    { cls: 'watch',    dotCls: 'dot-watch',    chipCls: 'chip-watch',    label: 'Monitor Closely', labelCls: 'label-watch',    headline: 'WATCH',      sublabel: 'Elevated low-band stress detected' },
    Warning:  { cls: 'warning',  dotCls: 'dot-warning',  chipCls: 'chip-warning',  label: 'Action Advised',  labelCls: 'label-warning',  headline: 'WARNING',    sublabel: 'Maintenance should be scheduled soon' },
    Critical: { cls: 'critical', dotCls: 'dot-critical', chipCls: 'chip-critical', label: 'Urgent Action',   labelCls: 'label-critical', headline: 'CRITICAL',   sublabel: 'Immediate maintenance required' }
  };

  const FAILURE_TYPES = {
    Normal: {
      icon:    '✅', iconCls: 'icon-normal',
      label:   'No Issue Detected',
      desc:    'The pump is operating within normal parameters. Continue your routine inspection schedule.',
      checks:  ['Confirm lubrication levels are adequate', 'Check seals and gaskets for visible wear', 'Log this status in the maintenance record']
    },
    Mechanical: {
      icon:    '⚙️', iconCls: 'icon-mech',
      label:   'Mechanical Wear Detected',
      desc:    'Signs of mechanical degradation detected — likely bearing wear, vibration, or misalignment.',
      checks:  [
        'Inspect bearings for wear, noise, or overheating',
        'Check shaft alignment and coupling condition',
        'Verify impeller for erosion or imbalance',
        'Measure vibration levels against baseline',
        'Inspect motor mounting bolts for loosening'
      ]
    },
    Chemical: {
      icon:    '🧪', iconCls: 'icon-chem',
      label:   'Chemical Corrosion Detected',
      desc:    'Elevated water aggression indicators. Chemical degradation (corrosion or scaling) may be affecting pump internals.',
      checks:  [
        'Test water pH, conductivity, and turbidity',
        'Inspect casing and impeller for corrosion or pitting',
        'Check for mineral scale on impeller vanes',
        'Review chemical dosing system and treatment records',
        'Inspect seals and O-rings for chemical degradation'
      ]
    }
  };

  const ACTIONS = {
    Normal: [
      { priority: 'low',    icon: '📋', title: 'Continue routine inspection',  detail: 'No immediate action required. Maintain your scheduled maintenance programme.' },
      { priority: 'low',    icon: '📊', title: 'Log current status',            detail: 'Record this healthy reading in the maintenance log for trend tracking.' }
    ],
    Watch: [
      { priority: 'medium', icon: '🔍', title: 'Increase monitoring frequency', detail: 'Revisit pump status within 48 hours. Watch for changes in noise or vibration.' },
      { priority: 'medium', icon: '📋', title: 'Review maintenance history',     detail: 'Check when the last inspection was carried out and plan the next one accordingly.' },
      { priority: 'low',    icon: '💧', title: 'Check water quality readings',   detail: 'Verify pH, turbidity, and conductivity are within acceptable ranges.' }
    ],
    Warning: [
      { priority: 'high',   icon: '🔧', title: 'Schedule maintenance within 7 days', detail: 'Pump is showing signs of deterioration. Book a maintenance visit promptly.' },
      { priority: 'high',   icon: '📞', title: 'Notify maintenance supervisor',       detail: 'Escalate to a senior engineer to review the pump condition.' },
      { priority: 'medium', icon: '🔍', title: 'Conduct visual inspection now',       detail: 'Perform an immediate walkdown inspection for leaks, noise, or vibration.' },
      { priority: 'medium', icon: '📝', title: 'Prepare maintenance work order',      detail: 'Raise a work order so parts and personnel can be organised in advance.' }
    ],
    Critical: [
      { priority: 'high',   icon: '🚨', title: 'Immediate maintenance required',      detail: 'Stop non-essential operation and arrange urgent inspection and repair.' },
      { priority: 'high',   icon: '📞', title: 'Alert maintenance team immediately',  detail: 'Contact the on-call engineer now. Do not delay — failure risk is elevated.' },
      { priority: 'high',   icon: '⛔', title: 'Consider isolating this pump',        detail: 'Evaluate whether a backup pump should take over while this unit is inspected.' },
      { priority: 'medium', icon: '🔧', title: 'Prepare spare parts on site',         detail: 'Ensure bearings, seals, and gaskets are available before the engineer arrives.' }
    ]
  };

  const URGENCY_LABELS = { Normal: 'Routine', Watch: 'Monitor', Warning: 'Soon', Critical: 'Urgent' };
  const RING_COLOURS    = { Normal: '#16a34a', Watch: '#d97706', Warning: '#ea580c', Critical: '#dc2626' };

  /* ─── State ───────────────────────────────────────────────────────────── */
  let appData = null;
  let selectedPumpId = null;
  let healthChartInst = null;

  /* ─── Boot ────────────────────────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', boot);

  function boot() {
    setTime();
    loadData(function (data) {
      appData = data;
      renderFleetGrid();
      updateFleetBadges();
      const pumps = Object.keys(appData.pumps);
      const urgentPump = pumps.find(id => {
        const lvl = appData.pumps[id].latest.alert_level;
        return lvl === 'Critical' || lvl === 'Warning';
      }) || pumps[0];
      if (urgentPump) selectPump(urgentPump);
    });
  }

  function setTime() {
    const el = document.getElementById('last-updated-time');
    if (el) el.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  /* ─── Data ────────────────────────────────────────────────────────────── */
  function loadData(cb) {
    if (window.AQUAGUARD_DATA) { cb(window.AQUAGUARD_DATA); return; }
    fetch('data/app_data.json')
      .then(r => r.json()).then(d => cb(d))
      .catch(() => fetch('/data/app_data.json').then(r => r.json()).then(d => cb(d)));
  }

  /* ─── Fleet Grid ──────────────────────────────────────────────────────── */
  function renderFleetGrid() {
    const grid = document.getElementById('fleet-grid');
    grid.innerHTML = '';
    Object.keys(appData.pumps).forEach(pid => {
      const pump  = appData.pumps[pid];
      const lvl   = pump.latest.alert_level || 'Normal';
      const cfg   = ALERT_LEVELS[lvl] || ALERT_LEVELS.Normal;
      const rul   = typeof pump.latest.rul_predicted === 'number' ? Math.round(pump.latest.rul_predicted) : '—';

      const card = document.createElement('div');
      card.className = `fleet-card status-${cfg.cls}`;
      card.setAttribute('role', 'listitem');
      card.setAttribute('aria-label', `${pid}, ${cfg.label}, ${rul} days remaining`);
      card.dataset.pumpId = pid;
      card.innerHTML = `
        <div class="fleet-card-header">
          <span class="fleet-pump-id">${pid.replace('_', ' ')}</span>
          <span class="status-dot ${cfg.dotCls}"></span>
        </div>
        <div>
          <div class="fleet-rul">${rul}</div>
          <div class="fleet-rul-unit">days remaining</div>
        </div>
        <span class="fleet-status-label ${cfg.labelCls}">${cfg.label}</span>
      `;
      card.addEventListener('click', () => selectPump(pid));
      grid.appendChild(card);
    });
  }

  function updateFleetBadges() {
    let crit = 0, warn = 0, ok = 0;
    Object.values(appData.pumps).forEach(p => {
      const lvl = p.latest.alert_level;
      if (lvl === 'Critical') crit++;
      else if (lvl === 'Warning' || lvl === 'Watch') warn++;
      else ok++;
    });
    setEl('badge-critical', `${crit} Critical`);
    setEl('badge-warning',  `${warn} Alerts`);
    setEl('badge-ok',       `${ok} Healthy`);
  }

  /* ─── Pump Selection ──────────────────────────────────────────────────── */
  function selectPump(pumpId) {
    selectedPumpId = pumpId;
    document.querySelectorAll('.fleet-card').forEach(c => {
      c.classList.toggle('selected', c.dataset.pumpId === pumpId);
    });

    const pump   = appData.pumps[pumpId];
    const latest = pump.latest;
    const lvl    = latest.alert_level || 'Normal';
    const mode   = latest.failure_mode_predicted || 'Normal';
    const cfg    = ALERT_LEVELS[lvl] || ALERT_LEVELS.Normal;
    const rul    = typeof latest.rul_predicted === 'number' ? Math.round(latest.rul_predicted) : null;

    // Section header
    setEl('detail-heading', pumpId.replace('_', ' '));
    setEl('detail-pump-location', `Station: ${pumpId} · Last reading: ${latest.timestamp || '—'}`);

    // Alert chip
    const chip = document.getElementById('detail-alert-chip');
    if (chip) { chip.className = `alert-chip ${cfg.chipCls}`; chip.textContent = cfg.label; }

    // Headline status label (big WATCH / CRITICAL text matching screenshot)
    const hl = document.getElementById('rul-headline-label');
    if (hl) {
      hl.className = `rul-headline-label status-${cfg.cls}`;
      hl.textContent = cfg.headline;
    }
    setEl('rul-headline-sublabel', cfg.sublabel);

    // Ring
    updateRulRing(rul, lvl);

    // Failure type
    updateFailureType(mode);

    // Actions
    updateActions(lvl, mode);

    // Status table rows
    setEl('stat-alert',        cfg.label);
    setEl('stat-issue',        FAILURE_TYPES[mode] ? FAILURE_TYPES[mode].label : '—');
    setEl('stat-days',         rul !== null ? `${rul} days` : '—');
    setEl('stat-last-checked', latest.timestamp || '—');

    // Chart desc
    const descs = {
      Normal:   'Pump stress readings are stable. No concerning trends detected.',
      Watch:    'A gradual upward trend detected. Continue close monitoring.',
      Warning:  'Readings are elevated and trending upward. Plan maintenance soon.',
      Critical: 'Stress readings significantly elevated. Immediate action required.'
    };
    setEl('health-chart-desc', descs[lvl] || '');

    const badge = document.getElementById('trend-badge');
    if (badge) badge.textContent = cfg.label;

    renderHealthChart(pump, lvl);

    if (window.innerWidth < 800) {
      document.getElementById('detail-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  /* ─── RUL Ring ────────────────────────────────────────────────────────── */
  function updateRulRing(rul, lvl) {
    setEl('rul-days', rul !== null ? rul : '—');
    const circle = document.getElementById('ring-fill-circle');
    if (circle) {
      const frac = rul !== null ? Math.min(1, Math.max(0, rul / 120)) : 0;
      circle.style.strokeDashoffset = 314 * (1 - frac);
      circle.style.stroke = RING_COLOURS[lvl] || '#16a34a';
    }
    setEl('rul-urgency', URGENCY_LABELS[lvl] || '—');
    const schedEl = document.getElementById('rul-schedule-by');
    if (schedEl) {
      if (rul !== null) {
        const d = new Date(); d.setDate(d.getDate() + rul);
        schedEl.textContent = d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
      } else { schedEl.textContent = '—'; }
    }
  }

  /* ─── Failure Type ────────────────────────────────────────────────────── */
  function updateFailureType(mode) {
    const ft = FAILURE_TYPES[mode] || FAILURE_TYPES.Normal;
    const iconWrap = document.getElementById('failure-icon-wrap');
    if (iconWrap) { iconWrap.className = `failure-icon-wrap ${ft.iconCls}`; iconWrap.textContent = ft.icon; }
    setEl('failure-label', ft.label);
    setEl('failure-desc',  ft.desc);
    const checksSection = document.getElementById('failure-what-to-check');
    const checkList     = document.getElementById('check-list');
    if (checksSection && checkList) {
      checksSection.style.display = 'block';
      checkList.innerHTML = ft.checks.map(c => `<li>${c}</li>`).join('');
    }
  }

  /* ─── Actions ─────────────────────────────────────────────────────────── */
  function updateActions(lvl, mode) {
    const list = document.getElementById('action-list');
    if (!list) return;
    const actions = [...(ACTIONS[lvl] || ACTIONS.Normal)];
    if (mode === 'Mechanical' && lvl !== 'Normal') {
      actions.unshift({ priority: 'high', icon: '⚙️', title: 'Inspect mechanical components', detail: 'Focus on bearings, shaft alignment, coupling, and impeller wear.' });
    } else if (mode === 'Chemical' && lvl !== 'Normal') {
      actions.unshift({ priority: 'high', icon: '🧪', title: 'Test water quality immediately', detail: 'Sample water for pH, conductivity, and turbidity. Compare against acceptable limits.' });
    }
    list.innerHTML = actions.map(a => `
      <li class="action-item priority-${a.priority}" role="listitem">
        <span class="action-icon">${a.icon}</span>
        <span class="action-text">
          <span class="action-title">${a.title}</span>
          <span class="action-detail">${a.detail}</span>
        </span>
      </li>`).join('');
  }

  /* ─── Health Chart ────────────────────────────────────────────────────── */
  function renderHealthChart(pump, lvl) {
    const ctx = document.getElementById('healthChart');
    if (!ctx) return;

    const timeline = pump.timeline || [];
    const step = Math.max(1, Math.floor(timeline.length / 120));
    const sub  = timeline.filter((_, i) => i % step === 0);
    const labels = sub.map(r => r.t ? r.t.slice(5, 16) : '');
    const data   = sub.map(r => r.h);
    const ptColours = sub.map(r => {
      const l = r.al || 'Normal';
      return l === 'Critical' ? '#dc2626' : l === 'Warning' ? '#ea580c' : l === 'Watch' ? '#d97706' : '#16a34a';
    });

    if (healthChartInst) healthChartInst.destroy();

    const borderCol = RING_COLOURS[lvl] || '#16a34a';
    const fillCol = hexToRgba(borderCol, 0.06);

    healthChartInst = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Pump Stress Index',
          data,
          borderColor: borderCol,
          borderWidth: 1.8,
          pointRadius: data.length > 60 ? 0 : 3,
          pointBackgroundColor: ptColours,
          pointBorderWidth: 0,
          fill: true,
          backgroundColor: fillCol,
          tension: 0.35
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        scales: {
          x: {
            grid: { color: 'rgba(0,0,0,0.04)', drawBorder: false },
            ticks: { color: '#9ca3af', maxTicksLimit: 8, font: { size: 11, family: 'Inter' } }
          },
          y: {
            grid: { color: 'rgba(0,0,0,0.04)' },
            ticks: { color: '#9ca3af', font: { size: 11, family: 'Inter' } },
            title: { display: true, text: 'Stress Index', color: '#9ca3af', font: { size: 11 } }
          }
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#111827',
            titleColor: '#f9fafb',
            bodyColor: '#9ca3af',
            borderColor: '#374151',
            borderWidth: 1,
            padding: 10,
            callbacks: { label: ctx => ` ${ctx.parsed.y.toFixed(3)}` }
          }
        }
      }
    });
  }

  /* ─── Utils ───────────────────────────────────────────────────────────── */
  function setEl(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1,3), 16);
    const g = parseInt(hex.slice(3,5), 16);
    const b = parseInt(hex.slice(5,7), 16);
    return `rgba(${r},${g},${b},${alpha})`;
  }

})();
