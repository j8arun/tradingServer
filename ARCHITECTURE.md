# 🏗️ System Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        TRADING BOT SYSTEM                        │
└─────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │   main.py        │
                    │  (Orchestrator)  │
                    └────────┬─────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│  Risk Manager  │  │   Database     │  │   Strategy     │
│  (Safety)      │  │   (Memory)     │  │   (Brain)      │
└────────────────┘  └────────────────┘  └────────────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             ▼
                    ┌────────────────┐
                    │  Broker Layer  │
                    │  (Interface)   │
                    └────────┬───────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
     ┌────────────────┐           ┌────────────────┐
     │  Groww Broker  │           │  Paper Broker  │
     │  (Real Money)  │           │  (Simulation)  │
     └────────┬───────┘           └────────┬───────┘
              │                             │
              ▼                             ▼
     ┌────────────────┐           ┌────────────────┐
     │  Groww API     │           │  Fake Orders   │
     │  (WebSocket)   │           │  (Test Data)   │
     └────────────────┘           └────────────────┘
```

---

## Component Details

### 1. Main Orchestrator (`main.py`)

**Purpose:** Central coordinator that ties everything together

**Responsibilities:**
- Initialize all components (broker, database, strategy, risk manager)
- Subscribe to market data streams
- Route ticks to strategy
- Execute trading signals (after risk checks)
- Monitor positions continuously
- Handle graceful shutdown

**Key Methods:**
- `start()` - Boot up the system
- `on_tick(tick)` - Process each market tick
- `_execute_buy()` - Place buy orders
- `_execute_sell()` - Place sell orders
- `_check_positions()` - Monitor for stop-loss/take-profit
- `stop()` - Graceful shutdown

---

### 2. Broker Interface (`interfaces.py`)

**Purpose:** Contract that all brokers must follow

**Why It Exists:**
- Decouple strategy from broker-specific code
- Switch brokers by changing ONE line
- Enable paper trading with same strategy code

**Core Interface (IBroker):**
```python
class IBroker:
    def connect() -> bool
    def subscribe_ticks(symbols, callback)
    def get_live_price(symbol) -> float
    def place_order(...) -> Order
    def get_positions() -> List[Position]
    def get_balance() -> Dict
    def get_pnl() -> Dict
```

**Implementations:**
1. `GrowwBroker` - Real trading via Groww API
2. `PaperBroker` - Simulated trading with fake money

---

### 3. Broker Adapters

#### A. Groww Adapter (`brokers/groww_adapter.py`)

**Purpose:** Connect to Groww's WebSocket API for real-time data

**Key Features:**
- ✅ WebSocket (push data, milliseconds latency)
- ✅ Auto-reconnect on disconnect
- ✅ Heartbeat monitoring
- ✅ Price validation (sanity checks)
- ✅ Real order execution

**Data Flow:**
```
Groww API → WebSocket → on_tick_received() → Validate → 
Update Cache → Call user callback → Strategy processes
```

**Error Handling:**
- Automatic reconnection (up to MAX_RECONNECT_ATTEMPTS)
- WebSocket error callbacks
- Network failure recovery

#### B. Paper Adapter (`brokers/paper_adapter.py`)

**Purpose:** Risk-free testing with real market data

**How It Works:**
- Uses real broker for price data
- Simulates order execution instantly
- Tracks virtual balance and positions
- Calculates PnL as if real

**Benefits:**
- Zero financial risk
- Test strategy changes safely
- Debug issues without losing money
- Perfect for model training

---

### 4. Strategy Engine (`strategies/strategy_engine.py`)

**Purpose:** The "brain" that generates trading signals

**Base Class: `TradingStrategy`**
```python
def on_tick(symbol, price):
    # Store price history
    # Generate signal if enough data
    return "BUY" | "SELL" | None
