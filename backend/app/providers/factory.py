from __future__ import annotations

from app.providers.base import PaymentProvider
from app.providers.phonepe import PhonePeProvider


def get_payment_provider(name: str) -> PaymentProvider:
    normalized = (name or "phonepe").strip().lower()
    if normalized == "phonepe":
        return PhonePeProvider()
    raise ValueError(f"Unsupported payment provider: {name}")
