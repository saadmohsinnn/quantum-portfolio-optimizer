/**
 * Quantum Playground - Frontend.
 * Demo mode, Learn More, Hall of Fame, theme (dark default), explainability, backtest, share.
 */

const API = {
  base: "",
  async get(url) {
    const r = await fetch(API.base + url);
    if (!r.ok) throw new Error(await r.text().then((t) => t || r.statusText));
    return r.json();
  },
  async post(url, body) {
    const r = await fetch(API.base + url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.error || r.statusText);
    }
    return r.json();
  },
};

// Tooltips for quantum terms (plain language)
const TOOLTIPS = {
  qubit:
    "A qubit is the basic unit of quantum information. Here, each stock is encoded as one qubit: 1 = hold, 0 = don't hold.",
  superposition:
    "Superposition means the quantum circuit can explore many portfolio combinations at once, instead of trying them one by one.",
  entanglement:
    "Entanglement links qubits so that measuring one affects others. This lets the algorithm capture how stocks move together (correlations).",
  risk: "Risk factor (q): 0 = maximize return only; 1 = minimize risk (volatility). Values in between trade off return vs risk.",
  vqe: "VQE (Variational Quantum Eigensolver) is a real quantum algorithm that finds the best portfolio by minimizing a cost function on a quantum computer.",
};

let marketAssets = [];
let demoMode = true;
let probChart = null;
let convergenceChart = null;
let riskReturnChart = null;
let backtestChart = null;
let lastOptimizeResult = null;
let dataLastUpdated = null;
const STALE_MINUTES = 6;
const AUTO_REFRESH_MS = 5 * 60 * 1000;
let autoRefreshTimer = null;

function $(id) {
  return document.getElementById(id);
}

function show(el) {
  if (el && el.classList) el.classList.remove("hidden");
}
function hide(el) {
  if (el && el.classList) el.classList.add("hidden");
}

