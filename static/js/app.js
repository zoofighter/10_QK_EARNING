/**
 * QK_EARNING × Memory Claude
 * Company-Centric Intelligence Workspace & Macro Value Chain Simulator
 */

// ─── Global State ───
const state = {
  currentMode: 'company-hub', // 'company-hub', 'macro-hub', 'indicators', 'calendar', 'filings-archive'
  currentTicker: 'NVDA',
  currentSubTab: 'snapshot',
  entities: [],
  layers: [],
  sidebarCollapsed: false,
  charts: {},
  sankeyData: null,
  macroSimulation: {
    capex: 35,
    hbm: 30,
    asp: 0,
    yield: 0
  },
  newsCache: [],
  currentNewsFilter: ''
};

// ─── Flag & Layer Helpers ───
const COUNTRY_FLAGS = {
  'US': '🇺🇸',
  'KR': '🇰🇷',
  'TW': '🇹🇼',
  'NL': '🇳🇱',
  'JP': '🇯🇵',
  'GB': '🇬🇧',
  'FR': '🇫🇷'
};

const LAYER_COLORS = {
  'L2_HYPERSCALER': '#06B6D4',
  'L3_COMPUTE': '#8B5CF6',
  'L4_FOUNDRY': '#10B981',
  'L5_MEMORY': '#F59E0B',
  'L6_OPTICAL': '#3B82F6',
  'L7_INFRA': '#EC4899',
  'L8_POWER': '#6366F1'
};

// ─── Chart Cleanup Helper ───
function destroyChart(key) {
  if (state.charts[key]) {
    try {
      state.charts[key].destroy();
    } catch (e) {
      console.warn(`Error destroying chart ${key}:`, e);
    }
    delete state.charts[key];
  }
}

// ─── App Initialization ───
document.addEventListener('DOMContentLoaded', async () => {
  // Set current date in header
  const today = new Date();
  const dateStr = today.toISOString().split('T')[0];
  const dateElem = document.getElementById('header-today-date');
  if (dateElem) dateElem.textContent = dateStr;

  // Initialize Google Charts
  if (window.google && window.google.charts) {
    google.charts.load('current', { packages: ['sankey'] });
  }

  // Load layers and entities master
  await loadMasterData();

  // Setup Global Keyboard Shortcuts (Cmd+K / Ctrl+K / [/])
  setupKeyboardShortcuts();

  // Handle Initial Route from URL Hash
  handleHashRouting();

  // Listen for Hash Changes
  window.addEventListener('hashchange', handleHashRouting);
});


// ─── Routing & Mode Switching ───

function handleHashRouting() {
  const hash = window.location.hash.replace('#', '').trim();
  if (!hash) {
    switchMainMode('company-hub', 'NVDA', 'snapshot');
    return;
  }

  const parts = hash.split('/');
  const route = parts[0];

  if (route === 'company') {
    const ticker = parts[1] || 'NVDA';
    const subtab = parts[2] || 'snapshot';
    switchMainMode('company-hub', ticker, subtab);
  } else if (route === 'macro') {
    switchMainMode('macro-hub');
  } else if (route === 'indicators') {
    switchMainMode('indicators');
  } else if (route === 'calendar') {
    switchMainMode('calendar');
  } else if (route === 'filings') {
    switchMainMode('filings-archive');
  } else {
    switchMainMode('company-hub', 'NVDA', 'snapshot');
  }
}

function updateHash() {
  if (state.currentMode === 'company-hub') {
    window.location.hash = `#company/${state.currentTicker}/${state.currentSubTab}`;
  } else if (state.currentMode === 'macro-hub') {
    window.location.hash = '#macro';
  } else if (state.currentMode === 'indicators') {
    window.location.hash = '#indicators';
  } else if (state.currentMode === 'calendar') {
    window.location.hash = '#calendar';
  } else if (state.currentMode === 'filings-archive') {
    window.location.hash = '#filings';
  }
}

function switchMainMode(mode, targetTicker, targetSubTab) {
  state.currentMode = mode;

  // Toggle mode views
  const modeViews = ['company-hub', 'macro-hub', 'indicators', 'calendar', 'filings-archive'];
  modeViews.forEach(m => {
    const el = document.getElementById(`mode-${m}`);
    if (el) el.style.display = (m === mode) ? 'block' : 'none';
  });

  // Toggle header button active class
  const modeBtns = {
    'company-hub': 'btn-mode-company',
    'macro-hub': 'btn-mode-macro',
    'indicators': 'btn-mode-indicators',
    'calendar': 'btn-mode-calendar',
    'filings-archive': 'btn-mode-filings'
  };
  Object.entries(modeBtns).forEach(([m, btnId]) => {
    const b = document.getElementById(btnId);
    if (b) {
      if (m === mode) b.classList.add('active');
      else b.classList.remove('active');
    }
  });

  if (mode === 'company-hub') {
    if (targetTicker) state.currentTicker = targetTicker;
    highlightSidebarActiveItem(state.currentTicker);
    loadCompanyWorkspace(state.currentTicker);
    switchCompanySubTab(targetSubTab || state.currentSubTab || 'snapshot', false);
  } else if (mode === 'macro-hub') {
    loadMacroHub();
  } else if (mode === 'indicators') {
    loadIndicators();
  } else if (mode === 'calendar') {
    loadCalendar();
  } else if (mode === 'filings-archive') {
    loadFilingsArchive();
  }

  updateHash();
}

function switchCompanySubTab(subTabKey, shouldUpdateHash = true) {
  state.currentSubTab = subTabKey;

  // Toggle button classes
  const tabKeys = ['snapshot', 'financials', 'filings', 'news', 'analysts', 'macro'];
  tabKeys.forEach(k => {
    const btn = document.getElementById(`btn-subtab-${k}`);
    const pane = document.getElementById(`pane-subtab-${k}`);
    if (btn) {
      if (k === subTabKey) btn.classList.add('active');
      else btn.classList.remove('active');
    }
    if (pane) {
      if (k === subTabKey) pane.classList.add('active');
      else pane.classList.remove('active');
    }
  });

  if (shouldUpdateHash) {
    updateHash();
  }
  loadCurrentSubTabData();
}


// ─── Master Data & Sidebar Tree ───

async function loadMasterData() {
  try {
    const [layersRes, entitiesRes, calendarRes] = await Promise.all([
      fetch('/api/layers').then(r => r.json()),
      fetch('/api/entities').then(r => r.json()),
      fetch('/api/calendar').then(r => r.json()).catch(() => ({ data: [] }))
    ]);

    state.layers = layersRes.data || [];
    state.entities = entitiesRes.data || [];

    // Map Calendar D-Days to Entities
    const calendarMap = {};
    if (calendarRes && calendarRes.data) {
      const today = new Date();
      calendarRes.data.forEach(item => {
        if (!calendarMap[item.ticker]) {
          try {
            const exp = new Date(item.expected_date.substring(0, 10));
            const diffDays = Math.ceil((exp - today) / (1000 * 60 * 60 * 24));
            calendarMap[item.ticker] = diffDays;
          } catch (e) {}
        }
      });
    }

    state.entities.forEach(e => {
      e.dDay = calendarMap[e.ticker] !== undefined ? calendarMap[e.ticker] : null;
    });

    renderSidebarCompanies(state.entities);
    const countBadge = document.getElementById('sidebar-total-count');
    if (countBadge) countBadge.textContent = `${state.entities.length}개사`;
  } catch (err) {
    console.error('Failed to load master data:', err);
  }
}

