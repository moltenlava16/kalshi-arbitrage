"""
Kalshi Fee Configuration
Last updated: June 18, 2025

This module contains the official Kalshi fee schedule and calculation logic.
"""

from decimal import Decimal, ROUND_UP
from typing import Dict, Set, Optional


class KalshiFeeSchedule:
    """
    Official Kalshi fee schedule as of June 18, 2025
    
    General Trading Fee Formula:
    fees = round up(0.07 × C × P × (1-P))
    
    Where:
    - C = number of contracts
    - P = price in dollars
    - Fees are only charged on taker orders (immediately matched)
    """
    
    # Fee rates by market type
    GENERAL_RATE = Decimal("0.07")  # 7% of expected profit
    SP500_NASDAQ_RATE = Decimal("0.035")  # 3.5% of expected profit
    MAKER_FEE_PER_CONTRACT = Decimal("0.0025")  # $0.0025 per contract
    
    # S&P500 and NASDAQ-100 market prefixes
    REDUCED_FEE_PREFIXES = {"INX", "NASDAQ100"}
    
    # Series with maker fees (as of June 18, 2025)
    MAKER_FEE_SERIES = {
        "KXAAAGASM", "KXGDP", "KXPAYROLLS", "KXU3", "KXEGGS", "KXCPI", "KXCPIYOY",
        "KXFEDDECISION", "KXFED", "KXNBA", "KXNBAEAST", "KXNBAWEST", "KXNBASERIES",
        "KXNBAGAME", "KXNHL", "KXNHLEAST", "KXNHLWEST", "KXNHLSERIES", "KXNHLGAME",
        "KXINDY500", "KXPGA", "KXUSOPEN", "KXPGARYDER", "KXTHEOPEN", "KXPGASOLHEIM",
        "KXFOMENSINGLES", "KXFOWOMENSINGLES", "KXWMENSINGLES", "KXWWOMENSINGLES",
        "KXUSOMENSINGLES", "KXUSOWOMENSINGLES", "KXAOMENSINGLES", "KXAOWOMENSINGLES",
        "KXNFLGAME", "KXUEFACL", "KXNBAFINALSMVP", "KXCONNSMYTHE", "KXFOMEN",
        "KXFOWOMEN", "KXNATHANSHD", "KXNATHANDOGS", "KXCLUBWC", "KXTOURDEFRANCE",
        "KXNASCARRACE"
    }
    
    # Other fees (for reference, not used in trading calculations)
    SETTLEMENT_FEE = Decimal("0")
    MEMBERSHIP_FEE = Decimal("0")
    ACH_DEPOSIT_FEE = Decimal("0")
    ACH_WITHDRAWAL_FEE = Decimal("0")
    DEBIT_DEPOSIT_FEE_PERCENT = Decimal("0.02")  # 2%
    DEBIT_WITHDRAWAL_FEE_FIXED = Decimal("2")    # $2
    
    @classmethod
    def get_fee_rate(cls, market_ticker: str) -> Decimal:
        """Get the appropriate fee rate for a market"""
        # Check if it's a reduced fee market (S&P500 or NASDAQ-100)
        for prefix in cls.REDUCED_FEE_PREFIXES:
            if market_ticker.startswith(prefix):
                return cls.SP500_NASDAQ_RATE
        return cls.GENERAL_RATE
    
    @classmethod
    def has_maker_fees(cls, series_ticker: str) -> bool:
        """Check if a series has maker fees"""
        return series_ticker in cls.MAKER_FEE_SERIES
    
    @classmethod
    def round_up_to_cent(cls, value: Decimal) -> Decimal:
        """Round up to the next cent as per Kalshi rules"""
        cents = value * 100
        return (cents.to_integral_value(rounding=ROUND_UP) / 100).quantize(
            Decimal("0.01"), rounding=ROUND_UP
        )
    
    @classmethod
    def calculate_trading_fee(cls, price: Decimal, contracts: int, 
                            market_ticker: str, is_maker: bool = False) -> Decimal:
        """
        Calculate trading fee for a single trade
        
        Args:
            price: Contract price in dollars (0.50 = $0.50)
            contracts: Number of contracts
            market_ticker: Full market ticker (e.g., "KXFED-23DEC-T3.00")
            is_maker: Whether this is a maker order (resting on book)
        
        Returns:
            Fee amount in dollars
        """
        # Extract series from ticker
        series = market_ticker.split("-")[0] if "-" in market_ticker else market_ticker
        
        # Check if this is a maker fee market
        if cls.has_maker_fees(series) and is_maker:
            # Maker fee: flat fee per contract
            return cls.round_up_to_cent(cls.MAKER_FEE_PER_CONTRACT * contracts)
        
        # Only charge trading fees for taker orders
        if is_maker:
            return Decimal("0")
        
        # Get appropriate fee rate
        fee_rate = cls.get_fee_rate(market_ticker)
        
        # Calculate fee: rate × C × P × (1-P)
        fee = fee_rate * contracts * price * (Decimal("1") - price)
        
        return cls.round_up_to_cent(fee)
    
    @classmethod
    def calculate_maker_rebate(cls, trades: list) -> Decimal:
        """
        Calculate potential maker fee rebate for the month
        
        Rebate = round up(round up(C × $0.0025) - (C × $0.0025))
        Only paid if total rebate > $10 for the month
        """
        total_rebate = Decimal("0")
        
        for contracts in trades:
            actual_fee = cls.round_up_to_cent(cls.MAKER_FEE_PER_CONTRACT * contracts)
            theoretical_fee = cls.MAKER_FEE_PER_CONTRACT * contracts
            rebate = actual_fee - theoretical_fee
            total_rebate += rebate
        
        return total_rebate if total_rebate > Decimal("10") else Decimal("0")


