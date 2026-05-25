# # # # stock_dashboard.py - Ultimate Enterprise Terminal
# # UPGRADE: Edge-to-Edge UI, Fleshed out Technical Analysis (Candlestick + RSI), Global & MENA

import os
import io
import time
import json
import sqlite3
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import redis
import yfinance as yf
import sqlalchemy as sa
from prophet import Prophet
from transformers import pipeline

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==============================================================================
# SMTP EMAIL CORE CONFIGURATION
# ==============================================================================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = "90.karim@gmail.com"
EMAIL_PASSWORD = "rakpehjuldjyzazr"

def send_terminal_alert_email(recipient_string, subject, body_html):
    try:
        recipients = [r.strip() for r in recipient_string.split(",") if r.strip()]
        if not recipients: return False, "No valid email recipients parsed."
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(body_html, "html"))
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, recipients, msg.as_string())
        return True, "Success"
    except Exception as smtp_err:
        return False, str(smtp_err)

# ==============================================================================
# 1. BILINGUAL LOCALIZATION DICTIONARY MATRIX
# ==============================================================================
TRANSLATIONS = {
    "EN": {
        "title": "📊 Global Stock Intelligence Terminal",
        "control_panel": "🛠️ Terminal Control Center",
        "universe": "Active Asset Universe (Global & MENA)",
        "recipients": "📬 Alert Configuration Group",
        "recipients_hint": "Recipient Outboxes (Comma Separated)",
        "email_test_btn": "🧪 Send Test Alert Email",
        "email_success": "Test email packet successfully dispatched to SMTP relay!",
        "email_failed": "SMTP Connection Interruption: ",
        "tolerances": "🚨 Risk Warning Tolerances",
        "drop_lbl": "Anomaly Deflection Drop (%)",
        "vol_lbl": "Volume Spike Multiple (x Avg)",
        "sent_lbl": "Negative AI Sentiment Barrier",
        "stream_settings": "⚡ ProScanner Streaming Mode",
        "refresh_on": "Enable Live Terminal Refresh Loop",
        "refresh_lbl": "Auto-Refresh Interval (Seconds)",
        "save_btn": "💾 Save Configuration Defaults",
        "save_success": "Layout profile synchronized to SQLite memory blocks!",
        "stream_status": "Fetching underlying security matrices across threads...",
        "m_active": "Assets Active",
        "m_telemetry": "Telemetry Points Processed",
        "m_ai": "FinBERT AI Engine Status",
        "m_chronos": "Chronos System Stamp",
        "tab_perf": "📈 Market Performance Grid",
        "tab_tech": "🔬 Technical Terminal",
        "tab_pred": "🔮 AI Forecasting",
        "tab_backtest": "💼 Portfolio Backtester",
        "tab_logs": "📡 Automation Hub",
        "perf_header": "Global Security Performance Tracker Matrix",
        "chart_lbl": "Select Asset to View Scatter Movement",
        "tech_header": "Advanced Candlestick Overlay & Momentum Oscillator Framework",
        "tech_select": "Choose Technical Analysis Target Node",
        "nlp_header": "Deep NLP Transformer Inference Engine & Predictive Regression",
        "select_asset": "Select Target Optimization Asset Node",
        "ai_online": "🤖 ProsusAI FinBERT Engine: ONLINE",
        "ai_offline": "⚠️ Local CPU Baseline Fallback Active",
        "fallback_msg": "🔄 Direct ticker news empty. Activating broader query aggregator fallback...",
        "headlines_lbl": "Ingested Headlines Block",
        "sent_idx": "FinBERT Sentiment Index Scale",
        "no_data": "ℹ️ Market data streams are currently dry for this asset. No global news captured.",
        "nlp_error": "NLP Pipeline Interruption",
        "bt_capital": "Initial Investment Capital ($)",
        "bt_mode": "Backtest Strategy Target Allocation",
        "bt_mode_whole": "Whole Collection (Equal Weight Balance)",
        "bt_mode_single": "Specific Single Stock",
        "bt_select_single": "Choose Asset Node for Isolation Analysis",
        "bt_run": "▶️ Run Historical Portfolio Backtest",
        "bt_curve": "Cumulative Portfolio Equity Curve",
        "export_btn": "📥 Download Executive Matrix Report (CSV)"
    },
    "AR": {
        "title": "📊 منصة استخبارات الأسهم العالمية",
        "control_panel": "🛠️ مركز التحكم في المنصة",
        "universe": "نطاق الأصول النشطة (العالمية والشرق الأوسط)",
        "recipients": "📬 مجموعة تكوين التنبيهات",
        "recipients_hint": "صناديق بريد المستلمين (مفصولة بفاصلة)",
        "email_test_btn": "🧪 إرسال بريد إلكتروني تجريبي",
        "email_success": "تم إرسال حزمة البريد التجريبية بنجاح عبر خادم SMTP!",
        "email_failed": "انقطاع الاتصال بخادم البريد: ",
        "tolerances": "🚨 حدود مخاطر التحذير",
        "drop_lbl": "نسبة هبوط انحراف الأسعار (%)",
        "vol_lbl": "مضاعف طفرة حجم التداول (x المتوسط)",
        "sent_lbl": "حاجز مشاعر الذكاء الاصطناعي السلبية",
        "stream_settings": "⚡ وضع البث الحي (بروسكانر)",
        "refresh_on": "تفعيل حلقة التحديث المباشر للمنصة",
        "refresh_lbl": "فترة التحديث التلقائي (بالثواني)",
        "save_btn": "💾 حفظ الإعدادات الافتراضية",
        "save_success": "تمت مزامنة ملف الإعدادات بنجاح!",
        "stream_status": "جاري جلب مصفوفات الأوراق المالية عبر المعالجة المتوازية...",
        "m_active": "الأصول النشطة",
        "m_telemetry": "نقاط البيانات المعالجة",
        "m_ai": "حالة محرك مشاعر الـ AI",
        "m_chronos": "طابع نظام كرونوس الزمني",
        "tab_perf": "📈 شبكة أداء السوق",
        "tab_tech": "🔬 التحليل الفني المتقدم",
        "tab_pred": "🔮 التنبؤ بالذكاء الاصطناعي",
        "tab_backtest": "💼 مختبر أداء المحفظة الأصول",
        "tab_logs": "📡 مركز الأتمتة والنظام",
        "perf_header": "مصفوفة تتبع أداء الأوراق المالية العالمية",
        "chart_lbl": "حدد أصلاً لعرض حركة السعر المبعثرة",
        "tech_header": "إطار عمل الشموع اليابانية المتقدمة ومذبذب الزخم",
        "tech_select": "اختر عقدة الأصل للتحليل الفني",
        "nlp_header": "محرك استدلال المحولات ومعالجة اللغة الطبيعية",
        "select_asset": "اختر أصل التحليل المستهدف",
        "ai_online": "🤖 محرك الذكاء الاصطناعي FinBERT: متصل",
        "ai_offline": "⚠️ الوضع الاحتياطي للمعالج المحلي نشط",
        "fallback_msg": "🔄 لا توجد أخبار مباشرة للأصل. جاري تفعيل بحث أشمل عبر المجمع...",
        "headlines_lbl": "كتلة العناوين الإخبارية المستخرجة",
        "sent_idx": "مؤشر قطبية المشاعر (FinBERT)",
        "no_data": "ℹ️ لا توجد بيانات حالية لهذا الأصل. لم يتم التقاط أخبار ضمن النطاق الزمني.",
        "nlp_error": "انقطاع في مسار معالجة اللغة الطبيعية",
        "bt_capital": "رأس المال الاستثماري الأولي ($)",
        "bt_mode": "استراتيجية تخصيص هدف الاختبار",
        "bt_mode_whole": "المجموعة الكاملة (موازنة أوزان متساوية)",
        "bt_mode_single": "سهم فردي محدد",
        "bt_select_single": "اختر عقدة الأصل للتحليل المنفصل",
        "bt_run": "▶️ تشغيل اختبار الأداء التاريخي",
        "bt_curve": "منحنى حقوق ملكية المحفظة التراكمي",
        "export_btn": "📥 تحميل التقرير التنفيذي الشامل (CSV)"
    }
}

# ==============================================================================
# TICKER DATABASE
# ==============================================================================
GLOBAL_AND_MENA_TICKERS = sorted([
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "V", "JNJ",
    "WMT", "JPM", "PG", "MA", "UNH", "HD", "CVX", "LLY", "ABBV", "MRK",
    "PEP", "KO", "BAC", "AVGO", "COST", "TMO", "MCD", "CSCO", "ABT", "CRM",
    "DHR", "ACN", "LIN", "NFLX", "ADBE", "NKE", "TXN", "CMCSA", "AMD", "PM",
    "VZ", "INTC", "QCOM", "HON", "COP", "RTX", "UNP", "IBM", "AMGN", "LOW",
    "BA", "SPGI", "GE", "NOW", "PLD", "CAT", "ELV", "GS", "SYK", "T",
    "VOD.L", "BP.L", "SAP.DE", "SIE.DE", "MC.PA", "OR.PA", "ASML.AS",
    "005930.KS", "RELIANCE.NS", "TCS.NS", "BABA", "TCEHY", "TSM",
    "2222.SR", "1120.SR", "2010.SR", "1180.SR", "7010.SR", "1211.SR",
    "IHC.AD", "FAB.AD", "EMIRATESNBD.DU", "EMAAR.DU", "DEWA.DU", "EAND.AD",
    "COMI.CA", "HRHO.CA", "TMGH.CA", "EAST.CA", "QNBK.QA", "IQCD.QA", "MARK.QA", "NBK.KW", "KFH.KW"
])

