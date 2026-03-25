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
        ticker = yf.Ticker(etf_db[name]["symbol"])
        price = ticker.fast_info['last_price']
    except: price = 25.0
    
    # 修正市值計算：張數 * 單價(元) * 1000股 / 10000 = 萬元
    # 例如：10張 * 22.9元 * 1000 / 10000 = 22.9萬
    mkt_val_wan = (info["owned"] * price * 1000) / 10000
    ann_div = info["owned"] * (etf_db[name]["div"] * 1000)
    
    total_monthly_now += (ann_div / 12)
    total_value_now_wan += mkt_val_wan
    
    for m in etf_db[name]["months"]:
        calendar[m] += (ann_div / len(etf_db[name]["months"]))
        
    results.append({
        "標的": name,
        "目前張數": info["owned"],
        "即時成交價": round(price, 2),
        "目前市值 (萬)": round(mkt_val_wan, 2),
        "預估月領": int(ann_div / 12),
        "配息月份備註": " ".join([f"{m}月" for m in etf_db[name]["months"]])
    })

# 複利計算
def run_compounding(inputs, years, ratio):
    history = []
    current_shares = {n: i["owned"] for n, i in inputs.items()}
    for y in range(1, years + 1):
        year_div = 0
        current_total_val = 0
        for n, s in current_shares.items():
            div = s * (etf_db[n]["div"] * 1000)
            try: p = yf.Ticker(etf_db[n]["symbol"]).fast_info['last_price']
            except: p = 25.0
            current_shares[n] += (div * ratio) / (p * 1000)
            year_div += div
            current_total_val += (current_shares[n] * p * 1000) / 10000
        history.append({"年度": f"第{y}年", "預估月領": int(year_div/12), "總資產(萬)": round(current_total_val, 1)})
    return history

comp_data = run_compounding(user_inputs, comp_years, reinvest_ratio)
df_comp = pd.DataFrame(comp_data)

# --- 5. 介面呈現 ---
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f'<div class="card"><div style="color:#aaa">目前月領金額</div><div class="highlight">{int(total_monthly_now)} 元</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="card"><div style="color:#aaa">{comp_years}年後月領 (複利)</div><div class="compounding">{df_comp.iloc[-1]["預估月領"]} 元</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="card"><div style="color:#aaa">目前總市值</div><div class="highlight">{round(total_value_now_wan, 2)} 萬元</div></div>', unsafe_allow_html=True)

st.write(f"### 🎯 目標達成率: {round(min(total_monthly_now/target_monthly, 1.0)*100, 1)}%")
st.progress(min(total_monthly_now/target_monthly, 1.0))

st.subheader("📋 我的資產明細 (金額修正版)")
st.table(pd.DataFrame(results))

st.subheader(f"📈 {comp_years}年複利成長模擬")
st.line_chart(df_comp.set_index("年度"))

with st.expander("🔍 查看複利數據表格"):
    st.dataframe(df_comp, use_container_width=True)
