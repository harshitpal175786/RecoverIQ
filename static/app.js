/**
 * RecoverIQ — Razorpay Merchant Frontend JavaScript.
 */

const API_BASE = ""; // Relative to current host

let actionsChartInstance = null;
let failureChartInstance = null;
let bmRateChartInstance = null;
let bmRevChartInstance = null;
let currentTransactions = [];

document.addEventListener("DOMContentLoaded", () => {
    initNavigation();
    initQuickTrigger();
    loadOverviewMetrics();
    loadTransactions();
    loadEscalations();

    document.getElementById("btnRefresh").addEventListener("click", () => {
        showToast("Syncing latest live data...");
        loadOverviewMetrics();
        loadTransactions();
        loadEscalations();
    });

    document.getElementById("txSearchInput").addEventListener("input", filterTransactionsTable);
    document.getElementById("txStatusFilter").addEventListener("change", filterTransactionsTable);
    document.getElementById("btnRunBenchmark").addEventListener("click", runBenchmark);
    document.getElementById("btnDrawerClose").addEventListener("click", closeDrawer);
});

// --- NAVIGATION ---
function initNavigation() {
    const sideLinks = document.querySelectorAll(".side-link");
    sideLinks.forEach(link => {
        link.addEventListener("click", (e) => {
            const targetView = link.getAttribute("data-view");
            if (!targetView) return;

            sideLinks.forEach(l => l.classList.remove("active"));
            link.classList.add("active");

            document.querySelectorAll(".view-panel").forEach(panel => {
                panel.classList.remove("active");
            });

            const activePanel = document.getElementById(`view-${targetView}`);
            if (activePanel) {
                activePanel.classList.add("active");
            }
        });
    });
}

// --- UTILS ---
function formatCurrency(amount) {
    if (amount === undefined || amount === null) return "₹0.00";
    const num = parseFloat(amount);
    if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)} Cr`;
    if (num >= 100000) return `₹${(num / 100000).toFixed(2)} Lakhs`;
    return `₹${num.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function getStatusBadge(status) {
    const s = String(status).toUpperCase();
    if (["RECOVERED", "SUCCESS", "VERIFIED_SUCCESS", "CAPTURED"].includes(s)) {
        return `<span class="status-badge status-recovered">● ${s}</span>`;
    } else if (["FAILED", "ABANDONED", "VERIFIED_FAILED"].includes(s)) {
        return `<span class="status-badge status-failed">● ${s}</span>`;
    } else if (["ESCALATED", "BLOCKED"].includes(s)) {
        return `<span class="status-badge status-escalated">● ${s}</span>`;
    }
    return `<span class="status-badge status-progress">● ${s}</span>`;
}

function showToast(msg) {
    const toast = document.getElementById("rzpToast");
    toast.innerText = msg;
    toast.style.display = "block";
    setTimeout(() => {
        toast.style.display = "none";
    }, 3500);
}

// --- OVERVIEW & METRICS ---
async function loadOverviewMetrics() {
    try {
        const res = await fetch(`${API_BASE}/metrics`);
        const data = await res.json();

        if (!data || !data.total_transactions) return;

        document.getElementById("kpiFailedAmount").innerText = formatCurrency(data.total_failed_amount_inr);
        document.getElementById("kpiFailedCount").innerText = `${data.total_transactions} failed transactions`;

        document.getElementById("kpiRecoveredAmount").innerText = `+${formatCurrency(data.recovered_amount_inr)}`;
        document.getElementById("kpiRecoveredCount").innerText = `${data.recovered_count} transactions won back`;

        document.getElementById("kpiRecoveryRate").innerText = `${data.recovery_rate_pct.toFixed(1)}%`;
        document.getElementById("kpiRateSub").innerText = `${data.recovered_count} of ${data.total_transactions} recovered`;

        document.getElementById("kpiCompliance").innerText = `${data.guardrail_compliance_pct.toFixed(0)}%`;
        document.getElementById("kpiEscalatedCount").innerText = `${data.escalated_count} held for human review`;

        renderActionsChart(data.action_distribution || {});
        renderFailureChart(data.failure_category_distribution || {});
    } catch (e) {
        console.error("Failed to load metrics:", e);
    }
}

function renderActionsChart(actions) {
    const ctx = document.getElementById("actionsChart").getContext("2d");
    const labels = Object.keys(actions);
    const values = Object.values(actions);

    const colors = {
        "DELAY_AND_RETRY": "#0284C7",
        "PAYMENT_LINK": "#10B981",
        "ALTERNATE_METHOD": "#8B5CF6",
        "ESCALATE": "#F59E0B",
        "RETRY": "#3B82F6",
        "NO_ACTION": "#EF4444",
        "PENDING": "#94A3B8"
    };

    const bgColors = labels.map(l => colors[l] || "#64748B");

    if (actionsChartInstance) actionsChartInstance.destroy();

    actionsChartInstance = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: bgColors,
                borderWidth: 2,
                borderColor: "#FFFFFF"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: "right", labels: { font: { family: "Inter", size: 12 } } }
            },
            cutout: "65%"
        }
    });
}

