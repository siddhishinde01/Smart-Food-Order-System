/* ─────────────────────────────────────────────────────────────────────────────
   FoodTech Command Center — Dashboard Logic
───────────────────────────────────────────────────────────────────────────── */

let allOrders = [];
let charts    = {};
let refreshInterval;
let countdownInterval;
let countdownVal = 30;

// ── Tab switching ──────────────────────────────────────────────────────────────
function switchTab(id, btn) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));

  const panel = document.getElementById('tab-' + id);
  if (panel) panel.classList.add('active');

  const targetBtn = btn || document.querySelector(`.tab-btn[onclick*="'${id}'"]`);
  if (targetBtn) targetBtn.classList.add('active');

  if (id === 'charts') renderCharts();
  if (id === 'delay')  loadDelayMonitor();
  if (id === 'ai')     loadRecommendations();
  if (id === 'partners') loadPartners();
}

function handleTabFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const tab = params.get('tab') || window.location.hash.replace('#', '');
  if (tab) {
    switchTab(tab);
  }
}

// ── Master load ───────────────────────────────────────────────────────────────
async function loadAll() {
  await Promise.all([
    loadSummary(),
    loadOrders(),
  ]);
  resetCountdown();
}

function resetCountdown() {
  countdownVal = 30;
  document.getElementById('countdown').textContent = 30;
}

// ── KPI Summary ───────────────────────────────────────────────────────────────
async function loadSummary() {
  const d = await fetch('/api/dashboard/summary').then(r => r.json()).catch(() => null);
  if (!d) return;
  animateNum('kpi-active',    d.active_orders);
  animateNum('kpi-risk',      d.at_risk_orders);
  animateNum('kpi-eta',       d.avg_eta_min);
  document.getElementById('kpi-partners').textContent = `${d.available_partners}/${d.total_partners}`;
  document.getElementById('kpi-load').textContent     = d.avg_restaurant_load + '%';
  animateNum('kpi-delivered', d.delivered_today);
}

