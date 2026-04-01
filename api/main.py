"""
api/main.py  —  FastAPI app with REST + WebSocket for live prices.
"""

import asyncio
import os

import yfinance as yf
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from api.route import router

app = FastAPI(title="QuantEdge API", version="2.0")

# Allow requests from React dev server and Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",       # Vite dev server
        "http://localhost:3000",
        "https://*.vercel.app",        # Vercel deployment
        os.getenv("FRONTEND_URL", ""), # custom domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
def root():
    return {"message": "QuantEdge API running", "docs": "/docs"}

# ─────────────────────────────────────────────────────────────────────────────
# WEBSOCKET  — push live prices every 5 seconds
# ─────────────────────────────────────────────────────────────────────────────

LIVE_SYMBOLS = ["TCS", "INFY", "RELIANCE", "HDFCBANK", "ICICIBANK",
                "SBIN", "ITC", "LT", "AXISBANK", "BAJFINANCE"]

async def fetch_prices_async():
    """Fetch latest prices in a thread pool so we don't block the event loop."""
    import concurrent.futures
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, _fetch_prices_sync)

def _fetch_prices_sync():
    prices = []
    for sym in LIVE_SYMBOLS:
        try:
            h = yf.Ticker(sym + ".NS").history(period="2d")
            if len(h) >= 2:
                p = round(float(h["Close"].iloc[-1]), 2)
                c = round((float(h["Close"].iloc[-1]) - float(h["Close"].iloc[-2])) / float(h["Close"].iloc[-2]) * 100, 2)
                prices.append({"symbol": sym, "price": p, "change_pct": c})
        except Exception:
            pass
    return prices

@app.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    """
    WebSocket endpoint.
    Sends live NSE prices every 5 seconds to connected clients.
    Connect from React with:  new WebSocket("ws://localhost:8000/ws/prices")
    """
    await websocket.accept()
    try:
        while True:
            prices = await fetch_prices_async()
            await websocket.send_json({"type": "prices", "data": prices})
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass