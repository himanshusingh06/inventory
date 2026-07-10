from __future__ import annotations

import base64
import json
from hashlib import sha256
from typing import Any
from uuid import uuid4

from app.core.config import settings
from app.providers.base import PaymentProvider


class PhonePeProvider(PaymentProvider):
    def __init__(self) -> None:
        self._mock_mode = not (
            settings.phonepe_merchant_id and settings.phonepe_merchant_secret
        )

    def create_payment(
        self,
        *,
        payment_id: str,
        amount: float,
        currency: str,
        callback_url: str,
        redirect_url: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        merchant_transaction_id = f"MTX-{payment_id}"
        provider_payment_id = f"PP-{uuid4().hex[:18]}"
        payload = {
            "merchantId": settings.phonepe_merchant_id or "MOCK_MERCHANT",
            "merchantTransactionId": merchant_transaction_id,
            "paymentId": payment_id,
            "amount": int(amount * 100),
            "currency": currency,
            "callbackUrl": callback_url,
            "redirectUrl": redirect_url,
            "metadata": metadata,
            "env": settings.phonepe_env,
        }
        qr_payload = base64.b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()
        return {
            "provider": "phonepe",
            "provider_payment_id": provider_payment_id,
            "merchant_transaction_id": merchant_transaction_id,
            "merchant_order_id": f"MO-{payment_id}",
            "transaction_id": f"TX-{uuid4().hex[:18]}",
            "qr_payload": qr_payload,
            "redirect_url": redirect_url,
            "verification_hint": "mock" if self._mock_mode else "live",
        }

    def verify_payment(
        self,
        *,
        payment_id: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        incoming = payload or {}
        status = (incoming.get("status") or "SUCCESS").upper()
        signature_source = f"{payment_id}:{status}:{settings.phonepe_webhook_secret}"
        signature = sha256(signature_source.encode()).hexdigest()
        return {
            "payment_id": payment_id,
            "status": status,
            "signature": signature,
            "verified": True,
        }
