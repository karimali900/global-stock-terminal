# # # # stock_dashboard.py - Ultimate Enterprise Terminal
# # UPGRADE: Global & MENA Asset Integration, Live SMTP Email, Backtester & Exporter

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
from email.mime.image import MIMEImage


import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# ==============================================================================
# SMTP EMAIL CORE CONFIGURATION (FILL IN YOUR CREDENTIALS HERE)
# ==============================================================================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = "90.karim@gmail.com"
EMAIL_PASSWORD = "rakpehjuldjyzazr"  # Replace with Google App Password

def send_terminal_alert_email(recipient_string, subject, body_html):
    """Secure background worker thread to execute SMTP transport relays."""
    try:
        recipients = [r.strip() for r in recipient_string.split(",") if r.strip()]
        if not recipients:
            return False, "No valid email recipients parsed."

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
        "title": "📊 منصة الأسهم العالمية",
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
        "stream_status": "جاري جلب  الأوراق المالية عبر المعالجة المتوازية...",
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
# GLOBAL MEGA-CAP & MENA REGION TICKER DATABASE
# ==============================================================================
GLOBAL_AND_MENA_TICKERS = sorted([
    # US & Global Mega-Caps
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "V", "JNJ",
    "WMT", "JPM", "PG", "MA", "UNH", "HD", "CVX", "LLY", "ABBV", "MRK",
    "PEP", "KO", "BAC", "AVGO", "COST", "TMO", "MCD", "CSCO", "ABT", "CRM",
    "DHR", "ACN", "LIN", "NFLX", "ADBE", "NKE", "TXN", "CMCSA", "AMD", "PM",
    "VZ", "INTC", "QCOM", "HON", "COP", "RTX", "UNP", "IBM", "AMGN", "LOW",
    "BA", "SPGI", "GE", "NOW", "PLD", "CAT", "ELV", "GS", "SYK", "T",
    "VOD.L", "BP.L", "SAP.DE", "SIE.DE", "MC.PA", "OR.PA", "ASML.AS",
    "005930.KS", "RELIANCE.NS", "TCS.NS", "BABA", "TCEHY", "TSM",
    # Saudi Arabia (Tadawul)
    "2222.SR", "1120.SR", "2010.SR", "1180.SR", "7010.SR", "1211.SR",
    # UAE (ADX & DFM)
    "IHC.AD", "FAB.AD", "EMIRATESNBD.DU", "EMAAR.DU", "DEWA.DU", "EAND.AD",
    # Egypt (EGX)
    "COMI.CA", "HRHO.CA", "TMGH.CA", "EAST.CA",
    # Qatar & Kuwait
    "QNBK.QA", "IQCD.QA", "MARK.QA", "NBK.KW", "KFH.KW"
])

SAFE_DEFAULT_TICKERS = ["AAPL", "TSLA", "MSFT", "2222.SR", "EMAAR.DU", "COMI.CA", "QNBK.QA"]

# ==============================================================================
# 2. SQLITE STATE STORAGE SCHEMA
# ==============================================================================
st.set_page_config(page_title="Global Stock Intelligence Terminal", layout="wide", initial_sidebar_state="expanded")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

# 🚀 TEST EMAIL CONNECTION ACTION BUTTON
if st.sidebar.button(L["email_test_btn"], type="secondary", use_container_width=True):
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    html_content = f"""
    <html>
        <body style='font-family: Arial, sans-serif; background-color: #121212; color: #ffffff; padding: 20px;'>
            <h2 style='color: #00ffcc;'>📡 Global Stock Intelligence Node Connected</h2>
            <p>This is an automated production verification packet validating your SMTP broadcast bridge loops.</p>
            <hr style='border: 0.5px solid #333;' />
            <p style='font-size: 11px; color: #888;'>Chronos Timestamp: {current_time}</p>
        </body>
    </html>
    """

    if EMAIL_PASSWORD == "your-16-character-app-password":
        st.sidebar.error("⚠️ Authentication Missing: Please enter your Google App Password in the code script.")
    else:
        with st.spinner("Processing network handshake..."):
            success, info = send_terminal_alert_email(email_input_raw, "📊 Terminal Verification Connection Packet", html_content)
            if success:
                st.sidebar.success(L["email_success"])
                st.sidebar.info(f"**📄 Delivery Receipt Confirmation:**\n* **Status:** Dispatched Successfully ✅\n* **Destination:** `{email_input_raw}`\n* **Timestamp:** `{current_time}`")
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

