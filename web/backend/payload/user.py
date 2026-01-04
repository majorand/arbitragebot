"""User payload schemas used by the backend API."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, EmailStr


class UserPayload(BaseModel):
	user_id: str
	email: Optional[EmailStr] = None
	name: Optional[str] = None


__all__ = ["UserPayload"]