function renderSidebarCompanies(entitiesList) {
  const container = document.getElementById('sidebar-companies-tree');
  if (!container) return;

  // Group entities by layer
  const grouped = {};
  state.layers.forEach(l => {
    grouped[l.code] = {
      layer: l,
      companies: []
    };
  });

  entitiesList.forEach(e => {
    if (grouped[e.layer_code]) {
      grouped[e.layer_code].companies.push(e);
    }
  });

  let html = '';
  Object.values(grouped).forEach(g => {
    if (g.companies.length === 0) return;
    const lCode = g.layer.code;
    const lColor = LAYER_COLORS[lCode] || '#94a3b8';

    html += `
      <div class="layer-accordion-group open" id="layer-group-${lCode}">
        <div class="layer-accordion-header" onclick="toggleLayerGroup('${lCode}')">
          <div class="layer-accordion-title">
            <span class="layer-dot" style="background: ${lColor};"></span>
            <span>${g.layer.name_ko}</span>
            <span style="font-size: 0.72rem; color: var(--text-muted);">(${g.companies.length})</span>
          </div>
          <span class="layer-chevron">▶</span>
        </div>
        <div class="layer-companies-list">
          ${g.companies.map(c => {
            const flag = COUNTRY_FLAGS[c.country] || '🌐';
            let dDayBadge = '';
            if (c.dDay !== null) {
              if (c.dDay === 0) {
                dDayBadge = `<span class="company-dday-badge imminent">🔥 D-Day</span>`;
              } else if (c.dDay > 0 && c.dDay <= 7) {
                dDayBadge = `<span class="company-dday-badge imminent">⚡ D-${c.dDay}</span>`;
              } else if (c.dDay > 0 && c.dDay <= 30) {
                dDayBadge = `<span class="company-dday-badge near">D-${c.dDay}</span>`;
              } else if (c.dDay > 30) {
                dDayBadge = `<span class="company-dday-badge">D-${c.dDay}</span>`;
              }
            }
            return `
              <button class="company-item-btn ${c.ticker === state.currentTicker ? 'active' : ''}"
                      id="sidebar-item-${c.ticker.replace('.', '_')}"
                      onclick="selectCompany('${c.ticker}')">
                <div class="company-item-left">
                  <span class="company-flag">${flag}</span>
                  <span class="company-ticker">${c.ticker}</span>
                  <span class="company-name-ko">${c.name_ko}</span>
                </div>
                ${dDayBadge}
              </button>
            `;
          }).join('')}
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

function toggleLayerGroup(layerCode) {
  const grp = document.getElementById(`layer-group-${layerCode}`);
  if (grp) grp.classList.toggle('open');
}

function handleSidebarFilter(query) {
  const q = query.trim().toLowerCase();
  if (!q) {
    renderSidebarCompanies(state.entities);
    return;
  }

  const filtered = state.entities.filter(e =>
    e.ticker.toLowerCase().includes(q) ||
    e.name_ko.toLowerCase().includes(q) ||
    e.name_en.toLowerCase().includes(q)
  );
  renderSidebarCompanies(filtered);
}

function highlightSidebarActiveItem(ticker) {
  document.querySelectorAll('.company-item-btn').forEach(b => b.classList.remove('active'));
  const activeBtn = document.getElementById(`sidebar-item-${ticker.replace('.', '_')}`);
  if (activeBtn) activeBtn.classList.add('active');
}

function toggleSidebar() {
  const sidebar = document.getElementById('company-sidebar');
  const btn = document.getElementById('sidebar-toggle-btn');
  if (!sidebar) return;

  state.sidebarCollapsed = !state.sidebarCollapsed;
  if (state.sidebarCollapsed) {
    sidebar.classList.add('collapsed');
    if (btn) btn.innerHTML = '▶';
  } else {
    sidebar.classList.remove('collapsed');
    if (btn) btn.innerHTML = '◀';
  }
}

function selectCompany(ticker) {
  state.currentTicker = ticker;
  highlightSidebarActiveItem(ticker);
  if (state.currentMode !== 'company-hub') {
    switchMainMode('company-hub', ticker, state.currentSubTab);
  } else {
    updateHash();
    loadCompanyWorkspace(ticker);
  }
}


// ─── Company Workspace & Sub-Tabs Loading ───

async function loadCompanyWorkspace(ticker) {
  try {
    const res = await fetch(`/api/companies/${ticker}/full`).then(r => r.json());
    if (res.status !== 'success') {
      console.error('Failed to load company profile:', res);
      return;
    }

    const { entity, stock, calendar, financials, analyst, value_chain } = res;

    // 1. Header Banner
    const nameKo = document.getElementById('company-name-ko');
    const nameEn = document.getElementById('company-name-en');
    const avatar = document.getElementById('company-avatar-box');
    const layerBadge = document.getElementById('company-layer-badge');
    const countryTag = document.getElementById('company-country-tag');
    const exchangeTag = document.getElementById('company-exchange-tag');
    const tickerTag = document.getElementById('company-ticker-tag');
    const cikTag = document.getElementById('company-cik-tag');
    const fiscalTag = document.getElementById('company-fiscal-tag');

    if (nameKo) nameKo.textContent = entity.name_ko;
    if (nameEn) nameEn.textContent = entity.name_en;
    if (avatar) avatar.textContent = entity.ticker.substring(0, 2);
    if (layerBadge) {
      layerBadge.textContent = entity.layer_name_ko;
      const color = LAYER_COLORS[entity.layer_code] || '#8B5CF6';
      layerBadge.style.color = color;
      layerBadge.style.borderColor = color;
      layerBadge.style.background = `${color}20`;
    }
    if (countryTag) countryTag.textContent = `${COUNTRY_FLAGS[entity.country] || '🌐'} ${entity.country}`;
    if (exchangeTag) exchangeTag.textContent = entity.exchange || '거래소';
    if (tickerTag) tickerTag.textContent = `티커: ${entity.ticker}`;
    if (cikTag) cikTag.textContent = `CIK: ${entity.sec_cik || 'N/A'}`;
    if (fiscalTag) fiscalTag.textContent = `결산월: ${entity.fiscal_year_end || '12'}월`;

    // Price Box
    const curPrice = document.getElementById('company-current-price');
    const prChange = document.getElementById('company-price-change');
    const prDate = document.getElementById('company-price-date');

    if (curPrice) curPrice.textContent = stock.price ? `$${stock.price.toFixed(2)}` : '-';
    if (prChange) {
      const isUp = (stock.change >= 0);
      prChange.className = `profile-price-change ${isUp ? 'up' : 'down'}`;
      prChange.innerHTML = `
        <span>${isUp ? '▲' : '▼'} ${isUp ? '+' : ''}${stock.change_pct}%</span>
        <span style="font-size: 0.78rem; opacity: 0.8;">(${isUp ? '+' : ''}${stock.change})</span>
      `;
    }
    if (prDate) prDate.textContent = stock.date ? `기준: ${stock.date}` : '';

    // 2. 4 Quick KPI Summary Cards
    const ddayVal = document.getElementById('kpi-dday-val');
    const ddayDate = document.getElementById('kpi-dday-date');
    if (ddayVal) ddayVal.textContent = calendar.d_day_label || '-';
    if (ddayDate) {
      ddayDate.textContent = calendar.expected_date ?
        `${calendar.expected_date} ${calendar.call_time_et || ''}` : '일정 미정';
    }

    const revVal = document.getElementById('kpi-rev-val');
    const revYoY = document.getElementById('kpi-rev-yoy');
    if (revVal) revVal.textContent = financials.revenue ? `$${Number(financials.revenue).toLocaleString()}M` : '-';
    if (revYoY) {
      if (financials.revenue_yoy !== null && financials.revenue_yoy !== undefined) {
        revYoY.textContent = `YoY ${financials.revenue_yoy >= 0 ? '+' : ''}${financials.revenue_yoy}%`;
        revYoY.style.color = financials.revenue_yoy >= 0 ? '#34d399' : '#f87171';
      } else {
        revYoY.textContent = 'YoY -';
      }
    }

    const opmVal = document.getElementById('kpi-opm-val');
    const opInc = document.getElementById('kpi-op-income');
    if (opmVal) opmVal.textContent = financials.op_margin_pct ? `${financials.op_margin_pct}%` : '-';
    if (opInc) opInc.textContent = financials.op_income ? `영업이익 $${Number(financials.op_income).toLocaleString()}M` : '-';

    const targetVal = document.getElementById('kpi-target-val');
    const targetUpside = document.getElementById('kpi-target-upside');
    if (targetVal) targetVal.textContent = analyst.target_mean ? `$${analyst.target_mean.toFixed(2)}` : '-';
    if (targetUpside) {
      if (analyst.upside_pct !== null && analyst.upside_pct !== undefined) {
        targetUpside.textContent = `상승여력 ${analyst.upside_pct >= 0 ? '+' : ''}${analyst.upside_pct}%`;
        targetUpside.style.color = analyst.upside_pct >= 0 ? '#38bdf8' : '#f87171';
      } else {
        targetUpside.textContent = '상승여력 -';
      }
    }

    // Role Description in Snapshot
    const roleElem = document.getElementById('company-role-description');
    if (roleElem) roleElem.textContent = value_chain.role || '밸류체인 핵심 구성원';

    // Upstream & Downstream Quick Mapping
    renderQuickSuppliersCustomers(value_chain);

    // Render Sub Tab Content
    loadCurrentSubTabData();
  } catch (err) {
    console.error('Failed to load company workspace:', err);
  }
}

function renderQuickSuppliersCustomers(chain) {
  const supEl = document.getElementById('company-quick-suppliers');
  const custEl = document.getElementById('company-quick-customers');

  if (supEl) {
    if (chain.suppliers && chain.suppliers.length > 0) {
      supEl.innerHTML = chain.suppliers.map(s => `
        <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 0.6rem 0.85rem; display: flex; justify-content: space-between; align-items: center;">
          <div>
            <strong style="color: #fff; cursor: pointer; text-decoration: underline;" onclick="selectCompany('${s.ticker}')">${s.name} (${s.ticker})</strong>
            <div style="font-size: 0.78rem; color: var(--text-muted);">${s.role}</div>
          </div>
          <button class="btn-secondary" onclick="selectCompany('${s.ticker}')" style="padding: 0.2rem 0.5rem; font-size: 0.72rem;">이동 →</button>
        </div>
      `).join('');
    } else {
      supEl.innerHTML = '<div style="color: var(--text-muted); font-size: 0.82rem;">상류 공급사 매핑 데이터 없음</div>';
    }
  }

  if (custEl) {
    if (chain.customers && chain.customers.length > 0) {
      custEl.innerHTML = chain.customers.map(c => `
        <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 0.6rem 0.85rem; display: flex; justify-content: space-between; align-items: center;">
          <div>
            <strong style="color: #fff; cursor: pointer; text-decoration: underline;" onclick="selectCompany('${c.ticker}')">${c.name} (${c.ticker})</strong>
            <div style="font-size: 0.78rem; color: var(--text-muted);">${c.share}</div>
          </div>
          <button class="btn-secondary" onclick="selectCompany('${c.ticker}')" style="padding: 0.2rem 0.5rem; font-size: 0.72rem;">이동 →</button>
        </div>
      `).join('');
    } else {
      custEl.innerHTML = '<div style="color: var(--text-muted); font-size: 0.82rem;">하류 고객사 매핑 데이터 없음</div>';
    }
  }
}

function loadCurrentSubTabData() {
  const ticker = state.currentTicker;
  switch (state.currentSubTab) {
    case 'snapshot':
      loadSubTabSnapshot(ticker);
      break;
    case 'financials':
      loadSubTabFinancials(ticker);
      break;
    case 'filings':
      loadCompanyFilings();
      break;
    case 'news':
      loadSubTabNews(ticker);
      break;
    case 'analysts':
      loadSubTabAnalysts(ticker);
      break;
    case 'macro':
      loadSubTabMacro(ticker);
      break;
  }
}


// ─── SubTab 1: 📊 기업 요약 (Snapshot Charts) ───

async function loadSubTabSnapshot(ticker) {
  // 1. 90-Day Stock Price Trend Chart
  try {
    const res = await fetch(`/api/prices/${ticker}?days=90`).then(r => r.json());
    const data = res.data || [];
    const labels = data.map(d => d.date);
    const closes = data.map(d => d.close);

    destroyChart('stock90d');
    const ctx = document.getElementById('chart-company-stock-90d');
    if (ctx && labels.length > 0) {
      state.charts['stock90d'] = new Chart(ctx, {
        type: 'line',
        data: {
          labels,
          datasets: [{
            label: '종가 ($)',
            data: closes,
            borderColor: '#38bdf8',
            backgroundColor: 'rgba(56, 189, 248, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.2,
            pointRadius: 0,
            pointHoverRadius: 4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: ctx => ` 종가: $${Number(ctx.raw).toFixed(2)}`
              }
            }
          },
          scales: {
            x: {
              grid: { display: false },
              ticks: { maxTicksLimit: 6, color: '#94a3b8' }
            },
            y: {
              grid: { color: 'rgba(255, 255, 255, 0.05)' },
              ticks: { color: '#94a3b8' }
            }
          }
        }
      });
    }
  } catch (e) {
    console.warn('Failed to load 90d prices:', e);
  }

  // 2. Business Segments Pie Chart
  try {
    const res = await fetch(`/api/companies/${ticker}/full`).then(r => r.json());
    const segments = (res.value_chain && res.value_chain.segments) ? res.value_chain.segments : [
      { name: '주요 사업 부문', pct: 80, color: '#6366f1' },
      { name: '기타 부문', pct: 20, color: '#94a3b8' }
    ];

    destroyChart('segments');
    const ctxPie = document.getElementById('chart-company-segments');
    if (ctxPie) {
      state.charts['segments'] = new Chart(ctxPie, {
        type: 'doughnut',
        data: {
          labels: segments.map(s => s.name),
          datasets: [{
            data: segments.map(s => s.pct),
            backgroundColor: segments.map(s => s.color || '#6366f1'),
            borderColor: '#0f172a',
            borderWidth: 2
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
              labels: { color: '#cbd5e1', font: { size: 10 } }
            },
            tooltip: {
              callbacks: {
                label: ctx => ` ${ctx.label}: ${ctx.raw}%`
              }
            }
          }
        }
      });
    }
  } catch (e) {
    console.warn('Failed to load segments:', e);
  }
}


// ─── SubTab 2: 📈 분기 실적 (Financials Series) ───

async function loadSubTabFinancials(ticker) {
  try {
    const res = await fetch(`/api/companies/${ticker}/financials`).then(r => r.json());
    const quarters = res.quarters || [];

    // Render Table
    const tbody = document.getElementById('tbody-company-financials');
    if (tbody) {
      if (quarters.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:2rem;">등록된 분기 재무 데이터가 없습니다.</td></tr>';
      } else {
        // Table in reverse chronological order
        const revQuarters = [...quarters].reverse();
        tbody.innerHTML = revQuarters.map(q => {
          const revStr = q.revenue ? `$${Number(q.revenue).toLocaleString()}M` : '-';
          const opStr = q.op_income ? `$${Number(q.op_income).toLocaleString()}M` : '-';
          const netStr = q.net_income ? `$${Number(q.net_income).toLocaleString()}M` : '-';
          const capexStr = q.capex ? `$${Number(q.capex).toLocaleString()}M` : '-';
          const opmStr = q.op_margin_pct ? `${q.op_margin_pct}%` : '-';
          const epsStr = q.eps ? `$${Number(q.eps).toFixed(2)}` : '-';

          let yoyBadge = '-';
          if (q.revenue_yoy !== null && q.revenue_yoy !== undefined) {
            const isPos = q.revenue_yoy >= 0;
            yoyBadge = `<span style="color:${isPos ? '#34d399' : '#f87171'}; font-weight:600;">${isPos ? '+' : ''}${q.revenue_yoy}%</span>`;
          }

          return `
            <tr>
              <td><strong>${q.quarter}</strong></td>
              <td>${revStr}</td>
              <td>${yoyBadge}</td>
              <td>${opStr}</td>
              <td><span class="badge" style="background:rgba(6,182,212,0.12); color:#38bdf8;">${opmStr}</span></td>
              <td>${netStr}</td>
              <td>${capexStr}</td>
              <td>${epsStr}</td>
            </tr>
          `;
        }).join('');
      }
    }

    // Render Combo Chart (Revenue Bar, Op Income Bar, CapEx Line)
    destroyChart('financialsCombo');
    const ctx = document.getElementById('chart-company-financials-series');
    if (ctx && quarters.length > 0) {
      const labels = quarters.map(q => q.quarter);
      const revData = quarters.map(q => q.revenue || 0);
      const opData = quarters.map(q => q.op_income || 0);
      const capexData = quarters.map(q => q.capex || 0);

      state.charts['financialsCombo'] = new Chart(ctx, {
        type: 'bar',
        data: {
          labels,
          datasets: [
            {
              type: 'bar',
              label: '매출액 ($M)',
              data: revData,
              backgroundColor: 'rgba(99, 102, 241, 0.7)',
              borderColor: '#6366f1',
              borderWidth: 1,
              borderRadius: 4
            },
            {
              type: 'bar',
              label: '영업이익 ($M)',
              data: opData,
              backgroundColor: 'rgba(16, 185, 129, 0.7)',
              borderColor: '#10b981',
              borderWidth: 1,
              borderRadius: 4
            },
            {
              type: 'line',
              label: '설비투자 CapEx ($M)',
              data: capexData,
              borderColor: '#f59e0b',
              backgroundColor: '#f59e0b',
              borderWidth: 2.5,
              tension: 0.2,
              pointRadius: 3,
              fill: false
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: {
              labels: { color: '#cbd5e1', font: { family: 'Inter', size: 11 } }
            },
            tooltip: {
              backgroundColor: 'rgba(15, 23, 42, 0.95)',
              callbacks: {
                label: ctx => ` ${ctx.dataset.label}: $${Number(ctx.raw).toLocaleString()}M`
              }
            }
          },
          scales: {
            x: {
              grid: { display: false },
              ticks: { color: '#94a3b8', font: { size: 10 } }
            },
            y: {
              grid: { color: 'rgba(255, 255, 255, 0.05)' },
              ticks: { color: '#94a3b8' }
            }
          }
        }
      });
    }
  } catch (err) {
    console.error('Failed to load financials series:', err);
  }
}


// ─── SubTab 3: 📑 SEC 공시 원문 & FTS ───

async function loadCompanyFilings() {
  const ticker = state.currentTicker;
  const typeFilter = document.getElementById('filings-type-filter')?.value || '';
  const searchQ = document.getElementById('filings-search-input')?.value || '';

  const tbody = document.getElementById('tbody-company-filings');
  if (tbody) tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:2rem;">공시를 검색 중...</td></tr>';

  try {
    let url = `/api/companies/${ticker}/filings?`;
    if (typeFilter) url += `type=${encodeURIComponent(typeFilter)}&`;
    if (searchQ) url += `q=${encodeURIComponent(searchQ)}&`;

    const res = await fetch(url).then(r => r.json());
    const filings = res.filings || [];

    if (!tbody) return;
    if (filings.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:2rem;">검색된 공시 내역이 없습니다.</td></tr>';
      return;
    }

    tbody.innerHTML = filings.map(f => {
      const formBadge = f.filing_type === '10-K' ?
        '<span class="badge" style="background:rgba(239,68,68,0.2); color:#f87171;">10-K 연례</span>' :
        f.filing_type === '10-Q' ?
        '<span class="badge" style="background:rgba(59,130,246,0.2); color:#60a5fa;">10-Q 분기</span>' :
        '<span class="badge" style="background:rgba(168,85,247,0.2); color:#c084fc;">8-K 수시</span>';

      const snippetHtml = f.snippet ?
        `<div style="font-size:0.75rem; color:#cbd5e1; margin-top:0.3rem; background:rgba(255,255,255,0.03); padding:0.4rem; border-radius:4px;">...${f.snippet}...</div>` : '';

      return `
        <tr>
          <td>${formBadge}</td>
          <td>${f.fiscal_year ? `${f.fiscal_year}-${f.fiscal_quarter || 'FY'}` : '-'}</td>
          <td>${f.filed_date || '-'}</td>
          <td><span class="badge" style="background:rgba(16,185,129,0.15); color:#34d399;">${f.status}</span></td>
          <td style="font-family:'JetBrains Mono', monospace; font-size:0.78rem;">${f.accession_number || '-'}</td>
          <td>
            <button class="btn-secondary" onclick="viewFilingRawText(${f.id}, '${f.filing_type}', '${f.filed_date}')" style="padding:0.25rem 0.65rem; font-size:0.76rem;">
              원문 열람 ↗
            </button>
            ${snippetHtml}
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Failed to load company filings:', err);
  }
}

async function viewFilingRawText(filingId, filingType, filedDate) {
  const modal = document.getElementById('filing-viewer-modal');
  const title = document.getElementById('filing-modal-title');
  const body = document.getElementById('filing-modal-body');

  if (title) title.textContent = `${state.currentTicker} [${filingType}] (${filedDate}) 공시 원문`;
  if (body) body.textContent = '원문 텍스트를 불러오는 중...';
  if (modal) modal.classList.add('open');

  try {
    const res = await fetch(`/api/filings/${filingId}/text`).then(r => r.json());
    if (res.status === 'success' && res.text) {
      body.textContent = res.text;
    } else {
      body.textContent = '원문 텍스트가 아직 추출되지 않았거나 로컬에 존재하지 않습니다.';
    }
  } catch (e) {
    body.textContent = '원문을 불러오는 데 실패했습니다.';
  }
}

function closeFilingViewerModal() {
  const modal = document.getElementById('filing-viewer-modal');
  if (modal) modal.classList.remove('open');
}


// ─── SubTab 4: 📰 중요 뉴스 (News Feed) ───

async function loadSubTabNews(ticker) {
  const container = document.getElementById('container-company-news');
  if (!container) return;
  container.innerHTML = '<div style="text-align:center; padding:2rem; color:var(--text-muted);">뉴스를 불러오는 중...</div>';

  try {
    let url = `/api/companies/${ticker}/news?limit=40`;
    if (state.currentNewsFilter) url += `&source=${state.currentNewsFilter}`;

    const res = await fetch(url).then(r => r.json());
    state.newsCache = res.news || [];
    renderNewsItems(state.newsCache);
  } catch (err) {
    console.error('Failed to load news:', err);
    container.innerHTML = '<div style="text-align:center; padding:2rem; color:var(--text-muted);">뉴스 데이터를 가져올 수 없습니다.</div>';
  }
}

function renderNewsItems(items) {
  const container = document.getElementById('container-company-news');
  if (!container) return;

  if (items.length === 0) {
    container.innerHTML = '<div style="text-align:center; padding:2rem; color:var(--text-muted);">해당 조건의 뉴스가 없습니다.</div>';
    return;
  }

  container.innerHTML = items.map(n => {
    const dateStr = n.published || n.collected_at ? (n.published || n.collected_at.substring(0, 10)) : '-';
    return `
      <div class="news-card-item">
        <div class="news-meta-row">
          <div class="news-meta-left">
            <span class="news-source-tag">${n.source}</span>
            <span style="color:var(--text-muted);">${dateStr}</span>
          </div>
          <span class="news-score-badge">Score: ${n.score || 0}</span>
        </div>
        <a href="${n.url}" target="_blank" rel="noopener noreferrer" class="news-card-title">
          ${n.title}
        </a>
        ${n.snippet ? `<p class="news-card-snippet">${n.snippet}</p>` : ''}
      </div>
    `;
  }).join('');
}

function filterNewsSource(source) {
  state.currentNewsFilter = source;
  document.querySelectorAll('#pane-subtab-news .filter-btn').forEach(b => {
    b.classList.remove('active');
  });
  if (event && event.target) event.target.classList.add('active');
  loadSubTabNews(state.currentTicker);
}


// ─── SubTab 5: 🎯 애널리스트 리포트 & 목표주가 ───

async function loadSubTabAnalysts(ticker) {
  try {
    const res = await fetch(`/api/companies/${ticker}/analysts`).then(r => r.json());
    const reports = res.reports || [];
    const history = res.target_history || [];

    // 1. Report Count Label
    const countLbl = document.getElementById('reports-count-label');
    if (countLbl) countLbl.textContent = `${reports.length}건`;

    // 2. Reports Table
    const tbody = document.getElementById('tbody-company-analyst-reports');
    if (tbody) {
      if (reports.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:2rem;">등록된 증권사 리포트가 없습니다.</td></tr>';
      } else {
        tbody.innerHTML = reports.map(r => {
          const upsideBadge = r.upside_pct ?
            `<span class="${r.upside_pct >= 0 ? 'badge-upside-positive' : 'badge-upside-negative'}">${r.upside_pct >= 0 ? '+' : ''}${r.upside_pct}%</span>` : '-';

          const pdfBtn = r.pdf_url ?
            `<a href="${r.pdf_url}" target="_blank" rel="noopener noreferrer" class="btn-pdf-view">📄 원문 PDF ↗</a>` :
            `<span style="color:var(--text-muted); font-size:0.75rem;">-</span>`;

          return `
            <tr>
              <td>${r.report_date}</td>
              <td><strong>${r.broker_name}</strong></td>
              <td>${r.analyst_name || '-'}</td>
              <td><span title="${r.title}">${r.title}</span></td>
              <td><span class="badge" style="background:rgba(99,102,241,0.15); color:#a5b4fc;">${r.rating || 'BUY'}</span></td>
              <td><strong>${r.target_price ? `$${r.target_price}` : '-'}</strong></td>
              <td>${upsideBadge}</td>
              <td>${pdfBtn}</td>
            </tr>
          `;
        }).join('');
      }
    }

    // 3. Target Price Bands Line Chart
    destroyChart('targetHistory');
    const ctx = document.getElementById('chart-company-target-history');
    if (ctx && history.length > 0) {
      const labels = history.map(h => h.date);
      const closePrices = history.map(h => h.close_price);
      const targetMeans = history.map(h => h.target_mean);
      const targetHighs = history.map(h => h.target_high);
      const targetLows = history.map(h => h.target_low);

      state.charts['targetHistory'] = new Chart(ctx, {
        type: 'line',
        data: {
          labels,
          datasets: [
            {
              label: '종가 ($)',
              data: closePrices,
              borderColor: '#f87171',
              backgroundColor: 'rgba(248, 113, 113, 0.1)',
              borderWidth: 2.5,
              tension: 0.1,
              pointRadius: 2
            },
            {
              label: '목표가 평균 ($)',
              data: targetMeans,
              borderColor: '#38bdf8',
              backgroundColor: 'transparent',
              borderWidth: 2,
              borderDash: [5, 5],
              tension: 0.1,
              pointRadius: 2
            },
            {
              label: '목표가 최고 ($)',
              data: targetHighs,
              borderColor: 'rgba(52, 211, 153, 0.5)',
              backgroundColor: 'transparent',
              borderWidth: 1.5,
              tension: 0.1,
              pointRadius: 0
            },
            {
              label: '목표가 최저 ($)',
              data: targetLows,
              borderColor: 'rgba(148, 163, 184, 0.5)',
              backgroundColor: 'transparent',
              borderWidth: 1.5,
              tension: 0.1,
              pointRadius: 0
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: { labels: { color: '#cbd5e1', font: { size: 11 } } },
            tooltip: {
              callbacks: {
                label: ctx => ` ${ctx.dataset.label}: $${Number(ctx.raw).toFixed(2)}`
              }
            }
          },
          scales: {
            x: {
              grid: { display: false },
              ticks: { maxTicksLimit: 8, color: '#94a3b8' }
            },
            y: {
              grid: { color: 'rgba(255, 255, 255, 0.05)' },
              ticks: { color: '#94a3b8' }
            }
          }
        }
      });
    }
  } catch (err) {
    console.error('Failed to load analyst reports & target history:', err);
  }
}


// ─── SubTab 6: 🔗 밸류체인 & 거시 연계 ───

async function loadSubTabMacro(ticker) {
  try {
    const res = await fetch(`/api/companies/${ticker}/macro-links`).then(r => r.json());
    const contracts = res.contracts || [];
    const fabs = res.fabs || [];
    const dcs = res.datacenters || [];

    // 1. Contracts List
    const cCont = document.getElementById('container-company-contracts');
    if (cCont) {
      if (contracts.length === 0) {
        cCont.innerHTML = '<div style="color:var(--text-muted); padding:1rem; font-size:0.85rem;">체결된 메가 계약 내역이 없습니다.</div>';
      } else {
        cCont.innerHTML = contracts.map(c => `
          <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border-subtle); border-radius:8px; padding:0.85rem 1rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.35rem;">
              <span class="badge" style="background:rgba(99,102,241,0.15); color:#a5b4fc; font-weight:700;">${c.contract_type}</span>
              <strong style="color:#34d399; font-size:1.05rem;">${c.value_b ? `$${c.value_b}B` : '비공개'}</strong>
            </div>
            <div style="font-weight:600; color:#fff; font-size:0.92rem; margin-bottom:0.25rem;">
              ${c.buyer_id} ➔ ${c.seller_id}
            </div>
            <p style="font-size:0.8rem; color:var(--text-secondary); line-height:1.4;">${c.description || ''}</p>
          </div>
        `).join('');
      }
    }

    // 2. Capacities (Fabs or Datacenters)
    const capCont = document.getElementById('container-company-capacities');
    if (capCont) {
      let capHtml = '';
      if (fabs.length > 0) {
        capHtml += `
          <div style="margin-bottom:0.75rem;">
            <h5 style="font-size:0.82rem; color:var(--accent-cyan); margin-bottom:0.4rem;">🏭 첨단 파운드리/패키징 팹</h5>
            ${fabs.map(f => `
              <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border-subtle); border-radius:6px; padding:0.6rem 0.85rem; margin-bottom:0.4rem;">
                <div style="display:flex; justify-content:space-between;">
                  <strong style="color:#fff;">${f.fab_name} (${f.process_node || '첨단'})</strong>
                  <span style="color:#38bdf8; font-weight:600;">${f.wspm_target ? `${f.wspm_target}k/월` : ''}</span>
                </div>
                <div style="font-size:0.75rem; color:var(--text-muted);">${f.location_city || ''}, ${f.location_country || ''} · ${f.key_notes || ''}</div>
              </div>
            `).join('')}
          </div>
        `;
      }

      if (dcs.length > 0) {
        capHtml += `
          <div>
            <h5 style="font-size:0.82rem; color:#a855f7; margin-bottom:0.4rem;">⚡ 데이터센터 전력 클러스터</h5>
            ${dcs.map(d => `
              <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border-subtle); border-radius:6px; padding:0.6rem 0.85rem; margin-bottom:0.4rem;">
                <div style="display:flex; justify-content:space-between;">
                  <strong style="color:#fff;">${d.dc_name}</strong>
                  <span style="color:#a855f7; font-weight:600;">${d.power_mw_target ? `${d.power_mw_target} MW` : ''}</span>
                </div>
                <div style="font-size:0.75rem; color:var(--text-muted);">${d.cooling_type || '수랭식'} · 주력: ${d.primary_chips || 'Blackwell'} · ${d.key_notes || ''}</div>
              </div>
            `).join('')}
          </div>
        `;
      }

      if (!capHtml) {
        capHtml = '<div style="color:var(--text-muted); padding:1rem; font-size:0.85rem;">관련 팹/데이터센터 데이터 없음</div>';
      }
      capCont.innerHTML = capHtml;
    }
  } catch (err) {
    console.error('Failed to load company macro links:', err);
  }
}


