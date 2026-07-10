from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_permission
from app.db import get_db
from app.models import Invoice, User
from app.schemas import InvoiceCreate, InvoiceRead
from app.services.payments import create_invoice, list_invoices

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


def _serialize_invoice(invoice: Invoice) -> InvoiceRead:
    return InvoiceRead(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        store_id=invoice.store_id,
        customer_id=invoice.customer_id,
        total_amount=invoice.total_amount,
        tax_amount=invoice.tax_amount,
        discount_amount=invoice.discount_amount,
        paid_amount=invoice.paid_amount,
        remaining_amount=invoice.remaining_amount,
        status=invoice.status,
        payment_status=invoice.payment_status,
        receipt_number=invoice.receipt_number,
        phonepe_reference=invoice.phonepe_reference,
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
        items=[
            {
                "id": item.id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "line_total": item.line_total,
                "product_name": item.product.name if item.product else "",
            }
            for item in invoice.items
        ],
        payments=[
            {
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
            }
            for payment in invoice.payments
        ],
    )


@router.get("", response_model=list[InvoiceRead])
def get_invoices(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("billing:read")),
):
    return [_serialize_invoice(invoice) for invoice in list_invoices(db)]


@router.post("", response_model=InvoiceRead)
def create(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("billing:write")),
):
    invoice = create_invoice(
        db,
        store_id=payload.store_id,
        customer_id=payload.customer_id,
        items=[item.model_dump() for item in payload.items],
        tax_amount=payload.tax_amount,
        discount_amount=payload.discount_amount,
    )
    if not invoice:
        raise HTTPException(status_code=500, detail="Invoice creation failed")
    db.refresh(invoice)
    return _serialize_invoice(invoice)
