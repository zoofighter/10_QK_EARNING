/**
 * QK_EARNING Application Logic
 */

let allEntities = [];
let allFilings = [];
let activeLayer = "ALL";
let priceChart = null;

// Initialization
document.addEventListener("DOMContentLoaded", () => {
  updateTodayDateDisplay();
  loadOverview();
  loadEntities();
  loadFilingsTable();
  loadCalendarTable();
});

function updateTodayDateDisplay() {
  const el = document.getElementById("today-date-display");
  if (!el) return;
  const now = new Date();
  const days = ["일", "월", "화", "수", "목", "금", "토"];
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  const dayName = days[now.getDay()];
  el.textContent = `${y}-${m}-${d} (${dayName})`;
}

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
  if (tabId === "tab-transcripts") {
    loadTranscriptsList();
  }
  if (tabId === "tab-reports") {
    loadReportStudio();
  }
  if (tabId === "tab-indicators") {
    loadMemorySpotData();
    loadKrExportData();
    loadKrExportCombinedChart();
    loadGpuRentalData();
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
      const nextPeriod = next.fiscal_year && next.fiscal_quarter ? `${next.fiscal_year}-${next.fiscal_quarter}` : (next.fiscal_year || '');
      document.getElementById("kpi-next-company").textContent = nextPeriod ? `${next.ticker} (${nextPeriod})` : next.ticker;
    }

    // Render upcoming table in overview
    const calBody = document.getElementById("overview-calendar-tbody");
    if (data.upcoming_earnings && data.upcoming_earnings.length > 0) {
      calBody.innerHTML = data.upcoming_earnings.map(item => `
        <tr>
          <td><span class="status-pill" style="font-weight:700;">${item.d_day}</span></td>
          <td><strong>${item.ticker}</strong> <span style="font-size:0.75rem; color:var(--text-muted);">${item.name_ko}</span></td>
          <td><span class="layer-tag ${getLayerShort(item.layer_code)}">${getLayerShort(item.layer_code)}</span></td>
          <td>${item.fiscal_year && item.fiscal_quarter ? `${item.fiscal_year}-${item.fiscal_quarter}` : (item.fiscal_year || '-')}</td>
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
    populateQuarterlyCompanySelect(allEntities);
  } catch (err) {
    console.error("Failed to load entities:", err);
  }
}

function populateQuarterlyCompanySelect(entities) {
  const select = document.getElementById("quarterly-ticker-select");
  if (!select || !entities || entities.length === 0) return;

  const currentVal = select.value || "NVDA";

  const layerOrder = [
    "L3_COMPUTE",
    "L2_HYPERSCALER",
    "L4_FOUNDRY",
    "L5_MEMORY",
    "L6_OPTICAL",
    "L7_INFRA",
    "L8_POWER"
  ];

  const layerNames = {
    "L2_HYPERSCALER": "L2 하이퍼스케일러",
    "L3_COMPUTE": "L3 컴퓨팅 / AI 가속기",
    "L4_FOUNDRY": "L4 파운드리 / 반도체 장비",
    "L5_MEMORY": "L5 메모리 / 스토리지",
    "L6_OPTICAL": "L6 광통신 / 네트워킹",
    "L7_INFRA": "L7 인프라 / 특수",
    "L8_POWER": "L8 전력 / 에너지 인프라"
  };

  const grouped = {};
  entities.forEach(e => {
    const l = e.layer_code || "ETC";
    if (!grouped[l]) grouped[l] = [];
    grouped[l].push(e);
  });

  let html = "";
  layerOrder.forEach(lCode => {
    const list = grouped[lCode];
    if (list && list.length > 0) {
      const label = `${layerNames[lCode] || lCode} (${list.length}개사)`;
      html += `<optgroup label="${label}">`;
      list.forEach(e => {
        const isSel = e.ticker === currentVal ? "selected" : "";
        html += `<option value="${e.ticker}" ${isSel}>${e.ticker} (${e.name_ko})</option>`;
      });
      html += `</optgroup>`;
    }
  });

  select.innerHTML = html;
  if (!select.value) {
    select.value = currentVal;
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
        <td>${item.fiscal_year && item.fiscal_quarter ? `${item.fiscal_year}-${item.fiscal_quarter}` : (item.fiscal_year || '-')}</td>
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
          <td>${f.fiscal_year && f.fiscal_quarter ? `${f.fiscal_year}-${f.fiscal_quarter}` : (f.fiscal_year || '-')}</td>
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
  const ddr5Chip = summary["SPOT_DRAM_DDR5_16GB_CHIP"];
  const ddr4 = summary["SPOT_DRAM_DDR4_8GB"];
  const ddr4Mod = summary["SPOT_DRAM_DDR4_16GB"];
  const dxi = summary["INDEX_DXI"];

  const updateCard = (valId, subId, item, isPoint = false, isDaily = false) => {
    const valEl = document.getElementById(valId);
    const subEl = document.getElementById(subId);
    if (!valEl || !subEl || !item) return;

    if (item.latest_price !== null && item.latest_price !== undefined) {
      valEl.textContent = isPoint ? Number(item.latest_price).toLocaleString() : `$${Number(item.latest_price).toFixed(2)}`;
      const sign = item.change_pct >= 0 ? "▲ +" : "▼ ";
      const color = item.change_pct >= 0 ? "var(--accent-emerald)" : "var(--accent-rose)";
      const term = isDaily ? "(세션 변동)" : "(전주 대비)";
      subEl.textContent = `${sign}${item.change_pct}% ${term}`;
      subEl.style.color = color;
    } else {
      valEl.textContent = "-";
      subEl.textContent = "데이터 없음";
      subEl.style.color = "var(--text-muted)";
    }
  };

  updateCard("val-spot-ddr5", "sub-spot-ddr5", ddr5, false, true);
  updateCard("val-spot-ddr5-chip", "sub-spot-ddr5-chip", ddr5Chip, false, true);
  updateCard("val-spot-ddr4", "sub-spot-ddr4", ddr4, false, true);
  updateCard("val-spot-ddr4-mod", "sub-spot-ddr4-mod", ddr4Mod, false, true);
  updateCard("val-spot-dxi", "sub-spot-dxi", dxi, true, false);
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
    "SPOT_DRAM_DDR5_16GB": "📈 DDR5 16GB 모듈 스팟 현물 가격 추이 (USD)",
    "SPOT_DRAM_DDR5_16GB_CHIP": "📈 DDR5 16Gb eTT 단품 칩 스팟 가격 추이 (USD)",
    "SPOT_DRAM_DDR4_8GB": "📈 DDR4 16Gb eTT 단품 칩 스팟 가격 추이 (USD)",
    "SPOT_DRAM_DDR4_16GB": "📈 DDR4 16GB (3200) 모듈 스팟 가격 추이 (USD)",
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

    // Default select latest quarter for MD&A highlight or reset panel
    if (currentQuarterlySeries.length > 0) {
      selectQuarterRow(0);
    } else {
      const titleEl = document.getElementById("mda-panel-title");
      const periodEl = document.getElementById("mda-panel-period");
      const contentEl = document.getElementById("mda-panel-content");
      const tickerName = (currentQuarterlyEntity && currentQuarterlyEntity.name_ko) || ticker;
      if (titleEl) titleEl.innerHTML = `🎙️ ${tickerName} (${ticker}) 경영진 실적 분석 (MD&A)`;
      if (periodEl) periodEl.textContent = "데이터 없음";
      if (contentEl) contentEl.textContent = `현재 ${tickerName} (${ticker})의 수집된 분기 실적 및 MD&A 분석 정보가 없습니다. 상단 '🔄 2020~ 실적 시드 로드'를 통해 대표 기업 시계열을 동기화하세요.`;
    }
  } catch (err) {
    console.error(`Failed to load quarterly financials for ${ticker}:`, err);
  }
}

function renderQuarterlySummary(series, entity) {
  const revEl = document.getElementById("kpi-q-rev");
  const revSubEl = document.getElementById("kpi-q-rev-sub");
  const opmEl = document.getElementById("kpi-q-opm");
  const opIncEl = document.getElementById("kpi-q-op-inc");
  const dcRatioEl = document.getElementById("kpi-q-dc-ratio");
  const dcAmtEl = document.getElementById("kpi-q-dc-amt");
  const capexEl = document.getElementById("kpi-q-capex");
  const capexSubEl = document.getElementById("kpi-q-capex-sub");

  if (!series || series.length === 0) {
    if (revEl) revEl.textContent = "-";
    if (revSubEl) { revSubEl.textContent = "실적 데이터 없음"; revSubEl.style.color = "var(--text-muted)"; }
    if (opmEl) opmEl.textContent = "-";
    if (opIncEl) opIncEl.textContent = "영업이익 -";
    if (dcRatioEl) dcRatioEl.textContent = "-";
    if (dcAmtEl) dcAmtEl.textContent = "부문 매출 -";
    if (capexEl) capexEl.textContent = "-";
    if (capexSubEl) capexSubEl.textContent = "설비투자액 -";
    return;
  }

  const latest = series[0];

  if (revEl && latest.revenue !== undefined) {
    revEl.textContent = `$${(latest.revenue / 1000).toFixed(1)}B`;
  }
  if (revSubEl) {
    const periodStr = latest.period || latest.period_key || (latest.fiscal_year ? `${latest.fiscal_year}-${latest.fiscal_quarter}` : "");
    const yoy = latest.revenue_yoy_pct;
    if (yoy !== null && yoy !== undefined) {
      revSubEl.textContent = `YoY ${yoy > 0 ? '+' : ''}${yoy.toFixed(1)}% (${periodStr})`;
      revSubEl.style.color = yoy >= 0 ? "var(--accent-emerald)" : "var(--accent-rose)";
    } else {
      revSubEl.textContent = `${periodStr} 기준`;
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
    const periodStr = latest.period || latest.period_key || (latest.fiscal_year ? `${latest.fiscal_year}-${latest.fiscal_quarter}` : "");
    capexSubEl.textContent = `설비투자액 (${periodStr})`;
  }
}

function renderQuarterlyChart(series, ticker) {
  const ctx = document.getElementById("quarterly-financial-chart");
  if (!ctx) return;
  if (quarterlyChart) quarterlyChart.destroy();

  if (!series || series.length === 0) return;

  const chronological = [...series].reverse();
  const labels = chronological.map(d => d.period || d.period_key || `${d.fiscal_year}-${d.fiscal_quarter}`);
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
  const labels = chronological.map(d => d.period || d.period_key || `${d.fiscal_year}-${d.fiscal_quarter}`);
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
    const curTicker = (currentQuarterlyEntity && currentQuarterlyEntity.ticker) || "해당 기업";
    const curName = (currentQuarterlyEntity && currentQuarterlyEntity.name_ko) || curTicker;
    tbody.innerHTML = `
      <tr>
        <td colspan="10" style="text-align: center; color: var(--text-muted); padding: 3rem 1.5rem;">
          <div style="font-size: 1.05rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem;">
            📊 ${curName} (${curTicker})의 수집된 분기 실적이 아직 없습니다.
          </div>
          <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1.2rem;">
            상단 '🔄 2020~ 실적 시드 로드' 버튼을 누르시면 대표 기업들의 벤치마크 재무 데이터가 일괄 적재됩니다.
          </p>
          <button class="btn" style="background: var(--accent-cyan); color: #0f172a; font-weight: 700; padding: 0.45rem 1.2rem; font-size: 0.85rem;" onclick="seedQuarterlyFinancialsData()">
            ⚡ 전체 기업 실적 시드 동기화
          </button>
        </td>
      </tr>`;
    return;
  }

  tbody.innerHTML = series.map((row, idx) => {
    const periodLabel = row.period || row.period_key || (row.fiscal_year ? `${row.fiscal_year}-${row.fiscal_quarter}` : '-');
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

    const origRevNote = row.original_revenue_str
      ? `<div style="font-size:0.75rem; font-weight:400; color:var(--text-muted); margin-top:0.15rem;">${row.original_revenue_str}</div>`
      : "";

    const fxBadge = row.original_currency && row.original_currency !== 'USD'
      ? `<span class="filing-badge" style="background: rgba(56, 189, 248, 0.12); color: var(--accent-cyan); border: 1px solid rgba(56, 189, 248, 0.3); font-size: 0.73rem; padding: 0.2rem 0.45rem;">${row.fx_rate_label || row.original_currency}</span>`
      : `<span style="color: var(--text-muted); font-size: 0.75rem;">1.0 (USD)</span>`;

    return `
      <tr onclick="selectQuarterRow(${idx})" style="cursor: pointer;" id="quarter-row-${idx}">
        <td><strong>${periodLabel}</strong></td>
        <td><span class="filing-badge filing-${row.filing_type || '10-Q'}">${row.filing_type || '10-Q'}</span></td>
        <td style="color: var(--text-muted); font-size: 0.8rem; text-align: center;">${row.report_date || row.filed_date || '-'}</td>
        <td style="text-align: right; font-weight: 600;">$${(row.revenue / 1000).toFixed(1)}B ${yoyBadge}${origRevNote}</td>
        <td style="text-align: right; color: var(--accent-cyan);">$${(row.operating_income / 1000).toFixed(1)}B <span style="font-size:0.75rem; color:var(--text-muted);">(${row.op_margin_pct ? row.op_margin_pct.toFixed(1) : '-'}%)</span></td>
        <td style="text-align: right;">$${row.net_income ? (row.net_income / 1000).toFixed(1) + 'B' : '-'}</td>
        <td style="text-align: right; color: #F43F5E;">$${row.capex ? (row.capex / 1000).toFixed(1) + 'B' : '-'}</td>
        <td style="text-align: right;">${dcText}</td>
        <td style="text-align: center;">${fxBadge}</td>
        <td style="text-align: center;">${filingBtn}</td>
      </tr>
    `;
  }).join("");
}

function selectQuarterRow(index) {
  if (!currentQuarterlySeries || !currentQuarterlySeries[index]) return;
  const item = currentQuarterlySeries[index];
  const periodLabel = item.period || item.period_key || (item.fiscal_year ? `${item.fiscal_year}-${item.fiscal_quarter}` : '-');

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
    titleEl.innerHTML = `🎙️ ${ticker} ${periodLabel} (${item.filing_type || '10-Q'}) 경영진 실적 분석 (MD&A) & 주요 코멘트`;
  }
  if (periodEl) {
    periodEl.textContent = `${periodLabel} ${item.filing_type || '10-Q'}`;
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

// ========================================================
// 8. Earnings Call Transcripts Logic
// ========================================================

let allTranscriptsList = [];
let currentTranscriptDetail = null;
let currentTranscriptSection = "all"; // 'all' | 'remarks' | 'qa'

async function loadTranscriptsList() {
  try {
    const res = await fetch("/api/earning-calls?limit=200");
    const json = await res.json();
    if (json.status !== "success") {
      console.error("Failed to load transcripts:", json.message);
      return;
    }

    allTranscriptsList = json.data || [];

    // Update KPI Bar
    const kpiTotal = document.getElementById("transcript-kpi-total");
    const kpiCompanies = document.getElementById("transcript-kpi-companies");
    const kpiLatest = document.getElementById("transcript-kpi-latest");

    if (kpiTotal) kpiTotal.textContent = `${allTranscriptsList.length}건`;
    if (kpiCompanies) {
      const uniqueTickers = new Set(allTranscriptsList.map(t => t.ticker));
      kpiCompanies.textContent = `${uniqueTickers.size}개사`;
    }
    if (kpiLatest) {
      if (allTranscriptsList.length > 0) {
        kpiLatest.textContent = allTranscriptsList[0].call_date || "-";
      } else {
        kpiLatest.textContent = "-";
      }
    }

    populateTranscriptFilterOptions();
    filterTranscriptsList();

    // Auto-select first transcript if available and none currently selected
    if (allTranscriptsList.length > 0 && !currentTranscriptDetail) {
      const firstId = allTranscriptsList[0].id;
      selectTranscript(firstId);
    }
  } catch (err) {
    console.error("Error loading transcripts list:", err);
  }
}

function populateTranscriptFilterOptions() {
  const select = document.getElementById("transcript-filter-ticker");
  if (!select) return;

  const currentVal = select.value;
  const companyMap = new Map();
  for (const item of allTranscriptsList) {
    if (!companyMap.has(item.ticker)) {
      companyMap.set(item.ticker, {
        ticker: item.ticker,
        name: item.name_ko || item.name_en || item.ticker,
        layer: item.layer_code || "ETC",
        count: 1
      });
    } else {
      companyMap.get(item.ticker).count += 1;
    }
  }

  let html = `<option value="">전체 기업 보기 (${allTranscriptsList.length}건 / ${companyMap.size}개사)</option>`;

  const layerNames = {
    "L2_HYPERSCALER": "L2 하이퍼스케일러 / 빅테크",
    "L3_COMPUTE": "L3 컴퓨팅 / AI 가속기",
    "L4_FOUNDRY": "L4 파운드리 / 반도체 장비",
    "L5_MEMORY": "L5 메모리 / 스토리지",
    "L6_OPTICAL": "L6 광통신 / AI 네트워킹",
    "L7_INFRA": "L7 서버 / 랙 인프라",
    "L8_POWER": "L8 전력 / 에너지 인프라",
  };

  const sortedCompanies = Array.from(companyMap.values()).sort((a, b) => {
    if (a.layer !== b.layer) return a.layer.localeCompare(b.layer);
    return a.ticker.localeCompare(b.ticker);
  });

  let currentLayer = null;
  for (const comp of sortedCompanies) {
    if (comp.layer !== currentLayer) {
      if (currentLayer !== null) html += `</optgroup>`;
      currentLayer = comp.layer;
      const groupLabel = layerNames[currentLayer] || currentLayer;
      html += `<optgroup label="${groupLabel}">`;
    }
    const selected = comp.ticker === currentVal ? "selected" : "";
    html += `<option value="${comp.ticker}" ${selected}>${comp.ticker} — ${comp.name} (${comp.count}건)</option>`;
  }
  if (currentLayer !== null) html += `</optgroup>`;

  select.innerHTML = html;
  if (currentVal) select.value = currentVal;
}

function filterTranscriptsList() {
  const tickerFilter = (document.getElementById("transcript-filter-ticker")?.value || "").toUpperCase().trim();
  const searchInput = (document.getElementById("transcript-search-input")?.value || "").toLowerCase().trim();

  const filtered = allTranscriptsList.filter(item => {
    if (tickerFilter && item.ticker !== tickerFilter) return false;
    if (searchInput) {
      const matchTicker = (item.ticker || "").toLowerCase().includes(searchInput);
      const matchName = (item.name_ko || item.name_en || "").toLowerCase().includes(searchInput);
      const matchPreview = (item.preview_text || "").toLowerCase().includes(searchInput);
      const matchPeriod = `${item.fiscal_year || ""} ${item.fiscal_quarter || ""}`.toLowerCase().includes(searchInput);
      if (!matchTicker && !matchName && !matchPreview && !matchPeriod) return false;
    }
    return true;
  });

  renderTranscriptsList(filtered);
}

function renderTranscriptsList(items) {
  const container = document.getElementById("transcript-cards-list");
  if (!container) return;

  if (items.length === 0) {
    container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 3rem 1rem;">일치하는 어닝콜 트랜스크립트가 없습니다.</div>`;
    return;
  }

  container.innerHTML = items.map(item => {
    const isSelected = currentTranscriptDetail && currentTranscriptDetail.id === item.id;
    const activeClass = isSelected ? "active" : "";
    const periodBadge = `${item.fiscal_year}-${item.fiscal_quarter}`;
    const wordCount = item.word_count ? `${item.word_count.toLocaleString()}단어` : (item.char_count ? `${item.char_count.toLocaleString()}자` : '');
    const cleanName = item.name_ko || item.name_en || item.ticker;

    return `
      <div class="transcript-card ${activeClass}" id="transcript-card-${item.id}" onclick="selectTranscript(${item.id})">
        <div class="transcript-card-meta">
          <div class="transcript-company-title">
            <span class="filing-badge" style="font-size:0.75rem; background:rgba(99,102,241,0.15); color:#A5B4FC;">${item.ticker}</span>
            <span>${cleanName}</span>
          </div>
          <span class="status-pill" style="font-size:0.72rem; padding:0.1rem 0.45rem;">${periodBadge}</span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.75rem; color:var(--text-muted); margin-top:0.25rem;">
          <span>📅 ${item.call_date || '-'}</span>
          <span>✍️ ${wordCount}</span>
        </div>
        <div class="transcript-preview-text">${item.preview_text || ''}</div>
      </div>
    `;
  }).join("");
}

