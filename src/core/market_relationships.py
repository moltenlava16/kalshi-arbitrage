"""
Market Relationship Engine for Kalshi Arbitrage

This module automatically detects logical relationships between markets
to identify potential arbitrage opportunities.
"""

import re
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal


class RelationshipType(Enum):
    """Types of logical relationships between markets"""
    SUBSET = "subset"              # A ⊆ B (A implies B)
    SUPERSET = "superset"          # A ⊇ B (B implies A)  
    DISJOINT = "disjoint"          # A ∩ B = ∅ (mutually exclusive)
    COMPLEMENT = "complement"      # A = ¬B (A is not B)
    OVERLAPPING = "overlapping"    # A ∩ B ≠ ∅ but neither subset
    IDENTICAL = "identical"        # A = B


@dataclass
class MarketInfo:
    """Parsed market information"""
    ticker: str
    event_ticker: str  # Base event (e.g., "KXFED", "HIGHNY")
    series_ticker: str  # Series identifier
    threshold_value: Optional[float] = None
    threshold_type: Optional[str] = None  # "above", "below", "between", "exactly"
    date: Optional[str] = None
    full_name: str = ""
    
    @classmethod
    def from_ticker(cls, ticker: str, full_name: str = "") -> 'MarketInfo':
        """Parse market info from ticker format like 'HIGHNY-22DEC23-B53.5'"""
        parts = ticker.split("-")
        
        info = cls(
            ticker=ticker,
            event_ticker=parts[0] if parts else ticker,
            series_ticker=parts[0] if parts else ticker,
            full_name=full_name
        )
        
        # Parse threshold and type
        if len(parts) >= 3:
            threshold_part = parts[2]
            info.date = parts[1]
            
            # Parse threshold type and value
            if threshold_part.startswith("B"):  # Below
                info.threshold_type = "below"
                info.threshold_value = float(threshold_part[1:])
            elif threshold_part.startswith("T"):  # Above (T for "greater Than")
                info.threshold_type = "above"
                info.threshold_value = float(threshold_part[1:])
            elif threshold_part.startswith("R"):  # Range (between)
                info.threshold_type = "between"
                # Parse range values if needed
            elif threshold_part.startswith("E"):  # Exactly
                info.threshold_type = "exactly"
                info.threshold_value = float(threshold_part[1:])
        
        return info


@dataclass
class MarketRelationship:
    """Represents a relationship between two markets"""
    market_a: MarketInfo
    market_b: MarketInfo
    relationship_type: RelationshipType
    confidence: float  # 0.0 to 1.0
    reasoning: str
    
    def get_arbitrage_direction(self) -> Optional[Tuple[str, str]]:
        """
        Returns the arbitrage direction based on relationship type
        Returns: (constraint, opportunity) or None
        """
        if self.relationship_type == RelationshipType.SUBSET:
            # A ⊆ B means P(A) ≤ P(B)
            # Arbitrage if P(A) > P(B)
            return ("P(A) ≤ P(B)", "Sell A YES, Buy B YES if A_YES > B_YES")
        elif self.relationship_type == RelationshipType.DISJOINT:
            # A ∩ B = ∅ means P(A) + P(B) ≤ 1
            # Arbitrage if P(A) + P(B) > 1
            return ("P(A) + P(B) ≤ 1", "Sell both YES if sum > 1")
        elif self.relationship_type == RelationshipType.COMPLEMENT:
            # A = ¬B means P(A) = 1 - P(B)
            # Arbitrage if prices don't match this constraint
            return ("P(A) = 1 - P(B)", "Buy A YES, Buy B NO if A_YES + B_YES < 1")
        return None


