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
  if (tabId === "tab-consensus") loadConsensusData();
  if (tabId === "tab-quarterly") {
    const sel = document.getElementById("quarterly-ticker-select");
    const t = sel ? sel.value : "NVDA";
    loadQuarterlyFinancials(t);
  }
  if (tabId === "tab-indicators") {
    loadMemorySpotData();
    loadKrExportData();
    loadKrExportCombinedChart();
  }
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

// Subtab switcher inside Filing Modal (Summary vs Raw)
function switchModalSubTab(tabName) {
  const sumTab = document.getElementById("modal-subtab-summary");
  const rawTab = document.getElementById("modal-subtab-raw");
  const btnSum = document.getElementById("btn-modal-tab-summary");
  const btnRaw = document.getElementById("btn-modal-tab-raw");

  if (tabName === "summary") {
    if (sumTab) sumTab.style.display = "block";
    if (rawTab) rawTab.style.display = "none";
    if (btnSum) btnSum.classList.add("active");
    if (btnRaw) btnRaw.classList.remove("active");
  } else {
    if (sumTab) sumTab.style.display = "none";
    if (rawTab) rawTab.style.display = "block";
    if (btnSum) btnSum.classList.remove("active");
    if (btnRaw) btnRaw.classList.add("active");
  }
}

// 6. Filing Excerpt & Full-Text Modal
let currentFilingId = null;
let fullFilingText = "";

async function openFilingModal(filingId) {
  currentFilingId = filingId;
  const contentEl = document.getElementById("modal-filing-content");
  const charCountEl = document.getElementById("modal-filing-char-count");
  const filterInput = document.getElementById("modal-text-filter");
  const rawLink = document.getElementById("modal-filing-raw-link");
  const mdaEl = document.getElementById("modal-sec-mda");
  const riskEl = document.getElementById("modal-sec-risk");
  const guidanceEl = document.getElementById("modal-sec-guidance");
  const mdaLenEl = document.getElementById("modal-sec-mda-len");
  const riskLenEl = document.getElementById("modal-sec-risk-len");

  if (filterInput) filterInput.value = "";
  if (contentEl) contentEl.textContent = "원문 텍스트를 불러오는 중...";
  if (charCountEl) charCountEl.textContent = "불러오는 중...";
  if (mdaEl) mdaEl.textContent = "MD&A 섹션 분할 분석 중...";
  if (riskEl) riskEl.textContent = "리스크 요인 분석 중...";
  if (guidanceEl) guidanceEl.textContent = "가이던스 발췌문 검색 중...";
  if (rawLink) rawLink.style.display = "none";

  // Default to summary subtab
  switchModalSubTab("summary");
  document.getElementById("filing-modal").classList.add("active");

  try {
    // 1. Fetch metadata
    const metaRes = await fetch(`/api/filings/${filingId}`);
    const metaJson = await metaRes.json();
    if (metaJson.status !== "success") return;
    const f = metaJson.data;

    const badge = document.getElementById("modal-filing-badge");
    badge.className = `filing-badge filing-${f.filing_type}`;
    badge.textContent = f.filing_type;

    document.getElementById("modal-filing-title").textContent = `${f.ticker} - ${f.fiscal_year} ${f.fiscal_quarter} (${f.filing_type})`;
    document.getElementById("modal-filing-meta").innerHTML = `
      제출일: ${f.filed_date} | 대상기간: ${f.period_end_date || '-'} | Accession No: ${f.accession_number || '-'} |
      <a href="${f.source_url || '#'}" target="_blank" style="color:var(--accent-cyan); text-decoration:underline;">SEC EDGAR 링크 ↗</a>
    `;

    // Local HTML Raw File link if available
    if (f.has_local_file && rawLink) {
      rawLink.href = `/api/filings/${filingId}/raw`;
      rawLink.style.display = "inline-flex";
    }

    // 2. Fetch Full Text
    const textRes = await fetch(`/api/filings/${filingId}/text`);
    const textJson = await textRes.json();
    fullFilingText = (textJson.data && textJson.data.text) || f.raw_text_preview || "(원문 텍스트가 없습니다. '원문 다운로드' 버튼을 클릭해 주세요.)";

    contentEl.textContent = fullFilingText;
    charCountEl.textContent = `전체 ${Number(fullFilingText.length).toLocaleString()}자`;

    // 3. Fetch Isolated Sections (MD&A, Risk, Highlights)
    const secRes = await fetch(`/api/filings/${filingId}/sections`);
    const secJson = await secRes.json();
    if (secJson.status === "success" && secJson.sections) {
      const secs = secJson.sections;
      const mda = secs.mda || secs.business || {};
      const risk = secs.risk_factors || {};
      const hl = secs.highlights || {};

      if (mdaEl) {
        mdaEl.textContent = mda.text || "(MD&A 섹션을 찾지 못했습니다. 원문 전문 탭에서 확인하세요.)";
        if (mdaLenEl) mdaLenEl.textContent = mda.length > 0 ? `${Number(mda.length).toLocaleString()}자 추출` : "미검출";
      }

      if (riskEl) {
        riskEl.textContent = risk.text || "(주요 리스크 섹션을 찾지 못했습니다. 원문 전문 탭에서 확인하세요.)";
        if (riskLenEl) riskLenEl.textContent = risk.length > 0 ? `${Number(risk.length).toLocaleString()}자 추출` : "미검출";
      }

      if (guidanceEl) {
        if (hl.guidance_mentions && hl.guidance_mentions.length > 0) {
          guidanceEl.innerHTML = hl.guidance_mentions.map(g => `
            <div style="margin-bottom:0.4rem; padding-left:0.5rem; border-left:2px solid var(--accent-emerald);">• ${g}</div>
          `).join("");
        } else {
          guidanceEl.textContent = "본문에서 감지된 명시적 분기 가이던스 문장이 없습니다.";
        }
      }
    }

  } catch (err) {
    console.error("Failed to load filing full text or sections:", err);
    contentEl.textContent = "오류 발생: 텍스트를 불러오지 못했습니다.";
  }
}