async function selectTranscript(callId) {
  // Update active visual state
  document.querySelectorAll(".transcript-card").forEach(el => el.classList.remove("active"));
  const activeCard = document.getElementById(`transcript-card-${callId}`);
  if (activeCard) activeCard.classList.add("active");

  try {
    const res = await fetch(`/api/earning-calls/${callId}`);
    const json = await res.json();
    if (json.status !== "success") {
      console.error("Failed to load transcript detail:", json.message);
      return;
    }

    currentTranscriptDetail = json.data;

    // Update Reader Header
    const badgeEl = document.getElementById("reader-company-badge");
    const titleEl = document.getElementById("reader-title");
    const dateEl = document.getElementById("reader-date");
    const wordsEl = document.getElementById("reader-words");
    const linkEl = document.getElementById("reader-source-link");

    if (badgeEl) badgeEl.textContent = currentTranscriptDetail.ticker;
    if (titleEl) {
      const coName = currentTranscriptDetail.name_ko || currentTranscriptDetail.name_en || currentTranscriptDetail.ticker;
      titleEl.textContent = `${coName} (${currentTranscriptDetail.ticker}) ${currentTranscriptDetail.fiscal_year}-${currentTranscriptDetail.fiscal_quarter} 실적발표 컨퍼런스 콜`;
    }
    if (dateEl) dateEl.textContent = `📅 ${currentTranscriptDetail.call_date || '-'}`;
    if (wordsEl) {
      const len = currentTranscriptDetail.char_count || (currentTranscriptDetail.transcript_text ? currentTranscriptDetail.transcript_text.length : 0);
      wordsEl.textContent = `총 ${len.toLocaleString()}자`;
    }
    if (linkEl) {
      if (currentTranscriptDetail.source_url) {
        linkEl.href = currentTranscriptDetail.source_url;
        linkEl.style.display = "inline-flex";
      } else {
        linkEl.style.display = "none";
      }
    }

    renderTranscriptContent();
  } catch (err) {
    console.error("Error fetching transcript detail:", err);
  }
}

