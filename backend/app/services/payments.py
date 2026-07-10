from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models import (
    Customer,
    Invoice,
    InvoiceItem,
    LedgerEntry,
    Payment,
    PaymentAttempt,
    PaymentStatusHistory,
    Product,
    Refund,
    Store,
    WebhookLog,
)
from app.providers.factory import get_payment_provider


def _invoice_number() -> str:
    return f"INV-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"


def _payment_ref() -> str:
    return f"PAY-{uuid.uuid4().hex[:12].upper()}"


def _refund_ref() -> str:
    return f"REF-{uuid.uuid4().hex[:12].upper()}"


def _add_status_history(
    db: Session,
    *,
    payment: Payment,
    old_status: str,
    new_status: str,
    source: str,
    notes: str = "",
) -> None:
    if old_status == new_status:
        return
    db.add(
        PaymentStatusHistory(
            payment_id=payment.id,
            old_status=old_status,
            new_status=new_status,
            source=source,
            notes=notes,
        )
    )


def _post_ledger(
    db: Session,
    *,
    invoice_id: int | None,
    payment_id: int | None,
    refund_id: int | None,
    ledger_name: str,
    entry_type: str,
    amount: float,
    narration: str,
) -> None:
    db.add(
        LedgerEntry(
            invoice_id=invoice_id,
            payment_id=payment_id,
            refund_id=refund_id,
            ledger_name=ledger_name,
            entry_type=entry_type,
            amount=round(amount, 2),
            narration=narration,
        )
    )


def _post_success_ledgers(db: Session, *, invoice: Invoice, payment: Payment) -> None:
    payment_ledger = "Cash Ledger" if payment.payment_method.lower() == "cash" else "UPI Ledger"
    _post_ledger(
        db,
        invoice_id=invoice.id,
        payment_id=payment.id,
        refund_id=None,
        ledger_name=payment_ledger,
        entry_type="Debit",
        amount=payment.amount,
        narration=f"Payment collected for {invoice.invoice_number}",
    )
    _post_ledger(
        db,
        invoice_id=invoice.id,
        payment_id=payment.id,
        refund_id=None,
        ledger_name="Sales Ledger",
        entry_type="Credit",
        amount=max(0.0, payment.amount - invoice.tax_amount),
        narration=f"Sales recognized for {invoice.invoice_number}",
    )
    if invoice.tax_amount > 0:
        _post_ledger(
            db,
            invoice_id=invoice.id,
            payment_id=payment.id,
            refund_id=None,
            ledger_name="GST Ledger",
            entry_type="Credit",
            amount=invoice.tax_amount,
            narration=f"GST recognized for {invoice.invoice_number}",
        )
    _post_ledger(
        db,
        invoice_id=invoice.id,
        payment_id=payment.id,
        refund_id=None,
        ledger_name="Customer Ledger",
        entry_type="Credit",
        amount=payment.amount,
        narration=f"Customer balance reduced for {invoice.invoice_number}",
    )


def create_invoice(db: Session, *, store_id: int, customer_id: int, items: list[dict[str, Any]], tax_amount: float = 0.0, discount_amount: float = 0.0) -> Invoice:
    store = db.get(Store, store_id)
    customer = db.get(Customer, customer_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    invoice = Invoice(
        invoice_number=_invoice_number(),
        store_id=store_id,
        customer_id=customer_id,
        tax_amount=tax_amount,
        discount_amount=discount_amount,
        status="Unpaid",
        payment_status="Pending",
    )
    total = 0.0
    for item in items:
        product = db.get(Product, item["product_id"])
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item['product_id']} not found")
        qty = int(item["quantity"])
        if qty > product.stock:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {product.name}. Available: {product.stock}",
            )
        line_total = qty * product.price
        total += line_total
        invoice.items.append(
            InvoiceItem(
                product_id=product.id,
                quantity=qty,
                unit_price=product.price,
                line_total=line_total,
            )
        )
    total = max(0.0, total + tax_amount - discount_amount)
    invoice.total_amount = total
    invoice.remaining_amount = total
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


def list_invoices(db: Session) -> list[Invoice]:
    stmt = select(Invoice).options(
        selectinload(Invoice.items).selectinload(InvoiceItem.product),
        selectinload(Invoice.payments),
    ).order_by(Invoice.created_at.desc())
    return list(db.scalars(stmt).unique().all())


