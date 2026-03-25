import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
import datetime

# --- 1. 頁面設定 ---
st.set_page_config(page_title="ETF 即時現值精算師", page_icon="⚡", layout="wide")

# 初始化 FinMind 載入器 (建議申請免費 Token 填入可增加抓取穩定度)
# api = DataLoader() 
# 如果你有 Token 可以改用：api = DataLoader(token="")
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMS0yMCAwODo1ODoxNiIsInVzZXJfaWQiOiJ6eGN2NjQxMiIsImVtYWlsIjoiamFjazAwMTQ4MjAwM0BnbWFpbC5jb20iLCJpcCI6IjExNC4xMzcuMTkwLjgifQ.H5tanX21Cz640KnMK0KAuf3RIJjzySMn-GM7awSFL90"
api = DataLoader()

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #00ff88; }
    .card { background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #333; margin-bottom: 10px; }
    .highlight { color: #00ff88; font-weight: bold; font-size: 28px; }
    .update-time { color: #888; font-size: 14px; margin-bottom: 20px; }
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
    "00940 元大台灣價值高息": {"id": "00940", "div": 0.6, "months": list(range(1, 13))},
    "0050 元大台灣50": {"id": "0050", "div": 4.5, "months": [1, 7]},
}

st.title("💹 ETF 即時市值與複利滾存計畫")
st.markdown(f'<div class="update-time">最後查詢時間：{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>', unsafe_allow_html=True)

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

# --- 4. 即時抓取與計算 ---
def get_price(stock_id):
    try:
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        start = (datetime.datetime.now() - datetime.timedelta(days=5)).strftime("%Y-%m-%d")
        df = api.taiwan_stock_daily(stock_id=stock_id, start_date=start, end_date=today)
        return float(df['close'].iloc[-1])
    except:
        return 25.0

# 預抓價格
price_map = {name: get_price(etf_db[name]["id"]) for name in user_inputs.keys()}

results = []
calendar = {m: 0 for m in range(1, 13)}
total_monthly_now = 0
total_value_now_wan = 0

for name, info in user_inputs.items():
    price = price_map[name]
    mkt_val_wan = (info["owned"] * price * 1000) / 10000
    ann_div = info["owned"] * (etf_db[name]["div"] * 1000)
    
    total_monthly_now += (ann_div / 12)
    total_value_now_wan += mkt_val_wan
    
    for m in etf_db[name]["months"]:
        calendar[m] += (ann_div / len(etf_db[name]["months"]))
        
    results.append({
        "標的": name,
        "目前張數": info["owned"],
        "即時股價": round(price, 2),
        "市值(萬)": round(mkt_val_wan, 2),
        "月領息": int(ann_div / 12),
        "配息月份": " ".join([f"{m}月" for m in etf_db[name]["months"]])
    })

# --- 5. 複利模擬計算 (補回複利表) ---
history = []
temp_shares = {n: i["owned"] for n, i in user_inputs.items()}
for y in range(1, comp_years + 1):
    y_div = 0
    y_val = 0
    for n, s in temp_shares.items():
        p = price_map[n]
        div_earned = s * (etf_db[n]["div"] * 1000)
        # 股息再投入換算成新張數
        temp_shares[n] += (div_earned * reinvest_ratio) / (p * 1000)
        y_div += div_earned
        y_val += (temp_shares[n] * p * 1000) / 10000
    history.append({"年度": f"第{y}年", "預估月領": int(y_div/12), "總市值(萬)": round(y_val, 1)})

df_comp = pd.DataFrame(history)

# --- 6. 介面呈現 ---
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f'<div class="card"><div style="color:#aaa">目前月領預估</div><div class="highlight">{int(total_monthly_now)} 元</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="card"><div style="color:#aaa">{comp_years}年後月領 (複利)</div><div class="highlight" style="color:#00d4ff">{df_comp.iloc[-1]["預估月領"] if not df_comp.empty else 0} 元</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="card"><div style="color:#aaa">即時總市值</div><div class="highlight">{round(total_value_now_wan, 2)} 萬元</div></div>', unsafe_allow_html=True)

st.subheader("📋 資產即時清單 (FinMind 修正版)")
st.table(pd.DataFrame(results))

# 複利成長圖
st.subheader(f"📈 {comp_years} 年複利成長模擬曲線")
if not df_comp.empty:
    st.line_chart(df_comp.set_index("年度"))

# 複利明細表 (補回)
with st.expander("🔍 查看逐年複利成長數據明細"):
    st.dataframe(df_comp, use_container_width=True, hide_index=True)

# 領息日曆
st.subheader("📅 年度預計領息月份")
cal_df = pd.DataFrame({"月份": [f"{m}月" for m in range(1, 13)], "預計金額": [int(calendar[m]) for m in range(1, 13)]})
st.bar_chart(cal_df.set_index("月份"))

if st.button("🔄 強制刷新即時數據"):
    st.rerun()
