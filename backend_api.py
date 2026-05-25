# =========================================================
# backend_api.py
# Enterprise FastAPI Market Intelligence Engine
# Phase 3: SQLite Timeseries Integration
# =========================================================

import asyncio
import random
import sqlite3
from datetime import datetime
from typing import List

import pandas as pd
import yfinance as yf
from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect
)
from prophet import Prophet
from pydantic import BaseModel
import uvicorn
import requests
# =========================================================
# FASTAPI INIT
# =========================================================

app = FastAPI(
    title="Global Stock Intelligence API"
)

DB_FILE = "enterprise_market_data.db"

# =========================================================
# DATABASE INIT
# =========================================================

def init_db():

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historical_prices (

            Ticker TEXT,
            Datetime TEXT,

            Open REAL,
            High REAL,
            Low REAL,
            Close REAL,

            Volume INTEGER,

            UNIQUE(Ticker, Datetime)
        )
    """)

    conn.commit()
    conn.close()

init_db()

# =========================================================
# API MODELS
# =========================================================

class MarketDataRequest(BaseModel):

    tickers: List[str]
    start_date: str
    end_date: str


class PredictRequest(BaseModel):

    ticker: str
    periods: int = 15


class AlertRequest(BaseModel):

    tickers: List[str]
    drop_threshold: float = -5.0

# =========================================================
# DATABASE HELPERS
# =========================================================

def get_connection():

    return sqlite3.connect(DB_FILE)

# =========================================================
# MARKET DATA INGESTION
# =========================================================

@app.post("/api/v1/load-market-data")
async def load_market_data(
    req: MarketDataRequest
):

    try:

        final_dfs = []

        conn = get_connection()

        for ticker in req.tickers:

            df = yf.download(
                ticker,
                start=req.start_date,
                end=req.end_date,
                progress=False
            )

            if df.empty:
                continue

            df.reset_index(inplace=True)

            df["Ticker"] = ticker

            df = df[
                [
                    "Ticker",
                    "Date",
                    "Open",
                    "High",
                    "Low",
                    "Close",
                    "Volume"
                ]
            ]

            df.rename(
                columns={
                    "Date": "Datetime"
                },
                inplace=True
            )

            df["Datetime"] = (
                df["Datetime"]
                .astype(str)
            )

            final_dfs.append(df)

            records = df.to_records(
                index=False
            )

            conn.executemany("""
                INSERT OR IGNORE INTO historical_prices
                (
                    Ticker,
                    Datetime,
                    Open,
                    High,
                    Low,
                    Close,
                    Volume
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, records)

        conn.commit()
        conn.close()

        if not final_dfs:

            raise HTTPException(
                status_code=404,
                detail="No market data found."
            )

        merged_df = pd.concat(
            final_dfs,
            ignore_index=True
        )

        return {
            "status": "success",
            "rows_loaded": len(merged_df),
            "data":
                merged_df.to_dict(
                    orient="records"
                )
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# =========================================================
# ALERT ENGINE
# =========================================================

@app.post("/api/v1/alert-engine")
async def run_alert_engine(
    req: AlertRequest
):

    alerts = []

    try:

        conn = get_connection()

        for ticker in req.tickers:

            query = """
                SELECT *
                FROM historical_prices
                WHERE Ticker = ?
                ORDER BY Datetime ASC
            """

            df = pd.read_sql_query(
                query,
                conn,
                params=(ticker,)
            )

            if len(df) < 200:
                continue

            # =============================================
            # MOVING AVERAGES
            # =============================================

            df["SMA_50"] = (
                df["Close"]
                .rolling(window=50)
                .mean()
            )

            df["SMA_200"] = (
                df["Close"]
                .rolling(window=200)
                .mean()
            )

            yesterday_50 = df.iloc[-2]["SMA_50"]
            yesterday_200 = df.iloc[-2]["SMA_200"]

            today_50 = df.iloc[-1]["SMA_50"]
            today_200 = df.iloc[-1]["SMA_200"]

            # =============================================
            # GOLDEN / DEATH CROSS
            # =============================================

            if (
                yesterday_50 <= yesterday_200
                and
                today_50 > today_200
            ):

                alerts.append({
                    "ticker": ticker,
                    "type": "golden_cross",
                    "status":
                        "🌟 GOLDEN CROSS"
                })

            elif (
                yesterday_50 >= yesterday_200
                and
                today_50 < today_200
            ):

                alerts.append({
                    "ticker": ticker,
                    "type": "death_cross",
                    "status":
                        "☠️ DEATH CROSS"
                })

            # =============================================
            # PRICE DROP
            # =============================================

            latest_close = df.iloc[-1]["Close"]
            previous_close = df.iloc[-2]["Close"]

            price_change = (
                (
                    latest_close
                    -
                    previous_close
                )
                /
                previous_close
            ) * 100

            if price_change <= req.drop_threshold:

                alerts.append({
                    "ticker": ticker,
                    "type": "critical_drop",
                    "change":
                        round(price_change, 2),
                    "status":
                        "🚨 CRITICAL DROP"
                })

        conn.close()

        return {
            "alerts": alerts
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# =========================================================
# FORECAST ENGINE
# =========================================================

@app.post("/api/v1/forecast")
async def get_forecast(
    req: PredictRequest
):

    try:

        conn = get_connection()

        query = """
            SELECT
                Datetime as ds,
                Close as y
            FROM historical_prices
            WHERE Ticker = ?
            ORDER BY Datetime ASC
        """

        df = pd.read_sql_query(
            query,
            conn,
            params=(req.ticker,)
        )

        conn.close()

        if len(df) < 30:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Not enough historical "
                    "data for forecasting."
                )
            )

        df["ds"] = pd.to_datetime(
            df["ds"]
        )

        model = Prophet(
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=True
        )

        model.fit(df)

        future = (
            model.make_future_dataframe(
                periods=req.periods
            )
        )

        forecast = model.predict(
            future
        )

        forecast["ds"] = (
            forecast["ds"]
            .astype(str)
        )

        return {

            "historical":
                df.assign(
                    ds=df["ds"].astype(str)
                ).to_dict(
                    orient="records"
                ),

            "forecast":
                forecast[
                    [
                        "ds",
                        "yhat",
                        "yhat_lower",
                        "yhat_upper"
                    ]
                ].to_dict(
                    orient="records"
                )
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# =========================================================
# LIVE WEBSOCKET STREAM
# =========================================================

@app.websocket(
    "/api/v1/ws/stream/{ticker}"
)
async def live_ticker_stream(
    websocket: WebSocket,
    ticker: str
):

    await websocket.accept()

    print(
        f"🟢 Connected to {ticker}"
    )

    current_price = 150.0

    try:

        while True:

            shift = random.uniform(
                -0.5,
                0.5
            )

            current_price += shift

            tick_data = {

                "ticker": ticker,

                "price":
                    round(
                        current_price,
                        2
                    ),

                "trend":
                    (
                        "up"
                        if shift > 0
                        else "down"
                    ),

                "timestamp":
                    datetime.now()
                    .strftime(
                        "%H:%M:%S.%f"
                    )[:-3]
            }

            await websocket.send_json(
                tick_data
            )

            await asyncio.sleep(1)

    except WebSocketDisconnect:

        print(
            f"🔴 Disconnected: {ticker}"
        )

    except Exception as e:

        print(
            f"WebSocket Error: {e}"
        )

# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/")
async def root():

    return {
        "status": "online",
        "service":
            "Global Stock Intelligence API"
    }

# =========================================================
# MAIN
# =========================================================

# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    uvicorn.run(
        "backend_api:app",
        host="0.0.0.0",
        port=8000,  # <--- Change this from 8002 to 8000
        reload=True
    )
