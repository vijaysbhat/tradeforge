from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import datetime
import enum


class OrderType(enum.Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(enum.Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(enum.Enum):
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Broker(ABC):
    """Base interface for all brokers."""
    
    @abstractmethod
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information including balances."""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions."""
        pass
    
    @abstractmethod
    async def place_order(self, symbol: str, side: OrderSide, order_type: OrderType, 
                         quantity: float, price: Optional[float] = None,
                         time_in_force: str = "GTC", **kwargs) -> Dict[str, Any]:
        """Place a new order."""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an existing order."""
        pass
    
    @abstractmethod
    async def get_order(self, order_id: str) -> Dict[str, Any]:
        """Get information about a specific order."""
        pass
    
    @abstractmethod
    async def get_orders(self, symbol: Optional[str] = None, status: Optional[OrderStatus] = None) -> List[Dict[str, Any]]:
        """Get all orders, optionally filtered by symbol and status."""
        pass
    
    @abstractmethod
    async def get_order_history(self, symbol: Optional[str] = None, 
                               start_time: Optional[datetime.datetime] = None,
                               end_time: Optional[datetime.datetime] = None,
                               limit: int = 100) -> List[Dict[str, Any]]:
        """Get historical orders."""
        pass
    
    @abstractmethod
    async def get_trades(self, symbol: Optional[str] = None,
                        start_time: Optional[datetime.datetime] = None,
                        end_time: Optional[datetime.datetime] = None,
                        limit: int = 100) -> List[Dict[str, Any]]:
        """Get trade history."""
        pass