function setTranscriptSectionView(section) {
  currentTranscriptSection = section;

  document.querySelectorAll("#transcript-section-pills .layer-pill").forEach(btn => btn.classList.remove("active"));
  const activeBtn = document.getElementById(`pill-section-${section}`);
  if (activeBtn) activeBtn.classList.add("active");

  renderTranscriptContent();
}

function renderTranscriptContent() {
  const container = document.getElementById("transcript-reader-body");
  if (!container || !currentTranscriptDetail) return;

  const sections = currentTranscriptDetail.sections || {};
  const remarks = sections.prepared_remarks || currentTranscriptDetail.prepared_remarks || "";
  const qa = sections.qa_session || currentTranscriptDetail.qa_session || "";
  const fullText = currentTranscriptDetail.transcript_text || "";

  let html = "";

  if (currentTranscriptSection === "remarks") {
    if (!remarks) {
      html = `<div style="text-align:center; color:var(--text-muted); padding:3rem;">경영진 발표문 섹션을 감지하지 못했습니다. 전체 보기를 이용해주세요.</div>`;
    } else {
      html = `
        <div class="section-divider-banner">
          <span>🎙️</span> 경영진 발표문 (Executive Prepared Remarks)
        </div>
        ${formatTranscriptParagraphs(remarks)}
      `;
    }
  } else if (currentTranscriptSection === "qa") {
    if (!qa) {
      html = `<div style="text-align:center; color:var(--text-muted); padding:3rem;">애널리스트 Q&A 질의응답 세션을 감지하지 못했습니다. 전체 보기를 이용해주세요.</div>`;
    } else {
      html = `
        <div class="section-divider-banner" style="border-left-color: #8B5CF6; background: linear-gradient(90deg, rgba(139,92,246,0.22), transparent);">
          <span>💬</span> 월가 애널리스트 질의응답 세션 (Q&A Session)
        </div>
        ${formatTranscriptParagraphs(qa)}
      `;
    }
  } else {
    // "all"
    if (remarks && qa) {
      html = `
        <div class="section-divider-banner">
          <span>🎙️</span> 제 1부: 경영진 공식 발표문 (Prepared Remarks)
        </div>
        ${formatTranscriptParagraphs(remarks)}
        <div class="section-divider-banner" style="border-left-color: #8B5CF6; background: linear-gradient(90deg, rgba(139,92,246,0.22), transparent);">
          <span>💬</span> 제 2부: 월가 애널리스트 질의응답 세션 (Q&A Session)
        </div>
        ${formatTranscriptParagraphs(qa)}
      `;
    } else {
      html = formatTranscriptParagraphs(fullText);
    }
  }

  container.innerHTML = html;
}

