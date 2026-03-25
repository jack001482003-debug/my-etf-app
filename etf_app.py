import streamlit as st
import pandas as pd
import yfinance as yf

# --- 1. 頁面設定 ---
st.set_page_config(page_title="ETF 萬能配置王", page_icon="💰", layout="wide")

# 自定義 CSS (螢光綠與對比色)
st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #00ff88; }
    .card { background-color: #1e1e1e; padding: 20px; border-radius: 10px; border-left: 5px solid #00ff88; border: 1px solid #333; }
    .highlight { color: #00ff88; font-weight: bold; font-size: 28px; }
    .stSlider [data-baseweb="slider"] { margin-bottom: 25px; }
</style>
""", unsafe_allow_html=True)

# --- 2. 擴充 ETF 數據庫 ---
# 這裡整理了台灣市場主流的各類標的
etf_db = {
    "00919 群益台灣精選高息": {"symbol": "00919.TW", "freq": "季配", "div": 2.8, "cat": "高股息"},
    "00878 國泰永續高股息": {"symbol": "00878.TW", "freq": "季配", "div": 1.6, "cat": "高股息"},
    "0056 元大高股息": {"symbol": "0056.TW", "freq": "季配", "div": 3.2, "cat": "高股息"},
    "00929 復華台灣科技優息": {"symbol": "00929.TW", "freq": "月配", "div": 2.4, "cat": "高股息"},
    "00940 元大台灣價值高息": {"symbol": "00940.TW", "freq": "月配", "div": 0.6, "cat": "高股息"},
    "00713 元大台灣高息低波": {"symbol": "00713.TW", "freq": "季配", "div": 6.0, "cat": "高股息"},
    "0050 元大台灣50": {"symbol": "0050.TW", "freq": "半年配", "div": 4.5, "cat": "市值型"},
    "006208 富邦台50": {"symbol": "006208.TW", "freq": "半年配", "div": 2.5, "cat": "市值型"},
    "00881 國泰台灣 5G+": {"symbol": "00881.TW", "freq": "半年配", "div": 1.2, "cat": "科技型"},
    "00830 國泰費城半導體": {"symbol": "00830.TW", "freq": "年配", "div": 2.0, "cat": "海外科技"},
    "00679B 元大美債20年": {"symbol": "00679B.TW", "freq": "季配", "div": 1.1, "cat": "債券型"},
    "00937B 群益ESG投等債20+": {"symbol": "00937B.TW", "freq": "月配", "div": 1.0, "cat": "債券型"},
}

st.title("🏦 ETF 萬能配置王：打造你的月領計畫")

# --- 3. 側邊欄：全局設定 ---
st.sidebar.header("🎯 核心目標")
total_budget = st.sidebar.number_input("總投入預算 (萬元)", value=100, step=10)
target_monthly = st.sidebar.number_input("目標月領股息 (元)", value=10000, step=1000)

st.sidebar.markdown("---")
st.sidebar.header("⚖️ 挑選標的與分配")

# 讓使用者先挑選要組合的標的
selected_etfs = st.sidebar.multiselect(
    "請選擇 1~5 支 ETF 進行分配", 
    options=list(etf_db.keys()),
    default=["00919 群益台灣精選高息", "00929 復華台灣科技優息"]
)

# 根據挑選的標的動態產生滑桿
alloc = {}
remaining = 100
for name in selected_etfs:
    if remaining > 0:
        percent = st.sidebar.slider(f"{name} (%)", 0, remaining, int(100/len(selected_etfs)))
        alloc[name] = percent
        remaining -= percent
    else:
        alloc[name] = 0

# --- 4. 計算與即時抓取 ---
results = []
total_annual_div = 0
total_current_value = 0

for name, pct in alloc.items():
    if pct > 0:
        money = (total_budget * 10000) * (pct / 100)
        try:
            # 加上緩存避免重複請求
            ticker = yf.Ticker(etf_db[name]["symbol"])
            price = ticker.fast_info['last_price']
        except:
            price = 20.0 # 預設保底
            
        shares = money / (price * 1000)
        annual_div = shares * (etf_db[name]["div"] * 1000)
        total_annual_div += annual_div
        total_current_value += money
        
        results.append({
            "標的": name,
            "類別": etf_db[name]["cat"],
            "分配比": f"{pct}%",
            "金額": f"{int(money/10000)} 萬",
            "持股張數": round(shares, 2),
            "配息頻率": etf_db[name]["freq"],
            "月均貢獻": int(annual_div / 12)
        })

# --- 5. 介面呈現 ---
# A. 數據看板
avg_monthly = total_annual_div / 12
达成率 = min(avg_monthly / target_monthly, 1.0)

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    st.markdown(f'<div class="card"><div style="color:#aaa">預估月均領息</div><div class="highlight">{int(avg_monthly)} 元</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="card"><div style="color:#aaa">目標達成率</div><div class="highlight">{round(达成率*100, 1)}%</div></div>', unsafe_allow_html=True)
with col3:
    st.write(f"### 🎯 距離月領 {target_monthly} 元還差：{max(0, int(target_monthly - avg_monthly))} 元")
    st.progress(达成率)

# B. 分配清單
st.write("### 📋 投資組合明細")
if results:
    df_res = pd.DataFrame(results)
    st.dataframe(df_res, use_container_width=True, hide_index=True)
else:
    st.warning("請在左側選擇 ETF 並分配比例！")

# C. 視覺化圖表
if results:
    c_col1, c_col2 = st.columns(2)
    with c_col1:
        st.write("#### 💰 資金佔比")
        chart_data = pd.DataFrame([{"ETF": r["標的"], "比例": int(r["分配比"].replace('%',''))} for r in results])
        st.bar_chart(chart_data.set_index("ETF"))
    with c_col2:
        st.write("#### 💵 每月領息貢獻度")
        div_chart = pd.DataFrame([{"ETF": r["標的"], "月領": r["月均貢獻"]} for r in results])
        st.area_chart(div_chart.set_index("ETF"))

# D. 底部提醒
st.info(f"💡 配置心法：目前你的組合以 **{results[0]['類別'] if results else '尚未選擇'}** 為主。若想提高達成率，可適度配置高股息標的；若想追求成長，建議保留部分比例於市值型 ETF。")