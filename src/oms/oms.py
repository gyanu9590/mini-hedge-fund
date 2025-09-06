from enum import Enum
class Status(Enum):
    NEW='NEW'; WORKING='WORKING'; FILLED='FILLED'; CANCELED='CANCELED'
class Order:
    def __init__(self, symbol, qty, side):
        self.symbol=symbol; self.qty=qty; self.side=side; self.status=Status.NEW
    def to_dict(self):
        return {'symbol': self.symbol, 'qty': self.qty, 'side': self.side, 'status': self.status.value}
