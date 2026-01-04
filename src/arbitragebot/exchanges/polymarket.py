"""Polymarket removed.

This file intentionally raises an ImportError to ensure no code
continues to rely on the removed Polymarket integration.
"""

from __future__ import annotations

raise ImportError(
	"Polymarket support has been removed. Use arbitragebot.exchanges.kalshi instead."
)