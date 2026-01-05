# Strategy Configuration Quick Reference

## Configuration Options

### Arbitrage Detection
- **Minimum Edge (%)** - Only trade opportunities with at least this percentage edge
  - Default: 0.5%
  - Conservative: 2.0%
  - Balanced: 1.0%
  - Aggressive: 0.5%

### Position Sizing
- **Max Stake Per Trade ($)** - Largest single bet allowed
  - Default: $50
  - Conservative: $25
  - Balanced: $50
  - Aggressive: $100

- **Max Exposure Per Market ($)** - Total risk per event
  - Default: $100
  - Conservative: $50
  - Balanced: $100
  - Aggressive: $250

### Risk Limits
- **Daily Loss Limit ($)** - Stop trading if losses exceed this
  - Default: $500
  - Conservative: $200
  - Balanced: $500
  - Aggressive: $1000

- **DraftKings Exposure Limit ($)** - Maximum allocation to DraftKings
  - Default: $250

## Preset Configurations

### 🛡️ Conservative
Best for: Risk-averse traders, learning phase, small bankroll
- Requires higher edge (2.0%) before trading
- Smaller position sizes ($25 max)
- Lower daily loss limit ($200)
- Safer market exposure ($50)

### ⚖️ Balanced (Recommended)
Best for: Most traders, steady growth, moderate risk
- Balanced edge requirement (1.0%)
- Moderate position sizes ($50 max)
- Reasonable daily limit ($500)
- Decent market exposure ($100)

### ⚡ Aggressive
Best for: Experienced traders, large bankroll, maximum volume
- Lower edge requirement (0.5%)
- Larger position sizes ($100 max)
- Higher daily limit ($1000)
- Higher market exposure ($250)

## How to Use

1. **Select a preset** - Click the preset button that matches your risk tolerance
   - Preset button will highlight blue when selected
2. **Fine-tune settings** - Adjust any specific parameters as needed
3. **Click Save** - Configuration changes take effect immediately
4. **Monitor results** - Check trade history for performance

## Tips

- Start conservative and increase position size as you gain confidence
- Adjust min_edge based on market conditions
  - Lower edge in efficient markets = fewer trades
  - Higher edge in volatile markets = more selective trades
- Use daily loss limit as your risk guardrail
- Test settings in paper mode before going live

## Safety Notes

⚠️ **Live Mode Warning**: Configuration changes in live mode affect real trades immediately

✓ **Paper Mode**: Practice with virtual balance first - no financial risk

## Example Scenarios

### New to Trading?
→ Use **Conservative** preset
→ Keep daily loss limit to $200
→ Start with $50-100 per trade

### Growing Account?
→ Use **Balanced** preset
→ Increase stake as account grows
→ Monitor win rate and adjust edge requirements

### Scaling Up?
→ Use **Aggressive** preset
→ Optimize for volume and consistency
→ Focus on fee minimization
