from typing import Dict, List, Any, Optional, Type
import datetime
import logging

from .base import MarketDataProvider
from .models import Ticker, Trade, OrderBook, Candle


class DataService:
    """Main data service that manages different data providers."""
    
    def __init__(self):
        self.providers: Dict[str, MarketDataProvider] = {}
        self.logger = logging.getLogger(__name__)
    
    def register_provider(self, name: str, provider: MarketDataProvider):
        """Register a new market data provider."""
        self.providers[name] = provider
        self.logger.info(f"Registered market data provider: {name}")
    
    def get_provider(self, name: str) -> Optional[MarketDataProvider]:
        """Get a registered provider by name."""
        return self.providers.get(name)
    
    async def get_ticker(self, provider_name: str, symbol: str) -> Ticker:
        """Get ticker data from a specific provider."""
        provider = self.get_provider(provider_name)
        if not provider:
            raise ValueError(f"Provider not found: {provider_name}")
        
        data = await provider.get_ticker(symbol)
        return Ticker(
            symbol=data["symbol"],
            bid=data["bid"],
            ask=data["ask"],
            last=data["last"],
            volume_24h=data["volume"],
            timestamp=data["timestamp"],
            raw_data=data["raw_data"]
        )
    
    async def get_orderbook(self, provider_name: str, symbol: str, depth: int = 10) -> OrderBook:
        """Get order book from a specific provider."""
        provider = self.get_provider(provider_name)
        if not provider:
            raise ValueError(f"Provider not found: {provider_name}")
        
        data = await provider.get_orderbook(symbol, depth)
        return OrderBook(
            symbol=data["symbol"],
            bids=data["bids"],
            asks=data["asks"],
            timestamp=data["timestamp"],
            raw_data=data["raw_data"]
        )
    
    async def get_recent_trades(self, provider_name: str, symbol: str, limit: int = 100) -> List[Trade]:
        """Get recent trades from a specific provider."""
        provider = self.get_provider(provider_name)
        if not provider:
            raise ValueError(f"Provider not found: {provider_name}")
        
        trades_data = await provider.get_recent_trades(symbol, limit)
        return [
            Trade(
                symbol=t["symbol"],
                price=t["price"],
                amount=t["amount"],
                side=t["side"],
                timestamp=t["timestamp"],
                trade_id=t["trade_id"],
                raw_data=t["raw_data"]
            )
            for t in trades_data
        ]
    
    async def get_candles(self, provider_name: str, symbol: str, interval: str,
                         start_time: Optional[datetime.datetime] = None,
                         end_time: Optional[datetime.datetime] = None,
                         limit: int = 100) -> List[Candle]:
        """Get OHLCV candles from a specific provider."""
        provider = self.get_provider(provider_name)
        if not provider:
            raise ValueError(f"Provider not found: {provider_name}")
        
        candles_data = await provider.get_candles(symbol, interval, start_time, end_time, limit)
        return [
            Candle(
                symbol=c["symbol"],
                timestamp=c["timestamp"],
                open=c["open"],
                high=c["high"],
                low=c["low"],
                close=c["close"],
                volume=c["volume"],
                raw_data=c.get("raw_data")
            )
            for c in candles_data
        ]
    
    async def subscribe_ticker(self, provider_name: str, symbol: str, callback):
        """Subscribe to real-time ticker updates."""
        provider = self.get_provider(provider_name)
        if not provider:
            raise ValueError(f"Provider not found: {provider_name}")
        
        await provider.subscribe_ticker(symbol, callback)
    
    async def subscribe_orderbook(self, provider_name: str, symbol: str, callback):
        """Subscribe to real-time order book updates."""
        provider = self.get_provider(provider_name)
        if not provider:
            raise ValueError(f"Provider not found: {provider_name}")
        
        await provider.subscribe_orderbook(symbol, callback)
    
    async def subscribe_trades(self, provider_name: str, symbol: str, callback):
        """Subscribe to real-time trade updates."""
        provider = self.get_provider(provider_name)
        if not provider:
            raise ValueError(f"Provider not found: {provider_name}")
        
        await provider.subscribe_trades(symbol, callback)
    
    async def close_all(self):
        """Close all provider connections."""
        for name, provider in self.providers.items():
            try:
                await provider.close()
                self.logger.info(f"Closed connection to provider: {name}")
            except Exception as e:
                self.logger.error(f"Error closing provider {name}: {str(e)}")
