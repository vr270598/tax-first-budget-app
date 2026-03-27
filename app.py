import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import hashlib

# --- 1. SETTINGS & STYLING ---
st.set_page_config(page_title="Global Budget Pro", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    div.stButton > button:first-child {
        width: 100%; height: 3em; font-weight: bold;
        background-color: #007bff; color: white; border-radius: 8px;
    }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #eee; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SECURITY & CLOUD CONNECTION ---
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def get_google_sheets():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    try:
        creds_info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        client = gspread.authorize(creds)
        sheet_id = "1XABtmw_1csXqNItG5jrkafyTx2wXanflem2tHha1VDE"
        sh = client.open_by_key(sheet_id)
        return sh.worksheet("Users"), sh.worksheet("Expenses")
    except Exception as e:
        st.error(f"Connection Error: {e}")
        st.stop()

user_sheet, expense_sheet = get_google_sheets()

# --- 3. AUTHENTICATION LOGIC ---
if 'auth' not in st.session_state:
    st.session_state['auth'] = False
    st.session_state['user'] = None

if not st.session_state['auth']:
    st.title("🔐 Secure Budget Login")
    tab1, tab2 = st.tabs(["Login", "Create Account"])

    with tab1:
        with st.form("login_form"):
            e_log = st.text_input("Email").lower().strip()
            p_log = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                u_df = pd.DataFrame(user_sheet.get_all_records())
                match = u_df[u_df['Email'] == e_log]
                if not match.empty and str(match.iloc[0]['Password']) == hash_password(p_log):
                    st.session_state['auth'] = True
                    st.session_state['user'] = e_log
                    st.rerun()
                else:
                    st.error("Invalid Email or Password")

    with tab2:
        with st.form("signup_form"):
            st.subheader("Join Budget Pro")
            n_email = st.text_input("Email").lower().strip()
            n_name = st.text_input("Full Name")
            n_pass = st.text_input("Password", type="password")
            n_country = st.selectbox("Country", ["India", "USA", "UK", "UAE", "Europe"])
            n_curr = st.selectbox("Currency", ["₹", "$", "£", "AED", "€"])
            n_income = st.number_input("Monthly Gross Income", min_value=0)
            n_tax = st.number_input("Estimated Tax %", min_value=0, max_value=100)
            
            if st.form_submit_button("Register"):
                u_df = pd.DataFrame(user_sheet.get_all_records())
                if n_email in u_df['Email'].values:
                    st.warning("Email already registered.")
                elif n_email and n_pass:
                    user_sheet.append_row([n_email, n_name, n_country, n_curr, n_income, n_tax, hash_password(n_pass)])
                    st.success("Registration successful! Go to Login tab.")
                else:
                    st.error("Please fill all fields.")
    st.stop()

# --- 4. LOAD USER DATA ---
u_email = st.session_state['user']
u_df = pd.DataFrame(user_sheet.get_all_records())
u_profile = u_df[u_df['Email'] == u_email].iloc[0]

CURRENCY = u_profile['Currency']
NAME = u_profile['Name']
NET_INCOME = float(u_profile['Monthly_Income']) * (1 - float(u_profile['Tax_Rate'])/100)

# --- 5. CALCULATIONS ---
all_exp = pd.DataFrame(expense_sheet.get_all_records())
if not all_exp.empty and 'Email' in all_exp.columns:
    my_exp = all_exp[all_exp['Email'] == u_email].copy()
    my_exp['Amount'] = pd.to_numeric(my_exp['Amount'], errors='coerce').fillna(0)
    total_spent = my_exp['Amount'].sum()
else:
    my_exp = pd.DataFrame()
    total_spent = 0.0

rem_bal = NET_INCOME - total_spent
today = datetime.datetime.now()
days_left = (pd.Period(today.strftime('%Y-%m'), freq='D').days_in_month - today.day) + 1
daily_safe = max(0, rem_bal / days_left) if days_left > 0 else 0

# --- 6. DASHBOARD UI ---
st.title(f"📊 {NAME}'s Budget")
st.sidebar.button("Logout", on_click=lambda: st.session_state.update({'auth': False, 'user': None}))

c1, c2 = st.columns(2)
c1.metric("Balance", f"{CURRENCY}{rem_bal:,.0f}")
c2.metric("Spent", f"{CURRENCY}{total_spent:,.0f}")

st.divider()
st.header(f"📍 Safe to Spend Today: {CURRENCY}{daily_safe:,.0f}")
st.progress(min(1.0, total_spent/NET_INCOME if NET_INCOME > 0 else 0))

# --- 7. ADD EXPENSE ---
with st.expander("📝 Log New Expense", expanded=True):
    with st.form("exp_form", clear_on_submit=True):
        f_item = st.text_input("What did you buy?")
        f_amt = st.number_input("Amount", min_value=0.0, step=10.0)
        f_cat = st.selectbox("Category", ["Food", "Transport", "Shopping", "Bills", "Health", "Misc"])
        if st.form_submit_button("SAVE EXPENSE"):
            if f_item and f_amt > 0:
                # Order: Date | Item | Amount | Category | Email
                expense_sheet.append_row([str(datetime.date.today()), f_item, f_amt, f_cat, u_email])
                st.success("Saved!")
                st.rerun()

# --- 8. HISTORY ---
st.subheader("📜 Recent History")
if not my_exp.empty:
    history_view = my_exp[['Date', 'Item', 'Amount', 'Category']].iloc[::-1]
    st.dataframe(history_view, use_container_width=True, hide_index=True)
else:
    st.info("No records yet. Start logging above!")