async function downloadCurrentFiling() {
  if (!currentFilingId) return;
  const btn = document.getElementById("modal-filing-download-btn");
  const origText = btn.textContent;
  btn.textContent = "다운로드 중...";
  btn.disabled = true;

  try {
    const res = await fetch(`/api/filings/${currentFilingId}/download`, { method: "POST" });
    const json = await res.json();
    if (json.status === "success") {
      alert(`✅ ${json.ticker} ${json.form} 원문 다운로드 및 FTS 색인이 완료되었습니다! (${json.text_length}자 추출)`);
      // Reload current modal text
      openFilingModal(currentFilingId);
      loadFilingsTable(); // Refresh archive table
    } else {
      alert(`❌ 다운로드 실패: ${json.message}`);
    }
  } catch (err) {
    alert(`오류: ${err.message}`);
  } finally {
    btn.textContent = origText;
    btn.disabled = false;
  }
}

function copyFilingText() {
  if (!fullFilingText) return;
  navigator.clipboard.writeText(fullFilingText).then(() => {
    alert("📋 공시 전문 텍스트가 클립보드에 복사되었습니다.");
  }).catch(err => {
    console.error("Copy failed:", err);
  });
}

function filterModalText(query) {
  const contentEl = document.getElementById("modal-filing-content");
  if (!contentEl || !fullFilingText) return;

  const q = query.trim().toLowerCase();
  if (!q) {
    contentEl.textContent = fullFilingText;
    return;
  }

  // Find occurrences with surrounding context
  const lines = fullFilingText.split("\n");
  const matched = lines.filter(line => line.toLowerCase().includes(q));

  if (matched.length > 0) {
    contentEl.textContent = `[검색어 '${query}' 포함 ${matched.length}개 단락]\n\n` + matched.join("\n\n---\n\n");
  } else {
    contentEl.textContent = `[검색어 '${query}'에 일치하는 내용이 없습니다.]`;
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

// ─── Combined 10-Day KR Export Chart (Amt + YoY) ───
async function loadKrExportCombinedChart() {
  const ctx = document.getElementById("kr-export-chart");
  if (!ctx) return;

  try {
    const [amtRes, yoyRes] = await Promise.all([
      fetch("/api/indicators/kr-export?type=KR_SEMI_EXPORT_AMT&limit=15"),
      fetch("/api/indicators/kr-export?type=KR_SEMI_EXPORT_YOY&limit=15")
    ]);
    const amtJson = await amtRes.json();
    const yoyJson = await yoyRes.json();

    const amtData = amtJson.data || [];
    const yoyData = yoyJson.data || [];

    if (amtData.length === 0 && yoyData.length === 0) return;

    if (krExportChart) krExportChart.destroy();

    const labels = amtData.map(d => d.date);
    const amounts = amtData.map(d => d.value);

    // Map YoY by date
    const yoyMap = {};
    yoyData.forEach(d => { yoyMap[d.date] = d.value; });
    const yoyValues = labels.map(date => yoyMap[date] !== undefined ? yoyMap[date] : null);

    krExportChart = new Chart(ctx, {
      data: {
        labels,
        datasets: [
          {
            type: "bar",
            label: "반도체 수출액 (M USD)",
            data: amounts,
            backgroundColor: "rgba(245, 158, 11, 0.4)",
            borderColor: "#F59E0B",
            borderWidth: 1.5,
            borderRadius: 4,
            yAxisID: "y"
          },
          {
            type: "line",
            label: "YoY 증감률 (%)",
            data: yoyValues,
            borderColor: "#10B981",
            backgroundColor: "transparent",
            borderWidth: 2.5,
            pointBackgroundColor: "#10B981",
            pointRadius: 4,
            pointHoverRadius: 6,
            tension: 0.3,
            yAxisID: "y1"
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: {
            display: true,
            labels: { color: "#9CA3AF", font: { size: 11 } }
          },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                if (ctx.dataset.type === "bar") {
                  return `수출액: ${Number(ctx.parsed.y).toLocaleString()} M USD`;
                }
                return `YoY: ${ctx.parsed.y > 0 ? '+' : ''}${ctx.parsed.y.toFixed(1)}%`;
              }
            }
          }
        },
        scales: {
          x: {
            grid: { color: "rgba(255,255,255,0.04)" },
            ticks: { color: "#9CA3AF", font: { size: 10 } }
          },
          y: {
            type: "linear",
            display: true,
            position: "left",
            grid: { color: "rgba(255,255,255,0.05)" },
            ticks: {
              color: "#F59E0B",
              font: { size: 10 },
              callback: v => `${(v / 1000).toFixed(1)}B`
            }
          },
          y1: {
            type: "linear",
            display: true,
            position: "right",
            grid: { drawOnChartArea: false },
            ticks: {
              color: "#10B981",
              font: { size: 10 },
              callback: v => `${v}%`
            }
          }
        }
      }
    });
  } catch (err) {
    console.error("Failed to render combined KR export chart:", err);
  }
}

