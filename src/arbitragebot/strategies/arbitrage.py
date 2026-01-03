from __future__ import annotations

from collections import defaultdict
from typing import Iterable, List

from arbitragebot.config import StrategyConfig
from arbitragebot.schemas import NormalizedOdds, OrderRequest
from arbitragebot.strategies.base import Strategy


class CrossMarketArbitrageStrategy(Strategy):
    def __init__(self, config: StrategyConfig) -> None:
        self.config = config

    def generate_orders(
        self, market_data: Iterable[NormalizedOdds]
    ) -> List[OrderRequest]:
        grouped = defaultdict(list)
        for item in market_data:
            grouped[item.event_id].append(item)

        orders: List[OrderRequest] = []
        for event_id, entries in grouped.items():
            polymarket_entries = [e for e in entries if e.source == "polymarket"]
            sportsbook_entries = [e for e in entries if e.source != "polymarket"]
            if not polymarket_entries or not sportsbook_entries:
                continue
            best_polymarket = max(polymarket_entries, key=lambda e: e.implied_probability)
            best_sportsbook = min(sportsbook_entries, key=lambda e: e.implied_probability)
            edge_pct = (
                best_sportsbook.implied_probability
                - best_polymarket.implied_probability
            ) * 100
            if edge_pct < self.config.min_edge_pct:
                continue
            per_book_limit = self.config.per_book_limit.get(best_sportsbook.source)
            stake_cap = (
                min(self.config.max_stake, per_book_limit)
                if per_book_limit is not None
                else self.config.max_stake
            )
            stake = min(stake_cap, self.config.max_exposure_per_market)
            if stake <= 0:
                continue
            orders.append(
                OrderRequest(
                    market_id=best_polymarket.event_id,
                    side="buy",
                    price=best_polymarket.price,
                    size=stake,
                    order_type="limit",
                )
            )
        return orders