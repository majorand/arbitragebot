"""Database schemas for arbitrage bot storage.

Lightweight dataclasses representing rows we persist to Supabase
or other storage backends. These are intentionally minimal and
compatible with the helpers in `storage.supabase`.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any


@dataclass
class OddsRow:
	odds_id: str
	event_id: str
	source: str
	market_type: str
	selection: str
	price: float
	implied_probability: float
	start_time: datetime
	last_updated: datetime

	def to_dict(self) -> Dict[str, Any]:
		d = asdict(self)
		d["start_time"] = self.start_time.isoformat()
		d["last_updated"] = self.last_updated.isoformat()
		return d


@dataclass
class TradeRow:
	trade_id: str
	event_id: str
	price: float
	stake: float
	status: str
	mode: str
	timestamp: datetime

	def to_dict(self) -> Dict[str, Any]:
		d = asdict(self)
		d["timestamp"] = self.timestamp.isoformat()
		return d


@dataclass
class PositionRow:
	event_id: str
	size: float

	def to_dict(self) -> Dict[str, Any]:
		return asdict(self)


__all__ = ["OddsRow", "TradeRow", "PositionRow"]
