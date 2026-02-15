"""
Prime Bot Strategy - Integrated into New Architecture
Based on your proven trading logic with ADX filter and XGBoost scoring

Original Strategy:
- XGBoost regression model
- ADX filter (>35 for high momentum)
- Score threshold (0.00375)
- Rich feature engineering (Hurst, momentum, vol, Nifty correlation, EMA distance)
"""
import numpy as np
import pandas as pd
from typing import Dict, Optional, List
from collections import deque
from datetime import datetime, timedelta
import config

class TradingStrategy:
    """
    Base class for trading strategies
    Your XGBoost model should implement this interface
    """
    
    def __init__(self, name: str = "BaseStrategy"):
        self.name = name
        self.price_history: Dict[str, deque] = {}
        self.tick_history: Dict[str, List] = {}  # Store full tick data for feature calculation
    
    def on_tick(self, symbol: str, price: float, timestamp: datetime = None, **kwargs) -> Optional[str]:
        """
        Process a new price tick and generate signal
        
        Args:
            symbol: Stock symbol
            price: Current price
            timestamp: Tick timestamp
            **kwargs: Additional data (volume, nifty_price, etc.)
            
        Returns:
            "BUY", "SELL", or None
        """
        # Store tick data
        if symbol not in self.tick_history:
            self.tick_history[symbol] = []
        
        tick_data = {
            'timestamp': timestamp or datetime.now(),
            'price': price,
            **kwargs
        }
        self.tick_history[symbol].append(tick_data)
        
        # Keep limited history (memory management)
        max_history = config.FEATURE_WINDOW * 100  # Enough for feature calculation
        if len(self.tick_history[symbol]) > max_history:
            self.tick_history[symbol] = self.tick_history[symbol][-max_history:]
        
        # Also maintain simple price history (for compatibility)
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=config.FEATURE_WINDOW)
        self.price_history[symbol].append(price)
        
        # Need enough data to make decision
        if len(self.tick_history[symbol]) < config.FEATURE_WINDOW:
            return None
        
        # Generate signal (override this in subclass)
        return self.generate_signal(symbol)
    
    def generate_signal(self, symbol: str) -> Optional[str]:
        """
        Generate trading signal based on current data
        Override this method in your strategy
        """
        raise NotImplementedError("Implement this in your strategy")


