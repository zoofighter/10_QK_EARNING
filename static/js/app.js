/**
 * QK_EARNING Application Logic
 */

let allEntities = [];
let allFilings = [];
let activeLayer = "ALL";
let priceChart = null;

// Initialization
document.addEventListener("DOMContentLoaded", () => {
  loadOverview();
  loadEntities();
  loadFilingsTable();
  loadCalendarTable();
});

// Tab Switching
function switchTab(tabId) {
  document.querySelectorAll(".tab-content").forEach(tab => tab.classList.remove("active"));
  document.querySelectorAll(".nav-tab-btn").forEach(btn => btn.classList.remove("active"));

  const targetTab = document.getElementById(tabId);
  const targetBtn = document.getElementById(`btn-${tabId}`);
  if (targetTab) targetTab.classList.add("active");
  if (targetBtn) targetBtn.classList.add("active");

  if (tabId === "tab-overview") loadOverview();
  if (tabId === "tab-companies") loadEntities();
  if (tabId === "tab-filings") loadFilingsTable();
  if (tabId === "tab-calendar") loadCalendarTable();
  if (tabId === "tab-indicators") loadKrExportData();
}

// 1. Overview Loader
async function loadOverview() {
  try {
    const res = await fetch("/api/stats");
    const json = await res.json();
    if (json.status !== "success") return;

    const data = json.data;
    document.getElementById("kpi-companies").textContent = data.company_count;
    document.getElementById("kpi-filings").textContent = data.filing_count;
    document.getElementById("kpi-prices").textContent = data.price_tracked_count;

    if (data.upcoming_earnings && data.upcoming_earnings.length > 0) {
      const next = data.upcoming_earnings[0];
      document.getElementById("kpi-next-earnings").textContent = next.d_day || "D-Day";
      document.getElementById("kpi-next-company").textContent = `${next.ticker} (${next.fiscal_year}-${next.fiscal_quarter})`;
    }

    // Render upcoming table in overview
    const calBody = document.getElementById("overview-calendar-tbody");
    if (data.upcoming_earnings && data.upcoming_earnings.length > 0) {
      calBody.innerHTML = data.upcoming_earnings.map(item => `
        <tr>
          <td><span class="status-pill" style="font-weight:700;">${item.d_day}</span></td>
          <td><strong>${item.ticker}</strong> <span style="font-size:0.75rem; color:var(--text-muted);">${item.name_ko}</span></td>
          <td><span class="layer-tag ${getLayerShort(item.layer_code)}">${getLayerShort(item.layer_code)}</span></td>
          <td>${item.fiscal_year}-${item.fiscal_quarter}</td>
          <td>${item.expected_date}</td>
          <td>${item.call_time_et || '미정'}</td>
          <td><span style="font-size:0.75rem; color:var(--accent-cyan);">${item.status || 'UPCOMING'}</span></td>
        </tr>
      `).join("");
    } else {
      calBody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--text-muted);">예정된 실적 발표 일정이 없습니다.</td></tr>`;
    }

    // Render layers list in overview
    const layersList = document.getElementById("overview-layers-list");
    layersList.innerHTML = data.layers.map(layer => {
      const short = getLayerShort(layer.code);
      return `
        <div style="display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.02); padding:0.6rem 0.85rem; border-radius:var(--radius-sm); border:1px solid var(--border-subtle);">
          <div style="display:flex; align-items:center; gap:0.6rem;">
            <span class="layer-tag ${short}">${short}</span>
            <span style="font-size:0.85rem; font-weight:500;">${layer.name_ko}</span>
          </div>
          <span style="font-size:0.85rem; font-weight:700; color:var(--text-secondary);">${layer.entity_count}개사</span>
        </div>
      `;
    }).join("");

    // Load recent filings in overview
    loadRecentFilingsOverview();

  } catch (err) {
    console.error("Failed to load overview stats:", err);
  }
}

