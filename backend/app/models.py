from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Store(Base, TimestampMixin):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    address: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    products: Mapped[list["Product"]] = relationship(back_populates="store")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="store")
    users: Mapped[list["User"]] = relationship(back_populates="store")


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    email: Mapped[str] = mapped_column(String(200), default="", nullable=False)

    invoices: Mapped[list["Invoice"]] = relationship(back_populates="customer")


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sku: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reorder_level: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    aisle: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    rack: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    shelf: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    bin: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    location_code: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    category: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    barcode: Mapped[str] = mapped_column(String(120), default="", nullable=False)

    store: Mapped["Store"] = relationship(back_populates="products")
    invoice_items: Mapped[list["InvoiceItem"]] = relationship(back_populates="product")
    movements: Mapped[list["StockMovement"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    store_id: Mapped[int | None] = mapped_column(ForeignKey("stores.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False, default="viewer")
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    store: Mapped["Store"] = relationship(back_populates="users")


class StockMovement(Base, TimestampMixin):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(40), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    before_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    after_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reference: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    performed_by: Mapped[str] = mapped_column(String(120), default="", nullable=False)

    product: Mapped["Product"] = relationship(back_populates="movements")


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_number: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    tax_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    discount_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    paid_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    remaining_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Draft")
    payment_status: Mapped[str] = mapped_column(String(40), nullable=False, default="Pending")
    receipt_number: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    phonepe_reference: Mapped[str] = mapped_column(String(120), default="", nullable=False)

    store: Mapped["Store"] = relationship(back_populates="invoices")
    customer: Mapped["Customer"] = relationship(back_populates="invoices")
    items: Mapped[list["InvoiceItem"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(back_populates="invoice")


class InvoiceItem(Base, TimestampMixin):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    line_total: Mapped[float] = mapped_column(Float, nullable=False)

    invoice: Mapped["Invoice"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(back_populates="invoice_items")


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payment_id: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    merchant_transaction_id: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    merchant_order_id: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="phonepe")
    provider_payment_id: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    payment_method: Mapped[str] = mapped_column(String(40), default="UPI", nullable=False)
    payment_status: Mapped[str] = mapped_column(String(40), nullable=False, default="Pending")
    amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    gst_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    convenience_fee: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    sale_id: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), nullable=False)
    terminal_id: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    cashier_id: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    initiated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    callback_received: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    webhook_received: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    remarks: Mapped[str] = mapped_column(Text, default="", nullable=False)
    extra_metadata: Mapped[str] = mapped_column("metadata", Text, default="{}", nullable=False)

    invoice: Mapped["Invoice"] = relationship(back_populates="payments")
    attempts: Mapped[list["PaymentAttempt"]] = relationship(
        back_populates="payment", cascade="all, delete-orphan"
    )
    webhooks: Mapped[list["WebhookLog"]] = relationship(
        back_populates="payment", cascade="all, delete-orphan"
    )
    refunds: Mapped[list["Refund"]] = relationship(
        back_populates="payment", cascade="all, delete-orphan"
    )
    status_history: Mapped[list["PaymentStatusHistory"]] = relationship(
        back_populates="payment", cascade="all, delete-orphan"
    )


class PaymentAttempt(Base, TimestampMixin):
    __tablename__ = "payment_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    request_payload: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    response_payload: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    response_code: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    response_message: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    ip: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    device: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    browser: Mapped[str] = mapped_column(String(120), default="", nullable=False)

    payment: Mapped["Payment"] = relationship(back_populates="attempts")


class WebhookLog(Base, TimestampMixin):
    __tablename__ = "webhook_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), nullable=False)
    headers: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    payload: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(40), default="Unknown", nullable=False)
    processing_status: Mapped[str] = mapped_column(String(40), default="Pending", nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    response: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    payment: Mapped["Payment"] = relationship(back_populates="webhooks")


class PaymentStatusHistory(Base, TimestampMixin):
    __tablename__ = "payment_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), nullable=False)
    old_status: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    new_status: Mapped[str] = mapped_column(String(40), nullable=False)
    source: Mapped[str] = mapped_column(String(40), default="system", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    payment: Mapped["Payment"] = relationship(back_populates="status_history")


class Refund(Base, TimestampMixin):
    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), nullable=False)
    refund_id: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="Pending Approval", nullable=False)
    requested_by: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    approved_by: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    provider_refund_id: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    payment: Mapped["Payment"] = relationship(back_populates="refunds")


class LedgerEntry(Base, TimestampMixin):
    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"), nullable=True)
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id"), nullable=True)
    refund_id: Mapped[int | None] = mapped_column(ForeignKey("refunds.id"), nullable=True)
    ledger_name: Mapped[str] = mapped_column(String(120), nullable=False)
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    narration: Mapped[str] = mapped_column(Text, default="", nullable=False)
    posted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