function renderFailureChart(failCats) {
    const ctx = document.getElementById("failureChart").getContext("2d");
    const labels = Object.keys(failCats);
    const values = Object.values(failCats);

    if (failureChartInstance) failureChartInstance.destroy();

    failureChartInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "Failures",
                data: values,
                backgroundColor: "#0066FF",
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: "#F1F5F9" }, ticks: { font: { family: "Inter" } } },
                y: { grid: { display: false }, ticks: { font: { family: "Inter" } } }
            }
        }
    });
}

// --- TRANSACTIONS ---
async function loadTransactions() {
    try {
        const res = await fetch(`${API_BASE}/transactions?limit=50`);
        currentTransactions = await res.json();
        renderTransactionsTable(currentTransactions);
    } catch (e) {
        console.error("Failed to load transactions:", e);
    }
}

function renderTransactionsTable(txList) {
    const tbody = document.getElementById("txTableBody");
    if (!txList || txList.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center py-4 text-muted">No transactions found. Trigger a test failure from the sidebar!</td></tr>`;
        return;
    }

    tbody.innerHTML = txList.map(tx => `
        <tr style="cursor:pointer;" onclick="openTransactionDrawer('${tx.transaction_id}')">
            <td><code>${tx.transaction_id}</code></td>
            <td><b>${tx.customer_name || 'Customer'}</b></td>
            <td><b>${formatCurrency(tx.amount_inr)}</b></td>
            <td>${tx.payment_method || 'N/A'} <span class="text-muted">(${tx.issuer_bank || 'N/A'})</span></td>
            <td><span class="text-muted">${tx.error_reason || tx.failure_category || 'N/A'}</span></td>
            <td><code>${tx.recovery_action || 'PENDING'}</code></td>
            <td>${getStatusBadge(tx.status)}</td>
            <td><button class="rzp-btn rzp-btn-outline" style="padding:4px 8px; font-size:11px;" onclick="event.stopPropagation(); openTransactionDrawer('${tx.transaction_id}')">Inspect</button></td>
        </tr>
    `).join("");
}

function filterTransactionsTable() {
    const q = document.getElementById("txSearchInput").value.toLowerCase();
    const st = document.getElementById("txStatusFilter").value;

    const filtered = currentTransactions.filter(t => {
        const matchesQuery = (t.transaction_id && t.transaction_id.toLowerCase().includes(q)) || 
                             (t.customer_name && t.customer_name.toLowerCase().includes(q));
        const matchesStatus = (st === "ALL" || t.status === st);
        return matchesQuery && matchesStatus;
    });

    renderTransactionsTable(filtered);
}

