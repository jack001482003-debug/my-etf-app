import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
import datetime
import time

# --- 1. 頁面設定 ---
st.set_page_config(page_title="ETF 即時複利加碼計算機", page_icon="💰", layout="wide")

# 【重要】請去 FinMind 官網註冊後把 Token 貼在下面，抓取會變超級穩定
# 註冊網址：https://finmindtrade.com/
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMS0yMCAwODo1ODoxNiIsInVzZXJfaWQiOiJ6eGN2NjQxMiIsImVtYWlsIjoiamFjazAwMTQ4MjAwM0BnbWFpbC5jb20iLCJpcCI6IjExNC4xMzcuMTkwLjgifQ.H5tanX21Cz640KnMK0KAuf3RIJjzySMn-GM7awSFL90" 

@st.cache_resource
def get_api():
    return DataLoader(token=FINMIND_TOKEN)

api = get_api()

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #00ff88; }
    .card { background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #333; margin-bottom: 10px; }
    .highlight { color: #00ff88; font-weight: bold; font-size: 28px; }
    .compounding { color: #00d4ff; font-weight: bold; font-size: 24px; }
    .update-time { color: #888; font-size: 12px; }
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

st.title("💰 ETF 定期定額與複利試算")
st.markdown(f'<div class="update-time">資料更新時間：{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>', unsafe_allow_html=True)

# --- 3. 側邊欄設定 ---
st.sidebar.header("🎯 長期投資計畫")
monthly_invest = st.sidebar.number_input("每月預計投入金額 (元)", value=15000, step=1000)
comp_years = st.sidebar.slider("複利模擬年數", 1, 30, 10)
reinvest_ratio = st.sidebar.slider("股息再投入比例 (%)", 0, 100, 100) / 100

st.sidebar.markdown("---")
st.sidebar.header("📂 我的現有庫存與加碼比")
selected_names = st.sidebar.multiselect("選取標的", options=list(etf_db.keys()), default=["00919 群益台灣精選高息", "00918 大華優利高填息30"])

user_inputs = {}
rem_pct = 100
for name in selected_names:
    st.sidebar.subheader(f"📍 {name}")
    owned = st.sidebar.number_input(f"目前持有張數", min_value=0.0, value=1.0, step=0.1, key=f"owned_{name}")
    pct = st.sidebar.slider(f"未來資金分配比 (%)", 0, rem_pct, int(100/len(selected_names)) if len(selected_names)>0 else 0, key=f"pct_{name}")
    user_inputs[name] = {"owned": owned, "pct": pct}
    rem_pct -= pct

# --- 4. 改進版即時價格抓取 ---
def get_real_price(stock_id):
    try:
        # 嘗試抓取最近一週的資料
        end_date = datetime.datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        
        df = api.taiwan_stock_daily(stock_id=stock_id, start_date=start_date, end_date=end_date)
        
        if not df.empty:
            latest_price = float(df['close'].iloc[-1])
            return latest_price
        else:
            return 25.0
    except Exception as e:
        # 如果噴錯，顯示在網頁上方便除錯
        st.warning(f"⚠️ 無法抓取 {stock_id}，請確認是否達到 FinMind 流量限制。")
        return 25.0

# 建立即時價格映射表
price_map = {}
for name in user_inputs.keys():
    price_map[name] = get_real_price(etf_db[name]["id"])
    time.sleep(0.5) # 稍微延遲避免被 API 封鎖

# --- 5. 計算與呈現 (保留原本強大的計算邏輯) ---
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
        "標的": name, "目前張數": info["owned"], "加碼比例": f"{info['pct']}%",
        "即時市價": round(price, 2), "市值(萬)": round(mkt_val_wan, 2), "預估月領": int(ann_div / 12)
    })

# 複利計算 (略，同上版，確保計算無誤)
history = []
temp_shares = {n: i["owned"] for n, i in user_inputs.items()}
for y in range(1, comp_years + 1):
    y_div_total = 0
    y_mkt_val = 0
    for _ in range(12): # 每月投入
        for n, s in temp_shares.items():
            invest_amount = monthly_invest * (user_inputs[n]["pct"] / 100)
            temp_shares[n] += invest_amount / (price_map[n] * 1000)
    for n, s in temp_shares.items(): # 年終複利
        div_earned = s * (etf_db[n]["div"] * 1000)
        temp_shares[n] += (div_earned * reinvest_ratio) / (price_map[n] * 1000)
        y_div_total += div_earned
        y_mkt_val += (temp_shares[n] * price_map[n] * 1000) / 10000
    history.append({"年度": f"第{y}年", "預估月領": int(y_div_total/12), "總資產(萬)": round(y_mkt_val, 1)})

# --- 介面呈現 ---
c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="card"><div style="color:#aaa">目前月領預估</div><div class="highlight">{int(total_monthly_now)} 元</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="card"><div style="color:#aaa">{comp_years}年後月領 (含加碼)</div><div class="compounding">{history[-1]["預估月領"] if history else 0} 元</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="card"><div style="color:#aaa">即時總市值</div><div class="highlight">{round(total_value_now_wan, 2)} 萬元</div></div>', unsafe_allow_html=True)

st.subheader("📋 資產清單 (即時更新)")
st.table(pd.DataFrame(results))

st.subheader(f"📈 {comp_years} 年複利加碼成長曲線")
st.line_chart(pd.DataFrame(history).set_index("年度"))

if st.button("🔄 手動重新抓取最新價格"):
    st.cache_resource.clear()
    st.rerun()