def create_payment_session(
    db: Session,
    *,
    invoice_id: int,
    amount: float,
    payment_method: str,
    provider_name: str,
    remarks: str = "",
    metadata: dict[str, Any] | None = None,
    ip: str = "",
    device: str = "",
    browser: str = "",
) -> dict[str, Any]:
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")
    if amount > invoice.remaining_amount:
        raise HTTPException(status_code=400, detail="Amount exceeds outstanding balance")

    payment = Payment(
        payment_id=_payment_ref(),
        payment_status="Pending",
        payment_method=payment_method,
        amount=amount,
        currency="INR",
        customer_id=invoice.customer_id,
        invoice_id=invoice.id,
        store_id=invoice.store_id,
        sale_id="",
        extra_metadata=json.dumps(metadata or {}),
        remarks=remarks,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.payment_expiry_minutes),
    )
    db.add(payment)
    db.flush()

    if payment_method.lower() == "cash":
        payment.provider = "cash"
        payment.provider_payment_id = f"CASH-{payment.payment_id}"
        payment.merchant_transaction_id = f"CASH-MTX-{payment.payment_id}"
        payment.merchant_order_id = f"CASH-MO-{payment.payment_id}"
        payment.transaction_id = f"CASH-TX-{payment.payment_id}"
        apply_payment_status(db, payment=payment, status="SUCCESS", webhook=False)
        attempt = PaymentAttempt(
            payment_id=payment.id,
            attempt_number=1,
            request_payload=json.dumps(
                {
                    "invoice_id": invoice.id,
                    "amount": amount,
                    "payment_method": payment_method,
                    "provider": "cash",
                    "metadata": metadata or {},
                }
            ),
            response_payload=json.dumps({"status": "SUCCESS", "provider": "cash"}),
            response_code="200",
            response_message="Collected in cash",
            ip=ip,
            device=device,
            browser=browser,
        )
        db.add(attempt)
        db.commit()
        db.refresh(payment)
        return {
            "payment": payment,
            "qr_payload": "",
            "redirect_url": "",
            "expiry_minutes": 0,
        }

    try:
        provider = get_payment_provider(provider_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    attempt = PaymentAttempt(
        payment_id=payment.id,
        attempt_number=1,
        request_payload=json.dumps(
            {
                "invoice_id": invoice.id,
                "amount": amount,
                "payment_method": payment_method,
                "provider": provider_name,
                "metadata": metadata or {},
            }
        ),
        ip=ip,
        device=device,
        browser=browser,
    )
    db.add(attempt)

    session = provider.create_payment(
        payment_id=payment.payment_id,
        amount=amount,
        currency="INR",
        callback_url=settings.phonepe_callback_url,
        redirect_url=settings.phonepe_redirect_url,
        metadata=metadata or {},
    )
    payment.provider = session["provider"]
    payment.provider_payment_id = session["provider_payment_id"]
    payment.merchant_transaction_id = session["merchant_transaction_id"]
    payment.merchant_order_id = session["merchant_order_id"]
    payment.transaction_id = session["transaction_id"]
    attempt.response_payload = json.dumps(session)
    attempt.response_code = "200"
    attempt.response_message = "Created"
    db.commit()
    db.refresh(payment)
    return {
        "payment": payment,
        "qr_payload": session["qr_payload"],
        "redirect_url": session["redirect_url"],
        "expiry_minutes": settings.payment_expiry_minutes,
    }


def _deduct_inventory(db: Session, invoice: Invoice) -> None:
    if invoice.status == "Paid":
        return
    for item in invoice.items:
        product = db.get(Product, item.product_id)
        if product:
            product.stock = max(0, product.stock - item.quantity)
    invoice.status = "Paid"
    invoice.payment_status = "Success"
    invoice.paid_amount = invoice.total_amount
    invoice.remaining_amount = 0.0
    invoice.receipt_number = invoice.receipt_number or f"RCPT-{invoice.invoice_number}"
    invoice.phonepe_reference = invoice.phonepe_reference or invoice.invoice_number


def apply_payment_status(
    db: Session,
    *,
    payment: Payment,
    status: str,
    provider_payment_id: str | None = None,
    transaction_id: str | None = None,
    merchant_transaction_id: str | None = None,
    merchant_order_id: str | None = None,
    webhook: bool = False,
) -> Payment:
    normalized = status.upper()
    old_status = payment.payment_status
    payment.payment_status = normalized
    payment.webhook_received = payment.webhook_received or webhook
    payment.callback_received = payment.callback_received or not webhook
    if provider_payment_id:
        payment.provider_payment_id = provider_payment_id
    if transaction_id:
        payment.transaction_id = transaction_id
    if merchant_transaction_id:
        payment.merchant_transaction_id = merchant_transaction_id
    if merchant_order_id:
        payment.merchant_order_id = merchant_order_id
    if normalized in {"SUCCESS", "COMPLETED"} and payment.completed_at is None:
        payment.completed_at = datetime.utcnow()
        invoice = db.get(Invoice, payment.invoice_id)
        if invoice:
            invoice.paid_amount = min(invoice.total_amount, invoice.paid_amount + payment.amount)
            invoice.remaining_amount = max(0.0, invoice.total_amount - invoice.paid_amount)
            _post_success_ledgers(db, invoice=invoice, payment=payment)
            if invoice.remaining_amount <= 0 and invoice.status != "Paid":
                _deduct_inventory(db, invoice)
            elif invoice.remaining_amount > 0:
                invoice.status = "Partially Paid"
                invoice.payment_status = "Partial"
    elif normalized in {"FAILED", "CANCELLED", "EXPIRED"}:
        invoice = db.get(Invoice, payment.invoice_id)
        if invoice and invoice.status == "Draft":
            invoice.status = "Unpaid"
            invoice.payment_status = "Failed" if normalized == "FAILED" else normalized.title()
        if invoice and invoice.remaining_amount > 0:
            invoice.payment_status = normalized.title()
    _add_status_history(
        db,
        payment=payment,
        old_status=old_status,
        new_status=normalized,
        source="webhook" if webhook else "api",
    )
    db.commit()
    db.refresh(payment)
    return payment


def log_webhook(db: Session, *, payment: Payment, headers: dict[str, str], payload: dict[str, Any], verification_status: str, processing_status: str, response: dict[str, Any], retry_count: int = 0) -> WebhookLog:
    record = WebhookLog(
        payment_id=payment.id,
        headers=json.dumps(headers),
        payload=json.dumps(payload),
        verification_status=verification_status,
        processing_status=processing_status,
        retry_count=retry_count,
        response=json.dumps(response),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def dashboard_summary(db: Session) -> dict[str, Any]:
    today = datetime.utcnow().date()
    start = datetime.combine(today, datetime.min.time())
    payments = db.scalars(select(Payment)).all()
    successful = [p for p in payments if p.payment_status.upper() in {"SUCCESS", "COMPLETED"}]
    durations = [
        (p.completed_at - p.initiated_at).total_seconds()
        for p in successful
        if p.completed_at
    ]
    phonepe_collections = sum(p.amount for p in successful if p.provider == "phonepe")
    cash_collections = sum(p.amount for p in successful if p.payment_method.lower() == "cash")
    today_collections = sum(
        p.amount for p in successful if p.completed_at and p.completed_at >= start
    )
    total_nonfailed = len([p for p in payments if p.payment_status.upper() not in {"FAILED", "CANCELLED", "EXPIRED"}])
    success_rate = (len(successful) / total_nonfailed * 100.0) if total_nonfailed else 0.0
    return {
        "today_collections": round(today_collections, 2),
        "phonepe_collections": round(phonepe_collections, 2),
        "cash_collections": round(cash_collections, 2),
        "pending_payments": len([p for p in payments if p.payment_status.upper() == "PENDING"]),
        "failed_payments": len([p for p in payments if p.payment_status.upper() in {"FAILED", "CANCELLED", "EXPIRED"}]),
        "refunds": 0,
        "payment_success_rate": round(success_rate, 2),
        "average_payment_time_seconds": round(sum(durations) / len(durations), 2) if durations else 0.0,
        "invoice_count": db.scalar(select(func.count(Invoice.id))) or 0,
        "product_count": db.scalar(select(func.count(Product.id))) or 0,
        "customer_count": db.scalar(select(func.count(Customer.id))) or 0,
        "partially_paid_invoices": db.scalar(
            select(func.count(Invoice.id)).where(Invoice.status == "Partially Paid")
        ) or 0,
        "expired_payments": len([p for p in payments if p.payment_status.upper() == "EXPIRED"]),
    }


def expire_pending_payments(db: Session) -> int:
    now = datetime.utcnow()
    pending = db.scalars(
        select(Payment).where(Payment.payment_status == "Pending", Payment.expires_at <= now)
    ).all()
    for payment in pending:
        apply_payment_status(db, payment=payment, status="EXPIRED", webhook=False)
    return len(pending)


def request_refund(
    db: Session,
    *,
    payment_id: str,
    amount: float,
    reason: str,
    requested_by: str,
) -> Refund:
    payment = db.scalars(select(Payment).where(Payment.payment_id == payment_id)).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.payment_status.upper() not in {"SUCCESS", "COMPLETED", "PARTIALLY REFUNDED"}:
        raise HTTPException(status_code=400, detail="Only successful payments can be refunded")
    refunded_amount = db.scalar(
        select(func.coalesce(func.sum(Refund.amount), 0.0)).where(
            Refund.payment_id == payment.id,
            Refund.status.in_(["Approved", "Processed"]),
        )
    ) or 0.0
    if amount > payment.amount - refunded_amount:
        raise HTTPException(status_code=400, detail="Refund amount exceeds refundable balance")
    refund = Refund(
        payment_id=payment.id,
        refund_id=_refund_ref(),
        amount=amount,
        reason=reason,
        requested_by=requested_by,
        status="Pending Approval",
    )
    db.add(refund)
    db.commit()
    db.refresh(refund)
    return refund


def approve_refund(db: Session, *, refund_id: str, approved_by: str) -> Refund:
    refund = db.scalars(select(Refund).where(Refund.refund_id == refund_id)).first()
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found")
    if refund.status not in {"Pending Approval", "Approved"}:
        return refund
    payment = db.get(Payment, refund.payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    invoice = db.get(Invoice, payment.invoice_id)
    refund.status = "Processed"
    refund.approved_by = approved_by
    refund.provider_refund_id = f"PR-{refund.refund_id}"
    refund.processed_at = datetime.utcnow()
    payment.payment_status = "REFUNDED" if refund.amount >= payment.amount else "PARTIALLY REFUNDED"
    if invoice:
        invoice.paid_amount = max(0.0, invoice.paid_amount - refund.amount)
        invoice.remaining_amount = max(0.0, invoice.total_amount - invoice.paid_amount)
        invoice.payment_status = "Refunded" if invoice.paid_amount == 0 else "Partially Refunded"
        invoice.status = "Refunded" if invoice.paid_amount == 0 else "Partially Paid"
        _post_ledger(
            db,
            invoice_id=invoice.id,
            payment_id=payment.id,
            refund_id=refund.id,
            ledger_name="Customer Ledger",
            entry_type="Debit",
            amount=refund.amount,
            narration=f"Refund issued for {invoice.invoice_number}",
        )
        _post_ledger(
            db,
            invoice_id=invoice.id,
            payment_id=payment.id,
            refund_id=refund.id,
            ledger_name="Sales Returns Ledger",
            entry_type="Debit",
            amount=refund.amount,
            narration=f"Sales return for {invoice.invoice_number}",
        )
    _add_status_history(
        db,
        payment=payment,
        old_status="SUCCESS",
        new_status=payment.payment_status,
        source="refund",
        notes=refund.refund_id,
    )
    db.commit()
    db.refresh(refund)
    return refund


def list_refunds(db: Session) -> list[Refund]:
    return list(db.scalars(select(Refund).order_by(Refund.created_at.desc())).all())


def list_ledgers(db: Session) -> list[LedgerEntry]:
    return list(db.scalars(select(LedgerEntry).order_by(LedgerEntry.posted_at.desc())).all())


def report_summary(db: Session) -> dict[str, Any]:
    payments = db.scalars(select(Payment)).all()
    invoices = db.scalars(select(Invoice).options(selectinload(Invoice.store))).all()
    refunds = db.scalars(select(Refund)).all()
    collections_by_method: dict[str, float] = {}
    for payment in payments:
        if payment.payment_status.upper() in {"SUCCESS", "COMPLETED"}:
            collections_by_method[payment.payment_method] = round(
                collections_by_method.get(payment.payment_method, 0.0) + payment.amount,
                2,
            )
    store_wise_sales: dict[str, float] = {}
    for invoice in invoices:
        store_name = invoice.store.name if invoice.store else str(invoice.store_id)
        store_wise_sales[store_name] = round(
            store_wise_sales.get(store_name, 0.0) + invoice.paid_amount,
            2,
        )
    pending_amount = sum(invoice.remaining_amount for invoice in invoices if invoice.remaining_amount > 0)
    failed_amount = sum(
        payment.amount
        for payment in payments
        if payment.payment_status.upper() in {"FAILED", "CANCELLED", "EXPIRED"}
    )
    refund_amount = sum(refund.amount for refund in refunds if refund.status == "Processed")
    return {
        "collections_by_method": collections_by_method,
        "store_wise_sales": store_wise_sales,
        "cashier_wise_collections": {"default": sum(collections_by_method.values())},
        "pending_amount": round(pending_amount, 2),
        "failed_amount": round(failed_amount, 2),
        "refund_amount": round(refund_amount, 2),
        "settlement_summary": {
            "gross_collections": round(sum(collections_by_method.values()), 2),
            "refunds": round(refund_amount, 2),
            "net_settlement": round(sum(collections_by_method.values()) - refund_amount, 2),
        },
    }
