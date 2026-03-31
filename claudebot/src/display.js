/**
 * Terminal rendering engine
 * Pinned header bar + scrolling feed
 */

const chalk = require('chalk');

const HEADER_LINES = 5; // Lines reserved for the header

/**
 * Format a dollar amount with commas
 */
function formatMoney(amount) {
  const abs = Math.abs(amount);
  const formatted = abs.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return amount < 0 ? `-$${formatted}` : `$${formatted}`;
}

/**
 * Render the persistent header bar
 * Moves cursor to top and overwrites in place
 */
function renderHeader(state, mode, isDemo) {
  const pnl = state.pnl;
  const pnlStr = pnl >= 0
    ? chalk.green(`(+${formatMoney(pnl)})`)
    : chalk.red(`(${formatMoney(pnl)})`);

  const balanceStr = chalk.bold.white(formatMoney(state.balance));
  const tradesStr = chalk.white(`TRADES: ${state.trades}`);
  const winStr = chalk.white(`WIN: ${state.winRate.toFixed(0)}%`);

  const demoTag = isDemo ? chalk.bgYellow.black(' DEMO MODE ') + ' ' : '';
  const modeTag = chalk.dim(`[${mode.toUpperCase()}]`);

  // Move cursor to top-left
  process.stdout.write('\x1B[1;1H');
  // Clear header area
  for (let i = 0; i < HEADER_LINES; i++) {
    process.stdout.write('\x1B[2K\n');
  }
  process.stdout.write(`\x1B[1;1H`);

  // Line 1: Balance and stats
  const line1 = `  ${demoTag}${modeTag}  ${balanceStr}  ${pnlStr}  ${tradesStr}  ${winStr}`;
  process.stdout.write(line1 + '\n');

  // Line 2: Boot status tags
  const bootTags = [
    chalk.dim('[') + chalk.green('BOOT') + chalk.dim(']'),
    chalk.dim('[') + chalk.green('BOOT') + chalk.dim('] ') + chalk.green('OK'),
    chalk.dim('[') + chalk.green('BOOT') + chalk.dim('] ') + chalk.green('SYNCED'),
    chalk.dim('[') + chalk.green('BOOT') + chalk.dim('] ') + chalk.green('SYNCED'),
  ].join('  ');
  process.stdout.write(`  ${bootTags}\n`);

  // Line 3: Separator
  process.stdout.write(chalk.dim('  ' + '─'.repeat(76)) + '\n');

  // Line 4: empty line for spacing
  process.stdout.write('\n');
}

/**
 * Print ARB DETECTED line
 */
function printArbDetected(opp) {
  const league = chalk.white(opp.league);
  const matchup = chalk.white(`${opp.teamA} vs ${opp.teamB}`);
  const market = chalk.white(opp.market);
  const aodds = chalk.white(`Aodds [${opp.aodds.toFixed(3)}]`);

  const latency = opp.latencyMs
    ? chalk.dim(` (${opp.latencyMs}ms)`)
    : '';

  const line = chalk.green('+ ') +
    chalk.green.bold('ARB DETECTED') + chalk.white(': ') +
    `${league} ${chalk.dim('|')} ${matchup} ${chalk.dim('|')} ${market} ${chalk.dim('|')} ${aodds}${latency}`;

  process.stdout.write(line + '\n');
}

/**
 * Print BUY line (leg 1)
 */
function printBuyLine(trade) {
  const side = trade.teamA;
  const market = trade.market;
  const odds = trade.oddsA.toFixed(2);
  const book = trade.bookA;
  const stake = formatMoney(trade.stake1);

  const line = chalk.white('  BUY   ') +
    padRight(chalk.white(side), 20) +
    padRight(chalk.dim(market), 12) +
    chalk.white('@ ') + padRight(chalk.bold.white(odds), 8) +
    chalk.dim('via ') + padRight(chalk.white(book), 16) +
    chalk.dim('~') + chalk.white(stake);

  process.stdout.write(line + '\n');
}

/**
 * Print WEDGE line (leg 2)
 */
function printWedgeLine(trade) {
  const side = trade.teamB;
  const market = trade.market;
  const odds = trade.oddsB.toFixed(2);
  const book = trade.bookB;
  const stake = formatMoney(trade.stake2);

  const line = chalk.white('  WEDGE ') +
    padRight(chalk.white(side), 20) +
    padRight(chalk.dim(market), 12) +
    chalk.white('@ ') + padRight(chalk.bold.white(odds), 8) +
    chalk.dim('via ') + padRight(chalk.white(book), 16) +
    chalk.dim('~') + chalk.white(stake);

  process.stdout.write(line + '\n');
}

/**
 * Print SETTLED line
 */
function printSettled(pnl, newBalance) {
  const pnlStr = pnl >= 0
    ? chalk.green(`+${formatMoney(pnl)}`)
    : chalk.red(formatMoney(pnl));

  const checkmark = pnl >= 0
    ? chalk.green('\u2713')
    : chalk.red('\u2717');

  const line = `${checkmark} ` +
    chalk.bold(pnl >= 0 ? chalk.green('SETTLED') : chalk.red('SETTLED')) +
    ` [${pnlStr}]` +
    chalk.dim(' | bal: ') + chalk.white(formatMoney(newBalance));

  process.stdout.write(line + '\n');
}

/**
 * Print a blank separator between arb cycles
 */
function printSeparator() {
  process.stdout.write('\n');
}

/**
 * Pad a string to a fixed width (accounts for chalk invisible chars)
 */
function padRight(str, width) {
  const stripped = str.replace(/\x1B\[[0-9;]*m/g, '');
  const pad = Math.max(0, width - stripped.length);
  return str + ' '.repeat(pad);
}

/**
 * Initialize the terminal for the bot display
 */
function initDisplay() {
  // Clear screen, hide cursor
  process.stdout.write('\x1B[2J\x1B[H');
  process.stdout.write('\x1B[?25l'); // Hide cursor

  // Set up scroll region below header
  process.stdout.write(`\x1B[${HEADER_LINES + 1};999r`);
}

/**
 * Move cursor to feed area (below header)
 */
function moveCursorToFeed() {
  // Move to bottom of terminal so feed scrolls naturally
  process.stdout.write('\x1B[999;1H');
}

/**
 * Cleanup on exit
 */
function cleanupDisplay() {
  process.stdout.write('\x1B[?25h'); // Show cursor
  process.stdout.write('\x1B[r');     // Reset scroll region
  process.stdout.write('\n');
}

/**
 * Sleep utility
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

module.exports = {
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
  formatMoney,
  HEADER_LINES,
};
