# Enhanced Arbitrage Bot - Quick Reference

## 🚀 Quick Start

```bash
# 1. Set environment variables
export KALSHI_API_KEY="your_key_here"
export POLYMARKET_PRIVATE_KEY="your_eth_private_key"
export TRADING_MODE="paper"  # Start in paper mode!

# 2. Start the bot
./start.sh  # or start.bat on Windows

# 3. Access dashboard
open http://localhost:3000
```

---

## 🔍 Core Concepts

### Arbitrage Detection (Probability Summation Method)

```python
# Single-leg binary arbitrage:
if (prob_YES_kalshi + prob_NO_polymarket) < 1.0:
    # ARBITRAGE OPPORTUNITY!
    edge_pct = (1.0 / sum_probabilities - 1.0) * 100
```

**Example:**
- Kalshi: YES @ 45¢ (0.45 probability)
- Polymarket: NO @ 50¢ (0.50 probability)
- Sum: 0.95 < 1.0 ✓
- Edge: (1/0.95 - 1) × 100 = **5.26% guaranteed profit**

### Stake Allocation

```python
# Optimal stakes for equal payout:
stake_kalshi = (1/prob_kalshi) / sum(1/prob_i) × total_stake
stake_polymarket = (1/prob_poly) / sum(1/prob_i) × total_stake
```

**Example with $1000:**
- Stake YES: (1/0.45) / ((1/0.45)+(1/0.50)) × 1000 = **$526.32**
- Stake NO: (1/0.50) / ((1/0.45)+(1/0.50)) × 1000 = **$473.68**
- Payout either outcome: **~$1052.63** (5.26% profit)

---

## 🛡️ Risk Controls

### 6-Layer Protection System

```python
# 1. Stake limit per leg
if stake > max_stake_per_leg:
    reject("Exceeds per-leg limit")

# 2. Event exposure limit
if event_total_exposure + stake > max_exposure_per_event:
    reject("Exceeds event limit")

# 3. Provider exposure limit
if provider_total_exposure + stake > max_exposure_per_provider:
    reject("Exceeds provider limit")

# 4. Total portfolio exposure
if total_exposure + stake > max_total_exposure:
    reject("Exceeds portfolio limit")

# 5. Daily loss limit
if daily_loss + potential_loss > daily_loss_limit:
    reject("Approaching daily loss limit")

# 6. Kill switch
if kill_switch_active:
    reject("Kill switch active - trading halted")
```

### Default Limits

| Limit Type | Default Value |
|------------|---------------|
| Max stake per leg | $100 |
| Max exposure per event | $500 |
| Max exposure per provider | $2,000 |
| Max total exposure | $5,000 |
| Daily loss limit | $1,000 |
| Max loss per trade | $500 |

---

## 📊 Code Examples

### Detect Arbitrage

```python
from arbitragebot.arbitrage.detector import detect_arbitrage_opportunities

# Get markets
kalshi_markets = kalshi_source.fetch_markets()
polymarket_markets = polymarket_source.fetch_markets()

# Detect opportunities
opportunities = detect_arbitrage_opportunities(
    kalshi_markets=kalshi_markets,
    polymarket_markets=polymarket_markets,
    min_edge_pct=2.0  # Only show edges >= 2%
)

for opp in opportunities:
    print(f"Event: {opp.event_name}")
    print(f"Edge: {opp.edge_pct:.2f}%")
    print(f"Kalshi: {opp.sides['kalshi']} @ ${opp.prices['kalshi']:.2f} (stake ${opp.stakes['kalshi']:.2f})")
    print(f"Polymarket: {opp.sides['polymarket']} @ ${opp.prices['polymarket']:.2f} (stake ${opp.stakes['polymarket']:.2f})")
    print(f"Expected profit: ${opp.expected_profit:.2f}")
    print(f"Risk level: {opp.risk_level}")
    print()
```

### Execute with Risk Management

