"""
Main Trading Bot - The Conductor
Orchestrates all components: broker, strategy, risk management, database.
"""
import time
from datetime import datetime
from typing import Dict
import signal
import sys
import config
from interfaces import Tick
from database import TradingDatabase
from utils.risk_manager import RiskManager
from strategies.prime_bot_strategy import PrimeBotStrategy, SimpleMovingAverageStrategy

# Import brokers
from brokers.groww_adapter import GrowwBroker
from brokers.paper_adapter import PaperBroker

class TradingBot:
    """
    Main trading bot that coordinates all components
    """
    
    def __init__(self, mode: str = config.TRADING_MODE):
        self.mode = mode
        self.db = TradingDatabase()
        self.risk_manager = RiskManager(self.db)
        
        # Initialize Prime Bot strategy with your proven settings
        self.strategy = PrimeBotStrategy(
            model_path=config.XGBOOST_MODEL_PATH,
            score_threshold=config.PRIME_SCORE_THRESHOLD,
            adx_min=config.PRIME_ADX_MIN
        )
        
        # Track Nifty for relative features (required by Prime Bot)
        self.nifty_price = None
        
        # Initialize broker based on mode
        if mode == "live":
            print("🚨 LIVE TRADING MODE - USING REAL MONEY 🚨")
            self.broker = GrowwBroker()
        elif mode == "paper":
            print("📝 PAPER TRADING MODE - SIMULATION")
            real_broker = GrowwBroker()  # Still need real data
            self.broker = PaperBroker(real_broker)
        else:
            raise ValueError(f"Invalid mode: {mode}. Use 'live' or 'paper'")
        
        self.running = False
        self.positions: Dict = {}  # {symbol: position_info}
        
        # Setup graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def start(self):
        """Start the trading bot"""
        print("\n" + "="*60)
        print(f"🤖 TRADING BOT STARTING | Strategy: {self.strategy.name}")
        print("="*60 + "\n")
        
        # Connect to broker
        if not self.broker.connect():
            print("❌ Failed to connect to broker. Exiting.")
            return
        
        # Log startup
        self.db.log_event("BOT_START", f"Bot started in {self.mode} mode", "INFO")
        
        # Subscribe to market data (stock + Nifty index)
        symbols_to_track = config.SYMBOLS.copy()
        # if config.NIFTY_SYMBOL not in symbols_to_track:
        #     symbols_to_track.append(config.NIFTY_SYMBOL)
        print(symbols_to_track)
        
        self.broker.subscribe_ticks(symbols_to_track, self.on_tick)
        
        self.running = True
        print("✅ Bot is now running. Press Ctrl+C to stop.\n")
        
        # Main loop
        try:
            while self.running:
                # Check risk limits
                self._check_positions()
                
                # Print status every 30 seconds
                time.sleep(30)
                self._print_status()
                
        except KeyboardInterrupt:
            print("\n⚠️  Keyboard interrupt received")
        finally:
            self.stop()
    
    def on_tick(self, tick: Tick):
        """
        Main callback - executes on every market tick
        Enhanced for Prime Bot to track Nifty data
        """
        # Save tick to database
        self.db.insert_tick(tick)
        
        # Handle Nifty separately (for relative performance calculation)
        if tick.symbol == config.NIFTY_SYMBOL:
            self.nifty_price = tick.ltp
            return  # Don't trade Nifty, just track it
        
        # Get trading signal from Prime Bot strategy
        # Pass Nifty price for relative features
        signal = self.strategy.on_tick(
            symbol=tick.symbol, 
            price=tick.ltp,
            timestamp=tick.timestamp,
            nifty_price=self.nifty_price,
            volume=tick.volume,
            high=tick.ltp,  # Use LTP if high/low not available
            low=tick.ltp
        )
        
        if signal is None:
            return  # No action needed
        
        # Risk check BEFORE trading
        can_trade, reason = self.risk_manager.can_trade()
        if not can_trade:
            print(f"🚫 Trade blocked: {reason}")
            return
        
        # Execute trade based on signal
        if signal == "BUY":
            self._execute_buy(tick.symbol, tick.ltp)
        elif signal == "SELL":
            self._execute_sell(tick.symbol, tick.ltp)
    
    def _execute_buy(self, symbol: str, price: float):
        """Execute a BUY order"""
        # Check if we already have a position
        if symbol in self.positions and self.positions[symbol]['quantity'] > 0:
            print(f"⏭️  Already long {symbol}, skipping")
            return
        
        # Calculate position size
        balance = self.broker.get_balance()
        quantity = self.risk_manager.calculate_position_size(symbol, price, balance['available'])
        
        if quantity == 0:
            print(f"⚠️  Position size too small for {symbol}")
            return
        
        # Validate order
        current_positions = {s: {'quantity': p['quantity'], 'current_price': price} 
                           for s, p in self.positions.items()}
        
        is_valid, reason = self.risk_manager.validate_order(
            symbol, "BUY", quantity, price, current_positions, balance
        )
        
        if not is_valid:
            print(f"🚫 Order validation failed: {reason}")
            return
        
        try:
            # Place order
            order = self.broker.place_order(symbol, "BUY", quantity)
            
            # Record in database
            self.db.insert_order(order, self.strategy.name)
            
            if order.status == "FILLED":
                # Update positions
                self.positions[symbol] = {
                    'side': 'LONG',
                    'quantity': quantity,
                    'entry_price': order.filled_price or price,
                    'entry_time': datetime.now()
                }
                
                # Record trade
                self.db.insert_trade(
                    order.order_id, symbol, "BUY", quantity, 
                    order.filled_price or price, self.strategy.name
                )
                
                print(f"✅ BUY: {quantity} {symbol} @ ₹{order.filled_price or price:.2f}")
                
        except Exception as e:
            print(f"❌ BUY failed: {e}")
            self.db.log_event("ORDER_ERROR", f"BUY {symbol}: {e}", "ERROR")
    
    def _execute_sell(self, symbol: str, price: float):
        """Execute a SELL order"""
        # Check if we have a position to close
        if symbol not in self.positions or self.positions[symbol]['quantity'] == 0:
            print(f"⏭️  No position in {symbol}, skipping")
            return
        
        position = self.positions[symbol]
        quantity = position['quantity']
        
        try:
            # Place order
            order = self.broker.place_order(symbol, "SELL", quantity)
            
            # Record in database
            self.db.insert_order(order, self.strategy.name)
            
            if order.status == "FILLED":
                # Calculate PnL
                exit_price = order.filled_price or price
                entry_price = position['entry_price']
                
                pnl = (exit_price - entry_price) * quantity
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                
                # Update database
                # (Note: You'd need to store trade_id when opening position)
                
                # Close position
                self.positions[symbol]['quantity'] = 0
                
                print(f"✅ SELL: {quantity} {symbol} @ ₹{exit_price:.2f} | PnL: ₹{pnl:.2f} ({pnl_pct:.2f}%)")
                
        except Exception as e:
            print(f"❌ SELL failed: {e}")
            self.db.log_event("ORDER_ERROR", f"SELL {symbol}: {e}", "ERROR")
    
    def _check_positions(self):
        """Check all positions for stop-loss / take-profit"""
        for symbol, position in list(self.positions.items()):
            if position['quantity'] == 0:
                continue
            
            # Get current price
            current_price = self.broker.get_live_price(symbol)
            if current_price is None:
                continue
            
            # Check if we should exit
            should_exit, reason = self.risk_manager.should_exit_position(
                position['entry_price'],
                current_price,
                position['side']
            )
            
            if should_exit:
                print(f"🛑 {reason} for {symbol}")
                self._execute_sell(symbol, current_price)
    
    def _print_status(self):
        """Print current status"""
        balance = self.broker.get_balance()
        pnl = self.broker.get_pnl()
        risk_report = self.risk_manager.get_risk_report()
        
        print("\n" + "="*60)
        print(f"📊 STATUS | {datetime.now().strftime('%H:%M:%S')}")
        print("-"*60)
        print(f"Balance:      ₹{balance['available']:,.2f} / ₹{balance['total']:,.2f}")
        print(f"Unrealized:   ₹{pnl['unrealized']:,.2f}")
        print(f"Realized:     ₹{pnl['realized']:,.2f}")
        print(f"Total PnL:    ₹{pnl['total']:,.2f}")
        print(f"Open Pos:     {len([p for p in self.positions.values() if p['quantity'] > 0])}")
        print(f"Day Trades:   {risk_report['trades_today']}")
        print("="*60 + "\n")
    
    def stop(self):
        """Stop the bot gracefully"""
        print("\n🛑 Stopping bot...")
        self.running = False
        
        # Close all positions
        print("📊 Closing all open positions...")
        for symbol, position in self.positions.items():
            if position['quantity'] > 0:
                current_price = self.broker.get_live_price(symbol)
                if current_price:
                    self._execute_sell(symbol, current_price)
        
        # Disconnect broker
        self.broker.disconnect()
        
        # Print final summary
        self._print_final_summary()
        
        # Log shutdown
        self.db.log_event("BOT_STOP", "Bot stopped", "INFO")
        
        print("✅ Bot stopped successfully\n")
    
    def _print_final_summary(self):
        """Print final performance summary"""
        stats = self.db.get_performance_stats(days=1)
        
        print("\n" + "="*60)
        print("📈 FINAL SUMMARY")
        print("="*60)
        print(f"Total Trades:    {stats['total_trades']}")
        print(f"Winning Trades:  {stats['winning_trades']} ({stats['win_rate']:.1f}%)")
        print(f"Losing Trades:   {stats['losing_trades']}")
        print(f"Gross Profit:    ₹{stats['gross_profit']:,.2f}")
        print(f"Gross Loss:      ₹{stats['gross_loss']:,.2f}")
        print(f"Net PnL:         ₹{stats['net_pnl']:,.2f}")
        print(f"Best Trade:      ₹{stats['best_trade']:,.2f}")
        print(f"Worst Trade:     ₹{stats['worst_trade']:,.2f}")
        print("="*60 + "\n")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print("\n⚠️  Shutdown signal received")
        self.running = False


def main():
    """Entry point"""
    # Create and start bot
    bot = TradingBot(mode=config.TRADING_MODE)
    bot.start()


if __name__ == "__main__":
    main()
