"""
Groww Broker Adapter - Real Trading Connection
Connects to Groww API via WebSocket for instant tick data.
Handles reconnections, errors, and order execution.
"""
import time
from datetime import datetime
from typing import List, Dict, Optional, Callable
import threading
import config
from interfaces import IBroker, Tick, Order, Position

# Note: You'll need to install growwapi
# pip install growwapi
try:
    from growwapi import GrowwAPI, GrowwFeed
    GROWW_AVAILABLE = True
except ImportError:
    print("⚠️  growwapi not installed. Run: pip install growwapi")
    GROWW_AVAILABLE = False

class GrowwBroker(IBroker):
    """
    Groww API Adapter with WebSocket support
    Provides instant tick data (push model) instead of polling
    """
    
    def __init__(self):
        if not GROWW_AVAILABLE:
            raise RuntimeError("growwapi package not installed")
        
        self.api = None
        self.feed = None
        self.latest_prices: Dict[str, Tick] = {}
        self.connected = False
        self.reconnect_attempts = 0
        self.tick_callback = None
        self.lock = threading.Lock()
        
        # For heartbeat monitoring
        self.last_tick_time = {}
        self.heartbeat_thread = None
    
    def connect(self) -> bool:
        """Establish connection to Groww"""
        try:
            print("🔌 Connecting to Groww API...")
            access_token = GrowwAPI.get_access_token(api_key=config.GROWW_API_TOKEN, secret=config.GROWW_API_SECRET)
            # Initialize API
            self.api = GrowwAPI(access_token)
            
            # Test connection
            profile = self.api.get_user_profile()
            print(f"✅ Connected as: {profile.get('ucc')}")
            
            # Initialize WebSocket feed
            self.feed = GrowwFeed(self.api)
            self.connected = True
            self.reconnect_attempts = 0
            
            # Start heartbeat monitor
            self._start_heartbeat_monitor()
            
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Close all connections gracefully"""
        print("🔌 Disconnecting from Groww...")
        if self.feed:
            try:
                self.feed.close()
            except:
                pass
        self.connected = False
        print("✅ Disconnected")
    
    def is_connected(self) -> bool:
        """Check if connection is alive"""
        return self.connected and self.api is not None
    
    def subscribe_ticks(self, symbols: List[str], callback: Callable[[Tick], None]):
        """
        Subscribe to real-time WebSocket ticks
        This is the MAIN advantage over yfinance - instant push data
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Groww")
        
        self.tick_callback = callback
        
        def on_tick_received(tick_data):
            """Internal handler for incoming ticks"""
            try:
                # Parse Groww tick format
                tick = Tick(
                    symbol=tick_data.get('trading_symbol', ''),
                    timestamp=datetime.now(),
                    ltp=float(tick_data.get('last_price', 0)),
                    volume=int(tick_data.get('volume', 0)),
                    bid=float(tick_data.get('bid', 0)) if 'bid' in tick_data else None,
                    ask=float(tick_data.get('ask', 0)) if 'ask' in tick_data else None,
                    oi=int(tick_data.get('oi', 0)) if 'oi' in tick_data else None
                )
                
                # Price sanity check
                if not self._validate_tick(tick):
                    return
                
                # Update cache
                with self.lock:
                    self.latest_prices[tick.symbol] = tick
                    self.last_tick_time[tick.symbol] = datetime.now()
                
                # Call user callback
                if self.tick_callback:
                    self.tick_callback(tick)
                    
            except Exception as e:
                print(f"⚠️  Error processing tick: {e}")
        
        def on_error(error):
            """Handle WebSocket errors"""
            print(f"❌ WebSocket error: {error}")
            self._handle_disconnect()
        
        def on_close():
            """Handle WebSocket closure"""
            print("🔌 WebSocket closed")
            self._handle_disconnect()
        
        # Subscribe to symbols
        print(f"📡 Subscribing to {len(symbols)} symbols...")
        self.feed.subscribe_ltp(
            symbols,
            on_data_received=on_tick_received
        )
        
        print("✅ WebSocket subscription active")
    
    def get_live_price(self, symbol: str) -> Optional[float]:
        """Get the latest price from cache (instant)"""
        with self.lock:
            tick = self.latest_prices.get(symbol)
            return tick.ltp if tick else None
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "MARKET",
        price: Optional[float] = None
    ) -> Order:
        """
        Place a real order on Groww
        🚨 THIS USES REAL MONEY 🚨
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Groww")
        
        try:
            print(f"🚀 PLACING LIVE ORDER: {side} {quantity} {symbol} @ {order_type}")
            
            # Map our standard format to Groww format
            groww_side = "BUY" if side == "BUY" else "SELL"
            groww_order_type = self.api.ORDER_TYPE_MARKET if order_type == "MARKET" else self.api.ORDER_TYPE_LIMIT
            
            # Place order via Groww API
            result = self.api.place_order(
                exchange=self.api.EXCHANGE_NSE,
                trading_symbol=symbol,
                transaction_type=groww_side,
                quantity=quantity,
                order_type=groww_order_type,
                price=price,
                product=self.api.PRODUCT_DELIVERY  # or INTRADAY
            )
            
            # Create Order object
            order = Order(
                order_id=result.get('order_id', ''),
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=order_type,
                price=price,
                status="PENDING",
                timestamp=datetime.now()
            )
            
            print(f"✅ Order placed: {order.order_id}")
            return order
            
        except Exception as e:
            print(f"❌ Order failed: {e}")
            raise
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order"""
        try:
            self.api.cancel_order(order_id=order_id)
            print(f"✅ Order cancelled: {order_id}")
            return True
        except Exception as e:
            print(f"❌ Cancel failed: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Order:
        """Get current status of an order"""
        result = self.api.get_order_history(order_id=order_id)
        
        return Order(
            order_id=result['order_id'],
            symbol=result['trading_symbol'],
            side=result['transaction_type'],
            quantity=result['quantity'],
            order_type=result['order_type'],
            status=result['status'],
            filled_price=result.get('average_price'),
            filled_qty=result.get('filled_quantity', 0),
            timestamp=datetime.fromisoformat(result['order_timestamp'])
        )
    
    def get_positions(self) -> List[Position]:
        """Get all current positions"""
        positions_data = self.api.get_positions()
        
        positions = []
        for pos_data in positions_data:
            # Get current price
            symbol = pos_data['trading_symbol']
            current_price = self.get_live_price(symbol) or pos_data.get('last_price', 0)
            
            position = Position(
                symbol=symbol,
                quantity=pos_data['quantity'],
                avg_price=pos_data['average_price'],
                current_price=current_price,
                pnl=pos_data.get('pnl', 0),
                pnl_pct=pos_data.get('pnl_percent', 0)
            )
            positions.append(position)
        
        return positions
    
    def get_balance(self) -> Dict[str, float]:
        """Get account balance"""
        funds = self.api.get_funds()
        
        return {
            "available": funds.get('available_cash', 0),
            "used": funds.get('used_margin', 0),
            "total": funds.get('total_cash', 0)
        }
    
    def get_pnl(self) -> Dict[str, float]:
        """Get profit/loss statistics"""
        positions = self.get_positions()
        
        realized_pnl = sum(p.pnl for p in positions if p.quantity == 0)
        unrealized_pnl = sum(p.pnl for p in positions if p.quantity != 0)
        
        return {
            "realized": realized_pnl,
            "unrealized": unrealized_pnl,
            "total": realized_pnl + unrealized_pnl
        }
    
    # ==================== INTERNAL HELPERS ====================
    
    def _validate_tick(self, tick: Tick) -> bool:
        """Validate tick data before processing"""
        # Check for reasonable price
        if not (config.PRICE_SANITY_CHECK['min_price'] <= tick.ltp <= config.PRICE_SANITY_CHECK['max_price']):
            print(f"⚠️  Invalid price for {tick.symbol}: ₹{tick.ltp}")
            return False
        
        # Check for extreme price changes
        if tick.symbol in self.latest_prices:
            prev_tick = self.latest_prices[tick.symbol]
            change_pct = abs((tick.ltp - prev_tick.ltp) / prev_tick.ltp)
            
            if change_pct > config.PRICE_SANITY_CHECK['max_tick_change']:
                print(f"⚠️  Suspicious price jump for {tick.symbol}: {change_pct*100:.2f}%")
                return False
        
        return True
    
    def _handle_disconnect(self):
        """Handle WebSocket disconnection"""
        self.connected = False
        
        if self.reconnect_attempts < config.MAX_RECONNECT_ATTEMPTS:
            self.reconnect_attempts += 1
            print(f"🔄 Attempting reconnect ({self.reconnect_attempts}/{config.MAX_RECONNECT_ATTEMPTS})...")
            time.sleep(config.WEBSOCKET_RECONNECT_DELAY)
            
            if self.connect():
                # Re-subscribe to symbols
                symbols = list(self.latest_prices.keys())
                if symbols and self.tick_callback:
                    self.subscribe_ticks(symbols, self.tick_callback)
        else:
            print(f"❌ Max reconnection attempts reached. Stopping.")
    
    def _start_heartbeat_monitor(self):
        """Monitor WebSocket health"""
        def heartbeat():
            while self.connected:
                time.sleep(config.HEARTBEAT_INTERVAL)
                
                # Check if we're receiving ticks
                now = datetime.now()
                for symbol, last_time in self.last_tick_time.items():
                    if (now - last_time).seconds > 60:  # No tick for 1 minute
                        print(f"⚠️  No ticks received for {symbol} in 60s")
        
        self.heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
        self.heartbeat_thread.start()