function animateNum(id, target) {
  const el = document.getElementById(id);
  if (!el) return;
  const start   = parseInt(el.textContent) || 0;
  const dur     = 600;
  const startTs = performance.now();
  function step(now) {
    const t   = Math.min((now - startTs) / dur, 1);
    const val = Math.round(start + (target - start) * t);
    el.textContent = val;
    if (t < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// ── Order Table ───────────────────────────────────────────────────────────────
async function loadOrders() {
  const data = await fetch('/api/orders').then(r => r.json()).catch(() => []);
  allOrders = data;
  document.getElementById('order-count-badge').textContent = data.length + ' orders';
  renderOrderTable();
}

function renderOrderTable() {
  const statusFilter   = document.getElementById('status-filter')?.value   || '';
  const priorityFilter = document.getElementById('priority-filter')?.value || '';

  let rows = allOrders.filter(o => {
    if (statusFilter   && o.status          !== statusFilter)   return false;
    if (priorityFilter && o.priority_class  !== priorityFilter) return false;
    return true;
  });

  const tbody = document.getElementById('order-tbody');
  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="11"><div class="empty-state"><div class="empty-icon">📭</div><h3>No orders match filter</h3></div></td></tr>`;
    return;
  }

  tbody.innerHTML = rows.map(o => {
    const priCls  = o.priority_class || 'NORMAL';
    const pColor  = priorityColor(priCls);
    const partner = o.partner_name || '—';
    const items   = (o.items || []).map(i => `${i.qty}× ${i.name}`).join(', ');
    const isCrit  = priCls === 'CRITICAL';

    return `<tr class="${isCrit ? 'order-row-critical' : ''}" onclick="openOrderModal('${o.id}')" style="cursor:pointer">
      <td><span class="pri-indicator ${priCls}" style="display:inline-block;width:12px;height:12px;border-radius:50%;background:${pColor}"></span></td>
      <td><span class="order-id">${o.id}</span></td>
      <td class="customer-cell">${o.customer}</td>
      <td><span style="font-size:.78rem">${o.restaurant_name || '—'}</span></td>
      <td style="font-size:.78rem;max-width:160px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${items}</td>
      <td style="font-size:.82rem">${o.prep_time || '—'} min</td>
      <td style="font-size:.82rem">${o.distance_km} km</td>
      <td><span class="badge badge-${o.status}"><span class="status-dot ${o.status}"></span>${statusLabel(o.status)}</span></td>
      <td><span style="font-size:.78rem">${partner}</span></td>
      <td>
        <div style="display:flex;align-items:center;gap:.5rem">
          <div style="width:42px;height:42px;position:relative">
            <svg width="42" height="42" viewBox="0 0 42 42">
              <circle cx="21" cy="21" r="16" fill="none" stroke="#e5e7eb" stroke-width="4"/>
              <circle cx="21" cy="21" r="16" fill="none" stroke="${pColor}" stroke-width="4"
                stroke-dasharray="${Math.round((o.priority_score||0)/100*100.5)} 100.5"
                stroke-dashoffset="25" stroke-linecap="round" transform="rotate(-90 21 21)"/>
            </svg>
            <span style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:.62rem;font-weight:800;color:${pColor}">${o.priority_score||0}</span>
          </div>
          <span class="badge" style="background:${pColor}18;color:${pColor};border:1px solid ${pColor}30;font-size:.65rem">${priCls}</span>
        </div>
      </td>
      <td onclick="event.stopPropagation()">
        <div style="display:flex;gap:.3rem;flex-wrap:wrap">
          <button class="action-btn" onclick="openOrderModal('${o.id}')">🔍 Details</button>
          ${o.status !== 'delivered' ? `<button class="action-btn" onclick="quickAssign('${o.id}')">🛵 Assign</button>` : ''}
        </div>
      </td>
    </tr>`;
  }).join('');
}

// ── Order Modal ───────────────────────────────────────────────────────────────
async function openOrderModal(orderId) {
  document.getElementById('order-modal').classList.add('open');
  document.getElementById('modal-title').textContent = 'Order Details — ' + orderId;
  document.getElementById('modal-body').innerHTML = `<div style="text-align:center;padding:3rem"><div class="spinner"></div></div>`;

  const d = await fetch('/api/orders/' + orderId).then(r => r.json()).catch(() => null);
  if (!d) { document.getElementById('modal-body').innerHTML = '<p>Failed to load order.</p>'; return; }

  const pColor  = priorityColor(d.priority_class || 'NORMAL');
  const factors = d.priority_factors || {};
  const factorBars = Object.entries(factors).map(([k, v]) =>
    `<div class="factor-bar-item">
      <div class="factor-bar-label"><span>${k}</span><span>${v}/100</span></div>
      <div class="factor-bar-track"><div class="factor-bar-fill" style="width:${v}%;background:${v>70?'#ef4444':v>45?'#f97316':'#8b5cf6'}"></div></div>
    </div>`
  ).join('');

  const rec = d.partner_recommendation || {};
  const recPartner = rec.partner;

  document.getElementById('modal-body').innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:1.25rem;margin-bottom:1.25rem">
      <!-- Score -->
      <div style="background:linear-gradient(135deg,#1e1b4b,#4c1d95);color:white;border-radius:var(--radius);padding:1.25rem;text-align:center">
        <div style="font-size:.7rem;opacity:.7;letter-spacing:.5px;margin-bottom:.4rem">AI PRIORITY SCORE</div>
        <div style="font-size:3rem;font-weight:900;color:${pColor};line-height:1">${d.priority_score||0}</div>
        <div style="margin-top:.5rem">
          <span style="background:${pColor};color:white;padding:.25rem .8rem;border-radius:99px;font-size:.72rem;font-weight:700">${d.priority_class||'NORMAL'}</span>
        </div>
      </div>
      <!-- Info -->
      <div>
        <div style="margin-bottom:.5rem;font-size:.78rem;color:var(--gray-500)">CUSTOMER</div>
        <div style="font-weight:700;margin-bottom:.75rem">${d.customer}</div>
        <div style="margin-bottom:.5rem;font-size:.78rem;color:var(--gray-500)">RESTAURANT</div>
        <div style="font-weight:700;margin-bottom:.75rem">${d.restaurant_name||'—'}</div>
        <div style="margin-bottom:.5rem;font-size:.78rem;color:var(--gray-500)">STATUS</div>
        <span class="badge badge-${d.status}"><span class="status-dot ${d.status}"></span>${statusLabel(d.status)}</span>
        <div style="margin-top:.75rem;font-size:.78rem;color:var(--gray-500)">Placed ${timeAgo(d.placed_at)}</div>
      </div>
    </div>

    <hr class="section-sep"/>

    <!-- Metrics -->
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:.75rem;margin-bottom:1.25rem;text-align:center">
      <div style="background:var(--gray-50);border-radius:10px;padding:.75rem">
        <div style="font-size:1.2rem;font-weight:800">${(d.priority_metrics||{}).waiting_min||0} min</div>
        <div style="font-size:.7rem;color:var(--gray-500)">Waiting</div>
      </div>
      <div style="background:var(--gray-50);border-radius:10px;padding:.75rem">
        <div style="font-size:1.2rem;font-weight:800">${d.prep_time||'—'} min</div>
        <div style="font-size:.7rem;color:var(--gray-500)">Prep Time</div>
      </div>
      <div style="background:var(--gray-50);border-radius:10px;padding:.75rem">
        <div style="font-size:1.2rem;font-weight:800">${d.distance_km||'—'} km</div>
        <div style="font-size:.7rem;color:var(--gray-500)">Distance</div>
      </div>
      <div style="background:var(--gray-50);border-radius:10px;padding:.75rem">
        <div style="font-size:1.2rem;font-weight:800">${(d.priority_metrics||{}).rest_load_pct||0}%</div>
        <div style="font-size:.7rem;color:var(--gray-500)">Kitchen Load</div>
      </div>
    </div>

    <!-- Factor Breakdown -->
    <div style="margin-bottom:1.25rem">
      <div style="font-size:.78rem;font-weight:700;color:var(--gray-500);margin-bottom:.75rem;letter-spacing:.4px">PRIORITY FACTOR BREAKDOWN</div>
      <div class="factor-bar-list">${factorBars}</div>
    </div>

    <hr class="section-sep"/>

    <!-- Reasoning -->
    <div style="margin-bottom:1.25rem">
      <div style="font-size:.78rem;font-weight:700;color:var(--gray-500);margin-bottom:.5rem;letter-spacing:.4px">🤖 WHY THIS PRIORITY</div>
      <ul class="reasoning-list">
        ${(d.priority_reasoning||['No specific concerns.']).map(r=>`<li>${r}</li>`).join('')}
      </ul>
    </div>

    <hr class="section-sep"/>

    <!-- Partner Recommendation -->
    <div>
      <div style="font-size:.78rem;font-weight:700;color:var(--gray-500);margin-bottom:.75rem;letter-spacing:.4px">🛵 RECOMMENDED DELIVERY PARTNER</div>
      ${recPartner ? `
      <div style="background:var(--purple-50);border:1.5px solid var(--purple-200);border-radius:var(--radius);padding:1rem;margin-bottom:.75rem">
        <div style="display:flex;align-items:center;gap:.75rem">
          <span style="font-size:1.8rem">🏍️</span>
          <div>
            <div style="font-weight:800;font-size:.95rem">${recPartner.name}</div>
            <div style="font-size:.75rem;color:var(--gray-500)">Zone: ${recPartner.zone} &nbsp;•&nbsp; ⭐${recPartner.rating} &nbsp;•&nbsp; ${recPartner.distance_from_hub_km}km away &nbsp;•&nbsp; ${recPartner.current_orders} active order(s)</div>
          </div>
          <button class="btn btn-primary btn-sm" style="margin-left:auto" onclick="assignPartner('${d.id}','${recPartner.id}')">Assign</button>
        </div>
      </div>
      <div style="font-size:.78rem;color:var(--gray-600);line-height:1.5;padding:.6rem;background:var(--gray-50);border-radius:8px">${rec.reason}</div>
      ` : `<div style="font-size:.85rem;color:var(--gray-500)">No available partner. All delivery partners are busy.</div>`}
    </div>

    <hr class="section-sep"/>

    <!-- Update Status -->
    <div style="display:flex;align-items:center;gap:.75rem;flex-wrap:wrap">
      <span style="font-size:.82rem;font-weight:600;color:var(--gray-600)">Update Status:</span>
      <select class="status-select" id="status-update-select">
        <option value="pending" ${d.status==='pending'?'selected':''}>Pending</option>
        <option value="preparing" ${d.status==='preparing'?'selected':''}>Preparing</option>
        <option value="out_for_delivery" ${d.status==='out_for_delivery'?'selected':''}>Out for Delivery</option>
        <option value="delivered" ${d.status==='delivered'?'selected':''}>Delivered</option>
      </select>
      <button class="btn btn-secondary btn-sm" onclick="updateStatus('${d.id}')">Update</button>
    </div>
  `;
}

function closeModal() {
  document.getElementById('order-modal').classList.remove('open');
}

async function updateStatus(orderId) {
  const select = document.getElementById('status-update-select');
  const status = select.value;
  const res = await fetch(`/api/orders/${orderId}/status`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status })
  }).then(r => r.json()).catch(() => null);
  if (res?.success) {
    showToast('Status updated to: ' + statusLabel(status), 'success');
    closeModal();
    loadAll();
  }
}