# Pre-calculated fee table for quick reference (from Kalshi's documentation)
FEE_TABLE_GENERAL = {
    # Price: (Fee for 1 contract, Fee for 100 contracts)
    Decimal("0.01"): (Decimal("0.01"), Decimal("0.07")),
    Decimal("0.05"): (Decimal("0.01"), Decimal("0.34")),
    Decimal("0.10"): (Decimal("0.01"), Decimal("0.63")),
    Decimal("0.15"): (Decimal("0.01"), Decimal("0.90")),
    Decimal("0.20"): (Decimal("0.02"), Decimal("1.12")),
    Decimal("0.25"): (Decimal("0.02"), Decimal("1.32")),
    Decimal("0.30"): (Decimal("0.02"), Decimal("1.47")),
    Decimal("0.35"): (Decimal("0.02"), Decimal("1.60")),
    Decimal("0.40"): (Decimal("0.02"), Decimal("1.68")),
    Decimal("0.45"): (Decimal("0.02"), Decimal("1.74")),
    Decimal("0.50"): (Decimal("0.02"), Decimal("1.75")),
    Decimal("0.55"): (Decimal("0.02"), Decimal("1.74")),
    Decimal("0.60"): (Decimal("0.02"), Decimal("1.68")),
    Decimal("0.65"): (Decimal("0.02"), Decimal("1.60")),
    Decimal("0.70"): (Decimal("0.02"), Decimal("1.47")),
    Decimal("0.75"): (Decimal("0.02"), Decimal("1.32")),
    Decimal("0.80"): (Decimal("0.02"), Decimal("1.12")),
    Decimal("0.85"): (Decimal("0.01"), Decimal("0.90")),
    Decimal("0.90"): (Decimal("0.01"), Decimal("0.63")),
    Decimal("0.95"): (Decimal("0.01"), Decimal("0.34")),
    Decimal("0.99"): (Decimal("0.01"), Decimal("0.07")),
}

FEE_TABLE_SP500_NASDAQ = {
    # Price: (Fee for 1 contract, Fee for 100 contracts)
    Decimal("0.01"): (Decimal("0.01"), Decimal("0.04")),
    Decimal("0.05"): (Decimal("0.01"), Decimal("0.17")),
    Decimal("0.10"): (Decimal("0.01"), Decimal("0.32")),
    Decimal("0.15"): (Decimal("0.01"), Decimal("0.45")),
    Decimal("0.20"): (Decimal("0.01"), Decimal("0.56")),
    Decimal("0.25"): (Decimal("0.01"), Decimal("0.66")),
    Decimal("0.30"): (Decimal("0.01"), Decimal("0.74")),
    Decimal("0.35"): (Decimal("0.01"), Decimal("0.80")),
    Decimal("0.40"): (Decimal("0.01"), Decimal("0.84")),
    Decimal("0.45"): (Decimal("0.01"), Decimal("0.87")),
    Decimal("0.50"): (Decimal("0.01"), Decimal("0.88")),
    Decimal("0.55"): (Decimal("0.01"), Decimal("0.87")),
    Decimal("0.60"): (Decimal("0.01"), Decimal("0.84")),
    Decimal("0.65"): (Decimal("0.01"), Decimal("0.80")),
    Decimal("0.70"): (Decimal("0.01"), Decimal("0.74")),
    Decimal("0.75"): (Decimal("0.01"), Decimal("0.66")),
    Decimal("0.80"): (Decimal("0.01"), Decimal("0.56")),
    Decimal("0.85"): (Decimal("0.01"), Decimal("0.45")),
    Decimal("0.90"): (Decimal("0.01"), Decimal("0.32")),
    Decimal("0.95"): (Decimal("0.01"), Decimal("0.17")),
    Decimal("0.99"): (Decimal("0.01"), Decimal("0.04")),
}


def get_fee_for_price(price: Decimal, contracts: int, market_type: str = "general") -> Optional[Decimal]:
    """
    Quick fee lookup using pre-calculated tables
    
    Args:
        price: Contract price (must match table values exactly)
        contracts: Number of contracts
        market_type: "general" or "sp500_nasdaq"
    
    Returns:
        Fee amount or None if price not in table
    """
    table = FEE_TABLE_SP500_NASDAQ if market_type == "sp500_nasdaq" else FEE_TABLE_GENERAL
    
    if price in table:
        fee_1, fee_100 = table[price]
        if contracts == 1:
            return fee_1
        elif contracts == 100:
            return fee_100
    
    # Fall back to calculation if not in table
    return None