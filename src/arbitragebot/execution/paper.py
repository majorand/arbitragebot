from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

from arbitragebot.schemas import OrderRequest, OrderResult

LOGGER = logging.getLogger(__name__)


@dataclass
class PaperFill:
    order: OrderRequest
    filled_price: float
    filled_size: float
    timestamp: datetime


class PaperTradingEngine:
    def __init__(self) -> None:
        self.fills: List[PaperFill] = []
        self.positions: Dict[str, float] = {}
        self.cash_balance: float = 0.0

    def submit_order(self, order: OrderRequest, reference_price: float) -> OrderResult:
        filled_price = reference_price if order.order_type == "market" else order.price
        filled_size = order.size
        self.fills.append(
            PaperFill(
                order=order,
                filled_price=filled_price,
                filled_size=filled_size,
                timestamp=datetime.utcnow(),
            )
        )
        self.positions[order.market_id] = self.positions.get(order.market_id, 0.0) + (
            filled_size if order.side == "buy" else -filled_size
        )
        self.cash_balance -= filled_price * filled_size
        LOGGER.info("Paper trade executed for %s", order.market_id)
        return OrderResult(
            success=True,
            order_id=f"paper-{len(self.fills)}",
            status="filled",
        )