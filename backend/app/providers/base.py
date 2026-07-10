from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class PaymentProvider(ABC):
    @abstractmethod
    def create_payment(self, *, payment_id: str, amount: float, currency: str, callback_url: str, redirect_url: str, metadata: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def verify_payment(self, *, payment_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        raise NotImplementedError


def utc_now() -> datetime:
    return datetime.utcnow()
