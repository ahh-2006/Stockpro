import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
import plotly.graph_objects as go
import time
from datetime import datetime
import json
from pathlib import Path
from io import StringIO
from core.data.ingest import fetch_prices_yahoo
from core.indicators.tech import add_indicators
from core.signals.rules import basic_signals
from streamlit_extras.colored_header import colored_header
from core.scanner import scan_market, get_default_tickers

# --- Page Config ---
st.set_page_config(page_title="StockPro Platform", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

# --- Logo ---
logo_path = "assets/logo.png"
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_container_width=True)
    if hasattr(st, "logo"):
        st.logo(logo_path)


# --- CSS Injection ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
html, body, [class^="css"]  {
  direction: rtl;
  text-align: right;
  font-family: 'Cairo', sans-serif;
}
/* Hide the sidebar collapse button */
[data-testid="stSidebarNav"] {display: none !important;}
/* Keep the sidebar visible, only hide the collapse button */
[data-testid="collapsedControl"] {display: none !important;}

[data-testid="stAppViewContainer"]{
  background:#0E1117;
  color:#C9D1D9;
}
[data-testid="stHeader"], [data-testid="stToolbar"]{
  background:#0E1117;
}
[data-testid="stSidebar"]{
  background:#161B22;
  border-left:1px solid #30363D;
}
.sp-card {
  background:#161B22;
  border:1px solid #30363D;
  border-radius:8px;
  padding:15px;
  margin-bottom:15px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}
