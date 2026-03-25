import streamlit as st
import pandas as pd
import yfinance as yf

# --- 1. 頁面設定 ---
st.set_page_config(page_title="ETF 複利與市值精算師", page_icon="💰", layout="wide")

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #00ff88; }
    .card { background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #333; margin-bottom: 10px; }
    .highlight { color: #00ff88; font-weight: bold; font-size: 28px; }
    .compounding { color: #00d4ff; font-weight: bold; font-size: 24px; }
</style>
""", unsafe_allow_html=True)

# --- 2. ETF 數據庫 ---
etf_db = {
    "00919 群益台灣精選高息": {"symbol": "00919.TW", "div": 2.8, "months": [3, 6, 9, 12]},
    "00918 大華優利高填息30": {"symbol": "00918.TW", "div": 3.0, "months": [3, 6, 9, 12]},
    "00878 國泰永續高股息": {"symbol": "00878.TW", "div": 1.6, "months": [2, 5, 8, 11]},
    "0056 元大高股息": {"symbol": "0056.TW", "div": 3.2, "months": [1, 4, 7, 10]},
    "00929 復華台灣科技優息": {"symbol": "00929.TW", "div": 2.4, "months": list(range(1, 13))},
    "00713 元大台灣高息低波": {"symbol": "00713.TW", "div": 6.0, "months": [3, 6, 9, 12]},
    "00940 元大台灣價值高息": {"symbol": "00940.TW", "div": 0.6, "months": list(range(1, 13))},
    "0050 元大台灣50": {"symbol": "0050.TW", "div": 4.5, "months": [1, 7]},
}

st.title("💰 ETF 市值精算與複利滾存計畫")

# --- 3. 側邊欄設定 ---
st.sidebar.header("🎯 目標與複利設定")
target_monthly = st.sidebar.number_input("目標月領金額 (元)", value=10000, step=1000)
comp_years = st.sidebar.slider("複利模擬年數", 1, 30, 10)
reinvest_ratio = st.sidebar.slider("股息再投入比例 (%)", 0, 100, 100) / 100

st.sidebar.markdown("---")
st.sidebar.header("📂 我的現有庫存")
selected_names = st.sidebar.multiselect("選取標的", options=list(etf_db.keys()), default=["00919 群益台灣精選高息", "00918 大華優利高填息30"])

user_inputs = {}
for name in selected_names:
    st.sidebar.subheader(f"📍 {name}")
    owned = st.sidebar.number_input(f"持有張數", min_value=0.0, value=1.0, step=0.1, key=f"owned_{name}")
    user_inputs[name] = {"owned": owned}

# --- 4. 計算邏輯 ---
results = []
calendar = {m: 0 for m in range(1, 13)}
total_monthly_now = 0
total_value_now_wan = 0

for name, info in user_inputs.items():
    try:
        ticker =