function formatTranscriptParagraphs(rawText) {
  if (!rawText) return "";

  const lines = rawText.split("\n");
  let outputHtml = "";
  let currentBlock = [];

  const flushBlock = () => {
    if (currentBlock.length > 0) {
      const paragraph = currentBlock.join("<br>").trim();
      if (paragraph) {
        outputHtml += `<div class="transcript-speech-block">${paragraph}</div>`;
      }
      currentBlock = [];
    }
  };

  for (let line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      flushBlock();
      continue;
    }

    // Check if line looks like a speaker introduction
    const isExecutive = /CEO|CFO|COO|President|Executive|VP|Vice President|Head of|대표이사|사장|부사장/i.test(trimmed);
    const isAnalyst = /Analyst|Securities|Research|Capital|Goldman|Morgan|Bernstein|JPMorgan|Bank of America|UBS|Citi|Barclays|애널리스트|연구원|증권/i.test(trimmed);
    const isOperator = /Operator|사회자|진행자/i.test(trimmed);

    const isSpeakerLine = (trimmed.length < 120 && (trimmed.endsWith(":") || trimmed.includes(" -- ") || trimmed.includes(" - "))) &&
      (isExecutive || isAnalyst || isOperator || /^[A-Z][a-z]+ [A-Z][a-z]+/.test(trimmed));

    if (isSpeakerLine) {
      flushBlock();

      let badgeHtml = "";
      if (isExecutive) {
        badgeHtml = `<span class="speaker-badge-exec">👔 Executive</span>`;
      } else if (isAnalyst) {
        badgeHtml = `<span class="speaker-badge-analyst">📊 Wall Street Analyst</span>`;
      } else if (isOperator) {
        badgeHtml = `<span class="status-pill" style="font-size:0.7rem;">🎙️ Conference Host</span>`;
      }

      outputHtml += `
        <div class="transcript-speaker-row" style="margin-top: 1.2rem;">
          <strong style="color: #fff; font-size: 0.96rem;">${escapeHtml(trimmed)}</strong>
          ${badgeHtml}
        </div>
      `;
    } else {
      currentBlock.push(escapeHtml(trimmed));
    }
  }

  flushBlock();
  return outputHtml;
}

