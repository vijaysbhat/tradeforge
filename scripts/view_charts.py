#!/usr/bin/env python3
import os
import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import json
from datetime import datetime
import argparse
import pandas as pd
import numpy as np
from dateutil import parser

def load_chart_data(symbol, charts_dir="charts"):
    """Load chart data from JSON files."""
    data_dir = os.path.join(charts_dir, "data")
    
    # Check if data directory exists
    if not os.path.exists(data_dir):
        return None, None, None
    
    # File paths
    candles_file = os.path.join(data_dir, f"{symbol}_candles.json")
    indicators_file = os.path.join(data_dir, f"{symbol}_indicators.json")
    signals_file = os.path.join(data_dir, f"{symbol}_signals.json")
    
    # Check if files exist
    if not (os.path.exists(candles_file) and 
            os.path.exists(indicators_file) and 
            os.path.exists(signals_file)):
        return None, None, None
    
    # Load data
    try:
        with open(candles_file, 'r') as f:
            candles_data = json.load(f)
        
        with open(indicators_file, 'r') as f:
            indicators_data = json.load(f)
        
        with open(signals_file, 'r') as f:
            signals_data = json.load(f)
        
        return candles_data, indicators_data, signals_data
    except Exception as e:
        print(f"Error loading chart data: {e}")
        return None, None, None

