import streamlit as st
import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List
import time

# --- CONFIG & CONSTANTS ---
API_URL = "http://localhost:8000"
APP_TITLE = "RecoverIQ — AI Revenue Recovery"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for dark/professional theme with blues and greens
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
    .status-recovered { background-color: rgba(0, 200, 83, 0.2); color: #00C853; }
    .status-failed { background-color: rgba(255, 82, 82, 0.2); color: #FF5252; }
    .status-escalated { background-color: rgba(255, 171, 0, 0.2); color: #FFAB00; }
    </style>
""", unsafe_allow_html=True)


# --- HELPER FUNCTIONS ---
def format_currency(amount: float) -> str:
    # Basic Indian Rupee formatting placeholder
    s, *d = str(float(amount)).partition(".")
    r = ",".join([s[x-2:x] for x in range(-3, -len(s), -2)][::-1] + [s[-3:]])
    return f"₹{r}{d[0]}{d[1][:2]}" if amount >= 1000 else f"₹{amount:,.2f}"

def get_status_badge(status: str) -> str:
    status_lower = status.lower()
    if status_lower in ["recovered", "success"]:
        return f'<span class="status-badge status-recovered">{status}</span>'
    elif status_lower in ["failed", "abandoned"]:
        return f'<span class="status-badge status-failed">{status}</span>'
    else:
        return f'<span class="status-badge status-escalated">{status}</span>'

# --- API CLIENT ---
@st.cache_data(ttl=5)
def fetch_api(endpoint: str, params: Dict = None) -> Dict:
    try:
        with httpx.Client(base_url=API_URL, timeout=10.0) as client:
            resp = client.get(endpoint, params=params)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        st.error(f"API Error ({endpoint}): {str(e)}")
        return {}

def post_api(endpoint: str, params: Dict = None) -> Dict:
    try:
        with httpx.Client(base_url=API_URL, timeout=30.0) as client:
            resp = client.post(endpoint, params=params)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        st.error(f"API Error ({endpoint}): {str(e)}")
        return {}


# --- SIDEBAR ---
with st.sidebar:
    st.title("💰 RecoverIQ")
    st.markdown("*AI Revenue Recovery*")
    st.divider()
    
    st.subheader("Settings")
    seed_count = st.slider("Seed Transaction Count", min_value=100, max_value=1000, value=500, step=100)
    use_ai = st.toggle("Enable AI Agent", value=True)
    
    st.divider()
    st.subheader("Actions")
    
    if st.button("🌱 Seed Data", use_container_width=True):
        with st.spinner("Seeding data..."):
            res = post_api("/seed", params={"count": seed_count, "seed": 42})
            if res:
                st.success(f"Seeded {res.get('count')} records. Total: {format_currency(res.get('total_amount_inr', 0))}")
                
    if st.button("🚀 Run Recovery Pipeline", type="primary", use_container_width=True):
        with st.spinner("Running AI Pipeline..."):
            res = post_api("/run", params={"use_ai": str(use_ai).lower()})
            if res:
                st.success(f"Processed: {res.get('processed')} | Recovered: {format_currency(res.get('total_recovered_inr', 0))}")
                
    st.divider()
    
    # API Health
    health = fetch_api("/health")
    if health:
        st.caption(f"🟢 API Status: {health.get('status', 'OK')} | v{health.get('version', '1.0')}")
    else:
        st.caption("🔴 API Offline")


# --- MAIN LAYOUT ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Recovery Dashboard", 
    "⚖️ Baseline vs AI", 
    "🔍 Transaction Explorer", 
    "📋 Audit Trail"
])

# --- TAB 1: RECOVERY DASHBOARD ---
with tab1:
    st.header("Real-time Recovery Metrics")
    metrics = fetch_api("/metrics")
    
    if not metrics:
        st.info("No metrics available. Please seed data and run the pipeline.")
    else:
        # Top Row Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        tot_failed = metrics.get('total_failed_amount_inr', 0)
        tot_recovered = metrics.get('total_recovered_amount_inr', 0)
        rec_rate = metrics.get('recovery_rate_percent', 0)
        compliance = metrics.get('guardrail_compliance_percent', 100) # Assuming 100 if not present
        
        with col1:
            st.metric("Total Failed Amount", format_currency(tot_failed))
        with col2:
            st.metric("Recovered Amount", format_currency(tot_recovered), delta=f"{rec_rate}%")
        with col3:
            st.metric("Recovery Rate", f"{rec_rate}%")
        with col4:
            st.metric("Guardrail Compliance", f"{compliance}%")
            
        st.divider()
        
        # Charts Row
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("Recovery Performance")
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=rec_rate,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Recovery Rate (%)", 'font': {'color': '#A0AABF'}},
                gauge={
                    'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
                    'bar': {'color': "#00C853"},
                    'bgcolor': "#1E2129",
                    'steps': [
                        {'range': [0, 30], 'color': '#FF5252'},
                        {'range': [30, 60], 'color': '#FFAB00'},
                        {'range': [60, 100], 'color': 'rgba(0, 200, 83, 0.3)'}
                    ],
                }
            ))
            fig_gauge.update_layout(height=350, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor="rgba(0,0,0,0)", font={'color': "#FFFFFF"})
            st.plotly_chart(fig_gauge, use_container_width=True)
            
        with col_chart2:
            st.subheader("Action Distribution")
            actions = metrics.get("action_distribution", {})
            if actions:
                fig_pie = px.pie(
                    names=list(actions.keys()), 
                    values=list(actions.values()),
                    hole=0.4,
                    color_discrete_sequence=px.colors.sequential.Teal
                )
                fig_pie.update_layout(height=350, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor="rgba(0,0,0,0)", font={'color': "#FFFFFF"})
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.write("No actions data available.")
                
        # Failure Categories
        st.subheader("Failure Category Breakdown")
        failures = metrics.get("failure_reasons", {})
        if failures:
            df_fail = pd.DataFrame(list(failures.items()), columns=["Reason", "Count"])
            fig_bar = px.bar(
                df_fail, x="Count", y="Reason", orientation='h',
                color="Count", color_continuous_scale="Reds"
            )
            fig_bar.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor="rgba(0,0,0,0)", font={'color': "#FFFFFF"})
            st.plotly_chart(fig_bar, use_container_width=True)


# --- TAB 2: BASELINE VS RECOVERIQ ---
with tab2:
    st.header("Baseline vs RecoverIQ AI")
    
    col_btn, _ = st.columns([1, 4])
    if col_btn.button("Run Comparison Analysis", key="btn_compare"):
        with st.spinner("Analyzing..."):
            comp = fetch_api("/compare")
            if comp:
                baseline = comp.get("baseline", {})
                recoveriq = comp.get("recoveriq", {})
                
                st.success("Analysis Complete!")
                
                col1, col2 = st.columns(2)
                
                # Baseline
                with col1:
                    st.markdown("### 📉 Baseline (Rule-based)")
                    st.metric("Recovery Rate", f"{baseline.get('recovery_rate_percent', 0)}%")
                    st.metric("Amount Recovered", format_currency(baseline.get('total_recovered_amount_inr', 0)))
                
                # RecoverIQ
                with col2:
                    st.markdown("### 🚀 RecoverIQ (AI Agent)")
                    rate_uplift = recoveriq.get('recovery_rate_percent', 0) - baseline.get('recovery_rate_percent', 0)
                    amt_uplift = recoveriq.get('total_recovered_amount_inr', 0) - baseline.get('total_recovered_amount_inr', 0)
                    
                    st.metric("Recovery Rate", f"{recoveriq.get('recovery_rate_percent', 0)}%", delta=f"{rate_uplift:.1f}% Uplift")
                    st.metric("Amount Recovered", format_currency(recoveriq.get('total_recovered_amount_inr', 0)), delta=format_currency(amt_uplift))
                
                # Chart
                st.subheader("Recovery Uplift Visualization")
                df_comp = pd.DataFrame({
                    "Approach": ["Baseline", "RecoverIQ"],
                    "Recovery Rate (%)": [baseline.get('recovery_rate_percent', 0), recoveriq.get('recovery_rate_percent', 0)],
                    "Recovered Amount (₹)": [baseline.get('total_recovered_amount_inr', 0), recoveriq.get('total_recovered_amount_inr', 0)]
                })
                
                fig_comp = px.bar(
                    df_comp, x="Approach", y="Recovery Rate (%)", 
                    color="Approach",
                    color_discrete_map={"Baseline": "#4A5568", "RecoverIQ": "#00C853"}
                )
                fig_comp.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "#FFFFFF"})
                st.plotly_chart(fig_comp, use_container_width=True)


# --- TAB 3: TRANSACTION EXPLORER ---
with tab3:
    st.header("Transaction Explorer")
    
    col_filt1, col_filt2 = st.columns(2)
    with col_filt1:
        tx_status = st.selectbox("Filter by Status", ["ALL", "FAILED", "RECOVERED", "ESCALATED", "ABANDONED"])
    with col_filt2:
        tx_limit = st.number_input("Limit", min_value=10, max_value=500, value=50)
        
    params = {"limit": tx_limit}
    if tx_status != "ALL":
        params["status"] = tx_status
        
    if st.button("Fetch Transactions"):
        txs = fetch_api("/transactions", params=params)
        if txs:
            for tx in txs:
                with st.expander(f"Tx: {tx.get('id')} | {format_currency(tx.get('amount_inr', 0))} | {tx.get('status')}"):
                    # Fetch details
                    details = fetch_api(f"/transactions/{tx.get('id')}")
                    if details:
                        col_dt1, col_dt2 = st.columns(2)
                        with col_dt1:
                            st.write("**Customer:**", details.get("customer_id"))
                            st.write("**Amount:**", format_currency(details.get("amount_inr", 0)))
                            st.write("**Initial Reason:**", details.get("failure_reason"))
                        with col_dt2:
                            st.markdown(f"**Status:** {get_status_badge(details.get('status', 'Unknown'))}", unsafe_allow_html=True)
                            
                        st.divider()
                        st.subheader("AI Reasoning & Actions")
                        
                        logs = fetch_api(f"/logs/{tx.get('id')}")
                        if logs:
                            for log in logs:
                                st.info(f"**Stage:** {log.get('stage')} | **Action:** {log.get('action_taken')} \n\n **Reasoning:** {log.get('ai_reasoning')}")
                                if log.get('guardrail_triggered'):
                                    st.error(f"🛑 Guardrail Blocked: {log.get('guardrail_reason')}")
                        else:
                            st.write("No audit logs available for this transaction.")
        else:
            st.info("No transactions found.")


# --- TAB 4: AUDIT TRAIL ---
with tab4:
    st.header("Global Audit & Escalations")
    
    subtab1, subtab2 = st.tabs(["Queue: Escalations", "System Logs"])
    
    with subtab1:
        st.subheader("Transactions Requiring Manual Review")
        escalations = fetch_api("/escalations")
        
        if escalations:
            df_esc = pd.DataFrame(escalations)
            if not df_esc.empty:
                # Select a few columns to show
                cols_to_show = ["id", "amount_inr", "failure_reason", "escalation_reason"]
                cols_present = [c for c in cols_to_show if c in df_esc.columns]
                st.dataframe(df_esc[cols_present], use_container_width=True)
        else:
            st.success("No pending escalations! 🎉")
            
    with subtab2:
        st.info("System logs typically show pipeline processing events here.")
        # Mocking system logs view as there's no direct global /logs endpoint defined in prompt (only /logs/{id})
        st.write("To view specific transaction logs, use the Transaction Explorer tab.")

