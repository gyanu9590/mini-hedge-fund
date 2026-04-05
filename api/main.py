"""
api/main.py  —  FastAPI app with REST + WebSocket for live prices.
WebSocket covers full Nifty50 universe, not just 5 symbols.
"""

import asyncio
import os

import yaml
import yfinance as yf
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware


from api.route import router

app = FastAPI(title="QuantEdge API", version="2.0")
from api.regime_route import regime_router
app.include_router(regime_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://*.vercel.app",
        os.getenv("FRONTEND_URL", ""),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
def root():
    return {"message": "QuantEdge API running", "docs": "/docs"}


def _load_universe() -> list[str]:
    """Read full symbol universe from settings.yaml."""
    try:
        with open("configs/settings.yaml") as f:
            cfg = yaml.safe_load(f)
        return [s.replace("NSE:", "").strip() for s in cfg.get("universe", [])]
    except Exception:
        return [
            "TCS", "INFY", "RELIANCE", "HDFCBANK", "ICICIBANK",
            "SBIN", "ITC", "LT", "AXISBANK", "BAJFINANCE",
            "ADANIENT", "ADANIPORTS", "ASIANPAINT", "WIPRO",
            "TITAN", "ULTRACEMCO", "POWERGRID", "NTPC", "MARUTI", "HINDUNILVR",
        ]


def _fetch_prices_sync() -> list[dict]:
    """Fetch latest price + daily change for every symbol in the universe."""
    symbols = _load_universe()
    prices = []
    for sym in symbols:
        try:
            h = yf.Ticker(sym + ".NS").history(period="2d")
            if len(h) >= 2:
                latest = float(h["Close"].iloc[-1])
                prev   = float(h["Close"].iloc[-2])
                chg    = round((latest - prev) / prev * 100, 2)
                prices.append({
                    "symbol":     sym,
                    "price":      round(latest, 2),
                    "change_pct": chg,
                })
        except Exception:
            pass
    return prices


async def _fetch_prices_async() -> list[dict]:
    import concurrent.futures
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, _fetch_prices_sync)


@app.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    """
    Sends live NSE prices for ALL universe symbols every 10 seconds.
    Covers the full 20-stock universe so Orders P&L works for every symbol.
    """
    await websocket.accept()
    try:
        while True:
            prices = await _fetch_prices_async()
            await websocket.send_json({"type": "prices", "data": prices})
            await asyncio.sleep(10)   # 10s interval — full universe takes a few seconds to fetch
    except WebSocketDisconnect:
        pass
    except Exception:
        pass