def update_plot(frame, symbol, charts_dir, ax, fig):
    """Update the plot with the latest data."""
    # Load data
    candles_data, indicators_data, signals_data = load_chart_data(symbol, charts_dir)
    
    if not candles_data:
        ax.clear()
        ax.text(0.5, 0.5, f"No data available for {symbol}", 
                horizontalalignment='center', verticalalignment='center',
                transform=ax.transAxes, fontsize=14)
        fig.canvas.draw_idle()
        return
    
    # Clear previous plot
    ax.clear()
    
    # Parse candles data
    timestamps = [parser.parse(candle["timestamp"]) for candle in candles_data]
    opens = [candle["open"] for candle in candles_data]
    highs = [candle["high"] for candle in candles_data]
    lows = [candle["low"] for candle in candles_data]
    closes = [candle["close"] for candle in candles_data]
    
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
    up_indices = up.index.tolist()
    if up_indices:
        ax.bar(up_indices, 
               [up.close.iloc[i] - up.open.iloc[i] for i in range(len(up_indices))], 
               width, 
               bottom=[up.open.iloc[i] for i in range(len(up_indices))], 
               color='green')
        ax.bar(up_indices, 
               [up.high.iloc[i] - up.close.iloc[i] for i in range(len(up_indices))], 
               width2, 
               bottom=[up.close.iloc[i] for i in range(len(up_indices))], 
               color='green')
        ax.bar(up_indices, 
               [up.low.iloc[i] - up.open.iloc[i] for i in range(len(up_indices))], 
               width2, 
               bottom=[up.open.iloc[i] for i in range(len(up_indices))], 
               color='green')
    
    # Plot down candles
    down_indices = down.index.tolist()
    if down_indices:
        ax.bar(down_indices, 
               [down.close.iloc[i] - down.open.iloc[i] for i in range(len(down_indices))], 
               width, 
               bottom=[down.open.iloc[i] for i in range(len(down_indices))], 
               color='red')
        ax.bar(down_indices, 
               [down.high.iloc[i] - down.open.iloc[i] for i in range(len(down_indices))], 
               width2, 
               bottom=[down.open.iloc[i] for i in range(len(down_indices))], 
               color='red')
        ax.bar(down_indices, 
               [down.low.iloc[i] - down.close.iloc[i] for i in range(len(down_indices))], 
               width2, 
               bottom=[down.close.iloc[i] for i in range(len(down_indices))], 
               color='red')
    
    # Plot moving averages if available
    if indicators_data and "short_ma" in indicators_data and indicators_data["short_ma"]:
        short_ma_data = indicators_data["short_ma"]
        short_ma_times = [parser.parse(x[0]) for x in short_ma_data]
        short_ma_values = [x[1] for x in short_ma_data]
        
        # Map timestamps to indices
        short_ma_indices = []
        for t in short_ma_times:
            try:
                idx = timestamps.index(t)
                short_ma_indices.append(idx)
            except ValueError:
                pass
        
        if short_ma_indices:
            ax.plot(short_ma_indices, 
                   [short_ma_values[i] for i in range(len(short_ma_indices))], 
                   color='yellow', linewidth=1, label='Short MA')
    
    if indicators_data and "long_ma" in indicators_data and indicators_data["long_ma"]:
        long_ma_data = indicators_data["long_ma"]
        long_ma_times = [parser.parse(x[0]) for x in long_ma_data]
        long_ma_values = [x[1] for x in long_ma_data]
        
        # Map timestamps to indices
        long_ma_indices = []
        for t in long_ma_times:
            try:
                idx = timestamps.index(t)
                long_ma_indices.append(idx)
            except ValueError:
                pass
        
        if long_ma_indices:
            ax.plot(long_ma_indices, 
                   [long_ma_values[i] for i in range(len(long_ma_indices))], 
                   color='blue', linewidth=1, label='Long MA')
    
    # Plot buy signals
    if signals_data and "buy" in signals_data and signals_data["buy"]:
        buy_data = signals_data["buy"]
        buy_times = [parser.parse(x[0]) for x in buy_data]
        buy_prices = [x[1] for x in buy_data]
        
        # Map timestamps to indices
        buy_indices = []
        buy_values = []
        for i, t in enumerate(buy_times):
            try:
                idx = timestamps.index(t)
                buy_indices.append(idx)
                buy_values.append(buy_prices[i])
            except ValueError:
                pass
        
        if buy_indices:
            ax.scatter(buy_indices, buy_values, 
                      color='lime', marker='^', s=100, label='Buy Signal')
    
    # Plot sell signals
    if signals_data and "sell" in signals_data and signals_data["sell"]:
        sell_data = signals_data["sell"]
        sell_times = [parser.parse(x[0]) for x in sell_data]
        sell_prices = [x[1] for x in sell_data]
        
        # Map timestamps to indices
        sell_indices = []
        sell_values = []
        for i, t in enumerate(sell_times):
            try:
                idx = timestamps.index(t)
                sell_indices.append(idx)
                sell_values.append(sell_prices[i])
            except ValueError:
                pass
        
        if sell_indices:
            ax.scatter(sell_indices, sell_values, 
                      color='red', marker='v', s=100, label='Sell Signal')
    
    # Set labels and title
    ax.set_title(f'{symbol} Trading Chart')
    ax.set_xlabel('Candle Number')
    ax.set_ylabel('Price')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Set x-axis tick labels to show dates
    tick_indices = np.linspace(0, len(timestamps)-1, min(10, len(timestamps))).astype(int)
    ax.set_xticks(tick_indices)
    ax.set_xticklabels([timestamps[int(i)].strftime('%Y-%m-%d %H:%M') for i in tick_indices], rotation=45)
    
    # Update title with timestamp
    current_time = datetime.now()
    ax.set_title(f"{symbol} - Last updated: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    fig.canvas.draw_idle()

def main():
    parser = argparse.ArgumentParser(description="View trading charts in real-time")
    parser.add_argument("--symbol", type=str, default="BTCUSD", help="Symbol to display")
    parser.add_argument("--charts-dir", type=str, default="charts", help="Directory containing chart data")
    parser.add_argument("--interval", type=int, default=5, help="Update interval in seconds")
    args = parser.parse_args()
    
    # Set up plot style
    plt.style.use('dark_background')
    
    # Create figure and axes
    fig, ax = plt.subplots(figsize=(12, 8))
    fig.tight_layout()
    
    # Set up the animation
    ani = FuncAnimation(fig, update_plot, fargs=(args.symbol, args.charts_dir, ax, fig),
                        interval=args.interval * 1000, cache_frame_data=False)
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