SAFE_DEFAULT_TICKERS = ["AAPL", "TSLA", "MSFT", "2222.SR", "EMAAR.DU", "COMI.CA"]

# ==============================================================================
# 2. STATE PERSISTENCE SCHEMA & INTERFACE STYLING
# ==============================================================================
st.set_page_config(page_title="Global Stock Intelligence Terminal", layout="wide", initial_sidebar_state="expanded")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Edge-to-Edge Custom CSS Injection
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 98% !important;
        }
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stDataFrame div { max-width: 100% !important; }
    </style>
""", unsafe_allow_html=True)

DB_STATE_FILE = "user_dashboard_state.db"

def init_state_db():
    conn = sqlite3.connect(DB_STATE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_config (
            id INTEGER PRIMARY KEY, tickers TEXT, emails TEXT,
            drop_limit REAL, vol_limit REAL, sentiment_limit REAL, lang_pref TEXT,
            refresh_enabled INTEGER DEFAULT 0, refresh_interval INTEGER DEFAULT 15
        )
    ''')
    conn.commit()
    conn.close()

def save_user_profile(tickers, emails, drop_limit, vol_limit, sentiment_limit, lang_pref, refresh_on, refresh_int):
    try:
        conn = sqlite3.connect(os.path.abspath(DB_STATE_FILE), timeout=10.0)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM system_config")
        cursor.execute(
            "INSERT INTO system_config (tickers, emails, drop_limit, vol_limit, sentiment_limit, lang_pref, refresh_enabled, refresh_interval) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (json.dumps(list(tickers)), str(emails), float(drop_limit), float(vol_limit), float(sentiment_limit), str(lang_pref), int(refresh_on), int(refresh_int))
        )
        conn.commit()
        conn.close()
        return True
    except: return False

def load_user_profile():
    try:
        conn = sqlite3.connect(DB_STATE_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT tickers, emails, drop_limit, vol_limit, sentiment_limit, lang_pref, refresh_enabled, refresh_interval FROM system_config LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "tickers": json.loads(row[0]), "emails": row[1], "drop_limit": row[2],
                "vol_limit": row[3], "sentiment_limit": row[4], "lang_pref": row[5],
                "refresh_enabled": bool(row[6]), "refresh_interval": row[7]
            }
    except: pass
    return None

init_state_db()
saved_profile = load_user_profile()

init_tickers = saved_profile["tickers"] if saved_profile else SAFE_DEFAULT_TICKERS
init_emails = saved_profile["emails"] if saved_profile else "90.karim@gmail.com"
init_drop = saved_profile["drop_limit"] if saved_profile else -5.0
init_vol = saved_profile["vol_limit"] if saved_profile else 2.0
init_sent = saved_profile["sentiment_limit"] if saved_profile else -0.15
init_lang = saved_profile["lang_pref"] if saved_profile else "EN"
init_refresh_on = saved_profile["refresh_enabled"] if saved_profile else False
init_refresh_int = saved_profile["refresh_interval"] if saved_profile else 15

# ==============================================================================
# 3. FinBERT TRANSFORMER CONFIGURATION
# ==============================================================================
@st.cache_resource
def load_finbert_pipeline():
    try:
        nlp_classifier = pipeline("sentiment-analysis", model="ProsusAI/finbert", tokenizer="ProsusAI/finbert")
        return nlp_classifier, True
    except: return None, False

FINBERT_ENGINE, FINBERT_READY = load_finbert_pipeline()

def run_finbert_inference(headlines_list):
    if not FINBERT_READY or not headlines_list: return "Neutral 😐", 0.0
    try:
        results = FINBERT_ENGINE(headlines_list[:5])
        scores = [{"positive": 1.0, "neutral": 0.0, "negative": -1.0}[res['label'].lower()] for res in results]
        mean_score = float(np.mean(scores))
        if mean_score > 0.2: return "Positive 😊", mean_score
        elif mean_score < -0.2: return "Negative 😟", mean_score
        else: return "Neutral 😐", mean_score
    except: return "Error ⚠️", 0.0

# ==============================================================================
# 4. SIDEBAR & LANGUAGE TOGGLE
# ==============================================================================
st.sidebar.markdown("### 🌐 Language Select / اختيار اللغة")
lang_choice = st.sidebar.radio("Language Mode", ["English", "العربية"], index=0 if init_lang == "EN" else 1, label_visibility="collapsed")
active_lang_code = "EN" if lang_choice == "English" else "AR"
L = TRANSLATIONS[active_lang_code]

if active_lang_code == "AR":
    st.markdown("""<style> div.stApp { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)

