import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from datetime import datetime
import os
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
        
        # Set up the plot
        plt.style.use('dark_background')  # Use dark theme for better visibility
        self.fig, self.ax = plt.subplots(figsize=(12, 8))
        self.fig.tight_layout()
    
    def add_candle(self, candle: Candle) -> None:
        """
        Add a new candle to the chart data.
        
        Args:
            candle: Candle data to add
        """
        self.candles.append(candle)
    
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
            logger.info(f"Chart saved to {filename}")
        
        # Show the chart if requested
        if show:
            plt.show()
        else:
            plt.close(self.fig)