.sp-metric-container {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.sp-metric-card {
  background:#21262d;
  border:1px solid #30363D;
  border-radius:6px;
  padding:10px 15px;
  flex: 1;
  min-width: 120px;
  text-align: center;
}
/* Responsive Design for Mobile */
@media (max-width: 768px) {
  .sp-metric-card {
    min-width: 45%; /* Two cards per row on mobile */
    flex: 1 1 45%;
    margin-bottom: 5px;
    padding: 8px 10px;
  }
  .sp-metric-label {
    font-size: 10px !important;
  }
  .sp-metric-value {
    font-size: 16px !important;
  }
  [data-testid="stSidebar"] {
    min-width: 200px !important;
    max-width: 250px !important;
  }
  h1, h2, h3 {
    font-size: 1.2rem !important;
  }
  .sp-card {
    padding: 10px;
  }
  /* Improve chart container on mobile */
  .js-plotly-plot {
    width: 100% !important;
  }
}
@media (max-width: 600px) {
  .block-container {
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    padding-top: 2rem !important;
  }
}
@media (max-width: 480px) {
  .sp-metric-card {
    min-width: 100%; /* Full width cards on very small screens */
    flex: 1 1 100%;
  }
}

.sp-metric-label {
  font-size: 12px;
  color: #8b949e;
  display: block;
}
.sp-metric-value {
  font-size: 18px;
  font-weight: 700;
  color: #C9D1D9;
}
.sp-metric-delta-pos {
  color: #22c55e;
  font-size: 14px;
}
.sp-metric-delta-neg {
  color: #ef4444;
  font-size: 14px;
}
.sp-signal-box {
  background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
  border: 1px solid #30363D;
  border-radius: 8px;
  padding: 15px;
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
div.stButton > button {
  background-color: #21262d;
  color: #c9d1d9;
  border: 1px solid #30363D;
  width: 100%;
}
div.stButton > button:hover {
  border-color: #58a6ff;
  color: #58a6ff;
}
div.stButton > button:focus {
  border-color: #58a6ff;
  color: #58a6ff;
}
</style>
""", unsafe_allow_html=True)

# --- Session State Init ---
hist_file = Path("search_history.json")
trades_file = Path("trades.json")

# --- Header ---
st.markdown("""
<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid #30363D;margin-bottom:20px;">
  <div style="display:flex;align-items:center;gap:10px;">
    <span style="font-size:24px;">🐂</span>
    <div>
      <h3 style="margin:0;color:#58a6ff;font-weight:700;">StockPro</h3>
      <span style="font-size:12px;color:#8b949e;">PROFESSIONAL TRADING</span>
    </div>
  </div>
  <div style="text-align:left;">
    <span style="color:#22c55e;font-weight:700;">● Live</span>
    <span style="color:#8b949e;font-size:12px;">v2.0</span>
  </div>
</div>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner=False, ttl=300)
def load_yahoo_cached(ticker: str, interval: str, period: str):
    return fetch_prices_yahoo(ticker, interval=interval, period=period)

col1, col2, col3 = st.columns([2, 1, 1])
if "search_history" not in st.session_state:
    try:
        st.session_state["search_history"] = json.loads(hist_file.read_text(encoding="utf-8")) if hist_file.exists() else []
    except Exception:
        st.session_state["search_history"] = []
if "tickers_input" not in st.session_state:
    st.session_state["tickers_input"] = ""
if "pending_ticker" in st.session_state:
    st.session_state["tickers_input"] = st.session_state.pop("pending_ticker")

# Initialize tool_section in session state if not present
if "tool_section" not in st.session_state:
    st.session_state["tool_section"] = "📈 المؤشرات"

with col1:
    s_in, s_btn = st.columns([5, 1])
    tickers_input = s_in.text_input("الرموز", st.session_state.get("tickers_input", ""), key="tickers_input").strip()
    run = s_btn.button("تحليل", type="primary", use_container_width=True)
with col2:
    interval = st.selectbox("الإطار الزمني", ["1d", "1h", "30m", "15m", "5m", "1m"], index=0)
with col3:
    period = st.selectbox("المدى (period)", ["7d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"], index=0)
    if interval == "1m" and period not in ["1d", "5d", "7d", "ytd"]:
        st.caption("لفاصل 1m يُفضّل اختيار 7d أو 5d بسبب قيود المصدر")

tool_items = [
    "📚 سجل البحث",
    "📈 المؤشرات",
    "⚙️ إعدادات المؤشرات",
    "🎯 الاقتراحات والمخاطر",
    "🔍 الماسح الضوئي",
]

# Ensure the session state value is in the list
if st.session_state["tool_section"] not in tool_items:
     st.session_state["tool_section"] = tool_items[1] # Default to Indicators

# Find index of current selection
current_index = tool_items.index(st.session_state["tool_section"])

st.sidebar.title("التنقل")
selected_tool = st.sidebar.radio("اختر الأداة", tool_items, index=current_index, key="tool_section_widget", label_visibility="collapsed")

# Update session state when widget changes
if selected_tool != st.session_state["tool_section"]:
    st.session_state["tool_section"] = selected_tool
    st.rerun()
    
section = st.session_state["tool_section"].split(" ", 1)[1]

# Initialize scanner variables
do_scan = False
scan_min_price = 1.0
scan_max_price = 20.0
scan_min_vol = 1_000_000.0
scan_min_chg = 3.0

if section == "الماسح الضوئي":
    with st.sidebar:
        colored_header(label="الماسح الضوئي", description="بحث سريع عن الفرص", color_name="green-70")
        scan_min_price = st.number_input("الحد الأدنى للسعر", value=1.0, min_value=0.1, step=0.5)
        scan_max_price = st.number_input("الحد الأعلى للسعر", value=20.0, min_value=1.0, step=1.0)
        scan_min_vol = st.number_input("الحد الأدنى للحجم (مليون)", value=1.0, min_value=0.1, step=0.5) * 1_000_000
        scan_min_chg = st.number_input("الحد الأدنى للتغيير %", value=3.0, min_value=-10.0, step=0.5)
        do_scan = st.button("🔎 ابدأ المسح", use_container_width=True)

# --- Scanner Section UI in Main Area ---
if section == "الماسح الضوئي":
    st.markdown("<h2 style='text-align: center; color: #58a6ff;'>🔍 ماسح السوق الذكي</h2>", unsafe_allow_html=True)
    st.info("يقوم هذا الماسح بالبحث في قائمة مختارة من الأسهم (Penny Stocks وأسهم التكنولوجيا) للعثور على الفرص بناءً على معاييرك.")
    
    if do_scan:
        with st.spinner("جاري مسح السوق... يرجى الانتظار"):
            scan_tickers = get_default_tickers()
            res_df = scan_market(scan_tickers, scan_min_price, scan_max_price, scan_min_vol, scan_min_chg)
            st.session_state["scan_results"] = res_df
            
    if "scan_results" in st.session_state and not st.session_state["scan_results"].empty:
        res_df = st.session_state["scan_results"]
        st.success(f"تم العثور على {len(res_df)} فرصة!")
        
        # Format for display
        st.dataframe(
            res_df.style.background_gradient(subset=["التغيير %"], cmap="Greens").format({"السعر": "{:.2f}", "التغيير %": "{:+.2f}%", "الحجم": "{:,}"}),
            use_container_width=True
        )
        
        # Quick Analyze Buttons
        st.markdown("### ⚡ تحليل سريع")
        cols = st.columns(min(len(res_df), 4))
        for idx, row in res_df.iterrows():
            c = cols[idx % 4]
            if c.button(f"تحليل {row['الرمز']}", key=f"scan_analyze_{row['الرمز']}"):
                st.session_state["pending_ticker"] = row['الرمز']
                # Correctly set the tool_section to the string value
                st.session_state["tool_section"] = "📈 المؤشرات"
                st.rerun()
    elif "scan_results" in st.session_state and st.session_state["scan_results"].empty:
        st.warning("لم يتم العثور على أي أسهم تطابق المعايير الحالية. جرب توسيع نطاق البحث.")

# --- Persistent Sidebar Controls ---
st.sidebar.markdown("---")
force_run = st.sidebar.button("🔄 تحديث الآن", use_container_width=True)

st.sidebar.markdown("##### ⚡ إعدادات سريعة")
p1, p2, p3 = st.sidebar.columns(3)
if p1.button("Scalp", help="إعدادات للمضاربة اللحظية", use_container_width=True):
    st.session_state["show_bbands"] = False
    st.session_state["show_rsi"] = True
    st.session_state["show_adx"] = True
    st.session_state["show_atr"] = True
    st.session_state["show_keltner"] = True
    st.session_state["show_ichimoku"] = False
    st.session_state["show_vwap"] = True
    st.session_state["show_obv"] = False
    st.session_state["show_stoch"] = True
    st.rerun()
if p2.button("Swing", help="إعدادات للتداول المتوسط", use_container_width=True):
    st.session_state["show_bbands"] = True
    st.session_state["show_rsi"] = True
    st.session_state["show_adx"] = True
    st.session_state["show_atr"] = False
    st.session_state["show_keltner"] = False
    st.session_state["show_ichimoku"] = True
    st.session_state["show_vwap"] = True
    st.session_state["show_obv"] = True
    st.session_state["show_stoch"] = False
    st.rerun()
if p3.button("Trend", help="إعدادات لتتبع الاتجاه", use_container_width=True):
    st.session_state["show_bbands"] = False
    st.session_state["show_rsi"] = False
    st.session_state["show_adx"] = True
    st.session_state["show_atr"] = True
    st.session_state["show_keltner"] = True
    st.session_state["show_ichimoku"] = True
    st.session_state["show_vwap"] = True
    st.session_state["show_obv"] = True
    st.session_state["show_stoch"] = False
    st.rerun()
if st.sidebar.button("🧹 تصفير الفلاتر", use_container_width=True):
    for k, v in {
        "show_bbands": True, "show_rsi": True, "show_adx": False, "show_atr": False,
        "show_keltner": False, "show_ichimoku": False, "show_vwap": False, "show_obv": False,
        "show_stoch": False, "auto_update": True
    }.items():
        st.session_state[k] = v
    st.rerun()
last_update = st.session_state.get("last_update", "—")
last_symbols = st.session_state.get("last_symbols_count", 0)
st.sidebar.caption(f"آخر تحديث: {last_update}")
st.sidebar.caption(f"عدد الرموز: {last_symbols}")


if section == "سجل البحث":
    with st.sidebar:
        colored_header(label="سجل البحث", description="آخر الرموز التي تم البحث عنها", color_name="blue-70")
        if st.session_state["search_history"]:
            head_l, head_r = st.columns([3, 1])
            with head_l:
                st.write("آخر الرموز")
            with head_r:
                if st.button("مسح", key="clear_history"):
                    st.session_state["search_history"] = []
                    try:
                        hist_file.write_text(json.dumps(st.session_state["search_history"], ensure_ascii=False), encoding="utf-8")
                    except Exception:
                        pass
                    st.rerun()
            for i, sym in enumerate(st.session_state["search_history"][:12]):
                b_sel, b_del = st.columns([4, 1])
                if b_sel.button(sym, key=f"hist_sel_{i}"):
                    st.session_state["pending_ticker"] = sym
                    st.rerun()
                if b_del.button("✕", key=f"hist_del_{i}"):
                    st.session_state["search_history"] = [s for s in st.session_state["search_history"] if s != sym]
                    try:
                        hist_file.write_text(json.dumps(st.session_state["search_history"], ensure_ascii=False), encoding="utf-8")
                    except Exception:
                        pass
                    st.rerun()

if section == "المؤشرات":
    with st.sidebar:
        colored_header(label="المؤشرات الفنية", description="اختر المؤشرات لعرضها على الرسم", color_name="violet-70")
        st.checkbox("Bollinger Bands", value=st.session_state.get("show_bbands", True), key="show_bbands")
        st.checkbox("RSI", value=st.session_state.get("show_rsi", True), key="show_rsi")
        st.checkbox("ADX", value=st.session_state.get("show_adx", False), key="show_adx")
        st.checkbox("ATR", value=st.session_state.get("show_atr", False), key="show_atr")
        st.checkbox("Keltner", value=st.session_state.get("show_keltner", False), key="show_keltner")
        st.checkbox("Ichimoku", value=st.session_state.get("show_ichimoku", False), key="show_ichimoku")
        st.checkbox("VWAP", value=st.session_state.get("show_vwap", False), key="show_vwap")
        st.checkbox("OBV", value=st.session_state.get("show_obv", False), key="show_obv")
        st.checkbox("Stochastic %K/%D", value=st.session_state.get("show_stoch", False), key="show_stoch")
        st.checkbox("تحديث التحليل عند التغيير", value=st.session_state.get("auto_update", True), key="auto_update")

if section == "إعدادات المؤشرات":
    with st.sidebar:
        colored_header(label="إعدادات المؤشرات", description="تخصيص القيم والفترات", color_name="orange-70")
        st.number_input("SMA قصيرة", value=st.session_state.get("sma_short", 20), min_value=2, max_value=500, key="sma_short")
        st.number_input("SMA طويلة", value=st.session_state.get("sma_long", 50), min_value=2, max_value=500, key="sma_long")
        st.number_input("نافذة EMA", value=st.session_state.get("ema_win", 20), min_value=2, max_value=500, key="ema_win")
        st.number_input("نافذة RSI", value=st.session_state.get("rsi_win", 14), min_value=2, max_value=200, key="rsi_win")
        st.number_input("MACD سريع", value=st.session_state.get("macd_fast", 12), min_value=2, max_value=200, key="macd_fast")
        st.number_input("MACD بطيء", value=st.session_state.get("macd_slow", 26), min_value=2, max_value=400, key="macd_slow")
        st.number_input("MACD إشارة", value=st.session_state.get("macd_signal", 9), min_value=2, max_value=200, key="macd_signal")
        st.number_input("نافذة بولنجر", value=st.session_state.get("bb_win", 20), min_value=2, max_value=400, key="bb_win")
        st.number_input("انحراف معياري بولنجر", value=st.session_state.get("bb_std", 2.0), min_value=0.5, max_value=5.0, step=0.1, key="bb_std")
        st.number_input("نافذة ATR", value=st.session_state.get("atr_win", 14), min_value=2, max_value=400, key="atr_win")
        st.number_input("نافذة ADX", value=st.session_state.get("adx_win", 14), min_value=2, max_value=400, key="adx_win")
        st.number_input("Stoch K", value=st.session_state.get("stoch_k", 14), min_value=2, max_value=400, key="stoch_k")
        st.number_input("Stoch D", value=st.session_state.get("stoch_d", 3), min_value=1, max_value=200, key="stoch_d")
        st.number_input("Keltner EMA (متوسط)", value=st.session_state.get("kel_ema", 20), min_value=2, max_value=400, key="kel_ema")
        st.number_input("Keltner ATR (مدى)", value=st.session_state.get("kel_atr", 10), min_value=2, max_value=400, key="kel_atr")
        st.number_input("معامل كيلتنر", value=st.session_state.get("kel_mult", 2.0), min_value=0.5, max_value=5.0, step=0.1, key="kel_mult")
if "trades" not in st.session_state:
    try:
        st.session_state["trades"] = json.loads(trades_file.read_text(encoding="utf-8")) if trades_file.exists() else []
    except Exception:
        st.session_state["trades"] = []
if st.session_state["trades"]:
    for tr in st.session_state["trades"]:
        if "closed_qty" not in tr:
            tr["closed_qty"] = 0
        if "realized_pl" not in tr:
            tr["realized_pl"] = 0.0
        if "status" not in tr:
            tr["status"] = "open"
if "atr_entry_default" not in st.session_state:
    st.session_state["atr_entry_default"] = 0.1
if "t1_r_default" not in st.session_state:
    st.session_state["t1_r_default"] = 1.0
if "t2_r_default" not in st.session_state:
    st.session_state["t2_r_default"] = 2.0
if section == "الاقتراحات والمخاطر":
    with st.sidebar:
        colored_header(label="إدارة المخاطر", description="Presets وحساب حجم الصفقات", color_name="red-70")
        
        st.markdown("##### ⚙️ إعدادات سريعة (Presets)")
        
        # Row 1
        r1_c1, r1_c2 = st.columns(2)
        with r1_c1:
            if st.button("🛡️ محافظ", help="Entry: 0.05×ATR | TP: 1.5R / 3R", use_container_width=True):
                st.session_state["atr_entry_default"] = 0.05
                st.session_state["t1_r_default"] = 1.5
                st.session_state["t2_r_default"] = 3.0
                st.rerun()
        with r1_c2:
            if st.button("📈 اتجاهي", help="Entry: 0.1×ATR | TP: 1R / 2R", use_container_width=True):
                st.session_state["atr_entry_default"] = 0.1
                st.session_state["t1_r_default"] = 1.0
                st.session_state["t2_r_default"] = 2.0
                st.rerun()
        
        # Row 2
        r2_c1, r2_c2 = st.columns(2)
        with r2_c1:
            if st.button("⚡ سكالب", help="Entry: 0.2×ATR | TP: 0.5R / 1R", use_container_width=True):
                st.session_state["atr_entry_default"] = 0.2
                st.session_state["t1_r_default"] = 0.5
                st.session_state["t2_r_default"] = 1.0
                st.rerun()
        with r2_c2:
            if st.button("🗑️ تصفير", help="مسح جميع الصفقات وسجل البحث", use_container_width=True):
                st.session_state["trades"] = []
                st.session_state["search_history"] = []
                try:
                    hist_file.write_text(json.dumps(st.session_state["search_history"], ensure_ascii=False), encoding="utf-8")
                except Exception:
                    pass
                st.rerun()
                
        st.divider()
        st.markdown("##### 🧮 حاسبة المخاطر")
        
        st.number_input("قيمة المخاطرة لكل صفقة ($)", value=st.session_state.get("risk_dollars", 100), min_value=10, max_value=100000, step=10, key="risk_dollars")
        
        c_input1, c_input2 = st.columns(2)
        with c_input1:
            st.number_input("هامش الدخول (ATR×)", value=st.session_state.get("atr_entry_default", 0.1), min_value=0.0, max_value=2.0, step=0.05, key="atr_entry_mult")
        with c_input2:
            st.number_input("الهدف الأول (R)", value=st.session_state.get("t1_r_default", 1.0), min_value=0.2, max_value=5.0, step=0.1, key="t1_r")
            
        st.number_input("الهدف الثاني (R)", value=st.session_state.get("t2_r_default", 2.0), min_value=0.5, max_value=10.0, step=0.5, key="t2_r")

with st.expander("💼 محفظة التداول الافتراضي", expanded=False):
    if st.session_state["trades"]:
        rows_live = []
        symbols = sorted({t["symbol"] for t in st.session_state["trades"]})
        latest = {}
        for sym in symbols:
            try:
                dtmp = load_yahoo_cached(sym, interval=interval, period="7d")
                if not dtmp.empty:
                    latest[sym] = float(dtmp["close"].iloc[-1])
            except Exception:
                pass
        total_realized = 0.0
        total_unreal = 0.0
        for idx, tr in enumerate(st.session_state["trades"]):
            px = latest.get(tr["symbol"])
            pl = None
            rem_qty = tr["qty"] - tr.get("closed_qty", 0)
            if px is not None and rem_qty > 0:
                if tr["side"] == "طويل":
                    pl = (px - tr["entry"]) * rem_qty
                else:
                    pl = (tr["entry"] - px) * rem_qty
                total_unreal += pl
            total_realized += float(tr.get("realized_pl", 0.0))
            rows_live.append({
                "الرمز": tr["symbol"],
                "الاتجاه": tr["side"],
                "الدخول": tr["entry"],
                "الوقف": tr["stop"],
                "هدف1": tr["tp1"],
                "هدف2": tr["tp2"],
                "الكمية": tr["qty"],
                "المنفذ": tr.get("closed_qty", 0),
                "المتبقي": rem_qty,
                "السعر الحالي": px if px is not None else None,
                "P&L غير محقق": round(pl, 2) if pl is not None else None,
                "P&L محقق": round(float(tr.get("realized_pl", 0.0)), 2),
                "الحالة": tr.get("status", "open"),
                "الوقت": tr["time"],
            })
        df_tr = pd.DataFrame(rows_live)
        st.dataframe(df_tr, use_container_width=True)
        m1, m2 = st.columns(2)
        with m1:
            st.metric("إجمالي P&L محقق", f"{total_realized:.2f}")
        with m2:
            st.metric("إجمالي P&L غير محقق", f"{total_unreal:.2f}")
        for idx, tr in enumerate(st.session_state["trades"]):
            px = latest.get(tr["symbol"])
            c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
            with c1:
                st.write(f"{tr['symbol']} | {tr['side']} | متبقي: {tr['qty'] - tr.get('closed_qty', 0)}")
            with c2:
                if st.button("Close 50% at TP1", key=f"t_close50_{idx}"):
                    rem = tr["qty"] - tr.get("closed_qty", 0)
                    if rem > 0:
                        close_qty = max(1, rem // 2)
                        price_exec = tr["tp1"]
                        if tr["side"] == "طويل":
                            tr["realized_pl"] = float(tr.get("realized_pl", 0.0)) + (price_exec - tr["entry"]) * close_qty
                        else:
                            tr["realized_pl"] = float(tr.get("realized_pl", 0.0)) + (tr["entry"] - price_exec) * close_qty
                        tr["closed_qty"] = tr.get("closed_qty", 0) + close_qty
                        if tr["closed_qty"] >= tr["qty"]:
                            tr["status"] = "closed"
                        try:
                            trades_file.write_text(json.dumps(st.session_state["trades"], ensure_ascii=False), encoding="utf-8")
                        except Exception:
                            pass
                        st.rerun()
            with c3:
                if st.button("Close All at Market", key=f"t_closeall_{idx}"):
                    rem = tr["qty"] - tr.get("closed_qty", 0)
                    if rem > 0 and px is not None:
                        if tr["side"] == "طويل":
                            tr["realized_pl"] = float(tr.get("realized_pl", 0.0)) + (px - tr["entry"]) * rem
                        else:
                            tr["realized_pl"] = float(tr.get("realized_pl", 0.0)) + (tr["entry"] - px) * rem
                        tr["closed_qty"] = tr.get("closed_qty", 0) + rem
                        tr["status"] = "closed"
                        try:
                            trades_file.write_text(json.dumps(st.session_state["trades"], ensure_ascii=False), encoding="utf-8")
                        except Exception:
                            pass
                        st.rerun()
            with c4:
                if st.button("Delete", key=f"t_delete_{idx}"):
                    st.session_state["trades"].pop(idx)
                    try:
                        trades_file.write_text(json.dumps(st.session_state["trades"], ensure_ascii=False), encoding="utf-8")
                    except Exception:
                        pass
                    st.rerun()
        csv_bytes = df_tr.to_csv(index=False).encode("utf-8-sig")
        dl_c1, dl_c2 = st.columns(2)
        with dl_c1:
            st.download_button("تنزيل CSV", data=csv_bytes, file_name="virtual_trades.csv", mime="text/csv")
        with dl_c2:
            if st.button("مسح الصفقات"):
                st.session_state["trades"] = []
                try:
                    trades_file.write_text("[]", encoding="utf-8")
                except Exception:
                    pass
                st.rerun()
    else:
        st.info("لا توجد صفقات افتراضية")

risk_dollars = st.session_state.get("risk_dollars", 100)

# قراءة قيم المؤشرات والإعدادات من الحالة حتى عند عدم عرض الودجات
show_bbands = st.session_state.get("show_bbands", True)
show_rsi = st.session_state.get("show_rsi", True)
show_adx = st.session_state.get("show_adx", False)
show_atr = st.session_state.get("show_atr", False)
show_keltner = st.session_state.get("show_keltner", False)
show_ichimoku = st.session_state.get("show_ichimoku", False)
show_vwap = st.session_state.get("show_vwap", False)
show_obv = st.session_state.get("show_obv", False)
show_stoch = st.session_state.get("show_stoch", False)
auto_update = st.session_state.get("auto_update", True)
sma_short = st.session_state.get("sma_short", 20)
sma_long = st.session_state.get("sma_long", 50)
ema_win = st.session_state.get("ema_win", 20)
rsi_win = st.session_state.get("rsi_win", 14)
macd_fast = st.session_state.get("macd_fast", 12)
macd_slow = st.session_state.get("macd_slow", 26)
macd_signal = st.session_state.get("macd_signal", 9)
bb_win = st.session_state.get("bb_win", 20)
bb_std = st.session_state.get("bb_std", 2.0)
atr_win = st.session_state.get("atr_win", 14)
adx_win = st.session_state.get("adx_win", 14)
stoch_k = st.session_state.get("stoch_k", 14)
stoch_d = st.session_state.get("stoch_d", 3)
kel_ema = st.session_state.get("kel_ema", 20)
kel_atr = st.session_state.get("kel_atr", 10)
kel_mult = st.session_state.get("kel_mult", 2.0)
atr_entry_mult = st.session_state.get("atr_entry_mult", st.session_state.get("atr_entry_default", 0.1))
t1_r = st.session_state.get("t1_r", st.session_state.get("t1_r_default", 1.0))
t2_r = st.session_state.get("t2_r", st.session_state.get("t2_r_default", 2.0))

if (run or auto_update or force_run) and tickers_input:
    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
    st.session_state["last_symbols_count"] = len(tickers)
    st.session_state["last_update"] = datetime.now().strftime("%H:%M:%S")
    last_prices = {}
    for t in tickers:
        if t not in st.session_state["search_history"]:
            st.session_state["search_history"].insert(0, t)
            st.session_state["search_history"] = st.session_state["search_history"][:20]
            try:
                hist_file.write_text(json.dumps(st.session_state["search_history"], ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass
        per = period
        if interval == "1m" and per not in ["1d", "5d", "7d", "ytd"]:
            per = "7d"
        df = load_yahoo_cached(t, interval=interval, period=per)
        if df.empty:
            st.warning(f"لا توجد بيانات للرمز {t}")
            continue
        params = {
            "sma_short": sma_short,
            "sma_long": sma_long,
            "ema_win": ema_win,
            "rsi_win": rsi_win,
            "macd_fast": macd_fast,
            "macd_slow": macd_slow,
            "macd_signal": macd_signal,
            "bb_win": bb_win,
            "bb_std": bb_std,
            "atr_win": atr_win,
            "adx_win": adx_win,
            "stoch_k": stoch_k,
            "stoch_d": stoch_d,
            "kel_ema": kel_ema,
            "kel_atr": kel_atr,
            "kel_mult": kel_mult,
        }
        df = basic_signals(add_indicators(df, params=params))
        # Ensure date column exists for plotting
        if "date" not in df.columns:
            if "Date" in df.columns:
                df = df.rename(columns={"Date": "date"})
            else:
                # If no date column exists, reset index to get date from index
                df = df.reset_index()
                if "index" in df.columns:
                    df = df.rename(columns={"index": "date"})
                elif "date" not in df.columns and len(df) > 0:
                    # Create a simple date range if nothing else works
                    df["date"] = pd.date_range(end=pd.Timestamp.now(), periods=len(df), freq='D')
        
        # --- Dashboard Header ---
        last_price = float(df["close"].iloc[-1])
        prev_price = float(df["close"].iloc[-2]) if len(df) > 1 else last_price
        change_pct = ((last_price - prev_price) / prev_price) * 100
        change_color = "sp-metric-delta-pos" if change_pct >= 0 else "sp-metric-delta-neg"
        
        vol_curr = df["volume"].iloc[-1]
        vol_avg = df["volume"].rolling(20).mean().iloc[-1] if len(df) >= 20 else vol_curr
        vol_ratio = (vol_curr / vol_avg) if vol_avg > 0 else 1.0
        
        rsi_val = float(df.get(f"rsi_{rsi_win}", pd.Series([50])).iloc[-1])
        adx_val = float(df.get(f"adx_{adx_win}", pd.Series([0])).iloc[-1])
        
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;border-bottom:1px solid #30363D;padding-bottom:10px;">
            <div style="display:flex;align-items:baseline;gap:12px;">
                <h2 style="margin:0;color:#58a6ff;">{t}</h2>
                <span style="font-size:24px;font-weight:700;color:#C9D1D9;">{last_price:.2f}</span>
                <span class="{change_color}" style="font-size:16px;">{change_pct:+.2f}%</span>
            </div>
            <div style="font-size:12px;color:#8b949e;">{interval} | {period}</div>
        </div>
        <div class="sp-metric-container">
            <div class="sp-metric-card">
                <span class="sp-metric-label">RSI ({rsi_win})</span>
                <span class="sp-metric-value" style="color:{'#ef4444' if rsi_val >= 70 else '#22c55e' if rsi_val <= 30 else '#C9D1D9'}">{rsi_val:.1f}</span>
            </div>
            <div class="sp-metric-card">
                <span class="sp-metric-label">ADX ({adx_win})</span>
                <span class="sp-metric-value" style="color:{'#eab308' if adx_val >= 25 else '#8b949e'}">{adx_val:.1f}</span>
            </div>
            <div class="sp-metric-card">
                <span class="sp-metric-label">Volume Ratio</span>
                <span class="sp-metric-value" style="color:{'#22c55e' if vol_ratio > 1.5 else '#C9D1D9'}">{vol_ratio:.1f}x</span>
            </div>
            <div class="sp-metric-card">
                <span class="sp-metric-label">ATR ({atr_win})</span>
                <span class="sp-metric-value">{df[f'atr_{atr_win}'].iloc[-1]:.2f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        legend_items = []
        legend_items.append(("#3b82f6", f"SMA {sma_short}"))
        legend_items.append(("#8b5cf6", f"SMA {sma_long}"))
        if show_bbands:
            legend_items.append(("#ef4444", "Bollinger Upper"))
            legend_items.append(("#22c55e", "Bollinger Lower"))
        if show_keltner:
            legend_items.append(("#f97316", "Keltner Upper"))
            legend_items.append(("#14b8a6", "Keltner Lower"))
        if show_vwap:
            legend_items.append(("#60a5fa", "VWAP"))
        if show_ichimoku:
            legend_items.append(("#22c55e", "Span A"))
            legend_items.append(("#ef4444", "Span B"))
            legend_items.append(("#0ea5e9", "Tenkan"))
            legend_items.append(("#f59e0b", "Kijun"))
        if show_rsi:
            legend_items.append(("#a78bfa", "RSI"))
        if show_adx:
            legend_items.append(("#eab308", "ADX"))
            legend_items.append(("#22c55e", "+DI"))
            legend_items.append(("#ef4444", "-DI"))
        if show_atr:
            legend_items.append(("#94a3b8", "ATR"))
        if show_stoch:
            legend_items.append(("#06b6d4", "%K"))
            legend_items.append(("#10b981", "%D"))
        if show_obv:
            legend_items.append(("#ef4444", "OBV"))
        if legend_items:
            items_html = "".join([f"<div style='display:flex;align-items:center;gap:6px;padding:2px 6px;border:1px solid #1f2937;border-radius:6px;background:#0b1220;'><span style='display:inline-block;width:12px;height:12px;border-radius:3px;background:{c}'></span><span style='font-size:12px;color:#e2e8f0'>{lbl}</span></div>" for c, lbl in legend_items])
            legend_html = f"<div style='display:flex;flex-wrap:wrap;gap:8px;margin:6px 0'>{items_html}</div>"
            st.markdown(legend_html, unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df["date"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Candles",
            increasing_line_color="#26A69A",
            increasing_fillcolor="#26A69A",
            decreasing_line_color="#EF5350",
            decreasing_fillcolor="#EF5350"
        ))
        sma_short_col = f"sma_{sma_short}"
        sma_long_col = f"sma_{sma_long}"
        
        # Plot EMA 5 and 20 if enabled or by default
        if "ema_5" in df.columns:
            fig.add_trace(go.Scatter(x=df["date"], y=df["ema_5"], mode="lines", name="EMA 5", line=dict(color="#fbbf24", width=1)))
        if "ema_20" in df.columns:
            fig.add_trace(go.Scatter(x=df["date"], y=df["ema_20"], mode="lines", name="EMA 20", line=dict(color="#ec4899", width=1)))

        if sma_short_col in df and df[sma_short_col].notna().any():
            fig.add_trace(go.Scatter(x=df["date"], y=df[sma_short_col], mode="lines", name=f"SMA {sma_short}", line=dict(color="#3b82f6")))
        if sma_long_col in df and df[sma_long_col].notna().any():
            fig.add_trace(go.Scatter(x=df["date"], y=df[sma_long_col], mode="lines", name=f"SMA {sma_long}", line=dict(color="#8b5cf6")))
        if show_bbands and df["bb_upper"].notna().any():
            fig.add_trace(go.Scatter(x=df["date"], y=df["bb_upper"], mode="lines", name="Bollinger Upper", line=dict(color="#ef4444")))
            fig.add_trace(go.Scatter(x=df["date"], y=df["bb_lower"], mode="lines", name="Bollinger Lower", line=dict(color="#22c55e")))
        if show_keltner and df["kel_upper"].notna().any():
            fig.add_trace(go.Scatter(x=df["date"], y=df["kel_upper"], mode="lines", name="Keltner Upper", line=dict(color="#f97316")))
            fig.add_trace(go.Scatter(x=df["date"], y=df["kel_lower"], mode="lines", name="Keltner Lower", line=dict(color="#14b8a6")))
        if show_vwap and df["vwap"].notna().any():
            fig.add_trace(go.Scatter(x=df["date"], y=df["vwap"], mode="lines", name="VWAP", line=dict(color="#60a5fa")))
        if show_ichimoku and df["ichi_span_a"].notna().any() and df["ichi_span_b"].notna().any():
            fig.add_trace(go.Scatter(x=df["date"], y=df["ichi_span_a"], mode="lines", name="Span A", line=dict(color="#22c55e")))
            fig.add_trace(go.Scatter(x=df["date"], y=df["ichi_span_b"], mode="lines", name="Span B", fill="tonexty", line=dict(color="#ef4444")))
            fig.add_trace(go.Scatter(x=df["date"], y=df["ichi_conv"], mode="lines", name="Tenkan", line=dict(color="#0ea5e9")))
            fig.add_trace(go.Scatter(x=df["date"], y=df["ichi_base"], mode="lines", name="Kijun", line=dict(color="#f59e0b")))
        highs = df["high"].rolling(5, min_periods=5).max()
        lows = df["low"].rolling(5, min_periods=5).min()
        swing_highs = df[(df["high"] == highs) & df["high"].notna()][["date", "high"]].tail(3)
        swing_lows = df[(df["low"] == lows) & df["low"].notna()][["date", "low"]].tail(3)
        for _, row in swing_highs.iterrows():
            fig.add_hline(y=row["high"], line_color="orange", opacity=0.2)
        for _, row in swing_lows.iterrows():
            fig.add_hline(y=row["low"], line_color="teal", opacity=0.2)
        if len(df) >= 2:
            ph = df["high"].iloc[-2]
            pl = df["low"].iloc[-2]
            pc = df["close"].iloc[-2]
            pp = (ph + pl + pc) / 3.0
            r1_f = pp + 0.382 * (ph - pl)
            r2_f = pp + 0.618 * (ph - pl)
            s1_f = pp - 0.382 * (ph - pl)
            s2_f = pp - 0.618 * (ph - pl)
            fig.add_hline(y=r1_f, line_color="red", opacity=0.15)
            fig.add_hline(y=r2_f, line_color="red", opacity=0.15)
            fig.add_hline(y=s1_f, line_color="green", opacity=0.15)
            fig.add_hline(y=s2_f, line_color="green", opacity=0.15)
        atr_col = f"atr_{atr_win}" if f"atr_{atr_win}" in df.columns else None
        atr_val = float(df[atr_col].iloc[-1]) if atr_col else max(0.01, float((df["high"].iloc[-1] - df["low"].iloc[-1])))
        last_swing_high = float(swing_highs["high"].iloc[-1]) if not swing_highs.empty else float(df["high"].iloc[-1])
        last_swing_low = float(swing_lows["low"].iloc[-1]) if not swing_lows.empty else float(df["low"].iloc[-1])
        entry_long = last_swing_high + atr_entry_mult * atr_val
        stop_long = last_swing_low
        r_long = entry_long - stop_long if entry_long > stop_long else None
        tp1_long = entry_long + (t1_r * (r_long or 0))
        tp2_long = entry_long + (t2_r * (r_long or 0))
        entry_short = last_swing_low - atr_entry_mult * atr_val
        stop_short = last_swing_high
        r_short = stop_short - entry_short if stop_short > entry_short else None
        tp1_short = entry_short - (t1_r * (r_short or 0))
        tp2_short = entry_short - (t2_r * (r_short or 0))
        fig.add_hline(y=entry_long, line_color="#60a5fa", opacity=0.6)
        fig.add_hline(y=stop_long, line_color="#ef4444", opacity=0.6)
        if r_long:
            fig.add_hline(y=tp1_long, line_color="#22c55e", opacity=0.4)
            fig.add_hline(y=tp2_long, line_color="#22c55e", opacity=0.4)
        fig.add_hline(y=entry_short, line_color="#60a5fa", opacity=0.6)
        fig.add_hline(y=stop_short, line_color="#ef4444", opacity=0.6)
        if r_short:
            fig.add_hline(y=tp1_short, line_color="#22c55e", opacity=0.4)
            fig.add_hline(y=tp2_short, line_color="#22c55e", opacity=0.4)
        fig.update_layout(
            xaxis_rangeslider_visible=False,
            height=620,
            margin=dict(l=10, r=10, t=20, b=10),
            paper_bgcolor="#161B22",
            plot_bgcolor="#0E1117",
            font=dict(color="#C9D1D9")
        )
        st.plotly_chart(fig, use_container_width=True)
        last_price = float(df["close"].iloc[-1])
        last_prices[t] = last_price
        supports, resistances = [], []
        supports += list(swing_lows["low"].values) if not swing_lows.empty else []
        resistances += list(swing_highs["high"].values) if not swing_highs.empty else []
        if len(df) >= 2:
            ph2 = df["high"].iloc[-2]
            pl2 = df["low"].iloc[-2]
            pc2 = df["close"].iloc[-2]
            pp2 = (ph2 + pl2 + pc2) / 3.0
            supports += [pp2 - 0.382 * (ph2 - pl2), pp2 - 0.618 * (ph2 - pl2)]
            resistances += [pp2 + 0.382 * (ph2 - pl2), pp2 + 0.618 * (ph2 - pl2)]
        supports_below = [s for s in supports if s <= last_price]
        resistances_above = [r for r in resistances if r >= last_price]
        nearest_support = max(supports_below) if supports_below else None
        nearest_resistance = min(resistances_above) if resistances_above else None
        trend = "عرضي"
        last = df.iloc[-1]
        if sma_short_col in df and sma_long_col in df:
            if last[sma_short_col] > last[sma_long_col] and last.get(f"adx_{adx_win}", 0) >= 20:
                trend = "اتجاه صاعد"
            elif last[sma_short_col] < last[sma_long_col] and last.get(f"adx_{adx_win}", 0) >= 20:
                trend = "اتجاه هابط"
        txt = ""
        if nearest_support is not None:
            txt += f"دعم: {nearest_support:.2f}  "
        if nearest_resistance is not None:
            txt += f"مقاومة: {nearest_resistance:.2f}"
            
        # --- Signal Logic ---
        reco_bg = "#22c55e"
        reco_txt = "مناسب للشراء"
        cond_up = trend == "اتجاه صاعد"
        price_above_vwap = "vwap" in df.columns and pd.notnull(df["vwap"].iloc[-1]) and last_price > float(df["vwap"].iloc[-1])
        rsi_val = float(df.get(f"rsi_{rsi_win}", pd.Series([50])).iloc[-1])
        adx_val = float(df.get(f"adx_{adx_win}", pd.Series([0])).iloc[-1])
        
        # EMA Crossover Logic (5/20)
        ema5_cross_up = False
        ema5_cross_down = False
        ema_signal_txt = ""
        
        if "ema_5" in df.columns and "ema_20" in df.columns:
            curr_ema5 = df["ema_5"].iloc[-1]
            curr_ema20 = df["ema_20"].iloc[-1]
            prev_ema5 = df["ema_5"].iloc[-2]
            prev_ema20 = df["ema_20"].iloc[-2]
            
            if curr_ema5 > curr_ema20 and prev_ema5 <= prev_ema20:
                ema5_cross_up = True
                ema_signal_txt = "تقاطع إيجابي (Golden Cross)"
            elif curr_ema5 < curr_ema20 and prev_ema5 >= prev_ema20:
                ema5_cross_down = True
                ema_signal_txt = "تقاطع سلبي (Death Cross)"
        
        good = (cond_up and price_above_vwap and 40 <= rsi_val <= 70 and adx_val >= 20) or ema5_cross_up
        neutral = (price_above_vwap and rsi_val <= 75) or (cond_up and adx_val >= 15)
        
        if ema5_cross_up:
             st.success(f"🔥 تنبيه استراتيجي: تقاطع إيجابي لمتوسطات EMA 5/20 على فاصل {interval} - إشارة دخول محتملة!")
        if ema5_cross_down:
             st.error(f"⚠️ تنبيه استراتيجي: تقاطع سلبي لمتوسطات EMA 5/20 على فاصل {interval} - إشارة خروج محتملة!")

        if good:
            reco_bg = "#238636" # Github Green
            reco_txt = "شراء قوي"
            reco_icon = "🚀"
        elif neutral:
            reco_bg = "#d29922" # Github Yellow
            reco_txt = "محايد / انتظار"
            reco_icon = "✋"
        else:
            reco_bg = "#da3633" # Github Red
            reco_txt = "سلبي / بيع"
            reco_icon = "🔻"

        # --- Technical Summary Card ---
        st.markdown(f"""
        <div class="sp-signal-box">
            <div style="display:flex;align-items:center;gap:15px;">
                <div style="text-align:center;">
                    <div style="font-size:32px;">{reco_icon}</div>
                </div>
                <div>
                    <div style="font-size:14px;color:#8b949e;">التوصية الفنية</div>
                    <div style="font-size:20px;font-weight:700;color:{reco_bg}">{reco_txt}</div>
                </div>
            </div>
            <div style="text-align:left;direction:ltr;">
                <div style="font-size:12px;color:#8b949e;">Trend: <span style="color:#C9D1D9">{trend}</span></div>
                <div style="font-size:12px;color:#8b949e;">Supp/Res: <span style="color:#C9D1D9">{txt or 'N/A'}</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- Risk Management Cards ---
        c1, c2 = st.columns(2)
        with c1:
            shares_long = int(risk_dollars / r_long) if r_long and r_long > 0 else 0
            rr_long = (tp1_long - entry_long) / (entry_long - stop_long) if r_long else 0
            st.markdown(f"""
            <div class="sp-card">
                <div style="display:flex;justify-content:space-between;margin-bottom:8px;border-bottom:1px solid #30363D;padding-bottom:5px;">
                    <span style="color:#22c55e;font-weight:700;">خطة شراء (Long)</span>
                    <span style="font-size:12px;color:#8b949e;">R/R: {rr_long:.1f}</span>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px;"><span>دخول:</span><span style="color:#C9D1D9">{entry_long:.2f}</span></div>
                <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px;"><span>وقف:</span><span style="color:#ef4444">{stop_long:.2f}</span></div>
                <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px;"><span>هدف 1:</span><span style="color:#22c55e">{tp1_long:.2f}</span></div>
                <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px;"><span>هدف 2:</span><span style="color:#22c55e">{tp2_long:.2f}</span></div>
                <div style="margin-top:8px;padding-top:8px;border-top:1px dashed #30363D;text-align:center;">
                    <span style="font-size:12px;color:#8b949e;">الكمية المقترحة</span><br>
                    <span style="font-size:16px;font-weight:700;color:#C9D1D9">{shares_long} سهم</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("تنفيذ شراء افتراضي", key=f"virt_buy_{t}", use_container_width=True) and r_long and r_long > 0:
                qty = int(risk_dollars / r_long)
                if qty > 0:
                    st.session_state["trades"].append({
                        "symbol": t, "side": "طويل", "entry": round(entry_long, 4), "stop": round(stop_long, 4),
                        "tp1": round(tp1_long, 4), "tp2": round(tp2_long, 4), "qty": qty, "time": str(df["date"].iloc[-1]),
                        "closed_qty": 0, "realized_pl": 0.0, "status": "open"
                    })
                    try:
                        trades_file.write_text(json.dumps(st.session_state["trades"], ensure_ascii=False), encoding="utf-8")
                    except Exception: pass
                    st.rerun()

        with c2:
            shares_short = int(risk_dollars / r_short) if r_short and r_short > 0 else 0
            rr_short = (entry_short - tp1_short) / (stop_short - entry_short) if r_short else 0
            st.markdown(f"""
            <div class="sp-card">
                <div style="display:flex;justify-content:space-between;margin-bottom:8px;border-bottom:1px solid #30363D;padding-bottom:5px;">
                    <span style="color:#ef4444;font-weight:700;">خطة بيع (Short)</span>
                    <span style="font-size:12px;color:#8b949e;">R/R: {rr_short:.1f}</span>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px;"><span>دخول:</span><span style="color:#C9D1D9">{entry_short:.2f}</span></div>
                <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px;"><span>وقف:</span><span style="color:#ef4444">{stop_short:.2f}</span></div>
                <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px;"><span>هدف 1:</span><span style="color:#22c55e">{tp1_short:.2f}</span></div>
                <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px;"><span>هدف 2:</span><span style="color:#22c55e">{tp2_short:.2f}</span></div>
                <div style="margin-top:8px;padding-top:8px;border-top:1px dashed #30363D;text-align:center;">
                    <span style="font-size:12px;color:#8b949e;">الكمية المقترحة</span><br>
                    <span style="font-size:16px;font-weight:700;color:#C9D1D9">{shares_short} سهم</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("تنفيذ بيع افتراضي", key=f"virt_sell_{t}", use_container_width=True) and r_short and r_short > 0:
                qty = int(risk_dollars / r_short)
                if qty > 0:
                    st.session_state["trades"].append({
                        "symbol": t, "side": "قصير", "entry": round(entry_short, 4), "stop": round(stop_short, 4),
                        "tp1": round(tp1_short, 4), "tp2": round(tp2_short, 4), "qty": qty, "time": str(df["date"].iloc[-1]),
                        "closed_qty": 0, "realized_pl": 0.0, "status": "open"
                    })
                    try:
                        trades_file.write_text(json.dumps(st.session_state["trades"], ensure_ascii=False), encoding="utf-8")
                    except Exception: pass
                    st.rerun()

        # --- Indicator Charts (RSI, ADX, etc.) ---
        if show_rsi:
            rsi_fig = go.Figure()
            rsi_col = f"rsi_{rsi_win}"
            rsi_fig.add_trace(go.Scatter(x=df["date"], y=df[rsi_col], mode="lines", name=f"RSI {rsi_win}", line=dict(color="#a78bfa")))
            rsi_fig.add_hline(y=70, line_color="red")
            rsi_fig.add_hline(y=30, line_color="green")
            rsi_fig.update_layout(height=250, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="#0E1117", plot_bgcolor="#0E1117", font=dict(color="#C9D1D9"))
            st.plotly_chart(rsi_fig, use_container_width=True)
        if show_adx:
            adx_fig = go.Figure()
            adx_fig.add_trace(go.Scatter(x=df["date"], y=df[f"adx_{adx_win}"], mode="lines", name=f"ADX {adx_win}", line=dict(color="#eab308")))
            adx_fig.add_trace(go.Scatter(x=df["date"], y=df["plus_di"], mode="lines", name="+DI", line=dict(color="#22c55e")))
            adx_fig.add_trace(go.Scatter(x=df["date"], y=df["minus_di"], mode="lines", name="-DI", line=dict(color="#ef4444")))
            adx_fig.update_layout(height=250, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="#0E1117", plot_bgcolor="#0E1117", font=dict(color="#C9D1D9"))
            st.plotly_chart(adx_fig, use_container_width=True)
        if show_atr:
            atr_fig = go.Figure()
            atr_fig.add_trace(go.Scatter(x=df["date"], y=df[f"atr_{atr_win}"], mode="lines", name=f"ATR {atr_win}", line=dict(color="#94a3b8")))
            atr_fig.update_layout(height=250, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="#0E1117", plot_bgcolor="#0E1117", font=dict(color="#C9D1D9"))
            st.plotly_chart(atr_fig, use_container_width=True)
        if show_stoch:
            last_k = df["stoch_k"].iloc[-1] if "stoch_k" in df.columns and pd.notnull(df["stoch_k"].iloc[-1]) else None
            last_d = df["stoch_d"].iloc[-1] if "stoch_d" in df.columns and pd.notnull(df["stoch_d"].iloc[-1]) else None
            label = f"STOCH ({stoch_k},1,{stoch_d}) — K: "
            if last_k is not None:
                label += f"<span style='color:#06b6d4'>{last_k:.2f}</span>  "
            else:
                label += "--  "
            label += "D: "
            if last_d is not None:
                label += f"<span style='color:#10b981'>{last_d:.2f}</span>"
            else:
                label += "--"
            st.markdown(label, unsafe_allow_html=True)
            stoch_fig = go.Figure()
            stoch_fig.add_trace(go.Scatter(x=df["date"], y=df["stoch_k"], mode="lines", name="%K", line=dict(color="#06b6d4")))
            stoch_fig.add_trace(go.Scatter(x=df["date"], y=df["stoch_d"], mode="lines", name="%D", line=dict(color="#10b981")))
            stoch_fig.add_hline(y=80, line_color="red")
            stoch_fig.add_hline(y=20, line_color="green")
            stoch_fig.update_layout(height=250, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="#0E1117", plot_bgcolor="#0E1117", font=dict(color="#C9D1D9"))
            st.plotly_chart(stoch_fig, use_container_width=True)
        if show_obv:
            obv_fig = go.Figure()
            obv_fig.add_trace(go.Scatter(x=df["date"], y=df["obv"], mode="lines", name="OBV", line=dict(color="#ef4444")))
            obv_fig.update_layout(height=250, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="#0E1117", plot_bgcolor="#0E1117", font=dict(color="#C9D1D9"))
            st.plotly_chart(obv_fig, use_container_width=True)

# --- Welcome Screen (Empty State) ---
if section == "المؤشرات" and not tickers_input:
    st.markdown("""<div style="text-align: center; padding: 60px 20px; max-width: 800px; margin: 0 auto;">
<h1 style="color: #58a6ff; margin-bottom: 15px; font-size: 2.5rem; font-weight: 700;">مرحبًا بك في StockPro</h1>
<p style="font-size: 20px; color: #8b949e; margin-bottom: 50px;">منصتك الاحترافية لتحليل الأسواق المالية بالذكاء الاصطناعي</p>
<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 25px; margin: 40px 0;">
<div style="background: linear-gradient(135deg, #1e2329 0%, #161b22 100%); padding: 30px; border-radius: 16px; border: 1px solid #30363D; box-shadow: 0 8px 16px rgba(0,0,0,0.4); transition: transform 0.3s ease, box-shadow 0.3s ease;" onmouseover="this.style.transform='translateY(-5px)'; this.style.boxShadow='0 12px 24px rgba(0,0,0,0.5)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 8px 16px rgba(0,0,0,0.4)';">
<div style="width: 60px; height: 4px; background: linear-gradient(90deg, #3b82f6, #60a5fa); border-radius: 2px; margin-bottom: 20px;"></div>
<h3 style="color: #e6edf3; font-size: 20px; margin: 0 0 15px 0; font-weight: 600;">تحليل فني متقدم</h3>
<p style="font-size: 14px; color: #8b949e; line-height: 1.7; margin: 0;">رسوم بيانية تفاعلية مع مؤشرات RSI, MACD, Bollinger Bands والمزيد من الأدوات الاحترافية.</p>
</div>
<div style="background: linear-gradient(135deg, #1e2329 0%, #161b22 100%); padding: 30px; border-radius: 16px; border: 1px solid #30363D; box-shadow: 0 8px 16px rgba(0,0,0,0.4); transition: transform 0.3s ease, box-shadow 0.3s ease;" onmouseover="this.style.transform='translateY(-5px)'; this.style.boxShadow='0 12px 24px rgba(0,0,0,0.5)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 8px 16px rgba(0,0,0,0.4)';">
<div style="width: 60px; height: 4px; background: linear-gradient(90deg, #10b981, #34d399); border-radius: 2px; margin-bottom: 20px;"></div>
<h3 style="color: #e6edf3; font-size: 20px; margin: 0 0 15px 0; font-weight: 600;">ماسح ضوئي ذكي</h3>
<p style="font-size: 14px; color: #8b949e; line-height: 1.7; margin: 0;">اكتشف الفرص الاستثمارية لحظياً بناءً على الحجم، السعر، والتغيير مع خوارزميات متقدمة.</p>
</div>
<div style="background: linear-gradient(135deg, #1e2329 0%, #161b22 100%); padding: 30px; border-radius: 16px; border: 1px solid #30363D; box-shadow: 0 8px 16px rgba(0,0,0,0.4); transition: transform 0.3s ease, box-shadow 0.3s ease;" onmouseover="this.style.transform='translateY(-5px)'; this.style.boxShadow='0 12px 24px rgba(0,0,0,0.5)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 8px 16px rgba(0,0,0,0.4)';">
<div style="width: 60px; height: 4px; background: linear-gradient(90deg, #f59e0b, #fbbf24); border-radius: 2px; margin-bottom: 20px;"></div>
<h3 style="color: #e6edf3; font-size: 20px; margin: 0 0 15px 0; font-weight: 600;">إدارة مخاطر</h3>
<p style="font-size: 14px; color: #8b949e; line-height: 1.7; margin: 0;">حاسبة مخاطر مدمجة ومحفظة افتراضية لتتبع صفقاتك بأمان وفعالية.</p>
</div>
</div>
<div style="margin-top: 60px; padding: 25px; background: linear-gradient(135deg, #161b22 0%, #0d1117 100%); border-radius: 12px; border: 1px solid #30363D; display: inline-block; max-width: 600px;">
<p style="color: #8b949e; margin: 0; font-size: 16px;">💡 ابدأ رحلتك الاستثمارية: اكتب رمز السهم في الحقل أعلاه (مثال: AAPL, TSLA) أو استكشف الماسح الضوئي للعثور على الفرص.</p>
</div>
</div>""", unsafe_allow_html=True)

# --- Footer ---
st.markdown("""
<div style="text-align: center; margin-top: 50px; padding-top: 20px; border-top: 1px solid #30363D; color: #8b949e; font-size: 12px;">
    StockPro Trading Platform © 2024 | Developed for Traders
</div>
""", unsafe_allow_html=True)