async function assignPartner(orderId, partnerId) {
  const res = await fetch(`/api/orders/${orderId}/assign`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ partner_id: partnerId })
  }).then(r => r.json()).catch(() => null);
  if (res?.success) {
    showToast('Delivery partner assigned successfully! 🛵', 'success');
    closeModal();
    loadAll();
  }
}

async function quickAssign(orderId) {
  const d = await fetch('/api/recommend-partner/' + orderId).then(r => r.json()).catch(() => null);
  if (!d?.partner) { showToast('No available delivery partner', 'error'); return; }
  if (confirm(`Assign ${d.partner.name} to ${orderId}?\n\nReason: ${d.reason}`)) {
    await assignPartner(orderId, d.partner.id);
  }
}

// ── AI Recommendations ────────────────────────────────────────────────────────
async function loadRecommendations() {
  const [recs, batches] = await Promise.all([
    fetch('/api/dashboard/recommendations').then(r => r.json()).catch(() => []),
    fetch('/api/dashboard/batching').then(r => r.json()).catch(() => []),
  ]);

  const recList = document.getElementById('rec-list');
  if (!recs.length) {
    recList.innerHTML = `<div style="text-align:center;opacity:.6;padding:2rem"><div style="font-size:2rem;margin-bottom:.75rem">✅</div><p>All orders are running smoothly. No urgent actions needed.</p></div>`;
  } else {
    recList.innerHTML = recs.map(r => `
      <div class="rec-item" ${r.order_id ? `onclick="openOrderModal('${r.order_id}')"` : ''} style="${r.order_id?'cursor:pointer':''}">
        <span style="font-size:1.3rem">${r.icon}</span>
        <div class="rec-text" style="flex:1">
          <h4>${r.title}</h4>
          <p>${r.description}</p>
        </div>
        <span class="rec-priority ${r.priority}">${r.priority}</span>
      </div>`).join('');
  }

  const batchList = document.getElementById('batch-list');
  if (!batches.length) {
    batchList.innerHTML = `<div class="empty-state"><div class="empty-icon">🚗</div><h3>No batching opportunities</h3><p>No orders with nearby destinations found right now.</p></div>`;
  } else {
    batchList.innerHTML = batches.map(b => `
      <div style="background:var(--purple-50);border:1.5px solid var(--purple-200);border-radius:var(--radius);padding:1rem;margin-bottom:.75rem">
        <div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.5rem">
          <span style="font-size:1.1rem">📦</span>
          <span style="font-weight:700;font-size:.9rem">Batch: ${b.orders.join(' + ')}</span>
          <span class="badge badge-purple" style="margin-left:auto">Saves ~${b.savings_km}km</span>
        </div>
        <div style="font-size:.78rem;color:var(--gray-600)">${b.reason}</div>
      </div>`).join('');
  }
}