// --- DRAWER MODAL ---
async function openTransactionDrawer(txId) {
    const tx = currentTransactions.find(t => t.transaction_id === txId);
    if (!tx) return;

    document.getElementById("drawerTitle").innerText = `Payment: ${tx.transaction_id}`;
    const body = document.getElementById("drawerBody");

    body.innerHTML = `
        <div style="margin-bottom:16px;">
            <div style="font-size:12px; color:#64748B; text-transform:uppercase; font-weight:700;">Customer & Payment</div>
            <div style="font-size:18px; font-weight:700; margin-top:4px;">${tx.customer_name} — ${formatCurrency(tx.amount_inr)}</div>
            <div style="font-size:12px; color:#64748B;">Segment: <b>${tx.customer_segment || 'STANDARD'}</b> | Method: <b>${tx.payment_method} (${tx.issuer_bank})</b></div>
        </div>

        <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:12px; margin-bottom:16px;">
            <div style="font-size:12px; font-weight:700; color:#334155;">FAILURE DIAGNOSIS</div>
            <div style="font-size:13px; color:#0F172A; margin-top:4px;">Category: <b>${tx.failure_category}</b></div>
            <div style="font-size:12px; color:#64748B;">Error: <code>${tx.error_code}</code> ➔ <i>${tx.error_reason}</i></div>
            <div style="margin-top:6px;">Status: ${getStatusBadge(tx.status)}</div>
        </div>

        <div id="drawerLogsArea"><p class="text-muted">Loading AI decision trace...</p></div>

        ${tx.status === 'FAILED' ? `
            <div style="margin-top:20px;">
                <button class="rzp-btn rzp-btn-primary btn-block" onclick="executeSingleRecovery('${tx.transaction_id}')">⚡ Execute Autonomous Recovery</button>
            </div>
        ` : ''}
    `;

    document.getElementById("txDrawer").style.display = "flex";

    // Fetch audit logs
    try {
        const res = await fetch(`${API_BASE}/logs/${txId}`);
        const logs = await res.json();
        const logsArea = document.getElementById("drawerLogsArea");

        if (logs && logs.length > 0) {
            let html = `<div style="font-size:12px; font-weight:700; color:#334155; margin-bottom:10px;">🔬 5-STAGE AI AUDIT TRAIL</div>`;
            logs.forEach(log => {
                let extra = "";
                try {
                    const out = JSON.parse(log.output_data || "{}");
                    if (out.decision) {
                        const d = out.decision;
                        extra += `
                            <div style="background:#EFF6FF; border:1px solid #BFDBFE; border-radius:6px; padding:10px; margin-top:6px;">
                                <b>AI Recommendation:</b> <code>${d.recommended_action}</code> (${(d.confidence_score * 100).toFixed(0)}% confidence)<br/>
                                <i style="font-size:12px; color:#334155;">"${d.reasoning}"</i>
                            </div>
                        `;
                        if (d.notification_message) {
                            extra += `
                                <div class="whatsapp-card">
                                    💬 <b>Customer WhatsApp Template:</b><br/>
                                    <i>"${d.notification_message}"</i>
                                </div>
                            `;
                        }
                    } else if (out.result && !out.result.passed) {
                        extra += `
                            <div style="background:#FFFBEB; border:1px solid #FDE68A; border-radius:6px; padding:8px; margin-top:6px; font-size:12px; color:#B45309;">
                                🛡️ <b>Guardrails Triggered:</b> ${out.result.checks_blocked.join(", ")} ➔ Modified to: <code>${out.result.final_action}</code>
                            </div>
                        `;
                    }
                } catch (e) {}

                html += `
                    <div class="timeline-step">
                        <div style="font-size:12px; font-weight:700; color:#0F172A;">${log.stage} <span style="font-weight:400; color:#64748B;">(${log.duration_ms}ms)</span></div>
                        ${extra}
                    </div>
                `;
            });
            logsArea.innerHTML = html;
        } else {
            logsArea.innerHTML = `<p class="text-muted" style="font-size:12px;">No audit logs recorded yet.</p>`;
        }
    } catch (e) {
        console.error("Failed to load logs:", e);
    }
}

function closeDrawer() {
    document.getElementById("txDrawer").style.display = "none";
}

async function executeSingleRecovery(txId) {
    showToast(`Executing recovery on ${txId}...`);
    try {
        const res = await fetch(`${API_BASE}/recovery/${txId}/execute`, { method: "POST" });
        const data = await res.json();
        showToast(`Recovery Executed: ${data.action} (${data.verified_status})`);
        closeDrawer();
        loadOverviewMetrics();
        loadTransactions();
    } catch (e) {
        showToast(`Error executing recovery: ${e}`);
    }
}

