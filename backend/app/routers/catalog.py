from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_permission
from app.db import get_db
from app.models import Customer, Product, StockMovement, Store, User
from app.schemas import (
    CustomerCreate,
    CustomerRead,
    ProductCreate,
    ProductRead,
    StockAdjust,
    StockMovementRead,
    StoreCreate,
    StoreRead,
)

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/stores", response_model=list[StoreRead])
def list_stores(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("catalog:read")),
):
    return db.query(Store).order_by(Store.name.asc()).all()


@router.post("/stores", response_model=StoreRead)
def create_store(
    payload: StoreCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("catalog:write")),
):
    if user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Only super admins can add stores")
    store = Store(**payload.model_dump())
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@router.get("/customers", response_model=list[CustomerRead])
def list_customers(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("billing:read")),
):
    return db.query(Customer).order_by(Customer.name.asc()).all()


@router.post("/customers", response_model=CustomerRead)
def create_customer(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("billing:write")),
):
    customer = Customer(**payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/products", response_model=list[ProductRead])
def list_products(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("inventory:read")),
):
    return db.query(Product).order_by(Product.created_at.desc()).all()


@router.get("/products/low-stock", response_model=list[ProductRead])
def low_stock_products(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("inventory:read")),
):
    return db.query(Product).filter(Product.stock <= Product.reorder_level).order_by(Product.stock.asc()).all()


@router.post("/products", response_model=ProductRead)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory:write")),
):
    data = payload.model_dump()
    if not data["location_code"]:
        data["location_code"] = "-".join(
            part for part in [data["aisle"], data["rack"], data["shelf"], data["bin"]] if part
        )
    product = Product(**data)
    db.add(product)
    db.flush()
    db.add(
        StockMovement(
            product_id=product.id,
            store_id=product.store_id,
            movement_type="opening",
            quantity=product.stock,
            before_quantity=0,
            after_quantity=product.stock,
            reference=product.sku,
            notes="Opening stock",
            performed_by=user.email,
        )
    )
    db.commit()
    db.refresh(product)
    return product


@router.post("/products/{product_id}/stock", response_model=ProductRead)
def adjust_stock(
    product_id: int,
    payload: StockAdjust,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory:write")),
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    before = product.stock
    if payload.movement_type in {"damage", "transfer_out"}:
        product.stock = max(0, product.stock - abs(payload.quantity))
    else:
        product.stock = max(0, product.stock + payload.quantity)
    db.add(
        StockMovement(
            product_id=product.id,
            store_id=product.store_id,
            movement_type=payload.movement_type,
            quantity=payload.quantity,
            before_quantity=before,
            after_quantity=product.stock,
            reference=product.sku,
            notes=payload.notes,
            performed_by=user.email,
        )
    )
    db.commit()
    db.refresh(product)
    return product


@router.get("/stock-movements", response_model=list[StockMovementRead])
def stock_movements(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("inventory:read")),
):
    return db.query(StockMovement).order_by(StockMovement.created_at.desc()).limit(100).all()
