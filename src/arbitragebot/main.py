from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):  # type: ignore
        pass

# Load .env file if it exists
_env_path = Path(__file__).resolve().parent.parent.parent / '.env'
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)

from arbitragebot.arbitrage import (
    is_arbitrage,
    calculate_arbitrage_percentage,
    allocate_stakes,
    ArbitrageOpportunity,
    ArbitrageLeg,
)
from arbitragebot.config import StrategyConfig, TradingConfig, load_yaml
from arbitragebot.data_sources.espn import ESPNDataSource
from arbitragebot.data_sources.kalshi import KalshiDataSource
from arbitragebot.data_sources.polymarket import PolymarketDataSource
from arbitragebot.execution.paper import PaperTradingEngine
from arbitragebot.exchanges.kalshi import KalshiTradingClient
from arbitragebot.normalization import (
    KalshiNormalizer,
    PolymarketNormalizer,
    ESPNNormalizer,
    EventMatcher,
    MarketMatcher,
    ArbitrageDetector,
    CanonicalEvent,
    DetectedArbitrage,
    MatchedEventSet,
    Sport,
)
from arbitragebot.normalization.aggregator import (
    aggregate_events,
    find_cross_provider_markets,
    validate_aggregation,
    canonical_event_id,
    canonical_market_key,
)
from arbitragebot.schemas import NormalizedOdds
from arbitragebot.strategies.arbitrage import CrossMarketArbitrageStrategy
from arbitragebot.utils.odds import decimal_to_american

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


