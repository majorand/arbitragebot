#!/usr/bin/env node

/**
 * ClaudeBot — Real-time sports arbitrage scanner and auto-executor
 * CLI entry point
 */

const { Command } = require('commander');
const { SessionState } = require('./state');
const { scanForArb } = require('./scanner');
const { executeTrade } = require('./executor');
const { settleTrade } = require('./settler');
const { parseSportsFlag } = require('./sports');
const {
  renderHeader,
  printArbDetected,
  printBuyLine,
  printWedgeLine,
  printSettled,
  printSeparator,
  initDisplay,
  moveCursorToFeed,
  cleanupDisplay,
  sleep,
} = require('./display');

const program = new Command();

program
  .name('claudebot')
  .description('Real-time sports arbitrage scanner and auto-executor')
  .version('1.0.0');

program
  .command('scan')
  .description('Start scanning for arbitrage opportunities')
  .option('--mode <mode>', 'Scan mode: latency_arb, standard_arb, midpoint_arb', 'standard_arb')
  .option('--sports <sports>', 'Sports to scan: all, nfl, nba, mlb, nhl, epl, la_liga, ufc, tennis (comma-separated)', 'all')
  .option('--books <N>', 'Number of bookmakers to scan', parseInt, 18)
  .option('--threshold <decimal>', 'Minimum arbitrage margin to execute', parseFloat, 0.03)
  .action(async (opts) => {
    const validModes = ['latency_arb', 'standard_arb', 'midpoint_arb'];
    if (!validModes.includes(opts.mode)) {
      console.error(`Invalid mode: ${opts.mode}. Use: ${validModes.join(', ')}`);
      process.exit(1);
    }

    const sportKeys = parseSportsFlag(opts.sports);
    if (sportKeys.length === 0) {
      console.error('No valid sports specified.');
      process.exit(1);
    }

    await runScanner({
      mode: opts.mode,
      sportKeys,
      numBooks: opts.books,
      threshold: opts.threshold,
    });
  });

program.parse(process.argv);

// If no command given, show help
if (!process.argv.slice(2).length) {
  program.outputHelp();
}

/**
 * Main scanner loop
 */
async function runScanner({ mode, sportKeys, numBooks, threshold }) {
  const state = new SessionState(1204.50);
  const isDemo = true; // No live API keys in this version

  // Initialize terminal
  initDisplay();

  // Handle graceful shutdown
  const shutdown = () => {
    cleanupDisplay();
    console.log('\n  ClaudeBot stopped. Session summary:');
    console.log(`  Trades: ${state.trades} | Wins: ${state.wins} | Losses: ${state.losses}`);
    console.log(`  P&L: ${state.pnl >= 0 ? '+' : ''}$${state.pnl.toFixed(2)} | Final Balance: $${state.balance.toFixed(2)}\n`);
    process.exit(0);
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);

  // Render initial header
  renderHeader(state, mode, isDemo);
  moveCursorToFeed();

  // Main loop
  while (true) {
    // Random delay between cycles (1-3 arbs per second)
    const cycleDelay = Math.floor(Math.random() * 700 + 300); // 300-1000ms between cycles

    // Scan for arb
    const opportunity = scanForArb(sportKeys, numBooks, threshold, mode);
    if (!opportunity) {
      await sleep(200);
      continue;
    }

    // Execute trade
    const trade = executeTrade(opportunity, state.balance);

    // Print ARB DETECTED
    moveCursorToFeed();
    printArbDetected(opportunity);
    renderHeader(state, mode, isDemo);

    // Delay before BUY line
    await sleep(Math.floor(Math.random() * 100 + 50));

    // Print BUY line
    moveCursorToFeed();
    printBuyLine(trade);
    renderHeader(state, mode, isDemo);

    // Delay before WEDGE line
    await sleep(Math.floor(Math.random() * 100 + 50));

    // Print WEDGE line
    moveCursorToFeed();
    printWedgeLine(trade);
    renderHeader(state, mode, isDemo);

    // Delay before settlement (150-400ms)
    await sleep(Math.floor(Math.random() * 250 + 150));

    // Settle trade
    const settled = settleTrade(trade);
    state.recordTrade(settled.actualPnl);

    // Print SETTLED line
    moveCursorToFeed();
    printSettled(settled.actualPnl, state.balance);
    renderHeader(state, mode, isDemo);

    // Blank line separator
    moveCursorToFeed();
    printSeparator();

    // Wait before next cycle
    await sleep(cycleDelay);
  }
}