```

**Current Implementations:**

#### A. XGBoostStrategy
- Loads trained XGBoost model
- Extracts features from price history
- Makes predictions with confidence threshold
- Returns signals only when confident

**Feature Engineering Example:**
- Returns (1-min, 5-min, 10-min)
- RSI (Relative Strength Index)
- Price momentum vs moving average
- Volatility (standard deviation)
- *(Add your custom features here)*

#### B. SimpleMovingAverageStrategy
- Example: SMA crossover
- Fast MA crosses slow MA = BUY
- Slow MA crosses fast MA = SELL

**How to Add Your Model:**
1. Create class extending `TradingStrategy`
2. Implement `generate_signal()` method
3. Update `main.py` to use your strategy

---

### 5. Risk Manager (`utils/risk_manager.py`)

**Purpose:** The safety net that prevents catastrophic losses

**Critical Checks:**

#### Pre-Trade Validation
```python
can_trade() -> (allowed, reason)
  ├─ Check trading hours (9:15 AM - 3:30 PM)
  ├─ Check circuit breaker (daily loss limit)
  ├─ Check rate limiting (orders per minute)
  └─ Return: True/False + reason
```

#### Order Validation
```python
validate_order(symbol, side, quantity, price, ...) -> (valid, reason)
  ├─ Position size limit (₹50,000)
  ├─ Total exposure limit (₹200,000)
  ├─ Sufficient balance
  ├─ Price sanity check
  └─ Return: True/False + reason
```

#### Position Monitoring
```python
should_exit_position(entry, current, side) -> (exit, reason)
  ├─ Stop-loss check (-2%)
  ├─ Take-profit check (+5%)
  └─ Return: True/False + reason
```

#### Position Sizing
- Fixed size method (₹10,000 per trade)
- Risk parity method (2% of capital at risk)
- Ensures max position size never exceeded

**Circuit Breaker:**
- Triggered when daily loss exceeds `MAX_LOSS_PER_DAY`
- Immediately stops all trading
- Requires manual reset next day

---

### 6. Database Layer (`database.py`)

**Purpose:** Persistent storage for all trading data

**Tables:**

#### 1. `ticks` - Market Data
```sql
timestamp, symbol, ltp, volume, bid, ask, oi
```
- Records every price tick
- Used for model retraining
- Can be disabled to save space

#### 2. `orders` - Order History
```sql
order_id, symbol, side, quantity, price, status, 
filled_price, filled_qty, timestamp, strategy_name
```
- Every order placed
- Tracks status (PENDING → FILLED/REJECTED)

#### 3. `trades` - Completed Trades
```sql
order_id, symbol, side, quantity, entry_price, 
exit_price, pnl, pnl_pct, entry_time, exit_time
```
- Only closed positions
- Includes calculated PnL

#### 4. `daily_performance` - Statistics
```sql
date, total_trades, winning_trades, losing_trades,
gross_profit, gross_loss, net_pnl, max_drawdown
```
- Daily aggregates
- For performance tracking

#### 5. `system_events` - Logs
```sql
timestamp, event_type, message, severity
```
- BOT_START, BOT_STOP
- CIRCUIT_BREAKER, ORDER_ERROR
- All significant events

**Key Features:**
- Thread-safe (multiple ticks per second)
- Bulk insert for efficiency
- Context managers for safety
- Automatic indexing for speed

---

## Data Flow Diagram

### Normal Trading Flow

```
1. Market Tick Arrives (WebSocket)
   ↓
2. Broker Receives & Validates Price
   ↓
3. Save to Database (ticks table)
   ↓
4. Strategy.on_tick() Called
   ↓
5. Strategy Generates Signal (BUY/SELL/None)
   ↓
6. Risk Manager Validates Trade
   │
   ├─ PASS → Continue
   └─ FAIL → Log & Skip
   ↓
7. Calculate Position Size
   ↓
8. Place Order via Broker
   ↓
9. Record Order to Database
   ↓
10. Monitor Position for Stop-Loss
```

### Position Closing Flow

```
1. _check_positions() Loop (every 30s)
   ↓
2. Get Current Price
   ↓
3. Calculate Current PnL
   ↓
4. Risk Manager Checks Exit Conditions
   │
   ├─ Stop-Loss Hit (-2%)
   ├─ Take-Profit Hit (+5%)
   └─ Strategy Signal (SELL)
   ↓
5. Place SELL Order
   ↓
6. Update Database (trades table)
   ↓