# Ribbon
m1, m2, m3, m4 = st.columns(4)
m1.metric(L["m_active"], len(selected_tickers))
m2.metric(L["m_telemetry"], len(df_live))
m3.metric(L["m_ai"], "ONLINE" if FINBERT_READY else "OFFLINE")
m4.metric(L["m_chronos"], datetime.now().strftime('%H:%M:%S'))

tab_dashboard, tab_tech, tab_pred, tab_backtest, tab_logs = st.tabs([
    L["tab_perf"], L["tab_tech"], L["tab_pred"], L["tab_backtest"], L["tab_logs"]
])

# --- DASHBOARD WITH ARROWS & SCATTER CHART ---
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
        color = '#00ffcc' if '🔺' in str(val) else '#ff4d4d' if '🔻' in str(val) else 'gray'
        return f'color: {color}; font-weight: bold;'

    st.dataframe(
        summary_df[['Ticker', 'Datetime', 'Open', 'High', 'Low', 'Close', 'Volume', '% Change', 'Trend']]
        .style.map(color_trend, subset=['Trend'])
        .format({'% Change': '{:+.2f}%', 'Close': '${:,.2f}'}),
        use_container_width=True
    )

    st.markdown("---")
    chart_ticker = st.selectbox(L["chart_lbl"], summary_df['Ticker'].unique())
    chart_df = df_live[df_live['Ticker'] == chart_ticker].sort_values('Datetime')

    fig_scatter = go.Figure()
    fig_scatter.add_trace(go.Scatter(
        x=chart_df['Datetime'], y=chart_df['Close'], mode='lines+markers',
        name=f'{chart_ticker} Price', marker=dict(size=6, color='#ff9900'), line=dict(width=2, color='rgba(255, 153, 0, 0.5)')
    ))
    fig_scatter.update_layout(title=f"Scatter Trend Analysis: {chart_ticker}", template='plotly_dark')
    st.plotly_chart(fig_scatter, use_container_width=True)

# --- TECHNICAL & AI PREDICTIVE TABS ---
with tab_tech:
    st.info("Technical charts rendering loops processing.")

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
            fig_forecast.update_layout(template='plotly_dark')
            st.plotly_chart(fig_forecast, use_container_width=True)

    with col_pred_r:
        if FINBERT_READY: st.success(L["ai_online"])
        else: st.warning(L["ai_offline"])
        with st.spinner(f"Ingesting feeds..."):
            try:
                ticker_obj = yf.Ticker(predict_ticker)
                headlines = [item.get('title', '') for item in (ticker_obj.news or []) if item.get('title')]
                if not headlines:
                    st.caption(L["fallback_msg"])
                    query_search = [f"{predict_ticker} stock financial update"]
                    for query in query_search:
                        try:
                            headlines.extend([item.get('title', '') for item in yf.Search(query, max_results=3).news if item.get('title')])
                        except: pass

                if headlines:
                    st.markdown(f"**{L['headlines_lbl']} ({len(headlines[:5])}):**")
                    for h in headlines[:3]: st.markdown(f"🔹 *\"{h}\"*")
                    label_output, numeric_mean = run_finbert_inference(headlines)
                    if "Negative" in label_output or "سلبية" in label_output: st.error(f"Analysis: {label_output} ({numeric_mean:.3f})")
                    elif "Positive" in label_output or "إيجابية" in label_output: st.success(f"Analysis: {label_output} ({numeric_mean:.3f})")
                    else: st.warning(f"Analysis: {label_output} ({numeric_mean:.3f})")
                    st.metric(label=L["sent_idx"], value=label_output, delta=f"{numeric_mean:.3f}")
                else: st.info(L["no_data"])
            except Exception as sent_err: st.error(f"{L['nlp_error']}: {sent_err}")