async function loadRecentFilingsOverview() {
  try {
    const res = await fetch("/api/filings?limit=5");
    const json = await res.json();
    const tbody = document.getElementById("overview-filings-tbody");
    if (json.data && json.data.length > 0) {
      tbody.innerHTML = json.data.map(f => `
        <tr>
          <td><strong>${f.ticker}</strong></td>
          <td>${f.name_ko}</td>
          <td><span class="filing-badge filing-${f.filing_type}">${f.filing_type}</span></td>
          <td>${f.fiscal_year || '-'} ${f.fiscal_quarter || ''}</td>
          <td>${f.filed_date}</td>
          <td style="font-family:'JetBrains Mono',monospace; font-size:0.75rem;">${f.accession_number || '-'}</td>
          <td><span class="status-pill" style="font-size:0.75rem;">${f.status}</span></td>
          <td><button class="btn" style="padding:0.25rem 0.6rem; font-size:0.75rem;" onclick="openFilingModal(${f.id})">상세</button></td>
        </tr>
      `).join("");
    }
  } catch (e) {
    console.error(e);
  }
}

// 2. Companies Loader & Filter
async function loadEntities() {
  try {
    const res = await fetch("/api/entities");
    const json = await res.json();
    if (json.status !== "success") return;
    allEntities = json.data;
    renderCompanies();
  } catch (err) {
    console.error("Failed to load entities:", err);
  }
}

function filterByLayer(layerCode) {
  activeLayer = layerCode;
  document.querySelectorAll(".layer-pill").forEach(btn => {
    btn.classList.toggle("active", btn.textContent.includes(getLayerShort(layerCode)) || (layerCode === "ALL" && btn.textContent.includes("전체")));
  });
  renderCompanies();
}

