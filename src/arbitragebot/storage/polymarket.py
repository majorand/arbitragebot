"""Deprecated storage shim retained for compatibility.

Use `arbitragebot.storage.kalshi` instead. This module forwards common
helpers to the Kalshi-specific implementation so older imports keep
working.
"""

from __future__ import annotations

from .kalshi import (
    save_kalshi_markets_to_file as save_markets_to_file,
    upsert_kalshi_markets_to_supabase as upsert_markets_to_supabase,
    serialize_order,
)

__all__ = [
    "save_markets_to_file",
    "upsert_markets_to_supabase",
    "serialize_order",
]