function escapeHtml(s) {
  if (s == null) return "";
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

// —— Theme (dark mode default) ——
function initTheme() {
  const stored = localStorage.getItem("theme");
  if (stored === "light") {
    document.documentElement.classList.remove("dark");
  } else {
    document.documentElement.classList.add("dark");
  }
}

function toggleTheme() {
  document.documentElement.classList.toggle("dark");
  localStorage.setItem("theme", document.documentElement.classList.contains("dark") ? "dark" : "light");
}

// —— Tooltips ——
function initTooltips() {
  const popup = $("tooltip-popup");
  if (!popup) return;
  document.querySelectorAll(".tooltip-trigger").forEach((el) => {
    const term = el.getAttribute("data-term");
    const text = TOOLTIPS[term];
    if (!text) return;
    el.addEventListener("mouseenter", (e) => {
      popup.textContent = text;
      popup.classList.remove("hidden");
      positionTooltip(popup, e);
    });
    el.addEventListener("mousemove", (e) => positionTooltip(popup, e));
    el.addEventListener("mouseleave", () => popup.classList.add("hidden"));
  });
}

function positionTooltip(popup, e) {
  const gap = 8;
  let x = e.clientX + gap;
  let y = e.clientY + gap;
  const rect = popup.getBoundingClientRect();
  if (x + rect.width > window.innerWidth) x = e.clientX - rect.width - gap;
  if (y + rect.height > window.innerHeight) y = e.clientY - rect.height - gap;
  popup.style.left = x + "px";
  popup.style.top = y + "px";
}

// —— Data timestamp & auto-refresh ——
function setDataTimestamp(ts) {
  dataLastUpdated = ts || (marketAssets.length && marketAssets[0].lastUpdated ? Math.min(...marketAssets.map((a) => a.lastUpdated)) : null);
  const el = $("data-timestamp");
  const staleEl = $("data-stale");
  if (!el) return;
  if (!dataLastUpdated) {
    el.textContent = "Data as of: —";
    if (staleEl) hide(staleEl);
    return;
  }
  const d = new Date(dataLastUpdated * 1000);
  el.textContent = "Data as of: " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  if (staleEl) {
    const mins = (Date.now() / 1000 - dataLastUpdated) / 60;
    if (mins > STALE_MINUTES) show(staleEl);
    else hide(staleEl);
  }
}

function scheduleAutoRefresh() {
  if (autoRefreshTimer) clearInterval(autoRefreshTimer);
  autoRefreshTimer = setInterval(() => {
    fetchMarket(true);
  }, AUTO_REFRESH_MS);
}

// —— Ticker & assets ——
function renderTicker(assets) {
  const list = $("ticker-list");
  if (!list) return;
  if (!assets || assets.length === 0) {
    list.innerHTML = '<span class="text-slate-500">No data. Click Refresh data.</span>';
    return;
  }
  list.innerHTML = assets
    .map((a) => {
      const up = (a.dayChangePercent || 0) >= 0;
      return `<span class="inline-flex items-center gap-1 text-sm">
        <span class="font-semibold text-blue-600 dark:text-blue-400">${escapeHtml(a.symbol)}</span>
        <span class="font-mono">$${Number(a.currentPrice || 0).toFixed(2)}</span>
        <span class="${up ? "text-emerald-600" : "text-red-600"}">${up ? "+" : ""}${Number(a.dayChangePercent || 0).toFixed(2)}%</span>
      </span>`;
    })
    .join("");
}

function renderAssetCheckboxes(assets) {
  const container = $("asset-checkboxes");
  if (!container) return;
  container.innerHTML = (assets || [])
    .map(
      (a) => `
    <label class="inline-flex items-center gap-1.5 cursor-pointer">
      <input type="checkbox" name="asset" value="${escapeHtml(a.symbol)}" data-name="${escapeHtml(a.name || a.symbol)}" class="rounded accent-blue-500" />
      <span>${escapeHtml(a.symbol)}</span>
    </label>
  `
    )
    .join("");
  container.querySelectorAll("input").forEach((cb) => cb.addEventListener("change", () => updateRunButton()));
}

function getSelectedSymbols() {
  return Array.from(document.querySelectorAll('input[name="asset"]:checked')).map((el) => el.value);
}

function getBudget() {
  const n = parseInt($("budget").value, 10);
  return isNaN(n) ? 2 : Math.max(1, Math.min(6, n));
}

function getRiskFactor() {
  const v = parseInt($("risk").value, 10);
  return (isNaN(v) ? 50 : v) / 100;
}

function updateRunButton() {
  const btn = $("run-optimize");
  const budgetEl = $("budget");
  const selected = getSelectedSymbols();
  btn.disabled = !demoMode && selected.length < 2;
  if (budgetEl) {
    const n = demoMode ? 5 : selected.length;
    budgetEl.max = Math.min(6, Math.max(1, n - 1));
    budgetEl.min = 1;
    const v = parseInt(budgetEl.value, 10);
    if (v >= parseInt(budgetEl.max, 10)) budgetEl.value = budgetEl.max;
  }
}

function updateRiskLabel() {
  const el = $("risk-value");
  if (el) el.textContent = getRiskFactor().toFixed(2);
}

// —— Predefined lists ——
async function loadPredefinedList(listId) {
  try {
    const data = await API.get("/api/predefined");
    const lists = data.lists || {};
    const symbols = lists[listId] || [];
    if (symbols.length === 0) return;
    // Fetch market data for these symbols so checkboxes exist
    const marketData = await API.get("/api/market?symbols=" + encodeURIComponent(symbols.join(",")));
    const assets = marketData.assets || symbols.map((s) => ({ symbol: s, name: s }));
    if (assets.length > 0) {
      renderAssetCheckboxes(assets);
      renderTicker(assets);
      setDataTimestamp();
    }
    document.querySelectorAll('input[name="asset"]').forEach((cb) => {
      cb.checked = symbols.includes(cb.value);
    });
    document.querySelectorAll(".predefined-tab").forEach((btn) => {
      btn.classList.remove("bg-blue-500", "text-white");
      btn.classList.add("bg-gray-200", "dark:bg-gray-600");
      if (btn.getAttribute("data-list") === listId) {
        btn.classList.remove("bg-gray-200", "dark:bg-gray-600");
        btn.classList.add("bg-blue-500", "text-white");
      }
    });
    updateRunButton();
  } catch (e) {
    console.warn("Predefined list failed", e);
  }
}

// —— Demo mode helpers ——
function setDemoMode(on) {
  demoMode = on;
  const badge = $("demo-badge");
  const tickerLabel = $("ticker-label");
  const liveControls = $("live-controls");
  const stockSelect = $("stock-select-wrap");
  const refreshBtn = $("refresh-data");
  if (badge) badge.classList.toggle("hidden", !on);
  if (tickerLabel) tickerLabel.textContent = on ? "Demo data" : "Live prices";
  if (liveControls) liveControls.classList.toggle("hidden", on);
  if (stockSelect) stockSelect.classList.toggle("hidden", on);
  if (refreshBtn) refreshBtn.classList.toggle("hidden", on);
  if (on) {
    loadDemoData();
  } else {
    fetchMarket();
  }
  updateRunButton();
}

async function loadDemoData() {
  try {
    const data = await API.get("/api/demo-data");
    const assets = data.assets || data.symbols.map((s, i) => ({
      symbol: s,
      name: (data.assetNames || {})[s] || s,
      currentPrice: 100,
      dayChangePercent: 0
    }));
    if (data.assets) {
      marketAssets = data.assets;
    } else {
      marketAssets = (data.symbols || []).map((s) => ({
        symbol: s,
        name: (data.assetNames || {})[s] || s,
        currentPrice: 100,
        dayChangePercent: 0
      }));
    }
    renderTicker(marketAssets);
    renderAssetCheckboxes(marketAssets);
    setDataTimestamp(Math.floor(Date.now() / 1000));
  } catch (e) {
    console.warn("Demo data failed", e);
    marketAssets = [
      { symbol: "NOK", name: "Nokia", currentPrice: 4.12, dayChangePercent: 0.8 },
      { symbol: "NDA-FI.HE", name: "Nordea", currentPrice: 11.85, dayChangePercent: -0.3 },
      { symbol: "FORTUM.HE", name: "Fortum", currentPrice: 14.2, dayChangePercent: 1.2 },
      { symbol: "AAPL", name: "Apple", currentPrice: 188.5, dayChangePercent: 0.5 },
      { symbol: "GOOGL", name: "Google", currentPrice: 142.3, dayChangePercent: 0.9 }
    ];
    renderTicker(marketAssets);
    renderAssetCheckboxes(marketAssets);
  }
  updateRunButton();
}

// —— Fetch market (with optional silent for auto-refresh) ——
async function fetchMarket(silent = false) {
  if (demoMode) return;
  try {
    const data = await API.get("/api/market");
    marketAssets = data.assets || [];
    if (marketAssets.length === 0) {
      const symData = await API.get("/api/symbols");
      const symbols = symData.symbols || [];
      renderAssetCheckboxes(symbols.map((s) => ({ symbol: s.symbol, name: s.name || s.symbol })));
    } else {
      renderAssetCheckboxes(marketAssets);
    }
    renderTicker(marketAssets);
    setDataTimestamp();
    if (!silent) scheduleAutoRefresh();
  } catch (e) {
    if (!silent) {
      const symData = await API.get("/api/symbols").catch(() => ({}));
      const symbols = symData.symbols || [];
      renderAssetCheckboxes(symbols.map((s) => ({ symbol: s.symbol, name: s.name || s.symbol })));
      renderTicker([]);
      showError("Could not load market data. Using cached list. Try again later.");
    }
  }
  updateRunButton();
}

// —— Progress bar animation ——
function startProgressBar() {
  const bar = $("progress-bar");
  if (!bar) return;
  bar.style.width = "0%";
  let w = 0;
  const iv = setInterval(() => {
    w += Math.random() * 8 + 4;
    if (w >= 90) w = 90;
    bar.style.width = w + "%";
  }, 200);
  window._progressInterval = iv;
}

function stopProgressBar() {
  if (window._progressInterval) {
    clearInterval(window._progressInterval);
    window._progressInterval = null;
  }
  const bar = $("progress-bar");
  if (bar) bar.style.width = "100%";
}

// —— Optimize (with risk slider debounce support) ——
let optimizeDebounce = null;
async function runOptimization() {
  const symbols = demoMode ? ["NOK", "NDA-FI.HE", "FORTUM.HE", "AAPL", "GOOGL"] : getSelectedSymbols();
  const budget = getBudget();
  const riskFactor = getRiskFactor();
  const useQuantum = $("use-quantum").checked;

  if (!demoMode && symbols.length < 2) {
    showError("Select at least 2 assets.");
    return;
  }
  if (budget >= symbols.length) {
    showError("Budget must be less than the number of selected assets.");
    return;
  }

  hide($("error-message"));
  hide($("results-area"));
  show($("loading"));
  startProgressBar();

  try {
    const payload = {
      symbols: demoMode ? [] : symbols,
      budget,
      riskFactor,
      useQuantum,
      useDemoData: demoMode,
    };
    const result = await API.post("/api/optimize", payload);

    stopProgressBar();
    hide($("loading"));
    show($("results-area"));

    lastOptimizeResult = result;
    renderResults(result);
    renderResultsSummary(result);
    renderHallOfFame();
    updateCircuitImage(symbols.length);
    renderRiskReturnChart(result.symbols || symbols, result);
    setDataTimestamp();

    const q = result.quantum || result.classical;
    const timeEl = $("completion-time");
    if (timeEl && q) {
      const sec = (q.computationTimeMs / 1000).toFixed(2);
      timeEl.textContent = "Quantum simulation completed in " + sec + " seconds.";
    }

    hide($("backtest-chart-wrap"));
    if (backtestChart) {
      backtestChart.destroy();
      backtestChart = null;
    }
  } catch (e) {
    stopProgressBar();
    hide($("loading"));
    const msg = e.message || "Optimization failed.";
    if (msg.toLowerCase().includes("vqe") || msg.toLowerCase().includes("quantum")) {
      showError(msg + " Try unchecking 'Use quantum' for a classical-only result.");
    } else {
      showError(msg + " You can try fewer stocks or Refresh data.");
    }
  }
}

function showError(msg) {
  const el = $("error-message");
  if (el) {
    el.textContent = msg;
    show(el);
  }
}

function renderResultsSummary(data) {
  const q = data.quantum || data.classical;
  const block = $("results-summary");
  const body = $("results-summary-body");
  if (!block || !body) return;
  if (!q) {
    hide(block);
    return;
  }
    body.innerHTML = `
    <div class="flex justify-between"><span>Expected return</span><span class="font-mono text-blue-600 dark:text-blue-400">${(q.expectedReturn * 100).toFixed(2)}%</span></div>
    <div class="flex justify-between"><span>Risk</span><span class="font-mono text-blue-600 dark:text-blue-400">${(q.risk * 100).toFixed(2)}%</span></div>
    <div class="flex justify-between"><span>Method</span><span class="font-mono">${escapeHtml(q.methodUsed)}</span></div>
    <div class="flex justify-between"><span>Time</span><span class="font-mono">${q.computationTimeMs} ms</span></div>
  `;
  show(block);
}

function renderResults(data) {
  const q = data.quantum || data.classical;
  const c = data.classical;
  if (!q) return;

  const names = q.selectedNames || q.selectedSymbols || [];
  $("recommended-text").textContent = "Buy: " + (names.join(", ") || "—");

  // Quantum run details: objective gap (real) and best bitstring interpretation (real)
  const detailsEl = $("quantum-details");
  if (detailsEl && data.quantum) {
    const parts = [];
    if (typeof data.objectiveGap === "number") {
      const pct = (data.objectiveGap * 100).toFixed(2);
      parts.push("Quantum solution is within " + pct + "% of the classical optimum (exact).");
    }
    const prob = q.probabilityDistribution || {};
    const sorted = Object.entries(prob).sort((a, b) => b[1] - a[1]);
    if (sorted.length > 0) {
      const [bitstring, probVal] = sorted[0];
      const symbols = data.symbols || [];
      const namesByIdx = data.assetNames || {};
      const selected = [];
      for (let i = 0; i < bitstring.length && i < symbols.length; i++) {
        if (bitstring[i] === "1") selected.push(namesByIdx[i] || symbols[i] || "asset " + i);
      }
      parts.push("Best bitstring \"" + bitstring + "\" → hold: " + (selected.join(", ") || "—") + " (probability " + (probVal * 100).toFixed(1) + "%).");
    }
    if (parts.length > 0) {
      detailsEl.innerHTML = parts.map((p) => "<p>" + escapeHtml(p) + "</p>").join("");
      show(detailsEl);
    } else {
      hide(detailsEl);
    }
  } else if (detailsEl) {
    hide(detailsEl);
  }

  const comparison = $("comparison-table");
  comparison.innerHTML = "";
  const table = document.createElement("table");
  table.className = "w-full text-sm border-collapse";
  table.innerHTML = `
    <thead><tr class="border-b border-gray-200 dark:border-gray-600"><th class="text-left py-2 pr-4">Metric</th><th class="text-left py-2 pr-4">Classical</th><th class="text-left py-2">Quantum</th></tr></thead>
    <tbody>
      <tr class="border-b border-gray-100 dark:border-gray-700"><td class="py-2 pr-4">Selected</td><td class="py-2 pr-4">${c && c.selectedNames ? c.selectedNames.join(", ") : "—"}</td><td class="py-2">${(q.selectedNames || []).join(", ")}</td></tr>
      <tr class="border-b border-gray-100 dark:border-gray-700"><td class="py-2 pr-4">Expected return</td><td class="py-2 pr-4">${c ? (c.expectedReturn * 100).toFixed(2) + "%" : "—"}</td><td class="py-2">${(q.expectedReturn * 100).toFixed(2)}%</td></tr>
      <tr class="border-b border-gray-100 dark:border-gray-700"><td class="py-2 pr-4">Risk</td><td class="py-2 pr-4">${c ? (c.risk * 100).toFixed(2) + "%" : "—"}</td><td class="py-2">${(q.risk * 100).toFixed(2)}%</td></tr>
      <tr class="border-b border-gray-100 dark:border-gray-700"><td class="py-2 pr-4">Objective</td><td class="py-2 pr-4">${c ? c.objectiveValue.toFixed(4) : "—"}</td><td class="py-2">${q.objectiveValue.toFixed(4)}</td></tr>
      <tr><td class="py-2 pr-4">Time (ms)</td><td class="py-2 pr-4">${c ? c.computationTimeMs : "—"}</td><td class="py-2">${q.computationTimeMs}</td></tr>
    </tbody>
  `;
  comparison.appendChild(table);

  const prob = q.probabilityDistribution || {};
  const probEntries = Object.entries(prob).sort((a, b) => b[1] - a[1]).slice(0, 12);
  if (probChart) probChart.destroy();
  const probCtx = document.getElementById("prob-chart");
  if (probCtx && probEntries.length > 0) {
    const isDark = document.documentElement.classList.contains("dark");
    probChart = new Chart(probCtx, {
      type: "bar",
      data: {
        labels: probEntries.map(([k]) => k),
        datasets: [{ label: "Probability", data: probEntries.map(([, v]) => v), backgroundColor: "rgba(59, 130, 246, 0.7)" }],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { max: 1, ticks: { stepSize: 0.2, color: isDark ? "#94a3b8" : "#64748b" } },
          y: { ticks: { color: isDark ? "#94a3b8" : "#64748b" } },
        },
      },
    });
  }

  const conv = q.convergenceHistory || [];
  if (convergenceChart) convergenceChart.destroy();
  const convCtx = document.getElementById("convergence-chart");
  if (convCtx && conv.length > 0) {
    const isDark = document.documentElement.classList.contains("dark");
    convergenceChart = new Chart(convCtx, {
      type: "line",
      data: {
        labels: conv.map((_, i) => i + 1),
        datasets: [{ label: "Objective", data: conv, borderColor: "#3B82F6", fill: false, tension: 0.1 }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { title: { display: true, text: "Iteration" }, ticks: { color: isDark ? "#94a3b8" : "#64748b" } },
          y: { title: { display: true, text: "Objective" }, ticks: { color: isDark ? "#94a3b8" : "#64748b" } },
        },
      },
    });
  }
}

