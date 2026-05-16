import streamlit as st
import pandas as pd
import asyncio
from sqlalchemy import select
from database.connection import AsyncSessionLocal
from database.models import AuditLog

st.set_page_config(page_title="Transaction Risk Dashboard", page_icon="🛡️", layout="wide")

# Fetch data asynchronously using your existing SQLAlchemy setup
async def fetch_data():
    async with AsyncSessionLocal() as session:
        stmt = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(500)
        result = await session.execute(stmt)
        logs = result.scalars().all()
        
        if not logs:
            return pd.DataFrame()
            
        data = []
        for log in logs:
            data.append({
                "transaction_id": log.transaction_id,
                "timestamp": log.timestamp,
                "user_id": log.user_id,
                "decision": log.decision.upper(),
                "risk_score": log.combined_risk_score,
                "amount": log.transaction.get("amount", 0.0)
            })
        return pd.DataFrame(data)

# Load data into Streamlit
@st.cache_data(ttl=5) # Refreshes every 5 seconds
def load_data():
    return asyncio.run(fetch_data())

st.title("🛡️ Transaction Risk Operations Center")
st.markdown("Real-time monitoring of the Fraud Detection Gateway.")

df = load_data()

if df.empty:
    st.warning("No transactions found in the database yet. Run `test_transaction.py` to generate some!")
else:
    # Top Row Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Transactions", len(df))
    col2.metric("Escalated (Manual Review)", len(df[df['decision'] == 'ESCALATE_TO_HUMAN']))
    col3.metric("Average Risk Score", f"{df['risk_score'].mean():.2f}")
    col4.metric("Total Volume Blocked", f"${df[df['decision'] == 'ESCALATE_TO_HUMAN']['amount'].sum():,.2f}")

    st.divider()

    # Charts
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("Decision Breakdown")
        decision_counts = df['decision'].value_counts().reset_index()
        decision_counts.columns = ['Decision', 'Count']
        st.bar_chart(decision_counts, x='Decision', y='Count', color='#ff4b4b')
        
    with col_chart2:
        st.subheader("Risk Score Distribution")
        # Creating a simple histogram using Streamlit's native charting
        hist_data = df['risk_score'].value_counts(bins=10).sort_index().reset_index()
        hist_data.columns = ['Risk Range', 'Count']
        hist_data['Risk Range'] = hist_data['Risk Range'].astype(str)
        st.bar_chart(hist_data, x='Risk Range', y='Count', color='#0068c9')

    st.divider()

    # Data Table
    st.subheader("Recent Audit Logs")
    st.dataframe(
        df.style.applymap(
            lambda x: 'background-color: #ffcccc; color: black;' if x == 'ESCALATE_TO_HUMAN' else '', 
            subset=['decision']
        ),
        use_container_width=True,
        hide_index=True
    )
