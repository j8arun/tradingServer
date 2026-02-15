# ⚡ QUICK START GUIDE

Get your trading bot running in 5 minutes!

---

## 🎯 What You Have

A **production-ready algorithmic trading system** with:

✅ **Real-time data** via Groww WebSocket (no more yfinance blocking!)  
✅ **Paper trading** mode (test risk-free)  
✅ **Risk management** (stop-loss, position limits, circuit breakers)  
✅ **Broker-agnostic** design (swap Groww → Zerodha → Angel easily)  
✅ **Complete observability** (logs, database, dashboard)  

---

## 📦 Installation (3 Steps)

### Step 1: Install Dependencies
```bash
cd trading_system
pip install -r requirements.txt
```

### Step 2: Get Groww API Access
1. Log into Groww website
2. Go to **Settings → API Access**
3. Enable API (usually ₹499/month)
4. Copy your **API Token** and **Secret**

### Step 3: Configure
**Option A: Using environment variables** (recommended)
```bash
export GROWW_API_TOKEN="your_token_here"
export GROWW_API_SECRET="your_secret_here"
```

**Option B: Edit config.py directly**
```python
# In config.py, line 9-10
GROWW_API_TOKEN = "paste_your_token_here"
GROWW_API_SECRET = "paste_your_secret_here"
```

---

## 🚀 Run the Bot

### Paper Trading (RECOMMENDED FIRST)
```bash
# Make sure TRADING_MODE = "paper" in config.py
python main.py
```

**You'll see:**
```
🤖 TRADING BOT STARTING | Strategy: XGBoost
📝 PAPER TRADING MODE - SIMULATION
✅ Connected as: Your Name
✅ Paper Trading Ready | Virtual Balance: ₹100,000.00
📡 Subscribing to 4 symbols...
✅ Bot is now running. Press Ctrl+C to stop.
```

### Live Trading (After Testing!)
```bash
# Edit config.py: TRADING_MODE = "live"
python main.py
```

---

## 📊 Monitor Performance

### Real-time (automatically prints every 30s)
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

### Dashboard (run anytime)
```bash
python dashboard.py
```

Shows:
- Overall statistics (win rate, PnL, etc.)
- Daily performance
- Per-symbol breakdown
- Recent trades
- Risk metrics

### Diagnostics (before going live)
```bash
python diagnostic.py
```

Verifies:
- All dependencies installed
- Configuration correct
- Database working
- Model loaded

---

## ⚙️ Essential Configuration

Edit `config.py` for these key settings:

### Trading Parameters
```python
SYMBOLS = ["RELIANCE", "TCS", "INFY", "HDFCBANK"]  # Stocks to trade
TRADING_MODE = "paper"  # "paper" or "live"
```

### Risk Limits (VERY IMPORTANT!)
```python
MAX_POSITION_SIZE = 50000      # Max ₹ per trade
MAX_TOTAL_EXPOSURE = 200000    # Max total capital at risk
MAX_LOSS_PER_DAY = 10000       # Stop trading if you lose this much
STOP_LOSS_PCT = 0.02           # 2% stop loss per trade
TAKE_PROFIT_PCT = 0.05         # 5% take profit per trade
```

### Strategy Settings
```python
XGBOOST_MODEL_PATH = "models/xgboost_model.pkl"  # Your trained model
MIN_PREDICTION_CONFIDENCE = 0.65  # Only trade if model is 65%+ confident
```

---

## 🧠 Integrate Your XGBoost Model

### 1. Train Your Model
```python
# train_model.py (you create this)
import xgboost as xgb
import pickle

# Train your model...
model = xgb.XGBClassifier()
model.fit(X_train, y_train)

# Save it
with open("models/xgboost_model.pkl", "wb") as f:
    pickle.dump(model, f)
```

### 2. Update Feature Extraction
Edit `strategies/strategy_engine.py`, method `_extract_features()`:

```python
def _extract_features(self, symbol: str):
    prices = list(self.price_history[symbol])
    
    # YOUR FEATURES HERE - must match training data!
    features = {
        'returns_1m': (prices[-1] - prices[-2]) / prices[-2],
        'returns_5m': (prices[-1] - prices[-5]) / prices[-5],
        'rsi': self._calculate_rsi(prices),
        'volume_ma': np.mean(volumes[-20:]),
        # ... add all your features
    }
    
    return features
```

### 3. Set Confidence Threshold
In `config.py`:
```python
MIN_PREDICTION_CONFIDENCE = 0.65  # Adjust based on your model's performance
```

---

## 🛡️ Safety Features

Your bot includes multiple safety layers:

### 1. Circuit Breaker
Stops trading if daily loss exceeds limit
```python
MAX_LOSS_PER_DAY = 10000  # ₹10,000
```

