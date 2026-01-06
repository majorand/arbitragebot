from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from datetime import datetime
from typing import Iterable, List, Sequence

import requests

from arbitragebot.schemas import NormalizedOdds
from arbitragebot.utils.time import parse_iso_datetime

LOGGER = logging.getLogger(__name__)

# Try to import web3 for Polymarket auth
try:
    from eth_account import Account
    from eth_account.messages import encode_defunct
    HAS_WEB3 = True
except ImportError:
    HAS_WEB3 = False
    LOGGER.warning("eth-account not available - Polymarket auth may not work")


class PolymarketDataSource:
    """Polymarket fetcher with optional Web3 authentication via private key."""

    def __init__(
        self,
        base_url: str | None = None,
        base_urls: Sequence[str] | None = None,
        private_key: str | None = None,
        min_interval_seconds: int = 120,
        limit: int = 200,
        active_only: bool = True,
    ) -> None:
        env_urls = os.getenv("POLYMARKET_BASE_URLS")
        if env_urls:
            configured_urls = [u.strip().rstrip("/") for u in env_urls.split(",") if u.strip()]
        elif base_urls:
            configured_urls = [u.rstrip("/") for u in base_urls if u]
        elif base_url:
            configured_urls = [base_url.rstrip("/")]
        else:
            configured_urls = [
                "https://clob.polymarket.com",  # main CLOB API
                "https://gamma-api.polymarket.com",  # legacy gamma API (resolves reliably)
            ]

        self.base_urls: List[str] = configured_urls
        self.min_interval_seconds = min_interval_seconds
        self.limit = limit
        self.active_only = active_only
        self._last_fetch_ts: float = 0.0
        self._cached: List[NormalizedOdds] = []
        
        # Setup Web3 auth if private key available
        self.account = None
        self.address = None
        private_key_str = private_key or os.getenv("POLYMARKET_PRIVATE_KEY")
        
        if private_key_str and HAS_WEB3:
            try:
                # Ensure private key has 0x prefix
                if not private_key_str.startswith("0x"):
                    private_key_str = "0x" + private_key_str
                self.account = Account.from_key(private_key_str)
                self.address = self.account.address
                LOGGER.info(f"Polymarket authenticated with address: {self.address}")
            except Exception as e:
                LOGGER.warning(f"Failed to setup Polymarket Web3 auth: {e}")
                self.account = None
        elif private_key_str and not HAS_WEB3:
            LOGGER.warning("Polymarket private key available but eth-account not installed")
        else:
            LOGGER.info("No Polymarket private key configured - using public API")

    def _get_auth_headers(self) -> dict:
        """Generate authentication headers if authenticated."""
        if not self.account:
            return {}
        
        # Polymarket uses timestamp-based signatures
        # Sign a challenge message with the account
        try:
            timestamp = int(time.time())
            # Create a challenge message
            challenge = f"polymarket-{timestamp}"
            message = encode_defunct(text=challenge)
            signed = self.account.sign_message(message)
            
            return {
                "X-Signature": signed.signature.hex(),
                "X-Address": self.address,
                "X-Timestamp": str(timestamp),
            }
        except Exception as e:
            LOGGER.debug(f"Failed to sign auth message: {e}")
            return {}

    def _should_skip(self) -> bool:
        return (time.time() - self._last_fetch_ts) < self.min_interval_seconds

    def fetch_markets(self) -> List[NormalizedOdds]:
        if self._should_skip():
            LOGGER.debug("Polymarket: Using cached data (rate limit check)")
            return self._cached

        params = {"limit": self.limit}
        if self.active_only:
            params["active"] = "true"
        
        # Get auth headers if authenticated
        headers = self._get_auth_headers()
        if headers:
            LOGGER.debug(f"Using authenticated Polymarket request from {self.address}")

        payload = None
        last_error: Exception | None = None
        selected_base: str | None = None

        def _extract_markets(obj):
            if isinstance(obj, list):
                return obj
            if isinstance(obj, dict):
                return obj.get("markets") or obj.get("data") or obj.get("results") or []
            return []

        def _is_tradable(m: dict) -> bool:
            # CLOB markets often have inconsistent active/closed/archived flags.
            # The most reliable signal for tradability is accepting_orders and/or enable_order_book.
            if m.get("accepting_orders") is True:
                return True
            if m.get("enable_order_book") is True:
                return True
            return False

        def _filter_active(markets: list[dict]) -> list[dict]:
            if not self.active_only:
                return markets
            filtered: list[dict] = []
            for m in markets:
                # Prefer tradable markets when those fields exist.
                if "accepting_orders" in m or "enable_order_book" in m:
                    if not _is_tradable(m):
                        continue
                    filtered.append(m)
                    continue

                # Fallback for legacy APIs without order-book flags.
                if m.get("archived") is True:
                    continue
                if m.get("closed") is True:
                    continue
                if m.get("active") is False:
                    continue
                filtered.append(m)
            return filtered

        def _paginate_and_filter(url_base: str) -> tuple[object | None, list[dict]]:
            """Fetch pages until we collect enough usable markets or run out."""
            url = f"{url_base}/markets"

            collected: list[dict] = []
            cursor: str | None = None
            max_pages = 50
            pages = 0

            last_payload: object | None = None
            while pages < max_pages and len(collected) < self.limit:
                page_params = dict(params)
                if cursor:
                    page_params["next_cursor"] = cursor

                resp = requests.get(url, params=page_params, headers=headers, timeout=10)
                resp.raise_for_status()
                candidate_payload = resp.json()
                last_payload = candidate_payload

                markets = _extract_markets(candidate_payload)
                usable = _filter_active(list(markets) if markets else [])
                collected.extend(usable)

                # Cursor is only available on dict payloads (CLOB); legacy APIs may return lists.
                if isinstance(candidate_payload, dict):
                    cursor = candidate_payload.get("next_cursor")
                else:
                    cursor = None

                pages += 1
                if not cursor:
                    break

            # De-dup by question_id/condition_id when possible
            deduped: list[dict] = []
            seen: set[str] = set()
            for m in collected:
                key = str(m.get("question_id") or m.get("condition_id") or m.get("id") or m.get("market_slug") or "")
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                deduped.append(m)

            return last_payload, deduped

        for url_base in self.base_urls:
            try:
                LOGGER.debug("Attempting Polymarket fetch from: %s/markets", url_base)
                candidate_payload, usable = _paginate_and_filter(url_base)
                payload = candidate_payload
                selected_base = url_base

                LOGGER.debug(
                    "Polymarket endpoint %s produced %d usable markets after pagination/filtering",
                    url_base,
                    len(usable),
                )

                # Prefer endpoints that actually return usable markets.
                if self.active_only and not usable:
                    last_error = None
                    continue

                # For normalization, use the filtered list directly.
                markets = usable
                LOGGER.info("Polymarket fetch succeeded via %s (authenticated: %s)", url_base, bool(headers))
                break
            except Exception as exc:
                last_error = exc
                LOGGER.warning("Polymarket fetch failed via %s: %s", url_base, exc)

        if payload is None:
            if last_error:
                LOGGER.error("Polymarket fetch failed after trying all base URLs: %s", last_error)
            else:
                LOGGER.warning("Polymarket returned None from all endpoints")
            LOGGER.info("Returning cached Polymarket data: %d markets", len(self._cached))
            return self._cached

        markets = _extract_markets(payload)
        if selected_base is None:
            # If we didn't pick a base URL (e.g. all returned unusable but no exceptions), keep the first payload.
            selected_base = self.base_urls[0] if self.base_urls else "<unknown>"
        
        # Local filter: the remote "active=true" param is not consistently honored across endpoints.
        if self.active_only:
            before = len(markets) if markets else 0
            markets = _filter_active(list(markets) if markets else [])
            LOGGER.info(
                "Polymarket active_only filter: kept %d/%d markets (source=%s)",
                len(markets),
                before,
                selected_base,
            )

        if not markets:
            LOGGER.warning(
                "Polymarket returned empty markets list after filtering. Response keys: %s",
                payload.keys() if isinstance(payload, dict) else "N/A",
            )
        
        LOGGER.debug(f"Polymarket API returned {len(markets) if markets else 0} markets (after extraction)")
        normalized = self._normalize_markets(markets)
        LOGGER.info("Polymarket normalized %d markets", len(normalized))
        self._cached = normalized
        self._last_fetch_ts = time.time()
        return normalized

    def fetch_raw_markets(self) -> List[dict]:
        """Fetch raw market data (not normalized) for use in other pipelines.
        
        Returns:
            List of raw market dictionaries from Polymarket API
        """
        params = {"limit": self.limit}
        if self.active_only:
            params["active"] = "true"
        
        # Get auth headers if authenticated
        headers = self._get_auth_headers()

        payload = None
        last_error: Exception | None = None

        def _extract_markets(obj):
            if isinstance(obj, list):
                return obj
            if isinstance(obj, dict):
                return obj.get("markets") or obj.get("data") or obj.get("results") or []
            return []

        def _is_tradable(m: dict) -> bool:
            if m.get("accepting_orders") is True:
                return True
            if m.get("enable_order_book") is True:
                return True
            return False

        def _filter_active(markets: list[dict]) -> list[dict]:
            if not self.active_only:
                return markets
            filtered: list[dict] = []
            for m in markets:
                if "accepting_orders" in m or "enable_order_book" in m:
                    if not _is_tradable(m):
                        continue
                    filtered.append(m)
                    continue

                if m.get("archived") is True:
                    continue
                if m.get("closed") is True:
                    continue
                if m.get("active") is False:
                    continue
                filtered.append(m)
            return filtered

        def _paginate_and_filter(url_base: str) -> list[dict]:
            url = f"{url_base}/markets"
            collected: list[dict] = []
            cursor: str | None = None
            max_pages = 50
            pages = 0
            while pages < max_pages and len(collected) < self.limit:
                page_params = dict(params)
                if cursor:
                    page_params["next_cursor"] = cursor

                resp = requests.get(url, params=page_params, headers=headers, timeout=10)
                resp.raise_for_status()
                candidate_payload = resp.json()
                markets = _extract_markets(candidate_payload)
                usable = _filter_active(list(markets) if markets else [])
                collected.extend(usable)

                if isinstance(candidate_payload, dict):
                    cursor = candidate_payload.get("next_cursor")
                else:
                    cursor = None
                pages += 1
                if not cursor:
                    break

            deduped: list[dict] = []
            seen: set[str] = set()
            for m in collected:
                key = str(m.get("question_id") or m.get("condition_id") or m.get("id") or m.get("market_slug") or "")
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                deduped.append(m)
            return deduped

        for url_base in self.base_urls:
            try:
                LOGGER.debug("Attempting Polymarket raw fetch from: %s/markets", url_base)
                usable = _paginate_and_filter(url_base)
                LOGGER.debug(
                    "Polymarket raw endpoint %s produced %d usable markets after pagination/filtering",
                    url_base,
                    len(usable),
                )

                if self.active_only and not usable:
                    last_error = None
                    continue

                payload = usable
                LOGGER.debug("Polymarket raw fetch succeeded via %s", url_base)
                break
            except Exception as exc:
                last_error = exc
                LOGGER.warning("Polymarket raw fetch failed via %s: %s", url_base, exc)

        if payload is None:
            if last_error:
                LOGGER.error("Polymarket raw fetch failed after trying all base URLs: %s", last_error)
            return []

        # `payload` is already the filtered list when successful.
        if isinstance(payload, list):
            return payload
        markets = _extract_markets(payload)
        if self.active_only:
            markets = _filter_active(list(markets) if markets else [])
        if not isinstance(markets, list):
            LOGGER.warning(f"Unexpected Polymarket response type after extraction: {type(markets)}")
            return []
        return markets

    def _normalize_markets(self, markets: Iterable[dict]) -> List[NormalizedOdds]:
        normalized: List[NormalizedOdds] = []
        now = datetime.utcnow()
        
        markets_list = list(markets) if markets else []
        LOGGER.debug(f"_normalize_markets called with {len(markets_list)} markets")
        
        if not markets_list:
            LOGGER.warning("Polymarket markets list is empty")
            return normalized

        # Log structure of first market to understand field names
        if markets_list:
            first_market = markets_list[0]
            LOGGER.info(f"First Polymarket market keys: {list(first_market.keys())}")
            if "tokens" in first_market and first_market["tokens"]:
                LOGGER.info(f"Sample token structure: {first_market['tokens'][0] if isinstance(first_market['tokens'], list) else first_market['tokens']}")

        for idx, mkt in enumerate(markets_list):
            try:
                # Polymarket uses question_id or condition_id as event ID
                event_id = str(mkt.get("question_id") or mkt.get("condition_id") or mkt.get("id") or "").strip()
                
                # If still no ID, skip
                if not event_id:
                    continue

                # Try multiple field names for title - question is most common
                title = (mkt.get("question") or mkt.get("title") or mkt.get("market_slug") or 
                        mkt.get("description") or event_id)
                
                # Parse teams from title for proper event labeling
                # Polymarket titles are like "DET @ CHI" or "Lions vs Bears"
                home_parsed, away_parsed = self._parse_teams_from_title(title)
                
                # Polymarket uses end_date_iso for end date
                start_time_raw = (mkt.get("end_date_iso") or mkt.get("endDate") or 
                                 mkt.get("game_start_time") or mkt.get("end_date"))
                start_time = parse_iso_datetime(start_time_raw) if start_time_raw else now
                
                # Category/sport - use tags if available
                tags = mkt.get("tags") or []
                if isinstance(tags, list) and tags:
                    category = tags[0]
                else:
                    category = mkt.get("category") or "polymarket"

                # Polymarket stores outcomes in 'tokens' field
                # tokens is typically a list of token objects with price info
                tokens = mkt.get("tokens") or []
                
                if not tokens:
                    continue
                
                # Process each token (outcome)
                for token in tokens:
                    if not isinstance(token, dict):
                        continue
                    
                    try:
                        # Token fields: 'ticker', 'outcome', 'price', etc.
                        token_name = token.get("ticker") or token.get("outcome") or token.get("name") or ""
                        token_price = token.get("price") or token.get("probability") or 0.0
                        
                        # Skip invalid outcomes
                        if not token_name:
                            continue
                        
                        # Parse price if it's a string
                        try:
                            price_float = float(token_price)
                            # Normalize: if > 1, it's in cents; if < 1, it's already decimal
                            if price_float > 1:
                                price_float = price_float / 100
                            # Clamp to valid probability range
                            price_float = min(max(price_float, 0.01), 0.99)
                        except (TypeError, ValueError):
                            continue
                        
                        normalized.append(
                            NormalizedOdds(
                                sport=str(category)[:50],
                                league="polymarket",
                                event_id=event_id[:100],
                                event_name=str(title)[:200],
                                start_time=start_time,
                                home_team=str(home_parsed or token_name)[:100],
                                away_team=str(away_parsed or "")[:100],
                                market_type="binary",
                                selection=str(token_name).lower()[:50],
                                price=float(price_float),
                                implied_probability=float(price_float),
                                source="polymarket",
                                last_updated=now,
                                american_odds=None,
                            )
                        )
                    except Exception as e:
                        if idx < 3:
                            LOGGER.debug(f"Error processing token in market {idx}: {e}")
                        continue
                        
            except Exception as exc:
                if idx < 3:  # Only log first few errors
                    LOGGER.debug(f"Error normalizing Polymarket market at index {idx}: {exc}")
                continue

        LOGGER.info(f"Polymarket _normalize_markets: input {len(markets_list)} markets, output {len(normalized)} normalized odds")
        if len(normalized) == 0 and markets_list:
            LOGGER.warning(f"No markets normalized! First market tokens: {markets_list[0].get('tokens', 'N/A')}")
        return normalized

    def _parse_teams_from_title(self, title: str) -> tuple[str, str]:
        """Parse team names from Polymarket title.
        
        Examples:
            "DET @ CHI" -> ("CHI", "DET")  # home @ away format
            "Lions vs Bears" -> ("Lions", "Bears")
            "Will the Lions win?" -> ("Lions", "")
        
        Returns:
            Tuple of (home_team, away_team)
        """
        if not title:
            return ("", "")
        
        # Try "X @ Y" pattern (away @ home)
        at_match = re.search(r"(\w+)\s*@\s*(\w+)", title, re.IGNORECASE)
        if at_match:
            return (at_match.group(2), at_match.group(1))  # home, away
        
        # Try "X vs Y" pattern
        vs_match = re.search(r"(\w+)\s+vs\.?\s+(\w+)", title, re.IGNORECASE)
        if vs_match:
            return (vs_match.group(1), vs_match.group(2))
        
        # Try "Will X" or "Does X" pattern
        will_match = re.search(r"(?:Will|Does|Can)\s+(?:the\s+)?(\w+)", title, re.IGNORECASE)
        if will_match:
            return (will_match.group(1), "")
        
        return ("", "")