// ─── 8. Consensus & Beat/Miss Dashboard ───
let rawConsensusMatrix = null;
let currentConsensusMetric = "all";

async function loadConsensusData() {
  const tbody = document.getElementById("consensus-matrix-tbody");
  if (tbody) tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-muted); padding:2rem;">컨센서스 및 실적 데이터를 불러오는 중...</td></tr>`;

  try {
    const res = await fetch("/api/consensus/matrix");
    const json = await res.json();
    if (json.status !== "success") return;

    rawConsensusMatrix = json.data;
    renderConsensusMatrix();
  } catch (err) {
    console.error("Failed to load consensus matrix:", err);
  }
}

function setConsensusMetricFilter(metric) {
  currentConsensusMetric = metric;
  document.querySelectorAll("#consensus-metric-selector .layer-pill").forEach(btn => {
    btn.classList.remove("active");
  });
  event.target.classList.add("active");
  renderConsensusMatrix();
}

function renderConsensusMatrix() {
  if (!rawConsensusMatrix) return;

  const { quarters, companies } = rawConsensusMatrix;
  const thead = document.getElementById("consensus-matrix-thead");
  const tbody = document.getElementById("consensus-matrix-tbody");

  if (!thead || !tbody) return;

  // Render headers
  thead.innerHTML = `
    <tr>
      <th style="min-width: 140px;">기업 / 티커</th>
      <th style="min-width: 80px;">레이어</th>
      ${quarters.map(q => `<th style="text-align:center; min-width: 110px;">${q}</th>`).join("")}
    </tr>
  `;

  if (!companies || companies.length === 0) {
    tbody.innerHTML = `<tr><td colspan="${quarters.length + 2}" style="text-align:center; color:var(--text-muted); padding:2rem;">등록된 컨센서스 데이터가 없습니다. 상단의 '🔄 샘플 데이터 로드'를 클릭해 보세요.</td></tr>`;
    return;
  }

  // Calculate KPIs
  let totalEvaluated = 0;
  let totalBeat = 0;
  let return1dSum = 0;
  let return1dCount = 0;

  companies.forEach(c => {
    Object.values(c.quarters).forEach(qData => {
      ["revenue", "eps"].forEach(m => {
        if (qData[m] && qData[m].status && qData[m].status !== "UNKNOWN") {
          totalEvaluated++;
          if (qData[m].status === "BEAT") totalBeat++;
          if (qData[m].ret_1d !== null && qData[m].ret_1d !== undefined) {
            return1dSum += qData[m].ret_1d;
            return1dCount++;
          }
        }
      });
    });
  });

  const beatRateEl = document.getElementById("consensus-kpi-beat-rate");
  const avgReturnEl = document.getElementById("consensus-kpi-avg-return");
  const compCountEl = document.getElementById("consensus-kpi-company-count");

  if (beatRateEl && totalEvaluated > 0) {
    const rate = ((totalBeat / totalEvaluated) * 100).toFixed(1);
    beatRateEl.textContent = `${rate}%`;
    beatRateEl.nextElementSibling.textContent = `최근 평가 실적 (${totalBeat} / ${totalEvaluated}건)`;
  }
  if (avgReturnEl && return1dCount > 0) {
    const avg = (return1dSum / return1dCount).toFixed(1);
    avgReturnEl.textContent = `${avg > 0 ? '+' : ''}${avg}%`;
  }
  if (compCountEl) {
    compCountEl.textContent = `${companies.length}개사`;
  }

  // Render Rows
  tbody.innerHTML = companies.map(c => {
    const short = getLayerShort(c.layer_code);
    const cells = quarters.map(qKey => {
      const qData = c.quarters[qKey] || {};
      const rev = qData.revenue;
      const eps = qData.eps;

      if (!rev && !eps) {
        return `<td><div style="color:var(--text-muted); text-align:center; font-size:0.75rem;">-</div></td>`;
      }

      let contentHtml = "";

      if (currentConsensusMetric === "all") {
        contentHtml = `
          ${renderMetricMiniBadge("Rev", rev)}
          ${renderMetricMiniBadge("EPS", eps)}
        `;
      } else if (currentConsensusMetric === "revenue") {
        contentHtml = renderMetricDetailCell(rev, "M_USD");
      } else if (currentConsensusMetric === "eps") {
        contentHtml = renderMetricDetailCell(eps, "USD");
      }

      return `<td>${contentHtml}</td>`;
    }).join("");

    return `
      <tr>
        <td>
          <div style="display:flex; align-items:center; gap:0.5rem;">
            <strong>${c.ticker}</strong>
            <span style="font-size:0.75rem; color:var(--text-muted);">${c.name_ko || c.name_en}</span>
          </div>
        </td>
        <td><span class="layer-tag ${short}">${short}</span></td>
        ${cells}
      </tr>
    `;
  }).join("");
}

