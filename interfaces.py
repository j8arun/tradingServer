"""
Abstract Broker Interface - The Contract
All broker adapters (Groww, Zerodha, Paper) must implement these methods.
This ensures your strategy code never changes when switching brokers.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Tick:
    """Represents a single market tick"""
    symbol: str
    timestamp: datetime
    ltp: float  # Last Traded Price
    volume: int
    bid: Optional[float] = None
    ask: Optional[float] = None
    oi: Optional[int] = None  # Open Interest (for F&O)

@dataclass
class Order:
    """Represents an order (placed or filled)"""
    order_id: str
    symbol: str
    side: str  # "BUY" or "SELL"
    quantity: int
    order_type: str  # "MARKET", "LIMIT"
    price: Optional[float] = None  # For limit orders
    status: str = "PENDING"  # PENDING, FILLED, REJECTED, CANCELLED
    filled_price: Optional[float] = None
    filled_qty: int = 0
    timestamp: datetime = None

@dataclass
class Position:
    """Represents a current position"""
    symbol: str
    quantity: int  # Positive for long, negative for short
    avg_price: float
    current_price: float
    pnl: float
    pnl_pct: float

class IBroker(ABC):
    """
    Abstract Broker Interface
    Every broker adapter MUST implement these methods
    """
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the broker
        Returns: True if successful, False otherwise
        """
        pass

    @abstractmethod
    def disconnect(self):
        """Close all connections gracefully"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connection is alive"""
        pass

    @abstractmethod
    def subscribe_ticks(self, symbols: List[str], callback):
        """
        Subscribe to real-time tick data
        Args:
            symbols: List of stock symbols
            callback: Function to call when tick arrives (callback(tick: Tick))
        """
        pass

    @abstractmethod
    def get_live_price(self, symbol: str) -> Optional[float]:
        """
        Get the latest price for a symbol
        Returns: Current price or None if unavailable
        """
        pass

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "MARKET",
        price: Optional[float] = None
    ) -> Order:
        """
        Place an order
        Returns: Order object with order_id
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order"""
        pass

    @abstractmethod
    def get_order_status(self, order_id: str) -> Order:
        """Get status of an order"""
        pass

    @abstractmethod
    def get_positions(self) -> List[Position]:
        """Get all current positions"""
        pass

    @abstractmethod
    def get_balance(self) -> Dict[str, float]:
        """
        Get account balance
        Returns: {"available": float, "used": float, "total": float}
        """
        pass

    @abstractmethod
    def get_pnl(self) -> Dict[str, float]:
        """
        Get profit/loss statistics
        Returns: {"realized": float, "unrealized": float, "total": float}
        """
        pass
