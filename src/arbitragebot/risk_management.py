"""
Risk Management and Control System for Arbitrage Trading.

Implements comprehensive risk controls including:
- Stake limits per trade and per provider
- Exposure tracking across open positions  
- Kill switch for emergency trading halt
- Real-time P&L monitoring
- Position size validation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

LOGGER = logging.getLogger(__name__)


@dataclass
class RiskLimits:
    """Configuration for risk management limits."""
    
    # Stake limits
    max_stake_per_trade: float = 500.0  # Max total stake per arbitrage
    max_stake_per_leg: float = 250.0  # Max stake on one side
    
    # Provider limits
    max_stake_kalshi: float = 250.0
    max_stake_polymarket: float = 250.0
    
    # Exposure limits
    max_exposure_per_event: float = 1000.0  # Max total on one event
    max_total_exposure: float = 5000.0  # Max across all open positions
    
    # Daily limits
    max_trades_per_day: int = 50
    max_daily_loss: float = 1000.0
    
    # Minimum thresholds
    min_edge_pct: float = 0.5  # Minimum profit margin
    fee_buffer: float = 0.005  # Buffer for fees (0.5%)
    
    def validate(self) -> bool:
        """Validate that limits are sensible."""
        if self.max_stake_per_trade <= 0:
            LOGGER.error("max_stake_per_trade must be positive")
            return False
        if self.max_stake_per_leg > self.max_stake_per_trade:
            LOGGER.error("max_stake_per_leg cannot exceed max_stake_per_trade")
            return False
        return True


@dataclass
class OpenPosition:
    """Represents an open arbitrage position."""
    
    position_id: str
    event_id: str
    event_name: str
    
    # Legs
    yes_provider: str
    yes_stake: float
    yes_price: float
    
    no_provider: str
    no_stake: float
    no_price: float
    
    # Metrics
    total_stake: float
    expected_profit: float
    edge_pct: float
    
    # Status
    opened_at: datetime
    status: str = "open"  # "open", "settled", "canceled"
    
    @property
    def exposure(self) -> float:
        """Total amount at risk (should be ~0 for true arbitrage)."""
        return self.total_stake


@dataclass
class TradeRecord:
    """Record of an executed trade for P&L tracking."""
    
    trade_id: str
    event_id: str
    event_name: str
    
    timestamp: datetime
    mode: str  # "paper" or "live"
    
    # Trade details
    yes_provider: str
    yes_stake: float
    yes_price: float
    yes_filled: bool
    
    no_provider: str
    no_stake: float
    no_price: float
    no_filled: bool
    
    # Outcomes
    expected_profit: float
    actual_profit: Optional[float] = None
    result: Optional[str] = None  # "settled", "canceled", "partial"
    
    notes: str = ""


class RiskManager:
    """
    Centralized risk management and control system.
    
    Responsibilities:
    - Validate trades against risk limits
    - Track open positions and exposure
    - Enforce kill switch
    - Monitor P&L
    - Prevent over-trading
    """
    
    def __init__(self, limits: Optional[RiskLimits] = None):
        """Initialize risk manager with limits."""
        self.limits = limits or RiskLimits()
        
        if not self.limits.validate():
            raise ValueError("Invalid risk limits configuration")
        
        # State tracking
        self.open_positions: Dict[str, OpenPosition] = {}
        self.trade_history: List[TradeRecord] = []
        self.daily_trades_count = 0
        self.daily_pnl = 0.0
        self.kill_switch_active = False
        
        # Statistics
        self.total_trades = 0
        self.total_profit = 0.0
        self.trades_by_provider: Dict[str, int] = {}
        
        LOGGER.info(
            f"RiskManager initialized with limits: "
            f"max_stake_per_trade=${self.limits.max_stake_per_trade}, "
            f"max_total_exposure=${self.limits.max_total_exposure}"
        )
    
    def can_execute_trade(
        self,
        event_id: str,
        total_stake: float,
        yes_stake: float,
        no_stake: float,
        yes_provider: str,
        no_provider: str,
        edge_pct: float,
    ) -> Tuple[bool, str]:
        """
        Check if a trade can be executed under current risk limits.
        
        Returns:
            (can_execute, reason) - True if trade is allowed, False with reason if not
        """
        # Check kill switch first
        if self.kill_switch_active:
            return False, "Kill switch is active - trading halted"
        
        # Check minimum edge
        if edge_pct < self.limits.min_edge_pct:
            return False, f"Edge {edge_pct:.2f}% below minimum {self.limits.min_edge_pct}%"
        
        # Check stake limits
        if total_stake > self.limits.max_stake_per_trade:
            return False, f"Total stake ${total_stake:.2f} exceeds limit ${self.limits.max_stake_per_trade:.2f}"
        
        if yes_stake > self.limits.max_stake_per_leg or no_stake > self.limits.max_stake_per_leg:
            return False, f"Individual leg stake exceeds limit ${self.limits.max_stake_per_leg:.2f}"
        
        # Check provider limits
        if yes_provider == "kalshi" and yes_stake > self.limits.max_stake_kalshi:
            return False, f"Kalshi stake ${yes_stake:.2f} exceeds limit ${self.limits.max_stake_kalshi:.2f}"
        if no_provider == "kalshi" and no_stake > self.limits.max_stake_kalshi:
            return False, f"Kalshi stake ${no_stake:.2f} exceeds limit ${self.limits.max_stake_kalshi:.2f}"
        
        if yes_provider == "polymarket" and yes_stake > self.limits.max_stake_polymarket:
            return False, f"Polymarket stake ${yes_stake:.2f} exceeds limit ${self.limits.max_stake_polymarket:.2f}"
        if no_provider == "polymarket" and no_stake > self.limits.max_stake_polymarket:
            return False, f"Polymarket stake ${no_stake:.2f} exceeds limit ${self.limits.max_stake_polymarket:.2f}"
        
        # Check event exposure
        event_exposure = self.get_event_exposure(event_id)
        if event_exposure + total_stake > self.limits.max_exposure_per_event:
            return False, (
                f"Event exposure ${event_exposure + total_stake:.2f} would exceed "
                f"limit ${self.limits.max_exposure_per_event:.2f}"
            )
        
        # Check total exposure
        total_exposure = self.get_total_exposure()
        if total_exposure + total_stake > self.limits.max_total_exposure:
            return False, (
                f"Total exposure ${total_exposure + total_stake:.2f} would exceed "
                f"limit ${self.limits.max_total_exposure:.2f}"
            )
        
        # Check daily limits
        if self.daily_trades_count >= self.limits.max_trades_per_day:
            return False, f"Daily trade limit reached ({self.limits.max_trades_per_day})"
        
        if self.daily_pnl < -self.limits.max_daily_loss:
            return False, (
                f"Daily loss limit reached (${abs(self.daily_pnl):.2f} / "
                f"${self.limits.max_daily_loss:.2f})"
            )
        
        # All checks passed
        return True, "Trade approved"
    
    def record_position(self, position: OpenPosition) -> None:
        """Record a new open position."""
        self.open_positions[position.position_id] = position
        self.daily_trades_count += 1
        self.total_trades += 1
        
        # Track by provider
        self.trades_by_provider[position.yes_provider] = (
            self.trades_by_provider.get(position.yes_provider, 0) + 1
        )
        self.trades_by_provider[position.no_provider] = (
            self.trades_by_provider.get(position.no_provider, 0) + 1
        )
        
        LOGGER.info(
            f"Recorded position {position.position_id}: "
            f"{position.event_name}, stake=${position.total_stake:.2f}, "
            f"expected_profit=${position.expected_profit:.2f}"
        )
    
    def settle_position(
        self,
        position_id: str,
        actual_profit: float,
        result: str = "settled",
    ) -> None:
        """Mark a position as settled and update P&L."""
        if position_id not in self.open_positions:
            LOGGER.warning(f"Attempted to settle unknown position {position_id}")
            return
        
        position = self.open_positions[position_id]
        position.status = result
        
        # Update P&L
        self.daily_pnl += actual_profit
        self.total_profit += actual_profit
        
        # Remove from open positions
        del self.open_positions[position_id]
        
        LOGGER.info(
            f"Settled position {position_id}: "
            f"expected=${position.expected_profit:.2f}, "
            f"actual=${actual_profit:.2f}, "
            f"result={result}"
        )
    
    def get_event_exposure(self, event_id: str) -> float:
        """Get total exposure on a specific event."""
        return sum(
            pos.total_stake
            for pos in self.open_positions.values()
            if pos.event_id == event_id
        )
    
    def get_total_exposure(self) -> float:
        """Get total exposure across all open positions."""
        return sum(pos.total_stake for pos in self.open_positions.values())
    
    def get_open_positions_count(self) -> int:
        """Get number of open positions."""
        return len(self.open_positions)
    
    def activate_kill_switch(self, reason: str = "") -> None:
        """Activate kill switch to halt all trading."""
        self.kill_switch_active = True
        LOGGER.critical(f"KILL SWITCH ACTIVATED: {reason}")
    
    def deactivate_kill_switch(self) -> None:
        """Deactivate kill switch to resume trading."""
        self.kill_switch_active = False
        LOGGER.info("Kill switch deactivated - trading resumed")
    
    def reset_daily_counters(self) -> None:
        """Reset daily counters (call at start of new trading day)."""
        self.daily_trades_count = 0
        self.daily_pnl = 0.0
        LOGGER.info("Daily counters reset")
    
    def get_statistics(self) -> Dict:
        """Get current risk and performance statistics."""
        return {
            "kill_switch_active": self.kill_switch_active,
            "open_positions": self.get_open_positions_count(),
            "total_exposure": self.get_total_exposure(),
            "daily_trades": self.daily_trades_count,
            "daily_pnl": self.daily_pnl,
            "total_trades": self.total_trades,
            "total_profit": self.total_profit,
            "trades_by_provider": self.trades_by_provider.copy(),
            "limits": {
                "max_stake_per_trade": self.limits.max_stake_per_trade,
                "max_total_exposure": self.limits.max_total_exposure,
                "max_trades_per_day": self.limits.max_trades_per_day,
            },
        }
    
    def validate_partial_fill(
        self,
        position_id: str,
        filled_amount: float,
        total_requested: float,
    ) -> bool:
        """
        Handle partial fill scenario.
        
        If only one leg is partially filled, we may have unhedged exposure.
        This function determines if we should proceed or cancel.
        
        Returns:
            True if partial fill is acceptable, False if should cancel
        """
        fill_percentage = filled_amount / total_requested if total_requested > 0 else 0
        
        # If filled >90%, consider it acceptable
        if fill_percentage >= 0.9:
            return True
        
        # If filled <50%, probably should cancel
        if fill_percentage < 0.5:
            LOGGER.warning(
                f"Position {position_id}: Low fill rate {fill_percentage:.1%}, "
                "recommend cancellation"
            )
            return False
        
        # Middle ground - log and allow (but with caution)
        LOGGER.warning(
            f"Position {position_id}: Partial fill {fill_percentage:.1%}, "
            "proceeding with reduced size"
        )
        return True


# Global risk manager instance (can be initialized in main)
_global_risk_manager: Optional[RiskManager] = None


def get_risk_manager() -> RiskManager:
    """Get the global risk manager instance."""
    global _global_risk_manager
    if _global_risk_manager is None:
        _global_risk_manager = RiskManager()
    return _global_risk_manager


def set_risk_manager(manager: RiskManager) -> None:
    """Set the global risk manager instance."""
    global _global_risk_manager
    _global_risk_manager = manager