7. Calculate & Record Final PnL
```

---

## Configuration Flow

```
config.py
  ├─ API_CREDENTIALS → Broker Adapter
  ├─ SYMBOLS → Main Orchestrator → Broker
  ├─ RISK_LIMITS → Risk Manager
  ├─ STRATEGY_PARAMS → Strategy Engine
  └─ TRADING_MODE → Determines Broker Type
                    ├─ "live" → GrowwBroker
                    └─ "paper" → PaperBroker(GrowwBroker)
```

---

## Error Handling Strategy

### Connection Errors
```
WebSocket Disconnect
  ↓
Broker._handle_disconnect() Called
  ↓
Wait WEBSOCKET_RECONNECT_DELAY seconds
  ↓
Attempt Reconnect (up to MAX_RECONNECT_ATTEMPTS)
  ↓
  ├─ Success → Re-subscribe to Symbols
  └─ Failure → Log Error, Notify User
```

### Order Errors
```
Order Placement Fails
  ↓
Exception Caught in _execute_buy/sell()
  ↓
Log to Database (system_events)
  ↓
Send Telegram Alert (if configured)
  ↓
Continue Trading (don't crash)
```

### Risk Violations
```
Risk Check Fails
  ↓
Log Reason
  ↓
Skip Order (don't execute)
  ↓
Continue Monitoring
```

---

## Threading Model

```
Main Thread (Orchestrator)
  │
  ├─ Broker Thread (WebSocket)
  │    └─ on_tick() callbacks
  │
  ├─ Heartbeat Thread
  │    └─ Monitor connection health
  │
  └─ Position Monitor (30s loop)
       └─ Check stop-loss/take-profit
```

**Thread Safety:**
- Database uses thread-local connections
- Price cache protected by locks
- Order queue is thread-safe

---

## Scalability Considerations

### Current Capacity
- **Symbols:** Up to ~20 (limited by WebSocket bandwidth)
- **Tick Rate:** ~1 tick/second per symbol
- **Database:** SQLite sufficient for single-user
- **Orders:** Limited by broker API rate limits

### Scaling Path

#### Phase 1: More Symbols
- Keep same architecture
- Monitor WebSocket latency
- May need multiple connections

#### Phase 2: Higher Frequency
- Move to PostgreSQL for better write performance
- Implement batch tick processing
- Consider time-series database (InfluxDB)

#### Phase 3: Multiple Strategies
- Run strategies in parallel threads
- Aggregate signals before execution
- Implement portfolio optimizer

#### Phase 4: Multi-Broker
- Add more broker adapters
- Implement broker router (route orders to best broker)
- Cross-broker arbitrage opportunities

---

## Security Considerations

### API Credentials
- Never commit to Git
- Use environment variables
- Consider encrypted storage

### Database
- No sensitive data in database
- Regular backups
- Access control on production servers

### Logs
- Don't log API keys
- Sanitize order details
- Rotate logs regularly

---

## Monitoring & Observability

### Logs (`trading.log`)
- All orders (placed, filled, rejected)
- Risk violations
- Strategy signals
- System events

### Dashboard (`dashboard.py`)
- Overall statistics (PnL, win rate, etc.)
- Daily performance
- Per-symbol breakdown
- Recent trades
- Risk metrics

### Real-time Status (printed every 30s)
- Current balance
- Open positions
- Unrealized PnL
- Trades today

### Alerts (optional Telegram)
- Circuit breaker triggered
- Large win/loss (configurable threshold)
- Critical errors

---

## Deployment Architecture

### Development
```
Local Machine → Paper Trading → Test Strategy
```

### Production
```
VPS/Cloud Server
  ├─ trading_system/ (code)
  ├─ trading_system.db (data)
  ├─ trading.log (logs)
  ├─ backups/ (daily DB backups)
  └─ models/ (trained models)
```

### Recommended Setup
- Ubuntu 20.04+ or similar Linux
- Python 3.8+
- systemd service (auto-restart)
- cron jobs for daily backups
- Monitoring (uptime checks)

---

This architecture is designed for:
✅ **Modularity** - Swap components easily
✅ **Safety** - Multiple layers of protection
✅ **Testability** - Paper trading included
✅ **Observability** - Comprehensive logging
✅ **Scalability** - Clear path to grow
