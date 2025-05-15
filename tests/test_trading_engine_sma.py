import asyncio
import datetime
from unittest.mock import Mock, AsyncMock
import pytest
import logging

from src.data.models import Candle, Ticker, OrderBook, Trade
from src.data.service import DataService
from src.execution.service import ExecutionService
from src.execution.base import OrderSide, OrderType, OrderStatus
from src.execution.models import Order, Position, Account, Balance
from src.engine.trading_engine import TradingEngine
from src.strategy.base import StrategySignal
from src.strategy.service import StrategyService
from strategies.simple_moving_average import SimpleMovingAverageStrategy


@pytest.fixture
async def trading_setup():
    """Set up the test environment."""
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Create mock services
    data_service = Mock(spec=DataService)
    execution_service = Mock(spec=ExecutionService)
    strategy_service = Mock(spec=StrategyService)
    
    # Set up async methods as AsyncMock
    data_service.get_candles = AsyncMock()
    data_service.close_all = AsyncMock()
    execution_service.place_order = AsyncMock()
    execution_service.get_account_info = AsyncMock()
    execution_service.get_positions = AsyncMock()
    execution_service.get_orders = AsyncMock()
    execution_service.close_all = AsyncMock()
    
    # Create the trading engine with mocked services
    trading_engine = TradingEngine(
        data_service=data_service,
        execution_service=execution_service,
        strategy_service=strategy_service
    )
    
    # Create the SMA strategy
    strategy = SimpleMovingAverageStrategy()
    
    # Mock the strategy service to return our strategy
    strategy_service.get_all_strategies.return_value = {
        "SimpleMovingAverageStrategy": strategy
    }
    
    # Configure the strategy
    strategy_config = {
        "symbol": "btcusd",
        "broker": "gemini",
        "data_provider": "gemini",
        "short_period": 5,
        "long_period": 10,
        "position_size": 0.1,
        "signal_callback": trading_engine._process_signal
    }
    strategy.initialize(strategy_config)
    
    # Mock the _execute_signal method to avoid actual order execution
    trading_engine._execute_signal = AsyncMock()
    
    # Set up mock account data
    account = Account(
        id="test_account",
        balances=[
            Balance(asset="USD", free=10000.0, locked=0.0),
            Balance(asset="BTC", free=1.0, locked=0.0)
        ],
        raw_data={}  # Add the missing raw_data parameter
    )
    execution_service.get_account_info.return_value = account
    
    # Set up mock positions data
    positions = [
        Position(
            symbol="btcusd",
            quantity=0.0,  # Start with no position
            entry_price=0.0,
            mark_price=10000.0,
            unrealized_pnl=0.0,
            raw_data={}  # Add the missing raw_data parameter
        )
    ]
    execution_service.get_positions.return_value = positions
    
    # Set up mock orders data
    execution_service.get_orders.return_value = []
    
    # Start the trading engine
    await trading_engine.start()
    
    # Return all the objects needed for testing
    yield {
        "trading_engine": trading_engine,
        "strategy": strategy,
        "data_service": data_service,
        "execution_service": execution_service,
        "strategy_service": strategy_service
    }
    
    # Stop the trading engine
    await trading_engine.stop()