```python
from arbitragebot.risk_management import RiskManager, RiskLimits

# Configure limits
limits = RiskLimits(
    max_stake_per_leg=100.0,
    max_exposure_per_event=500.0,
    daily_loss_limit=1000.0
)
risk_manager = RiskManager(limits=limits)

# Check if trade is allowed
for opp in opportunities:
    # Validate Kalshi leg
    can_execute_k, reason_k = risk_manager.can_execute_trade(
        event_id=opp.event_id,
        provider="kalshi",
        stake=opp.stakes["kalshi"]
    )
    
    # Validate Polymarket leg
    can_execute_p, reason_p = risk_manager.can_execute_trade(
        event_id=opp.event_id,
        provider="polymarket",
        stake=opp.stakes["polymarket"]
    )
    
    if can_execute_k and can_execute_p:
        # Execute trades
        pos_k = risk_manager.record_position(
            event_id=opp.event_id,
            provider="kalshi",
            side=opp.sides["kalshi"],
            stake=opp.stakes["kalshi"],
            price=opp.prices["kalshi"]
        )
        
        pos_p = risk_manager.record_position(
            event_id=opp.event_id,
            provider="polymarket",
            side=opp.sides["polymarket"],
            stake=opp.stakes["polymarket"],
            price=opp.prices["polymarket"]
        )
        
        # Place orders with exchanges...
        print(f"✅ Executed: {opp.event_name} - Edge {opp.edge_pct:.2f}%")
    else:
        print(f"❌ Rejected: {reason_k or reason_p}")
```

### Settle Positions

```python
# When market resolves
outcome = "YES"  # or "NO"

# Settle Kalshi position
pnl_kalshi = risk_manager.settle_position(
    position_id=pos_k,
    outcome=outcome,
    settlement_price=1.0 if outcome == opp.sides["kalshi"] else 0.0
)

# Settle Polymarket position
pnl_poly = risk_manager.settle_position(
    position_id=pos_p,
    outcome=outcome,
    settlement_price=1.0 if outcome == opp.sides["polymarket"] else 0.0
)

total_pnl = pnl_kalshi + pnl_poly
print(f"Total P&L: ${total_pnl:.2f}")
```

### Emergency Controls

```python
# Manual kill switch
risk_manager.activate_kill_switch("Market volatility - manual halt")

# Check status
if risk_manager.kill_switch_active:
    print(f"⚠️ Trading halted: {risk_manager.kill_switch_reason}")

# Resume trading
risk_manager.deactivate_kill_switch()

# Get position summary
summary = risk_manager.get_position_summary()
print(f"Total positions: {summary['total_positions']}")
print(f"Total exposure: ${summary['total_exposure']:.2f}")
print(f"Daily P&L: ${risk_manager.daily_pnl:.2f}")
```

---

## 🧪 Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Test Specific Modules
```bash
# Arbitrage detector
pytest tests/test_arbitrage_detector.py -v

# Risk management
pytest tests/test_risk_management.py -v
```

### Manual Testing
```python
# Test with mock data
from arbitragebot.schemas import NormalizedOdds
from datetime import datetime, timedelta

kalshi = NormalizedOdds(
    sport="basketball",
    league="nba",
    event_id="test-001",
    event_name="Will Lakers win?",
    start_time=datetime.utcnow() + timedelta(hours=24),
    home_team="Lakers",
    away_team="Celtics",
    market_type="binary",
    selection="YES",
    price=0.45,
    implied_probability=0.45,
    source="kalshi",
    last_updated=datetime.utcnow()
)

polymarket = NormalizedOdds(
    sport="basketball",
    league="nba",
    event_id="test-001",
    event_name="Will Lakers win?",
    start_time=datetime.utcnow() + timedelta(hours=24),
    home_team="Lakers",
    away_team="Celtics",
    market_type="binary",
    selection="NO",
    price=0.50,
    implied_probability=0.50,
    source="polymarket",
    last_updated=datetime.utcnow()
)

opps = detect_arbitrage_opportunities([kalshi], [polymarket])
print(opps[0] if opps else "No arbitrage found")
```

---

## 🐛 Troubleshooting

