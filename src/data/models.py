from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import datetime


@dataclass
class Ticker:
    symbol: str
    bid: float
    ask: float
    last: float
    volume_24h: float
    timestamp: datetime.datetime
    raw_data: Dict[str, Any]  # Store the original response


@dataclass
class Trade:
    symbol: str
    price: float
    amount: float
    side: str  # 'buy' or 'sell'
    timestamp: datetime.datetime
    trade_id: str
    raw_data: Dict[str, Any]


@dataclass
class OrderBookEntry:
    price: float
    amount: float


@dataclass
class OrderBook:
    symbol: str
    bids: List[OrderBookEntry]
    asks: List[OrderBookEntry]
    timestamp: datetime.datetime
    raw_data: Dict[str, Any]


@dataclass
class Candle:
    symbol: str
    timestamp: datetime.datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    raw_data: Optional[Dict[str, Any]] = None
