import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
import datetime
import os

# --- 1. 頁面設定 ---
st.set_page_config(page_title="ETF 稅務成本與複利試算", page_icon="🏦", layout="wide")

# --- Token 設定（從環境變數讀取，避免金鑰外洩）---
# 執行前在終端機設定：set FINMIND_TOKEN=你的token  (Windows)
# 或是直接在下方字串填入（僅限本機自用，不要上傳到 GitHub）
FINMIND_TOKEN = os.environ.get("FINMIND_TOKEN", "在這裡填入你的Token")
api = DataLoader(token=FINMIND_TOKEN)

st.markdown("""
<style>
    .card { background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #333; margin-bottom: 10px; }
    .highlight { color: #00ff88; font-weight: bold; font-size: 28px; }
    .tax-card { background-color: #2e1a1a; border: 1px solid #ff4b4b; padding: 20px; border-radius: 10px; }
    .tax-highlight { color: #ff4b4b; font-weight: bold; font-size: 28px; }
</style>
""", unsafe_allow_html=True)

# --- 2. ETF 資料庫 ---
etf_db = {
    "00919 群益台灣精選高息": {"id": "00919", "div": 2.8, "freq": 4,  "months": [3, 6, 9, 12]},
    "00713 元大台灣高息低波": {"id": "00713", "div": 6.0, "freq": 4,  "months": [3, 6, 9, 12]},
    "00918 大華優利高填息30": {"id": "00918", "div": 3.0, "freq": 4,  "months": [3, 6, 9, 12]},
    "00878 國泰永續高股息":   {"id": "00878", "div": 1.6, "freq": 4,  "months": [2, 5, 8, 11]},
    "0056 元大高股息":        {"id": "0056",  "div": 3.2, "freq": 4,  "months": [1, 4, 7, 10]},
    "00929 復華台灣科技優息": {"id": "00929", "div": 2.4, "freq": 12, "months": list(range(1, 13))},
    "00934 中信成長高股息":   {"id": "00934", "div": 1.6, "freq": 12, "months": list(range(1, 13))},
    "00945B 凱基美債15+":     {"id": "00945B","div": 1.2, "freq": 12, "months": list(range(1, 13))},
    "00712 FH富時不動產":     {"id": "00712", "div": 0.8, "freq": 4,  "months": [3, 6, 9, 12]},
    "00922 國泰台灣領袖50":   {"id": "00922", "div": 1.2, "freq": 2,  "months": [4, 10]},
    "2884 玉山金":            {"id": "2884",  "div": 1.4, "freq": 1,  "months": [8]},
    "0050 元大台灣50":        {"id": "0050",  "div": 4.5, "freq": 2,  "months": [1, 7]},
}

# --- 3. 價格快取（關鍵修正：避免每次互動都重打 API）---
# st.cache_data 讓價格每 30 分鐘才重抓一次，調整滑桿不會重打 API
@st.cache_data(ttl=1800, show_spinner="抓取最新股價中...")
def get_all_prices(stock_ids: tuple) -> dict:
    """一次抓取所有標的最新收盤價，結果快取 30 分鐘"""
    result = {}
    start = (datetime.datetime.now() - datetime.timedelta(days=10)).strftime("%Y-%m-%d")
    for sid in stock_ids:
        try:
            df = api.taiwan_stock_daily(stock_id=sid, start_date=start)
            result[sid] = float(df["close"].iloc[-1]) if not df.empty else 25.0
        except Exception:
            result[sid] = 25.0
    return result

# --- 4. 健保費計算（單獨函式，邏輯清楚）---
def calc_nhi(single_payment: float) -> float:
    """
    二代健保補充保費：單次配息 > 20,000 元才課 2.11%
    上限：單次給付不超過 1,000 萬（超過部分不課）
    """
    if single_payment < 20_000:
        return 0.0
    taxable = min(single_payment, 10_000_000)
    return taxable * 0.0211

# --- 5. 側邊欄 ---
st.sidebar.header("🎯 總預算與分配")

def update_all_cash():
    names = st.session_state.get("selected_etfs", [])
    if names:
        avg = int(st.session_state.total_budget / len(names))
        for name in names:
            st.session_state[f"cash_{name}"] = avg

total_budget = st.sidebar.number_input(
    "每月總預算 (元)", value=20000, step=1000,
    key="total_budget", on_change=update_all_cash
)
comp_years    = st.sidebar.slider("模擬年數", 1, 30, 10)
reinvest_ratio = st.sidebar.slider("股息再投入比例 (%)", 0, 100, 100) / 100

selected_etfs = st.sidebar.multiselect(
    "選取標的", options=list(etf_db.keys()),
    default=["00919 群益台灣精選高息", "00934 中信成長高股息"],
    key="selected_etfs", on_change=update_all_cash
)

# Session 初始化
avg_init = int(total_budget / len(selected_etfs)) if selected_etfs else 0
for name in selected_etfs:
    if f"cash_{name}" not in st.session_state:
        st.session_state[f"cash_{name}"] = avg_init

