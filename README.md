# Kalshi Arbitrage Trading System

An automated trading system that identifies and executes cross-option arbitrage opportunities on Kalshi's prediction markets using real-time WebSocket data feeds.

##  Overview
![perfectly-round-chinchilla-camerons-chinchillas-15-58ad5374a8afb__700](https://github.com/user-attachments/assets/64f70c47-ad14-45eb-a016-df79db8b04e1)

This system exploits logical inconsistencies in related market options on Kalshi. For example, if "Above 400" is priced higher than "Above 300" in the same market, this creates a guaranteed profit opportunity since logically P(Above 400) ≤ P(Above 300).

##  License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

##  Disclaimer

This software is for educational purposes. Trading prediction markets involves risk. Always understand the markets you're trading and never risk more than you can afford to lose.

---

**Note**: This project requires active Kalshi API credentials and is subject to Kalshi's terms of service and API rate limits.
