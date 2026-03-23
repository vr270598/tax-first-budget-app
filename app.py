import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime

# --- CONFIG & DATA ---
st.set_page_config(page_title="Global Tax-First Budget", layout="wide")

COUNTRY_DATA = {
    "India": {"currency": "₹", "default_tax": 20},
    "United States": {"currency": "$", "default_tax": 22},
    "United Kingdom": {"currency": "£", "default_tax": 20},
    "UAE": {"currency": "د.إ", "default_tax": 0},
}

# --- GOOGLE SHEETS CONNECTION ---
def get_google_data():
    try:
        # These match the [gcp_service_account] label you put in Secrets
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        creds_info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        client = gspread.authorize(creds)
        
        # Opening your specific sheet
        sheet_id = "1XABtmw_1csXqNItG5jrkafyTx2wXanflem2tHha1VDE"
        sh = client.open_by_key(sheet_id)
        worksheet = sh.worksheet("Expenses") # Ensure tab name matches!
        
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Waiting for Google Sheets Connection... {e}")
        raise e
        return pd.DataFrame()

# --- APP UI ---
st.title("💰 Personal Finance Command Center")

# Load Data from Sheets
df = get_google_data()

# Sidebar: Region & Profile
st.sidebar.header("🌍 Region Settings")
selected_country = st.sidebar.selectbox("Select Country", list(COUNTRY_DATA.keys()))
currency = COUNTRY_DATA[selected_country]["currency"]

st.sidebar.header("📈 Income & Tax")
gross_income = st.sidebar.number_input(f"Monthly Gross ({currency})", value=100000)
tax_rate = st.sidebar.slider("Tax Percentage (%)", 0, 50, COUNTRY_DATA[selected_country]["default_tax"])

# Calculations
net_income = gross_income * (1 - tax_rate/100)

if not df.empty and 'Amount' in df.columns:
    total_spent = pd.to_numeric(df['Amount']).sum()
else:
    total_spent = 0.0

disposable_income = net_income - total_spent

# Metrics Display
col1, col2, col3 = st.columns(3)
col1.metric("Monthly Net (After Tax)", f"{currency}{net_income:,.2f}")
col2.metric("Spent This Month", f"{currency}{total_spent:,.2f}")
col3.metric("Remaining Balance", f"{currency}{disposable_income:,.2f}")

st.divider()

# Daily Safe-to-Spend Logic
today = datetime.datetime.now()
last_day = pd.Period(today.strftime('%Y-%m'), freq='D').days_in_month
days_left = last_day - today.day + 1

if days_left > 0:
    daily_safe = disposable_income / days_left
    st.header(f"📍 Safe to Spend Today: {currency}{max(0, daily_safe):,.2f}")
    st.caption(f"Based on {days_left} days remaining in March.")

# Show Expense List
if not df.empty:
    with st.expander("See All Expenses"):
        st.dataframe(df, use_container_width=True)
