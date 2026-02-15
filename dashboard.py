#!/usr/bin/env python3
"""
Trading Dashboard - Visualize Performance
Shows trades, PnL charts, and statistics
"""
import sqlite3
from datetime import datetime, timedelta
import config

def print_banner(text):
    """Print a fancy banner"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def get_daily_stats(days=7):
    """Get daily performance statistics"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    cursor.execute('''
        SELECT 
            DATE(exit_time) as date,
            COUNT(*) as trades,
            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
            ROUND(SUM(pnl), 2) as net_pnl,
            ROUND(AVG(pnl), 2) as avg_pnl
        FROM trades
        WHERE exit_time >= ?
        GROUP BY DATE(exit_time)
        ORDER BY date DESC
    ''', (cutoff,))
    
    return cursor.fetchall()

def get_trade_history(limit=20):
    """Get recent trades"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            symbol,
            side,
            quantity,
            entry_price,
            exit_price,
            ROUND(pnl, 2) as pnl,
            ROUND(pnl_pct, 2) as pnl_pct,
            exit_time
        FROM trades
        WHERE exit_time IS NOT NULL
        ORDER BY exit_time DESC
        LIMIT ?
    ''', (limit,))
    
    return cursor.fetchall()

def get_position_summary():
    """Get summary by symbol"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            symbol,
            COUNT(*) as total_trades,
            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
            ROUND(SUM(pnl), 2) as net_pnl,
            ROUND(AVG(pnl), 2) as avg_pnl,
            ROUND(MAX(pnl), 2) as best_trade,
            ROUND(MIN(pnl), 2) as worst_trade
        FROM trades
        WHERE exit_time IS NOT NULL
        GROUP BY symbol
        ORDER BY net_pnl DESC
    ''')
    
    return cursor.fetchall()

def get_overall_stats():
    """Get overall system statistics"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            COUNT(*) as total_trades,
            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
            SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
            ROUND(SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END), 2) as gross_profit,
            ROUND(SUM(CASE WHEN pnl < 0 THEN pnl ELSE 0 END), 2) as gross_loss,
            ROUND(SUM(pnl), 2) as net_pnl,
            ROUND(AVG(pnl), 2) as avg_pnl,
            ROUND(MAX(pnl), 2) as best_trade,
            ROUND(MIN(pnl), 2) as worst_trade
        FROM trades
        WHERE exit_time IS NOT NULL
    ''')
    
    row = cursor.fetchone()
    
    if row and row[0] > 0:
        stats = {
            'total_trades': row[0],
            'winning_trades': row[1],
            'losing_trades': row[2],
            'win_rate': (row[1] / row[0] * 100) if row[0] > 0 else 0,
            'gross_profit': row[3],
            'gross_loss': row[4],
            'net_pnl': row[5],
            'avg_pnl': row[6],
            'best_trade': row[7],
            'worst_trade': row[8],
            'profit_factor': abs(row[3] / row[4]) if row[4] != 0 else 0
        }
        return stats
    
    return None

def show_overall_stats():
    """Display overall statistics"""
    print_banner("📊 OVERALL STATISTICS")
    
    stats = get_overall_stats()
    
    if not stats:
        print("No trades recorded yet.")
        return
    
    print(f"\n{'Metric':<25} {'Value':<20}")
    print("-" * 45)
    print(f"{'Total Trades':<25} {stats['total_trades']}")
    print(f"{'Winning Trades':<25} {stats['winning_trades']} ({stats['win_rate']:.1f}%)")
    print(f"{'Losing Trades':<25} {stats['losing_trades']}")
    print(f"{'Gross Profit':<25} ₹{stats['gross_profit']:,.2f}")
    print(f"{'Gross Loss':<25} ₹{stats['gross_loss']:,.2f}")
    print(f"{'Net PnL':<25} ₹{stats['net_pnl']:,.2f}")
    print(f"{'Average PnL per Trade':<25} ₹{stats['avg_pnl']:,.2f}")
    print(f"{'Best Trade':<25} ₹{stats['best_trade']:,.2f}")
    print(f"{'Worst Trade':<25} ₹{stats['worst_trade']:,.2f}")
    print(f"{'Profit Factor':<25} {stats['profit_factor']:.2f}")

def show_daily_stats():
    """Display daily performance"""
    print_banner("📅 DAILY PERFORMANCE (Last 7 Days)")
    
    rows = get_daily_stats(days=7)
    
    if not rows:
        print("No trades recorded yet.")
        return
    
    print(f"\n{'Date':<15} {'Trades':<10} {'Wins':<8} {'Losses':<8} {'Net PnL':<15} {'Avg PnL'}")
    print("-" * 75)
    
    for row in rows:
        date, trades, wins, losses, net_pnl, avg_pnl = row
        pnl_indicator = "🟢" if net_pnl > 0 else "🔴" if net_pnl < 0 else "⚪"
        print(f"{date:<15} {trades:<10} {wins:<8} {losses:<8} {pnl_indicator} ₹{net_pnl:>10,.2f}  ₹{avg_pnl:>8,.2f}")

def show_symbol_performance():
    """Display performance by symbol"""
    print_banner("🎯 PERFORMANCE BY SYMBOL")
    
    rows = get_position_summary()
    
    if not rows:
        print("No trades recorded yet.")
        return
    
    print(f"\n{'Symbol':<12} {'Trades':<8} {'Wins':<8} {'Net PnL':<15} {'Avg PnL':<12} {'Best':<12} {'Worst'}")
    print("-" * 85)
    
    for row in rows:
        symbol, trades, wins, net_pnl, avg_pnl, best, worst = row
        win_rate = (wins / trades * 100) if trades > 0 else 0
        pnl_indicator = "🟢" if net_pnl > 0 else "🔴" if net_pnl < 0 else "⚪"
        
        print(f"{symbol:<12} {trades:<8} {wins} ({win_rate:.0f}%)   "
              f"{pnl_indicator} ₹{net_pnl:>9,.2f}  ₹{avg_pnl:>9,.2f}  "
              f"₹{best:>9,.2f}  ₹{worst:>9,.2f}")

def show_recent_trades():
    """Display recent trade history"""
    print_banner("📝 RECENT TRADES")
    
    rows = get_trade_history(limit=15)
    
    if not rows:
        print("No trades recorded yet.")
        return
    
    print(f"\n{'Time':<17} {'Symbol':<10} {'Side':<6} {'Qty':<6} {'Entry':<10} {'Exit':<10} {'PnL':<12} {'PnL %'}")
    print("-" * 95)
    
    for row in rows:
        symbol, side, qty, entry, exit_p, pnl, pnl_pct, exit_time = row
        
        # Format timestamp
        ts = datetime.fromisoformat(exit_time).strftime("%m-%d %H:%M:%S")
        
        # Color indicators
        pnl_indicator = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
        
        print(f"{ts:<17} {symbol:<10} {side:<6} {qty:<6} ₹{entry:>8.2f} ₹{exit_p:>8.2f} "
              f"{pnl_indicator} ₹{pnl:>8.2f}  {pnl_pct:>6.2f}%")

def show_risk_metrics():
    """Display risk metrics"""
    print_banner("🛡️ RISK METRICS")
    
    stats = get_overall_stats()
    
    if not stats:
        print("No trades recorded yet.")
        return
    
    # Calculate additional risk metrics
    winning_avg = stats['gross_profit'] / stats['winning_trades'] if stats['winning_trades'] > 0 else 0
    losing_avg = abs(stats['gross_loss'] / stats['losing_trades']) if stats['losing_trades'] > 0 else 0
    
    reward_risk_ratio = winning_avg / losing_avg if losing_avg > 0 else 0
    
    print(f"\n{'Metric':<30} {'Value':<20}")
    print("-" * 50)
    print(f"{'Max Position Size':<30} ₹{config.MAX_POSITION_SIZE:,.2f}")
    print(f"{'Max Total Exposure':<30} ₹{config.MAX_TOTAL_EXPOSURE:,.2f}")
    print(f"{'Daily Loss Limit':<30} ₹{config.MAX_LOSS_PER_DAY:,.2f}")
    print(f"{'Stop Loss':<30} {config.STOP_LOSS_PCT * 100:.1f}%")
    print(f"{'Take Profit':<30} {config.TAKE_PROFIT_PCT * 100:.1f}%")
    print(f"{'Avg Winning Trade':<30} ₹{winning_avg:,.2f}")
    print(f"{'Avg Losing Trade':<30} ₹{losing_avg:,.2f}")
    print(f"{'Reward/Risk Ratio':<30} {reward_risk_ratio:.2f}")

def main():
    """Main dashboard"""
    print("\n" + "="*70)
    print("  🤖 TRADING SYSTEM DASHBOARD")
    print("="*70)
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Show all sections
    show_overall_stats()
    show_daily_stats()
    show_symbol_performance()
    show_recent_trades()
    show_risk_metrics()
    
    print("\n" + "="*70)
    print("  Dashboard complete. Happy trading! 🚀")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
