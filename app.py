import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import hashlib
import google.generativeai as genai
import json
import re

# --- 1. SETTINGS & STYLING ---
st.set_page_config(page_title="Paisa-Dasangu | AI Finance", layout="centered", page_icon="💰")

st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    div.stButton > button:first-child {
        width: 100%; height: 3.5em; font-weight: bold;
        background-color: #1E88E5; color: white; border-radius: 12px;
        border: none; transition: 0.3s;
    }
    div.stButton > button:hover { background-color: #1565C0; }
    .stMetric { background-color: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .instruction-card { background-color: #e3f2fd; padding: 15px; border-radius: 10px; border-left: 5px solid #1E88E5; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. AI CONFIGURATION (GEMINI) ---
def setup_ai():
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY")
        if not api_key:
            st.error("Missing GOOGLE_API_KEY in secrets!")
            return None
        genai.configure(api_key=api_key)
        
        # This is the exact technical ID for the Gemini 3 Flash Preview
        return genai.GenerativeModel('gemini-3-flash-preview')
    except Exception as e:
        # Emergency Fallback to Gemini 1.5 if the preview is down for maintenance
        try:
            return genai.GenerativeModel('gemini-1.5-flash')
        except:
            st.error(f"Paisa-Dasangu Brain is offline: {e}")
            return None

model = setup_ai()

def ask_paisa_dasangu(user_text):
    """Parses natural language into structured JSON using Gemini with Regex cleaning"""
    prompt = f"""
    You are Paisa-Dasangu, a smart expense manager. 
    Extract details from: '{user_text}'
    Return ONLY a JSON object: 
    {{ "item": "string", "amount": number, "category": "Food/Transport/Bills/Shopping/Health/Misc" }}
    
    Rules:
    1. Categories MUST be one of: Food, Transport, Bills, Shopping, Health, Misc.
    2. If amount is missing, use 0. 
    3. If 'item' is missing, use 'Unknown'.
    """
    try:
        if model is None: return None
        response = model.generate_content(prompt)
        # Regex to find the JSON block inside potential markdown or extra text
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            return json.loads(match.group())
        else:
            return {"item": "Manual Entry Required", "amount": 0, "category": "Misc"}
    except Exception as e:
        st.error(f"AI Connection Error: {e}")
        return None

# --- 3. CLOUD CONNECTION (GOOGLE SHEETS) ---
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

@st.cache_resource
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
        st.error(f"Google Sheets Connection Error: {e}")
        st.stop()

user_sheet, expense_sheet = get_google_sheets()

# --- 4. AUTHENTICATION ---
if 'auth' not in st.session_state:
    st.session_state['auth'] = False
    st.session_state['user'] = None

if not st.session_state['auth']:
    st.title("💰 Paisa-Dasangu")
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("login_form"):
            e_log = st.text_input("Email").lower().strip()
            p_log = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In"):
                u_data = user_sheet.get_all_records()
                u_df = pd.DataFrame(u_data)
                if not u_df.empty:
                    u_df.columns = u_df.columns.str.strip()
                    match = u_df[u_df['Email'].str.lower() == e_log]
                    if not match.empty and str(match.iloc[0]['Password']) == hash_password(p_log):
                        st.session_state['auth'] = True
                        st.session_state['user'] = e_log
                        st.rerun()
                st.error("Invalid credentials.")
    
    with tab2:
        with st.form("signup"):
            n_email = st.text_input("Email").lower().strip()
            n_name = st.text_input("Name")
            n_pass = st.text_input("Password", type="password")
            n_curr = st.selectbox("Currency", ["₹", "$", "AED"])
            n_income = st.number_input("Monthly Income", min_value=0.0)
            n_tax = st.number_input("Tax %", min_value=0.0, max_value=100.0)
            if st.form_submit_button("Create Account"):
                user_sheet.append_row([n_email, n_name, "India", n_curr, n_income, n_tax, hash_password(n_pass)])
                st.success("Account created! Please Login.")
    st.stop()

# --- 5. DATA LOADING & CALCULATIONS ---
u_email = st.session_state['user']
u_data_all = user_sheet.get_all_records()
u_df = pd.DataFrame(u_data_all)
u_df.columns = u_df.columns.str.strip()
u_profile = u_df[u_df['Email'] == u_email].iloc[0]

CURRENCY = u_profile.get('Currency', '₹')
NET_INCOME = float(u_profile.get('Monthly_Income', 0)) * (1 - float(u_profile.get('Tax_Rate', 0))/100)

all_exp_list = expense_sheet.get_all_records()
all_exp = pd.DataFrame(all_exp_list)
if not all_exp.empty:
    all_exp.columns = all_exp.columns.str.strip()
    my_exp = all_exp[all_exp['Email'].str.lower() == u_email].copy()
    my_exp['Amount'] = pd.to_numeric(my_exp['Amount'], errors='coerce').fillna(0)
    total_spent = my_exp['Amount'].sum()
else:
    my_exp = pd.DataFrame()
    total_spent = 0.0

rem_bal = NET_INCOME - total_spent

# --- 6. DASHBOARD UI ---
st.title(f"📈 {u_profile['Name']}'s Paisa-Dasangu")
st.sidebar.button("Logout", on_click=lambda: st.session_state.update({'auth':False}))

c1, c2 = st.columns(2)
c1.metric("Current Balance", f"{CURRENCY}{rem_bal:,.0f}")
c2.metric("Total Spent", f"{CURRENCY}{total_spent:,.0f}")

# --- 7. THE AI "QUICK LOG" ---
st.markdown('<div class="instruction-card"><b>Quick Log:</b> Message Paisa-Dasangu (e.g., "Lunch 200" or "Added 500 for petrol")</div>', unsafe_allow_html=True)

with st.form("ai_form", clear_on_submit=True):
    ai_input = st.text_input("Type here:", placeholder="Message your finance buddy...")
    submit_ai = st.form_submit_button("LOG VIA AI")

if submit_ai and ai_input:
    with st.spinner("Paisa-Dasangu is thinking..."):
        data = ask_paisa_dasangu(ai_input)
        if data and data.get('amount', 0) > 0:
            expense_sheet.append_row([str(datetime.date.today()), data['item'], data['amount'], data['category'], u_email])
            st.toast(f"✅ Saved: {data['item']} ({CURRENCY}{data['amount']})", icon="💰")
            st.rerun()
        else:
            st.warning("Could not find an amount. Please try again (e.g. 'Spent 50 on tea')")

# --- 8. HISTORY ---
with st.expander("📝 Manual Entry & Transaction History"):
    with st.form("manual", clear_on_submit=True):
        m_item = st.text_input("Item Name")
        m_amt = st.number_input("Amount", min_value=0.0)
        m_cat = st.selectbox("Category", ["Food", "Transport", "Bills", "Shopping", "Health", "Misc"])
        if st.form_submit_button("Add Record Manually"):
            expense_sheet.append_row([str(datetime.date.today()), m_item, m_amt, m_cat, u_email])
            st.success("Entry added manually!")
            st.rerun()
    
    st.divider()
    if not my_exp.empty:
        # Displaying columns except Email in descending order (latest first)
        st.dataframe(my_exp.drop(columns=['Email']).iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.info("No transactions logged yet.")