function renderCompanies() {
  const grid = document.getElementById("companies-grid");
  const filtered = activeLayer === "ALL" 
    ? allEntities 
    : allEntities.filter(e => e.layer_code === activeLayer);

  if (filtered.length === 0) {
    grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:3rem; color:var(--text-muted);">등록된 기업이 없습니다.</div>`;
    return;
  }

  grid.innerHTML = filtered.map(e => {
    const layerShort = getLayerShort(e.layer_code);
    const priceDisplay = e.latest_close ? `$${Number(e.latest_close).toFixed(2)}` : "미수집";
    return `
      <div class="company-card" onclick="openCompanyModal('${e.ticker}')">
        <div>
          <div class="card-top">
            <span class="ticker-badge">${e.ticker}</span>
            <span class="layer-tag ${layerShort}">${layerShort}</span>
          </div>
          <div class="company-names">
            <div class="company-name-en">${e.name_en}</div>
            <div class="company-name-ko">${e.name_ko} · ${e.exchange || '비상장'} (${e.country})</div>
          </div>
        </div>
        <div class="card-metrics">
          <div class="metric-item">
            <span class="metric-label">최근 종가</span>
            <span class="metric-value" style="color:${e.latest_close ? 'var(--accent-emerald)' : 'var(--text-muted)'};">${priceDisplay}</span>
          </div>
          <div class="metric-item" style="text-align:right;">
            <span class="metric-label">Filing 수집</span>
            <span class="metric-value">${e.filing_count}건</span>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

// 3. Filings Loader
async function loadFilingsTable() {
  const typeFilter = document.getElementById("filing-filter-type") ? document.getElementById("filing-filter-type").value : "";
  const url = typeFilter ? `/api/filings?type=${typeFilter}` : "/api/filings";
  try {
    const res = await fetch(url);
    const json = await res.json();
    allFilings = json.data || [];
    const tbody = document.getElementById("filings-tbody");
    if (!tbody) return;

    if (allFilings.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; color:var(--text-muted); padding:2rem;">수집된 공시 데이터가 없습니다. '수집 콘솔' 탭에서 데이터를 수집하세요.</td></tr>`;
      return;
    }

    tbody.innerHTML = allFilings.map(f => `
      <tr>
        <td><strong>${f.ticker}</strong></td>
        <td>${f.name_ko}</td>
        <td><span class="filing-badge filing-${f.filing_type}">${f.filing_type}</span></td>
        <td>${f.fiscal_year || '-'}</td>
        <td>${f.fiscal_quarter || '-'}</td>
        <td>${f.period_end_date || '-'}</td>
        <td>${f.filed_date}</td>
        <td><span class="status-pill" style="font-size:0.75rem;">${f.status}</span></td>
        <td><button class="btn" style="padding:0.25rem 0.6rem; font-size:0.75rem;" onclick="openFilingModal(${f.id})">원문 열람</button></td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Failed to load filings:", err);
  }
}

// 4. Calendar Loader
async function loadCalendarTable() {
  try {
    const res = await fetch("/api/calendar");
    const json = await res.json();
    const tbody = document.getElementById("calendar-tbody");
    if (!tbody) return;

    const data = json.data || [];
    if (data.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:var(--text-muted); padding:2rem;">등록된 일정이 없습니다.</td></tr>`;
      return;
    }

    tbody.innerHTML = data.map(item => `
      <tr>
        <td><span class="status-pill" style="font-weight:700;">${item.d_day}</span></td>
        <td><strong>${item.ticker}</strong></td>
        <td>${item.name_ko}</td>
        <td><span class="layer-tag ${getLayerShort(item.layer_code)}">${getLayerShort(item.layer_code)}</span></td>
        <td>${item.fiscal_year}-${item.fiscal_quarter}</td>
        <td>${item.expected_date}</td>
        <td>${item.call_time_et ? `${item.call_time_et} ET` : '시간 미정'}</td>
        <td><span style="font-size:0.78rem; color:var(--accent-cyan); font-weight:600;">${item.status}</span></td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Failed to load calendar:", err);
  }
}

// 5. Modals (Company Detail & Price Chart)
async function openCompanyModal(ticker) {
  try {
    const res = await fetch(`/api/entities/${ticker}`);
    const json = await res.json();
    if (json.status !== "success") return;

    const data = json.data;
    const ent = data.entity;

    document.getElementById("modal-company-ticker").textContent = ent.ticker;
    document.getElementById("modal-company-name-en").textContent = ent.name_en;
    document.getElementById("modal-company-name-ko").textContent = `(${ent.name_ko})`;

    const short = getLayerShort(ent.layer_code);
    document.getElementById("modal-company-badges").innerHTML = `
      <span class="layer-tag ${short}">${ent.layer_name_ko} (${short})</span>
      <span class="status-pill">${ent.exchange || '비상장'} · ${ent.country}</span>
      <span class="status-pill">CIK: ${ent.sec_cik || 'N/A'}</span>
      <span class="status-pill">회계연도 말: ${ent.fiscal_year_end || '12'}월</span>
    `;

    // Render Filings in modal
    const filingTbody = document.getElementById("modal-company-filings");
    if (data.filings && data.filings.length > 0) {
      filingTbody.innerHTML = data.filings.map(f => `
        <tr>
          <td><span class="filing-badge filing-${f.filing_type}">${f.filing_type}</span></td>
          <td>${f.fiscal_year}-${f.fiscal_quarter}</td>
          <td>${f.filed_date}</td>
          <td style="font-family:'JetBrains Mono',monospace; font-size:0.75rem;">${f.accession_number || '-'}</td>
          <td><span class="status-pill" style="font-size:0.72rem;">${f.status}</span></td>
        </tr>
      `).join("");
    } else {
      filingTbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-muted);">수집된 공시가 없습니다.</td></tr>`;
    }

    // Render Price Chart
    renderPriceChart(data.recent_prices);

    document.getElementById("company-modal").classList.add("active");
  } catch (err) {
    console.error("Failed to load company detail:", err);
  }
}