// ── Delay Monitor ─────────────────────────────────────────────────────────────
async function loadDelayMonitor() {
  const data = await fetch('/api/dashboard/delay-predictions').then(r => r.json()).catch(() => []);
  const atRisk = data.filter(d => d.at_risk);
  document.getElementById('delay-count-badge').textContent = atRisk.length + ' at risk';

  const list = document.getElementById('delay-list');
  if (!data.length) { list.innerHTML = '<div class="empty-state"><div class="empty-icon">✅</div><h3>No orders to monitor</h3></div>'; return; }

  list.innerHTML = data.map(d => `
    <div class="delay-item ${d.risk_level}" onclick="${d.risk_level!=='NONE'?`openOrderModal('${d.order_id}')`:'void 0'}" style="${d.risk_level!=='NONE'?'cursor:pointer':''}">
      <div>
        <div class="delay-badge ${d.risk_level}">${d.risk_level}</div>
      </div>
      <div class="delay-info">
        <h4>${d.order_id} — ${d.customer}</h4>
        <p>Status: ${statusLabel(d.status)} &nbsp;•&nbsp; Est. total: ${d.estimated_total_min} min &nbsp;•&nbsp; ${d.reason}</p>
      </div>
      <div class="delay-time">
        <div class="min">${d.predicted_delay_min > 0 ? '+' + d.predicted_delay_min : '✓'}</div>
        <div class="label">${d.predicted_delay_min > 0 ? 'min late' : 'on time'}</div>
      </div>
    </div>`).join('');
}

