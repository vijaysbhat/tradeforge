#!/usr/bin/env python3
"""
Gemini Market Data Test Script

This script demonstrates how to use the Gemini data provider to fetch live market data.
It can be run directly from the command line.

Usage:
    python scripts/test_gemini_data.py --symbol btcusd
"""

import asyncio
import argparse
import sys
import os
import json
from datetime import datetime, timedelta

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.service import DataService
from src.data.providers.gemini import GeminiDataProvider


async def display_ticker(data_service, symbol):
    """Display current ticker information."""
    print(f"\n=== {symbol.upper()} Ticker ===")
    ticker = await data_service.get_ticker("gemini", symbol)
    print(f"Last Price: ${ticker.last:.2f}")
    print(f"Bid: ${ticker.bid:.2f}")
    print(f"Ask: ${ticker.ask:.2f}")
    print(f"24h Volume: {ticker.volume_24h:.4f}")
    print(f"Timestamp: {ticker.timestamp}")


async def display_orderbook(data_service, symbol, depth=5):
    """Display current order book."""
    print(f"\n=== {symbol.upper()} Order Book (Depth: {depth}) ===")
    orderbook = await data_service.get_orderbook("gemini", symbol, depth)
    
    print("Asks (Sell Orders):")
    for i, ask in enumerate(reversed(orderbook.asks[:depth])):
        print(f"  ${ask.price:.2f} - {ask.amount:.6f}")
    
    print("\nBids (Buy Orders):")
    for i, bid in enumerate(orderbook.bids[:depth]):
        print(f"  ${bid.price:.2f} - {bid.amount:.6f}")


async def display_recent_trades(data_service, symbol, limit=10):
    """Display recent trades."""
    print(f"\n=== {symbol.upper()} Recent Trades (Last {limit}) ===")
    trades = await data_service.get_recent_trades("gemini", symbol, limit)
    
    for trade in trades:
        side = "BUY" if trade.side == "buy" else "SELL"
        timestamp = trade.timestamp.strftime("%H:%M:%S")
        print(f"{timestamp} | {side} | ${trade.price:.2f} | {trade.amount:.6f}")


async def display_candles(data_service, symbol, interval="1m", limit=10):
    """Display historical candles."""
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=limit)
    
    print(f"\n=== {symbol.upper()} Candles ({interval}, Last {limit}) ===")
    candles = await data_service.get_candles("gemini", symbol, interval, start_time, end_time, limit)
    
    print("Timestamp           | Open     | High     | Low      | Close    | Volume")
    print("-" * 75)
    
    for candle in candles:
        timestamp = candle.timestamp.strftime("%Y-%m-%d %H:%M")
        print(f"{timestamp} | ${candle.open:.2f} | ${candle.high:.2f} | ${candle.low:.2f} | ${candle.close:.2f} | {candle.volume:.6f}")


async def subscribe_to_ticker(data_service, symbol, duration=30):
    """Subscribe to real-time ticker updates for a specified duration."""
    print(f"\n=== {symbol.upper()} Live Ticker Updates (for {duration} seconds) ===")
    
    async def ticker_callback(data):
        if "events" in data and data["events"]:
            for event in data["events"]:
                if event["type"] == "trade":
                    price = float(event["price"])
                    amount = float(event["amount"])
                    side = event["makerSide"].upper()
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    print(f"{timestamp} | {side} | ${price:.2f} | {amount:.6f}")
    
    await data_service.subscribe_ticker("gemini", symbol, ticker_callback)
    
    # Keep the script running for the specified duration
    print(f"Listening for ticker updates (press Ctrl+C to stop early)...")
    try:
        await asyncio.sleep(duration)
    except asyncio.CancelledError:
        pass
    
    print("Subscription ended.")


async def main():
    parser = argparse.ArgumentParser(description="Test Gemini market data provider")
    parser.add_argument("--symbol", default="btcusd", help="Trading symbol (e.g., btcusd, ethusd)")
    parser.add_argument("--api-key", help="Gemini API key (optional)")
    parser.add_argument("--api-secret", help="Gemini API secret (optional)")
    parser.add_argument("--sandbox", action="store_true", help="Use Gemini sandbox environment")
    parser.add_argument("--depth", type=int, default=5, help="Order book depth")
    parser.add_argument("--trades", type=int, default=10, help="Number of recent trades to display")
    parser.add_argument("--interval", default="1m", help="Candle interval (e.g., 1m, 5m, 1h, 1d)")
    parser.add_argument("--candles", type=int, default=10, help="Number of candles to display")
    parser.add_argument("--live", type=int, default=0, help="Duration in seconds to listen for live updates (0 to skip)")
    
    args = parser.parse_args()
    
    # Initialize the data service
    data_service = DataService()
    
    # Create and register the Gemini data provider
    gemini_provider = GeminiDataProvider(
        api_key=args.api_key,
        api_secret=args.api_secret,
        sandbox=args.sandbox
    )
    data_service.register_provider("gemini", gemini_provider)
    
    try:
        # Display market data
        await display_ticker(data_service, args.symbol)
        await display_orderbook(data_service, args.symbol, args.depth)
        await display_recent_trades(data_service, args.symbol, args.trades)
        await display_candles(data_service, args.symbol, args.interval, args.candles)
        
        # Subscribe to live updates if requested
        if args.live > 0:
            await subscribe_to_ticker(data_service, args.symbol, args.live)
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Clean up
        await data_service.close_all()


if __name__ == "__main__":
    asyncio.run(main())