st.sidebar.header(L["control_panel"])
selected_tickers = st.sidebar.multiselect(L["universe"], GLOBAL_AND_MENA_TICKERS, default=init_tickers)

st.sidebar.subheader(L["recipients"])
email_input_raw = st.sidebar.text_area(L["recipients_hint"], value=init_emails)

if st.sidebar.button(L["email_test_btn"], type="secondary", use_container_width=True):
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    html_content = f"<html><body style='font-family:Arial; background:#121212; color:#fff; padding:20px;'><h2 style='color:#00ffcc;'>📡 Node Connected</h2><p>SMTP broadcast validation packet active.</p></body></html>"
    if EMAIL_PASSWORD == "your-16-character-app-password":
        st.sidebar.error("⚠️ Authentication Missing: Enter your Google App Password in the script.")
    else:
        with st.spinner("Processing network handshake..."):
            success, info = send_terminal_alert_email(email_input_raw, "📊 Terminal Verification Connection Packet", html_content)
            if success:
                st.sidebar.success(L["email_success"])
                st.sidebar.info(f"**📄 Delivery Receipt:**\n* **Status:** Dispatched ✅\n* **Destination:** `{email_input_raw}`")
            else:
                st.sidebar.error(f"{L['email_failed']} {info}")

st.sidebar.subheader(L["tolerances"])
drop_pct = st.sidebar.slider(L["drop_lbl"], -15.0, -1.0, init_drop, step=0.5)
vol_factor = st.sidebar.slider(L["vol_lbl"], 1.5, 5.0, init_vol, step=0.1)
sentiment_threshold = st.sidebar.slider(L["sent_lbl"], -1.0, 0.0, init_sent, step=0.05)

st.sidebar.subheader(L["stream_settings"])
enable_refresh = st.sidebar.toggle(L["refresh_on"], value=init_refresh_on)
refresh_interval = st.sidebar.number_input(L["refresh_lbl"], min_value=5, max_value=300, value=init_refresh_int, step=5)

if st.sidebar.button(L["save_btn"], type="secondary", use_container_width=True):
    save_user_profile(selected_tickers, email_input_raw, drop_pct, vol_factor, sentiment_threshold, active_lang_code, enable_refresh, refresh_interval)
    st.sidebar.success(L["save_success"])
    time.sleep(0.8)
    st.rerun()

# ==============================================================================
# 5. CORE DATA ENGINE
# ==============================================================================
st.title(L["title"])

def fetch_ticker_data(ticker):
    try:
        data = yf.download(ticker, period="3mo", interval="1d", auto_adjust=True, progress=False)
        if data.empty: return pd.DataFrame(), "Empty"
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]
        df = data.reset_index()
        df['Ticker'] = ticker
        df.rename(columns={'Date': 'Datetime'}, inplace=True)
        return df[['Datetime', 'Ticker', 'Open', 'High', 'Low', 'Close', 'Volume']].dropna(), "Sync 🌐"
    except: return pd.DataFrame(), "Error"

