#!/usr/bin/env python3
"""
Manual Arbitrage Calculator for Kalshi Markets

This tool allows users to manually input market prices and identify
cross-option arbitrage opportunities.
"""

import sys
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from enum import Enum


class MarketRelationship(Enum):
    """Types of logical relationships between markets"""
    SUBSET = "subset"  # A implies B (A ⊆ B)
    DISJOINT = "disjoint"  # A and B are mutually exclusive
    COMPLEMENT = "complement"  # A = not B


@dataclass
class Market:
    """Represents a market option with bid/ask prices"""
    name: str
    ticker: str
    yes_bid: Decimal
    yes_ask: Decimal
    no_bid: Decimal
    no_ask: Decimal
    
    @property
    def yes_spread(self) -> Decimal:
        return self.yes_ask - self.yes_bid
    
    @property
    def no_spread(self) -> Decimal:
        return self.no_ask - self.no_bid


@dataclass
class ArbitrageOpportunity:
    """Represents a profitable arbitrage opportunity"""
    type: str
    market_a: Market
    market_b: Market
    action_a: str  # "buy_yes", "sell_yes", "buy_no", "sell_no"
    action_b: str
    size: int
    gross_profit: Decimal
    fees: Decimal
    net_profit: Decimal
    capital_required: Decimal
    return_on_capital: Decimal
    
    def __str__(self) -> str:
        return f"""
=== ARBITRAGE OPPORTUNITY FOUND ===
Type: {self.type}
Market A ({self.market_a.ticker}): {self.action_a.replace('_', ' ').title()} at ${self.get_price_a():.2f}
Market B ({self.market_b.ticker}): {self.action_b.replace('_', ' ').title()} at ${self.get_price_b():.2f}
Size: {self.size} contracts
Gross Profit: ${self.gross_profit:.2f}
Fees: ${self.fees:.2f}
NET PROFIT: ${self.net_profit:.2f}
Capital Required: ${self.capital_required:.2f}
Return on Capital: {self.return_on_capital:.1%}
"""
    
    def get_price_a(self) -> Decimal:
        if "buy" in self.action_a:
            return self.market_a.yes_ask if "yes" in self.action_a else self.market_a.no_ask
        else:
            return self.market_a.yes_bid if "yes" in self.action_a else self.market_a.no_bid
    
    def get_price_b(self) -> Decimal:
        if "buy" in self.action_b:
            return self.market_b.yes_ask if "yes" in self.action_b else self.market_b.no_ask
        else:
            return self.market_b.yes_bid if "yes" in self.action_b else self.market_b.no_bid


class FeeCalculator:
    """Calculates Kalshi trading fees"""
    
    def __init__(self, fee_tier: str = "retail"):
        # Simplified fee structure - update with actual Kalshi fees
        self.fee_rates = {
            "retail": Decimal("0.01"),  # 1% on profit
            "market_maker": Decimal("0.005"),  # 0.5% on profit
        }
        self.fee_rate = self.fee_rates.get(fee_tier, Decimal("0.01"))
    
    def calculate_fees(self, trades: List[Tuple[str, Decimal, int]]) -> Decimal:
        """
        Calculate fees for a set of trades
        trades: List of (action, price, quantity) tuples
        """
        total_fees = Decimal("0")
        
        for action, price, quantity in trades:
            if "sell" in action:
                # Fee on expected profit for sells
                expected_profit = price * quantity
                total_fees += expected_profit * self.fee_rate
            else:
                # Fee on expected profit for buys (1 - price)
                expected_profit = (Decimal("1") - price) * quantity
                total_fees += expected_profit * self.fee_rate
        
        return total_fees.quantize(Decimal("0.01"), rounding=ROUND_DOWN)