// --- BENCHMARK ---
async function runBenchmark() {
    const btn = document.getElementById("btnRunBenchmark");
    btn.innerText = "Simulating (50 Txns)...";
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/compare?count=50`);
        const comp = await res.json();

        document.getElementById("benchmarkBanner").style.display = "block";
        document.getElementById("bmCardsGrid").style.display = "grid";
        document.getElementById("bmChartsGrid").style.display = "grid";

        document.getElementById("bmSummaryTitle").innerText = `🏆 Net Uplift: +${formatCurrency(comp.revenue_uplift_inr)} (+${comp.revenue_uplift_pct.toFixed(1)}%)`;
        document.getElementById("bmSummaryText").innerText = comp.summary;

        document.getElementById("bmBaselineRate").innerText = `${comp.baseline.recovery_rate_pct.toFixed(1)}%`;
        document.getElementById("bmBaselineAmt").innerText = formatCurrency(comp.baseline.recovered_amount_inr);

        document.getElementById("bmRiqRate").innerText = `${comp.recoveriq.recovery_rate_pct.toFixed(1)}%`;
        document.getElementById("bmRiqAmt").innerText = formatCurrency(comp.recoveriq.recovered_amount_inr);

        document.getElementById("bmUpliftRev").innerText = `+${formatCurrency(comp.revenue_uplift_inr)}`;
        document.getElementById("bmUpliftRate").innerText = `+${comp.recovery_rate_uplift_pct.toFixed(1)}pp recovery rate`;
        document.getElementById("bmFalseAction").innerText = `${comp.false_action_improvement_pct.toFixed(1)}%`;

        renderBenchmarkCharts(comp);
        showToast("Benchmark simulation finished!");
    } catch (e) {
        showToast("Error running benchmark: " + e);
    } finally {
        btn.innerText = "⚖️ Run Side-by-Side Benchmark (50 Txns)";
        btn.disabled = false;
    }
}

function renderBenchmarkCharts(comp) {
    const ctxRate = document.getElementById("bmRateChart").getContext("2d");
    if (bmRateChartInstance) bmRateChartInstance.destroy();

    bmRateChartInstance = new Chart(ctxRate, {
        type: "bar",
        data: {
            labels: ["Naive Baseline", "RecoverIQ AI"],
            datasets: [{
                label: "Recovery Rate (%)",
                data: [comp.baseline.recovery_rate_pct, comp.recoveriq.recovery_rate_pct],
                backgroundColor: ["#94A3B8", "#10B981"],
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } }
        }
    });

    const ctxRev = document.getElementById("bmRevChart").getContext("2d");
    if (bmRevChartInstance) bmRevChartInstance.destroy();

    bmRevChartInstance = new Chart(ctxRev, {
        type: "bar",
        data: {
            labels: ["Naive Baseline", "RecoverIQ AI"],
            datasets: [{
                label: "Recovered Amount (₹)",
                data: [comp.baseline.recovered_amount_inr, comp.recoveriq.recovered_amount_inr],
                backgroundColor: ["#94A3B8", "#0066FF"],
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } }
        }
    });
}

// --- ESCALATIONS ---
async function loadEscalations() {
    try {
        const res = await fetch(`${API_BASE}/escalations`);
        const escalations = await res.json();
        const escBadge = document.getElementById("escCountBadge");
        const container = document.getElementById("escalationsList");

        if (!escalations || escalations.length === 0) {
            escBadge.innerText = "0";
            container.innerHTML = `<div class="rzp-card"><p class="text-success">🎉 No pending escalations in queue!</p></div>`;
            return;
        }

        const unresolved = escalations.filter(e => !e.resolved);
        escBadge.innerText = unresolved.length;

        container.innerHTML = escalations.map(e => `
            <div class="escalation-card">
                <div class="esc-info">
                    <h4>[${e.priority}] ${e.escalation_id} — ${e.customer_name || 'Customer'} (${formatCurrency(e.amount_inr)})</h4>
                    <p><b>Flagged Reason:</b> ${e.reason} | <b>Transaction ID:</b> <code>${e.transaction_id}</code></p>
                    <p style="font-size:11px; margin-top:2px;">Method: ${e.payment_method} (${e.issuer_bank}) | Created: ${e.created_at || 'N/A'}</p>
                </div>
                <div class="esc-actions">
                    ${e.resolved ? `
                        <span class="status-badge status-recovered">● Resolved</span>
                    ` : `
                        <button class="rzp-btn rzp-btn-primary" onclick="resolveEscalationModal('${e.escalation_id}')">✅ Authorize & Resolve</button>
                    `}
                </div>
            </div>
        `).join("");
    } catch (e) {
        console.error("Failed to load escalations:", e);
    }
}

async function resolveEscalationModal(escId) {
    const notes = prompt("Enter human operator notes:", "Approved for manual VIP payment recovery.");
    if (notes === null) return;

    try {
        const res = await fetch(`${API_BASE}/escalations/${escId}/resolve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ notes: notes })
        });
        showToast("Escalation marked as resolved!");
        loadEscalations();
        loadOverviewMetrics();
    } catch (e) {
        showToast("Error resolving escalation: " + e);
    }
}

// --- QUICK TEST TRIGGER ---
function initQuickTrigger() {
    const btn = document.getElementById("btnTriggerTest");
    btn.addEventListener("click", async () => {
        const sel = document.getElementById("quickScenarioSelect");
        const idx = parseInt(sel.value);
        btn.innerText = "Intercepting...";
        btn.disabled = true;

        try {
            const res = await fetch(`${API_BASE}/demo/scenarios`, { method: "POST" });
            const data = await res.json();
            if (data && data.scenarios) {
                const sc = data.scenarios[idx];
                showToast(`✅ Intercepted ${sc.transaction_id}: ${sc.actual_action} (${sc.verification_status})`);
                loadOverviewMetrics();
                loadTransactions();
                loadEscalations();
            }
        } catch (e) {
            showToast("Error executing intercept: " + e);
        } finally {
            btn.innerText = "⚡ Intercept & Recover";
            btn.disabled = false;
        }
    });
}
