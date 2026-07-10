from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.models import Customer, Product, StockMovement, Store, User


def seed(db: Session) -> None:
    stores = [
        {
            "name": "BlinkMart Central Hub",
            "code": "BLR-HUB-01",
            "address": "Warehouse Road, Bengaluru",
        },
        {
            "name": "BlinkMart Indiranagar Dark Store",
            "code": "BLR-IND-02",
            "address": "12th Main, Indiranagar",
        },
    ]
    store_rows: dict[str, Store] = {}
    for store_data in stores:
        store = db.scalar(select(Store).where(Store.code == store_data["code"]))
        if not store:
            store = Store(**store_data)
            db.add(store)
            db.flush()
        store_rows[store.code] = store

    customer = db.scalar(select(Customer).where(Customer.email == "walkin@example.com"))
    if not customer:
        customer = Customer(name="Walk-in Customer", phone="0000000000", email="walkin@example.com")
        db.add(customer)
        db.flush()

    users = [
        {
            "name": "Super Admin",
            "email": "superadmin@example.com",
            "password_hash": hash_password("admin123"),
            "role": "super_admin",
            "store_id": None,
        },
        {
            "name": "Hub Manager",
            "email": "manager@example.com",
            "password_hash": hash_password("manager123"),
            "role": "store_manager",
            "store_id": store_rows["BLR-HUB-01"].id,
        },
        {
            "name": "Inventory Lead",
            "email": "inventory@example.com",
            "password_hash": hash_password("inventory123"),
            "role": "inventory_manager",
            "store_id": store_rows["BLR-HUB-01"].id,
        },
        {
            "name": "POS Cashier",
            "email": "cashier@example.com",
            "password_hash": hash_password("cashier123"),
            "role": "cashier",
            "store_id": store_rows["BLR-IND-02"].id,
        },
        {
            "name": "Accountant",
            "email": "accounts@example.com",
            "password_hash": hash_password("accounts123"),
            "role": "accountant",
            "store_id": None,
        },
    ]
    for user_data in users:
        user = db.scalar(select(User).where(User.email == user_data["email"]))
        if not user:
            db.add(User(**user_data))

    products = [
        {
            "store_id": store_rows["BLR-HUB-01"].id,
            "name": "Amul Taaza Milk 1L",
            "sku": "MILK-AMUL-1L",
            "barcode": "8901262010010",
            "category": "Dairy",
            "price": 68.0,
            "stock": 120,
            "reorder_level": 30,
            "aisle": "A1",
            "rack": "22",
            "shelf": "4",
            "bin": "C",
            "location_code": "A1-22-4-C",
        },
        {
            "store_id": store_rows["BLR-HUB-01"].id,
            "name": "Britannia Bread 400g",
            "sku": "BREAD-BRIT-400",
            "barcode": "8901063160013",
            "category": "Bakery",
            "price": 45.0,
            "stock": 75,
            "reorder_level": 20,
            "aisle": "A1",
            "rack": "18",
            "shelf": "2",
            "bin": "A",
            "location_code": "A1-18-2-A",
        },
        {
            "store_id": store_rows["BLR-HUB-01"].id,
            "name": "Tata Salt 1kg",
            "sku": "SALT-TATA-1KG",
            "barcode": "8904043901012",
            "category": "Staples",
            "price": 28.0,
            "stock": 200,
            "reorder_level": 50,
            "aisle": "B2",
            "rack": "10",
            "shelf": "1",
            "bin": "D",
            "location_code": "B2-10-1-D",
        },
        {
            "store_id": store_rows["BLR-IND-02"].id,
            "name": "Fortune Sunflower Oil 1L",
            "sku": "OIL-FORT-1L",
            "barcode": "8906007280018",
            "category": "Staples",
            "price": 145.0,
            "stock": 45,
            "reorder_level": 12,
            "aisle": "C3",
            "rack": "08",
            "shelf": "3",
            "bin": "B",
            "location_code": "C3-08-3-B",
        },
        {
            "store_id": store_rows["BLR-IND-02"].id,
            "name": "Fresh Tomato 1kg",
            "sku": "VEG-TOMATO-1KG",
            "barcode": "VEG000001",
            "category": "Fresh Produce",
            "price": 38.0,
            "stock": 32,
            "reorder_level": 15,
            "aisle": "F1",
            "rack": "02",
            "shelf": "1",
            "bin": "A",
            "location_code": "F1-02-1-A",
        },
    ]
    for product_data in products:
        product = db.scalar(select(Product).where(Product.sku == product_data["sku"]))
        if not product:
            product = Product(**product_data)
            db.add(product)
            db.flush()

        movement_exists = db.scalar(
            select(StockMovement.id).where(
                StockMovement.product_id == product.id,
                StockMovement.movement_type == "opening",
                StockMovement.reference == product.sku,
            )
        )
        if not movement_exists:
            db.add(
                StockMovement(
                    product_id=product.id,
                    store_id=product.store_id,
                    movement_type="opening",
                    quantity=product.stock,
                    before_quantity=0,
                    after_quantity=product.stock,
                    reference=product.sku,
                    notes="Seed opening stock for testing",
                    performed_by="seed",
                )
            )

    db.commit()
