import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from datetime import datetime
import os
import json
from typing import List, Dict, Any, Optional, Tuple
import logging

from ..data.models import Candle
from ..execution.base import OrderSide

logger = logging.getLogger(__name__)

class TradingChart:
    """
    Class for visualizing trading data including price, indicators, and signals.
    """
    
    def __init__(self, symbol: str, save_path: str = "charts"):
        """
        Initialize the chart visualization.
        
        Args:
            symbol: Trading symbol to display
            save_path: Directory to save chart images
        """
        self.symbol = symbol
        self.save_path = save_path
        self.candles = []
        self.short_ma_values = []
        self.long_ma_values = []
        self.buy_signals = []  # List of (timestamp, price) tuples
        self.sell_signals = []  # List of (timestamp, price) tuples
        
        # Create save directory if it doesn't exist
        os.makedirs(save_path, exist_ok=True)
        
        # Data file paths
        self.data_dir = os.path.join(save_path, "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.candles_file = os.path.join(self.data_dir, f"{symbol}_candles.json")
        self.indicators_file = os.path.join(self.data_dir, f"{symbol}_indicators.json")
        self.signals_file = os.path.join(self.data_dir, f"{symbol}_signals.json")
        
        # Set up the plot for saving images
        plt.style.use('dark_background')  # Use dark theme for better visibility
        self.fig, self.ax = plt.subplots(figsize=(12, 8))
        self.fig.tight_layout()
        
        # Initialize data files if they don't exist
        self._initialize_data_files()
    
    def _initialize_data_files(self):
        """Initialize data files with empty data if they don't exist."""
        if not os.path.exists(self.candles_file):
            with open(self.candles_file, 'w') as f:
                json.dump([], f)
        else:
            # Load existing candles
            try:
                with open(self.candles_file, 'r') as f:
                    candles_data = json.load(f)
                    
                # Convert loaded candles to Candle objects
                for candle_data in candles_data:
                    try:
                        timestamp = datetime.fromisoformat(candle_data["timestamp"])
                        candle = Candle(
                            symbol=self.symbol,
                            timestamp=timestamp,
                            open=candle_data["open"],
                            high=candle_data["high"],
                            low=candle_data["low"],
                            close=candle_data["close"],
                            volume=candle_data["volume"]
                        )
                        self.candles.append(candle)
                    except Exception as e:
                        logger.error(f"Error parsing candle data: {e}")
                
                logger.info(f"Loaded {len(self.candles)} existing candles")
            except Exception as e:
                logger.error(f"Error loading candles file: {e}")
        
        if not os.path.exists(self.indicators_file):
            with open(self.indicators_file, 'w') as f:
                json.dump({"short_ma": [], "long_ma": []}, f)
        else:
            # Load existing indicators
            try:
                with open(self.indicators_file, 'r') as f:
                    indicators_data = json.load(f)
                
                # Convert loaded indicators to the right format
                if "short_ma" in indicators_data:
                    self.short_ma_values = [(datetime.fromisoformat(t), v) for t, v in indicators_data["short_ma"]]
                if "long_ma" in indicators_data:
                    self.long_ma_values = [(datetime.fromisoformat(t), v) for t, v in indicators_data["long_ma"]]
                
                logger.info(f"Loaded {len(self.short_ma_values)} short MA and {len(self.long_ma_values)} long MA values")
            except Exception as e:
                logger.error(f"Error loading indicators file: {e}")
        
        if not os.path.exists(self.signals_file):
            with open(self.signals_file, 'w') as f:
                json.dump({"buy": [], "sell": []}, f)
        else:
            # Load existing signals
            try:
                with open(self.signals_file, 'r') as f:
                    signals_data = json.load(f)
                
                # Convert loaded signals to the right format
                if "buy" in signals_data:
                    self.buy_signals = [(datetime.fromisoformat(t), p) for t, p in signals_data["buy"]]
                if "sell" in signals_data:
                    self.sell_signals = [(datetime.fromisoformat(t), p) for t, p in signals_data["sell"]]
                
                logger.info(f"Loaded {len(self.buy_signals)} buy signals and {len(self.sell_signals)} sell signals")
            except Exception as e:
                logger.error(f"Error loading signals file: {e}")
    
    def add_candle(self, candle: Candle) -> None:
        """
        Add a new candle to the chart data.
        
        Args:
            candle: Candle data to add
        """
        self.candles.append(candle)
        
        # Save to file
        self._save_candles()
    
    def update_moving_averages(self, short_ma: float, long_ma: float) -> None:
        """
        Update the moving average values.
        
        Args:
            short_ma: Current short-term moving average value
            long_ma: Current long-term moving average value
        """
        if self.candles:
            timestamp = self.candles[-1].timestamp
            self.short_ma_values.append((timestamp, short_ma))
            self.long_ma_values.append((timestamp, long_ma))
            
            # Save to file
            self._save_indicators()
    
    def add_signal(self, timestamp: datetime, price: float, side: OrderSide) -> None:
        """
        Add a trading signal to the chart.
        
        Args:
            timestamp: Time of the signal
            price: Price at the signal
            side: Buy or sell side
        """
        if side == OrderSide.BUY:
            self.buy_signals.append((timestamp, price))
        elif side == OrderSide.SELL:
            self.sell_signals.append((timestamp, price))
        
        # Save to file
        self._save_signals()
    
    def _save_candles(self):
        """Save candles data to file."""
        # First load existing candles
        existing_candles = []
        try:
            if os.path.exists(self.candles_file):
                with open(self.candles_file, 'r') as f:
                    existing_candles = json.load(f)
        except Exception as e:
            logger.error(f"Error loading existing candles: {e}")
            existing_candles = []
        
        # Convert the latest candle to a dict
        if self.candles:
            latest_candle = self.candles[-1]
            candle_data = {
                "timestamp": latest_candle.timestamp.isoformat(),
                "open": latest_candle.open,
                "high": latest_candle.high,
                "low": latest_candle.low,
                "close": latest_candle.close,
                "volume": latest_candle.volume
            }
            
            # Check if this candle already exists (by timestamp)
            timestamp_exists = False
            for i, existing_candle in enumerate(existing_candles):
                if existing_candle["timestamp"] == candle_data["timestamp"]:
                    # Update the existing candle
                    existing_candles[i] = candle_data
                    timestamp_exists = True
                    break
            
            # If it's a new timestamp, append it
            if not timestamp_exists:
                existing_candles.append(candle_data)
        
        try:
            with open(self.candles_file, 'w') as f:
                json.dump(existing_candles, f)
            logger.debug(f"Saved {len(existing_candles)} candles to {self.candles_file}")
        except Exception as e:
            logger.error(f"Error saving candles data: {e}")
    
    def _save_indicators(self):
        """Save indicator data to file."""
        indicators_data = {
            "short_ma": [(t.isoformat(), v) for t, v in self.short_ma_values],
            "long_ma": [(t.isoformat(), v) for t, v in self.long_ma_values]
        }
        
        try:
            with open(self.indicators_file, 'w') as f:
                json.dump(indicators_data, f)
            logger.debug(f"Saved indicators data to {self.indicators_file}")
        except Exception as e:
            logger.error(f"Error saving indicators data: {e}")
    
    def _save_signals(self):
        """Save signals data to file."""
        signals_data = {
            "buy": [(t.isoformat(), p) for t, p in self.buy_signals],
            "sell": [(t.isoformat(), p) for t, p in self.sell_signals]
        }
        
        try:
            with open(self.signals_file, 'w') as f:
                json.dump(signals_data, f)
            logger.debug(f"Saved signals data to {self.signals_file}")
        except Exception as e:
            logger.error(f"Error saving signals data: {e}")
    
    def plot(self, show: bool = False, save: bool = True) -> None:
        """
        Generate and optionally display/save the chart.
        
        Args:
            show: Whether to display the chart
            save: Whether to save the chart to a file
        """
        if not self.candles:
            logger.warning("No candles to plot")
            return
        
        # Clear previous plot
        self.ax.clear()
        
        # Extract data for plotting
        timestamps = [candle.timestamp for candle in self.candles]
        opens = [candle.open for candle in self.candles]
        highs = [candle.high for candle in self.candles]
        lows = [candle.low for candle in self.candles]
        closes = [candle.close for candle in self.candles]
        
        # Create a pandas DataFrame for easier manipulation
        df = pd.DataFrame({
            'timestamp': timestamps,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes
        })
        
        # Plot candlestick chart
        width = 0.6
        width2 = width * 0.8
        
        up = df[df.close >= df.open]
        down = df[df.close < df.open]
        
        # Plot up candles
        self.ax.bar(up.index, up.close-up.open, width, bottom=up.open, color='green')
        self.ax.bar(up.index, up.high-up.close, width2, bottom=up.close, color='green')
        self.ax.bar(up.index, up.low-up.open, width2, bottom=up.open, color='green')
        
        # Plot down candles
        self.ax.bar(down.index, down.close-down.open, width, bottom=down.open, color='red')
        self.ax.bar(down.index, down.high-down.open, width2, bottom=down.open, color='red')
        self.ax.bar(down.index, down.low-down.close, width2, bottom=down.close, color='red')
        
        # Plot moving averages if available
        if self.short_ma_values:
            short_ma_times = [x[0] for x in self.short_ma_values]
            short_ma_values = [x[1] for x in self.short_ma_values]
            
            # Map timestamps to indices
            short_ma_indices = [timestamps.index(t) if t in timestamps else None for t in short_ma_times]
            short_ma_indices = [i for i in short_ma_indices if i is not None]
            
            if short_ma_indices:
                self.ax.plot(short_ma_indices, [short_ma_values[i] for i in range(len(short_ma_indices))], 
                         color='yellow', linewidth=1, label='Short MA')
        
        if self.long_ma_values:
            long_ma_times = [x[0] for x in self.long_ma_values]
            long_ma_values = [x[1] for x in self.long_ma_values]
            
            # Map timestamps to indices
            long_ma_indices = [timestamps.index(t) if t in timestamps else None for t in long_ma_times]
            long_ma_indices = [i for i in long_ma_indices if i is not None]
            
            if long_ma_indices:
                self.ax.plot(long_ma_indices, [long_ma_values[i] for i in range(len(long_ma_indices))], 
                         color='blue', linewidth=1, label='Long MA')
        
        # Plot buy signals
        if self.buy_signals:
            buy_times = [x[0] for x in self.buy_signals]
            buy_prices = [x[1] for x in self.buy_signals]
            
            # Map timestamps to indices
            buy_indices = [timestamps.index(t) if t in timestamps else None for t in buy_times]
            buy_indices = [i for i in buy_indices if i is not None]
            
            if buy_indices:
                self.ax.scatter(buy_indices, [buy_prices[i] for i in range(len(buy_indices))], 
                            color='lime', marker='^', s=100, label='Buy Signal')
        
        # Plot sell signals
        if self.sell_signals:
            sell_times = [x[0] for x in self.sell_signals]
            sell_prices = [x[1] for x in self.sell_signals]
            
            # Map timestamps to indices
            sell_indices = [timestamps.index(t) if t in timestamps else None for t in sell_times]
            sell_indices = [i for i in sell_indices if i is not None]
            
            if sell_indices:
                self.ax.scatter(sell_indices, [sell_prices[i] for i in range(len(sell_indices))], 
                            color='red', marker='v', s=100, label='Sell Signal')
        
        # Set labels and title
        self.ax.set_title(f'{self.symbol} Trading Chart')
        self.ax.set_xlabel('Candle Number')
        self.ax.set_ylabel('Price')
        self.ax.legend()
        self.ax.grid(True, alpha=0.3)
        
        # Set x-axis tick labels to show dates
        tick_indices = np.linspace(0, len(timestamps)-1, min(10, len(timestamps))).astype(int)
        self.ax.set_xticks(tick_indices)
        self.ax.set_xticklabels([timestamps[i].strftime('%Y-%m-%d %H:%M') for i in tick_indices], rotation=45)
        
        # Save the chart if requested
        if save:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.save_path}/{self.symbol}_{timestamp}.png"
            plt.savefig(filename, bbox_inches='tight')
            
            # Also save a "latest" version that's always overwritten
            latest_filename = f"{self.save_path}/{self.symbol}_latest.png"
            plt.savefig(latest_filename, bbox_inches='tight')
            
            logger.info(f"Chart saved to {filename}")
        
        # Show the chart if requested
        if show:
            plt.show()
        else:
            plt.close(self.fig)
