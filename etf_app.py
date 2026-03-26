import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
import datetime

# --- 1. 頁面設定 ---
st.set_page_config(page_title="ETF 健保避稅精算大師", page_icon="🏦", layout="wide")

# Token 設定
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMS0yMCAwODo1ODoxNiIsInVzZXJfaWQiOiJ6eGN2NjQxMiIsImVtYWlsIjoiamFjazAwMTQ4MjAwM0BnbWFpbC5jb20iLCJpcCI6IjExNC4xMzcuMTkwLjgifQ.H5tanX21Cz640KnMK0KAuf3RIJjzySMn-GM7awSFL90" 
api = DataLoader(token=FINMIND_TOKEN)

st.markdown("""
<style>
    .card { background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #333; margin-bottom: 10px; }
    .highlight { color: #00ff88; font-weight: bold; font-size: 28px; }
    .tax-card { background-color: #2e1a1a; border: 1px solid #ff4b4b; padding: 20px; border-radius: 10px; }
    .tax-highlight { color: #ff4b4b; font-weight: bold; font-size: 28px; }
</style>
""", unsafe_allow_html=True)

# --- 2. 擴充 ETF 數據庫 (加入新標的) ---
# div: 預估年配息(元/張), freq: 每年配息次數
etf_db = {
    "00919 群益台灣精選高息": {"id": "00919", "div": 2.8, "freq": 4, "months": [3, 6, 9, 12]},
    "00918 大華優利高填息30": {"id": "00918", "div": 3.0, "freq": 4, "months": [3, 6, 9, 12]},
    "00713 元大台灣高息低波": {"id": "00713", "div": 6.0, "freq": 4, "months": [3, 6, 9, 12]},
    "00878 國泰永續高股息": {"id": "00878", "div": 1.6, "freq": 4, "months": [2, 5, 8, 11]},
    "0056 元大高股息": {"id": "0056", "div": 3.2, "freq": 4, "months": [1, 4, 7, 10]},
    "00929 復華台灣科技優息": {"id": "00929", "div": 2.4, "freq": 12, "months": list(range(1, 13))},
    "00934B 中信優選8+配息": {"id": "00934B", "div": 0.6, "freq": 12, "months": list(range(1, 13))},
    "00712 FH富時不動產": {"id": "00712", "div": 0.8, "freq": 4, "months": [3, 6, 9, 12]},
    "00922 國泰台灣領袖50": {"id": "00922", "div": 1.2, "freq": 2, "months": [4, 10]},
    "0050 元大台灣50": {"id": "0050", "div": 4.5, "freq": 2, "months": [1, 7]},
}

# --- 3. 側邊欄連動邏輯 ---
st.sidebar.header("🎯 總預算與分配")

def update_all_cash():
    if st.session_state.get('selected_etfs'):
        avg = int(st.session_state.total_budget / len(st.session_state.selected_etfs))
        for name in st.session_state.selected_etfs:
            st.session_state[f"cash_{name}"] = avg

total_budget = st.sidebar.number_input("每月總投入預算 (元)", value=20000, step=1000, key="total_budget", on_change=update_all_cash)
comp_years = st.sidebar.slider("模擬年數", 1, 30, 10)
reinvest_ratio = st.sidebar.slider("股息再投入比例 (%)", 0, 100, 100) / 100

selected_etfs = st.sidebar.multiselect("選取標的", options=list(etf_db.keys()), default=["00919 群益台灣精選高息", "00713 元大台灣高息低波"], key="selected_etfs", on_change=update_all_cash)

# Session 初始化
if 'selected_etfs' in st.session_state:
    avg_init = int(total_budget / len(selected_etfs)) if selected_etfs else 0
    for name in selected_etfs:
        if f"cash_{name}" not in st.session_state: st.session_state[f"cash_{name}"] = avg_init

