/**
 * Session state management for ClaudeBot
 * Tracks balance, P&L, trades, and open positions
 */

class SessionState {
  constructor(startingBalance = 1204.50) {
    this.balance = startingBalance;
    this.startingBalance = startingBalance;
    this.trades = 0;
    this.wins = 0;
    this.losses = 0;
    this.totalProfit = 0;
    this.openPositions = [];
    this.history = [];
  }

  get pnl() {
    return this.balance - this.startingBalance;
  }

  get winRate() {
    if (this.trades === 0) return 0;
    return (this.wins / this.trades) * 100;
  }

  recordTrade(pnl) {
    this.trades++;
    this.totalProfit += pnl;
    this.balance += pnl;

    if (pnl >= 0) {
      this.wins++;
    } else {
      this.losses++;
    }

    this.history.push({
      trade: this.trades,
      pnl,
      balance: this.balance,
      timestamp: Date.now(),
    });
  }

  addOpenPosition(position) {
    this.openPositions.push(position);
  }

  closePosition(id) {
    this.openPositions = this.openPositions.filter(p => p.id !== id);
  }
}

module.exports = { SessionState };