### No opportunities detected
```python
# Check 1: Verify markets are being fetched
print(f"Kalshi markets: {len(kalshi_markets)}")
print(f"Polymarket markets: {len(polymarket_markets)}")

# Check 2: Verify probabilities
for market in kalshi_markets[:5]:
    print(f"{market.event_name}: {market.price}")

# Check 3: Lower threshold
detector = ArbitrageDetector(min_edge_pct=0.1)  # Very low threshold

# Check 4: Check canonical matching
# See ENHANCED_ARBITRAGE_COMPLETE.md for 5-layer matching details
```

### Risk manager rejecting all trades
```python
# Check 1: Verify limits aren't too restrictive
print(risk_manager.limits)

# Check 2: Check current exposure
summary = risk_manager.get_position_summary()
print(summary)

# Check 3: Check kill switch
if risk_manager.kill_switch_active:
    print(f"Kill switch active: {risk_manager.kill_switch_reason}")
    risk_manager.deactivate_kill_switch()

# Check 4: Reset daily P&L if testing
risk_manager.reset_daily_pnl()
```

### API errors
```bash
# Kalshi
curl -H "Authorization: Bearer $KALSHI_API_KEY" https://api.kalshi.com/v1/markets

# Check rate limits (60 req/min)
# Add caching to reduce calls

# Polymarket - check Web3 auth
python -c "from web3 import Web3; print(Web3().eth.account.from_key('$POLYMARKET_PRIVATE_KEY').address)"
```

---

## 📁 File Structure

```
src/arbitragebot/
├── arbitrage/
│   ├── detector.py          # ✨ NEW: Enhanced arbitrage detection
│   ├── calculator.py         # Legacy arbitrage math
│   └── __init__.py
├── risk_management.py        # ✨ NEW: Risk controls
├── data_sources/
│   ├── kalshi.py
│   └── polymarket.py         # ✅ Updated: Web3 auth
├── normalization/
│   ├── normalizers.py        # ✅ Updated: Added PolymarketNormalizer
│   └── schemas.py            # ✅ Updated: PROVIDER_POLYMARKET
├── main.py                   # ✅ Updated: Kalshi + Polymarket only
└── opportunity_helpers.py    # ✅ Updated: Removed Fanatics

tests/
├── test_arbitrage_detector.py      # ✨ NEW: 15 tests
└── test_risk_management.py         # ✨ NEW: 25 tests
```

---

## 🔗 Related Documentation

- **Full Implementation**: `ENHANCED_ARBITRAGE_COMPLETE.md`
- **Polymarket Integration**: `POLYMARKET_REVAMP_COMPLETE.md`
- **5-Layer Matching**: `5LAYER_README.md`
- **Data Flow**: `DATA_FLOW_ARCHITECTURE.md`
- **Getting Started**: `START_HERE.md`

---

## ⚙️ Configuration

### Environment Variables
```bash
# Required
KALSHI_API_KEY=your_kalshi_api_key
POLYMARKET_PRIVATE_KEY=0x...  # Ethereum private key

# Optional
TRADING_MODE=paper             # or "live"
MIN_EDGE_PCT=2.0              # Minimum profit %
MAX_STAKE=100.0               # Max $ per leg
BANKROLL=10000.0              # Total $ for allocation
REFRESH_INTERVAL=30           # Seconds between API calls
```

### config/strategy.yaml
```yaml
strategy:
  min_edge_pct: 2.0
  max_stake: 100.0
  max_exposure_per_market: 500.0
  per_day_loss_limit: 1000.0

trading:
  mode: paper
  max_order_size: 100.0
  
risk:
  max_stake_per_leg: 100.0
  max_exposure_per_event: 500.0
  max_exposure_per_provider: 2000.0
  max_total_exposure: 5000.0
  max_loss_per_trade: 500.0
```

---

## 📞 Support

**Issues?** Check:
1. `ENHANCED_ARBITRAGE_COMPLETE.md` - Full implementation details
2. Test files - See working examples
3. GitHub Issues - Report bugs

**Version:** 2.0.0  
**Last Updated:** 2025  
**Status:** Production Ready ✅