class ArbitrageCalculator:
    """Core arbitrage calculation engine"""
    
    def __init__(self, fee_calculator: FeeCalculator, min_profit: Decimal = Decimal("0.01")):
        self.fee_calculator = fee_calculator
        self.min_profit = min_profit
    
    def find_subset_arbitrage(self, market_a: Market, market_b: Market, 
                             max_size: int = 100) -> Optional[ArbitrageOpportunity]:
        """
        Find arbitrage where market_a ⊆ market_b
        E.g., "Above 400" ⊆ "Above 300"
        
        Key insight: P(A) ≤ P(B) must hold
        Arbitrage exists if market allows buying P(A) > P(B)
        """
        opportunities = []
        
        # Check: A_yes_ask > B_yes_bid (buy A YES expensive, sell B YES cheap)
        if market_a.yes_ask > market_b.yes_bid:
            # Arbitrage: Sell A YES, Buy B YES
            gross_profit_per_contract = market_a.yes_bid - market_b.yes_ask
            if gross_profit_per_contract > 0:
                size = min(max_size, 100)  # In production, check order book depth
                trades = [
                    ("sell_yes", market_a.yes_bid, size),
                    ("buy_yes", market_b.yes_ask, size)
                ]
                fees = self.fee_calculator.calculate_fees(trades)
                net_profit = (gross_profit_per_contract * size) - fees
                capital = market_b.yes_ask * size
                
                if net_profit >= self.min_profit:
                    opportunities.append(ArbitrageOpportunity(
                        type="SUBSET: A YES > B YES",
                        market_a=market_a,
                        market_b=market_b,
                        action_a="sell_yes",
                        action_b="buy_yes",
                        size=size,
                        gross_profit=gross_profit_per_contract * size,
                        fees=fees,
                        net_profit=net_profit,
                        capital_required=capital,
                        return_on_capital=net_profit / capital if capital > 0 else Decimal("0")
                    ))
        
        # Check: B_no_ask < A_no_bid (buy B NO cheap, sell A NO expensive)
        if market_b.no_ask < market_a.no_bid:
            # Arbitrage: Buy B NO, Sell A NO
            gross_profit_per_contract = market_a.no_bid - market_b.no_ask
            if gross_profit_per_contract > 0:
                size = min(max_size, 100)
                trades = [
                    ("buy_no", market_b.no_ask, size),
                    ("sell_no", market_a.no_bid, size)
                ]
                fees = self.fee_calculator.calculate_fees(trades)
                net_profit = (gross_profit_per_contract * size) - fees
                capital = market_b.no_ask * size
                
                if net_profit >= self.min_profit:
                    opportunities.append(ArbitrageOpportunity(
                        type="SUBSET: B NO < A NO",
                        market_a=market_a,
                        market_b=market_b,
                        action_a="sell_no",
                        action_b="buy_no",
                        size=size,
                        gross_profit=gross_profit_per_contract * size,
                        fees=fees,
                        net_profit=net_profit,
                        capital_required=capital,
                        return_on_capital=net_profit / capital if capital > 0 else Decimal("0")
                    ))
        
        # Return best opportunity
        return max(opportunities, key=lambda x: x.net_profit) if opportunities else None
    
    def find_disjoint_arbitrage(self, market_a: Market, market_b: Market,
                               max_size: int = 100) -> Optional[ArbitrageOpportunity]:
        """
        Find arbitrage where markets are mutually exclusive
        E.g., "Exactly 2 rate cuts" and "Exactly 3 rate cuts"
        
        Key insight: P(A) + P(B) ≤ 1 must hold
        Arbitrage exists if we can sell both for > $1 total
        """
        # Check if YES prices sum > 1
        if market_a.yes_bid + market_b.yes_bid > Decimal("1"):
            # Arbitrage: Sell both YES
            gross_profit = (market_a.yes_bid + market_b.yes_bid - Decimal("1"))
            size = min(max_size, 100)
            trades = [
                ("sell_yes", market_a.yes_bid, size),
                ("sell_yes", market_b.yes_bid, size)
            ]
            fees = self.fee_calculator.calculate_fees(trades)
            net_profit = (gross_profit * size) - fees
            capital = Decimal("0")  # Selling requires no capital upfront
            
            if net_profit >= self.min_profit:
                return ArbitrageOpportunity(
                    type="DISJOINT: Sum of YES > 1",
                    market_a=market_a,
                    market_b=market_b,
                    action_a="sell_yes",
                    action_b="sell_yes",
                    size=size,
                    gross_profit=gross_profit * size,
                    fees=fees,
                    net_profit=net_profit,
                    capital_required=capital,
                    return_on_capital=Decimal("inf") if capital == 0 else net_profit / capital
                )
        
        # Check if NO prices sum < 1 (equivalent to YES prices > 1)
        if market_a.no_ask + market_b.no_ask < Decimal("1"):
            # Arbitrage: Buy both NO
            gross_profit = Decimal("1") - (market_a.no_ask + market_b.no_ask)
            size = min(max_size, 100)
            trades = [
                ("buy_no", market_a.no_ask, size),
                ("buy_no", market_b.no_ask, size)
            ]
            fees = self.fee_calculator.calculate_fees(trades)
            net_profit = (gross_profit * size) - fees
            capital = (market_a.no_ask + market_b.no_ask) * size
            
            if net_profit >= self.min_profit:
                return ArbitrageOpportunity(
                    type="DISJOINT: Sum of NO < 1",
                    market_a=market_a,
                    market_b=market_b,
                    action_a="buy_no",
                    action_b="buy_no",
                    size=size,
                    gross_profit=gross_profit * size,
                    fees=fees,
                    net_profit=net_profit,
                    capital_required=capital,
                    return_on_capital=net_profit / capital if capital > 0 else Decimal("0")
                )
        
        return None