def collect_market_data(sources_config: dict) -> List[NormalizedOdds]:
    """Collect odds from Kalshi, ESPN, Polymarket and surface both raw and arbitrage opportunities."""

    # Kalshi elections API endpoint (hardcoded - this is the public API)
    kalshi = KalshiDataSource(
        api_key=os.getenv("KALSHI_API_KEY"),
    )
    # ESPN uses public API, no config needed
    espn = ESPNDataSource()
    # Polymarket with Web3 auth (uses private key from env)
    polymarket = PolymarketDataSource(
        private_key=os.getenv("POLYMARKET_PRIVATE_KEY")
    )

    # Collect odds from all sources
    kalshi_odds: List[NormalizedOdds] = []
    other_odds: List[NormalizedOdds] = []
    
    # Also collect canonical events for normalization pipeline
    events_by_provider = {}
    
    # Only fetch Kalshi if API key is present
    if os.getenv("KALSHI_API_KEY"):
        try:
            LOGGER.info("Fetching Kalshi markets...")
            kalshi_raw = kalshi.fetch_markets()
            kalshi_odds = kalshi.normalize_markets(kalshi_raw)
            LOGGER.info(f"Got {len(kalshi_odds)} Kalshi odds")
            
            # Normalize to canonical format for matching
            kalshi_normalizer = KalshiNormalizer()
            kalshi_events = []
            for market in kalshi_raw:
                try:
                    event = kalshi_normalizer.normalize_market(market)
                    if event:
                        kalshi_events.append(event)
                except Exception as e:
                    LOGGER.debug(f"Failed to normalize Kalshi market: {e}")
            events_by_provider["kalshi"] = kalshi_events
            LOGGER.info(f"Normalized {len(kalshi_events)} Kalshi markets to canonical format")
        except Exception as exc:
            LOGGER.warning("Failed to fetch Kalshi markets: %s", exc)
            events_by_provider["kalshi"] = []
    else:
        LOGGER.info("Skipping Kalshi: No API key configured (set KALSHI_API_KEY env var)")
        events_by_provider["kalshi"] = []

    try:
        LOGGER.info("Fetching ESPN events...")
        espn_data = espn.get_upcoming_games("basketball", "nba")
        other_odds.extend(espn_data)
        LOGGER.info(f"Got {len(espn_data)} ESPN events")
        
        # Normalize ESPN to canonical format
        espn_normalizer = ESPNNormalizer()
        espn_raw = espn.fetch_scoreboard("basketball", "nba")
        espn_events = []
        for comp in espn_raw:
            try:
                # Extract competitions from the event
                for competition in comp.get("competitions", []):
                    event = espn_normalizer.normalize_competition(competition, Sport.NBA)
                    if event:
                        espn_events.append(event)
            except Exception as e:
                LOGGER.debug(f"Failed to normalize ESPN competition: {e}")
        events_by_provider["espn"] = espn_events
        LOGGER.info(f"Normalized {len(espn_events)} ESPN events to canonical format")
    except Exception as exc:
        LOGGER.warning("Failed to fetch ESPN events: %s", exc)
        events_by_provider["espn"] = []

    # Optional: Polymarket comparator (cached per instance to limit requests)
    try:
        LOGGER.info("Fetching Polymarket markets...")
        pm_normalized = polymarket.fetch_markets()
        LOGGER.info(f"Polymarket fetch returned {len(pm_normalized) if pm_normalized else 0} markets")
        if pm_normalized:
            other_odds.extend(pm_normalized)
            LOGGER.info(f"Added {len(pm_normalized)} Polymarket markets to other_odds")
            
            # Also fetch raw markets for canonical normalization
            pm_raw = polymarket.fetch_raw_markets()
            polymarket_normalizer = PolymarketNormalizer()
            pm_events = []
            for market in pm_raw:
                try:
                    event = polymarket_normalizer.normalize_market(market)
                    if event:
                        pm_events.append(event)
                except Exception as e:
                    LOGGER.debug(f"Failed to normalize Polymarket market: {e}")
            events_by_provider["polymarket"] = pm_events
            LOGGER.info(f"Normalized {len(pm_events)} Polymarket markets to canonical format")
        else:
            LOGGER.info("Polymarket returned empty list (may be rate-limited or no active markets)")
            events_by_provider["polymarket"] = []
    except Exception as exc:
        LOGGER.error("Failed to fetch Polymarket markets: %s", exc, exc_info=True)
        events_by_provider["polymarket"] = []

    # Find arbitrage opportunities using aggregation pipeline
    detected_arbitrage = _find_arbitrage_with_normalization(
        events_by_provider,
        min_edge_pct=0.5,
    )
    
    # Convert detected arbitrage back to NormalizedOdds for display
    arbitrage_opportunities = _convert_detected_arbitrage_to_normalized_odds(detected_arbitrage)
    LOGGER.info(f"Converted {len(arbitrage_opportunities)} aggregated opportunities for display")

    # Also find arbitrage opportunities using legacy method (for comparison and backup)
    legacy_arbitrage = _find_arbitrage_opportunities(kalshi_odds, other_odds)

    # Always surface a blended list so UI shows all feeds
    blended: List[NormalizedOdds] = []
    blended.extend(arbitrage_opportunities)  # New canonical-based arbitrage
    blended.extend(legacy_arbitrage)  # Legacy arbitrage for comparison
    blended.extend(kalshi_odds)
    blended.extend(other_odds)

    if blended:
        return blended

    # Return mock opportunities for testing when no API keys configured
    LOGGER.info("No market data available - returning mock data for testing")
    return _generate_mock_opportunities()


def _normalize_event_key(name: str | None) -> str:
    if not name:
        return ""
    import re

    return re.sub(r"[^a-z0-9]", "", name.lower())


