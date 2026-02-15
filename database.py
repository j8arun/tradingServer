"""
Database Layer - The Memory
Handles all data persistence: ticks, trades, positions, and performance metrics.
"""
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import threading
from contextlib import contextmanager
import config

class TradingDatabase:
    """Thread-safe database manager for trading system"""
    
    def __init__(self, db_path: str = config.DB_PATH):
        self.db_path = db_path
        self.local = threading.local()
        self.init_tables()
    
    @contextmanager
    def get_connection(self):
        """Thread-safe connection manager"""
        if not hasattr(self.local, 'conn'):
            self.local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.local.conn.row_factory = sqlite3.Row
        try:
            yield self.local.conn
        except Exception as e:
            self.local.conn.rollback()
            raise e
    
    def init_tables(self):
        """Create all necessary tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Ticks table (high-frequency data)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ticks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    symbol TEXT NOT NULL,
                    ltp REAL NOT NULL,
                    volume INTEGER,
                    bid REAL,
                    ask REAL,
                    oi INTEGER
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ticks_symbol_time ON ticks(symbol, timestamp)')
            
            # 2. Orders table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    order_type TEXT NOT NULL,
                    price REAL,
                    status TEXT NOT NULL,
                    filled_price REAL,
                    filled_qty INTEGER DEFAULT 0,
                    timestamp DATETIME NOT NULL,
                    strategy_name TEXT
                )
            ''')
            
            # 3. Trades table (filled orders with PnL)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    pnl REAL,
                    pnl_pct REAL,
                    entry_time DATETIME NOT NULL,
                    exit_time DATETIME,
                    strategy_name TEXT,
                    FOREIGN KEY (order_id) REFERENCES orders(order_id)
                )
            ''')
            
            # 4. Daily performance table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_performance (
                    date DATE PRIMARY KEY,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    gross_profit REAL DEFAULT 0,
                    gross_loss REAL DEFAULT 0,
                    net_pnl REAL DEFAULT 0,
                    max_drawdown REAL DEFAULT 0,
                    sharpe_ratio REAL
                )
            ''')
            
            # 5. System events log
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    event_type TEXT NOT NULL,
                    message TEXT,
                    severity TEXT DEFAULT 'INFO'
                )
            ''')
            
            conn.commit()
    
    # ==================== TICK OPERATIONS ====================
    
    def insert_tick(self, tick: 'Tick'):
        """Insert a single tick"""
        if not config.ENABLE_TICK_RECORDING:
            return
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO ticks (timestamp, symbol, ltp, volume, bid, ask, oi)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (tick.timestamp, tick.symbol, tick.ltp, tick.volume, tick.bid, tick.ask, tick.oi))
            conn.commit()
    
    def bulk_insert_ticks(self, ticks: List['Tick']):
        """Insert multiple ticks efficiently"""
        if not config.ENABLE_TICK_RECORDING or not ticks:
            return
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            data = [(t.timestamp, t.symbol, t.ltp, t.volume, t.bid, t.ask, t.oi) for t in ticks]
            cursor.executemany('''
                INSERT INTO ticks (timestamp, symbol, ltp, volume, bid, ask, oi)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', data)
            conn.commit()
    
    def get_recent_ticks(self, symbol: str, minutes: int = 60) -> List[Dict]:
        """Get ticks for the last N minutes"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff = datetime.now() - timedelta(minutes=minutes)
            cursor.execute('''
                SELECT * FROM ticks 
                WHERE symbol = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            ''', (symbol, cutoff))
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== ORDER OPERATIONS ====================
    
    def insert_order(self, order: 'Order', strategy_name: str = "XGBoost"):
        """Record an order"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO orders (order_id, symbol, side, quantity, order_type, 
                                   price, status, filled_price, filled_qty, timestamp, strategy_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (order.order_id, order.symbol, order.side, order.quantity, order.order_type,
                  order.price, order.status, order.filled_price, order.filled_qty, 
                  order.timestamp or datetime.now(), strategy_name))
            conn.commit()
    
    def update_order_status(self, order_id: str, status: str, filled_price: float = None, filled_qty: int = None):
        """Update order when it gets filled/rejected"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE orders 
                SET status = ?, filled_price = COALESCE(?, filled_price), 
                    filled_qty = COALESCE(?, filled_qty)
                WHERE order_id = ?
            ''', (status, filled_price, filled_qty, order_id))
            conn.commit()
    
    # ==================== TRADE OPERATIONS ====================
    
    def insert_trade(self, order_id: str, symbol: str, side: str, quantity: int, 
                     entry_price: float, strategy_name: str = "XGBoost"):
        """Record a new trade (entry)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO trades (order_id, symbol, side, quantity, entry_price, entry_time, strategy_name)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (order_id, symbol, side, quantity, entry_price, datetime.now(), strategy_name))
            conn.commit()
    
    def close_trade(self, trade_id: int, exit_price: float):
        """Close a trade and calculate PnL"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM trades WHERE id = ?', (trade_id,))
            trade = dict(cursor.fetchone())
            
            # Calculate PnL
            if trade['side'] == 'BUY':
                pnl = (exit_price - trade['entry_price']) * trade['quantity']
            else:  # SELL (short)
                pnl = (trade['entry_price'] - exit_price) * trade['quantity']
            
            pnl_pct = (pnl / (trade['entry_price'] * trade['quantity'])) * 100
            
            cursor.execute('''
                UPDATE trades
                SET exit_price = ?, pnl = ?, pnl_pct = ?, exit_time = ?
                WHERE id = ?
            ''', (exit_price, pnl, pnl_pct, datetime.now(), trade_id))
            conn.commit()
            
            return pnl
    
    # ==================== ANALYTICS ====================
    
    def get_daily_pnl(self, date: datetime.date = None) -> float:
        """Get total PnL for a specific date"""
        if date is None:
            date = datetime.now().date()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COALESCE(SUM(pnl), 0) as total_pnl
                FROM trades
                WHERE DATE(exit_time) = ?
            ''', (date,))
            return cursor.fetchone()['total_pnl']
    
    def get_performance_stats(self, days: int = 30) -> Dict:
        """Get comprehensive performance statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff = datetime.now() - timedelta(days=days)
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                    COALESCE(SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END), 0) as gross_profit,
                    COALESCE(SUM(CASE WHEN pnl < 0 THEN pnl ELSE 0 END), 0) as gross_loss,
                    COALESCE(SUM(pnl), 0) as net_pnl,
                    COALESCE(AVG(pnl), 0) as avg_pnl,
                    MAX(pnl) as best_trade,
                    MIN(pnl) as worst_trade
                FROM trades
                WHERE exit_time >= ?
            ''', (cutoff,))
            
            stats = dict(cursor.fetchone())
            
            # Calculate win rate
            if stats['total_trades'] > 0:
                stats['win_rate'] = (stats['winning_trades'] / stats['total_trades']) * 100
            else:
                stats['win_rate'] = 0
            
            return stats
    
    def log_event(self, event_type: str, message: str, severity: str = "INFO"):
        """Log system events"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO system_events (timestamp, event_type, message, severity)
                VALUES (?, ?, ?, ?)
            ''', (datetime.now(), event_type, message, severity))
            conn.commit()
