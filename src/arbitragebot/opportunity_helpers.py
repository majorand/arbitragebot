"""Helper functions for Kalshi ↔ Polymarket binary opportunities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Optional
from urllib.parse import quote_plus

from arbitragebot.arbitrage.calculator import (
    allocate_stakes,
    calculate_arbitrage_percentage,
    is_arbitrage,
)
from arbitragebot.core.instruments import Instrument
from arbitragebot.normalization.schemas import PROVIDER_KALSHI, PROVIDER_POLYMARKET

ALLOWED_PROVIDERS = {PROVIDER_KALSHI, PROVIDER_POLYMARKET}
DEFAULT_BANKROLL = 100.0


@dataclass
class OpportunityLeg:
    provider: str
    selection: str
    implied_probability: float
    decimal_odds: float
    recommended_stake: float
    expected_return: float
    link: str


@dataclass
class BinaryArbitrageOpportunity:
    event_id: str
    event_name: str
    market: str
    edge_pct: float
    roi_percentage: float
    implied_probability_sum: float
    providers: List[str]
    legs: List[OpportunityLeg]
    links: Dict[str, str]
    best_yes: Dict[str, float | str]
    best_no: Dict[str, float | str]
    recommended_side: str
    execution_risk: str
    expected_profit: float
    yes_quotes: Dict[str, float]
    no_quotes: Dict[str, float]
    timestamp: datetime = field(default_factory=datetime.utcnow)


def _prob_to_decimal(probability: float) -> float:
    if not probability or probability <= 0:
        return 0.0
    return 1.0 / probability


def _build_provider_link(provider: str, event_name: str) -> str:
    safe_query = quote_plus(event_name or '')
    if provider == PROVIDER_KALSHI:
        return f"https://kalshi.com/search?query={safe_query}"
    if provider == PROVIDER_FANATICS:
        return f"https://www.fanatics.com/search?q={safe_query}"
    return ""


def is_arb_candidate(instrument: Instrument) -> bool:
    """Return True when instrument is eligible for Kalshi vs Fanatics binary arbitrage."""
    # Design constraint: limit detection to single-leg Kalshi ↔ Fanatics binaries only.
    providers = instrument.providers
    if providers != ALLOWED_PROVIDERS:
        return False
    true_quotes = instrument.outcomes.get("true") or {}
    false_quotes = instrument.outcomes.get("false") or {}
    return bool(true_quotes and false_quotes)


def _build_leg(
    provider: str,
    selection: str,
    implied_probability: float,
    decimal_odds: float,
    stake: float,
    event_name: str,
) -> OpportunityLeg:
    link = _build_provider_link(provider, event_name)
    expected_return = stake * decimal_odds
    return OpportunityLeg(
        provider=provider,
        selection=selection,
        implied_probability=implied_probability,
        decimal_odds=decimal_odds,
        recommended_stake=stake,
        expected_return=expected_return,
        link=link,
    )


def _evaluate_combo(
    instrument: Instrument,
    true_provider: str,
    false_provider: str,
    true_prob: float,
    false_prob: float,
    min_edge_pct: float,
) -> Optional[BinaryArbitrageOpportunity]:
    dec_true = _prob_to_decimal(true_prob)
    dec_false = _prob_to_decimal(false_prob)
    if dec_true <= 1.0 or dec_false <= 1.0:
        return None

    if not is_arbitrage([dec_true, dec_false]):
        return None

    edge_decimal = calculate_arbitrage_percentage([dec_true, dec_false])
    edge_pct = edge_decimal * 100
    if edge_pct < min_edge_pct:
        return None

    stakes = allocate_stakes(DEFAULT_BANKROLL, [dec_true, dec_false])
    if len(stakes) < 2:
        return None

    event_name = instrument.context.get("event_name") or instrument.subject
    true_leg = _build_leg(
        provider=true_provider,
        selection="YES",
        implied_probability=true_prob,
        decimal_odds=dec_true,
        stake=stakes[0],
        event_name=event_name,
    )
    false_leg = _build_leg(
        provider=false_provider,
        selection="NO",
        implied_probability=false_prob,
        decimal_odds=dec_false,
        stake=stakes[1],
        event_name=event_name,
    )

    providers = sorted(ALLOWED_PROVIDERS)
    links = {
        PROVIDER_KALSHI: _build_provider_link(PROVIDER_KALSHI, event_name),
        PROVIDER_FANATICS: _build_provider_link(PROVIDER_FANATICS, event_name),
    }

    execution_risk = "low" if edge_pct >= 2.0 else "medium"
    expected_profit = DEFAULT_BANKROLL * edge_decimal
    implied_probability_sum = true_prob + false_prob

    best_yes = {
        "provider": true_provider,
        "price": true_prob,
        "decimal_odds": dec_true,
        "stake": stakes[0],
        "link": true_leg.link,
        "selection": true_leg.selection,
    }

    best_no = {
        "provider": false_provider,
        "price": false_prob,
        "decimal_odds": dec_false,
        "stake": stakes[1],
        "link": false_leg.link,
        "selection": false_leg.selection,
    }

    return BinaryArbitrageOpportunity(
        event_id=instrument.instrument_id,
        event_name=event_name,
        market=instrument.predicate or "yes_no",
        edge_pct=edge_pct,
        roi_percentage=edge_pct,
        implied_probability_sum=implied_probability_sum,
        providers=providers,
        legs=[true_leg, false_leg],
        links=links,
        best_yes=best_yes,
        best_no=best_no,
        recommended_side="yes" if true_provider == PROVIDER_KALSHI else "no",
        execution_risk=execution_risk,
        expected_profit=expected_profit,
        yes_quotes={
            PROVIDER_KALSHI: true_leg.implied_probability if true_provider == PROVIDER_KALSHI else instrument.outcomes.get("true", {}).get(PROVIDER_KALSHI, 0.0),
            PROVIDER_FANATICS: true_leg.implied_probability if true_provider == PROVIDER_FANATICS else instrument.outcomes.get("true", {}).get(PROVIDER_FANATICS, 0.0),
        },
        no_quotes={
            PROVIDER_KALSHI: false_leg.implied_probability if false_provider == PROVIDER_KALSHI else instrument.outcomes.get("false", {}).get(PROVIDER_KALSHI, 0.0),
            PROVIDER_FANATICS: false_leg.implied_probability if false_provider == PROVIDER_FANATICS else instrument.outcomes.get("false", {}).get(PROVIDER_FANATICS, 0.0),
        },
    )


def _better_opportunity(
    instrument: Instrument,
    min_edge_pct: float,
) -> Optional[BinaryArbitrageOpportunity]:
    candidates: List[BinaryArbitrageOpportunity] = []

    true_quotes = instrument.outcomes.get("true", {})
    false_quotes = instrument.outcomes.get("false", {})

    for true_provider, false_provider in [
        (PROVIDER_KALSHI, PROVIDER_FANATICS),
        (PROVIDER_FANATICS, PROVIDER_KALSHI),
    ]:
        true_prob = true_quotes.get(true_provider)
        false_prob = false_quotes.get(false_provider)
        if true_prob is None or false_prob is None:
            continue

        maybe_opportunity = _evaluate_combo(
            instrument=instrument,
            true_provider=true_provider,
            false_provider=false_provider,
            true_prob=true_prob,
            false_prob=false_prob,
            min_edge_pct=min_edge_pct,
        )
        if maybe_opportunity:
            candidates.append(maybe_opportunity)

    if not candidates:
        return None

    candidates.sort(key=lambda opp: opp.edge_pct, reverse=True)
    return candidates[0]


def find_arb_opportunities(
    instruments: Iterable[Instrument],
    min_edge_pct: float,
) -> List[BinaryArbitrageOpportunity]:
    """Return Kalshi ↔ Fanatics binary opportunities that meet the edge threshold."""

    opportunities: List[BinaryArbitrageOpportunity] = []
    for instrument in instruments:
        if not is_arb_candidate(instrument):
            continue
        opp = _better_opportunity(instrument, min_edge_pct)
        if opp:
            opportunities.append(opp)

    opportunities.sort(key=lambda o: o.edge_pct, reverse=True)
    return opportunities