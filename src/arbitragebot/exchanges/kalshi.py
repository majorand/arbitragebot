from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Optional

from arbitragebot.schemas import OrderRequest, OrderResult
from arbitragebot.utils.http import build_session, request_json

LOGGER = logging.getLogger(__name__)


class KalshiTradingClient:
    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = build_session()

    def _request(self, method: str, path: str, payload: Optional[dict] = None) -> dict:
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None
        return request_json(self.session, method, url, headers=headers, payload=payload)

    def fetch_order_book(self, market_id: str) -> dict:
        return self._request("GET", f"markets/{market_id}/orderbook")

    def place_order(self, order: OrderRequest) -> OrderResult:
        payload = asdict(order)
        response = self._request("POST", "orders", payload=payload)
        return OrderResult(
            success=response.get("success", False),
            order_id=response.get("order_id"),
            status=response.get("status", "unknown"),
            message=response.get("message"),
        )
