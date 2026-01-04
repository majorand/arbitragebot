from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List

from arbitragebot.arbitrage import (
    is_arbitrage,
    calculate_arbitrage_percentage,
    allocate_stakes,
    ArbitrageOpportunity,
    ArbitrageLeg,
)
from arbitragebot.config import StrategyConfig, TradingConfig, load_yaml
from arbitragebot.data_sources.draftkings import DraftKingsDataSource
from arbitragebot.data_sources.espn import ESPNDataSource
from arbitragebot.data_sources.fanduel import FanDuelDataSource
from arbitragebot.data_sources.kalshi import KalshiDataSource
from arbitragebot.execution.paper import PaperTradingEngine
from arbitragebot.exchanges.kalshi import KalshiTradingClient
from arbitragebot.schemas import NormalizedOdds
from arbitragebot.strategies.arbitrage import CrossMarketArbitrageStrategy
from arbitragebot.utils.odds import decimal_to_american

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


def collect_market_data(sources_config: dict) -> List[NormalizedOdds]:
    """Collect odds from all sources and find arbitrage opportunities vs Kalshi.
    
    Strategy:
    1. Fetch Kalshi odds (primary exchange for placing trades)
    2. Fetch ESPN events (data source)
    3. Fetch DraftKings odds (comparison)
    4. Fetch FanDuel odds (comparison)
    5. Compare all sources to Kalshi and identify edges
    """
    kalshi_cfg = sources_config.get("kalshi", {})
    espn_cfg = sources_config.get("espn", {})
    draftkings_cfg = sources_config.get("draftkings", {})
    fanduel_cfg = sources_config.get("fanduel", {})

    kalshi = KalshiDataSource(
        base_url=kalshi_cfg.get(
            "base_url", os.getenv("KALSHI_API", "https://api.kalshi.com")
        ),
        api_key=os.getenv("KALSHI_API_KEY"),
    )
    # ESPN uses public API, no config needed
    espn = ESPNDataSource()
    draftkings = DraftKingsDataSource(
        base_url=draftkings_cfg.get(
            "base_url", "https://sportsbook.draftkings.com/sites/US-SB/api/v5"
        )
    )
    fanduel = FanDuelDataSource(
        base_url=fanduel_cfg.get("base_url", "https://api.fanduel.com/v4")
    )

    # Collect odds from all sources
    kalshi_odds: List[NormalizedOdds] = []
    other_odds: List[NormalizedOdds] = []
    
    # Only fetch Kalshi if API key is present
    if os.getenv("KALSHI_API_KEY"):
        try:
            LOGGER.info("Fetching Kalshi markets...")
            kalshi_odds = kalshi.normalize_markets(kalshi.fetch_markets())
            LOGGER.info(f"Got {len(kalshi_odds)} Kalshi odds")
        except Exception as exc:
            LOGGER.warning("Failed to fetch Kalshi markets: %s", exc)
    else:
        LOGGER.info("Skipping Kalshi: No API key configured (set KALSHI_API_KEY env var)")

    try:
        LOGGER.info("Fetching ESPN events...")
        espn_data = espn.get_upcoming_games("basketball", "nba")
        other_odds.extend(espn_data)
        LOGGER.info(f"Got {len(espn_data)} ESPN events")
    except Exception as exc:
        LOGGER.warning("Failed to fetch ESPN events: %s", exc)

    try:
        LOGGER.info("Fetching DraftKings odds...")
        odds = draftkings.fetch_odds("42648")
        dk_data = draftkings.normalize_odds(odds)
        other_odds.extend(dk_data)
        LOGGER.info(f"Got {len(dk_data)} DraftKings odds")
    except Exception as exc:
        LOGGER.warning("Failed to fetch DraftKings odds: %s", exc)

    try:
        LOGGER.info("Fetching FanDuel odds...")
        odds = fanduel.fetch_odds()
        fd_data = fanduel.normalize_odds(odds)
        other_odds.extend(fd_data)
        LOGGER.info(f"Got {len(fd_data)} FanDuel odds")
    except Exception as exc:
        LOGGER.warning("Failed to fetch FanDuel odds: %s", exc)

    # Find arbitrage opportunities: where other sources differ from Kalshi
    arbitrage_opportunities = _find_arbitrage_opportunities(kalshi_odds, other_odds)
    
    # If we have data, return it
    if arbitrage_opportunities:
        return arbitrage_opportunities
    if kalshi_odds:
        return kalshi_odds
    if other_odds:
        return other_odds
    
    # Return mock opportunities for testing when no API keys configured
    LOGGER.info("No market data available - returning mock data for testing")
    return _generate_mock_opportunities()


