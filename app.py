import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime

# --- 1. SETTINGS & STYLING ---
st.set_page_config(page_title="Global Budget Tracker", layout="centered")

# --- 2. CLOUD CONNECTION ---
def get_gspread_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

client = get_gspread_client()
sheet_id = "1XABtmw_1csXqNItG5jrkafyTx2wXanflem2tHha1VDE"
sh = client.open_by_key(sheet_id)
user_sheet = sh.worksheet("Users")
expense_sheet = sh.worksheet("Expenses")

# --- 3. SIMPLE AUTH (For now, we'll use a Text Input) ---
# In a real app, we'd use Google Login, but let's start simple.
user_email = st.sidebar.text_input("Enter Email to Login", value="").lower().strip()

if not user_email:
    st.title("👋 Welcome to Budget Pro")
    st.info("Please enter your email in the sidebar to access your dashboard.")
    st.stop()

# --- 4. CHECK IF USER EXISTS ---
users_df = pd.DataFrame(user_sheet.get_all_records())
user_data = users_df[users_df['Email'] == user_email]

if user_data.empty:
    st.warning(f"New User Detected: {user_email}")
    with st.form("onboarding_form"):
        st.subheader("🌍 Complete Your Profile")
        name = st.text_input("Full Name")
        country = st.selectbox("Country", ["India", "USA", "UK", "UAE", "Germany"])
        currency = st.selectbox("Currency Symbol", ["₹", "$", "£", "€", "AED"])
        income = st.number_input("Monthly Gross Income", min_value=0)
        tax = st.number_input("Estimated Tax %", min_value=0, max_value=100)
        
        if st.form_submit_button("Create My Account"):
            user_sheet.append_row([user_email, name, country, currency, income, tax])
            st.success("Account Created! Refreshing...")
            st.rerun()
    st.stop()

# --- 5. LOAD USER SPECIFIC SETTINGS ---
user_profile = user_data.iloc[0]
CURRENCY = user_profile['Currency']
NAME = user_profile['Name']
NET_INCOME = user_profile['Monthly_Income'] * (1 - user_profile['Tax_Rate']/100)

# --- 6. DASHBOARD LOGIC (Filtered by User) ---
all_expenses = pd.DataFrame(expense_sheet.get_all_records())
if not all_expenses.empty and 'Email' in all_expenses.columns:
    user_expenses = all_expenses[all_expenses['Email'] == user_email]
    user_expenses['Amount'] = pd.to_numeric(user_expenses['Amount'], errors='coerce').fillna(0)
    total_spent = user_expenses['Amount'].sum()
else:
    total_spent = 0.0

# Remaining Balance & Daily Safe Spend
rem_bal = NET_INCOME - total_spent
days_left = pd.Period(datetime.datetime.now().strftime('%Y-%m'), freq='D').days_in_month - datetime.datetime.now().day + 1
daily_safe = max(0, rem_bal / days_left) if days_left > 0 else 0

# --- 7. UI ---
st.title(f"📊 {NAME}'s Budget ({user_profile['Country']})")
col1, col2 = st.columns(2)
col1.metric("Balance", f"{CURRENCY}{rem_bal:,.0f}")
col2.metric("Spent", f"{CURRENCY}{total_spent:,.0f}")

st.header(f"📍 Safe to Spend Today: {CURRENCY}{daily_safe:,.0f}")

# --- 8. ADD EXPENSE (With Email Tagging) ---
with st.expander("📝 Add Expense"):
    with st.form("expense_form", clear_on_submit=True):
        item = st.text_input("Item")
        amt = st.number_input("Amount", min_value=0.0)
        cat = st.selectbox("Category", ["Food", "Bills", "Shopping", "Misc"])
        if st.form_submit_button("Save"):
            # We add user_email to the row so we know WHO spent it!
            # Sheet order: Date | Item | Amount | Category | Email
            expense_sheet.append_row([str(datetime.date.today()), item, amt, cat, user_email])
            st.rerun()
