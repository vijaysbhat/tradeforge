#!/usr/bin/env python3
"""
Gemini Trading Test Script

This script demonstrates how to use the Gemini broker to place and manage orders.
It can be run directly from the command line.

Usage:
    python scripts/test_gemini_trading.py --symbol btcusd --action buy --amount 0.001 --price 30000
    python scripts/test_gemini_trading.py --symbol btcusd --action sell --amount 0.001 --price 40000
    python scripts/test_gemini_trading.py --symbol btcusd --action cancel --order-id ORDER_ID
    python scripts/test_gemini_trading.py --symbol btcusd --action status --order-id ORDER_ID
    python scripts/test_gemini_trading.py --action account
    python scripts/test_gemini_trading.py --action orders
    python scripts/test_gemini_trading.py --action positions

Note: This script requires valid Gemini API credentials with trading permissions.
"""

import asyncio
import argparse
import sys
import os
import json
import datetime
from decimal import Decimal
import dotenv

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.execution.service import ExecutionService
from src.execution.brokers.gemini import GeminiBroker
from src.execution.base import OrderSide, OrderType, OrderStatus


async def display_account_info(execution_service, broker_name):
    """Display account information including balances."""
    print("\n=== Account Information ===")
    account = await execution_service.get_account_info(broker_name)
    
    print(f"Account ID: {account.id}")
    print("\nBalances:")
    print("Asset      | Free         | Locked       | Total")
    print("-" * 50)
    
    # Sort balances by total value (descending)
    sorted_balances = sorted(account.balances, key=lambda b: b.total, reverse=True)
    
    for balance in sorted_balances:
        if balance.total > 0:  # Only show assets with non-zero balance
            print(f"{balance.asset.ljust(10)} | {balance.free:.8f} | {balance.locked:.8f} | {balance.total:.8f}")


async def display_positions(execution_service, broker_name):
    """Display current positions."""
    print("\n=== Current Positions ===")
    positions = await execution_service.get_positions(broker_name)
    
    if not positions:
        print("No positions found.")
        return
    
    print("Symbol     | Quantity     | Entry Price  | Mark Price  | Unrealized P&L")
    print("-" * 75)
    
    for position in positions:
        print(f"{position.symbol.ljust(10)} | {position.quantity:.8f} | "
              f"${position.entry_price:.2f} | ${position.mark_price:.2f} | ${position.unrealized_pnl:.2f}")


async def place_order(execution_service, broker_name, symbol, side, order_type, amount, price=None):
    """Place a new order."""
    print(f"\n=== Placing {side.value.upper()} {order_type.value.upper()} Order ===")
    print(f"Symbol: {symbol}")
    print(f"Amount: {amount}")
    if price:
        print(f"Price: ${price}")
    
    # Confirm before placing real orders
    confirm = input("\nAre you sure you want to place this order? (y/n): ")
    if confirm.lower() != 'y':
        print("Order cancelled by user.")
        return
    
    try:
        order = await execution_service.place_order(
            broker_name=broker_name,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=float(amount),
            price=float(price) if price else None
        )
        
        print("\nOrder placed successfully:")
        print(f"Order ID: {order.id}")
        print(f"Status: {order.status.value}")
        print(f"Symbol: {order.symbol}")
        print(f"Side: {order.side.value}")
        print(f"Type: {order.type.value}")
        print(f"Quantity: {order.quantity}")
        if order.price:
            print(f"Price: ${order.price}")
        print(f"Created at: {order.created_at}")
        
        return order.id
    
    except Exception as e:
        print(f"\nError placing order: {str(e)}")


async def cancel_order(execution_service, broker_name, order_id):
    """Cancel an existing order."""
    print(f"\n=== Cancelling Order {order_id} ===")
    
    try:
        order = await execution_service.cancel_order(broker_name, order_id)
        
        print("\nOrder cancelled successfully:")
        print(f"Order ID: {order.id}")
        print(f"Status: {order.status.value}")
        print(f"Symbol: {order.symbol}")
        print(f"Side: {order.side.value}")
        print(f"Type: {order.type.value}")
        print(f"Quantity: {order.quantity}")
        if order.price:
            print(f"Price: ${order.price}")
        print(f"Updated at: {order.updated_at}")
        
    except Exception as e:
        print(f"\nError cancelling order: {str(e)}")


