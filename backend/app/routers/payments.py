from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth import require_permission
from app.db import get_db
from app.models import Payment, User
from app.schemas import (
    DashboardSummary,
    LedgerEntryRead,
    PaymentCreate,
    PaymentSessionRead,
    PaymentWebhookPayload,
    RefundApprove,
    RefundCreate,
    RefundRead,
    ReportSummary,
)
from app.services.payments import (
    apply_payment_status,
    create_payment_session,
    dashboard_summary,
    expire_pending_payments,
    list_ledgers,
    list_refunds,
    log_webhook,
    approve_refund,
    report_summary,
    request_refund,
)
from app.providers.factory import get_payment_provider

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.get("/options")
def options(_: User = Depends(require_permission("payments:read"))):
    return {
        "providers": [
            {
                "name": "phonepe",
                "methods": [
                    "PhonePe UPI",
                    "UPI QR",
                    "UPI Intent",
                    "UPI Collect",
                    "Credit Card",
                    "Debit Card",
                    "Net Banking",
                    "Wallet",
                    "Cash",
                ],
            }
        ]
    }


@router.get("/dashboard", response_model=DashboardSummary)
def summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("reports:read")),
):
    return dashboard_summary(db)


@router.post("/create-session", response_model=PaymentSessionRead)
def create_session(
    payload: PaymentCreate,
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("payments:write")),
):
    session = create_payment_session(
        db,
        invoice_id=payload.invoice_id,
        amount=payload.amount,
        payment_method=payload.payment_method,
        provider_name=payload.provider,
        remarks=payload.remarks,
        metadata=payload.metadata,
        ip=request.client.host if request.client else "",
        device=request.headers.get("user-agent", ""),
        browser=request.headers.get("user-agent", ""),
    )
    payment = session["payment"]
    return PaymentSessionRead(
        payment={
            "id": payment.id,
            "payment_id": payment.payment_id,
            "payment_status": payment.payment_status,
            "payment_method": payment.payment_method,
            "amount": payment.amount,
            "currency": payment.currency,
            "expires_at": payment.expires_at,
            "callback_received": payment.callback_received,
            "webhook_received": payment.webhook_received,
            "provider_payment_id": payment.provider_payment_id,
            "merchant_transaction_id": payment.merchant_transaction_id,
            "transaction_id": payment.transaction_id,
            "completed_at": payment.completed_at,
        },
        qr_payload=session["qr_payload"],
        redirect_url=session["redirect_url"],
        expiry_minutes=session["expiry_minutes"],
    )


@router.post("/expire")
def expire(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("payments:write")),
):
    return {"expired": expire_pending_payments(db)}


@router.get("/refunds", response_model=list[RefundRead])
def refunds(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("payments:read")),
):
    return list_refunds(db)


@router.post("/refunds", response_model=RefundRead)
def create_refund(
    payload: RefundCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("payments:write")),
):
    return request_refund(
        db,
        payment_id=payload.payment_id,
        amount=payload.amount,
        reason=payload.reason,
        requested_by=payload.requested_by,
    )


@router.post("/refunds/{refund_id}/approve", response_model=RefundRead)
def approve(
    refund_id: str,
    payload: RefundApprove,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("payments:write")),
):
    return approve_refund(db, refund_id=refund_id, approved_by=payload.approved_by)


@router.get("/ledgers", response_model=list[LedgerEntryRead])
def ledgers(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("reports:read")),
):
    return list_ledgers(db)


@router.get("/reports", response_model=ReportSummary)
def reports(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("reports:read")),
):
    return report_summary(db)


@router.get("/{payment_id}")
def get_payment(
    payment_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("payments:read")),
):
    payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return {
        "payment_id": payment.payment_id,
        "payment_status": payment.payment_status,
        "payment_method": payment.payment_method,
        "amount": payment.amount,
        "currency": payment.currency,
        "expires_at": payment.expires_at,
        "callback_received": payment.callback_received,
        "webhook_received": payment.webhook_received,
        "provider_payment_id": payment.provider_payment_id,
        "merchant_transaction_id": payment.merchant_transaction_id,
        "transaction_id": payment.transaction_id,
        "completed_at": payment.completed_at,
        "invoice_id": payment.invoice_id,
        "remarks": payment.remarks,
    }


@router.post("/{payment_id}/simulate")
def simulate(
    payment_id: str,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("payments:write")),
):
    payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    status = (payload.get("status") or "SUCCESS").upper()
    updated = apply_payment_status(
        db,
        payment=payment,
        status=status,
        provider_payment_id=payload.get("provider_payment_id"),
        transaction_id=payload.get("transaction_id"),
        merchant_transaction_id=payload.get("merchant_transaction_id"),
        merchant_order_id=payload.get("merchant_order_id"),
        webhook=False,
    )
    log_webhook(
        db,
        payment=updated,
        headers={"x-simulated": "true"},
        payload=payload,
        verification_status="Verified",
        processing_status="Processed",
        response={"ok": True},
    )
    return {"ok": True, "payment_status": updated.payment_status}


@router.post("/phonepe/callback")
async def phonepe_callback(
    request: Request,
    x_phonepe_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    body = await request.json()
    payload = PaymentWebhookPayload.model_validate(body)
    payment = db.query(Payment).filter(Payment.payment_id == payload.payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    verification = get_payment_provider("phonepe").verify_payment(
        payment_id=payload.payment_id, payload=payload.payload | {"status": payload.status}
    )
    if x_phonepe_signature and verification["signature"] != x_phonepe_signature:
        log_webhook(
            db,
            payment=payment,
            headers=dict(request.headers),
            payload=body,
            verification_status="Failed",
            processing_status="Rejected",
            response={"error": "invalid signature"},
        )
        raise HTTPException(status_code=401, detail="Invalid signature")

    updated = apply_payment_status(
        db,
        payment=payment,
        status=payload.status,
        provider_payment_id=payload.provider_payment_id,
        transaction_id=payload.transaction_id,
        merchant_transaction_id=payload.merchant_transaction_id,
        merchant_order_id=payload.merchant_order_id,
        webhook=True,
    )
    log_webhook(
        db,
        payment=updated,
        headers=dict(request.headers),
        payload=body,
        verification_status="Verified",
        processing_status="Processed",
        response={"payment_status": updated.payment_status},
    )
    return {"ok": True, "payment_status": updated.payment_status}
