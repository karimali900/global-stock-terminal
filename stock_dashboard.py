# # # # stock_dashboard.py - Enterprise Frontend UI
# # UPGRADE: Connected to FastAPI Backend (Microservices Architecture)

import os
import json
import sqlite3
import smtplib
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import websocket
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==============================================================================
# API CONNECTION & EMAIL CONFIG
# ==============================================================================
API_URL ="http://127.0.0.1:8000" # Talking to our new backend brain
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = "90.karim@gmail.com"
EMAIL_PASSWORD = "your-16-character-app-password"

# ==============================================================================
# TRANSLATIONS & CONSTANTS
# ==============================================================================
TRANSLATIONS = {
    "EN": {
        "title": "📊 Global Stock Intelligence Terminal",
        "universe": "Active Asset Universe (Global & MENA)",
        "time_horizon": "📅 Time Horizon",
        "start_date": "Start Date",
        "end_date": "End Date",
        "recipients": "📬 Alert Configuration Group",
        "save_btn": "💾 Save Configuration Defaults",
        "m_active": "Assets Active",
        "m_telemetry": "Telemetry Points Processed",
        "m_ai": "Backend AI Engine",
        "m_chronos": "Chronos System Stamp",
        "tab_perf": "📈 Market Performance Grid",
        "tab_tech": "🔬 Technical Terminal",
        "tab_pred": "🔮 AI Forecasting",
        "tab_backtest": "💼 Portfolio Backtester",
        "tab_logs": "📡 Automation Hub",
    },
    "AR": {
        "title": "📊 منصة استخبارات الأسهم العالمية",
        "universe": "نطاق الأصول النشطة (العالمية والشرق الأوسط)",
        "time_horizon": "📅 النطاق الزمني",
        "start_date": "تاريخ البدء",
        "end_date": "تاريخ الانتهاء",
        "recipients": "📬 مجموعة تكوين التنبيهات",
        "save_btn": "💾 حفظ الإعدادات الافتراضية",
        "m_active": "الأصول النشطة",
        "m_telemetry": "نقاط البيانات المعالجة",
        "m_ai": "محرك الذكاء الاصطناعي الخلفي",
        "m_chronos": "طابع نظام كرونوس الزمني",
        "tab_perf": "📈 شبكة أداء السوق",
        "tab_tech": "🔬 التحليل الفني المتقدم",
        "tab_pred": "🔮 التنبؤ بالذكاء الاصطناعي",
        "tab_backtest": "💼 مختبر أداء المحفظة الأصول",
        "tab_logs": "📡 مركز الأتمتة والنظام",
    }
}

GLOBAL_AND_MENA_TICKERS = sorted([
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "V", "JNJ",
    "2222.SR", "1120.SR", "EMAAR.DU", "DEWA.DU", "COMI.CA"
])
SAFE_DEFAULT_TICKERS = ["AAPL", "TSLA", "MSFT", "2222.SR", "EMAAR.DU", "COMI.CA"]

# ==============================================================================
# UI STATE & SIDEBAR
# ==============================================================================
st.set_page_config(page_title="Global Stock Intelligence Terminal", layout="wide")

st.sidebar.markdown("### 🌐 Language / اللغة")
lang_choice = st.sidebar.radio("Language Mode", ["English", "العربية"], label_visibility="collapsed")
active_lang_code = "EN" if lang_choice == "English" else "AR"
L = TRANSLATIONS[active_lang_code]

if active_lang_code == "AR": st.markdown("<style> div.stApp { direction: rtl; text-align: right; } </style>", unsafe_allow_html=True)

st.sidebar.header(L["universe"])
selected_tickers = st.sidebar.multiselect("Select Assets", GLOBAL_AND_MENA_TICKERS, default=SAFE_DEFAULT_TICKERS, label_visibility="collapsed")

st.sidebar.subheader(L["time_horizon"])
col_sd, col_ed = st.sidebar.columns(2)
with col_sd: start_date = st.date_input(L["start_date"], value=datetime.today() - timedelta(days=90))
with col_ed: end_date = st.date_input(L["end_date"], value=datetime.today())

st.sidebar.subheader(L["recipients"])
email_input_raw = st.sidebar.text_area("Emails", value="90.karim@gmail.com", label_visibility="collapsed")

# ==============================================================================
# DATA FETCHING FROM FASTAPI BACKEND
# ==============================================================================
st.title(L["title"])

@st.cache_data(ttl=60)
def fetch_data_from_backend(tickers, start, end):
    try:
        payload = {"tickers": tickers, "start_date": start.strftime("%Y-%m-%d"), "end_date": end.strftime("%Y-%m-%d")}
        response = requests.post(f"{API_URL}/api/v1/market-data", json=payload)

        if response.status_code == 200:
            df = pd.DataFrame(response.json()["data"])
            df['Datetime'] = pd.to_datetime(df['Datetime'])
            return df, True
        else:
            # The backend connected, but something crashed inside FastAPI
            st.error(f"Backend Connected, but returned Error {response.status_code}: {response.text}")
            return pd.DataFrame(), False

    except requests.exceptions.ConnectionError:
        # The backend genuinely cannot be reached
        st.error(f"Connection Refused. Ensure backend is running at {API_URL}")
        return pd.DataFrame(), False
    except Exception as e:
        # Some other Python error occurred
        st.error(f"Frontend Error: {str(e)}")
        return pd.DataFrame(), False
with st.spinner("Fetching data from API Backend..."):
    df_live, backend_online = fetch_data_from_backend(selected_tickers, start_date, end_date)

if not backend_online or df_live.empty:
    st.error("⚠️ Cannot connect to Backend API. Make sure `python backend_api.py` is running in another terminal window.")
    st.stop()