class MarketRelationshipEngine:
    """Engine for detecting relationships between markets"""
    
    def __init__(self):
        self.relationships_cache: Dict[Tuple[str, str], MarketRelationship] = {}
    
    def find_relationships(self, markets: List[MarketInfo]) -> List[MarketRelationship]:
        """Find all relationships between a list of markets"""
        relationships = []
        
        for i, market_a in enumerate(markets):
            for market_b in markets[i+1:]:
                # Check if we've already analyzed this pair
                cache_key = (market_a.ticker, market_b.ticker)
                if cache_key in self.relationships_cache:
                    relationships.append(self.relationships_cache[cache_key])
                    continue
                
                # Analyze the relationship
                rel = self.analyze_pair(market_a, market_b)
                if rel and rel.confidence > 0.7:  # Only include high-confidence relationships
                    relationships.append(rel)
                    self.relationships_cache[cache_key] = rel
        
        return relationships
    
    def analyze_pair(self, market_a: MarketInfo, market_b: MarketInfo) -> Optional[MarketRelationship]:
        """Analyze the relationship between two markets"""
        
        # Skip if different events/series
        if market_a.series_ticker != market_b.series_ticker:
            return None
        
        # Skip if different dates
        if market_a.date != market_b.date:
            return None
        
        # Check for threshold-based relationships
        if (market_a.threshold_value is not None and 
            market_b.threshold_value is not None and
            market_a.threshold_type == market_b.threshold_type):
            
            if market_a.threshold_type == "above":
                return self._analyze_above_thresholds(market_a, market_b)
            elif market_a.threshold_type == "below":
                return self._analyze_below_thresholds(market_a, market_b)
            elif market_a.threshold_type == "exactly":
                return self._analyze_exactly_values(market_a, market_b)
        
        return None
    
    def _analyze_above_thresholds(self, market_a: MarketInfo, 
                                  market_b: MarketInfo) -> Optional[MarketRelationship]:
        """Analyze 'above X' relationships"""
        val_a = market_a.threshold_value
        val_b = market_b.threshold_value
        
        if val_a is not None and val_b is not None and val_a > val_b:
            # "Above 400" ⊆ "Above 300"
            return MarketRelationship(
                market_a=market_a,
                market_b=market_b,
                relationship_type=RelationshipType.SUBSET,
                confidence=1.0,
                reasoning=f"If value > {val_a}, then value > {val_b} (subset)"
            )
        elif val_a is not None and val_b is not None and val_a < val_b:
            # "Above 300" ⊇ "Above 400"
            return MarketRelationship(
                market_a=market_a,
                market_b=market_b,
                relationship_type=RelationshipType.SUPERSET,
                confidence=1.0,
                reasoning=f"If value > {val_b}, then value > {val_a} (superset)"
            )
        else:
            # Same threshold - identical markets
            return MarketRelationship(
                market_a=market_a,
                market_b=market_b,
                relationship_type=RelationshipType.IDENTICAL,
                confidence=1.0,
                reasoning=f"Both markets have same threshold: above {val_a}"
            )
    
    def _analyze_below_thresholds(self, market_a: MarketInfo,
                                  market_b: MarketInfo) -> Optional[MarketRelationship]:
        """Analyze 'below X' relationships"""
        val_a = market_a.threshold_value
        val_b = market_b.threshold_value
        
        if val_a is not None and val_b is not None and val_a < val_b:
            # "Below 300" ⊆ "Below 400"
            return MarketRelationship(
                market_a=market_a,
                market_b=market_b,
                relationship_type=RelationshipType.SUBSET,
                confidence=1.0,
                reasoning=f"If value < {val_a}, then value < {val_b} (subset)"
            )
        elif val_a is not None and val_b is not None and val_a > val_b:
            # "Below 400" ⊇ "Below 300"
            return MarketRelationship(
                market_a=market_a,
                market_b=market_b,
                relationship_type=RelationshipType.SUPERSET,
                confidence=1.0,
                reasoning=f"If value < {val_b}, then value < {val_a} (superset)"
            )
        else:
            return MarketRelationship(
                market_a=market_a,
                market_b=market_b,
                relationship_type=RelationshipType.IDENTICAL,
                confidence=1.0,
                reasoning=f"Both markets have same threshold: below {val_a}"
            )
    
    def _analyze_exactly_values(self, market_a: MarketInfo,
                               market_b: MarketInfo) -> Optional[MarketRelationship]:
        """Analyze 'exactly X' relationships"""
        val_a = market_a.threshold_value
        val_b = market_b.threshold_value
        
        if val_a != val_b:
            # Different exact values are mutually exclusive
            return MarketRelationship(
                market_a=market_a,
                market_b=market_b,
                relationship_type=RelationshipType.DISJOINT,
                confidence=1.0,
                reasoning=f"Cannot be both exactly {val_a} and exactly {val_b} (disjoint)"
            )
        else:
            return MarketRelationship(
                market_a=market_a,
                market_b=market_b,
                relationship_type=RelationshipType.IDENTICAL,
                confidence=1.0,
                reasoning=f"Both markets are for exactly {val_a}"
            )
    
    def find_arbitrage_chains(self, markets: List[MarketInfo], 
                             max_chain_length: int = 3) -> List[List[MarketRelationship]]:
        """
        Find chains of relationships that could create arbitrage
        Example: A ⊆ B ⊆ C creates opportunity if P(A) > P(C)
        """
        relationships = self.find_relationships(markets)
        chains = []
        
        # Build adjacency graph
        graph: Dict[str, List[Tuple[str, MarketRelationship]]] = {}
        for rel in relationships:
            if rel.relationship_type in [RelationshipType.SUBSET, RelationshipType.SUPERSET]:
                # Add edges for transitive relationships
                a_ticker = rel.market_a.ticker
                b_ticker = rel.market_b.ticker
                
                if a_ticker not in graph:
                    graph[a_ticker] = []
                if b_ticker not in graph:
                    graph[b_ticker] = []
                
                if rel.relationship_type == RelationshipType.SUBSET:
                    graph[a_ticker].append((b_ticker, rel))
                else:  # SUPERSET
                    graph[b_ticker].append((a_ticker, rel))
        
        # Find chains using DFS
        def find_chains_from(start: str, path: List[MarketRelationship], 
                           visited: Set[str], depth: int):
            if depth >= max_chain_length:
                return
            
            if len(path) >= 2:
                chains.append(path.copy())
            
            if start in graph:
                for next_ticker, rel in graph[start]:
                    if next_ticker not in visited:
                        visited.add(next_ticker)
                        path.append(rel)
                        find_chains_from(next_ticker, path, visited, depth + 1)
                        path.pop()
                        visited.remove(next_ticker)
        
        # Start DFS from each node
        for start_ticker in graph:
            visited = {start_ticker}
            find_chains_from(start_ticker, [], visited, 0)
        
        return chains