// ─── Mode 2: 🌐 Macro Hub (Memory Claude Engine) ───

async function loadMacroHub() {
  await Promise.all([
    renderSankeyChart(),
    renderMacroHbmBalance(),
    renderMacroContracts(),
    renderMacroCapacities()
  ]);
}

async function renderSankeyChart() {
  const container = document.getElementById('macro_sankey_chart');
  if (!container) return;

  try {
    const res = await fetch('/api/macro/sankey').then(r => r.json());
    state.sankeyData = res;

    // Check Google Charts Loader
    if (!window.google || !window.google.visualization || !window.google.visualization.DataTable) {
      container.innerHTML = '<div style="text-align:center; padding:5rem; color:var(--text-muted);">Google Charts 라이브러리를 로드하는 중...</div>';
      setTimeout(renderSankeyChart, 500);
      return;
    }

    const data = new google.visualization.DataTable();
    data.addColumn('string', 'From');
    data.addColumn('string', 'To');
    data.addColumn('number', 'Weight ($B)');

    const rows = (res.flows || []).map(f => [f[0], f[1], f[2]]);
    data.addRows(rows);

    const colors = [
      '#4285f4', '#ff9900', '#00a4ef', '#0866ff', '#76b900',
      '#ed1c24', '#cc0033', '#e05e2b', '#ff6600', '#00bcd4',
      '#1428a0', '#009bdf', '#c97839', '#10a37f', '#f59e0b',
      '#10b981', '#8b5cf6', '#d97706'
    ];

    const options = {
      height: 520,
      backgroundColor: 'transparent',
      sankey: {
        node: {
          colors: colors,
          label: {
            fontName: 'Inter',
            fontSize: 12,
            color: '#f8fafc',
            bold: true
          },
          nodePadding: 24,
          width: 14
        },
        link: {
          colorMode: 'gradient',
          colors: colors
        }
      }
    };

    const chart = new google.visualization.Sankey(container);
    chart.draw(data, options);

    // Node Drill-down interaction
    google.visualization.events.addListener(chart, 'select', () => {
      const selectedItem = chart.getSelection()[0];
      if (selectedItem) {
        let nodeName = null;
        if (selectedItem.name) {
          nodeName = selectedItem.name;
        } else if (selectedItem.row !== undefined) {
          nodeName = rows[selectedItem.row][0];
        }

        if (nodeName && res.drilldown_map && res.drilldown_map[nodeName]) {
          const targetTicker = res.drilldown_map[nodeName];
          selectCompany(targetTicker);
        }
      }
    });

    // Update Simulation Panel with sensitivities
    updateMacroSimulation();
  } catch (err) {
    console.error('Failed to render Sankey chart:', err);
  }
}

