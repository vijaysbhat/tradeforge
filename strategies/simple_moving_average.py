import datetime
from typing import Dict, Any, List, Optional
import logging

from src.strategy.base import Strategy, StrategySignal
from src.data.models import Ticker, OrderBook, Trade, Candle
from src.execution.base import OrderSide, OrderType, OrderStatus
from src.execution.models import Order, Position, Account


class SimpleMovingAverageStrategy(Strategy):
    """
    Simple Moving Average crossover strategy.
    
    This strategy generates buy signals when the short-term moving average crosses above
    the long-term moving average, and sell signals when it crosses below.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.symbol = None
        self.broker = None
        self.data_provider = None
        
        # Strategy parameters
        self.short_period = 20
        self.long_period = 50
        self.position_size = 0.1  # 10% of account balance
        
        # State variables
        self.candles: Dict[str, List[Candle]] = {}  # interval -> candles
        self.current_position = 0.0  # Initialize as float to avoid type issues
        self.account_balance = 0.0
        self.last_signal_time = None
        self.signal_cooldown = datetime.timedelta(hours=1)
        
        # Signal callback
        self.signal_callback = None
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the strategy with configuration parameters."""
        self.symbol = config.get("symbol", "BTCUSD")
        self.broker = config.get("broker", "gemini")
        self.data_provider = config.get("data_provider", "gemini")
        
        # Strategy parameters
        self.short_period = config.get("short_period", self.short_period)
        self.long_period = config.get("long_period", self.long_period)
        self.position_size = config.get("position_size", self.position_size)
        
        # Sandbox mode
        self.sandbox = config.get("sandbox", True)
        
        # Signal callback
        self.signal_callback = config.get("signal_callback")
        
        self.logger.info(f"Initialized SimpleMovingAverageStrategy for {self.symbol}")
        self.logger.info(f"Parameters: short_period={self.short_period}, long_period={self.long_period}")
        self.logger.info(f"Running in {'sandbox' if self.sandbox else 'production'} mode")
    
    def on_ticker(self, ticker: Ticker, symbol: str, provider: str) -> None:
        """Process ticker updates."""
        # Not used in this strategy
        pass
    
    def on_orderbook(self, orderbook: OrderBook, symbol: str, provider: str) -> None:
        """Process orderbook updates."""
        # Not used in this strategy
        pass
    
    def on_trade(self, trade: Trade, symbol: str, provider: str) -> None:
        """Process trade updates."""
        # Not used in this strategy
        pass
    
    def on_candle(self, candle: Candle, symbol: str, interval: str, provider: str) -> None:
        """
        Process candle updates and generate trading signals based on moving average crossovers.
        """
        if symbol != self.symbol or provider != self.data_provider:
            return
        
        # Store candle
        if interval not in self.candles:
            self.candles[interval] = []
        
        # Add candle to the list
        self.candles[interval].append(candle)
        
        # Keep only the necessary number of candles
        max_period = max(self.short_period, self.long_period)
        if len(self.candles[interval]) > max_period + 10:  # Keep a few extra for safety
            self.candles[interval] = self.candles[interval][-max_period-10:]
        
        # Check for signal
        self._check_for_signal(interval)
    
    def on_order_update(self, order: Order, broker: str) -> None:
        """Process order updates."""
        if broker != self.broker or order.symbol != self.symbol:
            return
        
        self.logger.info(f"Order update: {order.id} - {order.status.name}")
    
    def on_position_update(self, position: Position, broker: str) -> None:
        """Process position updates."""
        if broker != self.broker or position.symbol != self.symbol:
            return
        
        self.current_position = position.quantity
        self.logger.info(f"Position update: {position.symbol} - {position.quantity}")
    
    def on_account_update(self, account: Account, broker: str) -> None:
        """Process account updates."""
        if broker != self.broker:
            return
        
        # Find USD balance
        for balance in account.balances:
            if balance.asset == "USD":
                self.account_balance = balance.free
                break
        
        self.logger.info(f"Account update: Balance = ${self.account_balance}")
    
    def on_timer(self, timestamp: datetime.datetime) -> None:
        """Called periodically by the trading engine."""
        # Not used in this strategy
        pass
    
    def _check_for_signal(self, interval: str) -> None:
        """
        Check for trading signals based on moving average crossover.
        
        Args:
            interval: Candle interval to analyze
        """
        candles = self.candles.get(interval, [])
        if len(candles) < self.long_period:
            self.logger.debug(f"Not enough candles: {len(candles)} < {self.long_period}")
            return  # Not enough data
        
        # Calculate short-term moving average
        short_ma = sum(c.close for c in candles[-self.short_period:]) / self.short_period
        
        # Calculate long-term moving average
        long_ma = sum(c.close for c in candles[-self.long_period:]) / self.long_period
        
        # Calculate previous short-term moving average
        prev_short_ma = sum(c.close for c in candles[-self.short_period-1:-1]) / self.short_period
        
        # Calculate previous long-term moving average
        prev_long_ma = sum(c.close for c in candles[-self.long_period-1:-1]) / self.long_period
        
        # Log the current MA values for debugging
        self.logger.info(f"MAs: short={short_ma:.2f}, long={long_ma:.2f}, prev_short={prev_short_ma:.2f}, prev_long={prev_long_ma:.2f}")
        
        # Check for crossover
        current_time = datetime.datetime.now()
        
        # Check if we're in cooldown period
        if self.last_signal_time and current_time - self.last_signal_time < self.signal_cooldown:
            self.logger.debug(f"In cooldown period, last signal: {self.last_signal_time}")
            return
        
        # Buy signal: short MA crosses above long MA
        if prev_short_ma <= prev_long_ma and short_ma > long_ma:
            self.logger.info(f"BUY SIGNAL DETECTED: short MA ({short_ma:.2f}) crossed above long MA ({long_ma:.2f})")
            # Check if we have a position, with proper float comparison to avoid precision issues
            if self.current_position is None or self.current_position < 0.000001:
                self._generate_buy_signal(candles[-1].close)
                self.last_signal_time = current_time
            else:
                self.logger.info(f"Already have position: {self.current_position}, not buying")
        
        # Sell signal: short MA crosses below long MA
        elif prev_short_ma >= prev_long_ma and short_ma < long_ma:
            self.logger.info(f"SELL SIGNAL DETECTED: short MA ({short_ma:.2f}) crossed below long MA ({long_ma:.2f})")
            # Check if we have a position to sell, with proper float comparison
            if self.current_position is not None and self.current_position > 0.000001:
                self._generate_sell_signal(candles[-1].close)
                self.last_signal_time = current_time
            else:
                self.logger.info(f"No position to sell: {self.current_position}")
        else:
            self.logger.debug(f"No crossover detected")
    
    def _generate_buy_signal(self, price: float) -> None:
        """
        Generate a buy signal.
        
        Args:
            price: Current price
        """
        if self.account_balance is None or self.account_balance <= 0:
            self.logger.warning("Cannot generate buy signal: No account balance available")
            return
        
        # Calculate quantity based on position size
        quantity = (self.account_balance * self.position_size) / price
        
        # Create signal
        signal = StrategySignal(
            symbol=self.symbol,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=quantity,
            broker=self.broker,
            strategy_id="SimpleMovingAverageStrategy"
        )
        
        # Add metadata after creation
        signal.metadata = {
            "reason": "MA_CROSSOVER_BUY",
            "short_ma_period": self.short_period,
            "long_ma_period": self.long_period
        }
        
        self.logger.info(f"Generated BUY signal for {self.symbol} at {price}")
        
        # Send signal
        if self.signal_callback:
            self.signal_callback(signal)
    
    def _generate_sell_signal(self, price: float) -> None:
        """
        Generate a sell signal.
        
        Args:
            price: Current price
        """
        if self.current_position is None or self.current_position <= 0:
            self.logger.warning("Cannot generate sell signal: No position to sell")
            return
        
        # Create signal
        signal = StrategySignal(
            symbol=self.symbol,
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=self.current_position,
            broker=self.broker,
            strategy_id="SimpleMovingAverageStrategy"
        )
        
        # Add metadata after creation
        signal.metadata = {
            "reason": "MA_CROSSOVER_SELL",
            "short_ma_period": self.short_period,
            "long_ma_period": self.long_period
        }
        
        self.logger.info(f"Generated SELL signal for {self.symbol} at {price}")
        
        # Send signal
        if self.signal_callback:
            self.signal_callback(signal)
