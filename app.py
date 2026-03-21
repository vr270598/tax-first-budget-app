
import streamlit as st
import datetime
import pandas as pd

# --- PAGE CONFIG ---
st.set_page_config(page_title="Tax-First Budget Pro", page_icon="💰")

st.title("🛡️ Tax-First Budget Engineer")
st.markdown("---")

# --- SIDEBAR: USER INPUTS ---
st.sidebar.header("Step 1: Financial Profile")
gross_income = st.sidebar.number_input("Monthly Gross Income ($)", value=5000, step=100)
fixed_costs = st.sidebar.number_input("Fixed Costs (Rent, Bills, etc.) ($)", value=1200, step=50)

st.sidebar.header("Step 2: Tax Strategy")
tax_rate = st.sidebar.slider("Estimated Tax % (Manual)", 0, 50, 20)

st.sidebar.header("Step 3: Calendar Settings")
# Find the last day of the current month
today = datetime.date.today()
if today.month == 12:
    last_day = datetime.date(today.year + 1, 1, 1) - datetime.timedelta(days=1)
else:
    last_day = datetime.date(today.year, today.month + 1, 1) - datetime.timedelta(days=1)

salary_day = st.sidebar.date_input("Next Salary Day", value=last_day)

# --- THE DATA ENGINE ---
def get_working_days(start, end):
    # Generates a list of all days between start and end
    all_days = pd.date_range(start, end)
    # Filters out weekends (Saturday=5, Sunday=6)
    working_days = all_days[all_days.weekday < 5]
    return len(working_days)

# Calculations
est_tax = gross_income * (tax_rate / 100)
net_income = gross_income - est_tax
disposable_monthly = net_income - fixed_costs
work_days_left = get_working_days(today, salary_day)

# Safe to Spend Logic
if work_days_left > 0:
    daily_safe = disposable_monthly / work_days_left
else:
    daily_safe = disposable_monthly

# --- DASHBOARD UI ---
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Net Income (After Tax)", f"${net_income:,.2f}")
with col2:
    st.metric("Work Days Remaining", work_days_left)
with col3:
    st.metric("Monthly Disposable", f"${disposable_monthly:,.2f}")

st.markdown("---")
st.header(f"📍 Safe to Spend Today: **${daily_safe:,.2f}**")
st.info("This is your daily allowance based strictly on remaining working days until your next paycheck.")

# Future Feature Placeholder
st.write("---")
st.caption("Next Weekend Sprint: Connecting to Live Google Sheets API for automated expense tracking.")