class PrimeBotStrategy(TradingStrategy):
    """
    Prime Bot V2 - Your Proven Strategy
    
    Features:
    - XGBoost regression model
    - ADX momentum filter (>35)
    - Score threshold (0.00375)
    - Multi-timeframe features
    
    Original performance metrics should be maintained!
    """
    
    def __init__(self, 
                 model_path: str = config.XGBOOST_MODEL_PATH,
                 score_threshold: float = 0.00375,
                 adx_min: float = 35):
        super().__init__(name="PrimeBot_V2")
        
        self.model = None
        self.score_threshold = score_threshold
        self.adx_min = adx_min
        self.feature_window = 100  # For Hurst, momentum, etc.
        
        # Track Nifty for relative features
        self.nifty_history = deque(maxlen=self.feature_window * 10)
        
        self.load_model(model_path)
    
    def load_model(self, model_path: str):
        """Load your trained XGBoost model"""
        try:
            import xgboost as xgb
            
            # Prime Bot uses XGBRegressor, so we load it that way
            self.model = xgb.XGBRegressor()
            self.model.load_model(model_path)
            
            print(f"✅ Prime Bot model loaded from {model_path}")
            print(f"   Score Threshold: {self.score_threshold}")
            print(f"   ADX Minimum: {self.adx_min}")
            
        except FileNotFoundError:
            print(f"⚠️  Model not found at {model_path}")
            print("    Please upload bajaj_xgboost_v1.json to the models/ directory")
            self.model = None
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            self.model = None
    
    def on_tick(self, symbol: str, price: float, timestamp: datetime = None, 
                nifty_price: float = None, volume: int = None, 
                high: float = None, low: float = None, **kwargs) -> Optional[str]:
        """
        Override to capture Nifty data for relative features
        """
        # Track Nifty separately
        if nifty_price is not None:
            self.nifty_history.append({
                'timestamp': timestamp or datetime.now(),
                'price': nifty_price
            })
        
        # Call parent to store tick
        return super().on_tick(symbol, price, timestamp, 
                              nifty_price=nifty_price, 
                              volume=volume,
                              high=high,
                              low=low,
                              **kwargs)
    
    def generate_signal(self, symbol: str) -> Optional[str]:
        """Generate signal using Prime Bot logic"""
        
        if self.model is None:
            return None  # Model not loaded
        
        # Extract features from tick history
        features = self._extract_prime_features(symbol)
        
        if features is None:
            return None  # Not enough data
        
        # Get model prediction (XGBoost score)
        try:
            score = self.model.predict([features['values']])[0]
            adx = features['adx']
            
            # Apply Prime Bot filters
            if abs(score) > self.score_threshold and adx > self.adx_min:
                signal = "BUY" if score > 0 else "SELL"
                
                print(f"🎯 Prime Signal: {signal} | Score: {score:.5f} | ADX: {adx:.1f}")
                return signal
            
        except Exception as e:
            print(f"⚠️  Prediction error: {e}")
            return None
        
        return None  # No signal
    
    def _extract_prime_features(self, symbol: str) -> Optional[Dict]:
        """
        Extract the exact features used in your original Prime Bot
        
        Features:
        1. f_hurst - Hurst exponent (mean reversion indicator)
        2. f_mom - Momentum (100-period % change)
        3. f_vol - Volatility (100-period std of log returns)
        4. f_rel_nifty - Relative performance vs Nifty
        5. f_dist_ema - Distance from 200-period EMA
        6. f_hour - Hour of day (time-based pattern)
        7. f_adx - ADX (momentum strength)
        """
        ticks = self.tick_history.get(symbol, [])
        
        if len(ticks) < self.feature_window * 2:
            return None  # Need more data
        
        # Convert to DataFrame for easier calculation
        df = pd.DataFrame(ticks)
        
        # Ensure we have price data
        if 'price' not in df.columns:
            return None
        
        # Get high/low for ADX (use price if not available)
        if 'high' not in df.columns:
            df['high'] = df['price']
        if 'low' not in df.columns:
            df['low'] = df['price']
        
        # Calculate features
        try:
            features = {}
            
            # 1. ADX Calculation (14-period)
            window_adx = 14
            high, low, close = df['high'], df['low'], df['price']
            
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
            tr_s = tr.rolling(window_adx).sum()
            
            # Directional Indicators
            pdi = 100 * pd.Series(p_dm).rolling(window_adx).sum() / tr_s
            mdi = 100 * pd.Series(m_dm).rolling(window_adx).sum() / tr_s
            
            # DX and ADX
            dx = 100 * abs(pdi - mdi) / (pdi + mdi)
            adx = dx.rolling(window_adx).mean()
            
            features['adx'] = adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 0
            
            # 2. Log Returns
            log_ret = np.log(df['price'] / df['price'].shift(1))
            
            # 3. Hurst Exponent (mean reversion indicator)
            # Hurst = 0.5 + (correlation of returns with lagged returns) / 2
            corr = log_ret.rolling(self.feature_window).corr(log_ret.shift(1))
            f_hurst = 0.5 + (corr / 2)
            features['f_hurst'] = f_hurst.iloc[-1] if not pd.isna(f_hurst.iloc[-1]) else 0.5
            
            # 4. Momentum (100-period % change)
            f_mom = df['price'].pct_change(self.feature_window)
            features['f_mom'] = f_mom.iloc[-1] if not pd.isna(f_mom.iloc[-1]) else 0
            
            # 5. Volatility (100-period std of log returns)
            f_vol = log_ret.rolling(self.feature_window).std()
            features['f_vol'] = f_vol.iloc[-1] if not pd.isna(f_vol.iloc[-1]) else 0
            
            # 6. Relative to Nifty
            if len(self.nifty_history) >= self.feature_window:
                nifty_df = pd.DataFrame(list(self.nifty_history))
                # Align Nifty with stock data
                nifty_close = nifty_df['price'].reindex(df.index).ffill()
                
                stock_change = df['price'].pct_change(self.feature_window).iloc[-1]
                nifty_change = nifty_close.pct_change(self.feature_window).iloc[-1]
                
                features['f_rel_nifty'] = stock_change - nifty_change if not pd.isna(stock_change) else 0
            else:
                features['f_rel_nifty'] = 0  # Default if no Nifty data
            
            # 7. Distance from 200-period EMA
            ema_200 = df['price'].ewm(span=200).mean()
            f_dist_ema = (df['price'].iloc[-1] / ema_200.iloc[-1]) - 1
            features['f_dist_ema'] = f_dist_ema if not pd.isna(f_dist_ema) else 0
            
            # 8. Hour of day (time-based pattern)
            hour = df['timestamp'].iloc[-1].hour if 'timestamp' in df.columns else 12
            features['f_hour'] = hour
            
            # Create feature vector in correct order
            feature_order = ['f_hurst', 'f_mom', 'f_vol', 'f_rel_nifty', 'f_dist_ema', 'f_hour', 'f_adx']
            feature_values = [features.get(f, 0) for f in feature_order]
            
            return {
                'values': feature_values,
                'adx': features['adx'],
                'features': features  # For debugging
            }
            
        except Exception as e:
            print(f"⚠️  Feature calculation error: {e}")
            return None
    
    def get_model_diagnostics(self) -> Dict:
        """Get current model state for monitoring"""
        return {
            "model_loaded": self.model is not None,
            "score_threshold": self.score_threshold,
            "adx_minimum": self.adx_min,
            "data_points": len(self.tick_history.get(config.SYMBOLS[0], [])) if config.SYMBOLS else 0,
            "nifty_data_points": len(self.nifty_history)
        }


