import aiohttp
import asyncio
import datetime
import json
import hmac
import base64
import hashlib
import time
from typing import Dict, List, Any, Optional

from ..base import Broker, OrderType, OrderSide, OrderStatus
from ..models import Balance, Account, Position, Order, Trade


class GeminiBroker(Broker):
    """Gemini broker implementation."""
    
    def __init__(self, api_key: str, api_secret: str, sandbox: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.sandbox = sandbox
        
        # Set the base URL based on sandbox mode
        if sandbox:
            self.base_url = "https://api.sandbox.gemini.com"
        else:
            self.base_url = "https://api.gemini.com"
            
        self.session = None
    
    async def _ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def _make_public_request(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        await self._ensure_session()
        url = f"{self.base_url}{endpoint}"
        
        async with self.session.get(url, params=params) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Gemini API error: {response.status} - {error_text}")
            return await response.json()
    
    async def _make_private_request(self, endpoint: str, payload: Dict = None) -> Dict[str, Any]:
        await self._ensure_session()
        url = f"{self.base_url}{endpoint}"
        
        if payload is None:
            payload = {}
        
        # Add required fields to payload
        payload["request"] = endpoint
        
        # Gemini API expects nonce in microseconds
        # The error shows server expects seconds, not milliseconds
        payload["nonce"] = str(int(time.time()))  # Use seconds since epoch as nonce
        
        # Encode payload as JSON and then as base64
        encoded_payload = base64.b64encode(json.dumps(payload).encode())
        
        # Create signature
        signature = hmac.new(self.api_secret.encode(), encoded_payload, hashlib.sha384).hexdigest()
        
        # Create headers
        headers = {
            "Content-Type": "text/plain",
            "X-GEMINI-APIKEY": self.api_key,
            "X-GEMINI-PAYLOAD": encoded_payload.decode(),
            "X-GEMINI-SIGNATURE": signature,
            "Cache-Control": "no-cache"
        }
        
        try:
            async with self.session.post(url, headers=headers) as response:
                response_text = await response.text()
                if response.status != 200:
                    # Check for nonce error and provide a more helpful message
                    if "Nonce" in response_text and "not within" in response_text:
                        raise Exception(f"Gemini API nonce error. Please check your system clock synchronization. Error: {response_text}")
                    raise Exception(f"Gemini API error: {response.status} - {response_text}")
                
                return json.loads(response_text)
        except aiohttp.ClientError as e:
            raise Exception(f"Network error when connecting to Gemini API: {str(e)}")
    
    async def get_account_info(self) -> Dict[str, Any]:
        data = await self._make_private_request("/v1/account")
        
        balances = []
        for balance in data.get("balances", []):
            balances.append(Balance(
                asset=balance.get("currency", ""),
                free=float(balance.get("available", 0)),
                locked=float(balance.get("amount", 0)) - float(balance.get("available", 0))
            ))
        
        return {
            "id": data.get("account", {}).get("id", ""),
            "balances": balances,
            "raw_data": data
        }
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        # Gemini doesn't have a direct positions API for spot trading
        # For spot trading, we can derive positions from balances
        account_info = await self.get_account_info()
        
        positions = []
        for balance in account_info["balances"]:
            if balance.total > 0:
                # For crypto assets, we need to get the current price
                # This is a simplified implementation
                positions.append({
                    "symbol": balance.asset,
                    "quantity": balance.total,
                    "entry_price": 0,  # Not available in Gemini
                    "mark_price": 0,   # Would need to fetch current price
                    "unrealized_pnl": 0,  # Would need to calculate
                    "raw_data": {"balance": balance.__dict__}
                })
        
        return positions
    
    async def place_order(self, symbol: str, side: OrderSide, order_type: OrderType, 
                         quantity: float, price: Optional[float] = None,
                         time_in_force: str = "GTC", **kwargs) -> Dict[str, Any]:
        # Map our order types to Gemini order types
        # Gemini uses different order type format than some other exchanges
        gemini_order_types = {
            OrderType.MARKET: "market",
            OrderType.LIMIT: "exchange limit",
            # Gemini doesn't directly support stop orders in the same way
            OrderType.STOP: "stop",
            OrderType.STOP_LIMIT: "stop_limit"
        }
        
        payload = {
            "symbol": symbol,
            "amount": str(quantity),
            "side": side.value,
            "type": gemini_order_types.get(order_type, "exchange limit")
        }
        
        if order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT] and price is not None:
            payload["price"] = str(price)
        
        if order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and "stop_price" in kwargs:
            payload["stop_price"] = str(kwargs["stop_price"])
        
        # Add client order ID if provided
        if "client_order_id" in kwargs:
            payload["client_order_id"] = kwargs["client_order_id"]
        
        data = await self._make_private_request("/v1/order/new", payload)
        
        # Map Gemini order status to our OrderStatus
        status_map = {
            "accepted": OrderStatus.OPEN,
            "live": OrderStatus.OPEN,
            "cancelled": OrderStatus.CANCELED,
            "fill": OrderStatus.FILLED,
            "partially filled": OrderStatus.PARTIALLY_FILLED,
            "rejected": OrderStatus.REJECTED
        }
        
        return {
            "id": str(data.get("order_id", "")),
            "client_order_id": data.get("client_order_id", ""),
            "symbol": data.get("symbol", ""),
            "side": OrderSide(data.get("side", "")),
            "type": order_type,
            "quantity": float(data.get("original_amount", 0)),
            "price": float(data.get("price", 0)) if data.get("price") else None,
            "stop_price": float(kwargs.get("stop_price", 0)) if "stop_price" in kwargs else None,
            "status": status_map.get(data.get("is_live", False), OrderStatus.PENDING),
            "created_at": datetime.datetime.fromtimestamp(data.get("timestampms", 0)/1000),
            "updated_at": datetime.datetime.fromtimestamp(data.get("timestampms", 0)/1000),
            "filled_quantity": float(data.get("executed_amount", 0)),
            "average_price": float(data.get("avg_execution_price", 0)) if data.get("avg_execution_price") else None,
            "time_in_force": time_in_force,
            "raw_data": data
        }
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        payload = {
            "order_id": int(order_id)
        }
        
        data = await self._make_private_request("/v1/order/cancel", payload)
        
        # Map Gemini order status to our OrderStatus
        status_map = {
            "accepted": OrderStatus.OPEN,
            "live": OrderStatus.OPEN,
            "cancelled": OrderStatus.CANCELED,
            "fill": OrderStatus.FILLED,
            "partially filled": OrderStatus.PARTIALLY_FILLED,
            "rejected": OrderStatus.REJECTED
        }
        
        return {
            "id": str(data.get("order_id", "")),
            "client_order_id": data.get("client_order_id", ""),
            "symbol": data.get("symbol", ""),
            "side": OrderSide(data.get("side", "")),
            "type": OrderType.LIMIT,  # Default as Gemini doesn't return this
            "quantity": float(data.get("original_amount", 0)),
            "price": float(data.get("price", 0)) if data.get("price") else None,
            "stop_price": None,
            "status": status_map.get(data.get("is_cancelled", True), OrderStatus.CANCELED),
            "created_at": datetime.datetime.fromtimestamp(data.get("timestampms", 0)/1000),
            "updated_at": datetime.datetime.fromtimestamp(data.get("timestampms", 0)/1000),
            "filled_quantity": float(data.get("executed_amount", 0)),
            "average_price": float(data.get("avg_execution_price", 0)) if data.get("avg_execution_price") else None,
            "time_in_force": "GTC",  # Default as Gemini doesn't return this
            "raw_data": data
        }
    
    async def get_order(self, order_id: str) -> Dict[str, Any]:
        payload = {
            "order_id": int(order_id)
        }
        
        data = await self._make_private_request("/v1/order/status", payload)
        
        # Map Gemini order status to our OrderStatus
        status_map = {
            "accepted": OrderStatus.OPEN,
            "live": OrderStatus.OPEN,
            "cancelled": OrderStatus.CANCELED,
            "fill": OrderStatus.FILLED,
            "partially filled": OrderStatus.PARTIALLY_FILLED,
            "rejected": OrderStatus.REJECTED
        }
        
        # Determine order status
        order_status = OrderStatus.PENDING
        if data.get("is_cancelled", False):
            order_status = OrderStatus.CANCELED
        elif data.get("is_live", False):
            order_status = OrderStatus.OPEN
        elif float(data.get("remaining_amount", 0)) == 0:
            order_status = OrderStatus.FILLED
        elif float(data.get("executed_amount", 0)) > 0:
            order_status = OrderStatus.PARTIALLY_FILLED
        
        return {
            "id": str(data.get("order_id", "")),
            "client_order_id": data.get("client_order_id", ""),
            "symbol": data.get("symbol", ""),
            "side": OrderSide(data.get("side", "")),
            "type": OrderType.LIMIT,  # Default as Gemini doesn't return this
            "quantity": float(data.get("original_amount", 0)),
            "price": float(data.get("price", 0)) if data.get("price") else None,
            "stop_price": None,
            "status": order_status,
            "created_at": datetime.datetime.fromtimestamp(data.get("timestampms", 0)/1000),
            "updated_at": datetime.datetime.fromtimestamp(data.get("timestampms", 0)/1000),
            "filled_quantity": float(data.get("executed_amount", 0)),
            "average_price": float(data.get("avg_execution_price", 0)) if data.get("avg_execution_price") else None,
            "time_in_force": "GTC",  # Default as Gemini doesn't return this
            "raw_data": data
        }
    
    async def get_orders(self, symbol: Optional[str] = None, status: Optional[OrderStatus] = None) -> List[Dict[str, Any]]:
        # Get active orders
        data = await self._make_private_request("/v1/orders")
        
        orders = []
        for order_data in data:
            # Filter by symbol if specified
            if symbol and order_data.get("symbol", "") != symbol:
                continue
            
            # Determine order status
            order_status = OrderStatus.PENDING
            if order_data.get("is_cancelled", False):
                order_status = OrderStatus.CANCELED
            elif order_data.get("is_live", False):
                order_status = OrderStatus.OPEN
            elif float(order_data.get("remaining_amount", 0)) == 0:
                order_status = OrderStatus.FILLED
            elif float(order_data.get("executed_amount", 0)) > 0:
                order_status = OrderStatus.PARTIALLY_FILLED
            
            # Filter by status if specified
            if status and order_status != status:
                continue
            
            orders.append({
                "id": str(order_data.get("order_id", "")),
                "client_order_id": order_data.get("client_order_id", ""),
                "symbol": order_data.get("symbol", ""),
                "side": OrderSide(order_data.get("side", "")),
                "type": OrderType.LIMIT,  # Default as Gemini doesn't return this
                "quantity": float(order_data.get("original_amount", 0)),
                "price": float(order_data.get("price", 0)) if order_data.get("price") else None,
                "stop_price": None,
                "status": order_status,
                "created_at": datetime.datetime.fromtimestamp(order_data.get("timestampms", 0)/1000),
                "updated_at": datetime.datetime.fromtimestamp(order_data.get("timestampms", 0)/1000),
                "filled_quantity": float(order_data.get("executed_amount", 0)),
                "average_price": float(order_data.get("avg_execution_price", 0)) if order_data.get("avg_execution_price") else None,
                "time_in_force": "GTC",  # Default as Gemini doesn't return this
                "raw_data": order_data
            })
        
        return orders
    
    async def get_order_history(self, symbol: Optional[str] = None, 
                               start_time: Optional[datetime.datetime] = None,
                               end_time: Optional[datetime.datetime] = None,
                               limit: int = 100) -> List[Dict[str, Any]]:
        # Gemini's past trades endpoint can be used for order history
        payload = {
            "limit_trades": limit
        }
        
        if symbol:
            payload["symbol"] = symbol
        
        if start_time:
            payload["timestamp"] = int(start_time.timestamp())
        
        data = await self._make_private_request("/v1/mytrades", payload)
        
        orders = {}
        for trade in data:
            order_id = str(trade.get("order_id", ""))
            
            # Skip if outside time range
            trade_time = datetime.datetime.fromtimestamp(trade.get("timestamp", 0))
            if end_time and trade_time > end_time:
                continue
            
            # Group trades by order_id to reconstruct orders
            if order_id not in orders:
                orders[order_id] = {
                    "id": order_id,
                    "client_order_id": "",  # Not available in trade history
                    "symbol": trade.get("symbol", ""),
                    "side": OrderSide(trade.get("type", "")),
                    "type": OrderType.LIMIT,  # Default as Gemini doesn't return this
                    "quantity": 0,  # Will accumulate
                    "price": float(trade.get("price", 0)),
                    "stop_price": None,
                    "status": OrderStatus.FILLED,  # Assuming filled since it's in trade history
                    "created_at": trade_time,
                    "updated_at": trade_time,
                    "filled_quantity": 0,  # Will accumulate
                    "average_price": 0,  # Will calculate
                    "time_in_force": "GTC",  # Default
                    "raw_data": {"trades": []}
                }
            
            # Update order with trade information
            orders[order_id]["filled_quantity"] += float(trade.get("amount", 0))
            orders[order_id]["quantity"] += float(trade.get("amount", 0))
            orders[order_id]["raw_data"]["trades"].append(trade)
            
            # Update timestamp if this trade is more recent
            if trade_time > orders[order_id]["updated_at"]:
                orders[order_id]["updated_at"] = trade_time
        
        # Calculate average price for each order
        for order_id, order in orders.items():
            total_cost = 0
            total_quantity = 0
            
            for trade in order["raw_data"]["trades"]:
                price = float(trade.get("price", 0))
                amount = float(trade.get("amount", 0))
                total_cost += price * amount
                total_quantity += amount
            
            if total_quantity > 0:
                order["average_price"] = total_cost / total_quantity
        
        return list(orders.values())
    
    async def get_trades(self, symbol: Optional[str] = None,
                        start_time: Optional[datetime.datetime] = None,
                        end_time: Optional[datetime.datetime] = None,
                        limit: int = 100) -> List[Dict[str, Any]]:
        payload = {
            "limit_trades": limit
        }
        
        if symbol:
            payload["symbol"] = symbol
        
        if start_time:
            payload["timestamp"] = int(start_time.timestamp())
        
        data = await self._make_private_request("/v1/mytrades", payload)
        
        trades = []
        for trade_data in data:
            trade_time = datetime.datetime.fromtimestamp(trade_data.get("timestamp", 0))
            
            # Skip if outside time range
            if end_time and trade_time > end_time:
                continue
            
            trades.append({
                "id": str(trade_data.get("tid", "")),
                "order_id": str(trade_data.get("order_id", "")),
                "symbol": trade_data.get("symbol", ""),
                "side": OrderSide(trade_data.get("type", "")),
                "price": float(trade_data.get("price", 0)),
                "quantity": float(trade_data.get("amount", 0)),
                "commission": float(trade_data.get("fee_amount", 0)),
                "commission_asset": trade_data.get("fee_currency", ""),
                "timestamp": trade_time,
                "raw_data": trade_data
            })
        
        return trades
    
    async def close(self):
        """Close the session."""
        if self.session and not self.session.closed:
            await self.session.close()