@pytest.mark.asyncio
async def test_sma_buy_signal_generation(trading_setup):
    """Test that the SMA strategy generates a buy signal when short MA crosses above long MA."""
    setup = await anext(trading_setup)  # Properly await the async generator
    trading_engine = setup["trading_engine"]
    strategy = setup["strategy"]
    
    # Generate historical candles where short MA is below long MA
    candles = []
    base_time = datetime.datetime.now() - datetime.timedelta(hours=15)
    
    # Create candles with decreasing prices (short MA below long MA)
    for i in range(15):
        candle = Candle(
            symbol="btcusd",
            timestamp=base_time + datetime.timedelta(hours=i),
            open=10000.0,
            high=10100.0,
            low=9900.0,
            close=10000.0 - (i * 10),  # Decreasing price
            volume=10.0
        )
        candles.append(candle)
    
    # Feed historical candles to the strategy
    for candle in candles:
        strategy.on_candle(candle, "btcusd", "1h", "gemini")
    
    # Reset the mock to track new calls
    trading_engine._execute_signal.reset_mock()
    
    # Now create candles with increasing prices to trigger a buy signal
    # The last 5 candles (short period) will have higher prices to make short MA cross above long MA
    for i in range(5):
        candle = Candle(
            symbol="btcusd",
            timestamp=base_time + datetime.timedelta(hours=15+i),
            open=9850.0,
            high=10200.0,
            low=9800.0,
            close=9850.0 + (i * 50),  # Increasing price
            volume=15.0
        )
        strategy.on_candle(candle, "btcusd", "1h", "gemini")
    
    # Verify a buy signal was generated and executed
    assert trading_engine._execute_signal.called, "No signal was executed"
    
    # Get the signal that was passed to execute_signal
    signal = trading_engine._execute_signal.call_args[0][0]
    
    # Verify signal properties
    assert signal.symbol == "btcusd"
    assert signal.side == OrderSide.BUY
    assert signal.order_type == OrderType.MARKET
    assert signal.broker == "gemini"
    assert signal.strategy_id == "SimpleMovingAverageStrategy"
    assert "MA_CROSSOVER_BUY" in signal.metadata.get("reason", "")


@pytest.mark.asyncio
async def test_sma_sell_signal_generation(trading_setup):
    """Test that the SMA strategy generates a sell signal when short MA crosses below long MA."""
    setup = await anext(trading_setup)  # Properly await the async generator
    trading_engine = setup["trading_engine"]
    strategy = setup["strategy"]
    
    # First, set up a position
    strategy.current_position = 0.5  # Set position in strategy
    
    # Generate historical candles where short MA is above long MA
    candles = []
    base_time = datetime.datetime.now() - datetime.timedelta(hours=15)
    
    # Create candles with increasing prices (short MA above long MA)
    for i in range(15):
        candle = Candle(
            symbol="btcusd",
            timestamp=base_time + datetime.timedelta(hours=i),
            open=10000.0,
            high=10100.0,
            low=9900.0,
            close=10000.0 + (i * 10),  # Increasing price
            volume=10.0
        )
        candles.append(candle)
    
    # Feed historical candles to the strategy
    for candle in candles:
        strategy.on_candle(candle, "btcusd", "1h", "gemini")
    
    # Reset the mock to track new calls
    trading_engine._execute_signal.reset_mock()
    
    # Now create candles with decreasing prices to trigger a sell signal
    # The last 5 candles (short period) will have lower prices to make short MA cross below long MA
    for i in range(5):
        candle = Candle(
            symbol="btcusd",
            timestamp=base_time + datetime.timedelta(hours=15+i),
            open=10150.0,
            high=10200.0,
            low=10000.0,
            close=10150.0 - (i * 50),  # Decreasing price
            volume=15.0
        )
        strategy.on_candle(candle, "btcusd", "1h", "gemini")
    
    # Verify a sell signal was generated and executed
    assert trading_engine._execute_signal.called, "No signal was executed"
    
    # Get the signal that was passed to execute_signal
    signal = trading_engine._execute_signal.call_args[0][0]
    
    # Verify signal properties
    assert signal.symbol == "btcusd"
    assert signal.side == OrderSide.SELL
    assert signal.order_type == OrderType.MARKET
    assert signal.quantity == 0.5  # Should sell the entire position
    assert signal.broker == "gemini"
    assert signal.strategy_id == "SimpleMovingAverageStrategy"
    assert "MA_CROSSOVER_SELL" in signal.metadata.get("reason", "")