// ── What-If Simulator ─────────────────────────────────────────────────────────
async function runSimulation() {
  const extra = parseInt(document.getElementById('extra-orders').value) || 5;
  const btn   = document.querySelector('[onclick="runSimulation()"]');
  btn.disabled = true;
  btn.textContent = 'Simulating…';

  const data = await fetch('/api/simulate/what-if', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ extra_orders: extra })
  }).then(r => r.json()).catch(() => null);

  btn.disabled = false;
  btn.textContent = '⚡ Run Simulation';

  if (!data) { showToast('Simulation failed', 'error'); return; }

  document.getElementById('simulation-placeholder').style.display = 'none';
  document.getElementById('simulation-result').style.display = 'block';

  const renderPanel = (d) => `
    <div class="comparison-row"><span class="label">Active Orders</span><span class="value">${d.active_orders}</span></div>
    <div class="comparison-row"><span class="label">Available Partners</span><span class="value">${d.available_partners}</span></div>
    <div class="comparison-row"><span class="label">Restaurant Load</span><span class="value">${d.restaurant_load}%</span></div>
    <div class="comparison-row"><span class="label">At-Risk Orders</span><span class="value">${d.at_risk_orders}</span></div>
    <div class="comparison-row"><span class="label">Avg ETA</span><span class="value">${d.avg_eta_min} min</span></div>`;

  document.getElementById('before-panel').innerHTML = renderPanel(data.before);
  document.getElementById('after-panel').innerHTML  = renderPanel(data.after);
  document.getElementById('ai-action-text').textContent = data.ai_action;

  const surgeColors = { CRITICAL: '#dc2626', HIGH: '#f97316', MEDIUM: '#d97706' };
  const badge = document.querySelector('.whatif-header h2');
  if (badge) badge.innerHTML = `🔮 What-If Simulator <span style="background:${surgeColors[data.surge_level]||'#6b7280'};color:white;padding:.2rem .7rem;border-radius:99px;font-size:.72rem;margin-left:.5rem">${data.surge_level} SURGE</span>`;
}

function resetSimulation() {
  document.getElementById('simulation-result').style.display = 'none';
  document.getElementById('simulation-placeholder').style.display = 'block';
  document.getElementById('extra-orders').value = 5;
}

// ── Delivery Partners ─────────────────────────────────────────────────────────
async function loadPartners() {
  const data = await fetch('/api/partners').then(r => r.json()).catch(() => []);
  const grid = document.getElementById('partners-grid');
  grid.innerHTML = data.map(p => {
    const avail = p.available && p.current_orders < 2;
    return `<div class="card card-body" style="border-left:4px solid ${avail?'var(--success)':'var(--gray-300)'}">
      <div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.75rem">
        <span style="font-size:2rem">${p.emoji}</span>
        <div>
          <div style="font-weight:800;font-size:.95rem">${p.name}</div>
          <div style="font-size:.75rem;color:var(--gray-500)">${p.zone} Zone &nbsp;•&nbsp; ${p.id}</div>
        </div>
        <span class="badge ${avail?'badge-normal':'badge-at_risk'}" style="margin-left:auto">${avail?'Available':'Busy'}</span>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem;font-size:.78rem">
        <div style="background:var(--gray-50);border-radius:8px;padding:.5rem;text-align:center">
          <div style="font-weight:800;font-size:1rem">${p.rating}</div>
          <div style="color:var(--gray-500)">Rating</div>
        </div>
        <div style="background:var(--gray-50);border-radius:8px;padding:.5rem;text-align:center">
          <div style="font-weight:800;font-size:1rem">${p.current_orders}</div>
          <div style="color:var(--gray-500)">Active</div>
        </div>
        <div style="background:var(--gray-50);border-radius:8px;padding:.5rem;text-align:center">
          <div style="font-weight:800;font-size:1rem">${p.distance_from_hub_km}km</div>
          <div style="color:var(--gray-500)">From Hub</div>
        </div>
        <div style="background:var(--gray-50);border-radius:8px;padding:.5rem;text-align:center">
          <div style="font-weight:800;font-size:1rem">${p.completed_today}</div>
          <div style="color:var(--gray-500)">Done Today</div>
        </div>
      </div>
    </div>`;
  }).join('');
}

