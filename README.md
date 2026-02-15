# 🤖 Production-Ready Algo Trading System

A modular, broker-agnostic algorithmic trading system with real-time data, risk management, and paper trading.

## 🎯 Key Features

- ✅ **WebSocket Data** - Instant ticks (milliseconds latency) vs polling (seconds)
- ✅ **Broker Agnostic** - Swap Groww → Zerodha → Angel with one line
- ✅ **Risk Management** - Stop-loss, position limits, circuit breakers
- ✅ **Paper Trading** - Test with real data, zero risk
- ✅ **Persistent Storage** - SQLite database for all trades and ticks
- ✅ **Strategy Isolation** - XGBoost logic decoupled from broker code
- ✅ **Error Recovery** - Auto-reconnect on WebSocket failures

---

## 📦 Installation

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Get Groww API Access
1. Go to Groww → Settings → API Access
2. Enable API trading (₹499/month usually)
3. Copy your API Token and Secret

### Step 3: Configure
```bash
# Create .env file
echo "GROWW_API_TOKEN=your_token_here" >> .env
echo "GROWW_API_SECRET=your_secret_here" >> .env
```

Or directly edit `config.py` and add your credentials.

---

## 🚀 Quick Start

### Paper Trading (Recommended First)
```bash
# Edit config.py
TRADING_MODE = "paper"  # Simulation mode

# Run bot
python main.py
```

### Live Trading (Real Money)
```bash
# Edit config.py
TRADING_MODE = "live"  # 🚨 USES REAL MONEY

# Run bot
python main.py
```

---

## 📁 File Structure

```
trading_system/
├── config.py              # All settings (API keys, risk limits, symbols)
├── interfaces.py          # Broker contract (IBroker interface)
├── database.py            # SQLite persistence layer
├── main.py                # Main orchestrator
│
├── brokers/
│   ├── groww_adapter.py   # Groww WebSocket implementation
│   └── paper_adapter.py   # Paper trading simulator
│
├── strategies/
│   └── strategy_engine.py # XGBoost model (replace with your model)
│
└── utils/
    ├── risk_manager.py    # Safety checks and position sizing
    └── logger.py          # Logging utilities
```

---

## 🧠 Integrating Your XGBoost Model

### Replace the placeholder in `strategies/strategy_engine.py`:

```python
class XGBoostStrategy(TradingStrategy):
    def __init__(self):
        super().__init__(name="XGBoost")
        
        # Load your trained model
        import pickle
        with open("models/xgboost_model.pkl", "rb") as f:
            self.model = pickle.load(f)
    
    def _extract_features(self, symbol: str):
        """
        Extract features matching your training data
        """
        prices = list(self.price_history[symbol])
        
        # Example features (replace with yours)
        features = {
            'returns_1m': (prices[-1] - prices[-2]) / prices[-2],
            'returns_5m': (prices[-1] - prices[-5]) / prices[-5],
            'rsi': self._calculate_rsi(prices),
            'volume_ma': np.mean(volumes[-20:]),
            # Add your features here...
        }
        
        return features
    
    def generate_signal(self, symbol: str):
        features = self._extract_features(symbol)
        prediction = self.model.predict_proba([features])[0]
        
        if prediction[2] > 0.65:  # 65% confidence for UP
            return "BUY"
        elif prediction[0] > 0.65:  # 65% confidence for DOWN
            return "SELL"
        
        return None
```

---

## ⚙️ Configuration (config.py)

### Trading Parameters
```python
SYMBOLS = ["RELIANCE", "TCS", "INFY"]  # Stocks to trade
TRADING_MODE = "paper"  # "paper" or "live"
```

### Risk Management
```python
MAX_POSITION_SIZE = 50000      # Max ₹ per trade
MAX_TOTAL_EXPOSURE = 200000    # Max total capital at risk
MAX_LOSS_PER_DAY = 10000       # Circuit breaker threshold
STOP_LOSS_PCT = 0.02           # 2% stop loss
TAKE_PROFIT_PCT = 0.05         # 5% take profit
```

### Strategy Settings
```python
XGBOOST_MODEL_PATH = "models/xgboost_model.pkl"
MIN_PREDICTION_CONFIDENCE = 0.65  # Only trade if model is 65%+ confident
```

