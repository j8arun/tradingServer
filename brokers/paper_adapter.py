"""
Paper Trading Adapter - Risk-Free Simulation
Uses REAL market data but FAKE money.
Perfect for testing your strategy before going live.
"""
from datetime import datetime
from typing import List, Dict, Optional, Callable
import uuid
from interfaces import IBroker, Tick, Order, Position

class PaperBroker(IBroker):
    """
    Paper trading simulator with realistic execution
    Uses real market data but simulated balance
    """
    
    def __init__(self, real_data_source: IBroker, starting_balance: float = 100000):
        """
        Args:
            real_data_source: A real broker (GrowwBroker) for live prices
            starting_balance: Starting virtual cash
        """
        self.data_source = real_data_source
        self.balance = starting_balance
        self.starting_balance = starting_balance
        self.positions: Dict[str, Dict] = {}  # {symbol: {qty, avg_price, ...}}
        self.orders: Dict[str, Order] = {}
        self.trade_history = []
        self.connected = False
    
    def connect(self) -> bool:
        """Connect to data source"""
        print("📝 Initializing Paper Trading...")
        self.connected = self.data_source.connect()
        if self.connected:
            print(f"✅ Paper Trading Ready | Virtual Balance: ₹{self.balance:,.2f}")
        return self.connected
    
    def disconnect(self):
        """Disconnect"""
        self.data_source.disconnect()
        self.connected = False
        print("📝 Paper Trading Session Ended")
        self._print_summary()
    
    def is_connected(self) -> bool:
        """Check connection"""
        return self.connected and self.data_source.is_connected()
    
    def subscribe_ticks(self, symbols: List[str], callback: Callable[[Tick], None]):
        """Subscribe to ticks via real data source"""
        # We just pass through to the real data source
        self.data_source.subscribe_ticks(symbols, callback)
    
    def get_live_price(self, symbol: str) -> Optional[float]:
        """Get real market price"""
        return self.data_source.get_live_price(symbol)
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "MARKET",
        price: Optional[float] = None
    ) -> Order:
        """
        Simulate order placement
        🟢 NO REAL MONEY - This is a simulation
        """
        # Get current market price
        current_price = self.get_live_price(symbol)
        if current_price is None:
            raise ValueError(f"No price data for {symbol}")
        
        # For market orders, use current price
        execution_price = current_price if order_type == "MARKET" else price
        
        # Create order
        order = Order(
            order_id=f"PAPER_{uuid.uuid4().hex[:8]}",
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=price,
            status="PENDING",
            timestamp=datetime.now()
        )
        
        # Simulate instant execution for market orders
        if order_type == "MARKET":
            order.status = "FILLED"
            order.filled_price = execution_price
            order.filled_qty = quantity
            
            # Update positions and balance
            self._execute_trade(symbol, side, quantity, execution_price)
            
            print(f"📝 PAPER TRADE: {side} {quantity} {symbol} @ ₹{execution_price:.2f}")
        
        self.orders[order.order_id] = order
        return order
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel pending order"""
        if order_id in self.orders:
            order = self.orders[order_id]
            if order.status == "PENDING":
                order.status = "CANCELLED"
                print(f"📝 PAPER: Cancelled order {order_id}")
                return True
        return False
    
    def get_order_status(self, order_id: str) -> Order:
        """Get order status"""
        return self.orders.get(order_id)
    
    def get_positions(self) -> List[Position]:
        """Get current positions"""
        positions = []
        
        for symbol, pos_data in self.positions.items():
            if pos_data['quantity'] == 0:
                continue
            
            current_price = self.get_live_price(symbol) or pos_data['avg_price']
            
            # Calculate PnL
            if pos_data['quantity'] > 0:  # Long
                pnl = (current_price - pos_data['avg_price']) * pos_data['quantity']
            else:  # Short
                pnl = (pos_data['avg_price'] - current_price) * abs(pos_data['quantity'])
            
            pnl_pct = (pnl / (pos_data['avg_price'] * abs(pos_data['quantity']))) * 100
            
            position = Position(
                symbol=symbol,
                quantity=pos_data['quantity'],
                avg_price=pos_data['avg_price'],
                current_price=current_price,
                pnl=pnl,
                pnl_pct=pnl_pct
            )
            positions.append(position)
        
        return positions
    
    def get_balance(self) -> Dict[str, float]:
        """Get simulated balance"""
        # Calculate used margin
        positions_value = sum(
            abs(pos['quantity'] * pos['avg_price'])
            for pos in self.positions.values()
        )
        
        return {
            "available": self.balance,
            "used": positions_value,
            "total": self.balance + positions_value
        }
    
    def get_pnl(self) -> Dict[str, float]:
        """Get P&L"""
        positions = self.get_positions()
        
        # Unrealized PnL (open positions)
        unrealized = sum(p.pnl for p in positions)
        
        # Realized PnL (from closed trades)
        realized = sum(trade['pnl'] for trade in self.trade_history if 'pnl' in trade)
        
        return {
            "realized": realized,
            "unrealized": unrealized,
            "total": realized + unrealized
        }
    
    # ==================== INTERNAL HELPERS ====================
    
    def _execute_trade(self, symbol: str, side: str, quantity: int, price: float):
        """Execute a trade and update positions"""
        cost = quantity * price
        
        if side == "BUY":
            # Deduct cash
            self.balance -= cost
            
            # Update position
            if symbol not in self.positions:
                self.positions[symbol] = {'quantity': 0, 'avg_price': 0}
            
            pos = self.positions[symbol]
            total_qty = pos['quantity'] + quantity
            pos['avg_price'] = ((pos['avg_price'] * pos['quantity']) + cost) / total_qty
            pos['quantity'] = total_qty
        
        elif side == "SELL":
            # Add cash
            self.balance += cost
            
            # Update position
            if symbol not in self.positions:
                self.positions[symbol] = {'quantity': 0, 'avg_price': price}
            
            pos = self.positions[symbol]
            
            # Calculate PnL if closing position
            if pos['quantity'] > 0:
                closed_qty = min(quantity, pos['quantity'])
                pnl = (price - pos['avg_price']) * closed_qty
                
                # Record closed trade
                self.trade_history.append({
                    'symbol': symbol,
                    'side': 'SELL',
                    'quantity': closed_qty,
                    'entry_price': pos['avg_price'],
                    'exit_price': price,
                    'pnl': pnl,
                    'timestamp': datetime.now()
                })
            
            pos['quantity'] -= quantity
    
    def _print_summary(self):
        """Print trading session summary"""
        pnl = self.get_pnl()
        roi = ((self.balance - self.starting_balance) / self.starting_balance) * 100
        
        print("\n" + "="*50)
        print("📊 PAPER TRADING SUMMARY")
        print("="*50)
        print(f"Starting Balance: ₹{self.starting_balance:,.2f}")
        print(f"Ending Balance:   ₹{self.balance:,.2f}")
        print(f"Realized PnL:     ₹{pnl['realized']:,.2f}")
        print(f"Unrealized PnL:   ₹{pnl['unrealized']:,.2f}")
        print(f"Total PnL:        ₹{pnl['total']:,.2f}")
        print(f"ROI:              {roi:.2f}%")
        print(f"Total Trades:     {len(self.trade_history)}")
        print("="*50 + "\n")