// —— Risk–return chart ——
async function renderRiskReturnChart(symbols, result) {
  const canvas = document.getElementById("risk-return-chart");
  if (!canvas) return;

  const q = result && (result.quantum || result.classical);
  const c = result && result.classical;

  if (riskReturnChart) riskReturnChart.destroy();

  const isDark = document.documentElement.classList.contains("dark");
  const tickColor = isDark ? "#94a3b8" : "#64748b";

  let assets = [];
  let frontier = [];

  try {
    const url = demoMode
      ? "/api/risk-return?useDemoData=true"
      : "/api/risk-return?symbols=" + encodeURIComponent(symbols.join(","));
    const data = await API.get(url);
    if (data && !data.error) {
      assets = data.assets || [];
      frontier = data.efficientFrontier || [];
    }
  } catch (e) {
    console.warn("Risk-return API failed, showing portfolio points only", e);
  }

  const datasets = [];

  if (frontier.length > 0) {
    const sorted = [...frontier].sort((a, b) => a.risk - b.risk);
    datasets.push({
      label: "Efficient frontier",
      data: sorted.map((p) => ({ x: p.risk * 100, y: p.return * 100 })),
      borderColor: "rgba(148, 163, 184, 0.8)",
      backgroundColor: "transparent",
      fill: false,
      pointRadius: 2,
      pointHoverRadius: 4,
      borderWidth: 2,
      showLine: true,
    });
  }

  if (assets.length > 0) {
    datasets.push({
      label: "Stocks",
      data: assets.map((a) => ({ x: a.risk * 100, y: a.return * 100 })),
      backgroundColor: "rgba(59, 130, 246, 0.6)",
      borderColor: "#3B82F6",
      pointRadius: 8,
      pointHoverRadius: 10,
    });
  }

  if (q) {
    datasets.push({
      label: "Quantum portfolio",
      data: [{ x: q.risk * 100, y: q.expectedReturn * 100 }],
      backgroundColor: "#10b981",
      borderColor: "#059669",
      pointRadius: 12,
      pointStyle: "star",
    });
  }
  if (c && result && result.quantum) {
    datasets.push({
      label: "Classical portfolio",
      data: [{ x: c.risk * 100, y: c.expectedReturn * 100 }],
      backgroundColor: "#f59e0b",
      borderColor: "#d97706",
      pointRadius: 10,
      pointStyle: "triangle",
    });
  }

  if (datasets.length === 0) return;

  riskReturnChart = new Chart(canvas, {
    type: "scatter",
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { title: { display: true, text: "Risk (%)" }, ticks: { color: tickColor } },
        y: { title: { display: true, text: "Expected return (%)" }, ticks: { color: tickColor } },
      },
      plugins: { legend: { labels: { color: tickColor } } },
    },
  });
}

