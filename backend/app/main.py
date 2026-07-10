from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.core.config import settings
from app.db import Base, engine, SessionLocal
from app.routers.auth import router as auth_router
from app.routers.catalog import router as catalog_router
from app.routers.health import router as health_router
from app.routers.invoices import router as invoices_router
from app.routers.payments import router as payments_router
from app.seed import seed

app = FastAPI(title="Inventory Management API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(catalog_router)
app.include_router(invoices_router)
app.include_router(payments_router)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_compatible_schema()
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


def ensure_compatible_schema() -> None:
    inspector = inspect(engine)
    if "products" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("products")}
    product_columns = {
        "reorder_level": "INTEGER DEFAULT 5 NOT NULL",
        "aisle": "VARCHAR(20) DEFAULT '' NOT NULL",
        "rack": "VARCHAR(20) DEFAULT '' NOT NULL",
        "shelf": "VARCHAR(20) DEFAULT '' NOT NULL",
        "bin": "VARCHAR(20) DEFAULT '' NOT NULL",
        "location_code": "VARCHAR(80) DEFAULT '' NOT NULL",
        "category": "VARCHAR(120) DEFAULT '' NOT NULL",
        "barcode": "VARCHAR(120) DEFAULT '' NOT NULL",
    }
    with engine.begin() as connection:
        for name, definition in product_columns.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE products ADD COLUMN {name} {definition}"))
