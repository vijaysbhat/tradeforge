# TradeForge

A cloud-native trading bot platform built on AWS for algorithmic trading across multiple asset classes including cryptocurrencies and stocks.

## Architecture Overview

TradeForge follows a microservices architecture with the following key components:

### Core Components
- **Trading Engine**: Central system coordinating trading activities and responding to market signals
- **Data Service**: Handles market data acquisition, normalization, and storage from external sources
- **Strategy Service**: Pluggable trading strategies with standardized interfaces
- **Execution Service**: Manages order execution through various broker integrations
- **Backtesting Engine**: Tests strategies against historical data
- **Paper Trading Service**: Simulated trading with live market data

### Supporting Infrastructure
- **Monitoring & Observability**: Comprehensive metrics, logging, and alerting
- **Configuration Management**: System for managing trading parameters and settings
- **User Interface**: Simple dashboard for monitoring system status and performance

### AWS Services Utilized
- ECS/EKS for container orchestration
- Lambda for event-driven components
- DynamoDB for configuration and trade data
- S3 for historical market data
- EventBridge for event-driven communication
- CloudWatch for monitoring and logging
- SQS/SNS for message queuing and notifications
- Secrets Manager for secure credential storage

## Features

- Multi-asset trading (crypto, stocks, forex, etc.)
- Pluggable broker interfaces
- Customizable trading strategies
- Backtesting with historical data
- Paper trading with live price feeds
- Real-time monitoring and alerting
- Performance analytics and reporting
- Autonomous operation based on market signals

## Installation

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Git
- AWS CLI (for cloud deployment)

### Local Development Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/vijaysbhat/tradeforge.git
   cd tradeforge
   ```

2. **Create and activate a virtual environment**

   ```bash
   # On Linux/macOS
   python -m venv venv
   source venv/bin/activate

   # On Windows
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

   Note: The project uses the `ta` package for technical analysis, which is a pure Python implementation that doesn't require any external C libraries.

4. **Set up environment variables**

   Create a `.env` file in the project root:

   ```
   # API Keys
   GEMINI_API_KEY=your_api_key
   GEMINI_API_SECRET=your_api_secret
   
   # Environment
   USE_SANDBOX=True
   ```

5. **Test the installation**

   ```bash
   # Test market data retrieval
   python scripts/test_gemini_data.py --symbol btcusd
   ```

### Test Scripts

* Test Gemini Data Feed
    ```bash
    # Basic usage with default parameters (BTC/USD)
    python scripts/test_gemini_data.py

    # Specify a different symbol
    python scripts/test_gemini_data.py --symbol ethusd

    # Show more detailed order book
    python scripts/test_gemini_data.py --depth 10

    # Show more recent trades
    python scripts/test_gemini_data.py --trades 20

    # Show different candle interval
    python scripts/test_gemini_data.py --interval 15m

    # Subscribe to live updates for 60 seconds
    python scripts/test_gemini_data.py --live 60

    # Use Gemini sandbox environment
    python scripts/test_gemini_data.py --sandbox
    ```

* Test Gemini Trade Execution

    ```bash
    # View account information
    python scripts/test_gemini_trading.py --action account

    # View current positions
    python scripts/test_gemini_trading.py --action positions

    # List open orders
    python scripts/test_gemini_trading.py --action orders

    # Place a limit buy order
    python scripts/test_gemini_trading.py --action buy --symbol btcusd --amount 0.01 --price 30000

    # Place a limit sell order
    python scripts/test_gemini_trading.py --action sell --symbol btcusd --amount 0.01 --price 30000

    # Check order status
    python scripts/test_gemini_trading.py --action status --order-id ORDER_ID

    # Cancel an order
    python scripts/test_gemini_trading.py --action cancel --order-id ORDER_ID

    # Use sandbox environment
    python scripts/test_gemini_trading.py --action account --sandbox
    ```


### AWS Deployment (Coming Soon)

Instructions for deploying TradeForge to AWS will be provided in future updates.

## Project Structure

```
tradeforge/
├── infrastructure/  # AWS CDK or CloudFormation templates
├── src/
│   ├── core/        # Core trading engine
│   ├── data/        # Data service
│   ├── strategy/    # Strategy implementations
│   ├── execution/   # Order execution
│   ├── backtesting/ # Backtesting engine
│   ├── paper/       # Paper trading service
│   ├── monitoring/  # Monitoring and observability
│   └── config/      # Configuration management
└── tests/           # Unit and integration tests
```