function renderPriceChart(prices) {
  const ctx = document.getElementById("company-price-chart");
  if (!ctx) return;

  if (priceChart) {
    priceChart.destroy();
  }

  if (!prices || prices.length === 0) {
    const context = ctx.getContext("2d");
    context.clearRect(0, 0, ctx.width, ctx.height);
    context.fillStyle = "#6B7280";
    context.font = "14px Inter";
    context.textAlign = "center";
    context.fillText("수집된 주가 데이터가 없습니다.", ctx.width / 2 || 150, 100);
    return;
  }

  const labels = prices.map(p => p.date);
  const closes = prices.map(p => p.close);

  priceChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: "종가 (USD)",
        data: closes,
        borderColor: "#10B981",
        backgroundColor: "rgba(16, 185, 129, 0.1)",
        borderWidth: 2,
        fill: true,
        tension: 0.3,
        pointRadius: 2,
        pointHoverRadius: 5
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          mode: 'index',
          intersect: false,
          callbacks: {
            label: (ctx) => `$${ctx.parsed.y.toFixed(2)}`
          }
        }
      },
      scales: {
        x: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#9CA3AF", maxTicksLimit: 6, font: { size: 10 } }
        },
        y: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: {
            color: "#9CA3AF",
            font: { size: 10 },
            callback: (val) => `$${val}`
          }
        }
      }
    }
  });
}

// 6. Filing Excerpt Modal
async function openFilingModal(filingId) {
  try {
    const res = await fetch(`/api/filings/${filingId}`);
    const json = await res.json();
    if (json.status !== "success") return;

    const f = json.data;
    const badge = document.getElementById("modal-filing-badge");
    badge.className = `filing-badge filing-${f.filing_type}`;
    badge.textContent = f.filing_type;

    document.getElementById("modal-filing-title").textContent = `${f.ticker} - ${f.fiscal_year} ${f.fiscal_quarter}`;
    document.getElementById("modal-filing-meta").innerHTML = `
      제출일: ${f.filed_date} | Accession No: ${f.accession_number || '-'} |
      <a href="${f.source_url || '#'}" target="_blank" style="color:var(--accent-cyan); text-decoration:underline;">SEC 원본 링크 ↗</a>
    `;

    document.getElementById("modal-filing-content").textContent = f.raw_text_preview || "저장된 텍스트 내용이 없습니다.";
    document.getElementById("filing-modal").classList.add("active");
  } catch (err) {
    console.error("Failed to load filing details:", err);
  }
}

function closeModal(modalId) {
  document.getElementById(modalId).classList.remove("active");
}

function closeModalOnOverlay(e, modalId) {
  if (e.target.id === modalId) {
    closeModal(modalId);
  }
}

// 7. Data Collection Trigger
async function triggerCollection(type, ticker) {
  appendLog(`[REQ] ${type.toUpperCase()} 수집 요청 시작... (대상: ${ticker || '배치'})`);
  try {
    const res = await fetch("/api/collect/trigger", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type, ticker })
    });
    const json = await res.json();
    if (json.status === "success") {
      appendLog(`[OK] 수집 성공! 세부 결과: ${JSON.stringify(json.result || json.batch_results)}`);
      // Refresh views
      loadOverview();
      loadEntities();
      loadFilingsTable();
    } else {
      appendLog(`[ERR] 수집 실패: ${json.message}`);
    }
  } catch (err) {
    appendLog(`[FAIL] 통신 오류: ${err.message}`);
  }
}

function appendLog(msg) {
  const box = document.getElementById("terminal-body");
  if (!box) return;
  const time = new Date().toLocaleTimeString();
  box.innerHTML += `<div><span style="color:#6B7280;">[${time}]</span> ${msg}</div>`;
  box.scrollTop = box.scrollHeight;
}

// Helpers
function getLayerShort(code) {
  if (!code) return "L2";
  return code.split("_")[0];
}

