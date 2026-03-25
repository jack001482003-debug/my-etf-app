import streamlit as st
import pandas as pd
import yfinance as yf

# --- 1. 頁面設定 ---
st.set_page_config(page_title="ETF 達標加碼計算機", page_icon="📈", layout="wide")

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #00ff88; }
    .card { background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #333; margin-bottom: 10px; }
    .highlight { color: #00ff88; font-weight: bold; font-size: 28px; }
    .need-more { color: #ff4b4b; font-weight: bold; font-size: 24px; }
</style>
""", unsafe_allow_html=True)

# --- 2. 擴充 ETF 數據庫 (加入 00918) ---
etf_db = {
    "00919 群益台灣精選高息": {"symbol": "00919.TW", "div": 2.8, "months": [3, 6, 9, 12]},
    "00918 大華優利高填息30": {"symbol": "00918.TW", "div": 3.0, "months": [3, 6, 9, 12]},
    "00878 國泰永續高股息": {"symbol": "00878.TW", "div": 1.6, "months": [2, 5, 8, 11]},
    "0056 元大高股息": {"symbol": "0056.TW", "div": 3.2, "months": [1, 4, 7, 10]},
    "00929 復華台灣科技優息": {"symbol": "00929.TW", "freq": "月配", "div": 2.4, "months": list(range(1, 13))},
    "00713 元大台灣高息低波": {"symbol": "00713.TW", "div": 6.0, "months": [3, 6, 9, 12]},
    "00940 元大台灣價值高息": {"symbol": "00940.TW", "div": 0.6, "months": list(range(1, 13))},
    "0050 元大台灣50": {"symbol": "0050.TW", "div": 4.5, "months": [1, 7]},
}

st.title("📈 ETF 現有持股與補足計畫")

# --- 3. 側邊欄設定 ---
st.sidebar.header("🎯 月領目標設定")
target_monthly = st.sidebar.number_input("目標月領金額 (元)", value=10000, step=1000)

st.sidebar.markdown("---")
st.sidebar.header("📂 我的庫存與新計畫")
selected_names = st.sidebar.multiselect("選取要計算的標的", options=list(etf_db.keys()), default=["00919 群益台灣精選高息", "00918 大華優利高填息30"])

# 儲存使用者輸入
user_inputs = {}
for name in selected_names:
    st.sidebar.subheader(f"📍 {name}")
    owned_shares = st.sidebar.number_input(f"目前持有張數", min_value=0.0, value=0.0, step=0.5, key=f"owned_{name}")
    plan_percent = st.sidebar.slider(f"未來資金分配比 (%)", 0, 100, 0, key=f"pct_{name}")
    user_inputs[name] = {"owned": owned_shares, "pct": plan_percent}

# --- 4. 計算邏輯 ---
results = []
calendar = {m: 0 for m in range(1, 13)}
total_current_monthly_income = 0
current_total_value = 0

for name, info in user_inputs.items():
    # 抓取即時市價
    try:
        ticker = yf.Ticker(etf_db[name]["symbol"])
        price = ticker.fast_info['last_price']
    except: price = 25.0
    
    # 計算現有持股的貢獻
    owned_ann_div = info["owned"] * (etf_db[name]["div"] * 1000)
    total_current_monthly_income += (owned_ann_div / 12)
    current_total_value += (info["owned"] * price * 1000)
    
    # 紀錄分配到日曆
    div_per_event = owned_ann_div / len(etf_db[name]["months"])
    for m in etf_db[name]["months"]:
        calendar[m] += div_per_event
        
    results.append({
        "標的": name,
        "目前張數": info["owned"],
        "目前市值": f"{int(info['owned'] * price * 10)} 萬",
        "預估月貢獻": int(owned_ann_div / 12),
        "配息月份": " ".join([f"{m}月" for m in etf_db[name]["months"]])
    })

# 計算補足目標所需的金額
shortfall = max(0, target_monthly - total_current_monthly_income)
# 簡單預估：假設平均殖利率 6% 來計算補足金額
additional_capital_needed = (shortfall * 12) / 0.06 / 10000 

# --- 5. 介面呈現 ---
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f'<div class="card"><div style="color:#aaa">目前月領預估</div><div class="highlight">{int(total_current_monthly_income)} 元</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="card"><div style="color:#aaa">目標達成率</div><div class="highlight">{round(min(total_current_monthly_income/target_monthly, 1.0)*100, 1)}%</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="card"><div style="color:#aaa">補足月領 1 萬需再投入</div><div class="need-more">約 {round(additional_capital_needed, 1)} 萬元</div></div>', unsafe_allow_html=True)

st.write(f"### 🎯 目標進度 (月領 {target
