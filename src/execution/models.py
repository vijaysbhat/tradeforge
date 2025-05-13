from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import datetime
from .base import OrderType, OrderSide, OrderStatus


@dataclass
class Balance:
    asset: str
    free: float
    locked: float
    total: float = field(init=False)
    
    def __post_init__(self):
        self.total = self.free + self.locked


@dataclass
class Account:
    id: str
    balances: List[Balance]
    raw_data: Dict[str, Any]


@dataclass
class Position:
    symbol: str
    quantity: float
    entry_price: float
    mark_price: float
    unrealized_pnl: float
    raw_data: Dict[str, Any]


@dataclass
class Order:
    id: str
    client_order_id: Optional[str]
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: float
    price: Optional[float]
    stop_price: Optional[float]
    status: OrderStatus
    created_at: datetime.datetime
    updated_at: datetime.datetime
    filled_quantity: float
    average_price: Optional[float]
    time_in_force: str
    raw_data: Dict[str, Any]


@dataclass
class Trade:
    id: str
    order_id: str
    symbol: str
    side: OrderSide
    price: float
    quantity: float
    commission: float
    commission_asset: str
    timestamp: datetime.datetime
    raw_data: Dict[str, Any]
