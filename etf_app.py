import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
import datetime

# --- 1. 頁面設定 ---
st.set_page_config(page_title="ETF 現金流自動連動計算機", page_icon="⚖️", layout="wide")

# Token 設定
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMS0yMCAwODo1ODoxNiIsInVzZXJfaWQiOiJ6eGN2NjQxMiIsImVtYWlsIjoiamFjazAwMTQ4MjAwM0BnbWFpbC5jb20iLCJpcCI6IjExNC4xMzcuMTkwLjgifQ.H5tanX21Cz640KnMK0KAuf3RIJjzySMn-GM7awSFL90" 
api = DataLoader(token=FINMIND_TOKEN)

st.markdown("""
<style>
    .card { background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #333; margin-bottom: 10px; }
    .highlight { color: #00ff88; font-weight: bold; font-size: 28px; }
    .compounding { color: #00d4ff; font-weight: bold; font-size: 24px; }
    .budget-info { background-color: #262730; padding: 10px; border-radius: 5px; border-left: 5px solid #00ff88; }
</style>
""", unsafe_allow_html=True)

# --- 2. ETF 數據庫 ---
etf_db = {
    "00919 群益台灣精選高息": {"id": "00919", "div": 2.8, "months": [3, 6, 9, 12]},
    "00918 大華優利高填息30": {"id": "00918", "div": 3.0, "months": [3, 6, 9, 12]},
    "00878 國泰永續高股息": {"id": "00878", "div": 1.6, "months": [2, 5, 8, 11]},
    "0056 元大高股息": {"id": "0056", "div": 3.2, "months": [1, 4, 7, 10]},
    "00929 復華台灣科技優息": {"id": "00929", "div": 2.4, "months": list(range(1, 13))},
    "00713 元大台灣高息低波": {"id": "00713", "div": 6.0, "months": [3, 6, 9, 12]},
    "0050 元大台灣50": {"id": "0050", "div": 4.5, "months": [1, 7]},
}

# --- 3. 側邊欄：連動邏輯核心 ---
st.sidebar.header("🎯 總預算設定")

# 總預算一變動，就重新計算平均值並更新 Session
def update_all_cash():
    if st.session_state.get('selected_etfs'):
        avg = int(st.session_state.total_budget / len(st.session_state.selected_etfs))
        for name in st.session_state.selected_etfs:
            st.session_state[f"cash_{name}"] = avg

total_budget = st.sidebar.number_input(
    "每月總投入預算 (元)", 
    value=20000, 
    step=1000, 
    key="total_budget", 
    on_change=update_all_cash
)

comp_years = st.sidebar.slider("模擬年數", 1, 30, 10)
reinvest_ratio = st.sidebar.slider("股息再投入比例 (%)", 0, 100, 100) / 100

st.sidebar.markdown("---")
st.sidebar.header("📂 標的分配")

selected_etfs = st.sidebar.multiselect(
    "選取標的", 
    options=list(etf_db.keys()), 
    default=["00919 群益台灣精選高息", "00918 大華優利高填息30"],
    key="selected_etfs",
    on_change=update_all_cash
)

# 初始化 Session 中的個別金額（如果還沒有的話）
if 'selected_etfs' in st.session_state:
    avg_init = int(total_budget / len(selected_etfs)) if selected_etfs else 0
    for name in selected_etfs:
        if f"cash_{name}" not in st.session_state:
            st.session_state[f"cash_{name}"] = avg_init

user_data = {}
total_allocated = 0

for name in selected_etfs:
    st.sidebar.subheader(f"📍 {name}")
    owned = st.sidebar.number_input(f"目前持有張數", min_value=0.0, step=0.1, key=f"owned_{name}")
    
    # 這裡的 value 使用 session_state 來達成強制連動
    cash = st.sidebar.number_input(
        f"每月投入現金 (元)", 
        min_value=0, 
        key=f"cash_{name}"
    )
    user_data[name] = {"owned": owned, "cash": cash}
    total_allocated += cash

st.sidebar.markdown(f"""
<div class="budget-info">
    <small>預算使用狀況：</small><br>
    <b>已分配：{total_allocated} 元</b><br>
    <b>剩餘：{total_budget - total_allocated} 元</b>
</div>
""", unsafe_allow_html=True)

if total_allocated > total_budget:
    st.sidebar.error(f"⚠️ 已超出預算 {total_allocated - total_budget} 元！")

# --- 4. 數據抓取 (其餘保持不變) ---
def get_live_price(sid):
    try:
        df = api.taiwan_stock_daily(stock_id=sid, start_date=(
