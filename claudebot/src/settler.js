/**
 * Settlement monitoring and P&L resolution
 */

/**
 * Settle a trade - determine actual P&L
 * In demo mode, simulates realistic settlement:
 * - Most arbs settle at expected profit
 * - Some have slippage (reduced profit)
 * - Rare cases: one leg fails (small loss)
 */
function settleTrade(trade) {
  const { expectedProfit, slippage, wager } = trade;

  if (slippage) {
    // Slippage ate the arb - small loss
    const loss = -(wager * (Math.random() * 0.015 + 0.002)); // 0.2-1.7% loss
    return {
      ...trade,
      settled: true,
      actualPnl: parseFloat(loss.toFixed(2)),
      settlementType: 'slippage',
    };
  }

  // Normal settlement - profit with slight variance
  const variance = 1 + (Math.random() - 0.5) * 0.1; // +/- 5% of expected
  const actualPnl = parseFloat((expectedProfit * variance).toFixed(2));

  return {
    ...trade,
    settled: true,
    actualPnl: Math.max(actualPnl, 0.01), // Arbs should be profitable
    settlementType: 'clean',
  };
}

module.exports = { settleTrade };