user_data = {}
for name in selected_etfs:
    st.sidebar.subheader(f"📍 {name}")
    owned = st.sidebar.number_input(f"目前持有張數", min_value=0.0, step=0.1, key=f"owned_{name}")
    cash = st.sidebar.number_input(f"每月投入現金 (元)", min_value=0, key=f"cash_{name}")
    user_data[name] = {"owned": owned, "cash": cash}

# --- 4. 數據計算與健保費精算 ---
def get_live_price(sid):
    try:
        df = api.taiwan_stock_daily(stock_id=sid, start_date=(datetime.datetime.now()-datetime.timedelta(days=7)).strftime("%Y-%m-%d"))
        return float(df['close'].iloc[-1])
    except: return 25.0

price_map = {n: get_live_price(etf_db[n]["id"]) for n in user_data.keys()}

summary_list = []
total_annual_div = 0
total_tax_cost = 0 # 二代健保總額
total_mkt_val_wan = 0

for n, info in user_data.items():
    p = price_map[n]
    shares = info["owned"]
    db = etf_db[n]
    
    # 計算單次配息金額 (張數 * 年配息 / 配息次數 * 1000)
    single_div = (shares * db["div"] * 1000) / db["freq"]
    
    # 二代健保判斷 (單次 > 20,000)
    tax_rate = 0.0211 # 2.11%
    tax_per_time = single_div * tax_rate if single_div >= 20000 else 0
    annual_tax = tax_per_time * db["freq"]
    
    total_annual_div += (shares * db["div"] * 1000)
    total_tax_cost += annual_tax
    total_mkt_val_wan += (shares * p * 1000) / 10000
    
    summary_list.append({
        "標的": n,
        "單次配息預估": int(single_div),
        "二代健保(單次)": int(tax_per_time),
        "頻率": f"{db['freq']}次/年",
        "市值(萬)": round((shares * p * 1000) / 10000, 2)
    })

# 複利模擬 (含稅後再投入)
history = []
temp_shares = {n: info["owned"] for n, info in user_data.items()}
for y in range(1, comp_years + 1):
    y_div_taxed = 0
    y_val = 0
    for _ in range(12): 
        for n in temp_shares:
            temp_shares[n] += user_data[n]["cash"] / (price_map[n] * 1000)
    for n, s in temp_shares.items(): 
        # 複利時也扣除健保費
        single = (s * etf_db[n]["div"] * 1000) / etf_db[n]["freq"]
        tax = single * 0.0211 if single >= 20000 else 0
        net_annual_div = (single - tax) * etf_db[n]["freq"]
        temp_shares[n] += (net_annual_div * reinvest_ratio) / (price_map[n] * 1000)
        y_div_taxed += net_annual_div
        y_val += (temp_shares[n] * price_map[n] * 1000) / 10000
    history.append({"年度": f"第 {y} 年", "稅後月領": int(y_div_taxed/12), "資產總額(萬)": round(y_val, 1)})

# --- 5. 介面呈現 ---
st.title("🏦 ETF 健保避稅與複利試算")

c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="card"><small>目前稅後月領</small><div class="highlight">{int((total_annual_div - total_tax_cost)/12)} 元</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="tax-card"><small>每年二代健保成本</small><div class="tax-highlight">{int(total_tax_cost)} 元</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="card"><small>目前資產市值</small><div class="highlight">{round(total_mkt_val_wan, 2)} 萬</div></div>', unsafe_allow_html=True)

st.subheader("📋 健保費課徵預估明細")
st.table(pd.DataFrame(summary_list))

st.subheader(f"📈 {comp_years} 年「稅後」資產成長曲線")
st.line_chart(pd.DataFrame(history).set_index("年度"))

with st.expander("🔍 查看逐年「扣稅後」複利數據表"):
    st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)

st.info("💡 避稅小撇步：如果你的單次配息超過 20,000 元，可以考慮將資金分散到「月配息」標的（如 00929、00934B），或分散到不同月份配息的季配標的，以降低單次領息金額。")