# ==================== SIMPLE STRATEGIES FOR COMPARISON ====================

class SimpleMovingAverageStrategy(TradingStrategy):
    """
    Example: Simple Moving Average Crossover
    Kept for comparison/testing
    """
    
    def __init__(self):
        super().__init__(name="SMA_Crossover")
        self.fast_period = 5
        self.slow_period = 15
    
    def generate_signal(self, symbol: str) -> Optional[str]:
        """Generate signal based on SMA crossover"""
        prices = list(self.price_history[symbol])
        
        if len(prices) < self.slow_period:
            return None
        
        # Calculate moving averages
        fast_sma = np.mean(prices[-self.fast_period:])
        slow_sma = np.mean(prices[-self.slow_period:])
        
        # Previous values
        prev_fast_sma = np.mean(prices[-self.fast_period-1:-1])
        prev_slow_sma = np.mean(prices[-self.slow_period-1:-1])
        
        # Detect crossover
        if prev_fast_sma <= prev_slow_sma and fast_sma > slow_sma:
            return "BUY"
        elif prev_fast_sma >= prev_slow_sma and fast_sma < slow_sma:
            return "SELL"
        
        return None


class MomentumStrategy(TradingStrategy):
    """
    Simple momentum strategy
    Alternative to Prime Bot for testing
    """
    
    def __init__(self, period: int = 20, threshold: float = 0.02):
        super().__init__(name="Momentum")
        self.period = period
        self.threshold = threshold
    
    def generate_signal(self, symbol: str) -> Optional[str]:
        """Generate signal based on momentum"""
        prices = list(self.price_history[symbol])
        
        if len(prices) < self.period:
            return None
        
        # Calculate momentum
        momentum = (prices[-1] - prices[-self.period]) / prices[-self.period]
        
        if momentum > self.threshold:
            return "BUY"
        elif momentum < -self.threshold:
            return "SELL"
        
        return None
