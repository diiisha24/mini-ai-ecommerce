from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.db import get_session
from app.deps import require_admin
from app.models import Product
from app.schemas import ProductCreate, ProductRead, ProductUpdate

router = APIRouter(prefix="/api/products", tags=["products"])
admin_router = APIRouter(prefix="/api/admin/products", tags=["admin-products"])

# Hard cap, not just a default: without one, a single request could pull the entire
# catalog into memory and serialize it, regardless of how the frontend calls the API.
MAX_PAGE_SIZE = 100


@router.get("", response_model=list[ProductRead])
def list_products(
    session: Session = Depends(get_session),
    limit: int = Query(default=MAX_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
) -> list[Product]:
    return session.exec(
        select(Product)
        .where(Product.is_active == True)  # noqa: E712
        .order_by(Product.id)
        .offset(offset)
        .limit(limit)
    ).all()


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, session: Session = Depends(get_session)) -> Product:
    product = session.get(Product, product_id)
    if product is None or not product.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    return product


@admin_router.get("", response_model=list[ProductRead], dependencies=[Depends(require_admin)])
def admin_list_products(
    session: Session = Depends(get_session),
    limit: int = Query(default=MAX_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
) -> list[Product]:
    return session.exec(select(Product).order_by(Product.id).offset(offset).limit(limit)).all()


@admin_router.post("", response_model=ProductRead, dependencies=[Depends(require_admin)])
def create_product(payload: ProductCreate, session: Session = Depends(get_session)) -> Product:
    product = Product(**payload.model_dump())
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


@admin_router.put("/{product_id}", response_model=ProductRead, dependencies=[Depends(require_admin)])
def update_product(
    product_id: int, payload: ProductUpdate, session: Session = Depends(get_session)
) -> Product:
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    product.updated_at = datetime.now(timezone.utc)

    session.add(product)
    session.commit()
    session.refresh(product)
    return product


@admin_router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_product(product_id: int, session: Session = Depends(get_session)) -> None:
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    # Soft delete: keep historical order items pointing at a valid product row.
    product.is_active = False
    session.add(product)
    session.commit()
