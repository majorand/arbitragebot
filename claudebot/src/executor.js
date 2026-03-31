/**
 * Stake calculation and trade placement
 */

/**
 * Calculate optimal stakes for a two-outcome arb
 * Guarantees equal profit on both outcomes
 *
 * @param {number} bankroll - Total amount to wager across both legs
 * @param {number} o1 - Decimal odds for leg 1 (BUY)
 * @param {number} o2 - Decimal odds for leg 2 (WEDGE)
 * @returns {{ stake1, stake2, guaranteedProfit, roi }}
 */
function calculateStakes(bankroll, o1, o2) {
  // Standard arb formula:
  // stake1 = bankroll / (1 + o1/o2)
  // stake2 = bankroll - stake1
  // Both outcomes yield the same return
  const stake1 = bankroll / (1 + o1 / o2);
  const stake2 = bankroll - stake1;

  // Guaranteed profit = (stake1 * o1) - bankroll
  const return1 = stake1 * o1;
  const return2 = stake2 * o2;
  const guaranteedProfit = Math.min(return1, return2) - bankroll;

  const roi = (guaranteedProfit / bankroll) * 100;

  return {
    stake1: parseFloat(stake1.toFixed(2)),
    stake2: parseFloat(stake2.toFixed(2)),
    guaranteedProfit: parseFloat(guaranteedProfit.toFixed(2)),
    roi: parseFloat(roi.toFixed(2)),
  };
}

/**
 * Determine wager size based on balance and confidence
 * Conservative: 2-8% of balance per arb
 */
function calculateWagerSize(balance, aodds) {
  // Higher aodds = higher confidence = larger wager
  const basePct = 0.02 + (aodds * 0.15); // 2% to ~9% of balance
  const clamped = Math.min(basePct, 0.10); // Cap at 10%
  return parseFloat((balance * clamped).toFixed(2));
}

/**
 * Execute an arb trade (simulate placement)
 * Returns the trade object with stakes and expected P&L
 */
function executeTrade(opportunity, balance) {
  const wager = calculateWagerSize(balance, opportunity.aodds);
  const stakes = calculateStakes(wager, opportunity.oddsA, opportunity.oddsB);

  return {
    id: `ARB-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
    ...opportunity,
    wager,
    stake1: stakes.stake1,
    stake2: stakes.stake2,
    expectedProfit: stakes.guaranteedProfit,
    roi: stakes.roi,
    timestamp: Date.now(),
  };
}

module.exports = { calculateStakes, calculateWagerSize, executeTrade };