function handleGlobalSearch(term) {
  const clean = term.toLowerCase().trim();
  if (!clean) {
    renderCompanies();
    return;
  }
  const filtered = allEntities.filter(e => 
    e.ticker.toLowerCase().includes(clean) || 
    e.name_en.toLowerCase().includes(clean) || 
    e.name_ko.toLowerCase().includes(clean)
  );
  
  // Switch to companies tab if not active
  switchTab("tab-companies");
  const grid = document.getElementById("companies-grid");
  grid.innerHTML = filtered.map(e => {
    const layerShort = getLayerShort(e.layer_code);
    return `
      <div class="company-card" onclick="openCompanyModal('${e.ticker}')">
        <div>
          <div class="card-top">
            <span class="ticker-badge">${e.ticker}</span>
            <span class="layer-tag ${layerShort}">${layerShort}</span>
          </div>
          <div class="company-names">
            <div class="company-name-en">${e.name_en}</div>
            <div class="company-name-ko">${e.name_ko} · ${e.exchange || '비상장'}</div>
          </div>
        </div>
        <div class="card-metrics">
          <div class="metric-item">
            <span class="metric-label">최근 종가</span>
            <span class="metric-value">${e.latest_close ? `$${Number(e.latest_close).toFixed(2)}` : '미수집'}</span>
          </div>
          <div class="metric-item" style="text-align:right;">
            <span class="metric-label">Filing</span>
            <span class="metric-value">${e.filing_count}건</span>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

// ─── Korea Semiconductor Export (순별) ───

let krExportChart = null;

async function loadKrExportData() {
  const indType = document.getElementById("kr-ind-type-filter")
    ? document.getElementById("kr-ind-type-filter").value
    : "KR_SEMI_EXPORT_AMT";

  try {
    const res = await fetch(`/api/indicators/kr-export?type=${indType}&limit=36`);
    const json = await res.json();
    const data = json.data || [];

    // Render table
    const tbody = document.getElementById("kr-export-tbody");
    if (tbody) {
      if (data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-muted); padding:2rem;">입력된 데이터가 없습니다. 오른쪽 폼에서 순별 수출 데이터를 입력하세요.</td></tr>`;
      } else {
        tbody.innerHTML = data.map(r => {
          const val = indType.includes("YOY") ? `${r.value.toFixed(1)}%` : `${Number(r.value).toLocaleString()}`;
          return `
            <tr>
              <td style="font-weight:600;">${r.date}</td>
              <td style="color: ${r.value >= 0 ? 'var(--accent-emerald)' : 'var(--accent-rose)'}; font-weight: 600;">${val}</td>
              <td style="color:var(--text-muted);">${r.unit || ''}</td>
              <td style="color:var(--text-muted);">${r.source || ''}</td>
              <td style="color:var(--text-muted); font-size:0.78rem;">${r.note || ''}</td>
            </tr>
          `;
        }).join("");
      }
    }

    // Render chart (only for AMT types)
    if (indType !== "KR_SEMI_EXPORT_YOY") {
      renderKrExportChart(data, indType);
    } else {
      renderKrExportBarChart(data);
    }
  } catch (err) {
    console.error("Failed to load KR export data:", err);
  }
}

function renderKrExportChart(data, indType) {
  const ctx = document.getElementById("kr-export-chart");
  if (!ctx) return;
  if (krExportChart) krExportChart.destroy();

  if (!data || data.length === 0) {
    const context = ctx.getContext("2d");
    context.clearRect(0, 0, ctx.width, ctx.height);
    context.fillStyle = "#6B7280";
    context.font = "14px Inter";
    context.textAlign = "center";
    context.fillText("데이터를 입력하면 차트가 표시됩니다.", ctx.width / 2 || 200, 130);
    return;
  }

  const labels = data.map(d => d.date);
  const values = data.map(d => d.value);
  const label = indType === "KR_TOTAL_EXPORT_AMT" ? "전체 수출액 (M USD)" : "반도체 수출액 (M USD)";
  const color = indType === "KR_TOTAL_EXPORT_AMT" ? "#3B82F6" : "#F59E0B";

  krExportChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label,
        data: values,
        borderColor: color,
        backgroundColor: color + "20",
        borderWidth: 2.5,
        fill: true,
        tension: 0.3,
        pointRadius: 4,
        pointHoverRadius: 7,
        pointBackgroundColor: color
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true, labels: { color: "#9CA3AF", font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: (ctx) => `${Number(ctx.parsed.y).toLocaleString()} M USD`
          }
        }
      },
      scales: {
        x: {
          grid: { color: "rgba(255,255,255,0.05)" },
          ticks: { color: "#9CA3AF", maxTicksLimit: 12, font: { size: 10 } }
        },
        y: {
          grid: { color: "rgba(255,255,255,0.05)" },
          ticks: {
            color: "#9CA3AF",
            font: { size: 10 },
            callback: v => `${(v / 1000).toFixed(1)}B`
          }
        }
      }
    }
  });
}

