import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Personal Budget Tracker", page_icon="💰", layout="wide")

# --- 1. CONNECTION SETUP ---
# This looks for [connections.gsheets] in your Streamlit Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. SIDEBAR / USER SETTINGS ---
st.sidebar.title("👤 User Profile")
user_email = st.sidebar.text_input("Enter Email to Filter Data:", "your-email@example.com")
monthly_budget = st.sidebar.number_input("Monthly Budget (₹)", min_value=0, value=25000)

st.sidebar.divider()
st.sidebar.info("Tip: Ensure the 'email' column in your Google Sheet matches the input above exactly.")

# --- 3. DATA LOADING LOGIC ---
st.title("📊 Expense Dashboard")

try:
    # Read the data. 
    # NOTE: 'worksheet' must match your Google Sheet tab name EXACTLY (case-sensitive)
    df = conn.read(worksheet="Expenses", ttl="0")
    
    # Check if the dataframe is empty or missing columns
    if df is not None and not df.empty:
        
        # Standardize column names to lowercase to avoid "KeyErrors"
        df.columns = [c.lower() for c in df.columns]
        
        # Filter for the specific user
        mask = df['email'].str.lower() == user_email.lower()
        user_df = df[mask].copy()
        
        # Convert 'date' column to datetime objects
        user_df['date'] = pd.to_datetime(user_df['date'], errors='coerce')
        user_df = user_df.dropna(subset=['date'])

        # --- 4. METRICS SECTION ---
        total_spent = user_df['amount'].sum()
        remaining = monthly_budget - total_spent
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Spent", f"₹{total_spent:,.2f}")
        col2.metric("Remaining", f"₹{remaining:,.2f}", delta_color="inverse")
        
        usage_pct = (total_spent / monthly_budget) * 100 if monthly_budget > 0 else 0
        col3.metric("Budget Usage", f"{usage_pct:.1f}%")
        
        st.progress(min(usage_pct / 100, 1.0))

        st.divider()

        # --- 5. VISUALIZATIONS ---
        if not user_df.empty:
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("🍕 Spending by Category")
                fig_pie = px.pie(user_df, values='amount', names='category', hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)
                
            with c2:
                st.subheader("📅 Spending Trend")
                daily_trend = user_df.groupby('date')['amount'].sum().reset_index()
                fig_line = px.line(daily_trend, x='date', y='amount', markers=True)
                st.plotly_chart(fig_line, use_container_width=True)

            st.subheader("📜 Recent Transactions")
            st.dataframe(user_df.sort_values(by='date', ascending=False), use_container_width=True)
        else:
            st.warning(f"No data found for user: {user_email}. Please add an expense below.")

    else:
        st.error("The Google Sheet is empty or the 'Expenses' tab was not found.")

except Exception as e:
    st.error("🚨 Connection Diagnostic")
    st.write(f"**Error Details:** {e}")
    st.info("""
    **Common Fixes for 404 / Connection Errors:**
    1. **Tab Name:** Is your Google Sheet tab named exactly **Expenses**? (Check for trailing spaces!)
    2. **Sharing:** Did you share the Google Sheet with the `client_email` as an **Editor**?
    3. **Secrets:** Does your Streamlit Cloud Secret have the correct `spreadsheet` URL?
    """)

# --- 6. MANUAL DATA ENTRY ---
with st.expander("➕ Add New Expense Manually"):
    with st.form("add_expense"):
        new_date = st.date_input("Date", datetime.now())
        new_item = st.text_input("Item/Description")
        new_amount = st.number_input("Amount", min_value=0.0)
        new_cat = st.selectbox("Category", ["Food", "Transport", "Shopping", "Bills", "Health", "Misc"])
        
        if st.form_submit_button("Submit Expense"):
            st.info("Note: Manual submission requires additional 'Write' permissions logic. For now, log via WhatsApp or add manually to the Sheet.")