// ── Charts ────────────────────────────────────────────────────────────────────
function renderCharts() {
  const statusCounts = {};
  const priorityCounts = {};
  allOrders.forEach(o => {
    statusCounts[o.status] = (statusCounts[o.status]||0) + 1;
    priorityCounts[o.priority_class] = (priorityCounts[o.priority_class]||0) + 1;
  });

  const defaultOpts = { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } } } };

  // Status Chart
  renderChart('status-chart', 'doughnut', {
    labels: ['Pending', 'Preparing', 'Out for Delivery', 'Delivered'],
    datasets: [{ data: [
      statusCounts.pending||0, statusCounts.preparing||0,
      statusCounts.out_for_delivery||0, statusCounts.delivered||0
    ], backgroundColor: ['#94a3b8','#f59e0b','#3b82f6','#10b981'], borderWidth: 0 }]
  }, defaultOpts);

  // Priority Chart
  renderChart('priority-chart', 'doughnut', {
    labels: ['Critical', 'High', 'Normal', 'Low'],
    datasets: [{ data: [
      priorityCounts.CRITICAL||0, priorityCounts.HIGH||0,
      priorityCounts.NORMAL||0,   priorityCounts.LOW||0
    ], backgroundColor: ['#dc2626','#ea580c','#10b981','#3b82f6'], borderWidth: 0 }]
  }, defaultOpts);

  // Restaurant Load
  fetch('/api/restaurants').then(r=>r.json()).then(rests => {
    renderChart('load-chart', 'bar', {
      labels: rests.map(r => r.name),
      datasets: [{
        label: 'Kitchen Load %',
        data: rests.map(r => r.current_load),
        backgroundColor: rests.map(r => r.current_load>=80?'#ef4444':r.current_load>=60?'#f59e0b':'#8b5cf6'),
        borderRadius: 8,
      }]
    }, { ...defaultOpts, plugins: { ...defaultOpts.plugins, legend: { display: false } }, scales: { y: { max: 100, grid: { color: '#f1f5f9' } } } });
  });

  // Risk vs ETA
  const riskMap = { HIGH: 2, MEDIUM: 1, LOW: 0.5, NONE: 0 };
  fetch('/api/dashboard/delay-predictions').then(r=>r.json()).then(preds => {
    renderChart('risk-chart', 'scatter', {
      datasets: [{
        label: 'Orders',
        data: preds.map(p => ({ x: p.estimated_total_min, y: p.predicted_delay_min, label: p.order_id })),
        backgroundColor: preds.map(p => ({HIGH:'#ef4444cc',MEDIUM:'#f97316cc',LOW:'#f59e0bcc',NONE:'#10b981cc'}[p.risk_level]||'#8b5cf6cc')),
        pointRadius: 8,
      }]
    }, { ...defaultOpts, scales: { x: { title: { display: true, text: 'Est. Total Time (min)' } }, y: { title: { display: true, text: 'Delay (min)' } } }, plugins: { legend: { display: false } } });
  });
}

function renderChart(id, type, data, options) {
  const ctx = document.getElementById(id);
  if (!ctx) return;
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart(ctx, { type, data, options: { ...options, animation: { duration: 500 } } });
}

// ── Modal keyboard close ──────────────────────────────────────────────────────
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
document.getElementById('order-modal').addEventListener('click', e => {
  if (e.target === document.getElementById('order-modal')) closeModal();
});

// ── Auto-refresh ──────────────────────────────────────────────────────────────
function startAutoRefresh() {
  refreshInterval = setInterval(loadAll, 30000);
  countdownInterval = setInterval(() => {
    countdownVal--;
    const el = document.getElementById('countdown');
    if (el) el.textContent = countdownVal;
    if (countdownVal <= 0) countdownVal = 30;
  }, 1000);
}

// ── Init ──────────────────────────────────────────────────────────────────────
loadAll();
handleTabFromUrl();
startAutoRefresh();
