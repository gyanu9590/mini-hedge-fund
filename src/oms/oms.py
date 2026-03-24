"""
src/oms/oms.py

Order Management System (OMS).

Modes
-----
- PAPER  : logs orders, no real execution (default)
- LIVE   : routes to Zerodha Kite Connect (requires KiteConnect installed + credentials)

Set OMS_MODE=LIVE in .env to enable live trading.
"""

import logging
import os
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    NEW       = "NEW"
    SUBMITTED = "SUBMITTED"
    FILLED    = "FILLED"
    REJECTED  = "REJECTED"
    CANCELED  = "CANCELED"


class OrderSide(Enum):
    BUY  = "BUY"
    SELL = "SELL"


@dataclass
class Order:
    symbol: str
    qty:    int
    side:   OrderSide
    price:  float = 0.0
    status: OrderStatus = OrderStatus.NEW
    order_id: str = ""
    filled_qty: int = 0
    filled_price: float = 0.0
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "symbol":       self.symbol,
            "qty":          self.qty,
            "side":         self.side.value,
            "price":        self.price,
            "status":       self.status.value,
            "order_id":     self.order_id,
            "filled_qty":   self.filled_qty,
            "filled_price": self.filled_price,
            "notes":        self.notes,
        }


class PaperOMS:
    """Simulates order execution — logs everything, executes nothing."""

    def submit(self, order: Order) -> Order:
        logger.info(
            "[PAPER] %s %d × %s @ %.2f",
            order.side.value, order.qty, order.symbol, order.price,
        )
        order.status      = OrderStatus.FILLED
        order.filled_qty  = order.qty
        order.filled_price = order.price
        order.order_id    = f"PAPER-{order.symbol}-{order.qty}"
        return order

    def cancel(self, order: Order) -> Order:
        order.status = OrderStatus.CANCELED
        return order


class KiteOMS:
    """
    Live OMS via Zerodha Kite Connect.

    Requires:
        pip install kiteconnect
        KITE_API_KEY and KITE_ACCESS_TOKEN in .env
    """

    def __init__(self):
        try:
            from kiteconnect import KiteConnect
            self._kite = KiteConnect(api_key=os.environ["KITE_API_KEY"])
            self._kite.set_access_token(os.environ["KITE_ACCESS_TOKEN"])
            logger.info("Kite OMS initialized (LIVE mode)")
        except ImportError:
            raise RuntimeError("kiteconnect not installed. pip install kiteconnect")
        except KeyError as e:
            raise RuntimeError(f"Missing environment variable: {e}")

    def submit(self, order: Order) -> Order:
        try:
            kite_side = "BUY" if order.side == OrderSide.BUY else "SELL"
            order_id  = self._kite.place_order(
                tradingsymbol=order.symbol,
                exchange="NSE",
                transaction_type=kite_side,
                quantity=order.qty,
                order_type="MARKET",
                product="CNC",
                variety="regular",
            )
            order.status   = OrderStatus.SUBMITTED
            order.order_id = str(order_id)
            logger.info("[LIVE] Submitted order_id=%s for %s", order_id, order.symbol)
        except Exception as e:
            order.status = OrderStatus.REJECTED
            order.notes  = str(e)
            logger.error("[LIVE] Order rejected for %s: %s", order.symbol, e)
        return order

    def cancel(self, order: Order) -> Order:
        try:
            self._kite.cancel_order(variety="regular", order_id=order.order_id)
            order.status = OrderStatus.CANCELED
        except Exception as e:
            logger.error("Cancel failed for order %s: %s", order.order_id, e)
        return order


def get_oms():
    """Factory: returns PaperOMS or KiteOMS based on OMS_MODE env var."""
    mode = os.getenv("OMS_MODE", "PAPER").upper()
    if mode == "LIVE":
        return KiteOMS()
    return PaperOMS()