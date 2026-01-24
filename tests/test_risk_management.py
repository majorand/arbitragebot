"""Test suite for risk management module.

Tests comprehensive risk controls including stake limits, exposure tracking,
kill switch, and P&L monitoring.
"""

import pytest
from datetime import datetime, timedelta
from arbitragebot.risk_management import (
    RiskLimits,
    RiskManager,
    OpenPosition,
    TradeRecord,
)


class TestRiskLimits:
    """Test RiskLimits configuration."""

    def test_default_limits(self):
        """Test default risk limit values."""
        limits = RiskLimits()
        assert limits.max_stake_per_leg == 100.0
        assert limits.max_exposure_per_event == 500.0
        assert limits.max_exposure_per_provider == 2000.0
        assert limits.max_total_exposure == 5000.0
        assert limits.daily_loss_limit == 1000.0
        assert limits.max_loss_per_trade == 500.0

    def test_custom_limits(self):
        """Test custom risk limit configuration."""
        limits = RiskLimits(
            max_stake_per_leg=200.0,
            max_exposure_per_event=1000.0,
            daily_loss_limit=2000.0,
        )
        assert limits.max_stake_per_leg == 200.0
        assert limits.max_exposure_per_event == 1000.0
        assert limits.daily_loss_limit == 2000.0