function renderMetricMiniBadge(label, item) {
  if (!item || !item.status || item.status === "UNKNOWN") {
    return `<div style="font-size:0.72rem; color:var(--text-muted); text-align:center;">${label}: 미입력</div>`;
  }

  const cls = item.status === "BEAT" ? "pill-beat" : (item.status === "MISS" ? "pill-miss" : "pill-inline");
  const sign = item.surprise_pct > 0 ? "+" : "";
  const priceReaction = item.ret_1d !== null && item.ret_1d !== undefined
    ? `<span class="price-reaction-tag">1d: ${item.ret_1d > 0 ? '+' : ''}${item.ret_1d}%</span>`
    : "";

  return `
    <div class="matrix-cell cell-${item.status.toLowerCase()}">
      <div style="display:flex; justify-content:space-between; width:100%; align-items:center;">
        <span style="font-size:0.7rem; color:var(--text-secondary);">${label}</span>
        <span class="beat-miss-pill ${cls}">${item.status}</span>
      </div>
      <div class="surprise-pct ${item.surprise_pct > 0 ? 'pos' : (item.surprise_pct < 0 ? 'neg' : 'zero')}">
        ${sign}${item.surprise_pct}%
      </div>
      ${priceReaction}
    </div>
  `;
}

function renderMetricDetailCell(item, unit) {
  if (!item || !item.status || item.status === "UNKNOWN") {
    return `<div style="font-size:0.75rem; color:var(--text-muted); text-align:center;">-</div>`;
  }

  const cls = item.status === "BEAT" ? "pill-beat" : (item.status === "MISS" ? "pill-miss" : "pill-inline");
  const sign = item.surprise_pct > 0 ? "+" : "";

  return `
    <div class="matrix-cell cell-${item.status.toLowerCase()}" style="padding: 0.5rem 0.6rem;">
      <span class="beat-miss-pill ${cls}">${item.status} (${sign}${item.surprise_pct}%)</span>
      <div style="font-size:0.75rem; color:#fff; font-family:'JetBrains Mono',monospace; margin-top:0.2rem;">
        실제: <strong>${item.actual}</strong>
      </div>
      <div style="font-size:0.7rem; color:var(--text-muted);">
        예상: ${item.consensus}
      </div>
    </div>
  `;
}

function openConsensusModal() {
  document.getElementById("consensus-modal").classList.add("active");
}