// —— Circuit ——
async function updateCircuitImage(numQubits) {
  const img = $("circuit-img");
  const container = $("circuit-container");
  const statsEl = $("circuit-stats");
  if (!img || !container) return;
  try {
    const data = await API.get("/api/circuit?numQubits=" + Math.min(6, Math.max(2, numQubits)));
    if (data.imageBase64) {
      img.src = "data:image/png;base64," + data.imageBase64;
      img.style.display = "block";
    }
    if (statsEl && data.numQubits != null) {
      const n = data.numQubits;
      const params = data.numParameters != null ? data.numParameters : "—";
      const depth = data.depth != null ? data.depth : "—";
      statsEl.textContent = "Circuit: " + n + " qubit" + (n !== 1 ? "s" : "") + ", " + params + " parameter" + (params !== 1 ? "s" : "") + ", depth " + depth + ".";
    }
  } catch (_) {}
  container.classList.add("hidden");
}

function toggleCircuit() {
  const container = $("circuit-container");
  const btn = $("circuit-toggle");
  if (!container || !btn) return;
  const show = container.classList.contains("hidden");
  if (show) container.classList.remove("hidden");
  else container.classList.add("hidden");
  btn.textContent = show ? "Hide quantum circuit" : "Show quantum circuit";
}

// —— Backtest ——
async function runBacktest() {
  if (!lastOptimizeResult) return;
  const symbols = lastOptimizeResult.symbols || [];
  const qIndices = (lastOptimizeResult.quantum || lastOptimizeResult.classical).selectedIndices || [];
  const cIndices = (lastOptimizeResult.classical || {}).selectedIndices || [];
  if (symbols.length === 0) return;

  const wrap = $("backtest-chart-wrap");
  show(wrap);
  try {
    const data = await API.post("/api/backtest", {
      symbols,
      quantumIndices: qIndices,
      classicalIndices: cIndices,
      days: 90,
    });
    const dates = data.dates || [];
    if (dates.length === 0) throw new Error("No backtest data");
    const L = dates.length;
    const trim = (arr) => (arr || []).slice(0, L).map((v) => v * 100);

    if (backtestChart) backtestChart.destroy();
    const ctx = document.getElementById("backtest-chart");
    const isDark = document.documentElement.classList.contains("dark");
    const tickColor = isDark ? "#94a3b8" : "#64748b";

    backtestChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: dates,
        datasets: [
          { label: "Quantum portfolio", data: trim(data.quantum), borderColor: "#10b981", fill: false, tension: 0.1 },
          { label: "Classical portfolio", data: trim(data.classical), borderColor: "#f59e0b", fill: false, tension: 0.1 },
          { label: "Equal weight", data: trim(data.equalWeight), borderColor: "#94a3b8", fill: false, tension: 0.1 },
          { label: "S&P 500", data: trim(data.benchmark), borderColor: "#6366f1", fill: false, tension: 0.1 },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { ticks: { color: tickColor, maxTicksLimit: 12 } },
          y: { title: { display: true, text: "Cumulative return (%)" }, ticks: { color: tickColor } },
        },
        plugins: { legend: { labels: { color: tickColor } } },
      },
    });
  } catch (e) {
    showError("Could not load historical performance. " + (e.message || "Try again later."));
  }
}