def _find_arbitrage_with_normalization(
    events_by_provider: dict,
    min_edge_pct: float = 0.5,
) -> List[DetectedArbitrage]:
    """
    NEW CORRECT PIPELINE:
    
    1. Aggregate events across providers (FIX #1, #2, #3)
    2. Validate aggregation (FIX #4)
    3. Run arbitrage detection on cross-provider outcomes (FIX #5)
    
    This ensures:
    - Events are shared across providers
    - Markets are grouped by type+line
    - Outcomes have provider tags
    - Arbitrage compares best prices across providers
    """
    
    detected_arbs = []
    
    try:
        LOGGER.info("=" * 60)
        LOGGER.info("AGGREGATION PHASE: Building cross-provider canonical events")
        LOGGER.info("=" * 60)
        
        # STEP 1: Aggregate events (enforces proper hierarchy)
        aggregated_events = aggregate_events(events_by_provider)
        
        # STEP 2: Validate aggregation quality
        stats = validate_aggregation(aggregated_events)
        if stats['cross_provider_events'] == 0:
            LOGGER.warning("⚠️ No cross-provider events found - arbitrage not possible")
            return []
        
        LOGGER.info("=" * 60)
        LOGGER.info("ARBITRAGE DETECTION PHASE: Scanning cross-provider outcomes")
        LOGGER.info("=" * 60)
        
        # STEP 3: Detect arbitrage on aggregated outcomes
        for event_id, event_data in aggregated_events.items():
            event_providers = event_data["providers"]
            
            # Skip single-provider events
            if len(event_providers) < 2:
                continue
            
            event_name = f"{event_data['home_team']} @ {event_data['away_team']}"
            LOGGER.debug(f"\nScanning: {event_name} (providers: {event_providers})")
            
            # For each market in this event
            for market_key, market_data in event_data.get("markets", {}).items():
                market_type = market_data["market_type"]
                
                # For each outcome in this market
                for outcome_key, provider_quotes in market_data["outcomes"].items():
                    provider_count = len(provider_quotes)
                    
                    # Only consider outcomes with 2+ provider quotes
                    if provider_count < 2:
                        continue
                    
                    # Extract prices from each provider
                    prices = {}
                    for provider, quote_data in provider_quotes.items():
                        prices[provider] = quote_data["implied_probability"]
                    
                    # Calculate best (lowest) and second-best price
                    sorted_prices = sorted(prices.items(), key=lambda x: x[1])
                    best_provider, best_price = sorted_prices[0]
                    
                    # Check for arbitrage: sum of best prices < 1
                    sum_best = sum([p[1] for p in sorted_prices[:2]])  # Two best prices
                    edge_pct = (1.0 - sum_best) * 100
                    
                    if edge_pct >= min_edge_pct and provider_count >= 2:
                        LOGGER.info(
                            f"✓ ARBITRAGE FOUND: {event_name} | {outcome_key} | "
                            f"Edge: {edge_pct:.2f}% | Providers: {list(prices.keys())}"
                        )
                        
                        # Create opportunity record
                        arb = {
                            "event_id": event_id,
                            "event_name": event_name,
                            "market_type": str(market_type),
                            "outcome": outcome_key,
                            "providers": event_providers,
                            "provider_quotes": prices,
                            "edge_pct": edge_pct,
                            "roi_pct": (1.0 / sum_best - 1.0) * 100 if sum_best > 0 else 0,
                            "best_provider": best_provider,
                            "best_price": best_price,
                        }
                        detected_arbs.append(arb)
        
        LOGGER.info(f"\n{'=' * 60}")
        LOGGER.info(f"Detection complete: {len(detected_arbs)} opportunities found")
        LOGGER.info(f"{'=' * 60}\n")
        
    except Exception as e:
        LOGGER.error(f"Aggregation pipeline failed: {e}", exc_info=True)
    
    return detected_arbs


