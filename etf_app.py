import streamlit as st
import pandas as pd
import requests
import datetime
 
st.set_page_config(page_title="ETF 稅務成本與複利試算", page_icon="🏦", layout="wide")
 
st.markdown("""
<style>
    .card { background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #333; margin-bottom: 10px; }
    .highlight { color: #00ff88; font-weight: bold; font-size: 28px; }
    .tax-card { background-color: #2e1a1a; border: 1px solid #ff4b4b; padding: 20px; border-radius: 10px; }
    .tax-highlight { color: #ff4b4b; font-weight: bold; font-size: 28px; }
</style>
""", unsafe_allow_html=True)
 
# --- ETF 資料庫（含預設股價，每季手動更新即可）---
etf_db = {
    "00919 群益台灣精選高息": {"id": "00919", "div": 2.8,  "freq": 4,  "months": [3,6,9,12],       "price": 22.0},
    "00713 元大台灣高息低波": {"id": "00713", "div": 6.0,  "freq": 4,  "months": [3,6,9,12],       "price": 52.0},
    "00918 大華優利高填息30": {"id": "00918", "div": 3.0,  "freq": 4,  "months": [3,6,9,12],       "price": 18.5},
    "00878 國泰永續高股息":   {"id": "00878", "div": 1.6,  "freq": 4,  "months": [2,5,8,11],       "price": 21.0},
    "0056 元大高股息":        {"id": "0056",  "div": 3.2,  "freq": 4,  "months": [1,4,7,10],       "price": 36.0},
    "00929 復華台灣科技優息": {"id": "00929", "div": 2.4,  "freq": 12, "months": list(range(1,13)),"price": 20.0},
    "00934 中信成長高股息":   {"id": "00934", "div": 1.6,  "freq": 12, "months": list(range(1,13)),"price": 17.5},
    "00945B 凱基美債15+":     {"id": "00945B","div": 1.2,  "freq": 12, "months": list(range(1,13)),"price": 35.0},
    "00712 FH富時不動產":     {"id": "00712", "div": 0.8,  "freq": 4,  "months": [3,6,9,12],       "price": 10.5},
    "00922 國泰台灣領袖50":   {"id": "00922", "div": 1.2,  "freq": 2,  "months": [4,10],           "price": 19.0},
    "2884 玉山金":            {"id": "2884",  "div": 1.4,  "freq": 1,  "months": [8],              "price": 28.0},
    "0050 元大台灣50":        {"id": "0050",  "div": 4.5,  "freq": 2,  "months": [1,7],            "price": 175.0},
}
 
