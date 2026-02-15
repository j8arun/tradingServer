# 🚀 Deployment Checklist

Before going live with real money, complete this checklist:

## ✅ Pre-Deployment Steps

### 1. Environment Setup
- [ ] Python 3.8+ installed
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Groww API package installed (`pip install growwapi`)
- [ ] API credentials configured in `config.py` or `.env`

### 2. Configuration Review
- [ ] `TRADING_MODE` set correctly (`"paper"` for testing, `"live"` for real)
- [ ] `SYMBOLS` list contains valid stock tickers
- [ ] `MAX_POSITION_SIZE` appropriate for your capital
- [ ] `MAX_TOTAL_EXPOSURE` appropriate for your capital
- [ ] `MAX_LOSS_PER_DAY` set to protect capital
- [ ] `STOP_LOSS_PCT` and `TAKE_PROFIT_PCT` defined
- [ ] Trading hours correctly set for your timezone

### 3. Model Preparation
- [ ] XGBoost model trained on sufficient data
- [ ] Model saved to `config.XGBOOST_MODEL_PATH`
- [ ] Features in `_extract_features()` match training data
- [ ] `MIN_PREDICTION_CONFIDENCE` threshold tested
- [ ] Backtest results show positive expectancy

### 4. Testing Phase
- [ ] Run `python diagnostic.py` - all checks pass
- [ ] Paper trading for at least 1 week
- [ ] Monitor logs daily during paper trading
- [ ] Review performance with `python dashboard.py`
- [ ] Verify risk management triggers work (manually test stop-loss)
- [ ] Check WebSocket reconnection works (disconnect internet briefly)

### 5. Database & Logging
- [ ] Database initializes correctly
- [ ] Ticks are being recorded (if `ENABLE_TICK_RECORDING = True`)
- [ ] Orders are logged to `orders` table
- [ ] Trades are recorded with correct PnL
- [ ] System events logged for debugging

### 6. Safety Nets
- [ ] Circuit breaker tested (temporarily lower `MAX_LOSS_PER_DAY`)
- [ ] Position size limits enforced
- [ ] Rate limiting prevents runaway orders
- [ ] Price sanity checks reject bad data
- [ ] Trading hours respected (no trading outside market hours)

### 7. Monitoring Setup
- [ ] Log file location confirmed (`trading.log`)
- [ ] Telegram alerts configured (optional but recommended)
- [ ] Dashboard working (`python dashboard.py`)
- [ ] Can monitor bot remotely (SSH, VPN, etc.)

---

## 🚨 Going Live Protocol

### Day 1: Minimal Exposure
```python
# In config.py - START SMALL!
MAX_POSITION_SIZE = 5000      # ₹5,000 per trade
MAX_TOTAL_EXPOSURE = 15000    # ₹15,000 total
MAX_LOSS_PER_DAY = 1000       # ₹1,000 daily limit
SYMBOLS = ["RELIANCE"]        # Start with ONE stock
```

**Tasks:**
- [ ] Change `TRADING_MODE = "live"` in `config.py`
- [ ] Run `python main.py`
- [ ] Monitor continuously for first 2 hours
- [ ] Check logs every 30 minutes
- [ ] Verify orders execute correctly
- [ ] Confirm PnL calculations match broker

### Week 1: Observation
- [ ] Check dashboard daily: `python dashboard.py`
- [ ] Review all trades manually
- [ ] Confirm stop-losses trigger correctly
- [ ] Verify no unexpected behavior
- [ ] Document any issues

### Week 2-4: Gradual Scale-Up
If Week 1 goes well:
```python
# Increase gradually
MAX_POSITION_SIZE = 10000     # ₹10,000
MAX_TOTAL_EXPOSURE = 50000    # ₹50,000
SYMBOLS = ["RELIANCE", "TCS"] # Add one more stock
```

---

## 🛑 Stop Trading If...

1. **Circuit Breaker Triggers Frequently**
   - Review risk settings
   - Check model performance
   - Investigate strategy logic

2. **Win Rate < 40%**
   - Model may need retraining
   - Market conditions may have changed
   - Review feature engineering

3. **Profit Factor < 1.0**
   - Losses exceed wins
   - Strategy not profitable
   - Stop and analyze

4. **Unexpected Orders**
   - Check logs immediately
   - Disconnect broker
   - Debug before resuming

5. **Technical Issues**
   - WebSocket disconnects repeatedly
   - Database errors
   - API rate limits hit

---

## 📊 Daily Routine

### Morning (Before Market Open - 9:00 AM)
1. Check bot is running: `ps aux | grep main.py`
2. Review yesterday's performance: `python dashboard.py`
3. Check logs for errors: `tail -n 50 trading.log`
4. Verify balance matches expectations

### During Trading Hours (9:15 AM - 3:30 PM)
1. Monitor status messages (printed every 30s)
2. Check for circuit breaker triggers
3. Watch for unusual price movements
4. Keep Telegram alerts enabled

### Evening (After Market Close - 4:00 PM)
1. Generate daily report: `python dashboard.py`
2. Review all trades for the day
3. Calculate actual vs expected PnL
4. Check for any warning logs
5. Backup database: `cp trading_system.db backups/$(date +%Y%m%d).db`

### Weekly Review
1. Analyze win rate and profit factor
2. Review per-symbol performance
3. Check if model needs retraining
4. Evaluate risk limit effectiveness
5. Document lessons learned

---

## 🆘 Emergency Procedures

### Immediate Stop
```bash
# Find and kill the bot process
ps aux | grep main.py
kill <PID>

# Or use Ctrl+C in the terminal
```

### Close All Positions Manually
```python
# Run this in Python console
from brokers.groww_adapter import GrowwBroker
broker = GrowwBroker()
broker.connect()

# Get positions
positions = broker.get_positions()

# Close each position
for pos in positions:
    if pos.quantity > 0:
        broker.place_order(pos.symbol, "SELL", pos.quantity)
```

### Emergency Contacts
- Broker Support: [Groww customer care]
- System Administrator: [your contact]
- Developer: [your contact]

---

## 📁 Backup Strategy

### Daily Backups
```bash
# Add to crontab (runs at 4:00 PM)
0 16 * * * cp /path/to/trading_system.db /backups/$(date +\%Y\%m\%d).db
```

### What to Backup
- Database file (`trading_system.db`)
- Logs (`trading.log`)
- Model file (`models/xgboost_model.pkl`)
- Configuration (`config.py`)

---

## 🎯 Success Metrics

### Minimum Viable Performance (Month 1)
- Win Rate: > 45%
- Profit Factor: > 1.2
- Sharpe Ratio: > 1.0
- Max Drawdown: < 10%
- Circuit Breaker: < 2 triggers/week

### Good Performance (Month 3+)
- Win Rate: > 55%
- Profit Factor: > 1.5
- Sharpe Ratio: > 1.5
- Max Drawdown: < 7%
- Consistent monthly profits

---

## 📞 Support & Resources

### Documentation
- README.md - System overview
- This file - Deployment checklist
- Code comments - Implementation details

### Debugging Tools
- `python diagnostic.py` - System health check
- `python dashboard.py` - Performance visualization
- `tail -f trading.log` - Live log monitoring

### Community
- GitHub Issues (if open source)
- Trading forums for strategy discussion
- Python communities for technical help

---

**Remember:** You can always switch back to paper trading if issues arise!

```python
# In config.py
TRADING_MODE = "paper"  # Back to simulation
```

Good luck, and trade responsibly! 🚀