# Specialized analyzers for common Kalshi market types

class FedRateAnalyzer:
    """Analyzer for Federal Reserve rate markets"""
    
    @staticmethod
    def analyze_rate_markets(markets: List[MarketInfo]) -> List[MarketRelationship]:
        """Find relationships in Fed rate markets"""
        relationships = []
        
        # Group by date
        by_date: Dict[str, List[MarketInfo]] = {}
        for market in markets:
            if market.series_ticker.startswith("KXFED") and market.date:
                if market.date not in by_date:
                    by_date[market.date] = []
                by_date[market.date].append(market)
        
        # Analyze each date group
        engine = MarketRelationshipEngine()
        for date, date_markets in by_date.items():
            relationships.extend(engine.find_relationships(date_markets))
        
        return relationships


class IndexAnalyzer:
    """Analyzer for S&P500 and NASDAQ markets"""
    
    @staticmethod
    def analyze_index_markets(markets: List[MarketInfo]) -> List[MarketRelationship]:
        """Find relationships in index markets"""
        relationships = []
        
        # Group by index and date
        by_index_date: Dict[Tuple[str, str], List[MarketInfo]] = {}
        for market in markets:
            if market.series_ticker in ["INX", "NASDAQ100"] and market.date:
                key = (market.series_ticker, market.date)
                if key not in by_index_date:
                    by_index_date[key] = []
                by_index_date[key].append(market)
        
        # Analyze each group
        engine = MarketRelationshipEngine()
        for (index, date), group_markets in by_index_date.items():
            relationships.extend(engine.find_relationships(group_markets))
        
        return relationships


# Example usage
if __name__ == "__main__":
    # Test with example markets
    markets = [
        MarketInfo.from_ticker("HIGHNY-22DEC23-T53.5", "High temperature NYC above 53.5"),
        MarketInfo.from_ticker("HIGHNY-22DEC23-T55.0", "High temperature NYC above 55.0"),
        MarketInfo.from_ticker("HIGHNY-22DEC23-T60.0", "High temperature NYC above 60.0"),
        MarketInfo.from_ticker("KXFED-23DEC-E2", "Fed rate exactly 2 cuts"),
        MarketInfo.from_ticker("KXFED-23DEC-E3", "Fed rate exactly 3 cuts"),
    ]
    
    engine = MarketRelationshipEngine()
    relationships = engine.find_relationships(markets)
    
    print("Found relationships:")
    for rel in relationships:
        print(f"\n{rel.market_a.ticker} {rel.relationship_type.value} {rel.market_b.ticker}")
        print(f"  Reasoning: {rel.reasoning}")
        print(f"  Confidence: {rel.confidence:.1%}")
        
        arb_info = rel.get_arbitrage_direction()
        if arb_info:
            constraint, opportunity = arb_info
            print(f"  Constraint: {constraint}")
            print(f"  Arbitrage: {opportunity}")