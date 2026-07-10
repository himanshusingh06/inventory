# Inventory Management System

A full-stack inventory, billing, payment, and store-operations system inspired by quick-commerce workflows used by stores such as Blinkit-style dark stores.

The project is split into:

- `backend/` - FastAPI, SQLAlchemy ORM, PostgreSQL, auth, RBAC, POS, inventory, payments, refunds, reports.
- `frontend/` - React/Vite operational dashboard.

## Features

- Login and role-based access control.
- Super admin staff management.
- Store and dark-store management.
- Store-specific inventory with exact physical locations like `A1-22-4-C`.
- Product SKU, barcode, category, price, stock, reorder level, and low-stock tracking.
- Stock movement history for receiving, adjustment, damage, transfer in, and transfer out.
- POS invoice creation with multiple line items.
- Cash and PhonePe-style payment sessions.
- Payment status tracking: pending, success, failed, expired, refunded, partially refunded.
- Refund request and approval workflow.
- Ledger entries for sales, cash/UPI, customer ledger, GST, and refunds.
- Dashboard reports for collections, pending amount, failed amount, refunds, and settlement.
- PhonePe credentials are environment-driven. Local development uses mock payment sessions when credentials are absent.

## Seed Accounts

The seed creates practical test users:

| Role | Email | Password |
| --- | --- | --- |
| Super Admin | `superadmin@example.com` | `admin123` |
| Store Manager | `manager@example.com` | `manager123` |
| Inventory Manager | `inventory@example.com` | `inventory123` |
| Cashier | `cashier@example.com` | `cashier123` |
| Accountant | `accounts@example.com` | `accounts123` |

## Role Permissions

- `super_admin`: manages everything, including staff.
- `store_manager`: manages store catalog, inventory, billing, payments, and reports.
- `inventory_manager`: manages stock, product location, low-stock, and inventory reports.
- `cashier`: creates invoices and collects payments.
- `accountant`: reviews payments, refunds, ledgers, and reports.
- `viewer`: read-only operational access.

## Database

PostgreSQL is the intended database. SQLAlchemy ORM is used for all app models.

Create a PostgreSQL database named `inventory_db`, or start the bundled container:

```bash
docker compose up -d postgres
```

Copy env values:

```bash
copy backend\.env.example backend\.env
```

Set `DATABASE_URL` in `backend/.env`, for example:

```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/inventory_db
APP_SECRET_KEY=change-this-secret-in-production
```

For existing development databases, startup includes additive compatibility for the product location columns.

## Backend Setup

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

API docs:

```text
http://localhost:8000/docs
```

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

The frontend proxies `/api` to `http://localhost:8000`.

## Core Workflow

1. Login as `superadmin@example.com`.
2. Create or review stores.
3. Add products with SKU, barcode, stock, reorder level, and location fields.
4. Use location codes such as `A1-22-4-C` to identify the exact aisle, rack, shelf, and bin.
5. Receive or adjust stock through stock movement controls.
6. Create a customer and invoice.
7. Collect payment by Cash or PhonePe mock session.
8. Verify status, refund if needed, and review ledgers/reports.

## PhonePe Environment Variables

```env
PHONEPE_ENV=UAT
PHONEPE_MERCHANT_ID=
PHONEPE_MERCHANT_SECRET=
PHONEPE_CLIENT_ID=
PHONEPE_CLIENT_SECRET=
PHONEPE_BASE_URL=https://api-preprod.phonepe.com
PHONEPE_CALLBACK_URL=http://localhost:8000/api/payments/phonepe/callback
PHONEPE_REDIRECT_URL=http://localhost:5173/payment/status
PHONEPE_WEBHOOK_SECRET=
PAYMENT_EXPIRY_MINUTES=15
```

No credentials are exposed to the frontend.

## Verification

Useful checks:

```bash
cd backend
Get-ChildItem app -Recurse -Filter *.py | ForEach-Object { .\.venv\Scripts\python -m py_compile $_.FullName }
```

```bash
cd frontend
npm run build
```
