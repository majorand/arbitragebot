"""Backend configuration utilities."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import List


@dataclass
class BackendConfig:
	supabase_url: str
	supabase_key: str
	kalshi_api: str
	kalshi_api_key: str
	frontend_origins: List[str]
	trading_mode: str


def load_config() -> BackendConfig:
	return BackendConfig(
		supabase_url=os.getenv("SUPABASE_URL", ""),
		supabase_key=os.getenv("SUPABASE_KEY", ""),
		kalshi_api=os.getenv("KALSHI_API", "https://api.kalshi.com"),
		kalshi_api_key=os.getenv("KALSHI_API_KEY", ""),
		frontend_origins=[
			origin.strip()
			for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:3000").split(",")
			if origin.strip()
		],
		trading_mode=os.getenv("TRADING_MODE", "paper"),
	)
