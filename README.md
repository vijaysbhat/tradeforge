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

## Development

### Adding a New Data Provider

To add a new market data provider, create a new class that implements the `MarketDataProvider` interface in `src/data/base.py`.

### Adding a New Broker

To add a new broker for order execution, create a new class that implements the `Broker` interface in `src/execution/base.py`.

## License

[License information]
