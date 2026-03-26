import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
import datetime
import time

# --- 1. 頁面設定 ---
st.set_page_config(page_title="ETF 現金流複利計算機", page_icon="💰", layout="wide")

# 【建議】在此填入你的 FinMind Token 抓取會更穩定
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMS0yMCAwODo1ODoxNiIsInVzZXJfaWQiOiJ6eGN2NjQxMiIsImVtYWlsIjoiamFjazAwMTQ4MjAwM0BnbWFpbC5jb20iLCJpcCI6IjExNC4xMzcuMTkwLjgifQ.H5tanX21Cz640KnMK0KAuf3RIJjzySMn-GM7awSFL90" 
api = DataLoader(token=FINMIND_TOKEN)

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #00ff88; }
    .card { background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #333; margin-bottom: 10px; }
    .highlight { color: #00ff88; font-weight: bold; font-size: 28px; }
    .compounding { color: #00d4ff; font-weight: bold; font-size: 24px; }
    .error-text { color: #ff4b4b; font-weight: bold; }
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

st.title("💰 ETF 定期定額現金分配與複利計畫")

# --- 3. 側邊欄設定 ---
st.sidebar.header("🎯 總預算設定")
total_budget = st.sidebar.number_input("每月總投入預算 (元)", value=20000, step=1000)
comp_years = st.sidebar.slider("複利模擬年數", 1, 30, 10)
reinvest_ratio = st.sidebar.slider("股息再投入比例 (%)", 0, 100, 100) / 100

st.sidebar.markdown("---")
st.sidebar.header("📂 標的分配 (現金)")
selected_names = st.sidebar.multiselect("選取標的", options=list(etf_db.keys()), default=["00919 群益台灣精選高息", "00918 大華優利高填息30"])

user_inputs = {}
current_allocated = 0
for name in selected_names:
    st.sidebar.subheader(f"📍 {name}")
    owned = st.sidebar.number_input(f"目前持股張數", min_value=0.0, value=1.0, step=0.1, key=f"owned_{name}")
    # 改為現金輸入
    max_allow = max(0, total_budget - current_allocated)
    invest_cash = st.sidebar.number_input(f"每月預計投入現金 (元)", min_value=0, max_value=total_budget, value=min(5000, max_allow), key=f"cash_{name}")
    user_inputs[name] = {"owned": owned, "invest_cash": invest_cash}
    current_allocated += invest_cash

# 預算超支檢查
if current_allocated > total_budget:
    st.sidebar.markdown(f'<p class="error-text">⚠️ 警告：已分配金額 ({current_allocated}) 超出總預算 ({total_budget})！</p>', unsafe_allow_html=True)

# --- 4. 即時價格抓取邏輯 ---
def get_real_price(stock_id):
    try:
        end_date = datetime.datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        df = api.taiwan_stock_daily(stock_id=stock_id, start_date=start_date, end_date=end_date)
        return float(df['close'].iloc[-1]) if not df.empty else 25.0
    except:
        return 25.0

price_map = {name: get_real_price(etf_db[name]["id"]) for name in user_inputs.keys()}

# --- 5. 計算現況與複利滾存 ---
results = []
total_monthly_now = 0
total_value_now_wan = 0

for name, info in user_inputs.items():
    price = price_map[name]
    mkt_val_wan = (info["owned"] * price * 1000) / 10000
    ann_div = info["owned"] * (etf_db[name]["div"] * 1000)
    total_monthly_now += (ann_div / 12)
    total_value_now_wan += mkt_val_wan
    results.append({
        "標的": name, "目前張數": info["owned"], "每月加碼(元)": info["invest_cash"],
        "即時市價": round(price, 2), "市值(萬)": round(mkt_val_wan, 2), "預計月領息": int(ann_div / 12)
    })

# 複利模擬 (含現金加碼)
history = []
temp_shares = {n: i["owned"] for n, i in user_inputs.items()}
for y in range(1, comp_years + 1):
    y_div_total = 0
    y_mkt_val = 0
    for _ in range(12): # 每月現金投入
        for n, s in temp_shares.items():
            p = price_map[n]
            temp_shares[n] += user_inputs[n]["invest_cash"] / (p * 1000)
    for n, s in temp_shares.items(): # 年終股息再投入
        p = price_map[n]
        div = s * (etf_db[n]["div"] * 1000)
        temp_shares[n] += (div * reinvest_ratio) / (p * 1000)
        y_div_total += div
        y_mkt_val += (temp_shares[n] * p * 1000) / 10000
    history.append({"年度": f"第{y}年", "預估月領": int(y_div_total/12), "總資產(萬)": round(y_mkt_val, 1)})

df_comp = pd.DataFrame(history)

# --- 6. 介面呈現 ---
c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="card"><div style="color:#aaa">目前月領預估</div><div class="highlight">{int(total_monthly_now)} 元</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="card"><div style="color:#aaa">{comp_years}年後月領 (複利)</div><div class="compounding">{df_comp.iloc[-1]["預估月領"] if not df_comp.empty else 0} 元</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="card"><div style="color:#aaa">目前總資產</div><div class="highlight">{round(total_value_now_wan, 2)} 萬元</div></div>', unsafe_allow_html=True)

st.subheader("📋 資產清單 (現金分配版)")
st.table(pd.DataFrame(results))

st.subheader(f"📈 {comp_years} 年複利成長曲線")
st.line_chart(df_comp.set_index("年度"))

# 補回的複利滾存列表
with st.expander("🔍 查看逐年複利滾存明細表"):
    st.write("此表格包含每月投入現金與股息再投入的累積效果：")
    st.dataframe(df_comp, use_container_width=True, hide_index=True)

if st.button("🔄 刷新即時數據"):
    st.rerun()