def load_live_universe(tickers):
    df_list = []
    stats = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_ticker_data, t): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            res_df, status = future.result()
            stats[ticker] = status
            if not res_df.empty: df_list.append(res_df)
    if not df_list: return pd.DataFrame(), stats
    return pd.concat(df_list, ignore_index=True).sort_values(['Ticker', 'Datetime']), stats

with st.spinner(L["stream_status"]):
    df_live, ingestion_stats = load_live_universe(selected_tickers)

if df_live.empty:
    st.error("Global system loop reported empty matrix arrays.")
    st.stop()

# Metric Status Block
m1, m2, m3, m4 = st.columns(4)
m1.metric(L["m_active"], len(selected_tickers))
m2.metric(L["m_telemetry"], len(df_live))
m3.metric(L["m_ai"], "ONLINE" if FINBERT_READY else "OFFLINE")
m4.metric(L["m_chronos"], datetime.now().strftime('%H:%M:%S'))

tab_dashboard, tab_tech, tab_pred, tab_backtest, tab_logs = st.tabs([
    L["tab_perf"], L["tab_tech"], L["tab_pred"], L["tab_backtest"], L["tab_logs"]
])

# --- TAB 1: DASHBOARD ---
with tab_dashboard:
    st.subheader(L["perf_header"])
    latest_rows = []
    for ticker in df_live['Ticker'].unique():
        sub = df_live[df_live['Ticker'] == ticker].sort_values('Datetime')
        if len(sub) >= 2:
            last = sub.iloc[-1].copy()
            prev = sub.iloc[-2]
            last['% Change'] = ((last['Close'] - prev['Close']) / prev['Close']) * 100
            last['Trend'] = "🟢 🔺 Up" if last['% Change'] > 0 else "🔴 🔻 Down"
            latest_rows.append(last)

    summary_df = pd.DataFrame(latest_rows)
    def color_trend(val):
        return f"color: {'#00ffcc' if '🔺' in str(val) else '#ff4d4d'}; font-weight: bold;"

    st.dataframe(
        summary_df[['Ticker', 'Datetime', 'Open', 'High', 'Low', 'Close', 'Volume', '% Change', 'Trend']]
        .style.map(color_trend, subset=['Trend'])
        .format({'% Change': '{:+.2f}%', 'Close': '${:,.2f}'}),
        use_container_width=True
    )

# --- TAB 2: TECHNICAL TERMINAL (FLESHED OUT) ---
with tab_tech:
    st.subheader(L["tech_header"])
    tech_ticker = st.selectbox(L["tech_select"], sorted(df_live['Ticker'].unique()), key="tech_selector_box")

    t_df = df_live[df_live['Ticker'] == tech_ticker].sort_values('Datetime').copy()

    if len(t_df) >= 14:
        # Vectorized Tech Indicators Calculations
        t_df['SMA20'] = t_df['Close'].rolling(window=20).mean()
        t_df['SMA50'] = t_df['Close'].rolling(window=50).mean()

        # Native Pandas RSI Engine
        delta = t_df['Close'].diff()
        gain = delta.clip(lower=0)
        loss = -1 * delta.clip(upper=0)
        ema_gain = gain.ewm(com=13, adjust=False).mean()
        ema_loss = loss.ewm(com=13, adjust=False).mean()
        rs = ema_gain / (ema_loss + 1e-10) # Prevent zero division
        t_df['RSI'] = 100 - (100 / (1 + rs))

        # Dual Plot Subplots Architecture
        fig_tech = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_width=[0.3, 0.7])

        # Row 1: Candlesticks & SMAs
        fig_tech.add_trace(go.Candlestick(
            x=t_df['Datetime'], open=t_df['Open'], high=t_df['High'], low=t_df['Low'], close=t_df['Close'], name="Candlestick"
        ), row=1, col=1)
        fig_tech.add_trace(go.Scatter(x=t_df['Datetime'], y=t_df['SMA20'], name='SMA 20', line=dict(color='#00ffcc', width=1.5)), row=1, col=1)
        fig_tech.add_trace(go.Scatter(x=t_df['Datetime'], y=t_df['SMA50'], name='SMA 50', line=dict(color='#ff9900', width=1.5)), row=1, col=1)

        # Row 2: RSI Oscillator
        fig_tech.add_trace(go.Scatter(x=t_df['Datetime'], y=t_df['RSI'], name='RSI (14)', line=dict(color='#e100ff', width=2)), row=2, col=1)
        fig_tech.add_hline(y=70, line_dash="dash", line_color="#ff4d4d", row=2, col=1)
        fig_tech.add_hline(y=30, line_dash="dash", line_color="#00ffcc", row=2, col=1)

        fig_tech.update_layout(height=650, template='plotly_dark', xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_tech, use_container_width=True)
    else:
        st.warning("Insufficient timeline points captured to build out technical indicators models.")

