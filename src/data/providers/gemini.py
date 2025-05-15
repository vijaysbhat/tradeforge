import aiohttp
import asyncio
import datetime
import json
import hmac
import base64
import hashlib
import time
from typing import Dict, List, Any, Optional, Callable

from ..base import MarketDataProvider
from ..models import Ticker, Trade, OrderBook, OrderBookEntry, Candle


class GeminiDataProvider(MarketDataProvider):
    """Gemini market data provider implementation."""
    
    def __init__(self, api_key: str = None, api_secret: str = None, sandbox: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.sandbox = sandbox
        
        # Set the base URL based on sandbox mode
        if sandbox:
            self.rest_url = "https://api.sandbox.gemini.com"
            self.ws_url = "wss://api.sandbox.gemini.com/v1/marketdata"
        else:
            self.rest_url = "https://api.gemini.com"
            self.ws_url = "wss://api.gemini.com/v1/marketdata"
            
        self.session = None
        self.ws_connections = {}
    
    async def _ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def _make_request(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        await self._ensure_session()
        url = f"{self.rest_url}{endpoint}"
        
        async with self.session.get(url, params=params) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Gemini API error: {response.status} - {error_text}")
            return await response.json()
    
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        data = await self._make_request(f"/v1/pubticker/{symbol}")
        return {
            "symbol": symbol,
            "bid": float(data.get("bid", 0)),
            "ask": float(data.get("ask", 0)),
            "last": float(data.get("last", 0)),
            "volume": float(data.get("volume", {}).get("USD", 0)),
            "timestamp": datetime.datetime.fromtimestamp(float(data.get("volume", {}).get("timestamp", 0))/1000),
            "raw_data": data
        }
    
    async def get_orderbook(self, symbol: str, depth: int = 10) -> Dict[str, Any]:
        data = await self._make_request(f"/v1/book/{symbol}", {"limit_bids": depth, "limit_asks": depth})
        
        bids = [OrderBookEntry(float(bid["price"]), float(bid["amount"])) for bid in data.get("bids", [])]
        asks = [OrderBookEntry(float(ask["price"]), float(ask["amount"])) for ask in data.get("asks", [])]
        
        return {
            "symbol": symbol,
            "bids": bids,
            "asks": asks,
            "timestamp": datetime.datetime.now(),
            "raw_data": data
        }
    
    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        # Ensure limit is within Gemini's acceptable range (max 500)
        if limit > 500:
            limit = 500
            
        data = await self._make_request(f"/v1/trades/{symbol}", {"limit_trades": limit})
        
        trades = []
        for trade in data:
            trades.append({
                "symbol": symbol,
                "price": float(trade.get("price", 0)),
                "amount": float(trade.get("amount", 0)),
                "side": "buy" if trade.get("type") == "buy" else "sell",
                "timestamp": datetime.datetime.fromtimestamp(trade.get("timestamp", 0)),
                "trade_id": str(trade.get("tid", "")),
                "raw_data": trade
            })
        
        return trades
    
    async def get_candles(self, symbol: str, interval: str = "1m", 
                         start_time: Optional[datetime.datetime] = None,
                         end_time: Optional[datetime.datetime] = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        # Gemini doesn't have a direct candle API, so we'd need to build candles from trades
        # This is a simplified implementation
        trades = await self.get_recent_trades(symbol, 500)  # Get more trades to build accurate candles
        
        # Convert interval string to seconds
        interval_seconds = self._interval_to_seconds(interval)
        
        # Group trades by time interval and create candles
        candles = []
        if trades:
            # Sort trades by timestamp
            trades.sort(key=lambda x: x["timestamp"])
            
            # Set start and end times
            if start_time is None:
                start_time = trades[0]["timestamp"]
            if end_time is None:
                end_time = trades[-1]["timestamp"]
            
            # Group trades into candles
            current_time = start_time
            while current_time < end_time and len(candles) < limit:
                next_time = current_time + datetime.timedelta(seconds=interval_seconds)
                
                # Filter trades in this time interval
                interval_trades = [t for t in trades if current_time <= t["timestamp"] < next_time]
                
                if interval_trades:
                    prices = [t["price"] for t in interval_trades]
                    volumes = [t["amount"] for t in interval_trades]
                    
                    candle = {
                        "symbol": symbol,
                        "timestamp": current_time,
                        "open": interval_trades[0]["price"],
                        "high": max(prices),
                        "low": min(prices),
                        "close": interval_trades[-1]["price"],
                        "volume": sum(volumes)
                    }
                    candles.append(candle)
                
                current_time = next_time
        
        return candles
    
    def _interval_to_seconds(self, interval: str) -> int:
        """Convert interval string like '1m', '1h', '1d' to seconds."""
        unit = interval[-1]
        value = int(interval[:-1])
        
        if unit == 'm':
            return value * 60
        elif unit == 'h':
            return value * 60 * 60
        elif unit == 'd':
            return value * 24 * 60 * 60
        else:
            raise ValueError(f"Unsupported interval: {interval}")
    
    async def subscribe_ticker(self, symbol: str, callback: Callable):
        await self._subscribe_websocket(symbol, ["ticker"], callback)
    
    async def subscribe_orderbook(self, symbol: str, callback: Callable):
        await self._subscribe_websocket(symbol, ["book"], callback)
    
    async def subscribe_trades(self, symbol: str, callback: Callable):
        await self._subscribe_websocket(symbol, ["trades"], callback)
    
    async def _subscribe_websocket(self, symbol: str, channels: List[str], callback: Callable):
        """Subscribe to Gemini websocket for real-time updates."""
        connection_key = f"{symbol}_{','.join(channels)}"
        
        if connection_key in self.ws_connections:
            return
        
        ws_url = f"{self.ws_url}/{symbol}?heartbeat=true"
        
        async def _ws_handler():
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(ws_url) as ws:
                    self.ws_connections[connection_key] = ws
                    
                    # Subscribe to specified channels
                    for channel in channels:
                        await ws.send_json({
                            "type": "subscribe",
                            "subscriptions": [{"name": channel}]
                        })
                    
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            # Call callback without awaiting it
                            try:
                                callback(data)
                            except Exception as e:
                                print(f"Error in callback: {e}")
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            print(f"WebSocket error: {msg}")
                            break
        
        # Start the WebSocket connection in the background
        asyncio.create_task(_ws_handler())
    
    async def close(self):
        """Close all connections."""
        if self.session and not self.session.closed:
            await self.session.close()
        
        for key, ws in self.ws_connections.items():
            if not ws.closed:
                await ws.close()
        
        self.ws_connections = {}
