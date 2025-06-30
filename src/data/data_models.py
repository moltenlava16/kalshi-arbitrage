"""
Core data models for Kalshi arbitrage trading system
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple
import json


class OrderSide(Enum):
    """Side of an order"""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Type of order"""
    LIMIT = "limit"
    MARKET = "market"


class OrderStatus(Enum):
    """Status of an order"""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class PositionSide(Enum):
    """Side of a position"""
    YES = "yes"
    NO = "no"


@dataclass
class PriceLevel:
    """Represents a price level in the order book"""
    price: Decimal
    quantity: int
    
    def __post_init__(self):
        self.price = Decimal(str(self.price))


@dataclass
class OrderBook:
    """Order book for a market"""
    market_ticker: str
    yes_bids: List[PriceLevel] = field(default_factory=list)
    yes_asks: List[PriceLevel] = field(default_factory=list)
    no_bids: List[PriceLevel] = field(default_factory=list)
    no_asks: List[PriceLevel] = field(default_factory=list)
    last_update: datetime = field(default_factory=datetime.now)
    sequence: int = 0
    
    @property
    def best_yes_bid(self) -> Optional[Decimal]:
        """Get best YES bid price"""
        return self.yes_bids[0].price if self.yes_bids else None
    
    @property
    def best_yes_ask(self) -> Optional[Decimal]:
        """Get best YES ask price"""
        return self.yes_asks[0].price if self.yes_asks else None
    
    @property
    def best_no_bid(self) -> Optional[Decimal]:
        """Get best NO bid price"""
        return self.no_bids[0].price if self.no_bids else None
    
    @property
    def best_no_ask(self) -> Optional[Decimal]:
        """Get best NO ask price"""
        return self.no_asks[0].price if self.no_asks else None
    
    @property
    def yes_spread(self) -> Optional[Decimal]:
        """Get YES bid-ask spread"""
        if self.best_yes_bid and self.best_yes_ask:
            return self.best_yes_ask - self.best_yes_bid
        return None
    
    @property
    def no_spread(self) -> Optional[Decimal]:
        """Get NO bid-ask spread"""
        if self.best_no_bid and self.best_no_ask:
            return self.best_no_ask - self.best_no_bid
        return None
    
    def get_depth_at_price(self, side: PositionSide, price: Decimal, 
                          is_bid: bool) -> int:
        """Get total quantity available at a specific price level"""
        if side == PositionSide.YES:
            levels = self.yes_bids if is_bid else self.yes_asks
        else:
            levels = self.no_bids if is_bid else self.no_asks
        
        for level in levels:
            if level.price == price:
                return level.quantity
        return 0
    
    def get_total_depth(self, side: PositionSide, is_bid: bool, 
                       max_price: Optional[Decimal] = None) -> int:
        """Get total depth up to a price level"""
        if side == PositionSide.YES:
            levels = self.yes_bids if is_bid else self.yes_asks
        else:
            levels = self.no_bids if is_bid else self.no_asks
        
        total = 0
        for level in levels:
            if max_price and ((is_bid and level.price < max_price) or 
                            (not is_bid and level.price > max_price)):
                break
            total += level.quantity
        return total


@dataclass
class Market:
    """Complete market information"""
    ticker: str
    event_ticker: str
    title: str
    subtitle: str = ""
    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    expected_expiration_time: Optional[datetime] = None
    status: str = "active"
    result: Optional[str] = None
    can_close_early: bool = True
    strike_value: Optional[float] = None
    
    @property
    def is_active(self) -> bool:
        """Check if market is active for trading"""
        return self.status == "active"
    
    @property
    def is_resolved(self) -> bool:
        """Check if market has been resolved"""
        return self.result is not None


@dataclass
class Order:
    """Represents an order"""
    order_id: str
    market_ticker: str
    side: OrderSide
    position_side: PositionSide
    quantity: int
    price: Decimal
    order_type: OrderType = OrderType.LIMIT
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    average_fill_price: Optional[Decimal] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def remaining_quantity(self) -> int:
        """Get remaining quantity to be filled"""
        return self.quantity - self.filled_quantity
    
    @property
    def is_fully_filled(self) -> bool:
        """Check if order is fully filled"""
        return self.filled_quantity >= self.quantity
    
    @property
    def fill_percentage(self) -> float:
        """Get fill percentage"""
        return (self.filled_quantity / self.quantity * 100) if self.quantity > 0 else 0


@dataclass
class Fill:
    """Represents a fill/trade"""
    fill_id: str
    order_id: str
    market_ticker: str
    side: OrderSide
    position_side: PositionSide
    quantity: int
    price: Decimal
    is_taker: bool
    fees: Decimal
    timestamp: datetime
    
    @property
    def total_cost(self) -> Decimal:
        """Total cost including fees"""
        if self.side == OrderSide.BUY:
            return (self.price * self.quantity) + self.fees
        else:
            return self.fees  # For sells, we receive money