# --- TAB 3: AI PREDICTIVE ---
with tab_pred:
    st.subheader(L["nlp_header"])
    predict_ticker = st.selectbox(L["select_asset"], selected_tickers, key="pred_box")
    col_pred_l, col_pred_r = st.columns([2, 1])

    with col_pred_l:
        p_df = df_live[df_live['Ticker'] == predict_ticker][['Datetime', 'Close']].rename(columns={'Datetime': 'ds', 'Close': 'y'})
        p_df['ds'] = p_df['ds'].dt.tz_localize(None)
        if len(p_df) > 12:
            model = Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=False)
            model.fit(p_df)
            forecast = model.predict(model.make_future_dataframe(periods=15))
            fig_forecast = go.Figure()
            fig_forecast.add_trace(go.Scatter(x=p_df['ds'], y=p_df['y'], name='Historical'))
            fig_forecast.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat'], name='Prophet Output', line=dict(color='#00ffcc')))
            fig_forecast.update_layout(template='plotly_dark', margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_forecast, use_container_width=True)

    with col_pred_r:
        if FINBERT_READY: st.success(L["ai_online"])
        else: st.warning(L["ai_offline"])
        with st.spinner("Ingesting feeds..."):
            try:
                ticker_obj = yf.Ticker(predict_ticker)
                headlines = [item.get('title', '') for item in (ticker_obj.news or []) if item.get('title')]
                if headlines:
                    st.markdown(f"**{L['headlines_lbl']} ({len(headlines[:5])}):**")
                    for h in headlines[:3]: st.markdown(f"🔹 *\"{h}\"*")
                    label_output, numeric_mean = run_finbert_inference(headlines)
                    st.metric(label=L["sent_idx"], value=label_output, delta=f"{numeric_mean:.3f}")
                else: st.info(L["no_data"])
            except Exception as sent_err: st.error(f"{L['nlp_error']}: {sent_err}")

# --- TAB 4: PORTFOLIO BACKTESTER ---
with tab_backtest:
    st.subheader(L["tab_backtest"])
    capital = st.number_input(L["bt_capital"], min_value=100, max_value=10000000, value=10000, step=1000)
    bt_mode = st.selectbox(L["bt_mode"], [L["bt_mode_whole"], L["bt_mode_single"]])

    target_asset_list = [st.selectbox(L["bt_select_single"], sorted(df_live['Ticker'].unique()))] if bt_mode == L["bt_mode_single"] else list(df_live['Ticker'].unique())

    if st.button(L["bt_run"], type="primary", use_container_width=True):
        subset_live = df_live[df_live['Ticker'].isin(target_asset_list)]
        pivot_df = subset_live.pivot(index='Datetime', columns='Ticker', values='Close').dropna(how='any')

        if not pivot_df.empty:
            normalized_returns = pivot_df / pivot_df.iloc[0]
            portfolio_value = normalized_returns.mean(axis=1) * capital

            fig_bt = go.Figure()
            fig_bt.add_trace(go.Scatter(x=portfolio_value.index, y=portfolio_value.values, mode='lines', name='Portfolio Value', line=dict(color='#00ffcc', width=3)))
            fig_bt.update_layout(title=f"{L['bt_curve']} ({bt_mode})", template='plotly_dark', margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_bt, use_container_width=True)

            final_val = portfolio_value.iloc[-1]
            st.metric(label="Ending Portfolio Value", value=f"${final_val:,.2f}", delta=f"{((final_val - capital) / capital) * 100:+.2f}%")
        else:
            st.warning("Insufficient overlapping timeline data.")

# --- TAB 5: AUTOMATION LOGS ---
with tab_logs:
    st.subheader("System Topology & Reports")
    st.json(ingestion_stats)
    st.markdown("---")
    csv_data = summary_df.to_csv(index=False).encode('utf-8')
    st.download_button(label=L["export_btn"], data=csv_data, file_name="Executive_Terminal_Report.csv", mime='text/csv', use_container_width=True)

if enable_refresh:
    time.sleep(refresh_interval)
    st.rerun()