// —— Hall of Fame (static examples) ——
const HALL_OF_FAME = [
  { stocks: "Apple + Microsoft", date: "March 2025", desc: "Quantum recommended these with 92% confidence during a market dip." },
  { stocks: "Nordea + Nokia + Fortum", date: "February 2025", desc: "Finnish portfolio with low correlation—quantum favored diversification." },
  { stocks: "Google + Apple", date: "January 2025", desc: "Tech duo with strong expected returns; quantum agreed with classical." },
  { stocks: "Nordea + Fortum", date: "December 2024", desc: "Defensive pick during volatility; VQE converged in 47 iterations." },
  { stocks: "Apple + Google + Microsoft", date: "November 2024", desc: "Quantum found 88% probability for this triple-tech allocation." },
];

function renderHallOfFame() {
  const container = $("hall-of-fame");
  if (!container) return;
  container.innerHTML = HALL_OF_FAME.map(
    (h) => `
    <div class="rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-600/30 p-3 text-sm">
      <p class="font-medium text-gray-900 dark:text-white">${escapeHtml(h.stocks)}</p>
      <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">${escapeHtml(h.date)}</p>
      <p class="text-gray-600 dark:text-gray-300 mt-1">${escapeHtml(h.desc)}</p>
    </div>
  `
  ).join("");
}

