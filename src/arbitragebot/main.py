from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List

from arbitragebot.config import StrategyConfig, TradingConfig, load_yaml
from arbitragebot.data_sources.draftkings import DraftKingsDataSource
from arbitragebot.data_sources.espn import ESPNDataSource
from arbitragebot.data_sources.kalshi import KalshiDataSource
from arbitragebot.execution.paper import PaperTradingEngine
from arbitragebot.exchanges.kalshi import KalshiTradingClient
from arbitragebot.schemas import NormalizedOdds
from arbitragebot.strategies.arbitrage import CrossMarketArbitrageStrategy

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


def collect_market_data(sources_config: dict) -> List[NormalizedOdds]:
    kalshi_cfg = sources_config.get("kalshi", {})
    espn_cfg = sources_config.get("espn", {})
    draftkings_cfg = sources_config.get("draftkings", {})

    kalshi = KalshiDataSource(
        base_url=kalshi_cfg.get(
            "base_url", os.getenv("KALSHI_API", "https://api.kalshi.com")
        ),
        api_key=os.getenv("KALSHI_API_KEY"),
    )
    espn = ESPNDataSource(
        base_url=espn_cfg.get("base_url", "https://site.api.espn.com/apis/site/v2")
    )
    draftkings = DraftKingsDataSource(
        base_url=draftkings_cfg.get(
            "base_url", "https://sportsbook.draftkings.com/sites/US-SB/api/v5"
        )
    )

    data: List[NormalizedOdds] = []
    try:
        data.extend(kalshi.normalize_markets(kalshi.fetch_markets()))
    except Exception as exc:  # noqa: BLE001 - log and continue
        LOGGER.warning("Failed to fetch Kalshi markets: %s", exc)

    try:
        events = espn.fetch_events("basketball", "nba")
        data.extend(espn.normalize_events(events))
    except Exception as exc:  # noqa: BLE001 - log and continue
        LOGGER.warning("Failed to fetch ESPN events: %s", exc)

    try:
        odds = draftkings.fetch_odds("42648")
        data.extend(draftkings.normalize_odds(odds))
    except Exception as exc:  # noqa: BLE001 - log and continue
        LOGGER.warning("Failed to fetch DraftKings odds: %s", exc)

    return data


def load_strategy_config(path: Path) -> StrategyConfig:
    config = load_yaml(path)
    payload = config.get("strategy", {})
    return StrategyConfig(
        min_edge_pct=payload.get("min_edge_pct", 1.5),
        max_stake=payload.get("max_stake", 50.0),
        max_exposure_per_market=payload.get("max_exposure_per_market", 100.0),
        per_day_loss_limit=payload.get("per_day_loss_limit", 500.0),
        per_book_limit=payload.get("per_book_limit", {}),
    )


def run_once() -> None:
    sources_path = Path(os.getenv("SOURCES_CONFIG", "config/example_sources.yaml"))
    strategy_path = Path(os.getenv("STRATEGY_CONFIG", "config/strategy.yaml"))

    sources_config = load_yaml(sources_path).get("sources", {})
    data = collect_market_data(sources_config)

    strategy = CrossMarketArbitrageStrategy(load_strategy_config(strategy_path))
    orders = strategy.generate_orders(data)
    trading_config = TradingConfig(
        mode=os.getenv("TRADING_MODE", "paper"), max_order_size=100
    )

    if trading_config.mode == "paper":
        paper = PaperTradingEngine()
        for order in orders:
            paper.submit_order(order, reference_price=order.price)
        LOGGER.info("Paper mode completed with %s orders", len(orders))
    else:
        client = KalshiTradingClient(
            base_url=os.getenv("KALSHI_API", "https://api.kalshi.com"),
            api_key=os.getenv("KALSHI_API_KEY"),
        )
        for order in orders:
            result = client.place_order(order)
            LOGGER.info("Placed order %s status=%s", result.order_id, result.status)


if __name__ == "__main__":
    run_once()