async def get_order_status(execution_service, broker_name, order_id):
    """Get the status of a specific order."""
    print(f"\n=== Order Status for {order_id} ===")
    
    try:
        order = await execution_service.get_order(broker_name, order_id)
        
        print(f"Order ID: {order.id}")
        print(f"Status: {order.status.value}")
        print(f"Symbol: {order.symbol}")
        print(f"Side: {order.side.value}")
        print(f"Type: {order.type.value}")
        print(f"Quantity: {order.quantity}")
        if order.price:
            print(f"Price: ${order.price}")
        print(f"Filled: {order.filled_quantity} / {order.quantity}")
        if order.average_price:
            print(f"Average Fill Price: ${order.average_price}")
        print(f"Created at: {order.created_at}")
        print(f"Updated at: {order.updated_at}")
        
    except Exception as e:
        print(f"\nError getting order status: {str(e)}")


async def list_orders(execution_service, broker_name, symbol=None):
    """List all open orders."""
    print("\n=== Open Orders ===")
    
    try:
        orders = await execution_service.get_orders(broker_name, symbol)
        
        if not orders:
            print("No open orders found.")
            return
        
        print("Order ID                | Symbol     | Side  | Type   | Quantity    | Price       | Status")
        print("-" * 100)
        
        for order in orders:
            price_str = f"${order.price:.2f}" if order.price else "Market"
            print(f"{order.id[:20].ljust(24)} | {order.symbol.ljust(10)} | "
                  f"{order.side.value.ljust(5)} | {order.type.value.ljust(6)} | "
                  f"{order.quantity:.8f} | {price_str.ljust(12)} | {order.status.value}")
        
    except Exception as e:
        print(f"\nError listing orders: {str(e)}")


async def main():
    # Load environment variables from .env file
    dotenv.load_dotenv()
    
    parser = argparse.ArgumentParser(description="Test Gemini trading functionality")
    parser.add_argument("--symbol", default="btcusd", help="Trading symbol (e.g., btcusd, ethusd)")
    parser.add_argument("--action", required=True, 
                        choices=["buy", "sell", "cancel", "status", "account", "orders", "positions"],
                        help="Action to perform")
    parser.add_argument("--amount", type=float, help="Amount to buy/sell")
    parser.add_argument("--price", type=float, help="Price for limit orders")
    parser.add_argument("--order-id", help="Order ID for cancel/status actions")
    parser.add_argument("--api-key", help="Gemini API key (defaults to GEMINI_API_KEY env var)")
    parser.add_argument("--api-secret", help="Gemini API secret (defaults to GEMINI_API_SECRET env var)")
    parser.add_argument("--sandbox", action="store_true", help="Use Gemini sandbox environment")
    
    args = parser.parse_args()
    
    # Get API credentials from args or environment variables
    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    api_secret = args.api_secret or os.environ.get("GEMINI_API_SECRET")
    
    if not api_key or not api_secret:
        print("Error: Gemini API credentials are required. Set GEMINI_API_KEY and GEMINI_API_SECRET "
              "environment variables or provide --api-key and --api-secret arguments.")
        return
    
    # Initialize the execution service
    execution_service = ExecutionService()
    
    # Create and register the Gemini broker
    gemini_broker = GeminiBroker(
        api_key=api_key,
        api_secret=api_secret,
        sandbox=args.sandbox
    )
    broker_name = "gemini"
    execution_service.register_broker(broker_name, gemini_broker)
    
    try:
        # Perform the requested action
        if args.action == "account":
            await display_account_info(execution_service, broker_name)
        
        elif args.action == "positions":
            await display_positions(execution_service, broker_name)
        
        elif args.action == "orders":
            await list_orders(execution_service, broker_name, args.symbol)
        
        elif args.action == "buy":
            if not args.amount:
                print("Error: --amount is required for buy action")
                return
            
            # Default to limit order if price is provided, otherwise market order
            order_type = OrderType.LIMIT if args.price else OrderType.MARKET
            await place_order(execution_service, broker_name, args.symbol, 
                             OrderSide.BUY, order_type, args.amount, args.price)
        
        elif args.action == "sell":
            if not args.amount:
                print("Error: --amount is required for sell action")
                return
            
            # Default to limit order if price is provided, otherwise market order
            order_type = OrderType.LIMIT if args.price else OrderType.MARKET
            await place_order(execution_service, broker_name, args.symbol, 
                             OrderSide.SELL, order_type, args.amount, args.price)
        
        elif args.action == "cancel":
            if not args.order_id:
                print("Error: --order-id is required for cancel action")
                return
            
            await cancel_order(execution_service, broker_name, args.order_id)
        
        elif args.action == "status":
            if not args.order_id:
                print("Error: --order-id is required for status action")
                return
            
            await get_order_status(execution_service, broker_name, args.order_id)
    
    except Exception as e:
        print(f"Error: {str(e)}")
    
    finally:
        # Clean up
        await execution_service.close_all()


if __name__ == "__main__":
    asyncio.run(main())
