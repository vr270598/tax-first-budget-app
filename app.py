import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Personal Expense Tracker", page_icon="💰", layout="wide")

# 1. Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Sidebar - User & Settings
st.sidebar.title("👤 User Settings")
user_email = st.sidebar.text_input("Logged in as:", "your-email@example.com")
monthly_budget = st.sidebar.number_input("Monthly Budget (₹)", min_value=100, value=25000)

# --- DATA FUNCTIONS ---
def get_data():
    # Read the 'Expenses' sheet
    df = conn.read(worksheet="Expenses", ttl="0")
    # Filter for current user only
    df = df[df['email'] == user_email]
    # Ensure Date is in datetime format
    df['Date'] = pd.to_datetime(df['Date'])
    return df

try:
    df = get_data()
except Exception as e:
    st.error("Could not connect to Google Sheets. Check your secrets and sheet name.")
    st.stop()

# --- HEADER & KEY METRICS ---
st.title("📊 Expense Dashboard")
st.markdown(f"Tracking expenses for **{user_email}**")

# Calculate Metrics
total_spent = df['amount'].sum()
remaining = monthly_budget - total_spent
percent_spent = (total_spent / monthly_budget) * 100

col1, col2, col3 = st.columns(3)
col1.metric("Total Spent", f"₹{total_spent:,.2f}")
col2.metric("Remaining", f"₹{remaining:,.2f}", delta_color="inverse")
col3.metric("Budget Usage", f"{percent_spent:.1f}%")

# Progress Bar (Burn Rate)
st.write("### 🕯️ Burn Rate")
bar_color = "red" if percent_spent > 90 else "orange" if percent_spent > 70 else "green"
st.progress(min(percent_spent / 100, 1.0))
if percent_spent > 100:
    st.warning(f"⚠️ You are ₹{abs(remaining):,.2f} over budget!")

st.divider()

# --- VISUAL CHARTS ---
c1, c2 = st.columns(2)

with c1:
    st.subheader("🍕 Spending by Category")
    if not df.empty:
        fig_pie = px.pie(df, values='amount', names='category', hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No data to display.")

with c2:
    st.subheader("📅 Daily Spending Trend")
    if not df.empty:
        daily_df = df.groupby('Date')['amount'].sum().reset_index()
        fig_line = px.line(daily_df, x='Date', y='amount', markers=True)
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("No data to display.")

st.divider()

# --- DATA ENTRY & LOG ---
tab1, tab2 = st.tabs(["➕ Add New Expense", "📜 Expense History"])

with tab1:
    st.subheader("Manual Log")
    with st.form("add_form", clear_on_submit=True):
        f_date = st.date_input("Date", datetime.now())
        f_item = st.text_input("Item Name (e.g., Grocery, Uber)")
        f_amt = st.number_input("Amount (₹)", min_value=1.0)
        f_cat = st.selectbox("Category", ["Food", "Transport", "Shopping", "Bills", "Health", "Misc"])
        
        if st.form_submit_button("Save to Cloud"):
            new_row = pd.DataFrame([{
                "Date": f_date.strftime('%Y-%m-%d'),
                "item": f_item,
                "amount": f_amt,
                "category": f_cat,
                "email": user_email
            }])
            # Append to existing sheet
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(worksheet="Expenses", data=updated_df)
            st.success(f"Successfully logged {f_item}!")
            st.rerun()

with tab2:
    st.subheader("Raw Log")
    st.dataframe(df.sort_values(by="Date", ascending=False), use_container_width=True)
