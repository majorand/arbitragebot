from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, List

from arbitragebot.schemas import NormalizedOdds, OrderRequest


class Strategy(ABC):
    @abstractmethod
    def generate_orders(
        self, market_data: Iterable[NormalizedOdds]
    ) -> List[OrderRequest]:
        raise NotImplementedError