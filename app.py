import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import hashlib

# --- 1. SETTINGS & STYLING ---
# Updated Brand Name: Paisa-Dasangu
st.set_page_config(page_title="Paisa-Dasangu | Smart Finance", layout="centered", page_icon="💰")

st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    div.stButton > button:first-child {
        width: 100%; height: 3.5em; font-weight: bold;
        background-color: #1E88E5; color: white; border-radius: 12px;
        border: none; transition: 0.3s;
    }
    div.stButton > button:hover { background-color: #1565C0; border: none; }
    .stMetric { background-color: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SECURITY & CLOUD CONNECTION ---
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

@st.cache_resource # Keeps connection alive without reloading every time
def get_google_sheets():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    try:
        # Note: Your secrets must have [gcp_service_account] header
        creds_info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        client = gspread.authorize(creds)
        # Using your existing Sheet ID
        sheet_id = "1XABtmw_1csXqNItG5jrkafyTx2wXanflem2tHha1VDE"
        sh = client.open_by_key(sheet_id)
        return sh.worksheet("Users"), sh.worksheet("Expenses")
    except Exception as e:
        st.error(f"Paisa-Dasangu Connection Error: {e}")
        st.stop()

user_sheet, expense_sheet = get_google_sheets()

# --- 3. AUTHENTICATION LOGIC ---
if 'auth' not in st.session_state:
    st.session_state['auth'] = False
    st.session_state['user'] = None

if not st.session_state['auth']:
    st.title("💰 Paisa-Dasangu")
    st.subheader("Your Financial Health Partner")
    tab1, tab2 = st.tabs(["Login", "Join Paisa-Dasangu"])

    with tab1:
        with st.form("login_form"):
            e_log = st.text_input("Email").lower().strip()
            p_log = st.text_input("Password", type="password")
            if st.form_submit_button("Login to Dashboard"):
                u_data = user_sheet.get_all_records()
                u_df = pd.DataFrame(u_data)
                if not u_df.empty:
                    u_df.columns = u_df.columns.str.strip() 
                    match = u_df[u_df['Email'].str.lower() == e_log]
                    if not match.empty and str(match.iloc[0]['Password']) == hash_password(p_log):
                        st.session_state['auth'] = True
                        st.session_state['user'] = e_log
                        st.rerun()
                    else:
                        st.error("Incorrect credentials. Please try again.")
                else:
                    st.error("No users registered.")

    with tab2:
        with st.form("signup_form"):
            st.subheader("Start Your Journey")
            n_email = st.text_input("Email").lower().strip()
            n_name = st.text_input("Full Name")
            n_pass = st.text_input("Password", type="password")
            n_curr = st.selectbox("Currency", ["₹", "$", "AED", "£"])
            n_income = st.number_input("Monthly Income", min_value=0.0)
            n_tax = st.number_input("Tax %", min_value=0.0, max_value=100.0)
            
            if st.form_submit_button("Register Account"):
                u_data = user_sheet.get_all_records()
                u_df = pd.DataFrame(u_data)
                if not u_df.empty and 'Email' in u_df.columns and n_email in u_df['Email'].values:
                    st.warning("Email already exists.")
                elif n_email and n_pass:
                    # Storing headers: Email, Name, Country (Dummy), Currency, Monthly_Income, Tax_Rate, Password
                    user_sheet.append_row([n_email, n_name, "India", n_curr, n_income, n_tax, hash_password(n_pass)])
                    st.success("Welcome to Paisa-Dasangu! Now please Login.")
                else:
                    st.error("All fields are required.")
    st.stop()

# --- 4. DATA PROCESSING ---
u_email = st.session_state['user']
u_raw = user_sheet.get_all_records()
u_df = pd.DataFrame(u_raw)
u_df.columns = u_df.columns.str.strip()
u_profile = u_df[u_df['Email'] == u_email].iloc[0]

CURRENCY = u_profile.get('Currency', '₹')
NAME = u_profile.get('Name', 'User')
income_val = float(u_profile.get('Monthly_Income', 0))
tax_val = float(u_profile.get('Tax_Rate', 0))
NET_INCOME = income_val * (1 - tax_val/100)

all_exp_list = expense_sheet.get_all_records()
all_exp = pd.DataFrame(all_exp_list)

if not all_exp.empty:
    all_exp.columns = all_exp.columns.str.strip()
    my_exp = all_exp[all_exp['Email'].str.lower() == u_email].copy()
    if not my_exp.empty and 'Amount' in my_exp.columns:
        my_exp['Amount'] = pd.to_numeric(my_exp['Amount'], errors='coerce').fillna(0)
        total_spent = my_exp['Amount'].sum()
    else:
        total_spent = 0.0
else:
    my_exp = pd.DataFrame()
    total_spent = 0.0

rem_bal = NET_INCOME - total_spent
daily_safe = max(0, rem_bal / 30) # Simple 30-day average for now

# --- 5. MAIN DASHBOARD ---
st.title(f"📈 {NAME}'s Paisa-Dasangu")
st.sidebar.title("Settings")
st.sidebar.write(f"User: {u_email}")
if st.sidebar.button("Logout"):
    st.session_state.update({'auth': False, 'user': None})
    st.rerun()

col1, col2 = st.columns(2)
col1.metric("Current Balance", f"{CURRENCY}{rem_bal:,.0f}")
col2.metric("Total Spent", f"{CURRENCY}{total_spent:,.0f}")

st.info(f"💡 **Safe to Spend Today:** {CURRENCY}{daily_safe:,.0f}")

# --- 6. WHATSAPP-STYLE QUICK LOG (AI PREP) ---
st.subheader("🚀 Quick Log (WhatsApp Style)")
ai_input = st.text_input("Chat with Paisa-Dasangu:", placeholder="e.g. 500 for dinner or Paid 2000 for electricity bill")
if ai_input:
    st.write("✨ *AI Parsing Feature coming tomorrow!*")

# --- 7. MANUAL ENTRY ---
with st.expander("📝 Manual Entry"):
    with st.form("exp_form", clear_on_submit=True):
        f_item = st.text_input("Item")
        f_amt = st.number_input("Amount", min_value=0.0)
        f_cat = st.selectbox("Category", ["Food", "Transport", "Bills", "Shopping", "Misc"])
        if st.form_submit_button("Add Record"):
            expense_sheet.append_row([str(datetime.date.today()), f_item, f_amt, f_cat, u_email])
            st.success("Hisaab Updated!")
            st.rerun()

# --- 8. HISTORY ---
st.subheader("📜 Recent Transactions")
if not my_exp.empty:
    st.dataframe(my_exp.drop(columns=['Email']).iloc[::-1], use_container_width=True, hide_index=True)
