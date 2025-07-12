# Kalshi Arbitrage Trading System

An automated trading system that identifies and executes cross-option arbitrage opportunities on Kalshi's prediction markets using real-time WebSocket data feeds.

##  Overview
![perfectly-round-chinchilla-camerons-chinchillas-15-58ad5374a8afb__700](https://github.com/user-attachments/assets/64f70c47-ad14-45eb-a016-df79db8b04e1)

This system exploits logical inconsistencies in related market options on Kalshi. For example, if "Above 400" is priced higher than "Above 300" in the same market, this creates a guaranteed profit opportunity since logically P(Above 400) ≤ P(Above 300).

### Key Features
- **Real-time arbitrage detection** using Kalshi's WebSocket API
- **Automated trade execution** with multi-leg order support
- **Risk management** with position limits and exposure controls
- **Live monitoring dashboard** for tracking opportunities and P&L
- **Fee-aware calculations** ensuring profitability after transaction costs

##  Quick Start

### Basic Usage

1. **Manual Arbitrage Calculator** (for testing):
```bash
python scripts/manual_calculator.py
```

2. **Run the automated trading system**:
```bash
python src/main.py --mode production
```

3. **Run in simulation mode** (no real trades):
```bash
python src/main.py --mode simulation
```

##  How It Works

### Arbitrage Example
Consider a market "How Many Laws will Congress Pass in 2025?" with two options:
- Option A: "Above 300"
- Option B: "Above 400"

If prices are:
- "Above 400 Yes" = $0.30
- "Above 300 Yes" = $0.25

This violates logic, creating an arbitrage opportunity:
1. **Sell** "Above 400 Yes" at $0.30
2. **Buy** "Above 300 Yes" at $0.25
3. **Collect** $0.05 guaranteed profit (minus fees)

### System Architecture
```
WebSocket Feed → Order Book Manager → Arbitrage Detector → Trade Executor
                                            ↓
                                    Risk Manager → Position Tracker
```

##  Project Structure

For detailed project structure and development phases, see [PROJECT_OUTLINE.md](PROJECT_OUTLINE.md).

Key components:
- `src/core/` - Arbitrage calculation engine
- `src/data/` - Real-time market data handling
- `src/trading/` - Trade execution and position management
- `src/monitoring/` - Dashboard and alerting

##  Configuration

### Environment Variables
Create a `.env` file in the project root:
```env
KALSHI_API_KEY=your_api_key_here
KALSHI_API_SECRET=your_api_secret_here
KALSHI_ENV=production  # or 'demo' for testing
LOG_LEVEL=INFO
```

### Trading Parameters
Edit `config/settings.py` to customize:
- Minimum profit thresholds
- Position size limits
- Risk management rules
- Market selection filters

##  Testing

Run the test suite:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest --cov=src tests/
```

##  Performance Monitoring

The system includes a real-time dashboard accessible at `http://localhost:8080` when running.

Metrics tracked:
- Active arbitrage opportunities
- Open positions and P&L
- Trade execution latency
- System health indicators

##  Risk Management

Built-in safety features:
- **Position limits** per market and overall
- **Daily loss limits** with automatic shutdown
- **Minimum profit thresholds** accounting for fees
- **Slippage protection** on order execution
- **Circuit breakers** for unusual market conditions

##  Development

### Setting up for development
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### Running in development mode
```bash
python src/main.py --mode development --debug
```

##  License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

##  Disclaimer

This software is for educational purposes. Trading prediction markets involves risk. Always understand the markets you're trading and never risk more than you can afford to lose.

---

**Note**: This project requires active Kalshi API credentials and is subject to Kalshi's terms of service and API rate limits.
