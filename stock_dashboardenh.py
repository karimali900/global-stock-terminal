import os
import json
import time
import smtplib
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Streamlit & Viz
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Email Utilities
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==============================================================================
# 1. CORE CONFIGURATION & CONSTANTS
# ==============================================================================
st.set_page_config(
    page_title="Global Stock Intelligence Terminal",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📊"
)

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = "90.karim@gmail.com"
# EMAIL_PASSWORD = os.getenv("EMAIL_PASS") # Best practice: use env var

TRANSLATIONS = {
    "EN": {
        "title": "📊 Global Stock Intelligence Terminal",
        "universe": "Active Asset Universe",
        "time_horizon": "📅 Time Horizon",
        "start_date": "Start Date",
        "end_date": "End Date",
        "recipients": "📬 Alert Configuration Group",
        "save_btn": "💾 Save Configuration Defaults",
        "m_active": "Assets Active",
        "m_telemetry": "Telemetry Points",
        "m_ai": "Backend AI Engine",
        "m_chronos": "System Stamp",
        "tab_perf": "📈 Market Performance",
        "tab_tech": "🔬 Technical Terminal",
        "tab_pred": "🔮 AI Forecasting",
        "tab_backtest": "💼 Portfolio Backtester",
        "tab_logs": "📡 Automation Hub",
        "tab_live": "⚡ Live Stream",
    },
    "AR": {
        "title": "📊 منصة استخبارات الأسهم العالمية",
        "universe": "نطاق الأصول النشطة",
        "time_horizon": "📅 النطاق الزمني",
        "start_date": "تاريخ البدء",
        "end_date": "تاريخ الانتهاء",
        "recipients": "📬 مجموعة تكوين التنبيهات",
        "save_btn": "💾 حفظ الإعدادات الافتراضية",
        "m_active": "الأصول النشطة",
        "m_telemetry": "نقاط البيانات",
        "m_ai": "محرك الذكاء الاصطناعي",
        "m_chronos": "طابع النظام",
        "tab_perf": "📈 أداء السوق",
        "tab_tech": "🔬 التحليل الفني",
        "tab_pred": "🔮 التنبؤ الذكي",
        "tab_backtest": "💼 مختبر المحفظة",
        "tab_logs": "📡 سجلات النظام",
        "tab_live": "⚡ البث الحي",
    }
}

GLOBAL_AND_MENA_TICKERS = sorted([
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "2222.SR", "1120.SR", "EMAAR.DU", "DEWA.DU", "COMI.CA"
])
SAFE_DEFAULT_TICKERS = ["AAPL", "2222.SR", "EMAAR.DU"]

# ==============================================================================
# 2. UI SIDEBAR & STATE
# ==============================================================================
st.sidebar.markdown("### 🌐 Language / اللغة")
lang_choice = st.sidebar.radio("Language Mode", ["English", "العربية"], label_visibility="collapsed")
active_lang_code = "EN" if lang_choice == "English" else "AR"
L = TRANSLATIONS[active_lang_code]

if active_lang_code == "AR":
    st.markdown("""
        <style>
        div.stApp { direction: rtl; text-align: right; }
        [data-testid="stSidebar"] { text-align: right; }
        .stTabs [data-baseweb="tab-list"] { direction: rtl; }
        </style>
    """, unsafe_allow_html=True)

st.sidebar.header(L["universe"])
selected_tickers = st.sidebar.multiselect("Select Assets", GLOBAL_AND_MENA_TICKERS, default=SAFE_DEFAULT_TICKERS)

st.sidebar.subheader(L["time_horizon"])
c1, c2 = st.sidebar.columns(2)
start_date = c1.date_input(L["start_date"], value=datetime.today() - timedelta(days=90))
end_date = c2.date_input(L["end_date"], value=datetime.today())