@pytest.mark.asyncio
async def test_trading_engine_processes_signal(trading_setup):
    """Test that the trading engine correctly processes a strategy signal."""
    setup = await anext(trading_setup)  # Properly await the async generator
    trading_engine = setup["trading_engine"]
    
    # Create a signal
    signal = StrategySignal(
        symbol="btcusd",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.1,
        broker="gemini",
        strategy_id="SimpleMovingAverageStrategy",
        metadata={"reason": "TEST_SIGNAL"}
    )
    
    # Process the signal
    trading_engine._process_signal(signal)
    
    # Verify the signal was passed to execute_signal
    trading_engine._execute_signal.assert_called_once()
    executed_signal = trading_engine._execute_signal.call_args[0][0]
    
    # Verify signal properties
    assert executed_signal.symbol == "btcusd"
    assert executed_signal.side == OrderSide.BUY
    assert executed_signal.order_type == OrderType.MARKET
    assert executed_signal.quantity == 0.1
    assert executed_signal.broker == "gemini"
    assert executed_signal.strategy_id == "SimpleMovingAverageStrategy"
    assert executed_signal.metadata.get("reason") == "TEST_SIGNAL"


@pytest.mark.asyncio
async def test_position_update_notification(trading_setup):
    """Test that position updates are correctly processed by the strategy."""
    setup = await anext(trading_setup)  # Properly await the async generator
    trading_engine = setup["trading_engine"]
    strategy = setup["strategy"]
    
    # Mock the strategy's on_position_update method
    original_on_position_update = strategy.on_position_update
    strategy.on_position_update = Mock()
    
    # Create a position update
    position = Position(
        symbol="btcusd",
        quantity=0.2,
        entry_price=10000.0,
        mark_price=10100.0,
        unrealized_pnl=20.0,
        raw_data={}  # Add the missing raw_data parameter
    )
    
    # Notify the strategy of the position update
    await trading_engine._notify_position_update(position, "gemini")
    
    # Verify the strategy received the position update
    strategy.on_position_update.assert_called_once_with(position, "gemini")
    
    # Restore original method
    strategy.on_position_update = original_on_position_update


@pytest.mark.asyncio
async def test_account_update_notification(trading_setup):
    """Test that account updates are correctly processed by the strategy."""
    setup = await anext(trading_setup)  # Properly await the async generator
    trading_engine = setup["trading_engine"]
    strategy = setup["strategy"]
    
    # Mock the strategy's on_account_update method
    original_on_account_update = strategy.on_account_update
    strategy.on_account_update = Mock()
    
    # Create an account update
    account = Account(
        id="test_account",
        balances=[
            Balance(asset="USD", free=9500.0, locked=500.0),
            Balance(asset="BTC", free=1.1, locked=0.0)
        ],
        raw_data={}  # Add the missing raw_data parameter
    )
    
    # Notify the strategy of the account update
    await trading_engine._notify_account_update(account, "gemini")
    
    # Verify the strategy received the account update
    strategy.on_account_update.assert_called_once_with(account, "gemini")
    
    # Restore original method
    strategy.on_account_update = original_on_account_update


@pytest.mark.asyncio
async def test_order_update_notification(trading_setup):
    """Test that order updates are correctly processed by the strategy."""
    setup = await anext(trading_setup)  # Properly await the async generator
    trading_engine = setup["trading_engine"]
    strategy = setup["strategy"]
    
    # Mock the strategy's on_order_update method
    original_on_order_update = strategy.on_order_update
    strategy.on_order_update = Mock()
    
    # Create an order update
    order = Order(
        id="order123",
        client_order_id="client123",
        symbol="btcusd",
        side=OrderSide.BUY,
        type=OrderType.MARKET,
        quantity=0.1,
        price=None,
        stop_price=None,
        status=OrderStatus.FILLED,
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
        filled_quantity=0.1,
        average_price=10050.0,
        time_in_force="GTC",
        raw_data={"strategy_id": "SimpleMovingAverageStrategy"}  # Changed metadata to raw_data
    )
    
    # Notify the strategy of the order update
    await trading_engine._notify_order_update(order, "gemini")
    
    # Verify the strategy received the order update
    strategy.on_order_update.assert_called_once_with(order, "gemini")
    
    # Restore original method
    strategy.on_order_update = original_on_order_update
