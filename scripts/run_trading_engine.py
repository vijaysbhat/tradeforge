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


# Basic logger configuration to start with
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def load_config(config_file: str = "config.json") -> Dict[str, Any]:
    """Load configuration from a JSON file."""
    # Load environment variables from .env file if it exists
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("Loaded environment variables from .env file")
    except ImportError:
        logger.warning("python-dotenv not installed, skipping .env file loading")
    
    # Get environment variables for API keys
    gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
    gemini_api_secret = os.environ.get("GEMINI_API_SECRET", "")
    gemini_sandbox_api_key = os.environ.get("GEMINI_SANDBOX_API_KEY", "")
    gemini_sandbox_api_secret = os.environ.get("GEMINI_SANDBOX_API_SECRET", "")
    use_sandbox = os.environ.get("USE_SANDBOX", "true").lower() == "true"
    
    # Log environment variables (masked for security)
    logger.info(f"GEMINI_API_KEY: {'*' * min(5, len(gemini_api_key))}{'*' * 5 if gemini_api_key else 'Not set'}")
    logger.info(f"GEMINI_API_SECRET: {'*' * min(5, len(gemini_api_secret))}{'*' * 5 if gemini_api_secret else 'Not set'}")
    logger.info(f"GEMINI_SANDBOX_API_KEY: {'*' * min(5, len(gemini_sandbox_api_key))}{'*' * 5 if gemini_sandbox_api_key else 'Not set'}")
    logger.info(f"GEMINI_SANDBOX_API_SECRET: {'*' * min(5, len(gemini_sandbox_api_secret))}{'*' * 5 if gemini_sandbox_api_secret else 'Not set'}")
    logger.info(f"USE_SANDBOX: {use_sandbox}")
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
            
            # Reconfigure logging based on loaded config
            logging_config = config.get("logging", {})
            logging_level = getattr(logging, logging_config.get("level", "INFO"))
            
            # Reset root logger
            for handler in logging.root.handlers[:]:
                logging.root.removeHandler(handler)
                
            logging.basicConfig(
                level=logging_level,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.StreamHandler(),
                    logging.FileHandler(logging_config.get("file", "trading_engine.log"))
                ]
            )
            
            # Set specific loggers based on configuration
            for module, level in logging_config.get("modules", {}).items():
                logging.getLogger(module).setLevel(getattr(logging, level))
                
            logger.info(f"Logging reconfigured at {logging_level} level")
            
            return config
    except FileNotFoundError:
        logger.warning(f"Config file {config_file} not found, using default configuration")
        default_config = {
            "providers": ["gemini"],
            "brokers": ["gemini"],
            "use_sandbox": use_sandbox,  # Use value from environment variable
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
            "symbols": ["BTCUSD", "ETHUSD"],
            "logging": {
                "level": "INFO",
                "file": "trading_engine.log",
                "modules": {
                    "src.execution.brokers.gemini": "DEBUG"
                }
            }
        }
        
        # Configure logging with default settings
        logging_config = default_config.get("logging", {})
        logging_level = getattr(logging, logging_config.get("level", "INFO"))
        
        # Reset root logger
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
            
        logging.basicConfig(
            level=logging_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(logging_config.get("file", "trading_engine.log"))
            ]
        )
        
        # Set specific loggers based on configuration
        for module, level in logging_config.get("modules", {}).items():
            logging.getLogger(module).setLevel(getattr(logging, level))
            
        logger.info(f"Logging configured with default settings at {logging_level} level")
        
        return default_config


async def setup_services(config: Dict[str, Any]):
    """Set up all services and the trading engine."""
    # Create data service
    data_service = DataService()
    
    # Create execution service
    execution_service = ExecutionService()
    
    # Create strategy service
    strategy_service = StrategyService()
    
    # Get global sandbox mode
    use_sandbox = config.get("use_sandbox", True)
    
    # Get API keys from environment variables
    gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
    gemini_api_secret = os.environ.get("GEMINI_API_SECRET", "")
    gemini_sandbox_api_key = os.environ.get("GEMINI_SANDBOX_API_KEY", "")
    gemini_sandbox_api_secret = os.environ.get("GEMINI_SANDBOX_API_SECRET", "")
    
    # Register data providers
    for provider_name in config.get("providers", ["gemini"]):
        if provider_name == "gemini":
            # Select the appropriate API keys based on sandbox mode
            if use_sandbox:
                api_key = gemini_sandbox_api_key
                api_secret = gemini_sandbox_api_secret
                logger.info(f"Using sandbox API keys for {provider_name} data provider")
            else:
                api_key = gemini_api_key
                api_secret = gemini_api_secret
                logger.info(f"Using production API keys for {provider_name} data provider")
            
            # Log key information (masked)
            logger.info(f"API Key length: {len(api_key)}")
            logger.info(f"API Secret length: {len(api_secret)}")
            
            provider = GeminiDataProvider(
                api_key=api_key,
                api_secret=api_secret,
                sandbox=use_sandbox
            )
            data_service.register_provider(provider_name, provider)
            logger.info(f"Registered data provider: {provider_name} (sandbox: {provider.sandbox})")
    
    # Register brokers
    for broker_name in config.get("brokers", ["gemini"]):
        if broker_name == "gemini":
            # Select the appropriate API keys based on sandbox mode
            if use_sandbox:
                api_key = gemini_sandbox_api_key
                api_secret = gemini_sandbox_api_secret
                logger.info(f"Using sandbox API keys for {broker_name} broker")
            else:
                api_key = gemini_api_key
                api_secret = gemini_api_secret
                logger.info(f"Using production API keys for {broker_name} broker")
            
            # Log key information (masked)
            logger.info(f"API Key length: {len(api_key)}")
            logger.info(f"API Secret length: {len(api_secret)}")
            
            broker = GeminiBroker(
                api_key=api_key,
                api_secret=api_secret,
                sandbox=use_sandbox
            )
            execution_service.register_broker(broker_name, broker)
            logger.info(f"Registered broker: {broker_name} (sandbox: {broker.sandbox})")
    
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
        
        # Add sandbox mode to strategy config if not already present
        if "sandbox" not in strategy_config:
            strategy_config["sandbox"] = use_sandbox
        
        # Load the strategy
        strategy = strategy_service.load_strategy(strategy_id, strategy_config)
        if strategy:
            logger.info(f"Loaded strategy: {strategy_id} (sandbox: {strategy_config['sandbox']})")
    
    # Start the trading engine
    await trading_engine.start()
    
    # Add active brokers
    for broker_name in config.get("brokers", ["gemini"]):
        await trading_engine.add_broker(broker_name)
    
    # Subscribe to market data
    for symbol in config.get("symbols", []):
        for provider_name in config.get("providers", ["gemini"]):
            await trading_engine.subscribe_market_data(
                provider_name, symbol, ["ticker", "trades"]
            )
    
    # Fetch historical data for strategies
    for symbol in config.get("symbols", []):
        for provider_name in config.get("providers", ["gemini"]):
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
