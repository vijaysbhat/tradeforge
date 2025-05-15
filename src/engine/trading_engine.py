import asyncio
import datetime
import logging
import time
from typing import Dict, List, Any, Optional, Set, Callable

from ..data.service import DataService
from ..data.models import Ticker, OrderBook, Trade, Candle, OrderBookEntry
from ..execution.service import ExecutionService
from ..execution.base import OrderSide, OrderType, OrderStatus
from ..execution.models import Order, Position, Account
from ..strategy.base import Strategy, StrategySignal
from ..strategy.service import StrategyService


class TradingEngine:
    """
    Main trading engine that coordinates data, execution, and strategies.
    """
    
    def __init__(self, data_service: DataService, execution_service: ExecutionService, 
                 strategy_service: StrategyService):
        self.data_service = data_service
        self.execution_service = execution_service
        self.strategy_service = strategy_service
        
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.subscriptions = set()
        self.active_symbols = set()
        self.active_brokers = set()
        
        # For tracking orders and positions
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Dict[str, Position]] = {}  # broker -> symbol -> position
        self.accounts: Dict[str, Account] = {}  # broker -> account
        
        # Signal handlers
        self.signal_handlers: List[Callable[[StrategySignal], None]] = []
        
        # Timer for periodic strategy updates
        self.timer_interval = 1.0  # seconds
        self.last_timer_time = 0
    
    def add_signal_handler(self, handler: Callable[[StrategySignal], None]) -> None:
        """
        Add a handler for strategy signals.
        
        Args:
            handler: Callback function that takes a StrategySignal
        """
        self.signal_handlers.append(handler)
    
    def remove_signal_handler(self, handler: Callable[[StrategySignal], None]) -> None:
        """
        Remove a signal handler.
        
        Args:
            handler: Handler to remove
        """
        if handler in self.signal_handlers:
            self.signal_handlers.remove(handler)
    
    def _process_signal(self, signal: StrategySignal) -> None:
        """
        Process a strategy signal.
        
        Args:
            signal: Trading signal from a strategy
        """
        # Notify all signal handlers
        for handler in self.signal_handlers:
            try:
                handler(signal)
            except Exception as e:
                self.logger.error(f"Error in signal handler: {str(e)}")
        
        # Execute the order if a broker is specified
        if signal.broker:
            asyncio.create_task(self._execute_signal(signal))
    
    async def _execute_signal(self, signal: StrategySignal) -> None:
        """
        Execute a trading signal by placing an order.
        
        Args:
            signal: Trading signal to execute
        """
        try:
            # Place the order
            order_result = await self.execution_service.place_order(
                broker_name=signal.broker,
                symbol=signal.symbol,
                side=signal.side,
                order_type=signal.order_type,
                quantity=signal.quantity,
                price=signal.price,
                time_in_force=signal.time_in_force,
                stop_price=signal.stop_price,
                client_order_id=signal.metadata.get("client_order_id")
            )
            
            # Store the order with strategy metadata
            order_id = order_result.get("id")
            if order_id:
                self.orders[order_id] = Order(
                    id=order_id,
                    client_order_id=order_result.get("client_order_id", ""),
                    symbol=signal.symbol,
                    side=signal.side,
                    type=signal.order_type,
                    quantity=signal.quantity,
                    price=signal.price,
                    stop_price=signal.stop_price,
                    status=OrderStatus(order_result.get("status", OrderStatus.PENDING.value)),
                    created_at=datetime.datetime.now(),
                    updated_at=datetime.datetime.now(),
                    filled_quantity=0.0,
                    average_price=None,
                    time_in_force=signal.time_in_force,
                    metadata={
                        "strategy_id": signal.strategy_id,
                        "signal_timestamp": signal.timestamp.isoformat(),
                        **signal.metadata
                    }
                )
                
                self.logger.info(f"Executed signal: {signal.strategy_id} placed order {order_id}")
            
        except Exception as e:
            self.logger.error(f"Error executing signal: {str(e)}")
    
    async def start(self) -> None:
        """Start the trading engine."""
        if self.running:
            return
        
        self.running = True
        self.logger.info("Starting trading engine")
        
        # Start the main loop
        asyncio.create_task(self._main_loop())
    
    async def stop(self) -> None:
        """Stop the trading engine."""
        if not self.running:
            return
        
        self.running = False
        self.logger.info("Stopping trading engine")
        
        # Unsubscribe from all data feeds
        for subscription in self.subscriptions.copy():
            symbol, channel, provider = subscription
            try:
                if channel == "ticker":
                    await self.data_service.unsubscribe_ticker(provider, symbol)
                elif channel == "orderbook":
                    await self.data_service.unsubscribe_orderbook(provider, symbol)
                # Skip trades unsubscribe if method doesn't exist
                # elif channel == "trades":
                #     await self.data_service.unsubscribe_trades(provider, symbol)
                
                self.subscriptions.remove(subscription)
            except Exception as e:
                self.logger.error(f"Error unsubscribing from {channel} for {symbol}: {str(e)}")
        
        self.subscriptions.clear()
        
        # Close all services
        await self.data_service.close_all()
        await self.execution_service.close_all()
    
    async def subscribe_market_data(self, provider: str, symbol: str, 
                                   channels: List[str] = None) -> None:
        """
        Subscribe to market data for a symbol.
        
        Args:
            provider: Data provider name
            symbol: Trading symbol
            channels: List of channels to subscribe to (ticker, orderbook, trades)
        """
        if channels is None:
            channels = ["ticker"]
        
        for channel in channels:
            subscription = (symbol, channel, provider)
            if subscription in self.subscriptions:
                continue
            
            try:
                if channel == "ticker":
                    # Create a callback that includes symbol and provider
                    # Convert raw websocket data to Ticker object
                    def ticker_callback(data):
                        try:
                            # Process the raw websocket data
                            if isinstance(data, dict) and data.get("type") == "update":
                                ticker_data = data.get("events", [{}])[0] if data.get("events") else {}
                                ticker = Ticker(
                                    symbol=symbol,
                                    bid=float(ticker_data.get("bid", 0)),
                                    ask=float(ticker_data.get("ask", 0)),
                                    last=float(ticker_data.get("price", 0)),
                                    volume_24h=float(ticker_data.get("volume", 0)),
                                    timestamp=datetime.datetime.now()
                                )
                                self._ticker_callback(ticker, symbol, provider)
                        except Exception as e:
                            self.logger.error(f"Error processing ticker data: {str(e)}")
                    
                    await self.data_service.subscribe_ticker(
                        provider, symbol, ticker_callback
                    )
                elif channel == "orderbook":
                    # Create a callback that includes symbol and provider
                    def orderbook_callback(data):
                        try:
                            # Process the raw websocket data
                            if isinstance(data, dict) and data.get("type") == "update":
                                events = data.get("events", [])
                                bids = []
                                asks = []
                                
                                for event in events:
                                    if event.get("side") == "bid":
                                        bids.append(OrderBookEntry(
                                            price=float(event.get("price", 0)),
                                            amount=float(event.get("remaining", 0))
                                        ))
                                    elif event.get("side") == "ask":
                                        asks.append(OrderBookEntry(
                                            price=float(event.get("price", 0)),
                                            amount=float(event.get("remaining", 0))
                                        ))
                                
                                orderbook = OrderBook(
                                    symbol=symbol,
                                    bids=bids,
                                    asks=asks,
                                    timestamp=datetime.datetime.now()
                                )
                                self._orderbook_callback(orderbook, symbol, provider)
                        except Exception as e:
                            self.logger.error(f"Error processing orderbook data: {str(e)}")
                    
                    await self.data_service.subscribe_orderbook(
                        provider, symbol, orderbook_callback
                    )
                elif channel == "trades":
                    # Create a callback that includes symbol and provider
                    def trades_callback(data):
                        try:
                            # Process the raw websocket data
                            if isinstance(data, dict) and data.get("type") == "update":
                                events = data.get("events", [])
                                
                                for event in events:
                                    if event.get("type") == "trade":
                                        trade = Trade(
                                            symbol=symbol,
                                            trade_id=str(event.get("tid", "")),
                                            price=float(event.get("price", 0)),
                                            amount=float(event.get("amount", 0)),
                                            side="buy" if event.get("makerSide") == "sell" else "sell",
                                            timestamp=datetime.datetime.now(),
                                            raw_data=event
                                        )
                                        self._trades_callback(trade, symbol, provider)
                        except Exception as e:
                            self.logger.error(f"Error processing trade data: {str(e)}")
                    
                    await self.data_service.subscribe_trades(
                        provider, symbol, trades_callback
                    )
                
                self.subscriptions.add(subscription)
                self.active_symbols.add(symbol)
                self.logger.info(f"Subscribed to {channel} for {symbol} via {provider}")
            
            except Exception as e:
                self.logger.error(f"Error subscribing to {channel} for {symbol}: {str(e)}")
    
    async def unsubscribe_market_data(self, provider: str, symbol: str, 
                                     channels: List[str] = None) -> None:
        """
        Unsubscribe from market data for a symbol.
        
        Args:
            provider: Data provider name
            symbol: Trading symbol
            channels: List of channels to unsubscribe from (ticker, orderbook, trades)
        """
        if channels is None:
            channels = ["ticker", "orderbook", "trades"]
        
        for channel in channels:
            subscription = (symbol, channel, provider)
            if subscription not in self.subscriptions:
                continue
            
            try:
                if channel == "ticker":
                    await self.data_service.unsubscribe_ticker(provider, symbol)
                elif channel == "orderbook":
                    await self.data_service.unsubscribe_orderbook(provider, symbol)
                elif channel == "trades":
                    await self.data_service.unsubscribe_trades(provider, symbol)
                
                self.subscriptions.remove(subscription)
                self.logger.info(f"Unsubscribed from {channel} for {symbol} via {provider}")
            
            except Exception as e:
                self.logger.error(f"Error unsubscribing from {channel} for {symbol}: {str(e)}")
        
        # Check if we're still subscribed to any channels for this symbol
        symbol_subscriptions = [(s, c, p) for s, c, p in self.subscriptions if s == symbol]
        if not symbol_subscriptions:
            self.active_symbols.remove(symbol)
    
    async def add_broker(self, broker_name: str) -> None:
        """
        Add a broker to the active brokers list.
        
        Args:
            broker_name: Name of the broker to add
        """
        if broker_name in self.active_brokers:
            return
        
        # Check if broker exists
        broker = self.execution_service.get_broker(broker_name)
        if not broker:
            self.logger.error(f"Broker {broker_name} not found")
            return
        
        self.active_brokers.add(broker_name)
        self.logger.info(f"Added broker: {broker_name}")
        
        # Fetch initial account and positions data
        asyncio.create_task(self._fetch_broker_data(broker_name))
    
    async def remove_broker(self, broker_name: str) -> None:
        """
        Remove a broker from the active brokers list.
        
        Args:
            broker_name: Name of the broker to remove
        """
        if broker_name not in self.active_brokers:
            return
        
        self.active_brokers.remove(broker_name)
        self.logger.info(f"Removed broker: {broker_name}")
    
    async def _fetch_broker_data(self, broker_name: str) -> None:
        """
        Fetch initial account and positions data for a broker.
        
        Args:
            broker_name: Name of the broker
        """
        try:
            # Fetch account info
            account_info = await self.execution_service.get_account_info(broker_name)
            self.accounts[broker_name] = account_info
            
            # Fetch positions
            positions = await self.execution_service.get_positions(broker_name)
            self.positions[broker_name] = {
                position.symbol: position for position in positions
            }
            
            # Fetch open orders
            orders = await self.execution_service.get_orders(broker_name)
            for order in orders:
                self.orders[order.id] = order
            
            self.logger.info(f"Fetched initial data for broker: {broker_name}")
        
        except Exception as e:
            self.logger.error(f"Error fetching data for broker {broker_name}: {str(e)}")
    
    async def _main_loop(self) -> None:
        """Main engine loop that updates strategies periodically."""
        self.last_timer_time = time.time()
        self.last_broker_update_time = time.time()
        broker_update_interval = 5.0  # Update broker data every 5 seconds to avoid rate limits
        
        while self.running:
            try:
                # Check if it's time for a timer update
                current_time = time.time()
                if current_time - self.last_timer_time >= self.timer_interval:
                    self.last_timer_time = current_time
                    await self._update_strategies_timer()
                
                # Update account and position data periodically with rate limiting
                if current_time - self.last_broker_update_time >= broker_update_interval:
                    self.last_broker_update_time = current_time
                    for broker_name in self.active_brokers:
                        await self._update_broker_data(broker_name)
                        # Add delay between broker updates to avoid rate limits
                        await asyncio.sleep(1.0)
                
                # Sleep to avoid high CPU usage
                await asyncio.sleep(0.1)
            
            except Exception as e:
                self.logger.error(f"Error in main loop: {str(e)}")
                await asyncio.sleep(1)  # Sleep longer on error
    
    async def _update_broker_data(self, broker_name: str) -> None:
        """
        Update account and position data for a broker.
        
        Args:
            broker_name: Name of the broker
        """
        try:
            # Update account info
            account_info = await self.execution_service.get_account_info(broker_name)
            old_account = self.accounts.get(broker_name)
            self.accounts[broker_name] = account_info
            
            # Notify strategies of account update
            if old_account != account_info:
                await self._notify_account_update(account_info, broker_name)
            
            # Update positions
            positions = await self.execution_service.get_positions(broker_name)
            old_positions = self.positions.get(broker_name, {})
            new_positions = {position.symbol: position for position in positions}
            self.positions[broker_name] = new_positions
            
            # Notify strategies of position updates
            for symbol, position in new_positions.items():
                old_position = old_positions.get(symbol)
                if old_position != position:
                    await self._notify_position_update(position, broker_name)
            
            # Check for closed positions
            for symbol, old_position in old_positions.items():
                if symbol not in new_positions:
                    # Position was closed
                    zero_position = Position(
                        symbol=symbol,
                        quantity=0,
                        entry_price=0,
                        mark_price=0,
                        unrealized_pnl=0
                    )
                    await self._notify_position_update(zero_position, broker_name)
            
            # Update orders
            orders = await self.execution_service.get_orders(broker_name)
            for order in orders:
                old_order = self.orders.get(order.id)
                self.orders[order.id] = order
                
                if old_order != order:
                    await self._notify_order_update(order, broker_name)
        
        except Exception as e:
            self.logger.error(f"Error updating data for broker {broker_name}: {str(e)}")
    
    async def _update_strategies_timer(self) -> None:
        """Update all strategies with timer event."""
        current_time = datetime.datetime.now()
        
        for strategy_id, strategy in self.strategy_service.get_all_strategies().items():
            try:
                strategy.on_timer(current_time)
            except Exception as e:
                self.logger.error(f"Error in strategy {strategy_id} timer update: {str(e)}")
    
    async def _notify_account_update(self, account: Account, broker: str) -> None:
        """
        Notify all strategies of an account update.
        
        Args:
            account: Updated account information
            broker: Broker name
        """
        for strategy_id, strategy in self.strategy_service.get_all_strategies().items():
            try:
                strategy.on_account_update(account, broker)
            except Exception as e:
                self.logger.error(f"Error in strategy {strategy_id} account update: {str(e)}")
    
    async def _notify_position_update(self, position: Position, broker: str) -> None:
        """
        Notify all strategies of a position update.
        
        Args:
            position: Updated position information
            broker: Broker name
        """
        for strategy_id, strategy in self.strategy_service.get_all_strategies().items():
            try:
                strategy.on_position_update(position, broker)
            except Exception as e:
                self.logger.error(f"Error in strategy {strategy_id} position update: {str(e)}")
    
    async def _notify_order_update(self, order: Order, broker: str) -> None:
        """
        Notify all strategies of an order update.
        
        Args:
            order: Updated order information
            broker: Broker name
        """
        for strategy_id, strategy in self.strategy_service.get_all_strategies().items():
            try:
                strategy.on_order_update(order, broker)
            except Exception as e:
                self.logger.error(f"Error in strategy {strategy_id} order update: {str(e)}")
    
    def _ticker_callback(self, ticker: Ticker, symbol: str, provider: str) -> None:
        """
        Callback for ticker updates.
        
        Args:
            ticker: Ticker data
            symbol: Trading symbol
            provider: Data provider name
        """
        for strategy_id, strategy in self.strategy_service.get_all_strategies().items():
            try:
                strategy.on_ticker(ticker, symbol, provider)
            except Exception as e:
                self.logger.error(f"Error in strategy {strategy_id} ticker update: {str(e)}")
    
    def _orderbook_callback(self, orderbook: OrderBook, symbol: str, provider: str) -> None:
        """
        Callback for orderbook updates.
        
        Args:
            orderbook: Orderbook data
            symbol: Trading symbol
            provider: Data provider name
        """
        for strategy_id, strategy in self.strategy_service.get_all_strategies().items():
            try:
                strategy.on_orderbook(orderbook, symbol, provider)
            except Exception as e:
                self.logger.error(f"Error in strategy {strategy_id} orderbook update: {str(e)}")
    
    def _trades_callback(self, trade: Trade, symbol: str, provider: str) -> None:
        """
        Callback for trade updates.
        
        Args:
            trade: Trade data
            symbol: Trading symbol
            provider: Data provider name
        """
        for strategy_id, strategy in self.strategy_service.get_all_strategies().items():
            try:
                strategy.on_trade(trade, symbol, provider)
            except Exception as e:
                self.logger.error(f"Error in strategy {strategy_id} trade update: {str(e)}")
    
    async def fetch_candles(self, provider: str, symbol: str, interval: str,
                           start_time: Optional[datetime.datetime] = None,
                           end_time: Optional[datetime.datetime] = None,
                           limit: int = 100) -> List[Candle]:
        """
        Fetch historical candles and notify strategies.
        
        Args:
            provider: Data provider name
            symbol: Trading symbol
            interval: Candle interval (e.g., "1m", "1h", "1d")
            start_time: Start time for candles
            end_time: End time for candles
            limit: Maximum number of candles to fetch
            
        Returns:
            List of candles
        """
        try:
            candles = await self.data_service.get_candles(
                provider, symbol, interval, start_time, end_time, limit
            )
            
            # Notify strategies of each candle
            for candle in candles:
                for strategy_id, strategy in self.strategy_service.get_all_strategies().items():
                    try:
                        strategy.on_candle(candle, symbol, interval, provider)
                    except Exception as e:
                        self.logger.error(f"Error in strategy {strategy_id} candle update: {str(e)}")
            
            return candles
        
        except Exception as e:
            self.logger.error(f"Error fetching candles for {symbol}: {str(e)}")
            return []
