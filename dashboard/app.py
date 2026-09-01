import streamlit as st
import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List
import json
from datetime import datetime

# --- CONFIG & CONSTANTS ---
API_URL = "http://localhost:8000"
APP_TITLE = "RecoverIQ — AI Revenue Recovery Agent"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for dark/professional fintech theme
st.markdown("""
    <style>
    .stApp {
        background-color: #0E1117;
    }
    .metric-card {
        background-color: #1E2129;
        border-radius: 8px;
        padding: 16px;
        border-left: 4px solid #00C853;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .metric-label {
        font-size: 14px;
        color: #A0AABF;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 28px;
        font-weight: bold;
        color: #FFFFFF;
    }
    .status-badge {
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
    }
    .status-recovered { background-color: rgba(0, 200, 83, 0.2); color: #00C853; border: 1px solid #00C853; }
    .status-failed { background-color: rgba(255, 82, 82, 0.2); color: #FF5252; border: 1px solid #FF5252; }
    .status-escalated { background-color: rgba(255, 171, 0, 0.2); color: #FFAB00; border: 1px solid #FFAB00; }
    .status-progress { background-color: rgba(33, 150, 243, 0.2); color: #2196F3; border: 1px solid #2196F3; }
    .demo-box {
        background: linear-gradient(135deg, #1A1F2C 0%, #111827 100%);
        border: 1px solid #374151;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    </style>
""", unsafe_allow_html=True)


# --- HELPER FUNCTIONS ---
def format_currency(amount: float) -> str:
    """Format float into Indian Rupee format."""
    if amount is None:
        return "₹0.00"
    amount = float(amount)
    if amount >= 100000:
        return f"₹{amount/100000:,.2f} Lakhs"
    elif amount >= 1000:
        s, *d = str(float(amount)).partition(".")
        r = ",".join([s[x-2:x] for x in range(-3, -len(s), -2)][::-1] + [s[-3:]])
        return f"₹{r}{d[0]}{d[1][:2]}" if r else f"₹{amount:,.2f}"
    return f"₹{amount:,.2f}"


def get_status_badge(status: str) -> str:
    status_str = str(status).upper()
    if status_str in ["RECOVERED", "SUCCESS", "VERIFIED_SUCCESS"]:
        return f'<span class="status-badge status-recovered">{status_str}</span>'
    elif status_str in ["FAILED", "ABANDONED", "VERIFIED_FAILED"]:
        return f'<span class="status-badge status-failed">{status_str}</span>'
    elif status_str in ["ESCALATED", "BLOCKED"]:
        return f'<span class="status-badge status-escalated">{status_str}</span>'
    else:
        return f'<span class="status-badge status-progress">{status_str}</span>'


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


# --- SIDEBAR ---
with st.sidebar:
    st.title("💰 RecoverIQ")
    st.markdown("**AI Revenue Recovery Agent**")
    st.caption("Razorpay Buildathon 2026 • Track 03")
    st.divider()

    st.subheader("⚡ 1-Click SRS Demo Launcher")
    st.markdown("Instantly test the 4 core SRS evaluation scenarios:")

    if st.button("🎯 Run All 4 SRS Scenarios", type="primary", use_container_width=True):
        with st.spinner("Executing 4 SRS Demo Scenarios across Agent Pipeline..."):
            demo_res = post_api("/demo/scenarios")
            if demo_res and "scenarios" in demo_res:
                st.session_state["demo_scenarios_results"] = demo_res["scenarios"]
                st.success("✅ 4 Demo Scenarios Executed Successfully!")
                st.rerun()

    demo_choice = st.selectbox(
        "Or Pick Individual Scenario:",
        [
            "1. Transient Bank Timeout (Retry)",
            "2. Method Optimization (Alt Link)",
            "3. Retry Limit Reached (Escalate)",
            "4. Gateway Timeout (Verifier)",
        ],
    )
    if st.button("▶️ Run Selected Scenario", use_container_width=True):
        scenario_idx = int(demo_choice[0]) - 1
        with st.spinner(f"Executing Scenario {scenario_idx + 1}..."):
            demo_res = post_api("/demo/scenarios")
            if demo_res and "scenarios" in demo_res:
                st.session_state["demo_scenarios_results"] = [demo_res["scenarios"][scenario_idx]]
                st.success(f"✅ Scenario {scenario_idx + 1} Executed!")
                st.rerun()

    st.divider()
    st.subheader("Batch Operations")
    seed_count = st.slider("Evaluation Batch Size", min_value=100, max_value=1000, value=500, step=100)
    use_ai = st.toggle("Enable AI Reasoner", value=True)

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🌱 Seed Data", use_container_width=True):
            with st.spinner(f"Generating {seed_count} synthetic transactions..."):
                res = post_api("/seed", params={"count": seed_count, "seed": 42})
                if res:
                    st.success(f"Seeded {res.get('count')} records ({format_currency(res.get('total_amount_inr', 0))})")
                    st.rerun()

    with col_btn2:
        if st.button("🚀 Run Pipeline", use_container_width=True):
            with st.spinner("Processing batch through AI Recovery Agent..."):
                res = post_api("/run", params={"use_ai": str(use_ai).lower(), "batch_size": 100})
                if res:
                    st.success(f"Recovered {format_currency(res.get('total_recovered_inr', 0))} across {res.get('processed')} records")
                    st.rerun()

    st.divider()
    # Health check
    health = fetch_api("/health")
    if health:
        st.caption(f"🟢 **API Status**: {health.get('status', 'OK')} | v{health.get('version', '0.1.0')}")
    else:
        st.caption("🔴 **API Offline** (Run `uvicorn api.main:app --reload`)")


