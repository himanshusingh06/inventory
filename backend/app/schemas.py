from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StoreCreate(BaseModel):
    name: str
    code: str
    address: str = ""


class StoreRead(StoreCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)


class CustomerCreate(BaseModel):
    name: str
    phone: str = ""
    email: str = ""


class CustomerRead(CustomerCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    store_id: int
    name: str
    sku: str
    price: float = 0.0
    stock: int = 0
    reorder_level: int = 5
    aisle: str = ""
    rack: str = ""
    shelf: str = ""
    bin: str = ""
    location_code: str = ""
    category: str = ""
    barcode: str = ""


class ProductRead(ProductCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)


class StockAdjust(BaseModel):
    quantity: int
    movement_type: Literal["receive", "adjust", "damage", "transfer_in", "transfer_out"] = "adjust"
    notes: str = ""


class StockMovementRead(BaseModel):
    id: int
    product_id: int
    store_id: int
    movement_type: str
    quantity: int
    before_quantity: int
    after_quantity: int
    reference: str
    notes: str
    performed_by: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserRead(BaseModel):
    id: int
    store_id: int | None
    name: str
    email: str
    role: str
    active: bool

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    store_id: int | None = None
    name: str
    email: str
    password: str = Field(min_length=6)
    role: Literal["super_admin", "store_manager", "inventory_manager", "cashier", "accountant", "viewer"] = "viewer"
    active: bool = True


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: UserRead


class InvoiceItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class InvoiceCreate(BaseModel):
    store_id: int
    customer_id: int
    items: list[InvoiceItemCreate]
    tax_amount: float = 0.0
    discount_amount: float = 0.0


class InvoiceItemRead(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: float
    line_total: float
    product_name: str

    model_config = ConfigDict(from_attributes=True)


class PaymentRead(BaseModel):
    id: int
    payment_id: str
    payment_status: str
    payment_method: str
    amount: float
    currency: str
    expires_at: datetime | None
    callback_received: bool
    webhook_received: bool
    provider_payment_id: str
    merchant_transaction_id: str
    transaction_id: str
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class InvoiceRead(BaseModel):
    id: int
    invoice_number: str
    store_id: int
    customer_id: int
    total_amount: float
    tax_amount: float
    discount_amount: float
    paid_amount: float
    remaining_amount: float
    status: str
    payment_status: str
    receipt_number: str
    phonepe_reference: str
    created_at: datetime
    updated_at: datetime
    items: list[InvoiceItemRead] = Field(default_factory=list)
    payments: list[PaymentRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class PaymentCreate(BaseModel):
    invoice_id: int
    amount: float
    payment_method: Literal["PhonePe UPI", "UPI QR", "UPI Intent", "UPI Collect", "Credit Card", "Debit Card", "Net Banking", "Wallet", "Cash"] = "PhonePe UPI"
    provider: str = "phonepe"
    remarks: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class PaymentSessionRead(BaseModel):
    payment: PaymentRead
    qr_payload: str
    redirect_url: str
    expiry_minutes: int


class DashboardSummary(BaseModel):
    today_collections: float
    phonepe_collections: float
    cash_collections: float
    pending_payments: int
    failed_payments: int
    refunds: int
    payment_success_rate: float
    average_payment_time_seconds: float
    invoice_count: int
    product_count: int
    customer_count: int
    partially_paid_invoices: int
    expired_payments: int


class PaymentWebhookPayload(BaseModel):
    payment_id: str
    status: str
    provider_payment_id: str | None = None
    transaction_id: str | None = None
    merchant_transaction_id: str | None = None
    merchant_order_id: str | None = None
    amount: float | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class RefundCreate(BaseModel):
    payment_id: str
    amount: float = Field(gt=0)
    reason: str
    requested_by: str = "admin"


class RefundApprove(BaseModel):
    approved_by: str = "admin"


class RefundRead(BaseModel):
    id: int
    payment_id: int
    refund_id: str
    amount: float
    reason: str
    status: str
    requested_by: str
    approved_by: str
    provider_refund_id: str
    processed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LedgerEntryRead(BaseModel):
    id: int
    invoice_id: int | None
    payment_id: int | None
    refund_id: int | None
    ledger_name: str
    entry_type: str
    amount: float
    currency: str
    narration: str
    posted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentStatusHistoryRead(BaseModel):
    id: int
    payment_id: int
    old_status: str
    new_status: str
    source: str
    notes: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReportSummary(BaseModel):
    collections_by_method: dict[str, float]
    store_wise_sales: dict[str, float]
    cashier_wise_collections: dict[str, float]
    pending_amount: float
    failed_amount: float
    refund_amount: float
    settlement_summary: dict[str, float]