## Getting Started

### Running Your First Strategy

Documentation on creating and running trading strategies will be available soon.

## Testing

This project includes automated tests to verify the functionality of the trading engine and strategies.

### Running Tests

To run all tests:

```bash
python -m pytest
```

To run specific test files:

```bash
python -m pytest tests/test_trading_engine_sma.py
```

To run tests with verbose output:

```bash
python -m pytest -v
```

### Test Coverage

To run tests with coverage reporting:

```bash
python -m pytest --cov=src tests/
```

### Writing Tests

When adding new features, please include appropriate tests. The project uses pytest and pytest-asyncio for testing asynchronous code.

Example test structure:

```python
import pytest

@pytest.mark.asyncio
async def test_something_async():
    # Setup
    ...
    # Test
    result = await some_async_function()
    # Assert
    assert result == expected_value
```

### Mocking External Services

For tests that would normally require external API connections, use the `unittest.mock` or `pytest-mock` libraries to mock these dependencies. See `tests/test_trading_engine_sma.py` for an example of how to mock the data service and execution service.

## Development

### Adding a New Data Provider

To add a new market data provider, create a new class that implements the `MarketDataProvider` interface in `src/data/base.py`.

### Adding a New Broker

To add a new broker for order execution, create a new class that implements the `Broker` interface in `src/execution/base.py`.

## Visualization

TradeForge includes built-in visualization capabilities to help you monitor and analyze your trading strategies in real-time.

### Enabling Visualization

Visualization is configured in the `config.json` file:

```json
"visualization": {
  "enabled": true,
  "charts_dir": "charts"
}
```

You can also enable or disable visualization for specific strategies:

```json
"strategies": {
  "simple_moving_average": {
    ...
    "enable_visualization": true,
    "charts_dir": "charts"
  }
}
```

### What Gets Visualized

The visualization system creates charts that include:

1. Price candlesticks
2. Moving averages (short and long term)
3. Buy signals (green triangles)
4. Sell signals (red triangles)

Charts are automatically generated and saved whenever a trading signal occurs.

### Viewing Charts

#### Option 1: View Saved Charts

Charts are saved to the `charts` directory (or the directory specified in your config) as PNG files. You can open these files with any image viewer.

#### Option 2: Real-time Chart Viewer

To view charts in real-time as they're generated:

```bash
python scripts/view_charts.py --symbol BTCUSD
```

Options:
- `--symbol`: The trading symbol to display (default: BTCUSD)
- `--charts-dir`: Directory containing chart images (default: charts)
- `--interval`: Update interval in seconds (default: 5)

Example:
```bash
python scripts/view_charts.py --symbol ETHUSD --interval 2
```

### How the Visualization Works

The visualization system works by:

1. The trading engine writes trading data (candles, indicators, signals) to JSON files in the `charts/data` directory
2. The view_charts.py script reads these files and creates real-time visualizations
3. Charts are also saved as PNG images in the `charts` directory

This approach allows you to view charts in a separate process from the trading engine.

### Customizing Visualization

You can customize the visualization by modifying the `src/visualization/chart.py` file:

- Change colors and styles
- Add additional indicators
- Modify chart layout and dimensions

### Adding Visualization to Custom Strategies

When creating custom strategies, you can add visualization support by:

1. Initialize the chart in your strategy's `initialize` method:
   ```python
   if self.enable_visualization:
       self.chart = TradingChart(self.symbol, self.charts_dir)
   ```

2. Add candles to the chart in your `on_candle` method:
   ```python
   if self.enable_visualization and self.chart:
       self.chart.add_candle(candle)
   ```

3. Update indicators in your signal generation logic:
   ```python
   if self.enable_visualization and self.chart:
       self.chart.update_moving_averages(short_ma, long_ma)
   ```

4. Add trading signals when they're generated:
   ```python
   if self.enable_visualization and self.chart:
       self.chart.add_signal(candle.timestamp, price, OrderSide.BUY)
       self.chart.plot(save=True)
   ```

## License

[License information]