function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return text.replace(/[&<>"']/g, m => map[m]);
}

async function openTranscriptUploadModal() {
  const dateInput = document.getElementById("upload-transcript-date");
  if (dateInput && !dateInput.value) {
    dateInput.value = new Date().toISOString().split("T")[0];
  }

  // Populate upload ticker select from entities if not yet populated
  const sel = document.getElementById("upload-transcript-ticker");
  if (sel && sel.options.length <= 15) {
    try {
      const res = await fetch("/api/entities");
      const json = await res.json();
      if (json.status === "success" && json.data) {
        const currentVal = sel.value;
        const layerNames = {
          "L2_HYPERSCALER": "L2 하이퍼스케일러 / 빅테크",
          "L3_COMPUTE": "L3 컴퓨팅 / AI 가속기",
          "L4_FOUNDRY": "L4 파운드리 / 반도체 장비",
          "L5_MEMORY": "L5 메모리 / 스토리지",
          "L6_OPTICAL": "L6 광통신 / AI 네트워킹",
          "L7_INFRA": "L7 서버 / 랙 인프라",
          "L8_POWER": "L8 전력 / 에너지 인프라",
        };

        const grouped = {};
        for (const e of json.data) {
          const l = e.layer_code || "ETC";
          if (!grouped[l]) grouped[l] = [];
          grouped[l].push(e);
        }

        let html = "";
        for (const [l, ents] of Object.entries(grouped)) {
          html += `<optgroup label="${layerNames[l] || l}">`;
          for (const ent of ents) {
            const isSel = ent.ticker === currentVal ? "selected" : "";
            html += `<option value="${ent.ticker}" ${isSel}>${ent.ticker} — ${ent.name_ko} (${ent.name_en})</option>`;
          }
          html += `</optgroup>`;
        }
        sel.innerHTML = html;
        if (currentVal) sel.value = currentVal;
      }
    } catch (e) {
      console.warn("Could not load entities for upload dropdown:", e);
    }
  }

  const modal = document.getElementById("transcript-upload-modal");
  if (modal) modal.classList.add("active");
}

async function submitTranscriptUpload(e) {
  e.preventDefault();

  const ticker = document.getElementById("upload-transcript-ticker").value;
  const fy = parseInt(document.getElementById("upload-transcript-fy").value, 10);
  const fq = document.getElementById("upload-transcript-fq").value;
  const callDate = document.getElementById("upload-transcript-date").value;
  const sourceUrl = document.getElementById("upload-transcript-url").value.trim();
  const transcriptText = document.getElementById("upload-transcript-text").value.trim();

  if (!ticker || !fy || !fq || !callDate || !transcriptText) {
    alert("필수 입력 항목을 모두 채워주세요.");
    return;
  }

  try {
    const res = await fetch("/api/earning-calls", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ticker,
        fiscal_year: fy,
        fiscal_quarter: fq,
        call_date: callDate,
        source_url: sourceUrl || null,
        transcript_text: transcriptText
      })
    });

    const json = await res.json();
    if (json.status === "success") {
      alert(`✅ 어닝콜 트랜스크립트가 성공적으로 등록되었습니다! (ID: ${json.call_id}, ${json.char_count.toLocaleString()}자)`);
      closeModal("transcript-upload-modal");
      document.getElementById("transcript-upload-form").reset();
      await loadTranscriptsList();
      selectTranscript(json.call_id);
    } else {
      alert(`등록 실패: ${json.message}`);
    }
  } catch (err) {
    alert(`통신 오류: ${err.message}`);
  }
}

async function seedTranscriptsData() {
  try {
    const res = await fetch("/api/earning-calls/seed", { method: "POST" });
    const json = await res.json();
    if (json.status === "success") {
      alert(`✅ 어닝콜 샘플 트랜스크립트(${json.seeded_count}건)가 적재되었습니다!`);
      loadTranscriptsList();
    } else {
      alert(`실패: ${json.message}`);
    }
  } catch (err) {
    alert(`오류: ${err.message}`);
  }
}

// ========================================================
// 9. AI Report Studio & Agent Logic
// ========================================================

let reportTemplates = {};
let selectedPeerTickers = new Set(["000660.KS", "NVDA"]);
let currentGeneratedReportMarkdown = "";

const ALL_PEER_CANDIDATES = [
  { ticker: "000660.KS", name: "SK하이닉스" },
  { ticker: "NVDA", name: "엔비디아" },
  { ticker: "TSM", name: "TSMC" },
  { ticker: "005930.KS", name: "삼성전자" },
  { ticker: "MSFT", name: "마이크로소프트" },
  { ticker: "AVGO", name: "브로드컴" },
  { ticker: "AMD", name: "AMD" },
  { ticker: "MU", name: "마이크론" },
  { ticker: "ASML", name: "ASML" },
  { ticker: "VRT", name: "버티브" },
  { ticker: "GOOGL", name: "구글" },
  { ticker: "AMZN", name: "아마존" },
  { ticker: "META", name: "메타" }
];

async function loadReportStudio() {
  await checkReportEngineStatus();
  await loadReportTemplates();
  renderPeerChips();
  renderChapterCheckboxes();
}

async function checkReportEngineStatus() {
  try {
    const res = await fetch("/api/reports/engine-status");
    const json = await res.json();
    if (json.status !== "success") return;

    const data = json.data;
    const badge = document.getElementById("report-engine-status-badge");
    const engineSelect = document.getElementById("report-engine-select");

    if (badge && data.gemini && data.gemini.available) {
      badge.innerHTML = `<span class="status-dot"></span><span>Gemini 2.5 Flash 준비 완료</span>`;
      badge.style.color = "var(--accent-emerald)";
      badge.style.borderColor = "rgba(16, 185, 129, 0.3)";
      badge.style.background = "rgba(16, 185, 129, 0.12)";
    }

    if (engineSelect && data.ollama && data.ollama.available) {
      const ollamaOpt = engineSelect.querySelector("option[value='ollama']");
      if (ollamaOpt) {
        ollamaOpt.textContent = `💻 로컬 Ollama 온라인 (${data.ollama.models.length}개 모델 감지)`;
      }
    }
  } catch (err) {
    console.warn("Could not fetch engine status:", err);
  }
}

async function loadReportTemplates() {
  try {
    const res = await fetch("/api/reports/templates");
    const json = await res.json();
    if (json.status === "success" && json.templates) {
      reportTemplates = json.templates;
    }
  } catch (err) {
    console.warn("Could not fetch templates:", err);
  }
}

function renderPeerChips() {
  const container = document.getElementById("report-peer-chips-container");
  if (!container) return;

  const targetTicker = document.getElementById("report-target-ticker")?.value || "";

  container.innerHTML = ALL_PEER_CANDIDATES.map(p => {
    if (p.ticker === targetTicker) return "";
    const isActive = selectedPeerTickers.has(p.ticker);
    return `
      <div class="peer-chip ${isActive ? 'active' : ''}" onclick="togglePeerChip('${p.ticker}')">
        <span>${isActive ? '✓' : '+'}</span>
        <span>${p.ticker}</span>
        <span style="font-size:0.7rem; color:var(--text-muted);">${p.name}</span>
      </div>
    `;
  }).join("");
}

function togglePeerChip(ticker) {
  if (selectedPeerTickers.has(ticker)) {
    selectedPeerTickers.delete(ticker);
  } else {
    selectedPeerTickers.add(ticker);
  }
  renderPeerChips();
}

function handleTemplateSelectChange(templateKey) {
  renderChapterCheckboxes(templateKey);
}

function renderChapterCheckboxes(templateKey = "cross_chain") {
  const container = document.getElementById("report-chapters-container");
  if (!container) return;

  const tpl = reportTemplates[templateKey] || {
    chapters: [
      "1. Executive Summary (핵심 결론 및 시사점 3줄 요약)",
      "2. 대상 기업 최근 실적 분석 (매출액, 영업이익, 영업이익률, CapEx 확정치 테이블)",
      "3. 밸류체인 전·후방 기업과의 교차 대조 (경쟁사 점유율 및 고객사 수요)",
      "4. 어닝콜 경영진 발언 및 시장 핵심 의구심(Q&A) 검증",
      "5. 산업 선행지표(TSMC 월매출, 메모리 현물가, 수출통계, GPU 렌탈가) 연계 시그널",
      "6. 향후 실적 전망 및 리스크 요인"
    ]
  };

  container.innerHTML = tpl.chapters.map((ch, idx) => `
    <label class="chapter-checkbox-row">
      <input type="checkbox" class="report-chapter-cb" value="${ch}" checked style="accent-color: var(--accent-primary);">
      <span>${ch}</span>
    </label>
  `).join("");
}

function handleEngineChange(engineVal) {
  const pill = document.getElementById("report-viewer-engine-pill");
  if (!pill) return;
  const labels = {
    "gemini:gemini-2.5-flash": "Gemini 2.5 Flash",
    "gemini:gemini-3.8-flash": "Gemini 3.8 Flash",
    "opencode:opencode/muse-spark-1.3-contributor-free": "Muse Spark 1.3",
    "opencode:opencode/muse-spark-1.2-contributor-free": "Muse Spark 1.2",
    "opencode:opencode/nemotron-3.5-lightning-free": "Nemotron 3.5",
    "opencode:opencode/ling-3.0-flash-fin-free": "Ling 3.0 Financial",
    "ollama:qwen2.5:7b": "Qwen 2.5 (Ollama)"
  };
  pill.textContent = labels[engineVal] || engineVal;
}

async function submitGenerateReport() {
  const targetTicker = document.getElementById("report-target-ticker")?.value || "005930.KS";
  const peerTickers = Array.from(selectedPeerTickers);

  const chapterCheckboxes = document.querySelectorAll(".report-chapter-cb:checked");
  const chapters = Array.from(chapterCheckboxes).map(cb => cb.value);

  if (chapters.length === 0) {
    alert("최소 1개 이상의 목차 챕터를 선택해 주세요.");
    return;
  }

  const toneStyle = document.getElementById("report-tone-select")?.value || "analyst";
  const timeframe = document.getElementById("report-timeframe-select")?.value || "latest";
  const userNotes = document.getElementById("report-user-notes")?.value || "";
  
  const engineRaw = document.getElementById("report-engine-select")?.value || "gemini:gemini-2.5-flash";
  let engine = "gemini";
  let modelName = "gemini-2.5-flash";
  if (engineRaw.includes(":")) {
    const parts = engineRaw.split(":");
    engine = parts[0];
    modelName = parts.slice(1).join(":");
  } else {
    engine = engineRaw;
  }

  const btn = document.getElementById("btn-generate-report");
  const activityContainer = document.getElementById("report-activity-container");
  const activityPills = document.getElementById("report-activity-pills");
  const contentBody = document.getElementById("report-content-body");
  const viewerBadge = document.getElementById("report-viewer-badge");
  const viewerTitle = document.getElementById("report-viewer-title");

  if (viewerBadge) viewerBadge.textContent = targetTicker;
  if (viewerTitle) viewerTitle.textContent = `${targetTicker} 교차 심층 분석 보고서`;

  // UI Loading State
  btn.disabled = true;
  btn.innerHTML = `<span class="status-dot" style="background:#fff;"></span> 에이전트 팩트 데이터 탐색 중...`;

  if (activityContainer) activityContainer.style.display = "block";
  if (activityPills) {
    activityPills.innerHTML = `
      <div class="report-activity-pill"><span>🔍</span><span>${targetTicker} 및 피어 그룹 데이터 분석 착수...</span></div>
    `;
  }

  contentBody.innerHTML = `
    <div style="text-align: center; color: var(--text-secondary); padding: 5rem 1rem;">
      <div style="font-size: 2.2rem; margin-bottom: 1rem; animation: pulse 1.5s infinite;">🧠</div>
      <h4 style="color: #fff; margin-bottom: 0.5rem;">AI 에이전트가 데이터베이스를 직접 조회하고 있습니다...</h4>
      <p style="font-size: 0.85rem; color: var(--text-muted);">재무제표 팩트 테이블 확인 · 타사 어닝콜 Q&A 발언 추출 · 선행지표 연계 추론 중</p>
    </div>
  `;

  try {
    const res = await fetch("/api/reports/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target_ticker: targetTicker,
        peer_tickers: peerTickers,
        chapters: chapters,
        user_notes: userNotes,
        timeframe: timeframe,
        tone_style: toneStyle,
        engine: engine,
        model_name: modelName
      })
    });

    const json = await res.json();

    if (json.status !== "success") {
      throw new Error(json.message || "보고서 생성 실패");
    }

    currentGeneratedReportMarkdown = json.report_markdown || "";

    // Render Activity Log Pills
    if (activityPills && json.tools_used) {
      activityPills.innerHTML = json.tools_used.map(t => {
        let icon = "🔍";
        if (t.tool.includes("financial")) icon = "📊";
        if (t.tool.includes("transcript")) icon = "🎙️";
        if (t.tool.includes("indicator")) icon = "🌐";
        if (t.tool.includes("consensus")) icon = "🎯";
        return `
          <div class="report-activity-pill">
            <span>${icon}</span>
            <span>${t.summary || t.tool}</span>
            <span style="color:var(--accent-emerald); font-weight:700;">✓</span>
          </div>
        `;
      }).join("") + `<div class="report-activity-pill" style="background:rgba(16,185,129,0.15); color:var(--accent-emerald); border-color:rgba(16,185,129,0.4);"><span>✍️</span><span>보고서 작성 완료</span></div>`;
    }

    // Render Formatted Markdown
    contentBody.innerHTML = renderMarkdownToHtml(currentGeneratedReportMarkdown);

  } catch (err) {
    alert(`보고서 생성 오류: ${err.message}`);
    contentBody.innerHTML = `
      <div style="text-align: center; color: var(--accent-rose); padding: 4rem;">
        <h4>❌ 생성 중 오류가 발생했습니다.</h4>
        <p style="font-size: 0.85rem; margin-top: 0.5rem;">${err.message}</p>
      </div>
    `;
  } finally {
    btn.disabled = false;
    btn.innerHTML = `🚀 맞춤형 교차 보고서 생성`;
  }
}

