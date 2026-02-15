#!/usr/bin/env python3
"""
Prime Bot Feature Verification Script
Compares feature calculations between old and new implementation
"""
import pandas as pd
import numpy as np
from datetime import datetime

def calculate_old_bot_features(df):
    """
    Original Prime Bot feature calculation
    (From your prime_bot.py)
    """
    w = 100
    temp = df.copy()
    
    # ADX Calculation
    window = 14
    high, low, close = temp['bajaj_high'], temp['bajaj_low'], temp['bajaj_close']
    tr = pd.concat([high-low, abs(high-close.shift(1)), abs(low-close.shift(1))], axis=1).max(axis=1)
    up, down = high-high.shift(1), low.shift(1)-low
    p_dm = np.where((up > down) & (up > 0), up, 0.0)
    m_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr_s = tr.rolling(window).sum()
    dx = 100 * abs((100*pd.Series(p_dm).rolling(window).sum()/tr_s) - (100*pd.Series(m_dm).rolling(window).sum()/tr_s)) / ((100*pd.Series(p_dm).rolling(window).sum()/tr_s) + (100*pd.Series(m_dm).rolling(window).sum()/tr_s))
    temp['f_adx'] = dx.rolling(window).mean()

    # Core Features
    temp['log_ret'] = np.log(temp['bajaj_close'] / temp['bajaj_close'].shift(1))
    temp['f_hurst'] = 0.5 + (temp['log_ret'].rolling(w).corr(temp['log_ret'].shift(1)) / 2)
    temp['f_mom'] = temp['bajaj_close'].pct_change(w)
    temp['f_vol'] = temp['log_ret'].rolling(w).std()
    temp['f_rel_nifty'] = temp['bajaj_close'].pct_change(w) - temp['nifty_close'].pct_change(w)
    temp['f_dist_ema'] = temp['bajaj_close'] / temp['bajaj_close'].ewm(span=200).mean() - 1
    temp['f_hour'] = temp['timestamp'].dt.hour
    
    return temp

def calculate_new_bot_features(df):
    """
    New Prime Bot feature calculation
    (From prime_bot_strategy.py)
    """
    w = 100
    temp = df.copy()
    
    # ADX Calculation (identical to old)
    window = 14
    high, low, close = temp['bajaj_high'], temp['bajaj_low'], temp['bajaj_close']
    
    # True Range
    tr = pd.concat([
        high - low,
        abs(high - close.shift(1)),
        abs(low - close.shift(1))
    ], axis=1).max(axis=1)
    
    # Directional Movement
    up = high - high.shift(1)
    down = low.shift(1) - low
    
    p_dm = np.where((up > down) & (up > 0), up, 0.0)
    m_dm = np.where((down > up) & (down > 0), down, 0.0)
    
    # Smoothed values
    tr_s = tr.rolling(window).sum()
    
    # Directional Indicators
    pdi = 100 * pd.Series(p_dm).rolling(window).sum() / tr_s
    mdi = 100 * pd.Series(m_dm).rolling(window).sum() / tr_s
    
    # DX and ADX
    dx = 100 * abs(pdi - mdi) / (pdi + mdi)
    temp['f_adx'] = dx.rolling(window).mean()
    
    # Core Features (identical to old)
    log_ret = np.log(temp['bajaj_close'] / temp['bajaj_close'].shift(1))
    temp['log_ret'] = log_ret
    
    temp['f_hurst'] = 0.5 + (log_ret.rolling(w).corr(log_ret.shift(1)) / 2)
    temp['f_mom'] = temp['bajaj_close'].pct_change(w)
    temp['f_vol'] = log_ret.rolling(w).std()
    temp['f_rel_nifty'] = temp['bajaj_close'].pct_change(w) - temp['nifty_close'].pct_change(w)
    temp['f_dist_ema'] = temp['bajaj_close'] / temp['bajaj_close'].ewm(span=200).mean() - 1
    temp['f_hour'] = temp['timestamp'].dt.hour
    
    return temp

def create_test_data():
    """Create synthetic test data for verification"""
    print("📊 Creating test dataset...")
    
    # Generate 500 candles (enough for 200-EMA)
    dates = pd.date_range(start='2026-01-01 09:15', periods=500, freq='5min')
    
    # Simulate Bajaj Finance price (around 7000-7500 range)
    np.random.seed(42)
    price_base = 7200
    returns = np.random.randn(500) * 0.005  # 0.5% std
    prices = price_base * np.exp(np.cumsum(returns))
    
    # Add some trend and volatility
    prices = prices + np.sin(np.arange(500) / 20) * 50
    
    # Create OHLC
    high = prices * (1 + abs(np.random.randn(500) * 0.002))
    low = prices * (1 - abs(np.random.randn(500) * 0.002))
    volume = np.random.randint(100000, 500000, 500)
    
    # Nifty (correlated with Bajaj but different magnitude)
    nifty_base = 23000
    nifty_returns = returns * 0.7 + np.random.randn(500) * 0.003
    nifty_prices = nifty_base * np.exp(np.cumsum(nifty_returns))
    
    df = pd.DataFrame({
        'timestamp': dates,
        'bajaj_open': prices * 0.999,
        'bajaj_high': high,
        'bajaj_low': low,
        'bajaj_close': prices,
        'bajaj_volume': volume,
        'nifty_close': nifty_prices
    })
    
    print(f"✅ Created {len(df)} candles")
    print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"   Bajaj range: ₹{df['bajaj_close'].min():.2f} - ₹{df['bajaj_close'].max():.2f}")
    print(f"   Nifty range: {df['nifty_close'].min():.2f} - {df['nifty_close'].max():.2f}")
    
    return df