# --- PORTFOLIO BACKTESTER CORE ---
with tab_backtest:
    st.subheader(L["tab_backtest"])
    capital = st.number_input(L["bt_capital"], min_value=100, max_value=10000000, value=10000, step=1000)
    bt_mode = st.selectbox(L["bt_mode"], [L["bt_mode_whole"], L["bt_mode_single"]])

    target_asset_list = []
    if bt_mode == L["bt_mode_single"]:
        chosen_isolated_ticker = st.selectbox(L["bt_select_single"], sorted(df_live['Ticker'].unique()))
        target_asset_list = [chosen_isolated_ticker]
    else:
        target_asset_list = list(df_live['Ticker'].unique())

    if st.button(L["bt_run"], type="primary", use_container_width=True):
        subset_live = df_live[df_live['Ticker'].isin(target_asset_list)]
        pivot_df = subset_live.pivot(index='Datetime', columns='Ticker', values='Close').dropna(how='any')

        if not pivot_df.empty:
            normalized_returns = pivot_df / pivot_df.iloc[0]
            portfolio_growth = normalized_returns.mean(axis=1)
            portfolio_value = portfolio_growth * capital

            fig_bt = go.Figure()
            fig_bt.add_trace(go.Scatter(
                x=portfolio_value.index, y=portfolio_value.values, mode='lines', name='Portfolio Value', line=dict(color='#00ffcc', width=3)
            ))
            fig_bt.add_hline(y=capital, line_dash="dash", line_color="#ff4d4d", annotation_text="Initial Capital Baseline")
            fig_bt.update_layout(title=f"{L['bt_curve']} ({bt_mode})", template='plotly_dark', yaxis_title="Equity Value ($)")
            st.plotly_chart(fig_bt, use_container_width=True)

            final_val = portfolio_value.iloc[-1]
            roi = ((final_val - capital) / capital) * 100

            c1, c2 = st.columns(2)
            c1.metric(label="Ending Portfolio Value", value=f"${final_val:,.2f}", delta=f"{roi:+.2f}%")
            c2.success("Backtest engine simulation executed successfully across the matrix timeline.")
        else:
            st.warning("Insufficient overlapping timeline data to execute strategy allocation for this selection.")

# --- EXECUTIVE REPORT EXPORT ---