function applyMacroPreset(presetName) {
  const presets = {
    ai_supercycle: { capex: 45, hbm: 80, asp: 15, yield: 10 },
    hbm_shortage:  { capex: 15, hbm: -30, asp: 25, yield: -15 },
    capex_peak:    { capex: -25, hbm: -20, asp: -10, yield: 0 },
    regulation:    { capex: -15, hbm: -10, asp: -5, yield: 0 }
  };

  const p = presets[presetName];
  if (!p) return;

  document.getElementById('s-capex').value = p.capex;
  document.getElementById('s-hbm').value = p.hbm;
  document.getElementById('s-asp').value = p.asp;
  document.getElementById('s-yield').value = p.yield;

  updateMacroSimulation();
}

function updateMacroSimulation() {
  const capex = +(document.getElementById('s-capex')?.value || 35) / 100;
  const hbm = +(document.getElementById('s-hbm')?.value || 30) / 100;
  const asp = +(document.getElementById('s-asp')?.value || 0) / 100;
  const yld = +(document.getElementById('s-yield')?.value || 0) / 100;

  const lblCapex = document.getElementById('v-capex');
  const lblHbm = document.getElementById('v-hbm');
  const lblAsp = document.getElementById('v-asp');
  const lblYield = document.getElementById('v-yield');

  if (lblCapex) lblCapex.textContent = `${capex >= 0 ? '+' : ''}${(capex * 100).toFixed(0)}%`;
  if (lblHbm) lblHbm.textContent = `${hbm >= 0 ? '+' : ''}${(hbm * 100).toFixed(0)}%`;
  if (lblAsp) lblAsp.textContent = `${asp >= 0 ? '+' : ''}${(asp * 100).toFixed(0)}%`;
  if (lblYield) lblYield.textContent = `${yld >= 0 ? '+' : ''}${(yld * 100).toFixed(0)}%p`;

  const companies = (state.sankeyData && state.sankeyData.companies) ? state.sankeyData.companies : [];
  if (companies.length === 0) return;

  const impacts = companies.map(c => {
    const delta =
      c.sens.capex * capex +
      c.sens.hbm * hbm +
      c.sens.asp * asp +
      c.sens.yield * yld;
    const pct = Math.round(delta * 100 * 10) / 10;
    return { ...c, pct };
  }).sort((a, b) => b.pct - a.pct);

  const avg = (impacts.reduce((s, c) => s + c.pct, 0) / impacts.length).toFixed(1);
  const badge = document.getElementById('macro-sim-overall-badge');
  if (badge) {
    badge.textContent = `전체 ${avg >= 0 ? '+' : ''}${avg}%`;
    badge.style.color = avg >= 0 ? '#34d399' : '#f87171';
  }

  const listContainer = document.getElementById('macro-sim-impact-list');
  if (listContainer) {
    listContainer.innerHTML = impacts.map(c => {
      const isPos = c.pct >= 0;
      return `
        <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.78rem; padding:0.25rem 0.5rem; background:rgba(255,255,255,0.02); border-radius:4px; cursor:pointer;" onclick="selectCompany('${c.ticker}')">
          <div style="display:flex; align-items:center; gap:0.4rem;">
            <strong style="color:#fff;">${c.name}</strong>
            <span style="font-size:0.7rem; color:var(--text-muted);">${c.layer}</span>
          </div>
          <span style="font-family:'JetBrains Mono',monospace; font-weight:700; color:${isPos ? '#34d399' : '#f87171'};">
            ${isPos ? '+' : ''}${c.pct}%
          </span>
        </div>
      `;
    }).join('');
  }
}