### 2. Position Limits
Prevents over-exposure
```python
MAX_POSITION_SIZE = 50000   # Per trade
MAX_TOTAL_EXPOSURE = 200000 # Total
```

### 3. Stop Loss / Take Profit
Automatic exits
```python
STOP_LOSS_PCT = 0.02   # -2%
TAKE_PROFIT_PCT = 0.05 # +5%
```

### 4. Rate Limiting
Prevents runaway algorithms
```python
MAX_ORDERS_PER_MINUTE = 10
```

### 5. Trading Hours
Only trades during market hours
```python
TRADING_HOURS = {
    "start": "09:15",  # NSE opens
    "end": "15:30"     # NSE closes
}
```

---

## 📁 File Structure

```
trading_system/
├── config.py                    # ⚙️  All settings (START HERE)
├── main.py                      # 🤖 Main bot (run this)
├── interfaces.py                # 📝 Broker contract
├── database.py                  # 💾 Data persistence
│
├── brokers/
│   ├── groww_adapter.py        # 🔌 Real Groww connection
│   └── paper_adapter.py        # 📝 Paper trading simulator
│
├── strategies/
│   └── strategy_engine.py      # 🧠 Your XGBoost model goes here
│
├── utils/
│   ├── risk_manager.py         # 🛡️  Safety checks
│   └── logger.py               # 📊 Logging utilities
│
├── dashboard.py                # 📈 Performance visualizer
├── diagnostic.py               # 🔍 System health check
│
├── README.md                   # 📖 Full documentation
├── DEPLOYMENT.md               # 🚀 Go-live checklist
├── ARCHITECTURE.md             # 🏗️  System design details
└── requirements.txt            # 📦 Dependencies
```

---

## 🎯 Recommended Workflow

### Week 1: Paper Trading
1. **Run in paper mode**
   ```bash
   python main.py
   ```

2. **Monitor daily**
   ```bash
   python dashboard.py
   ```

3. **Check logs**
   ```bash
   tail -f trading.log
   ```

4. **Review results**
   - Win rate > 45%?
   - Profit factor > 1.2?
   - Strategy behaving as expected?

### Week 2: Small Live Test
1. **Reduce risk limits** (config.py)
   ```python
   MAX_POSITION_SIZE = 5000    # ₹5,000
   MAX_TOTAL_EXPOSURE = 15000  # ₹15,000
   SYMBOLS = ["RELIANCE"]      # Just one stock
   ```

2. **Switch to live** (config.py)
   ```python
   TRADING_MODE = "live"
   ```

3. **Run and monitor closely**
   ```bash
   python main.py
   ```

4. **Check every hour** for first day

### Week 3+: Scale Gradually
If results are good:
- Increase position sizes
- Add more symbols
- Refine strategy

If results are bad:
- Switch back to paper
- Analyze what went wrong
- Retrain model or adjust features

---

## 🆘 Common Issues

### "growwapi not found"
```bash
pip install growwapi
```

### "No price data"
Check:
- API credentials correct?
- Market hours (9:15 AM - 3:30 PM)?
- Network connection stable?

### "Trade blocked: Outside trading hours"
This is normal! Bot won't trade outside market hours.

### "Circuit breaker active"
You hit the daily loss limit. This is GOOD - it's protecting you!
Reset tomorrow or adjust `MAX_LOSS_PER_DAY` if too strict.

### "Model not found"
Train your XGBoost model first:
```bash
python train_model.py  # You need to create this
```

---

## 📞 Support

### Documentation
- **README.md** - Complete system overview
- **DEPLOYMENT.md** - Go-live checklist
- **ARCHITECTURE.md** - Technical details

### Diagnostics
```bash
python diagnostic.py  # Check system health
python dashboard.py   # View performance
tail -f trading.log   # Monitor live logs
```

### Emergency Stop
Press **Ctrl+C** in the terminal running the bot, or:
```bash
ps aux | grep main.py
kill <PID>
```

---

## ⚠️ Important Reminders

1. **START WITH PAPER TRADING** - Test for at least a week
2. **START WITH SMALL AMOUNTS** - Use minimal position sizes initially
3. **MONITOR DAILY** - Check dashboard and logs every day
4. **USE STOP LOSSES** - Always have risk limits enabled
5. **BACKUP DATA** - Copy `trading_system.db` regularly

---

## 🚀 You're Ready!

Your bot is production-ready with:
✅ Real-time WebSocket data (no more blocking!)  
✅ Risk management (multiple safety layers)  
✅ Paper trading (risk-free testing)  
✅ Complete observability (logs, database, dashboard)  

**Next step:** Run `python diagnostic.py` to verify everything is set up correctly!

Good luck, and trade responsibly! 🎯
