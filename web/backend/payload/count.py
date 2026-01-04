"""Simple count payload schemas."""

from __future__ import annotations

from pydantic import BaseModel


class CountPayload(BaseModel):
	count: int


__all__ = ["CountPayload"]
