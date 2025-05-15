#!/usr/bin/env python3
import asyncio
import logging
import os
import sys
import signal
import json
from typing import Dict, Any

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.service import DataService
from src.data.providers.gemini import GeminiDataProvider
from src.execution.service import ExecutionService
from src.execution.brokers.gemini import GeminiBroker
from src.strategy.service import StrategyService
from src.engine.trading_engine import TradingEngine
from src.strategy.base import StrategySignal


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('trading_engine.log')
    ]
)

logger = logging.getLogger(__name__)


def load_config(config_file: str = "config.json") -> Dict[str, Any]:
    """Load configuration from a JSON file."""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Config file {config_file} not found, using default configuration")
        return {
            "data_providers": {
                "gemini": {
                    "api_key": os.environ.get("GEMINI_API_KEY", ""),
                    "api_secret": os.environ.get("GEMINI_API_SECRET", ""),
                    "sandbox": True
                }
            },
            "brokers": {
                "gemini": {
                    "api_key": os.environ.get("GEMINI_API_KEY", ""),
                    "api_secret": os.environ.get("GEMINI_API_SECRET", ""),
                    "sandbox": True
                }
            },
            "strategies": {
                "simple_moving_average": {
                    "symbol": "BTCUSD",
                    "broker": "gemini",
                    "data_provider": "gemini",
                    "short_period": 20,
                    "long_period": 50,
                    "position_size": 0.1
                }
            },
            "symbols": ["BTCUSD", "ETHUSD"]
        }


async def setup_services(config: Dict[str, Any]):
    """Set up all services and the trading engine."""
    # Create data service
    data_service = DataService()
    
    # Create execution service
    execution_service = ExecutionService()
    
    # Create strategy service
    strategy_service = StrategyService()
    
    # Register data providers
    for provider_name, provider_config in config.get("data_providers", {}).items():
        if provider_name == "gemini":
            provider = GeminiDataProvider(
                api_key=provider_config.get("api_key", ""),
                api_secret=provider_config.get("api_secret", ""),
                sandbox=provider_config.get("sandbox", True)
            )
            data_service.register_provider(provider_name, provider)
            logger.info(f"Registered data provider: {provider_name}")
    
    # Register brokers
    for broker_name, broker_config in config.get("brokers", {}).items():
        if broker_name == "gemini":
            broker = GeminiBroker(
                api_key=broker_config.get("api_key", ""),
                api_secret=broker_config.get("api_secret", ""),
                sandbox=broker_config.get("sandbox", True)
            )
            execution_service.register_broker(broker_name, broker)
            logger.info(f"Registered broker: {broker_name}")
    
    # Create trading engine
    trading_engine = TradingEngine(data_service, execution_service, strategy_service)
    
    # Set up signal handler
    trading_engine.add_signal_handler(on_strategy_signal)
    
    # Discover available strategies
    strategy_service.discover_strategies()
    
    # Load strategies
    for strategy_id, strategy_config in config.get("strategies", {}).items():
        # Add signal callback to config
        strategy_config["signal_callback"] = trading_engine._process_signal
        
        # Load the strategy
        strategy = strategy_service.load_strategy(strategy_id, strategy_config)
        if strategy:
            logger.info(f"Loaded strategy: {strategy_id}")
    
    # Start the trading engine
    await trading_engine.start()
    
    # Add active brokers
    for broker_name in config.get("brokers", {}).keys():
        await trading_engine.add_broker(broker_name)
    
    # Subscribe to market data
    for symbol in config.get("symbols", []):
        for provider_name in config.get("data_providers", {}).keys():
            await trading_engine.subscribe_market_data(
                provider_name, symbol, ["ticker", "trades"]
            )
    
    # Fetch historical data for strategies
    for symbol in config.get("symbols", []):
        for provider_name in config.get("data_providers", {}).keys():
            await trading_engine.fetch_candles(
                provider_name, symbol, "1h", limit=100
            )
    
    return trading_engine


def on_strategy_signal(signal: StrategySignal):
    """Handle strategy signals."""
    logger.info(f"Received signal from {signal.strategy_id}: {signal.side.name} {signal.quantity} {signal.symbol}")


async def main():
    """Main function to run the trading engine."""
    # Load configuration
    config = load_config()
    
    # Set up services and trading engine
    trading_engine = await setup_services(config)
    
    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    
    def handle_shutdown(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        loop.create_task(shutdown(trading_engine))
    
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    # Keep the program running
    while True:
        await asyncio.sleep(1)


async def shutdown(trading_engine):
    """Gracefully shut down the trading engine."""
    await trading_engine.stop()
    # Exit the program
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