async function submitConsensusForm(e) {
  e.preventDefault();
  const ticker = document.getElementById("consensus-ticker").value;
  const year = document.getElementById("consensus-year").value;
  const quarter = document.getElementById("consensus-quarter").value;
  const metric = document.getElementById("consensus-metric").value;
  const consensusVal = document.getElementById("consensus-val").value;
  const actualVal = document.getElementById("actual-val").value;
  const dateVal = document.getElementById("consensus-date").value;

  const payload = {
    ticker,
    fiscal_year: year,
    fiscal_quarter: quarter,
    metric_type: metric,
    consensus_value: parseFloat(consensusVal)
  };

  if (actualVal) payload.actual_value = parseFloat(actualVal);
  if (dateVal) payload.announcement_date = dateVal;

  try {
    const res = await fetch("/api/consensus", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const json = await res.json();
    if (json.status === "success") {
      alert(`✅ ${ticker} ${year}-${quarter} ${metric} 컨센서스가 저장되었습니다! (판정: ${json.beat_miss_status || '입력완료'})`);
      closeModal("consensus-modal");
      loadConsensusData();
    } else {
      alert(`❌ 저장 실패: ${json.message}`);
    }
  } catch (err) {
    alert(`오류: ${err.message}`);
  }
}

async function seedConsensusData() {
  try {
    const res = await fetch("/api/consensus/seed", { method: "POST" });
    const json = await res.json();
    if (json.status === "success") {
      alert(`✅ 주요 AI 기업 샘플 컨센서스(${json.seeded_count}건)가 적재되었습니다!`);
      loadConsensusData();
    } else {
      alert(`실패: ${json.message}`);
    }
  } catch (err) {
    alert(`오류: ${err.message}`);
  }
}

// ─── 9. Memory Semiconductor Spot Price Dashboard ───
let memorySpotChart = null;
let currentSpotType = "SPOT_DRAM_DDR5_16GB";

async function loadMemorySpotData() {
  try {
    const res = await fetch(`/api/indicators/memory-spot?type=${currentSpotType}&limit=30`);
    const json = await res.json();
    if (json.status !== "success") return;

    renderMemorySpotSummary(json.summary);
    renderMemorySpotChart(json.history, json.indicator_info);
  } catch (err) {
    console.error("Failed to load memory spot data:", err);
  }
}

function renderMemorySpotSummary(summary) {
  if (!summary) return;

  const ddr5 = summary["SPOT_DRAM_DDR5_16GB"];
  const ddr4 = summary["SPOT_DRAM_DDR4_8GB"];
  const nand = summary["SPOT_NAND_TLC_512GB"];
  const dxi = summary["INDEX_DXI"];

  const updateCard = (valId, subId, item, isPoint = false) => {
    const valEl = document.getElementById(valId);
    const subEl = document.getElementById(subId);
    if (!valEl || !subEl || !item) return;

    if (item.latest_price !== null && item.latest_price !== undefined) {
      valEl.textContent = isPoint ? Number(item.latest_price).toLocaleString() : `$${Number(item.latest_price).toFixed(2)}`;
      const sign = item.change_pct >= 0 ? "▲ +" : "▼ ";
      const color = item.change_pct >= 0 ? "var(--accent-emerald)" : "var(--accent-rose)";
      subEl.textContent = `${sign}${item.change_pct}% (전주 대비)`;
      subEl.style.color = color;
    } else {
      valEl.textContent = "-";
      subEl.textContent = "데이터 없음";
      subEl.style.color = "var(--text-muted)";
    }
  };

  updateCard("val-spot-ddr5", "sub-spot-ddr5", ddr5);
  updateCard("val-spot-ddr4", "sub-spot-ddr4", ddr4);
  updateCard("val-spot-nand", "sub-spot-nand", nand);
  updateCard("val-spot-dxi", "sub-spot-dxi", dxi, true);
}

function switchSpotChart(type) {
  currentSpotType = type;
  document.querySelectorAll("#spot-indicator-selector .layer-pill").forEach(btn => {
    btn.classList.remove("active");
  });
  if (event && event.target) {
    event.target.classList.add("active");
  }

  // Update chart title
  const titleMap = {
    "SPOT_DRAM_DDR5_16GB": "📈 DDR5 16Gb 스팟 현물 가격 추이 (USD)",
    "SPOT_DRAM_DDR4_8GB": "📈 DDR4 8Gb 스팟 현물 가격 추이 (USD)",
    "SPOT_NAND_TLC_512GB": "📈 NAND 512Gb TLC 스팟 현물 가격 추이 (USD)",
    "INDEX_DXI": "📈 DXI 메모리 반도체 종합 지수 추이 (Points)"
  };
  const titleEl = document.getElementById("spot-chart-title");
  if (titleEl && titleMap[type]) {
    titleEl.innerHTML = `<span>📈</span> ${titleMap[type]}`;
  }

  loadMemorySpotData();
}

function renderMemorySpotChart(history, info) {
  const ctx = document.getElementById("memory-spot-chart");
  if (!ctx) return;

  if (memorySpotChart) {
    memorySpotChart.destroy();
  }

  if (!history || history.length === 0) {
    const context = ctx.getContext("2d");
    context.clearRect(0, 0, ctx.width, ctx.height);
    context.fillStyle = "#6B7280";
    context.font = "14px Inter";
    context.textAlign = "center";
    context.fillText("현물 가격 데이터가 없습니다. 상단 '현물가 시드 로드'를 클릭하세요.", ctx.width / 2 || 200, 130);
    return;
  }

  const labels = history.map(d => d.date);
  const values = history.map(d => d.value);
  const isPoints = info && info.unit === "Points";
  const lineColor = isPoints ? "#818CF8" : "#38BDF8";

  memorySpotChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: `${(info && info.name_ko) || currentSpotType} (${(info && info.unit) || 'USD'})`,
        data: values,
        borderColor: lineColor,
        backgroundColor: lineColor + "15",
        borderWidth: 2.5,
        fill: true,
        tension: 0.35,
        pointRadius: 4,
        pointHoverRadius: 7,
        pointBackgroundColor: lineColor
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          display: true,
          labels: { color: "#9CA3AF", font: { size: 11 } }
        },
        tooltip: {
          callbacks: {
            label: (ctx) => isPoints ? `${Number(ctx.parsed.y).toLocaleString()} Points` : `$${ctx.parsed.y.toFixed(2)} USD`
          }
        }
      },
      scales: {
        x: {
          grid: { color: "rgba(255,255,255,0.04)" },
          ticks: { color: "#9CA3AF", maxTicksLimit: 12, font: { size: 10 } }
        },
        y: {
          grid: { color: "rgba(255,255,255,0.05)" },
          ticks: {
            color: "#9CA3AF",
            font: { size: 10 },
            callback: (v) => isPoints ? `${(v / 1000).toFixed(0)}k` : `$${v.toFixed(2)}`
          }
        }
      }
    }
  });
}