async function renderMacroHbmBalance() {
  try {
    const res = await fetch('/api/macro/hbm-balance').then(r => r.json());
    const timeline = res.timeline || [];
    const share = res.market_share || [];

    // Timeline Line Chart
    destroyChart('macroHbmTimeline');
    const ctx = document.getElementById('chart-macro-hbm-balance');
    if (ctx && timeline.length > 0) {
      state.charts['macroHbmTimeline'] = new Chart(ctx, {
        type: 'line',
        data: {
          labels: timeline.map(t => t.period),
          datasets: [
            {
              label: 'HBM 비트 수요량 (Demand)',
              data: timeline.map(t => t.demand_bit),
              borderColor: '#f43f5e',
              backgroundColor: 'rgba(244, 63, 94, 0.1)',
              borderWidth: 2.5,
              tension: 0.25,
              fill: false
            },
            {
              label: 'HBM 공급 캐파 (Supply)',
              data: timeline.map(t => t.supply_bit),
              borderColor: '#38bdf8',
              backgroundColor: 'rgba(56, 189, 248, 0.1)',
              borderWidth: 2.5,
              tension: 0.25,
              fill: false
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: { labels: { color: '#cbd5e1' } },
            tooltip: {
              callbacks: {
                label: ctx => ` ${ctx.dataset.label}: ${ctx.raw}M Bits`
              }
            }
          },
          scales: {
            x: { grid: { display: false }, ticks: { color: '#94a3b8' } },
            y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } }
          }
        }
      });
    }

    // Market Share Donut Chart
    destroyChart('macroHbmShare');
    const ctxDonut = document.getElementById('chart-macro-hbm-share');
    if (ctxDonut && share.length > 0) {
      state.charts['macroHbmShare'] = new Chart(ctxDonut, {
        type: 'doughnut',
        data: {
          labels: share.map(s => s.name),
          datasets: [{
            data: share.map(s => s.share_pct),
            backgroundColor: share.map(s => s.color),
            borderColor: '#0f172a',
            borderWidth: 2
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false }
          }
        }
      });
    }
  } catch (err) {
    console.error('Failed to render HBM balance:', err);
  }
}