# --- 用 TWSE 官方 API 抓即時股價（免費、不需要 token）---
@st.cache_data(ttl=1800, show_spinner="從證交所抓取最新股價...")
def get_twse_prices(stock_ids: tuple) -> dict:
    """
    呼叫台灣證交所公開 API 取得當日收盤價。
    快取 30 分鐘，調整滑桿不會重打 API。
    若收盤前或假日無資料，自動 fallback 到 etf_db 預設股價。
    """
    result = {}
    try:
        url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        resp = requests.get(url, timeout=10,
                            headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        data = resp.json()
        # 建立 {代號: 收盤價} 對照表
        price_lookup = {}
        for row in data:
            code  = row.get("Code", "").strip()
            close = row.get("ClosingPrice", "").strip().replace(",", "")
            if close and close != "--":
                try:
                    price_lookup[code] = float(close)
                except ValueError:
                    pass
        for sid in stock_ids:
            result[sid] = price_lookup.get(sid, None)
    except Exception:
        pass
    return result
 
# --- 健保費計算 ---
def calc_nhi(single_payment: float) -> float:
    """單次配息超過 20,000 元才課 2.11% 二代健保補充保費（上限 1000 萬）"""
    if single_payment < 20_000:
        return 0.0
    return min(single_payment, 10_000_000) * 0.0211
 
# --- 側邊欄 ---
st.sidebar.header("🎯 總預算與分配")
 
def update_all_cash():
    names = st.session_state.get("selected_etfs", [])
    if names:
        avg = int(st.session_state.total_budget / len(names))
        for name in names:
            st.session_state[f"cash_{name}"] = avg
 
total_budget   = st.sidebar.number_input("每月總預算 (元)", value=20000, step=1000,
                                          key="total_budget", on_change=update_all_cash)
comp_years     = st.sidebar.slider("模擬年數", 1, 30, 10)
reinvest_ratio = st.sidebar.slider("股息再投入比例 (%)", 0, 100, 100) / 100
 
selected_etfs = st.sidebar.multiselect(
    "選取標的", options=list(etf_db.keys()),
    default=["00919 群益台灣精選高息", "00934 中信成長高股息"],
    key="selected_etfs", on_change=update_all_cash
)
 
if not selected_etfs:
    st.info("請在左側選取至少一個標的")
    st.stop()
 
avg_init = int(total_budget / len(selected_etfs))
for name in selected_etfs:
    if f"cash_{name}" not in st.session_state:
        st.session_state[f"cash_{name}"] = avg_init
 
user_data = {}
for name in selected_etfs:
    st.sidebar.subheader(f"📍 {name}")
    owned = st.sidebar.number_input("目前張數", min_value=0.0, step=0.1, key=f"owned_{name}")
    cash  = st.sidebar.number_input("每月投入現金 (元)", min_value=0, key=f"cash_{name}")
    user_data[name] = {"owned": owned, "cash": cash}
 
# --- 取得股價（TWSE API → fallback 預設值）---
stock_ids    = tuple(etf_db[n]["id"] for n in selected_etfs)
twse_prices  = get_twse_prices(stock_ids)
 
price_map = {}
using_fallback = []
for name in selected_etfs:
    sid   = etf_db[name]["id"]
    live  = twse_prices.get(sid)
    if live:
        price_map[name] = live
    else:
        price_map[name] = etf_db[name]["price"]
        using_fallback.append(name)
 
if using_fallback:
    st.caption(f"⚠️ 以下標的使用預設股價（收盤後或假日正常）：{', '.join(using_fallback)}")
 
# --- 目前狀態計算 ---
summary_list         = []
total_annual_div_raw = 0.0
total_annual_tax     = 0.0
total_mkt_val_wan    = 0.0
 
for name, info in user_data.items():
    p      = price_map[name]
    db     = etf_db[name]
    shares = info["owned"]
 
    annual_div  = shares * db["div"] * 1000
    single_div  = annual_div / db["freq"]
    single_tax  = calc_nhi(single_div)
    annual_tax  = single_tax * db["freq"]
    mkt_val_wan = (shares * p * 1000) / 10_000
 
    total_annual_div_raw += annual_div
    total_annual_tax     += annual_tax
    total_mkt_val_wan    += mkt_val_wan
 
    summary_list.append({
        "標的":       name,
        "股價":       f"{p:.1f} 元",
        "單次配息":   f"{int(single_div):,} 元",
        "單次健保費": f"{int(single_tax):,} 元",
        "配息頻率":   f"{db['freq']} 次/年",
        "年健保費":   f"{int(annual_tax):,} 元",
        "市值(萬)":   round(mkt_val_wan, 2),
    })
 
# --- 複利模擬 ---
history       = []
temp_shares   = {n: info["owned"] for n, info in user_data.items()}
cumulative_tax = 0.0
 
for y in range(1, comp_years + 1):
    y_div_net     = 0.0
    y_val         = 0.0
    y_tax_this_yr = 0.0
 
    # 每月定期投入（整張計算）
    for _ in range(12):
        for name in temp_shares:
            p    = price_map[name]
            lots = int(user_data[name]["cash"] / (p * 1000))
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
 
        # 股息再投入（整張）
        lots = int((net_div * reinvest_ratio) / (p * 1000))
        temp_shares[name] += lots
 
        y_div_net += net_div
        y_val     += (temp_shares[name] * p * 1000) / 10_000
 
    cumulative_tax += y_tax_this_yr
 
    history.append({
        "年度":           f"第 {y} 年",
        "稅後月領(元)":   int(y_div_net / 12),
        "資產總額(萬)":   round(y_val, 1),
        "本年健保費(元)":  int(y_tax_this_yr),
        "累計健保費(元)":  int(cumulative_tax),
    })
 
df_h = pd.DataFrame(history)
 
# --- 畫面呈現 ---
st.title("🏦 ETF 稅務成本與複利試算")
st.caption(f"股價來源：台灣證交所公開 API · 每 30 分鐘更新 · {datetime.datetime.now().strftime('%H:%M')}")
 
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(
        f'<div class="card"><small>目前稅後月領</small>'
        f'<div class="highlight">{int((total_annual_div_raw - total_annual_tax) / 12):,} 元</div></div>',
        unsafe_allow_html=True)
with c2:
    st.markdown(
        f'<div class="tax-card"><small>目前每年二代健保成本</small>'
        f'<div class="tax-highlight">{int(total_annual_tax):,} 元</div></div>',
        unsafe_allow_html=True)
with c3:
    st.markdown(
        f'<div class="card"><small>目前資產市值</small>'
        f'<div class="highlight">{round(total_mkt_val_wan, 2):,} 萬</div></div>',
        unsafe_allow_html=True)
 
st.subheader("📋 健保費課徵預估明細")
st.table(pd.DataFrame(summary_list))
 
st.subheader(f"📈 {comp_years} 年「稅後」成長曲線")
st.line_chart(df_h.set_index("年度")[["資產總額(萬)"]])
 
with st.expander("🔍 查看逐年「扣稅後」複利數據與累計健保費"):
    st.write("每月投入以整張計算（不含零股），股息再投入同樣以整張計。")
    st.dataframe(df_h, use_container_width=True, hide_index=True)
 
st.info("💡 月配型 ETF（00929、00934、00945B）單次配息通常低於 2 萬，可有效規避二代健保補充保費。季配型標的持股越多，單次配息越容易超過門檻。")