async function seedMemorySpotData() {
  try {
    const res = await fetch("/api/indicators/memory-spot/seed", { method: "POST" });
    const json = await res.json();
    if (json.status === "success") {
      alert(`✅ 메모리 현물 가격 시계열 데이터(${json.seeded_count}건)가 적재되었습니다!`);
      loadMemorySpotData();
    } else {
      alert(`실패: ${json.message}`);
    }
  } catch (err) {
    alert(`오류: ${err.message}`);
  }
}

async function fetchMemorySpotApi() {
  try {
    const res = await fetch("/api/indicators/memory-spot/fetch", { method: "POST" });
    const json = await res.json();
    alert(`동기화 결과: ${json.message || `완료 (${json.imported || 0}건 저장)`}`);
    loadMemorySpotData();
  } catch (err) {
    alert(`오류: ${err.message}`);
  }
}

// ─── 10. Quarterly Financial Intelligence (10-Q/10-K from 2020) ───
let quarterlyChart = null;
let capexChart = null;
let currentQuarterlySeries = [];
let currentQuarterlyEntity = null;

async function loadQuarterlyFinancials(ticker = "NVDA") {
  const tbody = document.getElementById("quarterly-financial-tbody");
  if (tbody) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 2rem;">${ticker} 분기 실적 데이터를 불러오는 중...</td></tr>`;
  }

  try {
    const res = await fetch(`/api/financials/${ticker}`);
    const json = await res.json();
    if (json.status !== "success") return;

    currentQuarterlySeries = json.series || [];
    currentQuarterlyEntity = json.entity || {};

    const countLabel = document.getElementById("quarterly-count-label");
    if (countLabel) {
      countLabel.textContent = `${currentQuarterlySeries.length}개 분기 수집 완료 (2020~2026)`;
    }

    renderQuarterlySummary(currentQuarterlySeries, currentQuarterlyEntity);
    renderQuarterlyChart(currentQuarterlySeries, ticker);
    renderCapexChart(currentQuarterlySeries, ticker);
    renderQuarterlyTable(currentQuarterlySeries);

    // Default select latest quarter for MD&A highlight
    if (currentQuarterlySeries.length > 0) {
      selectQuarterRow(0);
    }
  } catch (err) {
    console.error(`Failed to load quarterly financials for ${ticker}:`, err);
  }
}

function renderQuarterlySummary(series, entity) {
  if (!series || series.length === 0) return;
  const latest = series[0];

  const revEl = document.getElementById("kpi-q-rev");
  const revSubEl = document.getElementById("kpi-q-rev-sub");
  const opmEl = document.getElementById("kpi-q-opm");
  const opIncEl = document.getElementById("kpi-q-op-inc");
  const dcRatioEl = document.getElementById("kpi-q-dc-ratio");
  const dcAmtEl = document.getElementById("kpi-q-dc-amt");
  const capexEl = document.getElementById("kpi-q-capex");
  const capexSubEl = document.getElementById("kpi-q-capex-sub");

  if (revEl && latest.revenue !== undefined) {
    revEl.textContent = `$${(latest.revenue / 1000).toFixed(1)}B`;
  }
  if (revSubEl) {
    const yoy = latest.revenue_yoy_pct;
    if (yoy !== null && yoy !== undefined) {
      revSubEl.textContent = `YoY ${yoy > 0 ? '+' : ''}${yoy.toFixed(1)}% (${latest.period})`;
      revSubEl.style.color = yoy >= 0 ? "var(--accent-emerald)" : "var(--accent-rose)";
    } else {
      revSubEl.textContent = `${latest.period} 기준`;
    }
  }

  if (opmEl && latest.op_margin_pct !== undefined) {
    opmEl.textContent = `${Number(latest.op_margin_pct).toFixed(1)}%`;
  }
  if (opIncEl && latest.operating_income !== undefined) {
    opIncEl.textContent = `영업이익 $${(latest.operating_income / 1000).toFixed(1)}B`;
  }

  if (dcRatioEl) {
    dcRatioEl.textContent = latest.revenue_datacenter_pct ? `${Number(latest.revenue_datacenter_pct).toFixed(1)}%` : "-";
  }
  if (dcAmtEl) {
    dcAmtEl.textContent = latest.revenue_datacenter ? `DC 매출 $${(latest.revenue_datacenter / 1000).toFixed(1)}B` : "부문 데이터 없음";
  }

  if (capexEl && latest.capex !== undefined) {
    capexEl.textContent = `$${(latest.capex / 1000).toFixed(1)}B`;
  }
  if (capexSubEl) {
    capexSubEl.textContent = `설비투자액 (${latest.period})`;
  }
}

