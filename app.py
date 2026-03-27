import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# --- CONFIG ---
st.set_page_config(page_title="Budget Tracker", layout="wide")

# 1. Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Sidebar Settings
st.sidebar.title("Settings")
user_email = st.sidebar.text_input("User Email", "your-email@example.com")
monthly_budget = st.sidebar.number_input("Monthly Budget", min_value=0, value=25000)

# 3. Load Data
try:
    # Read the sheet (Ensure the tab name is exactly 'Expenses')
    df = conn.read(worksheet="Expenses", ttl="0")
    
    # Filter for the logged in user (case-insensitive)
    df = df[df['email'].str.lower() == user_email.lower()]
    
    # --- HEADER METRICS ---
    total_spent = df['amount'].sum()
    remaining = monthly_budget - total_spent
    
    st.title("💰 Personal Budget Dashboard")
    
    col1, col2 = st.columns(2)
    col1.metric("Total Spent", f"₹{total_spent:,.2f}")
    col2.metric("Balance Remaining", f"₹{remaining:,.2f}")

    st.divider()

    # --- VISUALS ---
    if not df.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Spending by Category")
            # Creating a simple pie chart
            fig = px.pie(df, values='amount', names='category', hole=0.3)
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            st.subheader("Expense History")
            st.dataframe(df[['Date', 'item', 'amount', 'category']], use_container_width=True)
    else:
        st.warning(f"No data found for {user_email}. Check your sheet or sidebar email.")

except Exception as e:
    st.error(f"Connection Error: {e}")
    st.info("Check: 1. Is the Sheet shared with the service account? 2. Is the tab name 'Expenses'?")