# --- SRS DEMO SCENARIOS BANNER (IF TRIGGERED) ---
if "demo_scenarios_results" in st.session_state and st.session_state["demo_scenarios_results"]:
    with st.expander("🎯 **SRS Demo Scenarios Execution Report (Click to expand/collapse)**", expanded=True):
        st.markdown("### 🔍 Live Agent Decision Trace & Outcome Verification")
        scs = st.session_state["demo_scenarios_results"]
        for sc in scs:
            st.markdown(f"""
            <div class="demo-box">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h4 style="margin:0; color:#00E5FF;">{sc.get('title')}</h4>
                    {get_status_badge(sc.get('verification_status'))}
                </div>
                <p style="color:#A0AABF; margin: 4px 0 8px 0;">{sc.get('description')}</p>
                <div style="font-size:13px; line-height:1.6;">
                    <b>Transaction ID:</b> <code>{sc.get('transaction_id')}</code> | <b>Amount:</b> {format_currency(sc.get('amount_inr'))} <br/>
                    <b>Expected Action:</b> <code>{sc.get('expected_action')}</code> | <b>Actual AI Action:</b> <code>{sc.get('actual_action')}</code> | <b>Confidence:</b> {sc.get('confidence_score'):.0%}<br/>
                    <b>Guardrail Check:</b> {'✅ Passed (No policy violation)' if sc.get('guardrail_passed') else f"🛑 Modified ({', '.join(sc.get('guardrail_modifications', []))})"}<br/>
                    <b>AI Reasoner Trace:</b> <i>{sc.get('reasoning')}</i>
                </div>
            </div>
            """, unsafe_allow_html=True)
        if st.button("❌ Close Demo Report"):
            st.session_state["demo_scenarios_results"] = None
            st.rerun()


# --- MAIN LAYOUT TABS ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Recovery Dashboard", 
    "⚖️ Baseline vs AI Uplift", 
    "🔍 Transaction Explorer", 
    "📋 Audit Trail & Escalations"
])