function renderQuarterlyChart(series, ticker) {
  const ctx = document.getElementById("quarterly-financial-chart");
  if (!ctx) return;
  if (quarterlyChart) quarterlyChart.destroy();

  if (!series || series.length === 0) return;

  const chronological = [...series].reverse();
  const labels = chronological.map(d => d.period);
  const revValues = chronological.map(d => d.revenue);
  const opValues = chronological.map(d => d.operating_income);
  const opmValues = chronological.map(d => d.op_margin_pct);

  const titleEl = document.getElementById("chart-quarterly-title");
  if (titleEl) {
    titleEl.innerHTML = `<span>📊</span> ${ticker} 분기 매출액 & 영업이익 추이 (2020~2026, M USD)`;
  }

  quarterlyChart = new Chart(ctx, {
    data: {
      labels,
      datasets: [
        {
          type: "bar",
          label: "매출액 (M USD)",
          data: revValues,
          backgroundColor: "rgba(56, 189, 248, 0.4)",
          borderColor: "#38BDF8",
          borderWidth: 1.5,
          borderRadius: 3,
          yAxisID: "y"
        },
        {
          type: "bar",
          label: "영업이익 (M USD)",
          data: opValues,
          backgroundColor: "rgba(16, 185, 129, 0.5)",
          borderColor: "#10B981",
          borderWidth: 1.5,
          borderRadius: 3,
          yAxisID: "y"
        },
        {
          type: "line",
          label: "영업이익률 (%)",
          data: opmValues,
          borderColor: "#F59E0B",
          backgroundColor: "transparent",
          borderWidth: 2.5,
          pointBackgroundColor: "#F59E0B",
          pointRadius: 3,
          pointHoverRadius: 5,
          tension: 0.2,
          yAxisID: "y1"
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: true, labels: { color: "#9CA3AF", font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: (c) => {
              if (c.dataset.type === "bar") {
                return `${c.dataset.label}: $${Number(c.parsed.y).toLocaleString()}M ($${(c.parsed.y / 1000).toFixed(1)}B)`;
              }
              return `OPM: ${c.parsed.y.toFixed(1)}%`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: { color: "rgba(255,255,255,0.04)" },
          ticks: { color: "#9CA3AF", maxTicksLimit: 14, font: { size: 10 } }
        },
        y: {
          type: "linear",
          display: true,
          position: "left",
          grid: { color: "rgba(255,255,255,0.05)" },
          ticks: {
            color: "#38BDF8",
            font: { size: 10 },
            callback: v => `$${(v / 1000).toFixed(0)}B`
          }
        },
        y1: {
          type: "linear",
          display: true,
          position: "right",
          grid: { drawOnChartArea: false },
          ticks: {
            color: "#F59E0B",
            font: { size: 10 },
            callback: v => `${v}%`
          }
        }
      }
    }
  });
}

function renderCapexChart(series, ticker) {
  const ctx = document.getElementById("quarterly-capex-chart");
  if (!ctx) return;
  if (capexChart) capexChart.destroy();

  if (!series || series.length === 0) return;

  const chronological = [...series].reverse();
  const labels = chronological.map(d => d.period);
  const capexValues = chronological.map(d => d.capex);
  const dcValues = chronological.map(d => d.revenue_datacenter);

  capexChart = new Chart(ctx, {
    data: {
      labels,
      datasets: [
        {
          type: "bar",
          label: "설비투자(CapEx) (M USD)",
          data: capexValues,
          backgroundColor: "rgba(244, 63, 94, 0.4)",
          borderColor: "#F43F5E",
          borderWidth: 1.5,
          borderRadius: 3,
          yAxisID: "y"
        },
        {
          type: "line",
          label: "데이터센터 매출 (M USD)",
          data: dcValues,
          borderColor: "#A78BFA",
          backgroundColor: "rgba(167, 139, 250, 0.1)",
          borderWidth: 2.5,
          fill: true,
          pointBackgroundColor: "#A78BFA",
          pointRadius: 3,
          tension: 0.25,
          yAxisID: "y"
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: true, labels: { color: "#9CA3AF", font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: (c) => `${c.dataset.label}: $${Number(c.parsed.y).toLocaleString()}M`
          }
        }
      },
      scales: {
        x: {
          grid: { color: "rgba(255,255,255,0.04)" },
          ticks: { color: "#9CA3AF", maxTicksLimit: 14, font: { size: 10 } }
        },
        y: {
          grid: { color: "rgba(255,255,255,0.05)" },
          ticks: {
            color: "#A78BFA",
            font: { size: 10 },
            callback: v => `$${(v / 1000).toFixed(0)}B`
          }
        }
      }
    }
  });
}

function renderQuarterlyTable(series) {
  const tbody = document.getElementById("quarterly-financial-tbody");
  if (!tbody) return;

  if (!series || series.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 2rem;">수집된 분기 실적 데이터가 없습니다. 상단 '🔄 2020~ 실적 시드 로드'를 클릭해 보세요.</td></tr>`;
    return;
  }

  tbody.innerHTML = series.map((row, idx) => {
    const yoy = row.revenue_yoy_pct;
    const yoyBadge = yoy !== null && yoy !== undefined
      ? `<span style="font-size:0.75rem; color:${yoy >= 0 ? 'var(--accent-emerald)' : 'var(--accent-rose)'}; margin-left:0.4rem;">(${yoy > 0 ? '+' : ''}${yoy.toFixed(1)}%)</span>`
      : "";

    const filingBtn = row.filing_id
      ? `<button class="btn" style="padding: 0.2rem 0.5rem; font-size: 0.75rem;" onclick="event.stopPropagation(); openFilingModal(${row.filing_id})">📑 원문</button>`
      : `<span style="color:var(--text-muted); font-size:0.75rem;">-</span>`;

    const dcText = row.revenue_datacenter
      ? `$${(row.revenue_datacenter / 1000).toFixed(1)}B <span style="font-size:0.75rem; color:#A78BFA;">(${row.revenue_datacenter_pct ? row.revenue_datacenter_pct.toFixed(0) : '-'}%)</span>`
      : "-";

    return `
      <tr onclick="selectQuarterRow(${idx})" style="cursor: pointer;" id="quarter-row-${idx}">
        <td><strong>${row.period}</strong></td>
        <td><span class="filing-badge filing-${row.filing_type || '10-Q'}">${row.filing_type || '10-Q'}</span></td>
        <td style="color: var(--text-muted); font-size: 0.8rem;">${row.filed_date || '-'}</td>
        <td style="text-align: right; font-weight: 600;">$${(row.revenue / 1000).toFixed(1)}B ${yoyBadge}</td>
        <td style="text-align: right; color: var(--accent-cyan);">$${(row.operating_income / 1000).toFixed(1)}B <span style="font-size:0.75rem; color:var(--text-muted);">(${row.op_margin_pct ? row.op_margin_pct.toFixed(1) : '-'}%)</span></td>
        <td style="text-align: right;">$${row.net_income ? (row.net_income / 1000).toFixed(1) + 'B' : '-'}</td>
        <td style="text-align: right; color: #F43F5E;">$${row.capex ? (row.capex / 1000).toFixed(1) + 'B' : '-'}</td>
        <td style="text-align: right;">${dcText}</td>
        <td style="text-align: center;">${filingBtn}</td>
      </tr>
    `;
  }).join("");
}

function selectQuarterRow(index) {
  if (!currentQuarterlySeries || !currentQuarterlySeries[index]) return;
  const item = currentQuarterlySeries[index];

  // Highlight selected table row
  document.querySelectorAll("#quarterly-financial-tbody tr").forEach(tr => tr.style.background = "");
  const selectedTr = document.getElementById(`quarter-row-${index}`);
  if (selectedTr) {
    selectedTr.style.background = "rgba(56, 189, 248, 0.12)";
  }

  // Update MD&A highlight panel
  const titleEl = document.getElementById("mda-panel-title");
  const periodEl = document.getElementById("mda-panel-period");
  const contentEl = document.getElementById("mda-panel-content");

  const ticker = (currentQuarterlyEntity && currentQuarterlyEntity.ticker) || "NVDA";

  if (titleEl) {
    titleEl.innerHTML = `🎙️ ${ticker} ${item.period} (${item.filing_type || '10-Q'}) 경영진 실적 분석 (MD&A) & 주요 코멘트`;
  }
  if (periodEl) {
    periodEl.textContent = `${item.period} ${item.filing_type || '10-Q'}`;
  }
  if (contentEl) {
    contentEl.textContent = item.mda_summary || "(해당 분기에 등록된 MD&A 요약 정보가 없습니다.)";
  }
}

async function seedQuarterlyFinancialsData() {
  try {
    const res = await fetch("/api/financials/seed", { method: "POST" });
    const json = await res.json();
    if (json.status === "success") {
      alert(`✅ 2020년부터의 분기 실적 시계열(${json.seeded_count}건)이 적재되었습니다!`);
      const sel = document.getElementById("quarterly-ticker-select");
      const t = sel ? sel.value : "NVDA";
      loadQuarterlyFinancials(t);
    } else {
      alert(`실패: ${json.message}`);
    }
  } catch (err) {
    alert(`오류: ${err.message}`);
  }
}