def get_decimal_input(prompt: str, min_val: Decimal = Decimal("0.01"), 
                     max_val: Decimal = Decimal("0.99")) -> Decimal:
    """Get decimal input with validation"""
    while True:
        try:
            value = Decimal(input(prompt).strip())
            if min_val <= value <= max_val:
                return value
            print(f"Please enter a value between ${min_val} and ${max_val}")
        except:
            print("Invalid input. Please enter a decimal number (e.g., 0.25)")


def input_market_data(name: str, ticker: str) -> Market:
    """Input market prices from user"""
    print(f"\n=== Enter prices for {name} ({ticker}) ===")
    print("Note: Enter prices in dollars (e.g., 0.25 for $0.25)")
    
    yes_bid = get_decimal_input(f"YES BID price: $")
    yes_ask = get_decimal_input(f"YES ASK price: $", min_val=yes_bid)
    no_bid = get_decimal_input(f"NO BID price: $")
    no_ask = get_decimal_input(f"NO ASK price: $", min_val=no_bid)
    
    # Validate that YES and NO prices are consistent
    if yes_bid + no_ask < Decimal("0.99") or yes_ask + no_bid > Decimal("1.01"):
        print("Warning: YES and NO prices seem inconsistent!")
    
    return Market(
        name=name,
        ticker=ticker,
        yes_bid=yes_bid,
        yes_ask=yes_ask,
        no_bid=no_bid,
        no_ask=no_ask
    )


def main():
    """Main CLI interface"""
    print("=" * 60)
    print("KALSHI ARBITRAGE CALCULATOR")
    print("=" * 60)
    print("\nThis tool identifies cross-option arbitrage opportunities.")
    print("You'll input prices for two related markets.\n")
    
    # Initialize calculator
    fee_calculator = FeeCalculator(fee_tier="retail")
    calculator = ArbitrageCalculator(fee_calculator)
    
    while True:
        print("\n" + "=" * 60)
        print("RELATIONSHIP TYPES:")
        print("1. SUBSET (A ⊆ B): e.g., 'Above 400' ⊆ 'Above 300'")
        print("2. DISJOINT (A ∩ B = ∅): e.g., 'Exactly 2' vs 'Exactly 3'")
        print("3. EXIT")
        
        choice = input("\nSelect relationship type (1-3): ").strip()
        
        if choice == "3":
            print("\nThank you for using the arbitrage calculator!")
            break
        
        if choice not in ["1", "2"]:
            print("Invalid choice. Please select 1, 2, or 3.")
            continue
        
        # Input market data
        print("\n--- Market A (more restrictive/specific) ---")
        market_a_name = input("Market A name (e.g., 'Above 400'): ").strip()
        market_a_ticker = input("Market A ticker: ").strip()
        market_a = input_market_data(market_a_name, market_a_ticker)
        
        print("\n--- Market B (less restrictive/broader) ---")
        market_b_name = input("Market B name (e.g., 'Above 300'): ").strip()
        market_b_ticker = input("Market B ticker: ").strip()
        market_b = input_market_data(market_b_name, market_b_ticker)
        
        # Find arbitrage
        opportunity = None
        if choice == "1":
            opportunity = calculator.find_subset_arbitrage(market_a, market_b)
        elif choice == "2":
            opportunity = calculator.find_disjoint_arbitrage(market_a, market_b)
        
        # Display results
        if opportunity:
            print(opportunity)
            
            # Show outcome scenarios
            print("\n=== OUTCOME SCENARIOS ===")
            if choice == "1":  # Subset
                print(f"If {market_a_name} is TRUE: Both pay out → Profit = ${opportunity.net_profit:.2f}")
                print(f"If {market_b_name} is FALSE: Neither pays → Profit = ${opportunity.net_profit:.2f}")
                print(f"If {market_b_name} TRUE but {market_a_name} FALSE: Mixed → Profit = ${opportunity.net_profit:.2f}")
            else:  # Disjoint
                print(f"If {market_a_name} is TRUE: A pays, B doesn't → Profit = ${opportunity.net_profit:.2f}")
                print(f"If {market_b_name} is TRUE: B pays, A doesn't → Profit = ${opportunity.net_profit:.2f}")
                print(f"If NEITHER is TRUE: Neither pays → Profit = ${opportunity.net_profit:.2f}")
        else:
            print("\n❌ No arbitrage opportunity found at current prices.")
            print("   (After accounting for fees and minimum profit threshold)")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()