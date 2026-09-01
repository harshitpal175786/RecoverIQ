"""RecoverIQ — Razorpay Merchant Dashboard Theme.
Razorpay Buildathon 2026 • Track 03: AI Revenue Recovery
"""

import streamlit as st
import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List
import json
from datetime import datetime

# --- APP CONFIGURATION ---
API_URL = "http://localhost:8000"
APP_TITLE = "Razorpay Dashboard | RecoverIQ"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- RAZORPAY DESIGN SYSTEM CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');

    /* Global Typography & Light Theme */
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #F8FAFC !important;
        color: #0F172A !important;
    }

    /* Razorpay Top Navigation Bar */
    .rzp-topbar {
        background-color: #0C1322;
        color: #FFFFFF;
        padding: 10px 20px;
        border-radius: 8px 8px 0 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin: -4rem -4rem 1.5rem -4rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    }

    .rzp-logo {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 20px;
        font-weight: 800;
        color: #3395FF;
        letter-spacing: -0.5px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .rzp-test-pill {
        background-color: #059669;
        color: #FFFFFF;
        font-size: 11px;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 12px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* White Cards */
    .rzp-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 16px;
    }

    .rzp-card-title {
        font-size: 13px;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }

    .rzp-card-val {
        font-size: 26px;
        font-weight: 700;
        color: #0F172A;
    }

    .rzp-card-sub {
        font-size: 12px;
        color: #0284C7;
        margin-top: 4px;
        font-weight: 500;
    }

    /* Status Badges */
    .status-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
    }
    .status-recovered { background-color: #ECFDF5; color: #059669; border: 1px solid #A7F3D0; }
    .status-failed { background-color: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; }
    .status-escalated { background-color: #FFFBEB; color: #D97706; border: 1px solid #FDE68A; }
    .status-progress { background-color: #EFF6FF; color: #2563EB; border: 1px solid #BFDBFE; }

    /* Razorpay Primary Buttons */
    div.stButton > button:first-child {
        background-color: #0066FF !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        padding: 8px 16px !important;
        transition: background-color 0.15s ease !important;
    }
    div.stButton > button:first-child:hover {
        background-color: #0052CC !important;
    }

    /* Expander & Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
        border-bottom: 1px solid #E2E8F0;
        padding-bottom: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        color: #64748B;
        font-weight: 600;
        font-size: 14px;
        border-radius: 6px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #EFF6FF !important;
        color: #0066FF !important;
    }
</style>

<!-- Razorpay Top Bar Header -->
<div class="rzp-topbar">
    <div style="display:flex; align-items:center; gap:16px;">
        <div class="rzp-logo">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="#3395FF"/>
                <path d="M2 17L12 22L22 17" stroke="#3395FF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 12L12 17L22 12" stroke="#3395FF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            Razorpay <span style="font-weight:400; color:#94A3B8; font-size:16px;">| RecoverIQ</span>
        </div>
        <span class="rzp-test-pill">● Test Mode</span>
    </div>
    <div style="font-size:13px; color:#94A3B8; display:flex; gap:16px; align-items:center;">
        <span>Track 03: AI Revenue Recovery</span>
        <div style="background:#1E293B; border-radius:50%; width:28px; height:28px; display:flex; align-items:center; justify-content:center; color:#FFFFFF; font-weight:700; font-size:11px;">HP</div>
    </div>
</div>
""", unsafe_allow_html=True)


# --- FORMATTING UTILS ---
def format_currency(amount: float) -> str:
    """Format float into Indian Rupee format."""
    if amount is None:
        return "₹0.00"
    amount = float(amount)
    if amount >= 10000000:
        return f"₹{amount/10000000:,.2f} Cr"
    elif amount >= 100000:
        return f"₹{amount/100000:,.2f} Lakhs"
    elif amount >= 1000:
        s, *d = str(float(amount)).partition(".")
        r = ",".join([s[x-2:x] for x in range(-3, -len(s), -2)][::-1] + [s[-3:]])
        return f"₹{r}{d[0]}{d[1][:2]}" if r else f"₹{amount:,.2f}"
    return f"₹{amount:,.2f}"


def get_status_badge(status: str) -> str:
    status_str = str(status).upper()
    if status_str in ["RECOVERED", "SUCCESS", "VERIFIED_SUCCESS", "CAPTURED"]:
        return f'<span class="status-badge status-recovered">● {status_str}</span>'
    elif status_str in ["FAILED", "ABANDONED", "VERIFIED_FAILED"]:
        return f'<span class="status-badge status-failed">● {status_str}</span>'
    elif status_str in ["ESCALATED", "BLOCKED"]:
        return f'<span class="status-badge status-escalated">● {status_str}</span>'
    else:
        return f'<span class="status-badge status-progress">● {status_str}</span>'


# --- API CLIENT ---
def fetch_api(endpoint: str, params: Dict = None) -> Any:
    try:
        with httpx.Client(base_url=API_URL, timeout=120.0) as client:
            resp = client.get(endpoint, params=params)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        st.error(f"API Error ({endpoint}): {str(e)}")
        return {}


def post_api(endpoint: str, params: Dict = None, json_body: Dict = None) -> Any:
    try:
        with httpx.Client(base_url=API_URL, timeout=120.0) as client:
            resp = client.post(endpoint, params=params, json=json_body)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        st.error(f"API Error ({endpoint}): {str(e)}")
        return {}


# --- SIDEBAR: LIVE RAZORPAY INTEGRATION ---
with st.sidebar:
    st.markdown("### 💳 Razorpay Test Mode")
    st.caption("RecoverIQ is actively listening to your Razorpay Test Dashboard webhooks.")

    # Live Connection Status Box
    st.markdown("""
    <div style="background:#F1F5F9; border:1px solid #CBD5E1; border-radius:8px; padding:12px; margin-bottom:16px;">
        <div style="font-size:12px; color:#475569; font-weight:600;">WEBHOOK LISTENER</div>
        <div style="font-size:13px; color:#0F172A; font-weight:700; margin-top:2px;">🟢 Active: <code>/webhooks/razorpay</code></div>
        <div style="font-size:11px; color:#64748B; margin-top:4px;">Events: <code>payment.failed</code>, <code>payment_link.paid</code></div>
    </div>
    """, unsafe_allow_html=True)

    # Fast Interactive Demo Failure Trigger
    st.markdown("### 🧪 Quick Test Failure")
    st.caption("Trigger an instant test failure to see RecoverIQ intercept and recover it:")
    
    test_scenario = st.selectbox(
        "Select Failure Type:",
        [
            "1. UPI Bank Timeout (₹1,999)",
            "2. Degraded UPI ➔ Card Link (₹15,000)",
            "3. High-Value Payment Escalation (₹65,000)",
            "4. Recovered Payment (Duplicate Prevention)",
        ]
    )

    if st.button("⚡ Trigger Test Failure", type="primary", use_container_width=True):
        scenario_idx = int(test_scenario[0]) - 1
        with st.spinner("Intercepting payment failure & running AI recovery..."):
            demo_res = post_api("/demo/scenarios")
            if demo_res and "scenarios" in demo_res:
                st.session_state["recent_demo_tx"] = demo_res["scenarios"][scenario_idx]
                st.success(f"✅ Transaction processed via AI Recovery Agent!")
                st.rerun()

    st.divider()
    # Refresh / Sync
    if st.button("🔄 Refresh Live Dashboard", use_container_width=True):
        st.rerun()

    health = fetch_api("/health")
    if health:
        st.caption(f"🟢 **Backend**: Connected (v{health.get('version', '0.1.0')})")
        st.caption("🔗 **API Key**: `rzp_test_TWqY...`")
    else:
        st.caption("🔴 **Backend Offline**")


# --- MAIN RAZORPAY DASHBOARD TABS ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Overview & Analytics", 
    "💳 Payments & Recovery Logs", 
    "⚖️ ROI & Baseline Uplift", 
    "🚨 Human Escalation Desk"
])


# =========================================================================
# --- TAB 1: OVERVIEW & ANALYTICS ---
# =========================================================================
with tab1:
    st.markdown("### Hey Harshit, welcome to RecoverIQ Revenue Recovery")
    st.caption("Real-time revenue protection and autonomous failure recovery across your payment channels.")

    metrics = fetch_api("/metrics")

    if not metrics or "total_transactions" not in metrics:
        st.info("No transaction data loaded. Click **'Seed Data'** on the left sidebar to populate test transactions.")
    else:
        tot_tx = metrics.get("total_transactions", 0)
        tot_failed = metrics.get("total_failed_amount_inr", 0.0)
        tot_recovered = metrics.get("recovered_amount_inr", 0.0)
        rec_rate = metrics.get("recovery_rate_pct", 0.0)
        rec_count = metrics.get("recovered_count", 0)
        esc_count = metrics.get("escalated_count", 0)
        compliance = metrics.get("guardrail_compliance_pct", 100.0)

        # 4 Razorpay-styled Metric Cards
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""
            <div class="rzp-card">
                <div class="rzp-card-title">Failed Volume at Risk</div>
                <div class="rzp-card-val">{format_currency(tot_failed)}</div>
                <div class="rzp-card-sub">{tot_tx} Failed Transactions</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="rzp-card">
                <div class="rzp-card-title">Recovered Revenue</div>
                <div class="rzp-card-val" style="color:#059669;">+{format_currency(tot_recovered)}</div>
                <div class="rzp-card-sub" style="color:#059669;">{rec_count} Transactions Won Back</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="rzp-card">
                <div class="rzp-card-title">Recovery Success Rate</div>
                <div class="rzp-card-val" style="color:#0284C7;">{rec_rate:.1f}%</div>
                <div class="rzp-card-sub">{rec_count} of {tot_tx} Recovered</div>
            </div>
            """, unsafe_allow_html=True)
        with c4:
            st.markdown(f"""
            <div class="rzp-card">
                <div class="rzp-card-title">Guardrail Compliance</div>
                <div class="rzp-card-val" style="color:#D97706;">{compliance:.0f}%</div>
                <div class="rzp-card-sub">{esc_count} Flagged for Review</div>
            </div>
            """, unsafe_allow_html=True)

        # Clean Chart Breakdowns
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("#### 🎯 Recovery Action Breakdown")
            actions = metrics.get("action_distribution", {})
            if actions:
                color_map = {
                    "DELAY_AND_RETRY": "#0284C7",
                    "PAYMENT_LINK": "#10B981",
                    "ALTERNATE_METHOD": "#8B5CF6",
                    "ESCALATE": "#F59E0B",
                    "RETRY": "#3B82F6",
                    "NO_ACTION": "#EF4444",
                    "PENDING": "#94A3B8"
                }
                fig_act = px.pie(
                    names=list(actions.keys()),
                    values=list(actions.values()),
                    hole=0.6,
                    color=list(actions.keys()),
                    color_discrete_map=color_map,
                )
                fig_act.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    font={'color': "#0F172A", 'family': 'Inter'},
                    margin=dict(l=10, r=10, t=10, b=10),
                    height=260,
                )
                st.plotly_chart(fig_act, use_container_width=True)

        with col_g2:
            st.markdown("#### 🔍 Failure Root-Causes")
            fail_cats = metrics.get("failure_category_distribution", {})
            if fail_cats:
                df_fail = pd.DataFrame(list(fail_cats.items()), columns=["Category", "Count"]).sort_values(by="Count", ascending=True)
                fig_fail = px.bar(
                    df_fail,
                    x="Count",
                    y="Category",
                    orientation='h',
                    color_discrete_sequence=["#0066FF"],
                    text="Count"
                )
                fig_fail.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font={'color': "#0F172A", 'family': 'Inter'},
                    margin=dict(l=10, r=10, t=10, b=10),
                    height=260,
                    xaxis=dict(showgrid=True, gridcolor="#E2E8F0"),
                    yaxis=dict(showgrid=False)
                )
                st.plotly_chart(fig_fail, use_container_width=True)


# =========================================================================
# --- TAB 2: TRANSACTIONS & DECISION TRACE ---
# =========================================================================
with tab2:
    st.markdown("### Payment Transactions & Recovery Logs")
    st.caption("Search, filter, and inspect AI recovery traces for individual customer transactions.")

    c_f1, c_f2, c_f3 = st.columns([2, 1, 1])
    with c_f1:
        search_kw = st.text_input("Search Transaction ID or Customer Name", placeholder="e.g. txn_ or Sharma")
    with c_f2:
        flt_status = st.selectbox("Status", ["ALL", "FAILED", "RECOVERED", "ESCALATED", "ABANDONED"])
    with c_f3:
        max_recs = st.selectbox("Rows per page", [15, 30, 50, 100], index=0)

    params = {"limit": max_recs}
    if flt_status != "ALL":
        params["status"] = flt_status

    tx_list = fetch_api("/transactions", params=params)

    if tx_list and isinstance(tx_list, list):
        if search_kw:
            tx_list = [t for t in tx_list if search_kw.lower() in t.get("transaction_id", "").lower() or search_kw.lower() in t.get("customer_name", "").lower()]

        for tx in tx_list:
            tid = tx.get("transaction_id")
            amt = tx.get("amount_inr", 0.0)
            status = tx.get("status", "UNKNOWN")
            cust = tx.get("customer_name", "Customer")
            method = tx.get("payment_method", "N/A")
            bank = tx.get("issuer_bank", "N/A")
            action = tx.get("recovery_action", "PENDING")

            with st.expander(f"💳 {tid}  |  {cust}  |  {format_currency(amt)}  |  {method} ({bank})  |  Action: {action}"):
                c_d1, c_d2 = st.columns(2)
                with c_d1:
                    st.markdown("**Customer & Payment Details**")
                    st.write(f"- **Customer Name:** {cust}")
                    st.write(f"- **Segment:** `{tx.get('customer_segment', 'STANDARD')}`")
                    st.write(f"- **Amount:** {format_currency(amt)}")
                    st.write(f"- **Method / Bank:** {method} • {bank}")
                with c_d2:
                    st.markdown("**Failure Diagnosis**")
                    st.write(f"- **Failure Category:** `{tx.get('failure_category')}`")
                    st.write(f"- **Error Code:** `{tx.get('error_code')}`")
                    st.write(f"- **Error Reason:** `{tx.get('error_reason')}`")
                    st.write(f"- **Status:** {get_status_badge(status)}", unsafe_allow_html=True)

                # Fetch and render AI Decision Trace
                logs = fetch_api(f"/logs/{tid}")
                if logs and isinstance(logs, list):
                    st.markdown("---")
                    st.markdown("**🧠 AI Reasoning Trace & Action Plan**")
                    for log in logs:
                        try:
                            out = json.loads(log.get("output_data_json", "{}"))
                            if out.get("decision"):
                                d = out.get("decision")
                                st.info(f"**Recommended Action:** `{d.get('recommended_action')}` (Confidence: {d.get('confidence_score', 0):.0%})\n\n**Reasoning:** {d.get('reasoning')}")
                                if d.get("notification_message"):
                                    st.success(f"💬 **Outbound Customer Template ({d.get('communication_channel')}):**\n\n_{d.get('notification_message')}_")
                            elif out.get("result"):
                                r = out.get("result")
                                if not r.get("passed"):
                                    st.warning(f"🛑 **Guardrails Applied:** {', '.join(r.get('checks_blocked', []))} ➔ Action Modified to: `{r.get('final_action')}`")
                        except Exception:
                            pass

                if status == "FAILED":
                    if st.button(f"⚡ Execute Recovery on {tid}", key=f"btn_{tid}"):
                        with st.spinner("Executing..."):
                            post_api(f"/recovery/{tid}/execute")
                            st.success("Recovery Executed!")
                            st.rerun()
    else:
        st.info("No transactions found.")


# =========================================================================
# --- TAB 3: BASELINE VS. AI UPLIFT BENCHMARK ---
# =========================================================================
with tab3:
    st.markdown("### Comparative Benchmark: Naive Baseline vs. RecoverIQ AI")
    st.caption("Empirical demonstration of money recovered and false-action reduction across an identical 50-transaction evaluation batch.")

    if st.button("⚖️ Run Side-by-Side Benchmark", type="primary"):
        with st.spinner("Executing benchmark simulation..."):
            comp = fetch_api("/compare", params={"count": 50})
            if comp:
                st.session_state["comparison_report"] = comp
                st.success("Benchmark completed!")

    if "comparison_report" in st.session_state and st.session_state["comparison_report"]:
        comp = st.session_state["comparison_report"]
        bl = comp.get("baseline", {})
        riq = comp.get("recoveriq", {})
        uplift_rate = comp.get("recovery_rate_uplift_pct", 0.0)
        uplift_rev = comp.get("revenue_uplift_inr", 0.0)
        uplift_rev_pct = comp.get("revenue_uplift_pct", 0.0)
        false_action_imp = comp.get("false_action_improvement_pct", 0.0)

        st.markdown(f"""
        <div style="background-color:#ECFDF5; border:1px solid #A7F3D0; border-radius:8px; padding:16px; margin: 16px 0;">
            <h4 style="margin:0; color:#065F46;">🏆 Net Uplift: +{format_currency(uplift_rev)} ({uplift_rev_pct:.1f}% more revenue recovered)</h4>
            <p style="margin:4px 0 0 0; color:#047857; font-size:13px;">{comp.get('summary', '')}</p>
        </div>
        """, unsafe_allow_html=True)

        cb1, cb2, cb3, cb4 = st.columns(4)
        with cb1:
            st.metric(label="Baseline Recovery Rate", value=f"{bl.get('recovery_rate_pct', 0):.1f}%", delta=format_currency(bl.get('recovered_amount_inr', 0)), delta_color="off")
        with cb2:
            st.metric(label="RecoverIQ AI Recovery", value=f"{riq.get('recovery_rate_pct', 0):.1f}%", delta=f"+{uplift_rate:.1f}% rate ({format_currency(riq.get('recovered_amount_inr', 0))})")
        with cb3:
            st.metric(label="Net Revenue Uplift", value=format_currency(uplift_rev), delta=f"+{uplift_rev_pct:.1f}% uplift")
        with cb4:
            st.metric(label="False-Action Reduction", value=f"{false_action_imp:.1f}%", delta="Safe Guardrails")

        st.markdown("#### Comparison Charts")
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            df_r = pd.DataFrame({
                "Strategy": ["Naive Single-Retry Baseline", "RecoverIQ AI Agent"],
                "Recovery Rate (%)": [bl.get('recovery_rate_pct', 0), riq.get('recovery_rate_pct', 0)]
            })
            fig_r = px.bar(df_r, x="Strategy", y="Recovery Rate (%)", color="Strategy",
                           color_discrete_map={"Naive Single-Retry Baseline": "#94A3B8", "RecoverIQ AI Agent": "#10B981"}, text="Recovery Rate (%)")
            fig_r.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font={'color': "#0F172A", 'family': 'Inter'}, showlegend=False, height=280)
            st.plotly_chart(fig_r, use_container_width=True)

        with col_b2:
            df_v = pd.DataFrame({
                "Strategy": ["Naive Single-Retry Baseline", "RecoverIQ AI Agent"],
                "Recovered Amount (₹)": [bl.get('recovered_amount_inr', 0), riq.get('recovered_amount_inr', 0)]
            })
            fig_v = px.bar(df_v, x="Strategy", y="Recovered Amount (₹)", color="Strategy",
                           color_discrete_map={"Naive Single-Retry Baseline": "#94A3B8", "RecoverIQ AI Agent": "#0066FF"}, text="Recovered Amount (₹)")
            fig_v.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font={'color': "#0F172A", 'family': 'Inter'}, showlegend=False, height=280)
            st.plotly_chart(fig_v, use_container_width=True)


# =========================================================================
# --- TAB 4: ESCALATIONS & GUARDRAILS QUEUE ---
# =========================================================================
with tab4:
    st.markdown("### Human-in-the-Loop Review Desk")
    st.caption("Transactions flagged by deterministic guardrails (High-Value >₹50,000 or Retry Limits) held for operator approval.")

    escalations = fetch_api("/escalations")

    if escalations and isinstance(escalations, list):
        unresolved = [e for e in escalations if not e.get("resolved")]
        st.write(f"**{len(unresolved)}** Pending Human Escalations:")

        for esc in escalations:
            eid = esc.get("escalation_id", "")
            tx_id = esc.get("transaction_id", "")
            amt = esc.get("amount_inr", 0.0)
            reason = esc.get("reason", "")
            priority = esc.get("priority", "MEDIUM")
            resolved = esc.get("resolved", False)
            cust = esc.get("customer_name", "Customer")

            with st.expander(f"[{priority}] {eid} | {cust} ({format_currency(amt)}) | {'✅ Resolved' if resolved else '⚠️ Pending Review'}"):
                c1, c2 = st.columns(2)
                with c1:
                    st.write("**Transaction ID:**", tx_id)
                    st.write("**Customer:**", cust)
                    st.write("**Amount:**", format_currency(amt))
                    st.write("**Method / Bank:**", f"{esc.get('payment_method')} ({esc.get('issuer_bank')})")
                with c2:
                    st.write("**Flagged Reason:**", reason)
                    st.write("**Priority:**", priority)
                    st.write("**Created At:**", esc.get("created_at", "N/A"))

                if not resolved:
                    notes = st.text_input("Resolution Notes", key=f"notes_{eid}", placeholder="e.g. Approved for manual VIP bank transfer")
                    if st.button("✅ Mark as Resolved", key=f"res_{eid}"):
                        res_out = post_api(f"/escalations/{eid}/resolve", json_body={"notes": notes})
                        if res_out:
                            st.success("Escalation resolved!")
                            st.rerun()
                else:
                    st.info(f"**Resolution Notes:** {esc.get('resolution_notes', 'N/A')} (Resolved at: {esc.get('resolved_at')})")
    else:
        st.success("🎉 No pending escalations in queue!")
