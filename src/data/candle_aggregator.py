import datetime
from typing import Dict, Tuple, Optional
from .models import Ticker, Trade, Candle


class CandleAggregator:
    """
    Aggregates ticker/trade data into OHLCV candles in real-time.
    
    This class collects incoming market data and constructs candles at specified
    intervals (e.g., 1m, 5m, 15m, etc.). It tracks the current in-progress candle
    and returns completed candles when they're ready.
    """
    
    def __init__(self, symbol: str, interval: str = "1m"):
        """
        Initialize a candle aggregator for a specific symbol and interval.
        
        Args:
            symbol: The trading symbol (e.g., 'btcusd')
            interval: The candle interval (e.g., '1m', '5m', '15m', '1h', '1d')
        """
        self.symbol = symbol
        self.interval = interval
        self.current_candle = None
        self.last_candle_time = None
        self.last_ticker_price = None
        self.volume_since_last_candle = 0.0
    
    def process_ticker(self, ticker: Ticker) -> Tuple[Optional[Candle], Optional[Candle]]:
        """
        Process a ticker update and update the current candle.
        
        Args:
            ticker: The ticker data
            
        Returns:
            A tuple of (completed_candle, current_candle) where completed_candle
            is None if no candle was completed during this update
        """
        if ticker.symbol != self.symbol:
            return None, None
            
        current_time = ticker.timestamp
        interval_seconds = self._interval_to_seconds(self.interval)
        
        # Determine candle start time (rounded down to interval)
        candle_start = self._round_time_down(current_time, interval_seconds)
        
        # If we need to start a new candle
        if self.current_candle is None or candle_start > self.last_candle_time:
            # Finalize previous candle if it exists
            completed_candle = self.current_candle
            
            # Start a new candle
            self.current_candle = Candle(
                symbol=self.symbol,
                timestamp=candle_start,
                open=ticker.last,
                high=ticker.last,
                low=ticker.last,
                close=ticker.last,
                volume=0.0
            )
            self.last_candle_time = candle_start
            self.volume_since_last_candle = 0.0
            
            return completed_candle, self.current_candle
        
        # Update current candle
        if ticker.last > self.current_candle.high:
            self.current_candle.high = ticker.last
        if ticker.last < self.current_candle.low:
            self.current_candle.low = ticker.last
        self.current_candle.close = ticker.last
        
        # Store last price for volume calculations from trades
        self.last_ticker_price = ticker.last
        
        return None, self.current_candle
    
    def process_trade(self, trade: Trade) -> Tuple[Optional[Candle], Optional[Candle]]:
        """
        Process a trade update and update the current candle.
        
        Args:
            trade: The trade data
            
        Returns:
            A tuple of (completed_candle, current_candle) where completed_candle
            is None if no candle was completed during this update
        """
        if trade.symbol != self.symbol:
            return None, None
            
        current_time = trade.timestamp
        interval_seconds = self._interval_to_seconds(self.interval)
        
        # Determine candle start time (rounded down to interval)
        candle_start = self._round_time_down(current_time, interval_seconds)
        
        # If we need to start a new candle
        if self.current_candle is None or candle_start > self.last_candle_time:
            # Finalize previous candle if it exists
            completed_candle = self.current_candle
            
            # Start a new candle
            self.current_candle = Candle(
                symbol=self.symbol,
                timestamp=candle_start,
                open=trade.price,
                high=trade.price,
                low=trade.price,
                close=trade.price,
                volume=trade.amount
            )
            self.last_candle_time = candle_start
            self.volume_since_last_candle = trade.amount
            
            return completed_candle, self.current_candle
        
        # Update current candle
        if trade.price > self.current_candle.high:
            self.current_candle.high = trade.price
        if trade.price < self.current_candle.low:
            self.current_candle.low = trade.price
        self.current_candle.close = trade.price
        
        # Update volume
        self.volume_since_last_candle += trade.amount
        self.current_candle.volume = self.volume_since_last_candle
        
        return None, self.current_candle
    
    def check_candle_completion(self, current_time: datetime.datetime) -> Optional[Candle]:
        """
        Check if the current candle should be completed based on the current time.
        
        Args:
            current_time: The current timestamp
            
        Returns:
            The completed candle if the interval has passed, otherwise None
        """
        if self.current_candle is None or self.last_candle_time is None:
            return None
            
        interval_seconds = self._interval_to_seconds(self.interval)
        next_candle_time = self.last_candle_time + datetime.timedelta(seconds=interval_seconds)
        
        if current_time >= next_candle_time:
            completed_candle = self.current_candle
            
            # Start a new candle using the last known price
            if self.last_ticker_price:
                self.current_candle = Candle(
                    symbol=self.symbol,
                    timestamp=next_candle_time,
                    open=self.current_candle.close,  # Use previous close as new open
                    high=self.current_candle.close,
                    low=self.current_candle.close,
                    close=self.current_candle.close,
                    volume=0.0
                )
                self.last_candle_time = next_candle_time
                self.volume_since_last_candle = 0.0
            else:
                # If we don't have a price, just mark the current candle as None
                self.current_candle = None
                self.last_candle_time = None
            
            return completed_candle
        
        return None
    
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
    
    def _round_time_down(self, dt: datetime.datetime, seconds: int) -> datetime.datetime:
        """Round a datetime down to the nearest interval."""
        timestamp = dt.timestamp()
        rounded = int(timestamp / seconds) * seconds
        return datetime.datetime.fromtimestamp(rounded)
