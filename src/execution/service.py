from typing import Dict, List, Any, Optional, Type
import datetime
import logging

from .base import Broker, OrderType, OrderSide, OrderStatus
from .models import Account, Position, Order, Trade


class ExecutionService:
    """Main execution service that manages different brokers."""
    
    def __init__(self):
        self.brokers: Dict[str, Broker] = {}
        self.logger = logging.getLogger(__name__)
    
    def register_broker(self, name: str, broker: Broker):
        """Register a new broker."""
        self.brokers[name] = broker
        self.logger.info(f"Registered broker: {name}")
    
    def get_broker(self, name: str) -> Optional[Broker]:
        """Get a registered broker by name."""
        return self.brokers.get(name)
    
    async def get_account_info(self, broker_name: str) -> Account:
        """Get account information from a specific broker."""
        broker = self.get_broker(broker_name)
        if not broker:
            raise ValueError(f"Broker not found: {broker_name}")
        
        data = await broker.get_account_info()
        return Account(
            id=data["id"],
            balances=data["balances"],
            raw_data=data["raw_data"]
        )
    
    async def get_positions(self, broker_name: str) -> List[Position]:
        """Get positions from a specific broker."""
        broker = self.get_broker(broker_name)
        if not broker:
            raise ValueError(f"Broker not found: {broker_name}")
        
        positions_data = await broker.get_positions()
        return [
            Position(
                symbol=p["symbol"],
                quantity=p["quantity"],
                entry_price=p["entry_price"],
                mark_price=p["mark_price"],
                unrealized_pnl=p["unrealized_pnl"],
                raw_data=p["raw_data"]
            )
            for p in positions_data
        ]
    
    async def place_order(self, broker_name: str, symbol: str, side: OrderSide, order_type: OrderType, 
                         quantity: float, price: Optional[float] = None,
                         time_in_force: str = "GTC", **kwargs) -> Order:
        """Place an order with a specific broker."""
        broker = self.get_broker(broker_name)
        if not broker:
            raise ValueError(f"Broker not found: {broker_name}")
        
        order_data = await broker.place_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            time_in_force=time_in_force,
            **kwargs
        )
        
        return Order(
            id=order_data["id"],
            client_order_id=order_data["client_order_id"],
            symbol=order_data["symbol"],
            side=order_data["side"],
            type=order_data["type"],
            quantity=order_data["quantity"],
            price=order_data["price"],
            stop_price=order_data["stop_price"],
            status=order_data["status"],
            created_at=order_data["created_at"],
            updated_at=order_data["updated_at"],
            filled_quantity=order_data["filled_quantity"],
            average_price=order_data["average_price"],
            time_in_force=order_data["time_in_force"],
            raw_data=order_data["raw_data"]
        )
    
    async def cancel_order(self, broker_name: str, order_id: str) -> Order:
        """Cancel an order with a specific broker."""
        broker = self.get_broker(broker_name)
        if not broker:
            raise ValueError(f"Broker not found: {broker_name}")
        
        order_data = await broker.cancel_order(order_id)
        
        return Order(
            id=order_data["id"],
            client_order_id=order_data["client_order_id"],
            symbol=order_data["symbol"],
            side=order_data["side"],
            type=order_data["type"],
            quantity=order_data["quantity"],
            price=order_data["price"],
            stop_price=order_data["stop_price"],
            status=order_data["status"],
            created_at=order_data["created_at"],
            updated_at=order_data["updated_at"],
            filled_quantity=order_data["filled_quantity"],
            average_price=order_data["average_price"],
            time_in_force=order_data["time_in_force"],
            raw_data=order_data["raw_data"]
        )
    
    async def get_order(self, broker_name: str, order_id: str) -> Order:
        """Get information about a specific order."""
        broker = self.get_broker(broker_name)
        if not broker:
            raise ValueError(f"Broker not found: {broker_name}")
        
        order_data = await broker.get_order(order_id)
        
        return Order(
            id=order_data["id"],
            client_order_id=order_data["client_order_id"],
            symbol=order_data["symbol"],
            side=order_data["side"],
            type=order_data["type"],
            quantity=order_data["quantity"],
            price=order_data["price"],
            stop_price=order_data["stop_price"],
            status=order_data["status"],
            created_at=order_data["created_at"],
            updated_at=order_data["updated_at"],
            filled_quantity=order_data["filled_quantity"],
            average_price=order_data["average_price"],
            time_in_force=order_data["time_in_force"],
            raw_data=order_data["raw_data"]
        )
    
    async def get_orders(self, broker_name: str, symbol: Optional[str] = None, 
                        status: Optional[OrderStatus] = None) -> List[Order]:
        """Get all orders, optionally filtered by symbol and status."""
        broker = self.get_broker(broker_name)
        if not broker:
            raise ValueError(f"Broker not found: {broker_name}")
        
        orders_data = await broker.get_orders(symbol, status)
        
        return [
            Order(
                id=o["id"],
                client_order_id=o["client_order_id"],
                symbol=o["symbol"],
                side=o["side"],
                type=o["type"],
                quantity=o["quantity"],
                price=o["price"],
                stop_price=o["stop_price"],
                status=o["status"],
                created_at=o["created_at"],
                updated_at=o["updated_at"],
                filled_quantity=o["filled_quantity"],
                average_price=o["average_price"],
                time_in_force=o["time_in_force"],
                raw_data=o["raw_data"]
            )
            for o in orders_data
        ]
    
    async def get_order_history(self, broker_name: str, symbol: Optional[str] = None,
                               start_time: Optional[datetime.datetime] = None,
                               end_time: Optional[datetime.datetime] = None,
                               limit: int = 100) -> List[Order]:
        """Get historical orders."""
        broker = self.get_broker(broker_name)
        if not broker:
            raise ValueError(f"Broker not found: {broker_name}")
        
        orders_data = await broker.get_order_history(symbol, start_time, end_time, limit)
        
        return [
            Order(
                id=o["id"],
                client_order_id=o["client_order_id"],
                symbol=o["symbol"],
                side=o["side"],
                type=o["type"],
                quantity=o["quantity"],
                price=o["price"],
                stop_price=o["stop_price"],
                status=o["status"],
                created_at=o["created_at"],
                updated_at=o["updated_at"],
                filled_quantity=o["filled_quantity"],
                average_price=o["average_price"],
                time_in_force=o["time_in_force"],
                raw_data=o["raw_data"]
            )
            for o in orders_data
        ]
    
    async def get_trades(self, broker_name: str, symbol: Optional[str] = None,
                        start_time: Optional[datetime.datetime] = None,
                        end_time: Optional[datetime.datetime] = None,
                        limit: int = 100) -> List[Trade]:
        """Get trade history."""
        broker = self.get_broker(broker_name)
        if not broker:
            raise ValueError(f"Broker not found: {broker_name}")
        
        trades_data = await broker.get_trades(symbol, start_time, end_time, limit)
        
        return [
            Trade(
                id=t["id"],
                order_id=t["order_id"],
                symbol=t["symbol"],
                side=t["side"],
                price=t["price"],
                quantity=t["quantity"],
                commission=t["commission"],
                commission_asset=t["commission_asset"],
                timestamp=t["timestamp"],
                raw_data=t["raw_data"]
            )
            for t in trades_data
        ]
    
    async def close_all(self):
        """Close all broker connections."""
        for name, broker in self.brokers.items():
            try:
                await broker.close()
                self.logger.info(f"Closed connection to broker: {name}")
            except Exception as e:
                self.logger.error(f"Error closing broker {name}: {str(e)}")