function renderKrExportBarChart(data) {
  const ctx = document.getElementById("kr-export-chart");
  if (!ctx) return;
  if (krExportChart) krExportChart.destroy();

  if (!data || data.length === 0) return;

  const labels = data.map(d => d.date);
  const values = data.map(d => d.value);
  const colors = values.map(v => v >= 0 ? "rgba(16, 185, 129, 0.7)" : "rgba(244, 63, 94, 0.7)");
  const borderColors = values.map(v => v >= 0 ? "#10B981" : "#F43F5E");

  krExportChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "YoY 증감률 (%)",
        data: values,
        backgroundColor: colors,
        borderColor: borderColors,
        borderWidth: 1.5,
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true, labels: { color: "#9CA3AF", font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.parsed.y.toFixed(1)}%`
          }
        }
      },
      scales: {
        x: {
          grid: { color: "rgba(255,255,255,0.05)" },
          ticks: { color: "#9CA3AF", maxTicksLimit: 12, font: { size: 10 } }
        },
        y: {
          grid: { color: "rgba(255,255,255,0.05)" },
          ticks: {
            color: "#9CA3AF",
            font: { size: 10 },
            callback: v => `${v}%`
          }
        }
      }
    }
  });
}

async function submitKrExport(e) {
  e.preventDefault();
  const year = document.getElementById("kr-year").value;
  const month = document.getElementById("kr-month").value;
  const period = document.querySelector('input[name="kr-period"]:checked').value;
  const semiAmt = document.getElementById("kr-semi-amt").value;
  const semiYoy = document.getElementById("kr-semi-yoy").value;
  const totalAmt = document.getElementById("kr-total-amt").value;
  const note = document.getElementById("kr-note").value;

  const payload = {
    year: parseInt(year),
    month: parseInt(month),
    period: period,
    semi_export_amt: parseFloat(semiAmt)
  };
  if (semiYoy) payload.semi_yoy_pct = parseFloat(semiYoy);
  if (totalAmt) payload.total_export_amt = parseFloat(totalAmt);
  if (note) payload.note = note;

  try {
    const res = await fetch("/api/indicators/kr-export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const json = await res.json();
    const resultEl = document.getElementById("kr-export-result");
    if (json.status === "success") {
      resultEl.style.display = "block";
      resultEl.style.color = "var(--accent-emerald)";
      resultEl.textContent = `✅ ${json.period} 데이터가 저장되었습니다.`;
      loadKrExportData(); // Refresh
      // Reset form partly
      document.getElementById("kr-semi-amt").value = "";
      document.getElementById("kr-semi-yoy").value = "";
      document.getElementById("kr-total-amt").value = "";
    } else {
      resultEl.style.display = "block";
      resultEl.style.color = "var(--accent-rose)";
      resultEl.textContent = `❌ 오류: ${json.message || json.error}`;
    }
  } catch (err) {
    console.error("Failed to submit KR export:", err);
  }
}

// Radio button visual active states for 순 구분
document.addEventListener("change", (e) => {
  if (e.target.name === "kr-period") {
    document.querySelectorAll('input[name="kr-period"]').forEach(radio => {
      radio.parentElement.classList.toggle("active", radio.checked);
    });
  }
});