async function renderMacroContracts() {
  const tbody = document.getElementById('tbody-macro-contracts');
  if (!tbody) return;

  try {
    const res = await fetch('/api/macro/contracts').then(r => r.json());
    const contracts = res.contracts || [];

    tbody.innerHTML = contracts.map(c => `
      <tr>
        <td style="font-family:'JetBrains Mono', monospace; font-size:0.75rem; color:var(--text-muted);">${c.contract_id}</td>
        <td><strong>${c.buyer_id}</strong></td>
        <td><strong>${c.seller_id}</strong></td>
        <td><span class="badge" style="background:rgba(99,102,241,0.15); color:#a5b4fc;">${c.contract_type}</span></td>
        <td style="font-weight:700; color:#34d399;">${c.value_b ? `$${c.value_b}B` : '비공개'}</td>
        <td><span class="badge" style="background:rgba(6,182,212,0.15); color:var(--accent-cyan);">${c.product_type || 'AI'}</span></td>
        <td>${c.announced_date || '-'}</td>
        <td style="max-width:320px; font-size:0.8rem; color:var(--text-secondary);">${c.description || ''}</td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Failed to load macro contracts:', err);
  }
}

async function renderMacroCapacities() {
  try {
    const res = await fetch('/api/macro/capacity').then(r => r.json());
    const fabs = res.fabs || [];
    const dcs = res.datacenters || [];

    const tbodyFabs = document.getElementById('tbody-macro-fabs');
    if (tbodyFabs) {
      tbodyFabs.innerHTML = fabs.map(f => `
        <tr>
          <td><strong>${f.fab_name}</strong></td>
          <td>${f.location_country || '-'}</td>
          <td><span class="badge" style="background:rgba(16,185,129,0.15); color:#34d399;">${f.process_node || '첨단'}</span></td>
          <td style="font-weight:700;">${f.wspm_target ? `${f.wspm_target}k` : '-'}</td>
          <td style="font-size:0.75rem; color:var(--text-muted);">${f.key_customers || '-'}</td>
        </tr>
      `).join('');
    }

    const tbodyDcs = document.getElementById('tbody-macro-dcs');
    if (tbodyDcs) {
      tbodyDcs.innerHTML = dcs.map(d => `
        <tr>
          <td><strong>${d.dc_name}</strong></td>
          <td>${d.location_state || ''}, ${d.location_country || ''}</td>
          <td style="font-weight:700; color:#c084fc;">${d.power_mw_target ? `${d.power_mw_target} MW` : '-'}</td>
          <td><span class="badge" style="background:rgba(99,102,241,0.15); color:#a5b4fc;">${d.cooling_type || '수랭식'}</span></td>
          <td>${d.online_date || '-'}</td>
        </tr>
      `).join('');
    }
  } catch (err) {
    console.error('Failed to render macro capacities:', err);
  }
}


// ─── Mode 3, 4, 5: Legacy Views (Indicators, Calendar, Filings Archive) ───

async function loadIndicators() {
  await fetchKrExportData();
  await fetchMemorySpotData();
}

async function fetchKrExportData() {
  try {
    const res = await fetch('/api/indicators/kr-export').then(r => r.json());
    const data = res.data || [];

    const tbody = document.getElementById('tbody-kr-export-legacy');
    if (tbody && data.length > 0) {
      tbody.innerHTML = data.slice(0, 15).map(d => `
        <tr>
          <td>${d.date}</td>
          <td>${d.hs_code || '-'}</td>
          <td><strong>${d.item_name || '반도체'}</strong></td>
          <td style="font-weight:700;">$${Number(d.value).toLocaleString()}M</td>
          <td><span style="color:${(d.yoy_growth || 0) >= 0 ? '#34d399' : '#f87171'}; font-weight:600;">${d.yoy_growth ? `${d.yoy_growth >= 0 ? '+' : ''}${d.yoy_growth}%` : '-'}</span></td>
        </tr>
      `).join('');
    }

    // Chart
    destroyChart('krExport');
    const ctx = document.getElementById('chart-kr-export-legacy');
    if (ctx && data.length > 0) {
      const dates = [...new Set(data.map(d => d.date))].sort();
      const values = dates.map(dt => {
        const item = data.find(d => d.date === dt);
        return item ? item.value : 0;
      });

      state.charts['krExport'] = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: dates,
          datasets: [{
            label: '10일 주기 반도체 수출액 ($M)',
            data: values,
            backgroundColor: 'rgba(6, 182, 212, 0.65)',
            borderColor: '#06b6d4',
            borderRadius: 4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { labels: { color: '#cbd5e1' } } },
          scales: {
            x: { grid: { display: false }, ticks: { color: '#94a3b8' } },
            y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } }
          }
        }
      });
    }
  } catch (err) {
    console.error('Failed to load KR export:', err);
  }
}

async function fetchMemorySpotData() {
  try {
    const res = await fetch('/api/indicators/memory-spot').then(r => r.json());
    const data = res.data || [];

    destroyChart('memorySpot');
    const ctx = document.getElementById('chart-memory-spot-legacy');
    if (ctx && data.length > 0) {
      const dates = [...new Set(data.map(d => d.date))].sort();
      const ddr5 = dates.map(dt => {
        const item = data.find(d => d.date === dt && d.indicator_type.includes('DDR5'));
        return item ? item.value : null;
      });

      state.charts['memorySpot'] = new Chart(ctx, {
        type: 'line',
        data: {
          labels: dates,
          datasets: [{
            label: 'DRAM DDR5 16Gb Spot ($)',
            data: ddr5,
            borderColor: '#f59e0b',
            borderWidth: 2,
            tension: 0.2,
            spanGaps: true
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { labels: { color: '#cbd5e1' } } },
          scales: {
            x: { grid: { display: false }, ticks: { color: '#94a3b8' } },
            y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } }
          }
        }
      });
    }
  } catch (err) {
    console.error('Failed to load memory spot data:', err);
  }
}

async function loadCalendar() {
  try {
    const res = await fetch('/api/calendar').then(r => r.json());
    const data = res.data || [];

    const tbody = document.getElementById('tbody-calendar-full');
    if (!tbody) return;

    if (data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:3rem;">캘린더 데이터가 없습니다.</td></tr>';
      return;
    }

    const today = new Date();
    tbody.innerHTML = data.map(item => {
      let ddayBadge = '-';
      try {
        const exp = new Date(item.expected_date.substring(0, 10));
        const diff = Math.ceil((exp - today) / (1000 * 60 * 60 * 24));
        if (diff === 0) ddayBadge = '<span class="company-dday-badge imminent">🔥 D-Day</span>';
        else if (diff > 0 && diff <= 7) ddayBadge = `<span class="company-dday-badge imminent">⚡ D-${diff}</span>`;
        else if (diff > 0) ddayBadge = `<span class="company-dday-badge near">D-${diff}</span>`;
        else ddayBadge = `<span class="company-dday-badge">D+${Math.abs(diff)}</span>`;
      } catch (e) {}

      return `
        <tr>
          <td>${ddayBadge}</td>
          <td><strong>${item.expected_date}</strong></td>
          <td><strong>${item.ticker}</strong></td>
          <td>${item.name_ko}</td>
          <td><span class="badge" style="background:rgba(99,102,241,0.15); color:#a5b4fc;">${item.layer_name_ko || ''}</span></td>
          <td>${item.fiscal_year}-${item.fiscal_quarter}</td>
          <td>${item.call_time_et || 'TBD'}</td>
          <td>
            <button class="btn-primary" onclick="selectCompany('${item.ticker}')" style="padding:0.25rem 0.65rem; font-size:0.75rem;">
              기업 허브 ↗
            </button>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Failed to load calendar:', err);
  }
}

async function loadFilingsArchive() {
  try {
    const res = await fetch('/api/filings?limit=50').then(r => r.json());
    const filings = res.filings || [];

    const tbody = document.getElementById('tbody-all-filings');
    if (!tbody) return;

    if (filings.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:3rem;">공시 데이터가 없습니다.</td></tr>';
      return;
    }

    tbody.innerHTML = filings.map(f => `
      <tr>
        <td><strong>${f.ticker}</strong></td>
        <td>${f.name_ko || ''}</td>
        <td><span class="badge" style="background:rgba(59,130,246,0.15); color:#60a5fa;">${f.filing_type}</span></td>
        <td>${f.fiscal_year ? `${f.fiscal_year}-${f.fiscal_quarter}` : '-'}</td>
        <td>${f.filed_date}</td>
        <td style="font-family:'JetBrains Mono',monospace; font-size:0.75rem;">${f.accession_number || '-'}</td>
        <td><span class="badge" style="background:rgba(16,185,129,0.15); color:#34d399;">${f.status}</span></td>
        <td>
          <button class="btn-secondary" onclick="viewFilingRawText(${f.id}, '${f.filing_type}', '${f.filed_date}')" style="padding:0.25rem 0.65rem; font-size:0.75rem;">
            열람 ↗
          </button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Failed to load filings archive:', err);
  }
}


// ─── Global Keyboard Shortcuts & Cmd + K Modal ───

function setupKeyboardShortcuts() {
  document.addEventListener('keydown', e => {
    // Cmd + K or Ctrl + K or '/'
    if ((e.metaKey && e.key === 'k') || (e.ctrlKey && e.key === 'k') || (e.key === '/' && document.activeElement.tagName !== 'INPUT')) {
      e.preventDefault();
      openCmdKModal();
    }

    // Esc closes modal
    if (e.key === 'Escape') {
      closeCmdKModal();
      closeFilingViewerModal();
    }

    // '[' and ']' switches to prev/next company
    if ((e.key === '[' || e.key === ']') && document.activeElement.tagName !== 'INPUT') {
      const idx = state.entities.findIndex(x => x.ticker === state.currentTicker);
      if (idx !== -1) {
        if (e.key === '[' && idx > 0) {
          selectCompany(state.entities[idx - 1].ticker);
        } else if (e.key === ']' && idx < state.entities.length - 1) {
          selectCompany(state.entities[idx + 1].ticker);
        }
      }
    }
  });
}

function openCmdKModal() {
  const modal = document.getElementById('cmd-k-modal');
  const input = document.getElementById('cmd-k-input');
  if (modal) modal.classList.add('open');
  if (input) {
    input.value = '';
    input.focus();
    handleCmdKSearch('');
  }
}

function closeCmdKModal() {
  const modal = document.getElementById('cmd-k-modal');
  if (modal) modal.classList.remove('open');
}

function handleCmdKSearch(val) {
  const q = val.trim().toLowerCase();
  const resultsEl = document.getElementById('cmd-k-results');
  if (!resultsEl) return;

  const filtered = state.entities.filter(e =>
    !q ||
    e.ticker.toLowerCase().includes(q) ||
    e.name_ko.toLowerCase().includes(q) ||
    e.name_en.toLowerCase().includes(q)
  ).slice(0, 10);

  if (filtered.length === 0) {
    resultsEl.innerHTML = '<div style="padding:1rem; text-align:center; color:var(--text-muted);">검색 결과가 없습니다.</div>';
    return;
  }

  resultsEl.innerHTML = filtered.map((c, i) => `
    <div class="cmd-k-item ${i === 0 ? 'selected' : ''}" onclick="selectCompanyFromCmdK('${c.ticker}')">
      <div style="display:flex; align-items:center; gap:0.6rem;">
        <span>${COUNTRY_FLAGS[c.country] || '🌐'}</span>
        <strong style="color:#fff; font-family:'JetBrains Mono',monospace;">${c.ticker}</strong>
        <span style="color:var(--text-primary); font-size:0.88rem;">${c.name_ko}</span>
        <span style="font-size:0.75rem; color:var(--text-muted);">${c.name_en}</span>
      </div>
      <span class="badge" style="background:rgba(99,102,241,0.15); color:#a5b4fc; font-size:0.72rem;">${c.layer_code}</span>
    </div>
  `).join('');
}

function selectCompanyFromCmdK(ticker) {
  closeCmdKModal();
  selectCompany(ticker);
}

function handleCmdKKeyDown(e) {
  if (e.key === 'Enter') {
    const selected = document.querySelector('.cmd-k-item.selected');
    if (selected) selected.click();
  }
}
