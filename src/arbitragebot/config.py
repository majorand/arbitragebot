from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

import yaml


@dataclass
class SourceConfig:
    name: str
    base_url: str
    rate_limit_per_minute: int
    enabled: bool = True


@dataclass
class StrategyConfig:
    min_edge_pct: float
    max_stake: float
    max_exposure_per_market: float
    per_day_loss_limit: float
    per_book_limit: Dict[str, float] = field(default_factory=dict)


@dataclass
class TradingConfig:
    mode: str
    max_order_size: float


def load_yaml(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}