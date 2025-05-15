#!/usr/bin/env python3
import os
import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import glob
from datetime import datetime
import argparse

def get_latest_chart(symbol, charts_dir="charts"):
    """Get the most recent chart file for a symbol."""
    pattern = f"{charts_dir}/{symbol}_*.png"
    files = glob.glob(pattern)
    if not files:
        return None
    
    # Sort by modification time (most recent last)
    files.sort(key=os.path.getmtime)
    return files[-1]

def update_plot(frame, symbol, charts_dir, ax, fig):
    """Update the plot with the latest chart."""
    latest_chart = get_latest_chart(symbol, charts_dir)
    if latest_chart:
        # Clear the current axes
        ax.clear()
        
        # Display the image
        img = plt.imread(latest_chart)
        ax.imshow(img)
        ax.axis('off')
        
        # Update title with timestamp
        mod_time = datetime.fromtimestamp(os.path.getmtime(latest_chart))
        ax.set_title(f"{symbol} - Last updated: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        fig.canvas.draw_idle()

def main():
    parser = argparse.ArgumentParser(description="View trading charts in real-time")
    parser.add_argument("--symbol", type=str, default="BTCUSD", help="Symbol to display")
    parser.add_argument("--charts-dir", type=str, default="charts", help="Directory containing chart images")
    parser.add_argument("--interval", type=int, default=5, help="Update interval in seconds")
    args = parser.parse_args()
    
    # Create figure and axes
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.axis('off')
    
    # Set up the animation
    ani = FuncAnimation(fig, update_plot, fargs=(args.symbol, args.charts_dir, ax, fig),
                        interval=args.interval * 1000, cache_frame_data=False)
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