# ==============================================================================
# 3. DATA LAYER (Robust Fetcher)
# ==============================================================================
@st.cache_data(ttl=60, show_spinner=False)
def fetch_data_from_backend(tickers, start, end):
    """
    Attempts to fetch from FastAPI. If offline, generates realistic mock data
    to keep the UI functional for demos.
    """
    payload = {
        "tickers": tickers,
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d")
    }

    # 1. Try Real Backend
    try:
        response = requests.post(f"{API_URL}/api/v1/market-data", json=payload, timeout=2)
        if response.status_code == 200:
            data = response.json().get("data", [])
            df = pd.DataFrame(data)
            if not df.empty:
                df['Datetime'] = pd.to_datetime(df['Datetime'])
                return df, True # True = Backend Online
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        pass # Fallthrough to mock

    # 2. Fallback: Generate Realistic Mock Data
    mock_rows = []
    date_range = pd.date_range(start=start, end=end, freq='D')
    for t in tickers:
        base_price = 150 if "SR" not in t else 40 # Different base for Saudi/Global
        noise = np.random.normal(0, 2, len(date_range))
        trend = np.linspace(0, 10, len(date_range))
        prices = base_price + trend + noise

        for dt, price in zip(date_range, prices):
            mock_rows.append({
                "Ticker": t,
                "Datetime": dt,
                "Open": price - 1,
                "High": price + 2,
                "Low": price - 2,
                "Close": price,
                "Volume": int(np.random.randint(1000, 50000))
            })

    df_mock = pd.DataFrame(mock_rows)
    return df_mock, False # False = Backend Offline (Simulation Mode)

# Execute Data Load
st.title(L["title"])
with st.spinner("📡 Synchronizing with Market Stream..."):
    df_live, backend_online = fetch_data_from_backend(selected_tickers, start_date, end_date)

# Status Alert
if not backend_online:
    st.warning("⚠️ Backend API Unreachable. Running in **Simulation Mode** with mock data.")

# Metric Strip
m1, m2, m3, m4 = st.columns(4)
m1.metric(L["m_active"], len(selected_tickers))
m2.metric(L["m_telemetry"], f"{len(df_live):,}")
m3.metric(L["m_ai"], "CONNECTED 🟢" if backend_online else "SIMULATION 🟠")
m4.metric(L["m_chronos"], datetime.now().strftime('%H:%M:%S'))

# ==============================================================================
# 4. MAIN TABS
# ==============================================================================
tab_dashboard, tab_tech, tab_pred, tab_backtest, tab_logs, tab_live = st.tabs([
    L["tab_perf"], L["tab_tech"], L["tab_pred"], L["tab_backtest"], L["tab_logs"], L["tab_live"]
])

# --- TAB 1: MARKET PERFORMANCE ---
with tab_dashboard:
    if not df_live.empty:
        latest_rows = []
        for ticker in df_live['Ticker'].unique():
            sub = df_live[df_live['Ticker'] == ticker].sort_values('Datetime')
            if len(sub) >= 2:
                last = sub.iloc[-1]
                first = sub.iloc[0]
                pct_change = ((last['Close'] - first['Close']) / first['Close']) * 100
                trend_icon = "🟢 🔺 Up" if pct_change > 0 else "🔴 🔻 Down"
                latest_rows.append({
                    "Asset": ticker,
                    "Price": last['Close'],
                    "Change %": pct_change,
                    "Trend": trend_icon,
                    "Volume": last['Volume']
                })

        summ_df = pd.DataFrame(latest_rows)

        def color_trend(val):
            return f"color: {'#00ffcc' if '🔺' in str(val) else '#ff4d4d'}; font-weight: bold;"

        if not summ_df.empty:
            st.dataframe(
                summ_df.style.map(color_trend, subset=['Trend'])
                .format({'Change %': '{:+.2f}%', 'Price': '${:,.2f}', 'Volume': '{:,}'}),
                use_container_width=True
            )

# --- TAB 2: TECHNICAL TERMINAL ---
with tab_tech:
    tech_ticker = st.selectbox("Analyze Asset", selected_tickers, key="tech_sel")

    if not df_live.empty:
        t_data = df_live[df_live['Ticker'] == tech_ticker]

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            vertical_spacing=0.03, row_heights=[0.7, 0.3])

        # Candlestick
        fig.add_trace(go.Candlestick(
            x=t_data['Datetime'], open=t_data['Open'], high=t_data['High'],
            low=t_data['Low'], close=t_data['Close'], name="OHLC"
        ), row=1, col=1)

        # Volume
        fig.add_trace(go.Bar(
            x=t_data['Datetime'], y=t_data['Volume'], name="Volume", marker_color='teal'
        ), row=2, col=1)

        fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

