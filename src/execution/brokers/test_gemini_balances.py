#!/usr/bin/env python3
"""
Test script for Gemini broker balances functionality.
This script verifies that the Gemini broker can correctly fetch account balances.
"""

import asyncio
import os
import sys
import logging
from pprint import pprint

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.execution.brokers.gemini import GeminiBroker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_get_account_info(broker):
    """Test the get_account_info method which uses the /v1/balances endpoint."""
    logger.info("Testing get_account_info (balances)...")
    try:
        account_info = await broker.get_account_info()
        logger.info("Account info retrieved successfully")
        
        # Print balances in a readable format
        print("\nAccount Balances:")
        print("=" * 50)
        for balance in account_info["balances"]:
            print(f"Asset: {balance.asset}")
            print(f"  Free: {balance.free}")
            print(f"  Locked: {balance.locked}")
            print(f"  Total: {balance.total}")
            print("-" * 30)
        
        # Print raw data for debugging
        print("\nRaw API Response:")
        print("=" * 50)
        pprint(account_info["raw_data"])
        
        return True
    except Exception as e:
        logger.error(f"Error testing get_account_info: {str(e)}")
        return False

async def main():
    """Main function to run the tests."""
    # Get API credentials from environment variables
    api_key = os.environ.get("GEMINI_API_KEY")
    api_secret = os.environ.get("GEMINI_API_SECRET")
    sandbox = os.environ.get("GEMINI_SANDBOX", "true").lower() == "true"
    
    if not api_key or not api_secret:
        logger.error("Missing API credentials. Please set GEMINI_API_KEY and GEMINI_API_SECRET environment variables.")
        if sandbox:
            logger.error("For sandbox testing, set GEMINI_SANDBOX_API_KEY and GEMINI_SANDBOX_API_SECRET.")
        return
    
    logger.info(f"Initializing Gemini broker (sandbox={sandbox})...")
    broker = GeminiBroker(api_key, api_secret, sandbox)
    
    try:
        # Test account info (balances)
        success = await test_get_account_info(broker)
        if success:
            logger.info("Account info test completed successfully")
        else:
            logger.error("Account info test failed")
    finally:
        # Close the broker session
        await broker.close()
        logger.info("Broker session closed")

if __name__ == "__main__":
    asyncio.run(main())