# Metric Status Block
m1, m2, m3, m4 = st.columns(4)
m1.metric(L["m_active"], len(selected_tickers))
m2.metric(L["m_telemetry"], len(df_live))
m3.metric(L["m_ai"], "CONNECTED 🟢" if backend_online else "OFFLINE 🔴")
m4.metric(L["m_chronos"], datetime.now().strftime('%H:%M:%S'))

tab_dashboard, tab_tech, tab_pred, tab_backtest, tab_logs = st.tabs([
    L["tab_perf"], L["tab_tech"], L["tab_pred"], L["tab_backtest"], L["tab_logs"]
])
# --- TAB 6: WEBSOCKET LIVE STREAM ---
with tab_live:
    st.subheader("⚡ High-Frequency Live Ticker (WebSocket Pipe)")
    st.markdown("This tab maintains a persistent, open connection to the backend. Prices update every 500ms without refreshing the page.")

    live_ticker = st.selectbox("Select Asset to Stream", selected_tickers, key="live_stream_box")

    if st.button("▶️ Connect to Data Pipe", type="primary"):
        import json
        from websocket import create_connection

        # Create UI placeholders so we don't redraw the whole app
        status_text = st.empty()
        metric_box = st.empty()

        status_text.success(f"Establishing WebSocket connection for {live_ticker}...")

        try:
            # Change http:// to ws:// for websockets
            ws_url = API_URL.replace("http://", "ws://") + f"/api/v1/ws/stream/{live_ticker}"
            ws = create_connection(ws_url)
            status_text.success("🟢 Connected! Receiving live ticks...")

            # Infinite loop to catch the stream
            for _ in range(100): # We limit to 100 ticks just so it doesn't run forever in the browser
                result = ws.recv()
                tick = json.loads(result)

                color = "green" if tick['trend'] == 'up' else "red"
                arrow = "🔺" if tick['trend'] == 'up' else "🔻"

                # Overwrite the metric box instantly
                metric_box.markdown(f"""
                <div style='padding: 20px; border: 1px solid #333; border-radius: 10px; background-color: #121212; text-align: center;'>
                    <h2 style='margin:0;'>{tick['ticker']}</h2>
                    <h1 style='color: {color}; margin:0;'>${tick['price']:.2f} {arrow}</h1>
                    <p style='color: #888; font-family: monospace;'>Last Tick: {tick['timestamp']}</p>
                </div>
                """, unsafe_allow_html=True)

            ws.close()
            status_text.warning("Stream simulation paused after 100 ticks to save browser memory.")

        except Exception as e:
            status_text.error(f"WebSocket Connection Failed: {e}")
# --- TAB 1: DASHBOARD ---
with tab_dashboard:
    latest_rows = []
    for ticker in df_live['Ticker'].unique():
        sub = df_live[df_live['Ticker'] == ticker].sort_values('Datetime')
        if len(sub) >= 2:
            last = sub.iloc[-1].copy()
            first = sub.iloc[0]
            last['% Change'] = ((last['Close'] - first['Close']) / first['Close']) * 100
            last['Trend'] = "🟢 🔺 Up" if last['% Change'] > 0 else "🔴 🔻 Down"
            latest_rows.append(last)

    summary_df = pd.DataFrame(latest_rows)
    def color_trend(val): return f"color: {'#00ffcc' if '🔺' in str(val) else '#ff4d4d'}; font-weight: bold;"
    if not summary_df.empty:
        st.dataframe(summary_df[['Ticker', 'Datetime', 'Close', '% Change', 'Trend']].style.map(color_trend, subset=['Trend']).format({'% Change': '{:+.2f}%', 'Close': '${:,.2f}'}), use_container_width=True)

# --- TAB 3: AI PREDICTIVE (NOW TALKING TO BACKEND) ---
with tab_pred:
    predict_ticker = st.selectbox("Select Target Asset", selected_tickers, key="pred_box")
    col_pred_l, col_pred_r = st.columns([2, 1])

    with col_pred_l:
        if st.button("🔮 Run Prophet AI Forecast"):
            with st.spinner("Asking backend to run Prophet..."):
                try:
                    res = requests.post(f"{API_URL}/api/v1/forecast", json={"ticker": predict_ticker, "start_date": start_date.strftime("%Y-%m-%d"), "end_date": end_date.strftime("%Y-%m-%d"), "periods": 15})
                    if res.status_code == 200:
                        hist_data = pd.DataFrame(res.json()["historical"])
                        fore_data = pd.DataFrame(res.json()["forecast"])
                        fig_forecast = go.Figure()
                        fig_forecast.add_trace(go.Scatter(x=hist_data['ds'], y=hist_data['y'], name='Historical'))
                        fig_forecast.add_trace(go.Scatter(x=fore_data['ds'], y=fore_data['yhat'], name='AI Forecast', line=dict(color='#00ffcc')))
                        fig_forecast.update_layout(template='plotly_dark', margin=dict(l=10, r=10, t=10, b=10))
                        st.plotly_chart(fig_forecast, use_container_width=True)
                except Exception as e:
                    st.error(f"Backend AI Error: {e}")

    with col_pred_r:
        if st.button("🧠 Run FinBERT Sentiment Analysis"):
            with st.spinner("Asking backend to analyze news..."):
                try:
                    sent_res = requests.post(f"{API_URL}/api/v1/sentiment", json={"ticker": predict_ticker})
                    if sent_res.status_code == 200:
                        s_data = sent_res.json()
                        st.metric(label="FinBERT Sentiment Index", value=s_data["label"], delta=f"{s_data['score']:.3f}")
                        st.markdown("**Latest Headlines Analyzed:**")
                        for h in s_data["headlines"]: st.markdown(f"🔹 *{h}*")
                except:
                    st.error("Could not reach NLP Engine.")