class TestRiskManager:
    """Test RiskManager functionality."""

    def test_init(self):
        """Test risk manager initialization."""
        manager = RiskManager()
        assert not manager.kill_switch_active
        assert len(manager.positions) == 0
        assert len(manager.trades) == 0

    def test_can_execute_trade_basic(self):
        """Test basic trade validation."""
        manager = RiskManager()
        
        # Should allow trade within limits
        can_execute, reason = manager.can_execute_trade(
            event_id="event1",
            provider="kalshi",
            stake=50.0,
        )
        assert can_execute
        assert reason is None

    def test_can_execute_trade_exceeds_stake_limit(self):
        """Test stake limit enforcement."""
        limits = RiskLimits(max_stake_per_leg=100.0)
        manager = RiskManager(limits=limits)
        
        # Should reject stake exceeding limit
        can_execute, reason = manager.can_execute_trade(
            event_id="event1",
            provider="kalshi",
            stake=150.0,
        )
        assert not can_execute
        assert "stake limit" in reason.lower()

    def test_can_execute_trade_exceeds_event_exposure(self):
        """Test event exposure limit enforcement."""
        limits = RiskLimits(
            max_stake_per_leg=200.0,
            max_exposure_per_event=500.0,
        )
        manager = RiskManager(limits=limits)
        
        # Add existing position
        manager.record_position(
            event_id="event1",
            provider="kalshi",
            side="YES",
            stake=400.0,
            price=0.50,
        )
        
        # Should reject trade that would exceed event exposure
        can_execute, reason = manager.can_execute_trade(
            event_id="event1",
            provider="polymarket",
            stake=150.0,  # Would total 550.0 > 500.0 limit
        )
        assert not can_execute
        assert "event exposure" in reason.lower()

    def test_can_execute_trade_exceeds_provider_exposure(self):
        """Test provider exposure limit enforcement."""
        limits = RiskLimits(
            max_stake_per_leg=500.0,
            max_exposure_per_event=1000.0,
            max_exposure_per_provider=2000.0,
        )
        manager = RiskManager(limits=limits)
        
        # Add multiple positions on same provider
        manager.record_position("event1", "kalshi", "YES", 800.0, 0.50)
        manager.record_position("event2", "kalshi", "NO", 800.0, 0.60)
        
        # Should reject trade exceeding provider limit
        can_execute, reason = manager.can_execute_trade(
            event_id="event3",
            provider="kalshi",
            stake=500.0,  # Would total 2100.0 > 2000.0 limit
        )
        assert not can_execute
        assert "provider exposure" in reason.lower()

    def test_can_execute_trade_exceeds_total_exposure(self):
        """Test total exposure limit enforcement."""
        limits = RiskLimits(
            max_stake_per_leg=1000.0,
            max_exposure_per_event=2000.0,
            max_exposure_per_provider=4000.0,
            max_total_exposure=5000.0,
        )
        manager = RiskManager(limits=limits)
        
        # Add positions across multiple providers
        manager.record_position("event1", "kalshi", "YES", 2000.0, 0.50)
        manager.record_position("event2", "polymarket", "NO", 2500.0, 0.60)
        
        # Should reject trade exceeding total exposure
        can_execute, reason = manager.can_execute_trade(
            event_id="event3",
            provider="kalshi",
            stake=600.0,  # Would total 5100.0 > 5000.0 limit
        )
        assert not can_execute
        assert "total exposure" in reason.lower()

    def test_can_execute_with_kill_switch_active(self):
        """Test that kill switch blocks all trades."""
        manager = RiskManager()
        manager.activate_kill_switch("Manual test activation")
        
        can_execute, reason = manager.can_execute_trade(
            event_id="event1",
            provider="kalshi",
            stake=10.0,
        )
        assert not can_execute
        assert "kill switch" in reason.lower()

    def test_record_position(self):
        """Test position recording."""
        manager = RiskManager()
        
        position_id = manager.record_position(
            event_id="event1",
            provider="kalshi",
            side="YES",
            stake=100.0,
            price=0.55,
        )
        
        assert len(manager.positions) == 1
        position = manager.positions[position_id]
        assert position.event_id == "event1"
        assert position.provider == "kalshi"
        assert position.side == "YES"
        assert position.stake == 100.0
        assert position.entry_price == 0.55
        assert position.current_stake == 100.0

    def test_settle_position_profit(self):
        """Test settling position with profit."""
        manager = RiskManager()
        
        position_id = manager.record_position(
            event_id="event1",
            provider="kalshi",
            side="YES",
            stake=100.0,
            price=0.50,
        )
        
        pnl = manager.settle_position(
            position_id=position_id,
            outcome="YES",  # Won
            settlement_price=1.0,
        )
        
        # Profit = stake / entry_price - stake = 100/0.5 - 100 = 100
        assert pnl == 100.0
        assert position_id not in manager.positions  # Position closed
        assert manager.daily_pnl == 100.0

    def test_settle_position_loss(self):
        """Test settling position with loss."""
        manager = RiskManager()
        
        position_id = manager.record_position(
            event_id="event1",
            provider="kalshi",
            side="YES",
            stake=100.0,
            price=0.50,
        )
        
        pnl = manager.settle_position(
            position_id=position_id,
            outcome="NO",  # Lost
            settlement_price=0.0,
        )
        
        # Loss = -stake = -100
        assert pnl == -100.0
        assert position_id not in manager.positions
        assert manager.daily_pnl == -100.0

    def test_daily_loss_limit(self):
        """Test daily loss limit enforcement."""
        limits = RiskLimits(daily_loss_limit=500.0)
        manager = RiskManager(limits=limits)
        
        # Record and settle losing trades
        pos1 = manager.record_position("event1", "kalshi", "YES", 200.0, 0.50)
        manager.settle_position(pos1, "NO", 0.0)  # -200 loss
        
        pos2 = manager.record_position("event2", "polymarket", "YES", 250.0, 0.60)
        manager.settle_position(pos2, "NO", 0.0)  # -250 loss
        
        # Total loss = -450, within limit but close
        # Next trade should be rejected if it could exceed limit
        can_execute, reason = manager.can_execute_trade(
            event_id="event3",
            provider="kalshi",
            stake=100.0,  # Potential loss of 100 would total -550
        )
        assert not can_execute
        assert "daily loss limit" in reason.lower()

    def test_partial_fill_handling(self):
        """Test handling of partial fills."""
        manager = RiskManager()
        
        position_id = manager.record_position(
            event_id="event1",
            provider="kalshi",
            side="YES",
            stake=100.0,
            price=0.50,
        )
        
        # Partially close position
        manager.update_position_stake(position_id, 60.0)
        
        position = manager.positions[position_id]
        assert position.current_stake == 60.0
        assert position.stake == 100.0  # Original stake unchanged
        
        # Settle remaining
        pnl = manager.settle_position(position_id, "YES", 1.0)
        # PNL calculated on current_stake
        # Profit = 60/0.5 - 60 = 60
        assert pnl == 60.0

    def test_get_exposure_by_event(self):
        """Test exposure calculation by event."""
        manager = RiskManager()
        
        manager.record_position("event1", "kalshi", "YES", 100.0, 0.50)
        manager.record_position("event1", "polymarket", "NO", 150.0, 0.60)
        manager.record_position("event2", "kalshi", "YES", 200.0, 0.55)
        
        event1_exposure = manager.get_exposure_by_event("event1")
        assert event1_exposure == 250.0  # 100 + 150
        
        event2_exposure = manager.get_exposure_by_event("event2")
        assert event2_exposure == 200.0

    def test_get_exposure_by_provider(self):
        """Test exposure calculation by provider."""
        manager = RiskManager()
        
        manager.record_position("event1", "kalshi", "YES", 100.0, 0.50)
        manager.record_position("event2", "kalshi", "NO", 200.0, 0.60)
        manager.record_position("event3", "polymarket", "YES", 150.0, 0.55)
        
        kalshi_exposure = manager.get_exposure_by_provider("kalshi")
        assert kalshi_exposure == 300.0  # 100 + 200
        
        polymarket_exposure = manager.get_exposure_by_provider("polymarket")
        assert polymarket_exposure == 150.0

    def test_get_total_exposure(self):
        """Test total exposure calculation."""
        manager = RiskManager()
        
        manager.record_position("event1", "kalshi", "YES", 100.0, 0.50)
        manager.record_position("event2", "polymarket", "NO", 150.0, 0.60)
        manager.record_position("event3", "kalshi", "YES", 200.0, 0.55)
        
        total = manager.get_total_exposure()
        assert total == 450.0  # 100 + 150 + 200

    def test_activate_kill_switch(self):
        """Test kill switch activation."""
        manager = RiskManager()
        
        assert not manager.kill_switch_active
        
        manager.activate_kill_switch("Test reason")
        assert manager.kill_switch_active
        assert manager.kill_switch_reason == "Test reason"
        assert manager.kill_switch_timestamp is not None

    def test_deactivate_kill_switch(self):
        """Test kill switch deactivation."""
        manager = RiskManager()
        
        manager.activate_kill_switch("Test")
        assert manager.kill_switch_active
        
        manager.deactivate_kill_switch()
        assert not manager.kill_switch_active
        assert manager.kill_switch_reason is None
        assert manager.kill_switch_timestamp is None

    def test_auto_kill_switch_on_loss_limit(self):
        """Test automatic kill switch on daily loss limit."""
        limits = RiskLimits(daily_loss_limit=500.0)
        manager = RiskManager(limits=limits)
        
        # Create position that will trigger kill switch
        pos = manager.record_position("event1", "kalshi", "YES", 600.0, 0.50)
        manager.settle_position(pos, "NO", 0.0)  # -600 loss > 500 limit
        
        # Kill switch should be active
        assert manager.kill_switch_active
        assert "daily loss limit" in manager.kill_switch_reason.lower()

    def test_trade_history_recording(self):
        """Test trade history is properly recorded."""
        manager = RiskManager()
        
        pos = manager.record_position("event1", "kalshi", "YES", 100.0, 0.50)
        manager.settle_position(pos, "YES", 1.0)
        
        assert len(manager.trades) == 1
        trade = manager.trades[0]
        assert trade.event_id == "event1"
        assert trade.provider == "kalshi"
        assert trade.pnl == 100.0

    def test_reset_daily_pnl(self):
        """Test resetting daily P&L."""
        manager = RiskManager()
        
        pos = manager.record_position("event1", "kalshi", "YES", 100.0, 0.50)
        manager.settle_position(pos, "YES", 1.0)
        
        assert manager.daily_pnl != 0
        
        manager.reset_daily_pnl()
        assert manager.daily_pnl == 0.0

    def test_get_position_summary(self):
        """Test getting position summary."""
        manager = RiskManager()
        
        manager.record_position("event1", "kalshi", "YES", 100.0, 0.50)
        manager.record_position("event2", "polymarket", "NO", 150.0, 0.60)
        
        summary = manager.get_position_summary()
        assert summary["total_positions"] == 2
        assert summary["total_exposure"] == 250.0
        assert "kalshi" in summary["by_provider"]
        assert "polymarket" in summary["by_provider"]

    def test_max_loss_per_trade_limit(self):
        """Test max loss per trade limit."""
        limits = RiskLimits(max_loss_per_trade=100.0)
        manager = RiskManager(limits=limits)
        
        # Trade with potential loss > 100 should be rejected
        can_execute, reason = manager.can_execute_trade(
            event_id="event1",
            provider="kalshi",
            stake=150.0,  # Max loss = 150
        )
        assert not can_execute
        assert "max loss per trade" in reason.lower()


