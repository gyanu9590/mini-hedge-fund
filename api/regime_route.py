"""
api/regime_route.py
Adds /regime endpoint to FastAPI so the React dashboard can show current regime.
Add  `from api.regime_route import regime_router`  and
     `app.include_router(regime_router)`  to api/main.py
"""

from fastapi import APIRouter, Depends
from api.route import _auth

regime_router = APIRouter()

@regime_router.get("/regime")
def get_regime(_k=Depends(_auth)):
    """
    Returns current market regime (BULL / BEAR / SIDEWAYS) and component signals.
    Reads from cache — no live fetch on every request.
    """
    try:
        from src.research.regime import get_cached_regime
        return get_cached_regime()
    except Exception as e:
        return {"regime": "UNKNOWN", "score": 0, "error": str(e)}

@regime_router.post("/regime/refresh")
def refresh_regime(_k=Depends(_auth)):
    """Force a fresh regime computation and cache update."""
    try:
        from src.research.regime import detect_regime
        result = detect_regime()
        return result
    except Exception as e:
        return {"error": str(e)}