function renderMarkdownToHtml(md) {
  if (!md) return "";

  let html = md
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Headers
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

  // Blockquotes
  html = html.replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>');

  // Bold & Italic
  html = html.replace(/\*\*\*(.*?)\*\*\*/gim, '<strong><em>$1</em></strong>');
  html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
  html = html.replace(/\*(.*?)\*/gim, '<em>$1</em>');

  // Horizontal rules
  html = html.replace(/^---$/gim, '<hr style="border:none; border-top:1px solid rgba(255,255,255,0.1); margin:1.5rem 0;">');

  // Tables
  const lines = html.split("\n");
  let inTable = false;
  let tableHtml = "";
  let newLines = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line.startsWith("|") && line.endsWith("|")) {
      if (!inTable) {
        inTable = true;
        tableHtml = "<table>";
      }
      const cells = line.split("|").slice(1, -1);
      if (line.includes("---")) {
        continue;
      }
      const isHeader = !tableHtml.includes("<tbody>") && !tableHtml.includes("<tr>");
      const tag = isHeader ? "th" : "td";
      tableHtml += "<tr>" + cells.map(c => `<${tag}>${c.trim()}</${tag}>`).join("") + "</tr>";
    } else {
      if (inTable) {
        tableHtml += "</table>";
        newLines.push(tableHtml);
        inTable = false;
      }
      newLines.push(line);
    }
  }
  if (inTable) {
    tableHtml += "</table>";
    newLines.push(tableHtml);
  }

  html = newLines.join("\n");

  // Lists
  html = html.replace(/^\- (.*$)/gim, '<li>$1</li>');
  html = html.replace(/^(\d+)\. (.*$)/gim, '<li><strong>$1.</strong> $2</li>');
  html = html.replace(/(<li>.*<\/li>)/gim, '<ul>$1</ul>');
  html = html.replace(/<\/ul>\s*<ul>/gim, '');

  // Paragraphs
  html = html.split("\n\n").map(para => {
    const trimmed = para.trim();
    if (!trimmed) return "";
    if (trimmed.startsWith("<h") || trimmed.startsWith("<table") || trimmed.startsWith("<ul") || trimmed.startsWith("<block") || trimmed.startsWith("<hr")) {
      return trimmed;
    }
    return `<p>${trimmed.replace(/\n/g, "<br>")}</p>`;
  }).join("\n");

  return html;
}

function copyReportMarkdown() {
  if (!currentGeneratedReportMarkdown) {
    alert("복사할 생성된 보고서가 없습니다.");
    return;
  }
  navigator.clipboard.writeText(currentGeneratedReportMarkdown).then(() => {
    alert("✅ 보고서 원문 마크다운이 클립보드에 복사되었습니다!");
  }).catch(err => {
    alert("클립보드 복사 실패: " + err.message);
  });
}