user_data = {}
for name in selected_etfs:
    st.sidebar.subheader(f"📍 {name}")
    owned = st.sidebar.number_input(f"目前張數", min_value=0.0, step=0.1, key=f"owned_{name}")
    cash  = st.sidebar.number_input(f"每月投入現金 (元)", min_value=0, key=f"cash_{name}")
    user_data[name] = {"owned": owned, "cash": cash}

# --- 6. 抓價格（利用快取，只在標的改變時才重打 API）---
if not selected_etfs:
    st.info("請在左側選取至少一個標的")
    st.stop()

stock_ids = tuple(etf_db[n]["id"] for n in selected_etfs)
price_by_id = get_all_prices(stock_ids)
price_map = {n: price_by_id[etf_db[n]["id"]] for n in selected_etfs}

# --- 7. 目前狀態計算 ---
summary_list = []
total_annual_div_raw = 0.0
total_annual_tax     = 0.0
total_mkt_val_wan    = 0.0

for name, info in user_data.items():
    p   = price_map[name]
    db  = etf_db[name]
    shares = info["owned"]

    annual_div  = shares * db["div"] * 1000           # 年總配息（元）
    single_div  = annual_div / db["freq"]              # 單次配息（元）
    single_tax  = calc_nhi(single_div)                 # 單次健保費
    annual_tax  = single_tax * db["freq"]              # 年健保費

    mkt_val_wan = (shares * p * 1000) / 10_000        # 市值（萬）

    total_annual_div_raw += annual_div
    total_annual_tax     += annual_tax
    total_mkt_val_wan    += mkt_val_wan

    summary_list.append({
        "標的":       name,
        "單次配息":   f"{int(single_div):,} 元",
        "單次健保費": f"{int(single_tax):,} 元",
        "配息頻率":   f"{db['freq']} 次/年",
        "年健保費":   f"{int(annual_tax):,} 元",
        "市值(萬)":   round(mkt_val_wan, 2),
    })

# --- 8. 複利模擬 ---
history = []
temp_shares   = {n: info["owned"] for n, info in user_data.items()}
cumulative_tax = 0.0

for y in range(1, comp_years + 1):
    y_div_net      = 0.0
    y_val          = 0.0
    y_tax_this_yr  = 0.0

    # 每月定期投入（以整股計，不買零股）
    for _ in range(12):
        for name in temp_shares:
            p = price_map[name]
            monthly_cash = user_data[name]["cash"]
            # 買整張（1張=1000股），剩餘現金留著下個月累積
            lots = int(monthly_cash / (p * 1000))
            temp_shares[name] += lots

    # 年度配息結算
    for name, shares in temp_shares.items():
        p  = price_map[name]
        db = etf_db[name]

        annual_div = shares * db["div"] * 1000
        single_div = annual_div / db["freq"]
        annual_tax = calc_nhi(single_div) * db["freq"]
        net_div    = annual_div - annual_tax

        y_tax_this_yr += annual_tax

        # 再投入（同樣以整張計）
        reinvest_cash = net_div * reinvest_ratio
        lots = int(reinvest_cash / (p * 1000))
        temp_shares[name] += lots

        y_div_net += net_div
        y_val     += (temp_shares[name] * p * 1000) / 10_000

    cumulative_tax += y_tax_this_yr

    history.append({
        "年度":          f"第 {y} 年",
        "稅後月領(元)":  int(y_div_net / 12),
        "資產總額(萬)":  round(y_val, 1),
        "本年健保費(元)": int(y_tax_this_yr),
        "累計健保費(元)": int(cumulative_tax),
    })

df_h = pd.DataFrame(history)

# --- 9. 畫面呈現 ---
st.title("🏦 ETF 稅務成本與複利試算")

last_refresh = datetime.datetime.now().strftime("%H:%M")
st.caption(f"股價快取 30 分鐘更新一次 · 最後刷新：{last_refresh}")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(
        f'<div class="card"><small>目前稅後月領</small>'
        f'<div class="highlight">{int((total_annual_div_raw - total_annual_tax) / 12):,} 元</div></div>',
        unsafe_allow_html=True
    )
with c2:
    st.markdown(
        f'<div class="tax-card"><small>目前每年二代健保成本</small>'
        f'<div class="tax-highlight">{int(total_annual_tax):,} 元</div></div>',
        unsafe_allow_html=True
    )
with c3:
    st.markdown(
        f'<div class="card"><small>目前資產市值</small>'
        f'<div class="highlight">{round(total_mkt_val_wan, 2):,} 萬</div></div>',
        unsafe_allow_html=True
    )

st.subheader("📋 健保費課徵預估明細")
st.table(pd.DataFrame(summary_list))

st.subheader(f"📈 {comp_years} 年「稅後」成長曲線")
st.line_chart(df_h.set_index("年度")[["資產總額(萬)"]])

with st.expander("🔍 查看逐年「扣稅後」複利數據與累計健保費"):
    st.write("每月投入以整張計算（不含零股），股息再投入同樣以整張計。")
    st.dataframe(df_h, use_container_width=True, hide_index=True)

st.info(
    "💡 小提醒：月配型 ETF（00929、00934、00945B）"
    "單次配息通常低於 2 萬，可有效規避二代健保補充保費。"
    "季配型標的持股越多，單次配息越容易超過門檻。"
)
