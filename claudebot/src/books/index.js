/**
 * Bookmaker registry and odds simulation
 */

const BOOKMAKERS = [
  'BetMGM', 'DraftKings', 'FanDuel', 'Unibet', 'Pinnacle',
  'Betfair', 'BetUS', '1xBet', 'William Hill', 'PokerStars',
  'Bovada', 'Million Hit', 'BetMCM', 'Pointsbet', 'Caesars',
  'BetRivers', 'SuperDraft', 'Bet365',
];

/**
 * Force-generate an arb opportunity with a specific target aodds
 * Works backwards from the desired margin to produce valid odds
 */
function forceArbOdds(numBooks, targetAodds = null) {
  const aodds = targetAodds || (Math.random() * 0.35 + 0.03); // 0.03 to 0.38
  const shuffled = [...BOOKMAKERS].sort(() => Math.random() - 0.5);
  const selected = shuffled.slice(0, Math.min(numBooks, BOOKMAKERS.length));

  // 1/o1 + 1/o2 = 1 - aodds
  const impliedSum = 1 - aodds;

  // Split the implied sum between two sides with realistic variance
  const split = 0.3 + Math.random() * 0.4; // 30-70% split
  const p1 = impliedSum * split;
  const p2 = impliedSum * (1 - split);

  // Clamp to prevent extreme odds
  const clampedP1 = Math.max(0.15, Math.min(0.85, p1));
  const clampedP2 = Math.max(0.15, Math.min(0.85, p2));

  const o1 = parseFloat((1 / clampedP1).toFixed(2));
  const o2 = parseFloat((1 / clampedP2).toFixed(2));

  // Recalculate actual aodds from rounded odds
  const actualAodds = 1 - (1 / o1 + 1 / o2);

  return {
    bookA: selected[0],
    bookB: selected[1] || selected[0],
    oddsA: o1,
    oddsB: o2,
    aodds: parseFloat(Math.max(actualAodds, 0.001).toFixed(3)),
    allBooks: selected,
  };
}

module.exports = {
  BOOKMAKERS,
  forceArbOdds,
};