---

## 🛡️ Risk Management Features

### 1. Position Limits
- Maximum position size per trade
- Maximum total exposure across all positions

### 2. Stop Loss / Take Profit
- Automatic exits when thresholds are hit
- Configurable percentages

### 3. Circuit Breaker
- Stops trading if daily loss exceeds limit
- Prevents catastrophic losses from bugs

### 4. Rate Limiting
- Max orders per minute
- Prevents runaway algorithms

### 5. Price Sanity Checks
- Rejects obviously wrong prices
- Detects suspicious price jumps

---

## 📊 Database Schema

### Tables Created Automatically:
- `ticks` - Every market tick (for model retraining)
- `orders` - All order history
- `trades` - Completed trades with PnL
- `daily_performance` - Daily statistics
- `system_events` - Bot logs and errors

### Query Examples:
```python
from database import TradingDatabase

db = TradingDatabase()

# Get today's PnL
pnl = db.get_daily_pnl()

# Get performance stats
stats = db.get_performance_stats(days=30)
print(f"Win Rate: {stats['win_rate']:.1f}%")
print(f"Net PnL: ₹{stats['net_pnl']:,.2f}")
```

---

## 🔄 Switching Brokers

### Example: Add Zerodha Support

1. Create `brokers/zerodha_adapter.py`:
```python
from interfaces import IBroker

class ZerodhaBroker(IBroker):
    def connect(self):
        # Zerodha-specific connection logic
        pass
    
    # Implement all IBroker methods...
```

2. Update `main.py`:
```python
# Just change ONE line:
# self.broker = GrowwBroker()  # Old
self.broker = ZerodhaBroker()  # New
```

**That's it!** Your strategy code doesn't change at all.

---

## 📈 Monitoring

### Real-time Status (printed every 30s)
```
📊 STATUS | 14:35:22
----------------------------------------
Balance:      ₹85,423.50 / ₹100,000.00
Unrealized:   ₹2,345.00
Realized:     ₹8,123.50
Total PnL:    ₹10,468.50
Open Pos:     2
Day Trades:   12
```

### Optional: Telegram Alerts
```python
# In config.py
ENABLE_TELEGRAM_ALERTS = True
TELEGRAM_BOT_TOKEN = "your_bot_token"
TELEGRAM_CHAT_ID = "your_chat_id"
```

Get instant alerts on:
- Circuit breaker triggers
- Large wins/losses
- System errors

---

## 🐛 Troubleshooting

### Issue: WebSocket disconnects
**Solution:** Auto-reconnect is built-in. Check logs for why.

### Issue: Orders not executing
**Solution:** Check:
1. Risk limits in `config.py`
2. Sufficient balance
3. Trading hours (9:15 AM - 3:30 PM)

### Issue: yfinance blocking
**Solution:** You're already using Groww WebSocket! yfinance not used.

### Issue: Model not loading
**Solution:** Train your model first:
```bash
python train_model.py  # Create this script to train XGBoost
```

---

## 🎯 Next Steps

### Phase 1: Test Paper Trading
1. Run in paper mode for 1 week
2. Analyze results in database
3. Tune `MIN_PREDICTION_CONFIDENCE`

### Phase 2: Train Better Model
1. Use ticks stored in database
2. Retrain XGBoost with more features
3. Backtest improvements

### Phase 3: Go Live (Carefully!)
1. Start with small position sizes
2. Monitor closely for first few days
3. Gradually increase exposure

### Phase 4: Scale
1. Add more symbols
2. Try multiple strategies
3. Implement portfolio optimization

---

## ⚠️ Important Notes

1. **Start Small**: Test with small amounts first
2. **Monitor Daily**: Check logs and PnL every day
3. **Set Stop Losses**: ALWAYS use risk limits
4. **Diversify**: Don't put all capital in one stock
5. **Keep Learning**: Markets change, adapt your model

---

## 📞 Support

- GitHub Issues: [your-repo]/issues
- Email: your-email@example.com
- Discord: [your-server]

---

## 📜 License

MIT License - Free to use and modify

---

**Disclaimer**: This system is for educational purposes. Past performance does not guarantee future results. You are responsible for your own trading decisions.
# tradingServer
