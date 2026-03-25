import streamlit as st
import pandas as pd
import yfinance as yf

# --- 1. 頁面設定 ---
st.set_page_config(page_title="ETF 月月配計畫王", page_icon="🗓️", layout="wide")

st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #00ff88; }
    .month-tag { background-color: #333; color: #00ff88; padding: 2px 8px; border-radius: 5px; margin-right: 5px; font-size: 12px; border: 1px solid #00ff88; }
    .card { background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #333; }
    .highlight { color: #00ff88; font-weight: bold; font-size: 28px; }
</style>
""", unsafe_allow_html=True)

# --- 2. 完整 ETF 數據庫 (加入配息月份邏輯) ---
# months 列表代表該 ETF 通常在哪些月份「除息」或「領息」
etf_db = {
    # 月配息系列
    "00929 復華台灣科技優息": {"symbol": "00929.TW", "freq": "月配", "div": 2.4, "months": list(range(1, 13))},
    "00940 元大台灣價值高息": {"symbol": "00940.TW", "freq": "月配", "div": 0.6, "months": list(range(1, 13))},
    "00934 中信成長高股息": {"symbol": "00934.TW", "freq": "月配", "div": 1.5, "months": list(range(1, 13))},
    "00936 台新臺灣IC設計": {"symbol": "00936.TW", "freq": "月配", "div": 1.2, "months": list(range(1, 13))},
    "00937B 群益ESG投等債20+": {"symbol": "00937B.TW", "freq": "月配", "div": 1.0, "months": list(range(1, 13))},
    
    # 季配息系列 (1, 4, 7, 10 組)
    "00919 群益台灣精選高息": {"symbol": "00919.TW", "freq": "季配", "div": 2.8, "months": [3, 6, 9, 12]},
    "00713 元大台灣高息低波": {"symbol": "00713.TW", "freq": "季配", "div": 6.0, "months": [3, 6, 9, 12]},
    
    # 季配息系列 (2, 5, 8, 11 組)
    "00878 國泰永續高股息": {"symbol": "00878.TW", "freq": "季配", "div": 1.6, "months": [2, 5, 8, 11]},
    "00900 富邦特選高股息30": {"symbol": "00900.TW", "freq": "季配", "div": 1.0, "months": [2, 5, 8, 11]},
    
    # 季配息系列 (1, 5, 8, 11 組 或 1, 4, 7, 10 等)
    "0056 元大高股息": {"symbol": "0056.TW", "freq": "季配", "div": 3.2, "months": [1, 4, 7, 10]},
    "00915 凱基優選高股息30": {"symbol": "00915.TW", "freq": "季配", "div": 2.5, "months": [3, 6, 9, 12]},
    
    # 半年配系列
    "0050 元大台灣50": {"symbol": "0050.TW", "freq": "半年配", "div": 4.5, "months": [1, 7]},
    "006208 富邦台50": {"symbol": "006208.TW", "freq": "半年配", "div": 2.5, "months": [7, 11]},
}

st.title("🏦 ETF 領息日曆配置工具")

# --- 3. 側邊欄設定 ---
st.sidebar.header("🎯 預算與目標")
total_budget = st.sidebar.number_input("投入資金 (萬元)", value=100, step=10)
target_monthly = st.sidebar.number_input("目標月領金額 (元)", value=10000, step=1000)

st.sidebar.markdown("---")
st.sidebar.header("⚖️ 配置你的組合")
selected_names = st.sidebar.multiselect("選取標的", options=list(etf_db.keys()), default=["00919 群益台灣精選高息", "00878 國泰永續高股息", "0056 元大高股息"])

alloc = {}
rem = 100
for n in selected_names:
    if rem > 0:
        p = st.sidebar.slider(f"{n} (%)", 0, rem, int(100/len(selected_names)))
        alloc[n] = p
        rem -= p

# --- 4. 計算邏輯 ---
results = []
calendar = {m: 0 for m in range(1, 13)}
total_ann_div = 0

for name, pct in alloc.items():
    if pct > 0:
        money = (total_budget * 10000) * (pct / 100)
        try:
            p_val = yf.Ticker(etf_db[name]["symbol"]).fast_info['last_price']
        except: p_val = 25.0
        
        shares = money / (p_val * 1000)
        ann_div = shares * (etf_db[name]["div"] * 1000)
        total_ann_div += ann_div
        
        # 分散到配息月份
        div_per_event = ann_div / len(etf_db[name]["months"])
        for m in etf_db[name]["months"]:
            calendar[m] += div_per_event
            
        # 格式化顯示月份
        month_str = " ".join([f"{m}月" for m in etf_db[name]["months"]])
        
        results.append({
            "標的": name,
            "分配比": f"{pct}%",
            "持股張數": round(shares, 2),
            "配息頻率": etf_db[name]["freq"],
            "預定配息月份": month_str,
            "預估年領": int(ann_div)
        })

# --- 5. 介面呈現 ---
avg_m = total_ann_div / 12
col1, col2 = st.columns([1, 2])
with col1:
    st.markdown(f'<div class="card"><div style="color:#aaa">平均月領預估</div><div class="highlight">{int(avg_m)} 元</div></div>', unsafe_allow_html=True)
with col2:
    st.write(f"### 🎯 達成率: {round(min(avg_m/target_monthly, 1.0)*100, 1)}%")
    st.progress(min(avg_m/target_monthly, 1.0))

# 配息日曆視覺化
st.write("### 📅 年度領息日曆 (預估金額)")
cal_df = pd.DataFrame({
    "月份": [f"{m}月" for m in range(1, 13)],
    "預估領息金額": [int(calendar[m]) for m in range(1, 13)]
})
st.bar_chart(cal_df.set_index("月份"))

# 明細表格
st.write("### 📋 組合詳細清單")
st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

st.info("💡 貼心提醒：若想達成『月月穩定領息』，建議混合選取【1,4,7,10月】、【2,5,8,11月】與【3,6,9,12月】發息的季配標的，或是直接配置【月配息】標的。")