# --- TAB 3: AI FORECASTING ---
with tab_pred:
    col_pred_l, col_pred_r = st.columns([2, 1])
    predict_ticker = col_pred_l.selectbox("Target Asset for AI", selected_tickers)

    with col_pred_l:
        if st.button("🔮 Run Prophet AI Forecast", type="primary"):
            if not backend_online:
                st.error("🚫 AI Forecasting requires active Backend connection.")
            else:
                with st.spinner("Asking backend to run Prophet..."):
                    try:
                        # Real API Call
                        res = requests.post(f"{API_URL}/api/v1/forecast",
                                            json={"ticker": predict_ticker, "days": 30})
                        if res.status_code == 200:
                            data = res.json()
                            hist = pd.DataFrame(data["historical"])
                            fcst = pd.DataFrame(data["forecast"])

                            fig_f = go.Figure()
                            fig_f.add_trace(go.Scatter(x=hist['ds'], y=hist['y'], name='History'))
                            fig_f.add_trace(go.Scatter(x=fcst['ds'], y=fcst['yhat'], name='AI Forecast',
                                                      line=dict(color='#00ffcc', dash='dot')))
                            st.plotly_chart(fig_f, use_container_width=True)
                    except Exception as e:
                        st.error(f"Model Error: {e}")

    with col_pred_r:
        st.markdown("#### 🧠 FinBERT Sentiment")
        if st.button("Analyze News Sentiment"):
            if not backend_online:
                st.info("💡 Simulation: Sentiment is BULLISH (0.85)")
            else:
                # Placeholder for real NLP call
                st.success("Fetching latest news...")

# --- TAB 4 & 5: BACKTEST & LOGS (Placeholders) ---
with tab_backtest:
    st.info("💼 Portfolio Backtesting Engine is ready for strategy injection.")

with tab_logs:
    st.text_area("System Logs", value=f"[INFO] System initialized at {datetime.now()}\n[DATA] Fetched {len(df_live)} rows.\n[MODE] {'Online' if backend_online else 'Offline Simulation'}")

# --- TAB 6: WEBSOCKET LIVE STREAM ---
with tab_live:
    st.subheader("⚡ High-Frequency Live Ticker (WebSocket)")
    live_ticker = st.selectbox("Stream Asset", selected_tickers, key="live_stream_box")

    if st.button("▶️ Connect Pipe", type="primary"):
        stream_placeholder = st.empty()

        if not backend_online:
            # Simulation Loop for Demo
            for i in range(10):
                price = 150.0 + np.random.uniform(-1, 1)
                stream_placeholder.markdown(f"""
                    <div style='padding: 20px; background-color: #121212; border-radius: 10px; text-align: center; border: 1px solid #333;'>
                        <h2>{live_ticker} (SIMULATION)</h2>
                        <h1 style='color: #00ffcc'>${price:.2f}</h1>
                    </div>
                """, unsafe_allow_html=True)
                time.sleep(0.5)
            st.caption("Simulation ended.")

        else:
            # Real WebSocket Logic
            try:
                from websocket import create_connection
                ws_url = API_URL.replace("http", "ws") + f"/ws/stream/{live_ticker}"
                ws = create_connection(ws_url)

                st.toast(f"Connected to {live_ticker}", icon="🟢")

                for _ in range(50):
                    result = ws.recv()
                    data = json.loads(result)
                    color = "#00ffcc" if data.get('trend') == 'up' else "#ff4d4d"

                    stream_placeholder.markdown(f"""
                    <div style='padding: 20px; background-color: #121212; border-radius: 10px; text-align: center;'>
                        <h2>{data['ticker']}</h2>
                        <h1 style='color: {color};'>${data['price']:.2f}</h1>
                    </div>
                    """, unsafe_allow_html=True)
                ws.close()
            except ImportError:
                st.error("Missing library. Run `pip install websocket-client`")
            except Exception as e:
                st.error(f"Connection Failed: {e}")
