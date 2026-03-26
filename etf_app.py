import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
import datetime

# --- 1. 頁面設定 ---
st.set_page_config(page_title="ETF 現金流自動分配器", page_icon="⚖️", layout="wide")

# Token 設定 (若有 yji3hk4 等 Token 請填入)
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMS0yMCAwODo1ODoxNiIsInVzZXJfaWQiOiJ6eGN2NjQxMiIsImVtYWlsIjoiamFjazAwMTQ4MjAwM0BnbWFpbC5jb20iLCJpcCI6IjExNC4xMzcuMTkwLjgifQ.H5tanX21Cz640KnMK0KAuf3RIJjzySMn-GM7awSFL90" 
api = DataLoader(token=FINMIND_TOKEN)

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #00ff88; }
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

st.title("⚖️ ETF 自動分配與複利計畫")

# --- 3. 側邊欄：預算與自動分配邏輯 ---
st.sidebar.header("🎯 總預算設定")
total_budget = st.sidebar.number_input("每月總投入預算 (元)", value=20000, step=1000)
comp_years = st.sidebar.slider("模擬年數", 1, 30, 10)
reinvest_ratio = st.sidebar.slider("股息再投入比例 (%)", 0, 100, 100) / 100

st.sidebar.markdown("---")
st.sidebar.header("📂 標的分配 (自動連動)")
selected_etfs = st.sidebar.multiselect("選取標的", options=list(etf_db.keys()), default=["00919 群益台灣精選高息", "00918 大華優利高填息30"])

# 計算初始平均分配金額
avg_amount = int(total_budget / len(selected_etfs)) if selected_etfs else 0

user_data = {}
total_allocated = 0

for name in selected_etfs:
    st.sidebar.subheader(f"📍 {name}")
    owned = st.sidebar.number_input(f"目前持有張數", min_value=0.0, value=0.0, step=0.1, key=f"owned_{name}")
    
    # 這裡的 value 設為 avg_amount 達成自動連動，但使用者仍可手動改
    cash = st.sidebar.number_input(f"每月投入現金 (元)", min_value=0, value=avg_amount, step=500, key=f"cash_{name}")
    user_data[name] = {"owned": owned, "cash": cash}
    total_allocated += cash

# 預算即時狀態顯示
st.sidebar.markdown(f"""
<div class="budget-info">
    <small>預算使用狀況：</small><br>
    <b>已分配：{total_allocated} 元</b><br>
    <b>剩餘：{total_budget - total_allocated} 元</b>
</div>
""", unsafe_allow_html=True)

if total_allocated > total_budget:
    st.sidebar.error(f"⚠️ 已超出預算 {total_allocated - total_budget} 元！")

# --- 4. 數據抓取 ---
@st.cache_data(ttl=3600)
def get_live_price(sid):
    try:
        df = api.taiwan_stock_daily(stock_id=sid, start_date=(datetime.datetime.now()-datetime.timedelta(days=7)).strftime("%Y-%m-%d"))
        return float(df['close'].iloc[-1])
    except: return 25.0

price_map = {n: get_live_price(etf_db[n]["id"]) for n in user_data.keys()}

# --- 5. 計算邏輯 ---
summary_list = []
now_monthly_div = 0
now_total_val_wan = 0

for n, info in user_data.items():
    p = price_map[n]
    val_wan = (info["owned"] * p * 1000) / 10000
    div_m = (info["owned"] * etf_db[n]["div"] * 1000) / 12
    now_monthly_div += div_m
    now_total_val_wan += val_wan
    summary_list.append({"標的": n, "張數": info["owned"], "預計每月投入": info["cash"], "即時市價": p, "市值(萬)": round(val_wan, 2)})

# 複利計算
history = []
temp_shares = {n: info["owned"] for n, info in user_data.items()}
for y in range(1, comp_years + 1):
    y_div = 0
    y_val = 0
    for _ in range(12): 
        for n in temp_shares:
            temp_shares[n] += user_data[n]["cash"] / (price_map[n] * 1000)
    for n, s in temp_shares.items(): 
        d = s * (etf_db[n]["div"] * 1000)
        temp_shares[n] += (d * reinvest_ratio) / (price_map[n] * 1000)
        y_div += d
        y_val += (temp_shares[n] * price_map[n] * 1000) / 10000
    history.append({"年度": f"第 {y} 年", "預估月領": int(y_div/12), "資產總額(萬)": round(y_val, 1)})

df_h = pd.DataFrame(history)

# --- 6. 介面呈現 ---
c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="card"><small>目前月領</small><div class="highlight">{int(now_monthly_div)} 元</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="card"><small>{comp_years}年後月領 (含定期定額)</small><div class="compounding">{df_h.iloc[-1]["預估月領"] if not df_h.empty else 0} 元</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="card"><small>