# ==========================================
# --- TAB 1: RECOVERY DASHBOARD ---
# ==========================================
with tab1:
    st.header("Real-Time Revenue Recovery Performance")
    metrics = fetch_api("/metrics")

    if not metrics or "total_transactions" not in metrics:
        st.info("No transaction data loaded. Please click **'Seed Data'** and **'Run Recovery Pipeline'** in the sidebar.")
    else:
        tot_tx = metrics.get("total_transactions", 0)
        tot_failed = metrics.get("total_failed_amount_inr", 0.0)
        tot_recovered = metrics.get("recovered_amount_inr", 0.0)
        rec_rate = metrics.get("recovery_rate_pct", 0.0)
        rec_count = metrics.get("recovered_count", 0)
        esc_count = metrics.get("escalated_count", 0)
        compliance = metrics.get("guardrail_compliance_pct", 100.0)

        # Top KPI Cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="Total Revenue at Risk", value=format_currency(tot_failed), delta=f"{tot_tx} Transactions", delta_color="off")
        with col2:
            st.metric(label="Recovered Revenue", value=format_currency(tot_recovered), delta=f"{rec_count} Recovered ({rec_rate:.1f}%)")
        with col3:
            st.metric(label="Recovery Success Rate", value=f"{rec_rate:.1f}%", delta=f"{rec_count}/{tot_tx} Recovered")
        with col4:
            st.metric(label="Guardrail Compliance", value=f"{compliance:.0f}%", delta=f"{esc_count} Escalated", delta_color="off")

        st.divider()

        # Visualizations
        col_c1, col_c2 = st.columns(2)

        with col_c1:
            st.subheader("Recovery Rate Gauge")
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=rec_rate,
                number={'suffix': "%", 'font': {'color': "#FFFFFF"}},
                domain={'x': [0, 1], 'y': [0, 1]},
                gauge={
                    'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
                    'bar': {'color': "#00C853"},
                    'bgcolor': "#1E2129",
                    'steps': [
                        {'range': [0, 25], 'color': 'rgba(255, 82, 82, 0.4)'},
                        {'range': [25, 50], 'color': 'rgba(255, 171, 0, 0.4)'},
                        {'range': [50, 100], 'color': 'rgba(0, 200, 83, 0.4)'}
                    ],
                }
            ))
            fig_gauge.update_layout(height=320, margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor="rgba(0,0,0,0)", font={'color': "#FFFFFF"})
            st.plotly_chart(fig_gauge, use_container_width=True)

        with col_c2:
            st.subheader("Recovery Action Distribution")
            actions = metrics.get("action_distribution", {})
            if actions:
                fig_pie = px.pie(
                    names=list(actions.keys()),
                    values=list(actions.values()),
                    hole=0.45,
                    color_discrete_sequence=px.colors.qualitative.Prism
                )
                fig_pie.update_layout(height=320, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor="rgba(0,0,0,0)", font={'color': "#FFFFFF"})
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.write("No recovery action data.")

        # Failure Category Breakdown
        st.subheader("Failure Category Distribution")
        fail_cats = metrics.get("failure_category_distribution", {})
        if fail_cats:
            df_fail = pd.DataFrame(list(fail_cats.items()), columns=["Failure Category", "Count"]).sort_values("Count", ascending=True)
            fig_bar = px.bar(
                df_fail, x="Count", y="Failure Category", orientation='h',
                color="Count", color_continuous_scale="Viridis", text="Count"
            )
            fig_bar.update_layout(height=280, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor="rgba(0,0,0,0)", font={'color': "#FFFFFF"})
            st.plotly_chart(fig_bar, use_container_width=True)


# ==========================================
# --- TAB 2: BASELINE VS RECOVERIQ AI ---
# ==========================================
with tab2:
    st.header("Comparative Benchmark: Naive Baseline vs. RecoverIQ AI")
    st.markdown(
        "Demonstrates measured money recovered across a standardized 200-transaction evaluation batch "
        "comparing **Single-Retry Baseline** against **RecoverIQ AI Agent** with contextual intervention & guardrails."
    )

    if st.button("⚖️ Run Live Benchmark Comparison", type="primary"):
        with st.spinner("Executing side-by-side benchmark simulation..."):
            comp = fetch_api("/compare", params={"count": 50})
            if comp:
                st.session_state["comparison_report"] = comp
                st.success("Benchmark completed successfully!")

    if "comparison_report" in st.session_state and st.session_state["comparison_report"]:
        comp = st.session_state["comparison_report"]
        bl = comp.get("baseline", {})
        riq = comp.get("recoveriq", {})
        uplift_rate = comp.get("recovery_rate_uplift_pct", 0.0)
        uplift_rev = comp.get("revenue_uplift_inr", 0.0)
        uplift_rev_pct = comp.get("revenue_uplift_pct", 0.0)
        false_action_imp = comp.get("false_action_improvement_pct", 0.0)

        st.divider()
        st.markdown(f"### 🏆 Uplift Summary: **+{format_currency(uplift_rev)} ({uplift_rev_pct:.1f}% more revenue recovered)**")
        st.info(comp.get("summary", ""))

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric(
                label="Baseline Recovery Rate",
                value=f"{bl.get('recovery_rate_pct', 0):.1f}%",
                delta=format_currency(bl.get('recovered_amount_inr', 0)),
                delta_color="off"
            )
        with c2:
            st.metric(
                label="RecoverIQ AI Recovery",
                value=f"{riq.get('recovery_rate_pct', 0):.1f}%",
                delta=f"+{uplift_rate:.1f}% rate ({format_currency(riq.get('recovered_amount_inr', 0))})"
            )
        with c3:
            st.metric(
                label="Net Revenue Uplift",
                value=format_currency(uplift_rev),
                delta=f"+{uplift_rev_pct:.1f}%"
            )
        with c4:
            st.metric(
                label="False-Action Reduction",
                value=f"{false_action_imp:.1f}%",
                delta="Safe Guardrails"
            )

        st.subheader("Performance Comparison")
        col_bar1, col_bar2 = st.columns(2)

        with col_bar1:
            df_rates = pd.DataFrame({
                "Strategy": ["Naive Baseline (Fixed Retry)", "RecoverIQ AI Agent"],
                "Recovery Rate (%)": [bl.get('recovery_rate_pct', 0), riq.get('recovery_rate_pct', 0)]
            })
            fig_r = px.bar(df_rates, x="Strategy", y="Recovery Rate (%)", color="Strategy",
                           color_discrete_map={"Naive Baseline (Fixed Retry)": "#64748B", "RecoverIQ AI Agent": "#00C853"}, text="Recovery Rate (%)")
            fig_r.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "#FFFFFF"}, showlegend=False, height=300)
            st.plotly_chart(fig_r, use_container_width=True)

        with col_bar2:
            df_revs = pd.DataFrame({
                "Strategy": ["Naive Baseline (Fixed Retry)", "RecoverIQ AI Agent"],
                "Recovered Amount (₹)": [bl.get('recovered_amount_inr', 0), riq.get('recovered_amount_inr', 0)]
            })
            fig_rev = px.bar(df_revs, x="Strategy", y="Recovered Amount (₹)", color="Strategy",
                             color_discrete_map={"Naive Baseline (Fixed Retry)": "#64748B", "RecoverIQ AI Agent": "#00E5FF"}, text="Recovered Amount (₹)")
            fig_rev.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "#FFFFFF"}, showlegend=False, height=300)
            st.plotly_chart(fig_rev, use_container_width=True)