function downloadReportMarkdown() {
  if (!currentGeneratedReportMarkdown) {
    alert("다운로드할 생성된 보고서가 없습니다.");
    return;
  }
  const targetTicker = document.getElementById("report-target-ticker")?.value || "REPORT";
  const dateStr = new Date().toISOString().split("T")[0];
  const filename = `${targetTicker}_AI_Cross_Analysis_${dateStr}.md`;

  const blob = new Blob([currentGeneratedReportMarkdown], { type: "text/markdown;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ─── 13. GPU Cloud Rental Spot Prices (H100/H200/B200/A100) ───
let gpuRentalChart = null;
let currentGpuModel = "H100";
let cachedGpuProviders = [];

async function loadGpuRentalData() {
  try {
    const res = await fetch("/api/gpu/prices");
    const json = await res.json();
    if (json.status !== "success") return;

    const kpis = json.kpis || {};
    cachedGpuProviders = json.providers || [];

    // Update KPI Cards
    updateGpuCard("h100", kpis.H100);
    updateGpuCard("h200", kpis.H200);
    updateGpuCard("b200", kpis.B200);
    updateGpuCard("a100", kpis.A100);

    // Render Table
    renderGpuProviderTable(cachedGpuProviders, currentGpuModel);

    // Render Chart
    await renderGpuRentalChart(currentGpuModel);
  } catch (err) {
    console.error("Error loading GPU rental data:", err);
  }
}

function updateGpuCard(prefix, kpi) {
  if (!kpi) return;
  const valEl = document.getElementById(`val-gpu-${prefix}`);
  const subEl = document.getElementById(`sub-gpu-${prefix}`);
  if (valEl) {
    valEl.innerHTML = `$${kpi.current_price.toFixed(2)}<span style="font-size: 0.75rem; font-weight: normal; color: var(--text-muted);">/hr</span>`;
  }
  if (subEl) {
    const sign = kpi.pct_30d > 0 ? "▲ +" : (kpi.pct_30d < 0 ? "▼ " : "");
    const color = kpi.pct_30d > 0 ? "var(--accent-emerald)" : (kpi.pct_30d < 0 ? "var(--accent-cyan)" : "var(--text-muted)");
    subEl.style.color = color;
    subEl.textContent = `30일 변동: ${sign}${kpi.pct_30d}%`;
  }
}

function renderGpuProviderTable(providers, filterModel = "H100") {
  const tbody = document.getElementById("gpu-providers-tbody");
  if (!tbody) return;

  const filtered = (filterModel === "ALL")
    ? providers
    : providers.filter(p => p.model_key === filterModel);

  if (!filtered.length) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">해당 모델에 대한 호가 데이터가 없습니다.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(p => {
    const availTag = p.availability === "HIGH"
      ? `<span class="layer-tag L2" style="background: rgba(16, 185, 129, 0.2); color: var(--accent-emerald);">즉시 대여가능</span>`
      : (p.availability === "MEDIUM"
        ? `<span class="layer-tag L4" style="background: rgba(245, 158, 11, 0.2); color: var(--accent-amber);">제한적 가용</span>`
        : `<span class="layer-tag L5" style="background: rgba(99, 102, 241, 0.2); color: var(--accent-indigo);">예약/할당제</span>`);

    return `
      <tr>
        <td style="font-weight: 700; color: #fff;">${p.provider}</td>
        <td><span class="layer-tag L3">${p.gpu_model}</span></td>
        <td style="font-weight: 700; color: var(--accent-cyan);">$${p.spot_price.toFixed(2)}/hr</td>
        <td style="color: var(--text-secondary);">$${p.ondemand_price.toFixed(2)}/hr</td>
        <td style="font-size: 0.78rem; color: var(--text-muted);">${p.interconnect}</td>
        <td>${availTag}</td>
        <td style="font-size: 0.78rem; color: var(--text-muted);">${p.region}</td>
        <td style="font-size: 0.75rem; color: var(--text-muted);">${p.updated_at}</td>
      </tr>
    `;
  }).join("");
}

function filterProviderTable(filterVal) {
  renderGpuProviderTable(cachedGpuProviders, filterVal);
}

async function switchGpuModel(modelKey) {
  currentGpuModel = modelKey.toUpperCase();

  // Highlight pill
  document.querySelectorAll("#gpu-model-selector .layer-pill").forEach(p => p.classList.remove("active"));
  const activePill = document.getElementById(`pill-gpu-${currentGpuModel.toLowerCase()}`);
  if (activePill) activePill.classList.add("active");

  // Highlight KPI card
  document.querySelectorAll("#gpu-kpi-grid .kpi-card").forEach(c => {
    c.classList.remove("active");
    c.style.borderColor = "var(--border-glass)";
  });
  const activeCard = document.getElementById(`card-gpu-${currentGpuModel.toLowerCase()}`);
  if (activeCard) {
    activeCard.classList.add("active");
    activeCard.style.borderColor = "var(--accent-cyan)";
  }

  // Update title
  const titleEl = document.getElementById("gpu-chart-title");
  const modelNames = {
    H100: "NVIDIA H100 (SXM5 80GB)",
    H200: "NVIDIA H200 (141GB HBM3e)",
    B200: "NVIDIA B200 (Blackwell NVL)",
    A100: "NVIDIA A100 (SXM4 80GB)"
  };
  if (titleEl) {
    titleEl.innerHTML = `<span>📈</span> ${modelNames[currentGpuModel] || currentGpuModel} 시간당 렌탈 스팟 가격 추이 (USD/hr)`;
  }

  // Update table filter dropdown
  const filterSelect = document.getElementById("gpu-provider-filter");
  if (filterSelect) {
    filterSelect.value = currentGpuModel;
  }
  renderGpuProviderTable(cachedGpuProviders, currentGpuModel);

  // Reload Chart
  await renderGpuRentalChart(currentGpuModel);
}

async function renderGpuRentalChart(modelKey = "H100") {
  const canvas = document.getElementById("gpu-rental-chart");
  if (!canvas) return;

  try {
    const res = await fetch(`/api/gpu/history?model=${modelKey}&limit=50`);
    const json = await res.json();
    if (json.status !== "success") return;

    const history = json.history || [];
    const labels = history.map(h => h.date);
    const prices = history.map(h => h.value);
    const notes = history.map(h => h.note || "");

    const colors = {
      H100: { line: "#06b6d4", fill: "rgba(6, 182, 212, 0.12)" },
      H200: { line: "#10b981", fill: "rgba(16, 185, 129, 0.12)" },
      B200: { line: "#f59e0b", fill: "rgba(245, 158, 11, 0.12)" },
      A100: { line: "#6366f1", fill: "rgba(99, 102, 241, 0.12)" }
    };
    const c = colors[modelKey] || colors.H100;

    if (gpuRentalChart) {
      gpuRentalChart.destroy();
    }

    const ctx = canvas.getContext("2d");
    gpuRentalChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [{
          label: `${json.name_ko} Spot ($/hr)`,
          data: prices,
          borderColor: c.line,
          backgroundColor: c.fill,
          borderWidth: 2.5,
          tension: 0.25,
          fill: true,
          pointRadius: 4,
          pointHoverRadius: 6,
          pointBackgroundColor: c.line
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: "index",
          intersect: false
        },
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            backgroundColor: "rgba(15, 23, 42, 0.95)",
            titleColor: "#38bdf8",
            bodyColor: "#f1f5f9",
            borderColor: "rgba(255, 255, 255, 0.1)",
            borderWidth: 1,
            padding: 10,
            callbacks: {
              label: function(context) {
                return ` Spot 단가: $${context.parsed.y.toFixed(2)} / hr`;
              },
              afterLabel: function(context) {
                const note = notes[context.dataIndex];
                return note ? ` 📌 ${note}` : "";
              }
            }
          }
        },
        scales: {
          x: {
            grid: {
              color: "rgba(255, 255, 255, 0.04)"
            },
            ticks: {
              color: "#94a3b8",
              font: { size: 11 },
              maxRotation: 45
            }
          },
          y: {
            grid: {
              color: "rgba(255, 255, 255, 0.04)"
            },
            ticks: {
              color: "#94a3b8",
              font: { size: 11 },
              callback: function(value) {
                return "$" + value.toFixed(2);
              }
            }
          }
        }
      }
    });
  } catch (err) {
    console.error("Error rendering GPU rental chart:", err);
  }
}

async function seedGpuRentalData() {
  try {
    const res = await fetch("/api/gpu/seed", { method: "POST" });
    const json = await res.json();
    if (json.status === "success") {
      alert(`✅ GPU 클라우드 렌탈 스팟 시계열 데이터(${json.seeded_count}건)가 데이터베이스에 적재되었습니다!`);
      loadGpuRentalData();
    } else {
      alert(`실패: ${json.message}`);
    }
  } catch (err) {
    alert(`오류: ${err.message}`);
  }
}