@dataclass
class Position:
    """Represents a position in a market"""
    market_ticker: str
    position_side: PositionSide
    quantity: int
    average_entry_price: Decimal
    market_price: Optional[Decimal] = None
    realized_pnl: Decimal = Decimal("0")
    fees_paid: Decimal = Decimal("0")
    
    @property
    def unrealized_pnl(self) -> Optional[Decimal]:
        """Calculate unrealized P&L"""
        if self.market_price is None:
            return None
        return (self.market_price - self.average_entry_price) * self.quantity
    
    @property
    def total_pnl(self) -> Optional[Decimal]:
        """Calculate total P&L"""
        if self.unrealized_pnl is None:
            return None
        return self.realized_pnl + self.unrealized_pnl - self.fees_paid


@dataclass
class ArbitrageOpportunity:
    """Represents an arbitrage opportunity"""
    opportunity_id: str
    strategy_type: str  # "subset", "disjoint", "complement"
    markets: List[str]  # List of market tickers involved
    orders: List[Tuple[str, OrderSide, PositionSide, Decimal, int]]  # (ticker, side, position, price, qty)
    expected_profit: Decimal
    required_capital: Decimal
    confidence_score: float  # 0.0 to 1.0
    detected_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    @property
    def return_on_capital(self) -> Decimal:
        """Calculate return on capital"""
        if self.required_capital > 0:
            return self.expected_profit / self.required_capital
        return Decimal("inf")
    
    @property
    def is_expired(self) -> bool:
        """Check if opportunity has expired"""
        if self.expires_at:
            return datetime.now() > self.expires_at
        return False
    
    def to_json(self) -> str:
        """Convert to JSON for storage/transmission"""
        return json.dumps({
            "opportunity_id": self.opportunity_id,
            "strategy_type": self.strategy_type,
            "markets": self.markets,
            "orders": [(t, s.value, p.value, str(pr), q) 
                      for t, s, p, pr, q in self.orders],
            "expected_profit": str(self.expected_profit),
            "required_capital": str(self.required_capital),
            "confidence_score": self.confidence_score,
            "detected_at": self.detected_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        })


@dataclass
class TradingSession:
    """Represents a trading session with performance metrics"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    starting_balance: Decimal = Decimal("0")
    current_balance: Decimal = Decimal("0")
    total_trades: int = 0
    winning_trades: int = 0
    total_fees: Decimal = Decimal("0")
    gross_pnl: Decimal = Decimal("0")
    
    @property
    def net_pnl(self) -> Decimal:
        """Net P&L after fees"""
        return self.gross_pnl - self.total_fees
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate"""
        return (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
    
    @property
    def average_trade_pnl(self) -> Decimal:
        """Average P&L per trade"""
        return self.net_pnl / self.total_trades if self.total_trades > 0 else Decimal("0")


# WebSocket message models

@dataclass
class WSMessage:
    """Base WebSocket message"""
    type: str
    sid: Optional[int] = None
    seq: Optional[int] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'WSMessage':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class OrderBookSnapshot:
    """Order book snapshot message"""
    type: str
    market_ticker: str
    sid: Optional[int] = None
    seq: Optional[int] = None
    yes: List[List[int]] = field(default_factory=list)  # [[price_cents, quantity], ...]
    no: List[List[int]] = field(default_factory=list)
    
    def to_order_book(self) -> OrderBook:
        """Convert to OrderBook object"""
        book = OrderBook(market_ticker=self.market_ticker, sequence=self.seq or 0)
        
        # Convert YES levels
        for price_cents, quantity in self.yes:
            price = Decimal(price_cents) / 100
            book.yes_asks.append(PriceLevel(price, quantity))
        
        # Convert NO levels
        for price_cents, quantity in self.no:
            price = Decimal(price_cents) / 100
            book.no_asks.append(PriceLevel(price, quantity))
        
        # Sort by price
        book.yes_asks.sort(key=lambda x: x.price)
        book.no_asks.sort(key=lambda x: x.price)
        
        return book


@dataclass
class OrderBookDelta:
    """Order book delta message"""
    type: str
    market_ticker: str
    price: int  # in cents
    delta: int  # change in quantity
    side: str  # "yes" or "no"
    sid: Optional[int] = None
    seq: Optional[int] = None
    
    def apply_to_book(self, book: OrderBook):
        """Apply delta to order book"""
        price_decimal = Decimal(self.price) / 100
        
        if self.side == "yes":
            levels = book.yes_asks if self.delta > 0 else book.yes_bids
        else:
            levels = book.no_asks if self.delta > 0 else book.no_bids
        
        # Find and update the level
        level_found = False
        for i, level in enumerate(levels):
            if level.price == price_decimal:
                level.quantity += self.delta
                if level.quantity <= 0:
                    levels.pop(i)
                level_found = True
                break
        
        # Add new level if not found and delta > 0
        if not level_found and self.delta > 0:
            levels.append(PriceLevel(price_decimal, self.delta))
            levels.sort(key=lambda x: x.price, reverse=(self.delta < 0))
        
        book.sequence = self.seq or book.sequence + 1
        book.last_update = datetime.now()