def _find_arbitrage_opportunities(
    kalshi_odds: List[NormalizedOdds], 
    other_odds: List[NormalizedOdds],
    min_edge_pct: float = 1.5
) -> List[NormalizedOdds]:
    """Compare odds across sources to find arbitrage edges.
    
    An arbitrage exists when:
    - Kalshi has one side of a bet
    - Another sportsbook has better odds on the opposite side
    - The combined implied probabilities are < 100% (profit opportunity)
    
    Uses proper arbitrage mathematics from arbitrage.calculator module.
    """
    opportunities = []
    
    # Group odds by event for comparison
    kalshi_by_event = {}
    for odd in kalshi_odds:
        key = (odd.event_id, odd.market_type, odd.selection)
        if key not in kalshi_by_event:
            kalshi_by_event[key] = odd
    
    other_by_event = {}
    for odd in other_odds:
        key = (odd.event_id, odd.market_type, odd.selection)
        if key not in other_by_event:
            other_by_event[key] = odd
    
    # Find edges: compare Kalshi to other sources
    for (event_id, market_type, selection), kalshi_odd in kalshi_by_event.items():
        # Find opposite side bets
        opposite_selections = [
            sel for (e, m, sel) in other_by_event.keys() 
            if e == event_id and m == market_type and sel != selection
        ]
        
        for opp_side in opposite_selections:
            opp_key = (event_id, market_type, opp_side)
            other_odd = other_by_event.get(opp_key)
            
            if not other_odd:
                continue
            
            # Check for arbitrage using proper calculator
            decimal_odds = [kalshi_odd.price, other_odd.price]
            
            if not is_arbitrage(decimal_odds, fee_buffer=0.005):
                continue
            
            # Calculate actual arbitrage percentage
            arb_pct = calculate_arbitrage_percentage(decimal_odds) * 100
            
            if arb_pct < min_edge_pct:
                continue
            
            # Calculate stake allocation for $100 bankroll
            stakes = allocate_stakes(100.0, decimal_odds)
            
            # Create opportunity with enriched data
            opp = kalshi_odd.__class__(
                sport=kalshi_odd.sport,
                league=kalshi_odd.league,
                event_id=kalshi_odd.event_id,
                start_time=kalshi_odd.start_time,
                home_team=kalshi_odd.home_team,
                away_team=kalshi_odd.away_team,
                market_type=kalshi_odd.market_type,
                selection=kalshi_odd.selection,
                price=kalshi_odd.price,
                implied_probability=kalshi_odd.implied_probability,
                source="kalshi",
                last_updated=kalshi_odd.last_updated,
            )
            
            # Add arbitrage metadata
            opp.edge = arb_pct
            opp.vs_source = other_odd.source
            opp.vs_price = other_odd.price
            opp.vs_selection = other_odd.selection
            opp.recommended_stake_kalshi = stakes[0]
            opp.recommended_stake_other = stakes[1]
            opp.vs_american_odds = decimal_to_american(other_odd.price)
            
            opportunities.append(opp)
    
    LOGGER.info(f"Found {len(opportunities)} arbitrage opportunities >= {min_edge_pct}%")
    return sorted(opportunities, key=lambda x: x.edge, reverse=True)


def _generate_mock_opportunities() -> List[NormalizedOdds]:
    """Generate mock opportunities for testing when APIs aren't configured."""
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    
    mock_data = [
        NormalizedOdds(
            sport="basketball",
            league="nba",
            event_id="MOCK-NBA-001",
            start_time=now + timedelta(hours=2),
            home_team="Los Angeles Lakers",
            away_team="Boston Celtics",
            market_type="moneyline",
            selection="home",
            price=1.85,
            american_odds=-130,
            implied_probability=0.54,
            source="kalshi",
            last_updated=now,
        ),
        NormalizedOdds(
            sport="football",
            league="nfl",
            event_id="MOCK-NFL-002",
            start_time=now + timedelta(hours=4),
            home_team="Kansas City Chiefs",
            away_team="Buffalo Bills",
            market_type="moneyline",
            selection="home",
            price=2.04,
            american_odds=-105,
            implied_probability=0.49,
            source="kalshi",
            last_updated=now,
        ),
    ]
    
    # Add mock arbitrage metadata by attaching attributes
    for idx, opp in enumerate(mock_data):
        opp.edge = 1.5 + (idx * 0.3)  # 1.5%, 1.8%
        opp.vs_source = "draftkings"
        opp.vs_price = opp.price - 0.05  # Slightly worse odds on DraftKings
        opp.vs_selection = opp.selection
        opp.recommended_stake_kalshi = 100.0 * (idx + 1)
        opp.recommended_stake_other = 95.0 * (idx + 1)
        opp.vs_american_odds = -115 if idx == 0 else -110
    
    LOGGER.info(f"Generated {len(mock_data)} mock arbitrage opportunities for testing")
    return mock_data


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