// —— LinkedIn & screenshot ——
function generateLinkedInPost() {
  if (!lastOptimizeResult) return;
  const q = lastOptimizeResult.quantum || lastOptimizeResult.classical;
  const names = (q.selectedNames || q.selectedSymbols || []).join(", ");
  const confidence = q.probabilityDistribution
    ? (Math.max(...Object.values(q.probabilityDistribution)) * 100).toFixed(0)
    : "—";
  const url = window.location.origin + window.location.pathname || "https://your-app-url.com";
  const text = `I just optimized a portfolio using real quantum computing! The algorithm recommended buying ${names} with ${confidence}% confidence. Check out the live app: ${url} #QuantumComputing #FinTech #PortfolioOptimization`;
  const ta = $("linkedin-text");
  const out = $("linkedin-output");
  if (ta) ta.value = text;
  if (out) show(out);
}

function downloadScreenshot() {
  if (typeof html2canvas === "undefined") {
    showError("Screenshot library not loaded.");
    return;
  }
  const results = $("results-area");
  if (!results) return;
  html2canvas(results, { scale: 2, useCORS: true }).then((canvas) => {
    const a = document.createElement("a");
    a.download = "quantum-playground-results.png";
    a.href = canvas.toDataURL("image/png");
    a.click();
  });
}

