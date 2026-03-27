import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime

# --- 1. SETTINGS & STYLING ---
st.set_page_config(page_title="Budget Tracker", layout="centered")

# Custom CSS for a clean mobile-friendly look
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    div.stButton > button:first-child {
        width: 100%; height: 3.5em; font-weight: bold;
        background-color: #007bff; color: white; border-radius: 10px;
    }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA CONNECTION ---
def get_google_sheet():
    # Authenticate using Streamlit Secrets
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    try:
        creds_info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        client = gspread.authorize(creds)
        
        # Open your specific sheet
        sheet_id = "1XABtmw_1csXqNItG5jrkafyTx2wXanflem2tHha1VDE"
        sh = client.open_by_key(sheet_id)
        return sh.worksheet("Expenses")
    except Exception as e:
        st.error(f"⚠️ Connection Error: {e}")
        st.info("Tip: Ensure you shared the Google Sheet with 'sheets-connector@budget-app-491105.iam.gserviceaccount.com' as Editor.")
        st.stop()

# Load Data
worksheet = get_google_sheet()
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# --- 3. CALCULATIONS ---
# Income Settings (You can change these values)
gross_income = 100000 
tax_rate = 20
net_income = gross_income * (1 - tax_rate/100)

# Spending Logic
if not df.empty and 'Amount' in df.columns:
    # Convert 'Amount' column to numeric, ignoring errors (like text in rows)
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
    total_spent = df['Amount'].sum()
else:
    total_spent = 0.0

remaining_balance = net_income - total_spent

# Daily Safe-to-Spend logic
today = datetime.datetime.now()
days_in_month = pd.Period(today.strftime('%Y-%m'), freq='D').days_in_month
days_left = days_in_month - today.day + 1
daily_safe = max(0, remaining_balance / days_left) if days_left > 0 else 0

# --- 4. DASHBOARD UI ---
st.title("💸 Budget Dashboard")

col1, col2 = st.columns(2)
col1.metric("Remaining Balance", f"₹{remaining_balance:,.0f}")
col2.metric("Spent So Far", f"₹{total_spent:,.0f}")

st.divider()

# Progress Bar Logic
usage_pct = (total_spent / net_income) if net_income > 0 else 1.0
st.header(f"📍 Safe to Spend Today: ₹{daily_safe:,.0f}")
st.progress(min(1.0, usage_pct))
st.caption(f"You have used {int(usage_pct * 100)}% of your monthly net income.")

# --- 5. QUICK LOG FORM ---
st.subheader("📝 Add New Expense")
with st.form("add_expense", clear_on_submit=True):
    item_name = st.text_input("What did you buy?")
    amount_input = st.number_input("How much?", min_value=0.0, step=10.0)
    category_input = st.selectbox("Category", ["Food", "Transport", "Bills", "Shopping", "Misc"])
    
    submitted = st.form_submit_button("SAVE TO SHEET")
    
    if submitted:
        if item_name and amount_input > 0:
            # Append row: Date, Item, Category, Amount
            new_row = [str(datetime.date.today()), item_name, category_input, amount_input]
            worksheet.append_row(new_row)
            st.success(f"✅ Saved {item_name}!")
            st.rerun()
        else:
            st.warning("Please enter a name and amount.")

# --- 6. HISTORY ---
with st.expander("View Recent Expenses"):
    if not df.empty:
        st.dataframe(df.tail(10), use_container_width=True)
    else:
        st.write("No expenses logged yet.")
