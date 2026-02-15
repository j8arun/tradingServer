"""
Strategy Engine - The Brain
Pure trading logic separated from broker details.
Replace this with your XGBoost model.
"""
import numpy as np
from typing import Dict, Optional
from collections import deque
import config

class TradingStrategy:
    """
    Base class for trading strategies
    Your XGBoost model should implement this interface
    """
    
    def __init__(self, name: str = "BaseStrategy"):
        self.name = name
        self.price_history: Dict[str, deque] = {}
    
    def on_tick(self, symbol: str, price: float) -> Optional[str]:
        """
        Process a new price tick and generate signal
        
        Args:
            symbol: Stock symbol
            price: Current price
            
        Returns:
            "BUY", "SELL", or None
        """
        # Store price history
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=config.FEATURE_WINDOW)
        
        self.price_history[symbol].append(price)
        
        # Need enough data to make decision
        if len(self.price_history[symbol]) < config.FEATURE_WINDOW:
            return None
        
        # Generate signal (override this in subclass)
        return self.generate_signal(symbol)
    
    def generate_signal(self, symbol: str) -> Optional[str]:
        """
        Generate trading signal based on current data
        Override this method in your strategy
        """
        raise NotImplementedError("Implement this in your strategy")


class SimpleMovingAverageStrategy(TradingStrategy):
    """
    Example: Simple Moving Average Crossover
    Replace this with your XGBoost model
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


class XGBoostStrategy(TradingStrategy):
    """
    XGBoost Model Strategy - PLACEHOLDER
    This is where you integrate your trained model
    """
    
    def __init__(self, model_path: str = config.XGBOOST_MODEL_PATH):
        super().__init__(name="XGBoost")
        self.model = None
        self.load_model(model_path)
    
    def load_model(self, model_path: str):
        """Load your trained XGBoost model"""
        try:
            import pickle
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
            print(f"✅ XGBoost model loaded from {model_path}")
        except FileNotFoundError:
            print(f"⚠️  Model not found at {model_path}")
            print("    Using placeholder logic for now")
            self.model = None
    
    def generate_signal(self, symbol: str) -> Optional[str]:
        """Generate signal using XGBoost model"""
        
        if self.model is None:
            # Placeholder: Use simple logic until model is trained
            return self._placeholder_logic(symbol)
        
        # Extract features from price history
        features = self._extract_features(symbol)
        
        if features is None:
            return None
        
        # Get model prediction
        prediction = self.model.predict_proba([features])[0]
        
        # prediction = [prob_down, prob_neutral, prob_up]
        confidence = max(prediction)
        
        if confidence < config.MIN_PREDICTION_CONFIDENCE:
            return None  # Not confident enough
        
        # Generate signal
        predicted_class = np.argmax(prediction)
        
        if predicted_class == 2:  # Up
            return "BUY"
        elif predicted_class == 0:  # Down
            return "SELL"
        else:
            return None  # Neutral
    
    def _extract_features(self, symbol: str) -> Optional[np.ndarray]:
        """
        Extract features from price history
        
        Features you might include:
        - Returns (1-min, 5-min, 15-min)
        - RSI
        - MACD
        - Bollinger Bands
        - Volume indicators
        - Previous high/low
        
        This is where your feature engineering goes
        """
        prices = list(self.price_history[symbol])
        
        if len(prices) < config.FEATURE_WINDOW:
            return None
        
        # Example features (expand this with your actual features)
        prices_array = np.array(prices)
        
        features = []
        
        # 1. Returns at different horizons
        features.append((prices[-1] - prices[-2]) / prices[-2])  # 1-min return
        features.append((prices[-1] - prices[-5]) / prices[-5])  # 5-min return
        features.append((prices[-1] - prices[-10]) / prices[-10])  # 10-min return
        
        # 2. RSI (Relative Strength Index)
        rsi = self._calculate_rsi(prices_array, period=14)
        features.append(rsi)
        
        # 3. Price momentum
        sma = np.mean(prices)
        features.append((prices[-1] - sma) / sma)
        
        # 4. Volatility (std dev of returns)
        returns = np.diff(prices_array) / prices_array[:-1]
        features.append(np.std(returns))
        
        # Add more features here...
        
        return np.array(features)
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate RSI indicator"""
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _placeholder_logic(self, symbol: str) -> Optional[str]:
        """Placeholder until model is trained"""
        # Simple momentum strategy
        prices = list(self.price_history[symbol])
        
        if len(prices) < 10:
            return None
        
        recent_change = (prices[-1] - prices[-10]) / prices[-10]
        
        if recent_change > 0.01:  # 1% up
            return "BUY"
        elif recent_change < -0.01:  # 1% down
            return "SELL"
        
        return None
