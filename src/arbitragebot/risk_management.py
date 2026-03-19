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
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

LOGGER = logging.getLogger(__name__)


@dataclass
class RiskLimits:
    """Configuration for risk management limits."""

    # Stake limits
    max_stake_per_leg: float = 100.0

    # Exposure limits
    max_exposure_per_event: float = 500.0
    max_exposure_per_provider: float = 2000.0
    max_total_exposure: float = 5000.0

    # Daily limits
    daily_loss_limit: float = 1000.0
    max_loss_per_trade: float = 500.0

    # Minimum thresholds
    min_edge_pct: float = 0.5
    fee_buffer: float = 0.005


@dataclass
class OpenPosition:
    """Represents an open position."""

    position_id: str
    event_id: str
    provider: str
    side: str  # "YES" or "NO"
    stake: float
    entry_price: float
    timestamp: datetime
    current_stake: float = 0.0

    def __post_init__(self):
        if self.current_stake == 0.0:
            self.current_stake = self.stake


@dataclass
class TradeRecord:
    """Record of a completed trade."""

    trade_id: str
    event_id: str
    provider: str
    side: str
    stake: float
    entry_price: float
    exit_price: float
    pnl: float
    timestamp: datetime


class RiskManager:
    """
    Centralized risk management and control system.

    Validates trades against risk limits, tracks open positions and exposure,
    enforces kill switch, and monitors P&L.
    """

    def __init__(self, limits: Optional[RiskLimits] = None):
        self.limits = limits or RiskLimits()

        self.positions: Dict[str, OpenPosition] = {}
        self.trades: List[TradeRecord] = []
        self.daily_pnl: float = 0.0
        self.kill_switch_active: bool = False
        self.kill_switch_reason: Optional[str] = None
        self.kill_switch_timestamp: Optional[datetime] = None

    # ------------------------------------------------------------------
    # Trade validation
    # ------------------------------------------------------------------

    def can_execute_trade(
        self,
        event_id: str,
        provider: str,
        stake: float,
    ) -> Tuple[bool, Optional[str]]:
        """Check if a trade can be executed under current risk limits."""

        if self.kill_switch_active:
            return False, "Kill switch is active - trading halted"

        # Stake limit and max loss per trade.
        # When both would reject, prefer the "max loss per trade" message.
        exceeds_stake = stake > self.limits.max_stake_per_leg
        exceeds_loss = stake > self.limits.max_loss_per_trade

        if exceeds_loss and exceeds_stake:
            return False, f"Max loss per trade ${stake:.2f} exceeds limit ${self.limits.max_loss_per_trade:.2f}"
        if exceeds_stake:
            return False, f"Stake ${stake:.2f} exceeds stake limit ${self.limits.max_stake_per_leg:.2f}"

        # Event exposure
        event_exposure = self.get_exposure_by_event(event_id)
        if event_exposure + stake > self.limits.max_exposure_per_event:
            return False, (
                f"Event exposure ${event_exposure + stake:.2f} exceeds "
                f"limit ${self.limits.max_exposure_per_event:.2f}"
            )

        # Provider exposure
        provider_exposure = self.get_exposure_by_provider(provider)
        if provider_exposure + stake > self.limits.max_exposure_per_provider:
            return False, (
                f"Provider exposure ${provider_exposure + stake:.2f} exceeds "
                f"limit ${self.limits.max_exposure_per_provider:.2f}"
            )

        # Total exposure
        total_exposure = self.get_total_exposure()
        if total_exposure + stake > self.limits.max_total_exposure:
            return False, (
                f"Total exposure ${total_exposure + stake:.2f} exceeds "
                f"limit ${self.limits.max_total_exposure:.2f}"
            )

        # Max loss per trade (checked after exposure for cases where stake
        # passes the stake limit but exceeds the loss limit)
        if exceeds_loss:
            return False, f"Max loss per trade ${stake:.2f} exceeds limit ${self.limits.max_loss_per_trade:.2f}"

        # Daily loss check: reject if already near limit and this trade
        # could push us over
        if self.daily_pnl < 0 and abs(self.daily_pnl) + stake > self.limits.daily_loss_limit:
            return False, (
                f"Daily loss limit: current loss ${abs(self.daily_pnl):.2f} + "
                f"potential ${stake:.2f} exceeds ${self.limits.daily_loss_limit:.2f}"
            )

        return True, None

    # ------------------------------------------------------------------
    # Position management
    # ------------------------------------------------------------------

    def record_position(
        self,
        event_id: str,
        provider: str,
        side: str,
        stake: float,
        price: float,
        current_stake: float = 0.0,
    ) -> str:
        """Record a new open position. Returns position_id."""
        position_id = str(uuid4())
        position = OpenPosition(
            position_id=position_id,
            event_id=event_id,
            provider=provider,
            side=side,
            stake=stake,
            entry_price=price,
            timestamp=datetime.utcnow(),
            current_stake=current_stake if current_stake > 0 else stake,
        )
        self.positions[position_id] = position
        return position_id

    def settle_position(
        self,
        position_id: str,
        outcome: str,
        settlement_price: float,
    ) -> float:
        """Settle a position and return realized P&L."""
        if position_id not in self.positions:
            LOGGER.warning(f"Attempted to settle unknown position {position_id}")
            return 0.0

        pos = self.positions.pop(position_id)

        # Calculate P&L
        if outcome.upper() == pos.side.upper():
            # Won: payout = current_stake / entry_price, profit = payout - current_stake
            pnl = (pos.current_stake / pos.entry_price) - pos.current_stake
        else:
            # Lost: lose entire stake
            pnl = -pos.current_stake

        self.daily_pnl += pnl

        # Record trade
        self.trades.append(
            TradeRecord(
                trade_id=str(uuid4()),
                event_id=pos.event_id,
                provider=pos.provider,
                side=pos.side,
                stake=pos.current_stake,
                entry_price=pos.entry_price,
                exit_price=settlement_price,
                pnl=pnl,
                timestamp=datetime.utcnow(),
            )
        )

        # Auto kill switch if daily loss limit exceeded
        if self.daily_pnl < 0 and abs(self.daily_pnl) > self.limits.daily_loss_limit:
            self.activate_kill_switch("Daily loss limit exceeded")

        return pnl

    def update_position_stake(self, position_id: str, new_stake: float) -> None:
        """Update the current stake of a position (e.g., partial fill)."""
        if position_id in self.positions:
            self.positions[position_id].current_stake = new_stake

    # ------------------------------------------------------------------
    # Exposure calculations
    # ------------------------------------------------------------------

    def get_exposure_by_event(self, event_id: str) -> float:
        return sum(
            pos.current_stake
            for pos in self.positions.values()
            if pos.event_id == event_id
        )

    def get_exposure_by_provider(self, provider: str) -> float:
        return sum(
            pos.current_stake
            for pos in self.positions.values()
            if pos.provider == provider
        )

    def get_total_exposure(self) -> float:
        return sum(pos.current_stake for pos in self.positions.values())

    # ------------------------------------------------------------------
    # Kill switch
    # ------------------------------------------------------------------

    def activate_kill_switch(self, reason: str = "") -> None:
        self.kill_switch_active = True
        self.kill_switch_reason = reason
        self.kill_switch_timestamp = datetime.utcnow()
        LOGGER.critical(f"KILL SWITCH ACTIVATED: {reason}")

    def deactivate_kill_switch(self) -> None:
        self.kill_switch_active = False
        self.kill_switch_reason = None
        self.kill_switch_timestamp = None
        LOGGER.info("Kill switch deactivated - trading resumed")

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def reset_daily_pnl(self) -> None:
        self.daily_pnl = 0.0

    def get_position_summary(self) -> Dict:
        by_provider: Dict[str, float] = {}
        for pos in self.positions.values():
            by_provider[pos.provider] = by_provider.get(pos.provider, 0) + pos.current_stake

        return {
            "total_positions": len(self.positions),
            "total_exposure": self.get_total_exposure(),
            "by_provider": by_provider,
        }

    def get_statistics(self) -> Dict:
        return {
            "kill_switch_active": self.kill_switch_active,
            "open_positions": len(self.positions),
            "total_exposure": self.get_total_exposure(),
            "daily_pnl": self.daily_pnl,
            "total_trades": len(self.trades),
        }