// —— Video modal ——
function openVideoModal() {
  const modal = $("video-modal");
  const iframe = $("video-iframe");
  if (modal && iframe) {
    iframe.src = "https://www.youtube.com/embed/QuR969uMICM?autoplay=1";
    modal.classList.remove("hidden");
  }
}

function closeVideoModal() {
  const modal = $("video-modal");
  const iframe = $("video-iframe");
  if (modal) modal.classList.add("hidden");
  if (iframe) iframe.src = "about:blank";
}

// —— Risk slider: debounced re-run ——
function onRiskChange() {
  updateRiskLabel();
  if (!lastOptimizeResult) return;
  if (optimizeDebounce) clearTimeout(optimizeDebounce);
  optimizeDebounce = setTimeout(() => {
    runOptimization();
  }, 400);
}

function init() {
  initTheme();
  initTooltips();

  const coldStartNotice = $("cold-start-notice");
  const coldStartDismiss = $("cold-start-dismiss");
  if (coldStartNotice && coldStartDismiss) {
    if (sessionStorage.getItem("coldStartNoticeDismissed")) coldStartNotice.classList.add("hidden");
    coldStartDismiss.addEventListener("click", () => {
      coldStartNotice.classList.add("hidden");
      sessionStorage.setItem("coldStartNoticeDismissed", "1");
    });
  }

  const demoCheck = $("demo-mode");
  if (demoCheck) {
    demoCheck.checked = true;
    demoMode = true;
    setDemoMode(true);
    demoCheck.addEventListener("change", () => {
      demoMode = demoCheck.checked;
      setDemoMode(demoMode);
    });
  }

  const learnMoreBtn = $("learn-more-btn");
  const learnMoreSection = $("learn-more-section");
  if (learnMoreBtn && learnMoreSection) {
    learnMoreBtn.addEventListener("click", () => {
      learnMoreSection.classList.toggle("hidden");
    });
  }

  $("theme-toggle").addEventListener("click", toggleTheme);
  $("video-btn").addEventListener("click", openVideoModal);
  $("video-close").addEventListener("click", closeVideoModal);
  $("video-modal").addEventListener("click", (e) => {
    if (e.target.id === "video-modal") closeVideoModal();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeVideoModal();
  });

  $("refresh-data").addEventListener("click", () => fetchMarket());
  $("run-optimize").addEventListener("click", () => runOptimization());
  $("risk").addEventListener("input", onRiskChange);
  $("budget").addEventListener("change", updateRunButton);

  document.querySelectorAll(".predefined-tab").forEach((btn) => {
    btn.addEventListener("click", () => loadPredefinedList(btn.getAttribute("data-list")));
  });

  $("circuit-toggle").addEventListener("click", toggleCircuit);
  $("backtest-btn").addEventListener("click", runBacktest);
  $("linkedin-btn").addEventListener("click", generateLinkedInPost);
  $("screenshot-btn").addEventListener("click", downloadScreenshot);

  if (!demoMode) fetchMarket();
  renderHallOfFame();
  updateRiskLabel();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
