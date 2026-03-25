import streamlit as st
import pandas as pd
import yfinance as yf

# --- 1. 頁面設定 ---
st.set_page_config(page_title="ETF 複利滾存計算機", page_icon="💹", layout="wide")

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #00ff88; }
    .card { background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #333; margin-bottom: 10px; }
    .highlight { color: #00ff88; font-weight: bold; font-size: 28px; }
    .compounding { color: #00d4ff; font-weight: bold; font-size: 24px; }
</style>
""", unsafe_allow_html=True)

# --- 2. ETF 數據庫 (包含 00918) ---
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

st.title("💹 ETF 現有庫存與複利滾存模擬")

# --- 3. 側邊欄設定 ---
st.sidebar.header("🎯 目標與複利設定")
target_monthly = st.sidebar.number_input("目標月領金額 (元)", value=10000, step=1000)
compounding_years = st.sidebar.slider("複利滾存年數", 1, 30, 10)
reinvest_ratio = st.sidebar.slider("股息再投入比例 (%)", 0, 100, 100) / 100

st.sidebar.markdown("---")
st.sidebar.header("📂 我的庫存清單")
selected_names = st.sidebar.multiselect("選取要計算的標的", options=list(etf_db.keys()), default=["00919 群益台灣精選高息", "00918 大華優利高填息30"])

user_inputs = {}
for name in selected_names:
    st.sidebar.subheader(f"📍 {name}")
    owned = st.sidebar.number_input(f"目前持有張數", min_value=0.0, value=1.0, step=0.1, key=f"owned_{name}")
    user_inputs[name] = {"owned": owned}

# --- 4. 計算邏輯 ---
results = []
calendar = {m: 0 for m in range(1, 13)}
total_monthly_now = 0
total_value_now = 0
total_ann_div_now = 0

# A. 計算現況與修正市值顯示
for name, info in user_inputs.items():
    try:
        ticker = yf.Ticker(etf_db[name]["symbol"])
        price = ticker.fast_info['last_price']
    except: price = 25.0
    
    ann_div = info["owned"] * (etf_db[name]["div"] * 1000)
    market_value_wan = (info["owned"] * price * 1000) / 10000 # 修正後的萬元換算
    
    total_monthly_now += (ann_div / 12)
    total_value_now += (market_value_wan * 10000)
    total_ann_div_now += ann_div
    
    for m in etf_db[name]["months"]:
        calendar[m] += (ann_div / len(etf_db[name]["months"]))
        
    results.append({
        "標的": name,
        "目前張數": info["owned"],
        "目前市值 (萬)": round(market_value_wan, 2),
        "月均領息": int(ann_div / 12),
        "配息月份": " ".join([f"{m}月" for m in etf_db[name]["months"]])
    })

# B. 複利滾存計算 (核心新功能)
# 假設股價不變，將股息除以市價換成新股數
def calculate_compounding(current_shares_dict, years, ratio):
    compound_data = []
    # 建立一個動態追蹤張數的字典
    temp_shares = {name: info["owned"] for name, info in user_inputs.items()}
    
    for year in range(1, years + 1):
        year_total_div = 0
        for name, s in temp_shares.items():
            # 1. 算出今年領多少息
            div_income = s * (etf_db[name]["div"] * 1000)
            # 2. 依照比例再投入買股
            try:
                p = yf.Ticker(etf_db[name]["symbol"]).fast_info['last_price']
            except: p = 25.0
            new_shares = (div_income * ratio) / (p * 1000)
            temp_shares[name] += new_shares
            year_total_div += div_income
            
        compound_data.append({
            "年度": f"第 {year} 年",
            "預估年領息": int(year_total_div),
            "預估月均領": int(year_total_div / 12),
            "複利後總市值 (萬)": round(sum([temp_shares[n] * yf.Ticker(etf_db[n]["symbol"]).fast_info['last_price'] * 1000 for n in temp_shares]) / 10000, 1)
        })
    return compound_data, temp_shares

comp_history, final_shares = calculate_compounding(user_inputs, compounding_years, reinvest_ratio)
df_comp = pd.DataFrame(comp_history)

# --- 5. 介面呈現 ---
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f'<div class="card"><div style="color:#aaa">目前月領預估</div><div class="highlight">{int(total_monthly_now)} 元</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="card"><div style="color:#aaa">{compounding_years}年後月領 (複利)</div><div class="compounding">{df_comp.iloc[-1]["預估月均領"]} 元</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="card"><div style="color:#aaa">目前總資產</div><div class="highlight">{round(total_value_now/10000, 1)} 萬元</div></div>', unsafe_allow_html=True)

# 複利增長圖表
st.subheader(f"📈 複利滾存成長曲線 ({compounding_years} 年模擬)")
st.line_chart(df_comp.set_index("年度")[["預估月均領", "複利後總市值 (萬)"]])

# 庫存明細
st.subheader("📋 我的庫存與市值明細 (已修正金額顯示)")
st.table(pd.DataFrame(results))

# 複利明細
with st.expander("🔍 查看逐年複利成長明細"):
    st.dataframe(df_comp, use_container_width=True)

st.info("💡 複利說明：此計算假設『股價與配息金額』維持不變。複利的威力在於將領到的股息重新買回股票，使持股張數隨時間增加，進而帶動領息金額加速上升。")