# --- TAB 5: AUTOMATION LOGS & REPORT DISPATCH ---
with tab_logs:
    st.subheader("System Topology & Reports")
    st.json(ingestion_stats)
    st.markdown("---")

    col_export1, col_export2 = st.columns(2)

    with col_export1:
        # Existing CSV Export
        csv_data = summary_df.to_csv(index=False).encode('utf-8')
        st.download_button(label=L["export_btn"], data=csv_data, file_name="Executive_Terminal_Report.csv", mime='text/csv', use_container_width=True)

    with col_export2:
        # NEW: Full Report Email Dispatcher
        if st.button("📧 Email Full Executive Report Now", type="primary", use_container_width=True):
            if EMAIL_PASSWORD == "your-16-character-app-password":
                st.error("⚠️ Authentication Missing: Enter your Google App Password in the script.")
            else:
                with st.spinner("Generating charts and compiling executive briefing..."):
                    try:
                        # 1. Generate the Chart Image (Using the first active ticker as the visual)
                        target_chart_ticker = summary_df.iloc[0]['Ticker'] if not summary_df.empty else "AAPL"
                        chart_df = df_live[df_live['Ticker'] == target_chart_ticker].sort_values('Datetime')

                        fig_export = go.Figure()
                        fig_export.add_trace(go.Scatter(x=chart_df['Datetime'], y=chart_df['Close'], mode='lines+markers', line=dict(color='#00ffcc', width=2)))
                        fig_export.update_layout(title=f"{target_chart_ticker} Market Trajectory", template='plotly_dark', paper_bgcolor='#121212', plot_bgcolor='#121212')

                        chart_filename = "temp_market_chart.png"
                        fig_export.write_image(chart_filename, engine="kaleido")

                        # 2. Build the HTML Table from summary_df
                        table_rows_html = ""
                        for _, row in summary_df.iterrows():
                            color = "#00ffcc" if row['% Change'] > 0 else "#ff4d4d"
                            table_rows_html += f"""
                            <tr style="border-bottom: 1px solid #333;">
                                <td style="padding: 12px; font-weight: bold;">{row['Ticker']}</td>
                                <td style="padding: 12px;">${row['Close']:.2f}</td>
                                <td style="padding: 12px; color: {color}; font-weight: bold;">{row['% Change']:+.2f}%</td>
                                <td style="padding: 12px;">{row['Trend']}</td>
                            </tr>
                            """

                        html_body = f"""
                        <html>
                            <body style="font-family: Arial, sans-serif; background-color: #ffffff; color: #333333; padding: 20px;">
                                <div style="max-width: 650px; margin: auto; border: 1px solid #e0e0e0; border-radius: 8px; padding: 25px;">
                                    <h2 style="color: #111111; border-bottom: 2px solid #00ffcc; padding-bottom: 10px;">📊 Institutional Daily Market Briefing</h2>
                                    <p>Please find below the closing performance matrices across the active security universe:</p>
                                    <table style="width: 100%; border-collapse: collapse; text-align: left; margin-bottom: 25px;">
                                        <thead>
                                            <tr style="background-color: #f8f9fa; border-bottom: 2px solid #ddd;">
                                                <th style="padding: 12px;">Asset Node</th><th style="padding: 12px;">Closing Price</th><th style="padding: 12px;">Variance</th><th style="padding: 12px;">Direction</th>
                                            </tr>
                                        </thead>
                                        <tbody>{table_rows_html}</tbody>
                                    </table>
                                    <h3 style="color: #222222;">📈 Market Trend Visualization ({target_chart_ticker})</h3>
                                    <img src="cid:market_chart" style="width: 100%; max-width: 600px; border-radius: 4px;" />
                                    <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;" />
                                    <p style="font-size: 11px; color: #999;">Automated Global Stock Intelligence Node | Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                                </div>
                            </body>
                        </html>
                        """

                        # 3. Transmit the Email
                        recipients = [r.strip() for r in email_input_raw.split(",") if r.strip()]
                        msg = MIMEMultipart("related")
                        msg["Subject"] = f"📊 Executive Briefing: Daily Market Intelligence ({datetime.now().strftime('%b %d')})"
                        msg["From"] = EMAIL_SENDER
                        msg["To"] = ", ".join(recipients)

                        msg_alt = MIMEMultipart("alternative")
                        msg.attach(msg_alt)
                        msg_alt.attach(MIMEText(html_body, "html"))

                        # Embed Image
                        with open(chart_filename, "rb") as img_file:
                            msg_image = MIMEImage(img_file.read())
                            msg_image.add_header("Content-ID", "<market_chart>")
                            msg.attach(msg_image)

                        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                            server.starttls()
                            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
                            server.sendmail(EMAIL_SENDER, recipients, msg.as_string())

                        # Cleanup
                        if os.path.exists(chart_filename): os.remove(chart_filename)
                        st.success(f"✅ Full Executive Report successfully sent to {len(recipients)} recipient(s)!")

                    except Exception as e:
                        st.error(f"❌ Transmission Interrupted: {str(e)}")

# ==============================================================================
# PROSCANNER ASYNC LOOP EXECUTION
# ==============================================================================
if enable_refresh:
    time.sleep(refresh_interval)
    st.rerun()