# ==========================================
# --- TAB 3: TRANSACTION EXPLORER ---
# ==========================================
with tab3:
    st.header("Transaction Explorer & Decision Traces")

    col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
    with col_f1:
        tx_status = st.selectbox("Filter Status", ["ALL", "FAILED", "RECOVERED", "ESCALATED", "ABANDONED", "RECOVERY_IN_PROGRESS"])
    with col_f2:
        tx_limit = st.number_input("Limit", min_value=10, max_value=200, value=30, step=10)
    with col_f3:
        fetch_btn = st.button("🔍 Load Records", use_container_width=True)

    params = {"limit": tx_limit}
    if tx_status != "ALL":
        params["status"] = tx_status

    txs = fetch_api("/transactions", params=params)

    if txs and isinstance(txs, list):
        st.write(f"Showing **{len(txs)}** transactions:")
        for tx in txs:
            tid = tx.get("transaction_id", "")
            amt = tx.get("amount_inr", 0)
            status = tx.get("status", "UNKNOWN")
            method = tx.get("payment_method", "UNKNOWN")
            bank = tx.get("issuer_bank", "UNKNOWN")
            customer = tx.get("customer_name", "Customer")
            category = tx.get("failure_category", "UNKNOWN")

            with st.expander(f"{tid} | {customer} | {format_currency(amt)} | {method} ({bank}) | {status}"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.write("**Customer:**", customer)
                    st.write("**Segment:**", tx.get("customer_segment", "STANDARD"))
                    st.write("**Customer LTV:**", format_currency(tx.get("customer_ltv_inr", 0)))
                with c2:
                    st.write("**Payment Method:**", f"{method} / {bank}")
                    st.write("**Failure Category:**", category)
                    st.write("**Error Reason:**", tx.get("error_reason", "N/A"))
                with c3:
                    st.markdown(f"**Status:** {get_status_badge(status)}", unsafe_allow_html=True)
                    st.write("**Attempts:**", tx.get("attempt_count", 1))
                    if tx.get("recovered_amount_inr", 0) > 0:
                        st.write("**Amount Recovered:**", format_currency(tx.get("recovered_amount_inr", 0)))

                # Decision details & Audit Logs
                tx_details = fetch_api(f"/transactions/{tid}")
                if tx_details:
                    logs = tx_details.get("audit_logs", [])
                    attempts = tx_details.get("recovery_attempts", [])

                    if logs:
                        st.divider()
                        st.subheader("📋 Decision Trace & Audit Stages")
                        for log in logs:
                            stage = log.get("stage", "STAGE")
                            duration = log.get("duration_ms", 0.0)
                            st.markdown(f"**Stage: `{stage}`** ({duration:.1f}ms)")
                            
                            # Parse and display input/output data
                            try:
                                in_data = json.loads(log.get("input_data_json", "{}"))
                                out_data = json.loads(log.get("output_data_json", "{}"))
                                if out_data.get("decision"):
                                    d = out_data.get("decision")
                                    st.info(f"**AI Recommendation:** `{d.get('recommended_action')}` (Confidence: {d.get('confidence_score', 0):.0%})\n\n**Reasoning:** {d.get('reasoning')}")
                                    if d.get("notification_message"):
                                        st.success(f"💬 **Customer Message Template ({d.get('communication_channel')}):**\n\n_{d.get('notification_message')}_")
                                elif out_data.get("result"):
                                    r = out_data.get("result")
                                    if not r.get("passed"):
                                        st.error(f"🛑 **Guardrails Triggered:** {', '.join(r.get('checks_blocked', []))} $\\rightarrow$ Final Action Modified to: `{r.get('final_action')}`")
                            except Exception:
                                pass

                # Manual Execution Button if still failed
                if status == "FAILED":
                    if st.button(f"⚡ Execute Recovery on {tid}", key=f"exec_{tid}"):
                        with st.spinner("Processing..."):
                            exec_res = post_api(f"/recovery/{tid}/execute")
                            if exec_res:
                                st.success("Recovery Executed!")
                                st.rerun()
    else:
        st.info("No transactions found. Click **'Seed Data'** on the sidebar.")


# ==========================================
# --- TAB 4: AUDIT TRAIL & ESCALATIONS ---
# ==========================================
with tab4:
    st.header("Compliance Audit Trail & Escalation Queue")

    sub1, sub2 = st.tabs(["🚨 Human Review Queue (Escalations)", "🛡️ Guardrail Rules & Policy Engine"])

    with sub1:
        st.subheader("Transactions Flagged for Human Review")
        escalations = fetch_api("/escalations")

        if escalations and isinstance(escalations, list):
            df_esc = pd.DataFrame(escalations)
            unresolved = [e for e in escalations if not e.get("resolved")]
            st.write(f"**{len(unresolved)}** Pending Escalations:")

            for esc in escalations:
                eid = esc.get("escalation_id", "")
                tx_id = esc.get("transaction_id", "")
                amt = esc.get("amount_inr", 0.0)
                reason = esc.get("reason", "")
                priority = esc.get("priority", "MEDIUM")
                resolved = esc.get("resolved", False)
                cust = esc.get("customer_name", "Customer")

                with st.expander(f"[{priority}] {eid} | {cust} ({format_currency(amt)}) | {'✅ Resolved' if resolved else '⚠️ Pending'}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write("**Transaction ID:**", tx_id)
                        st.write("**Customer:**", cust)
                        st.write("**Amount:**", format_currency(amt))
                        st.write("**Payment Method / Bank:**", f"{esc.get('payment_method')} ({esc.get('issuer_bank')})")
                    with c2:
                        st.write("**Escalation Reason:**", reason)
                        st.write("**Priority:**", priority)
                        st.write("**Created At:**", esc.get("created_at", "N/A"))

                    if not resolved:
                        notes = st.text_input("Human Operator Resolution Notes", key=f"notes_{eid}")
                        if st.button("✅ Mark as Resolved", key=f"res_{eid}"):
                            res_out = post_api(f"/escalations/{eid}/resolve", json_body={"notes": notes})
                            if res_out:
                                st.success("Escalation resolved!")
                                st.rerun()
                    else:
                        st.info(f"**Resolution Notes:** {esc.get('resolution_notes', 'N/A')} (Resolved at: {esc.get('resolved_at')})")
        else:
            st.success("No pending escalations found! 🎉")

    with sub2:
        st.subheader("Active Guardrails & Safety Parameters")
        st.markdown("""
        RecoverIQ enforces deterministic safety guardrails before any recovery action is executed:
        - **Max 2 Automated Retries**: Prevents payment network throttling and customer spam.
        - **High-Value Cap (>₹50,000)**: Automatically pauses automated retries on large sums and routes to human approval.
        - **TRAI Quiet Hours (9 PM - 8 AM IST)**: Holds customer-facing communications and schedules morning delivery.
        - **Already-Recovered Check**: Verifier inspects payment status to eliminate duplicate debits.
        - **Low AI Confidence Threshold (<0.60)**: Falls back to deterministic rule engine when confidence is insufficient.
        - **Idempotency & Deduplication**: Prevents duplicate execution on webhook retries.
        """)
