"""
Risk Management System - The Safety Net
Prevents catastrophic losses and enforces trading discipline.
"""
from datetime import datetime, timedelta
from typing import Dict, Optional
import config
from database import TradingDatabase

class RiskManager:
    """
    Enforces risk limits and prevents dangerous trades.
    This is the MOST IMPORTANT component for live trading.
    """
    
    def __init__(self, db: TradingDatabase):
        self.db = db
        self.order_timestamps = []  # For rate limiting
        self.daily_loss_checkpoint = None
        self.circuit_breaker_active = False
    
    def can_trade(self) -> tuple[bool, str]:
        """
        Master risk check - returns (allowed, reason)
        This runs BEFORE every trade
        """
        # Check 1: Trading hours
        if not self._is_trading_hours():
            return False, "Outside trading hours"
        
        # Check 2: Circuit breaker (triggered by excessive losses)
        if self.circuit_breaker_active:
            return False, "Circuit breaker active - daily loss limit exceeded"
        
        # Check 3: Daily loss limit
        daily_pnl = self.db.get_daily_pnl()
        if daily_pnl < -config.MAX_LOSS_PER_DAY:
            self.circuit_breaker_active = True
            self.db.log_event("CIRCUIT_BREAKER", f"Daily loss limit breached: {daily_pnl:.2f}", "CRITICAL")
            return False, f"Daily loss limit breached: ₹{daily_pnl:.2f}"
        
        # Check 4: Rate limiting (prevent runaway algos)
        if not self._check_rate_limit():
            return False, "Order rate limit exceeded (too many orders)"
        
        return True, "All risk checks passed"
    
    def validate_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        current_positions: Dict,
        balance: Dict
    ) -> tuple[bool, str]:
        """
        Validate a specific order before execution
        Returns: (is_valid, reason)
        """
        # Check 1: Position size limit
        order_value = quantity * price
        if order_value > config.MAX_POSITION_SIZE:
            return False, f"Order value (₹{order_value:.2f}) exceeds max position size (₹{config.MAX_POSITION_SIZE})"
        
        # Check 2: Total exposure limit
        total_exposure = sum(abs(pos['quantity'] * pos['current_price']) for pos in current_positions.values())
        if total_exposure + order_value > config.MAX_TOTAL_EXPOSURE:
            return False, f"Total exposure would exceed limit (₹{config.MAX_TOTAL_EXPOSURE})"
        
        # Check 3: Sufficient balance
        if side == "BUY" and order_value > balance['available']:
            return False, f"Insufficient balance (₹{balance['available']:.2f} < ₹{order_value:.2f})"
        
        # Check 4: Price sanity check
        if not self._is_price_sane(price):
            return False, f"Price (₹{price}) failed sanity check"
        
        return True, "Order validated"
    
    def calculate_position_size(self, symbol: str, entry_price: float, balance: float) -> int:
        """
        Calculate optimal position size based on risk management
        """
        if config.POSITION_SIZE_METHOD == "fixed":
            quantity = int(config.FIXED_POSITION_SIZE / entry_price)
        
        elif config.POSITION_SIZE_METHOD == "risk_parity":
            # Risk a fixed % of capital per trade
            risk_per_trade = balance * 0.02  # 2% risk
            stop_loss_distance = entry_price * config.STOP_LOSS_PCT
            quantity = int(risk_per_trade / stop_loss_distance)
        
        else:
            # Default to fixed size
            quantity = int(config.FIXED_POSITION_SIZE / entry_price)
        
        # Ensure we don't exceed position size limit
        max_qty = int(config.MAX_POSITION_SIZE / entry_price)
        return min(quantity, max_qty)
    
    def should_exit_position(
        self,
        entry_price: float,
        current_price: float,
        side: str
    ) -> tuple[bool, str]:
        """
        Check if position should be closed due to stop-loss or take-profit
        Returns: (should_exit, reason)
        """
        if side == "BUY":
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:  # SELL (short)
            pnl_pct = ((entry_price - current_price) / entry_price) * 100
        
        # Stop Loss
        if pnl_pct <= -config.STOP_LOSS_PCT * 100:
            return True, f"STOP_LOSS triggered at {pnl_pct:.2f}%"
        
        # Take Profit
        if pnl_pct >= config.TAKE_PROFIT_PCT * 100:
            return True, f"TAKE_PROFIT triggered at {pnl_pct:.2f}%"
        
        return False, "Position within risk limits"
    
    # ==================== INTERNAL CHECKS ====================
    
    def _is_trading_hours(self) -> bool:
        """Check if current time is within trading hours"""
        now = datetime.now().time()
        start = datetime.strptime(config.TRADING_HOURS['start'], "%H:%M").time()
        end = datetime.strptime(config.TRADING_HOURS['end'], "%H:%M").time()
        
        # Also check if it's a weekday (Monday=0, Sunday=6)
        is_weekday = datetime.now().weekday() < 5
        
        return is_weekday and start <= now <= end
    
    def _check_rate_limit(self) -> bool:
        """Prevent too many orders in a short time"""
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)
        
        # Remove old timestamps
        self.order_timestamps = [ts for ts in self.order_timestamps if ts > cutoff]
        
        # Check if we're under the limit
        if len(self.order_timestamps) >= config.MAX_ORDERS_PER_MINUTE:
            return False
        
        self.order_timestamps.append(now)
        return True
    
    def _is_price_sane(self, price: float) -> bool:
        """Validate price is within reasonable bounds"""
        return (config.PRICE_SANITY_CHECK['min_price'] <= price <= 
                config.PRICE_SANITY_CHECK['max_price'])
    
    def reset_daily_limits(self):
        """Reset circuit breaker (call at start of new trading day)"""
        self.circuit_breaker_active = False
        self.daily_loss_checkpoint = None
        self.db.log_event("RISK_MANAGER", "Daily limits reset", "INFO")
    
    def get_risk_report(self) -> Dict:
        """Get current risk status"""
        daily_pnl = self.db.get_daily_pnl()
        stats = self.db.get_performance_stats(days=1)
        
        return {
            "circuit_breaker_active": self.circuit_breaker_active,
            "daily_pnl": daily_pnl,
            "remaining_loss_buffer": config.MAX_LOSS_PER_DAY + daily_pnl,
            "trades_today": stats['total_trades'],
            "orders_last_minute": len(self.order_timestamps),
            "trading_allowed": self._is_trading_hours()
        }
