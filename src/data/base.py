from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import datetime


class MarketDataProvider(ABC):
    """Base interface for all market data providers."""
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get current ticker information for a symbol."""
        pass
    
    @abstractmethod
    async def get_orderbook(self, symbol: str, depth: int = 10) -> Dict[str, Any]:
        """Get order book for a symbol with specified depth."""
        pass
    
    @abstractmethod
    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent trades for a symbol."""
        pass
    
    @abstractmethod
    async def get_candles(self, symbol: str, interval: str, 
                         start_time: Optional[datetime.datetime] = None,
                         end_time: Optional[datetime.datetime] = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        """Get OHLCV candles for a symbol."""
        pass
    
    @abstractmethod
    async def subscribe_ticker(self, symbol: str, callback):
        """Subscribe to real-time ticker updates."""
        pass
    
    @abstractmethod
    async def subscribe_orderbook(self, symbol: str, callback):
        """Subscribe to real-time order book updates."""
        pass
    
    @abstractmethod
    async def subscribe_trades(self, symbol: str, callback):
        """Subscribe to real-time trade updates."""
        pass
