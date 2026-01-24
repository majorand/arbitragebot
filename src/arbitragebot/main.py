from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

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
from arbitragebot.arbitrage.detector import ArbitrageDetector as NewArbitrageDetector, detect_arbitrage_opportunities
from arbitragebot.config import StrategyConfig, TradingConfig, load_yaml
from arbitragebot.data_sources.kalshi import KalshiDataSource
from arbitragebot.data_sources.polymarket import PolymarketDataSource
from arbitragebot.execution.paper import PaperTradingEngine
from arbitragebot.exchanges.kalshi import KalshiTradingClient
from arbitragebot.normalization import (
    KalshiNormalizer,
    PolymarketNormalizer,
    EventMatcher,
    MarketMatcher,
    ArbitrageDetector as LegacyArbitrageDetector,
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
from arbitragebot.normalization.schemas import PROVIDER_KALSHI, PROVIDER_POLYMARKET
from arbitragebot.schemas import NormalizedOdds
from arbitragebot.strategies.arbitrage import CrossMarketArbitrageStrategy
from arbitragebot.utils.odds import decimal_to_american
from arbitragebot.core.instruments import InstrumentExtractor
from arbitragebot.opportunity_helpers import BinaryArbitrageOpportunity, find_arb_opportunities

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


def collect_market_data(sources_config: dict) -> List[NormalizedOdds]:
    """Collect odds from Kalshi and Polymarket for cross-market arbitrage detection."""

    # Kalshi prediction markets API
    kalshi = KalshiDataSource(
        api_key=os.getenv("KALSHI_API_KEY"),
    )
    # Polymarket decentralized prediction markets
    polymarket = PolymarketDataSource(
        private_key=os.getenv("POLYMARKET_PRIVATE_KEY"),
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

    # Fetch Polymarket markets
    try:
        LOGGER.info("Fetching Polymarket markets...")
        polymarket_raw = polymarket.fetch_markets()
        polymarket_odds = polymarket.normalize_markets(polymarket_raw)
        other_odds.extend(polymarket_odds)
        LOGGER.info(f"Got {len(polymarket_odds)} Polymarket markets")
        
        # Normalize to canonical format for matching
        polymarket_normalizer = PolymarketNormalizer()
        polymarket_events = []
        for market in polymarket_raw:
            try:
                event = polymarket_normalizer.normalize_market(market)
                if event:
                    polymarket_events.append(event)
            except Exception as e:
                LOGGER.debug(f"Failed to normalize Polymarket market: {e}")
        events_by_provider["polymarket"] = polymarket_events
        LOGGER.info(f"Normalized {len(polymarket_events)} Polymarket markets to canonical format")
    except Exception as exc:
        LOGGER.warning("Failed to fetch Polymarket markets: %s", exc)
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
    INSTRUMENT-LEVEL AGGREGATION PIPELINE:
    
    1. Extract canonical instruments from each provider
    2. Group outcomes by instrument across providers
    3. Detect arbitrage at instrument level (not event level)
    
    This ensures different market phrasings map to the same instrument.
    """
    
    detected_arbs = []
    
    try:
        LOGGER.info("=" * 60)
        LOGGER.info("INSTRUMENT AGGREGATION: Converting markets to canonical instruments")
        LOGGER.info("=" * 60)
        
        # Create instrument extractor/aggregator
        extractor = InstrumentExtractor()
        
        # Track stats
        total_events = 0
        processed_events = 0
        
        # Process each provider's canonical events
        for provider_name, events in events_by_provider.items():
            if not events:
                continue
                
            total_events += len(events)
            LOGGER.info(f"Processing {len(events)} events from {provider_name}")
            
            for event in events:
                home_team = getattr(event, 'home_team', None)
                away_team = getattr(event, 'away_team', None)
                raw_event_name = getattr(event, 'event_name', None)
                league = getattr(event, 'league', '')
                start_time = getattr(event, 'start_time', None)
                sport_obj = getattr(event, 'sport', 'sports')

                # Canonical sport string (handles enums)
                sport = sport_obj.value if hasattr(sport_obj, 'value') else sport_obj

                # Prefer explicit event name/question
                text = raw_event_name
                if not text and hasattr(event, 'display_name'):
                    try:
                        text = event.display_name()
                    except Exception:
                        text = None
                if not text:
                    if home_team and away_team:
                        text = f"{home_team} vs {away_team}"
                    else:
                        LOGGER.debug(f"Skipping event with empty text from {provider_name}")
                        continue

                # Add outcomes per market (enforces market-type compatibility)
                markets = getattr(event, 'markets', [])
                if not markets:
                    continue

                processed_events += 1

                for market_obj in markets:
                    market_type_obj = getattr(market_obj, 'market_type', None)
                    market_type = market_type_obj.value if hasattr(market_type_obj, 'value') else market_type_obj

                    # Only ESPN has reliable structured teams; other providers often use placeholders (e.g., "MARKET")
                    use_structured_teams = bool(provider_name == "espn" and home_team and away_team)

                    instrument = extractor.extract_instrument(
                        domain=sport,
                        text=text or "",
                        market_type=str(market_type) if market_type else None,
                        home_team=home_team if use_structured_teams else None,
                        away_team=away_team if use_structured_teams else None,
                        event_name=text or raw_event_name,
                        league=league,
                        event_date=str(start_time) if start_time else None,
                    )

                    if instrument is None:
                        LOGGER.debug(f"Failed to extract instrument from {provider_name}: {text}")
                        continue

                    outcomes = getattr(market_obj, 'outcomes', [])
                    for outcome in outcomes:
                        outcome_type_obj = getattr(outcome, 'outcome_type', None)
                        outcome_type = outcome_type_obj.value if hasattr(outcome_type_obj, 'value') else outcome_type_obj
                        implied_prob = getattr(outcome, 'implied_probability', None)
                        title = getattr(outcome, 'title', '')

                        if implied_prob is None:
                            continue

                        # Canonical YES/NO mapping
                        normalized_outcome = str(outcome_type or title).upper()
                        if normalized_outcome in ["YES", "HOME", "TRUE", "WIN"]:
                            normalized_outcome = "true"
                        elif normalized_outcome in ["NO", "AWAY", "FALSE", "LOSE"]:
                            normalized_outcome = "false"
                        else:
                            # Team-based mapping fallback
                            if home_team and title and home_team.lower() in title.lower():
                                normalized_outcome = "true"
                            elif away_team and title and away_team.lower() in title.lower():
                                normalized_outcome = "false"
                            else:
                                continue

                        extractor.add_outcome(
                            instrument=instrument,
                            outcome=normalized_outcome,
                            provider=provider_name,
                            price=implied_prob,
                        )
        
        LOGGER.info(f"Processed {processed_events}/{total_events} events")
        LOGGER.info(f"Extracted {len(extractor.instruments)} unique instruments")
        
        # Count cross-provider instruments
        cross_provider = [inst for inst in extractor.instruments.values() if len(inst.providers) >= 2]
        cross_provider_count = len(cross_provider)
        single_provider_count = len(extractor.instruments) - cross_provider_count
        avg_providers = sum(len(inst.providers) for inst in extractor.instruments.values()) / len(extractor.instruments) if extractor.instruments else 0
        
        LOGGER.info(f"Cross-provider instruments: {cross_provider_count}")
        LOGGER.info(f"Single-provider instruments: {single_provider_count}")
        LOGGER.info(f"Average providers per instrument: {avg_providers:.2f}")
        
        if cross_provider_count == 0:
            LOGGER.warning("⚠️ No cross-provider instruments found - arbitrage not possible")
            return []
        
        LOGGER.info("=" * 60)
        LOGGER.info("ARBITRAGE DETECTION: Scanning instruments for opportunities")
        LOGGER.info("=" * 60)
        
        # Get arbitrage opportunities
        opportunities = find_arb_opportunities(
            extractor.instruments.values(),
            min_edge_pct,
        )

        LOGGER.info(
            f"Found {len(opportunities)} Kalshi ↔ Polymarket opportunities >= {min_edge_pct}%"
        )
        detected_arbs.extend(opportunities)
        
        LOGGER.info(f"\n{'=' * 60}")
        LOGGER.info(f"Detection complete: {len(detected_arbs)} opportunities found")
        LOGGER.info(f"{'=' * 60}\n")
        
    except Exception as e:
        LOGGER.error(f"Instrument aggregation pipeline failed: {e}", exc_info=True)
    
    return detected_arbs


def _convert_detected_arbitrage_to_normalized_odds(
    arbs: List[BinaryArbitrageOpportunity | dict],
) -> List[NormalizedOdds]:
    """Convert aggregated Kalshi ↔ Polymarket opportunities into NormalizedOdds for the UI."""

    def _get_attr(item, name, default=None):
        if isinstance(item, dict):
            return item.get(name, default)
        return getattr(item, name, default)

    results: List[NormalizedOdds] = []

    for arb in arbs:
        event_name = _get_attr(arb, "event_name") or "Market"
        market_label = (_get_attr(arb, "market") or "YES_NO").replace("_", " ").upper()
        providers = _get_attr(arb, "providers") or []
        best_yes = (_get_attr(arb, "best_yes") or {})
        best_no = (_get_attr(arb, "best_no") or {})
        links = _get_attr(arb, "links") or {}
        edge_pct = float(_get_attr(arb, "edge_pct", 0.0))
        recommended_side = _get_attr(arb, "recommended_side") or "yes"
        expected_profit = _get_attr(arb, "expected_profit", 0.0)

        kalshi_leg = None
        polymarket_leg = None
        for leg in (best_yes, best_no):
            provider = leg.get("provider")
            if provider == PROVIDER_KALSHI:
                kalshi_leg = leg
            elif provider == PROVIDER_POLYMARKET:
                polymarket_leg = leg

        kalshi_price = float(kalshi_leg.get("price", 0.0)) if kalshi_leg else 0.0
        polymarket_price = float(polymarket_leg.get("price", 0.0)) if polymarket_leg else 0.0
        kalshi_decimal = float(kalshi_leg.get("decimal_odds", 0.0)) if kalshi_leg else 0.0
        polymarket_decimal = float(polymarket_leg.get("decimal_odds", 0.0)) if polymarket_leg else 0.0

        opp = NormalizedOdds(
            sport="sports",
            league="",
            event_id=_get_attr(arb, "event_id") or f"arb-{datetime.utcnow().timestamp()}",
            event_name=event_name,
            start_time=datetime.utcnow(),
            home_team="",
            away_team="",
            market_type="moneyline",
            selection=(kalshi_leg.get("selection") if kalshi_leg else market_label) or "YES",
            price=kalshi_price,
            implied_probability=kalshi_price,
            american_odds=decimal_to_american(kalshi_decimal) if kalshi_decimal else None,
            source="aggregated",
            last_updated=datetime.utcnow(),
        )

        opp.is_arbitrage = True
        opp.edge = edge_pct
        opp.roi_percentage = edge_pct
        opp.sources = providers
        opp.providers = providers
        opp.best_yes = best_yes
        opp.best_no = best_no
        opp.market = market_label
        opp.links = links
        opp.recommended_side = recommended_side
        opp.reason = f"Kalshi vs Polymarket single-leg binary edge {edge_pct:.2f}%"
        opp.recommendation = f"Buy {opp.selection} on Kalshi and hedge the opposite on Polymarket."
        opp.venues = "Kalshi ↔ Polymarket"
        opp.ev = float(expected_profit)
        opp.legs = _get_attr(arb, "legs") or []

        if kalshi_leg:
            opp.stake_kalshi = float(kalshi_leg.get("stake", 0.0))
        if polymarket_leg:
            opp.vs_source = PROVIDER_POLYMARKET
            opp.vs_selection = polymarket_leg.get("selection") or "NO"
            opp.vs_price = polymarket_price
            opp.vs_american_odds = decimal_to_american(polymarket_decimal) if polymarket_decimal else None
            opp.stake_other = float(polymarket_leg.get("stake", 0.0))

        opp.market_id = _get_attr(arb, "event_id")

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