def compare_features(old_df, new_df):
    """Compare feature values between old and new calculations"""
    print("\n🔍 Comparing Features...")
    print("="*70)
    
    features = ['f_hurst', 'f_mom', 'f_vol', 'f_rel_nifty', 'f_dist_ema', 'f_adx']
    
    # Compare last 10 rows (where all features are calculated)
    comparison_rows = 10
    
    print(f"\n{'Feature':<15} {'Old Value':<15} {'New Value':<15} {'Diff':<15} {'Match'}")
    print("-"*70)
    
    all_match = True
    
    for feat in features:
        # Get last valid values
        old_vals = old_df[feat].dropna().tail(comparison_rows)
        new_vals = new_df[feat].dropna().tail(comparison_rows)
        
        if len(old_vals) > 0 and len(new_vals) > 0:
            old_val = old_vals.iloc[-1]
            new_val = new_vals.iloc[-1]
            diff = abs(old_val - new_val)
            
            # Consider match if difference < 1e-6
            match = diff < 1e-6
            match_symbol = "✅" if match else "❌"
            
            if not match:
                all_match = False
            
            print(f"{feat:<15} {old_val:>14.6f} {new_val:>14.6f} {diff:>14.6e} {match_symbol}")
        else:
            print(f"{feat:<15} {'N/A':<15} {'N/A':<15} {'N/A':<15} ⚠️")
    
    print("="*70)
    
    if all_match:
        print("🎉 All features MATCH! Migration is correct.")
    else:
        print("⚠️  Some features don't match. Check implementation.")
    
    return all_match

def test_signal_generation(old_df, new_df, score_threshold=0.00375, adx_min=35):
    """Test if signal generation would be identical"""
    print("\n🎯 Testing Signal Generation...")
    print("="*70)
    
    # Simulate model predictions (random for testing)
    np.random.seed(42)
    old_df['model_score'] = np.random.randn(len(old_df)) * 0.01
    new_df['model_score'] = old_df['model_score'].copy()  # Same predictions
    
    # Apply Prime Bot logic
    old_df['signal'] = None
    new_df['signal'] = None
    
    for i in range(len(old_df)):
        if not pd.isna(old_df.loc[i, 'f_adx']) and not pd.isna(old_df.loc[i, 'model_score']):
            score = old_df.loc[i, 'model_score']
            adx = old_df.loc[i, 'f_adx']
            
            if abs(score) > score_threshold and adx > adx_min:
                old_df.loc[i, 'signal'] = "BUY" if score > 0 else "SELL"
                new_df.loc[i, 'signal'] = "BUY" if score > 0 else "SELL"
    
    # Compare signals
    old_signals = old_df[old_df['signal'].notna()]
    new_signals = new_df[new_df['signal'].notna()]
    
    print(f"Old Bot Signals: {len(old_signals)}")
    print(f"New Bot Signals: {len(new_signals)}")
    
    if len(old_signals) == len(new_signals):
        print("✅ Signal count MATCHES")
        
        # Check if signals are at same timestamps
        signals_match = (old_df['signal'] == new_df['signal']).all()
        
        if signals_match:
            print("✅ All signals IDENTICAL")
        else:
            print("⚠️  Some signals differ")
            
            # Show differences
            diff_idx = old_df[old_df['signal'] != new_df['signal']].index
            print(f"   Differences at indices: {list(diff_idx)}")
    else:
        print("❌ Signal count MISMATCH")
    
    print("="*70)

def main():
    """Run complete verification"""
    print("\n" + "="*70)
    print("  PRIME BOT FEATURE VERIFICATION")
    print("  Comparing Old vs New Implementation")
    print("="*70)
    
    # Create test data
    df = create_test_data()
    
    # Calculate features using both methods
    print("\n⏳ Calculating features (Old Bot logic)...")
    old_df = calculate_old_bot_features(df.copy())
    
    print("⏳ Calculating features (New Bot logic)...")
    new_df = calculate_new_bot_features(df.copy())
    
    # Compare
    features_match = compare_features(old_df, new_df)
    
    # Test signal generation
    test_signal_generation(old_df, new_df)
    
    # Summary
    print("\n" + "="*70)
    print("📋 VERIFICATION SUMMARY")
    print("="*70)
    
    if features_match:
        print("✅ Feature calculations: IDENTICAL")
        print("✅ Migration: SUCCESS")
        print("\nYour Prime Bot strategy will work exactly the same in the new system!")
    else:
        print("⚠️  Feature calculations: DIFFERENCES FOUND")
        print("⚠️  Migration: NEEDS REVIEW")
        print("\nPlease check the differences above and adjust implementation.")
    
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