class TestOpenPosition:
    """Test OpenPosition dataclass."""

    def test_position_creation(self):
        """Test creating an open position."""
        position = OpenPosition(
            position_id="pos1",
            event_id="event1",
            provider="kalshi",
            side="YES",
            stake=100.0,
            entry_price=0.55,
            timestamp=datetime.utcnow(),
        )
        assert position.current_stake == 100.0  # Should equal stake initially

    def test_position_with_custom_current_stake(self):
        """Test position with custom current stake (partial fill)."""
        position = OpenPosition(
            position_id="pos1",
            event_id="event1",
            provider="kalshi",
            side="YES",
            stake=100.0,
            entry_price=0.55,
            timestamp=datetime.utcnow(),
            current_stake=60.0,
        )
        assert position.stake == 100.0
        assert position.current_stake == 60.0


class TestTradeRecord:
    """Test TradeRecord dataclass."""

    def test_trade_record_creation(self):
        """Test creating a trade record."""
        trade = TradeRecord(
            trade_id="trade1",
            event_id="event1",
            provider="kalshi",
            side="YES",
            stake=100.0,
            entry_price=0.55,
            exit_price=1.0,
            pnl=81.82,
            timestamp=datetime.utcnow(),
        )
        assert trade.pnl == 81.82
        assert trade.provider == "kalshi"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
