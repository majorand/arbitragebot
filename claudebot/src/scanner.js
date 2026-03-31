/**
 * Odds ingestion and arbitrage detection logic
 */

const { forceArbOdds } = require('./books');
const { getRandomMatchup } = require('./sports');

/**
 * Scan for an arbitrage opportunity across given sports
 * In demo mode, force-generates realistic arb opportunities
 */
function scanForArb(sportKeys, numBooks, threshold, mode) {
  const sportKey = sportKeys[Math.floor(Math.random() * sportKeys.length)];
  const matchup = getRandomMatchup(sportKey);
  if (!matchup) return null;

  // ~82% of arbs settle profitably, ~18% hit slippage
  const isWin = Math.random() < 0.82;

  if (isWin) {
    // Generate arb with margin above threshold
    const targetAodds = threshold + Math.random() * 0.35; // threshold to threshold+0.35
    const arb = forceArbOdds(numBooks, targetAodds);

    return {
      ...matchup,
      bookA: arb.bookA,
      bookB: arb.bookB,
      oddsA: arb.oddsA,
      oddsB: arb.oddsB,
      aodds: Math.max(arb.aodds, threshold),
      mode,
      latencyMs: mode === 'latency_arb' ? Math.floor(Math.random() * 180 + 20) : null,
    };
  }

  // Slippage scenario: arb looked good but execution ate the margin
  const arb = forceArbOdds(numBooks, Math.random() * 0.015 + 0.005);
  return {
    ...matchup,
    bookA: arb.bookA,
    bookB: arb.bookB,
    oddsA: arb.oddsA,
    oddsB: arb.oddsB,
    aodds: arb.aodds,
    mode,
    slippage: true,
    latencyMs: mode === 'latency_arb' ? Math.floor(Math.random() * 180 + 20) : null,
  };
}

module.exports = { scanForArb };