def _convert_detected_arbitrage_to_normalized_odds(
    arbs: List[dict],
) -> List[NormalizedOdds]:
    """Convert aggregated arbitrage opportunities back to NormalizedOdds for display.
    
    Bridges the aggregator output to the existing UI format.
    """
    
    results = []
    
    for arb in arbs:
        # Get best provider quote
        best_provider = arb.get("best_provider", "unknown")
        best_price = arb.get("best_price", 0.5)
        
        # Get alternate providers for vs_source
        all_providers = list(arb["provider_quotes"].keys())
        vs_providers = [p for p in all_providers if p != best_provider]
        vs_provider = vs_providers[0] if vs_providers else None
        vs_price = arb["provider_quotes"].get(vs_provider, best_price) if vs_provider else best_price
        
        opp = NormalizedOdds(
            sport=arb.get("market_type", "unknown"),
            league="",
            event_id=arb["event_id"],
            event_name=arb["event_name"],
            start_time=datetime.utcnow(),
            home_team=arb["event_name"].split("@")[0].strip() if "@" in arb["event_name"] else "",
            away_team=arb["event_name"].split("@")[1].strip() if "@" in arb["event_name"] else "",
            market_type=arb.get("market_type", "unknown"),
            selection=arb["outcome"],
            price=best_price,
            implied_probability=best_price,
            american_odds=None,
            source=best_provider,
            last_updated=datetime.utcnow(),
        )
        
        # Add arbitrage metadata
        opp.edge = arb["edge_pct"]
        opp.vs_source = vs_provider or "N/A"
        opp.vs_price = vs_price
        opp.vs_selection = arb["outcome"]
        opp.vs_american_odds = None
        opp.recommended_stake_kalshi = 50.0  # Default stake
        opp.recommended_stake_other = 50.0
        
        results.append(opp)
    
    return results


def _prob_to_decimal(prob: float) -> float:
    return 1.0 / prob if prob and prob > 0 else 0.0


def _find_arbitrage_opportunities(
    kalshi_odds: List[NormalizedOdds],
    other_odds: List[NormalizedOdds],
    min_edge_pct: float = 0.5,
) -> List[NormalizedOdds]:
    """Compare odds across sources to find arbitrage edges by event name and market type.

    Uses proper arbitrage math: sum(1/odds) < 1 flags opportunity; profit% = (1/sum_implied) - 1.
    """

    opportunities: List[NormalizedOdds] = []

    # Build lookups keyed by normalized event + market_type for cross-source comparison
    kalshi_by_event = {}
    for odd in kalshi_odds:
        key = (_normalize_event_key(getattr(odd, "event_name", None) or odd.event_id), odd.market_type)
        kalshi_by_event.setdefault(key, []).append(odd)

    other_by_event = {}
    for odd in other_odds:
        key = (_normalize_event_key(getattr(odd, "event_name", None) or odd.event_id), odd.market_type)
        other_by_event.setdefault(key, []).append(odd)

    for key, kalshi_list in kalshi_by_event.items():
        other_list = other_by_event.get(key, [])
        if not other_list:
            continue

        for kalshi_odd in kalshi_list:
            for other_odd in other_list:
                # Skip same selection side; we need opposite legs
                if other_odd.selection == kalshi_odd.selection:
                    continue

                dec_kalshi = _prob_to_decimal(kalshi_odd.price)
                dec_other = _prob_to_decimal(other_odd.price)
                if dec_kalshi <= 1.0 or dec_other <= 1.0:
                    continue

                decimal_odds = [dec_kalshi, dec_other]

                if not is_arbitrage(decimal_odds, fee_buffer=0.005):
                    continue

                arb_pct = calculate_arbitrage_percentage(decimal_odds) * 100
                if arb_pct < min_edge_pct:
                    continue

                stakes = allocate_stakes(100.0, decimal_odds)

                opp = kalshi_odd.__class__(
                    sport=kalshi_odd.sport,
                    league=kalshi_odd.league,
                    event_id=kalshi_odd.event_id,
                    event_name=getattr(kalshi_odd, "event_name", None),
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

                opp.edge = arb_pct
                opp.vs_source = other_odd.source
                opp.vs_price = other_odd.price
                opp.vs_selection = other_odd.selection
                opp.recommended_stake_kalshi = stakes[0]
                opp.recommended_stake_other = stakes[1]
                opp.vs_american_odds = decimal_to_american(dec_other)

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
            event_name="MOCK-NBA-001",
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
            event_name="MOCK-NFL-002",
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
        opp.vs_source = "espn"
        opp.vs_price = opp.price - 0.05  # Slightly worse odds on ESPN baseline
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