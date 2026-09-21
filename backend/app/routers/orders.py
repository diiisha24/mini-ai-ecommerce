import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.db import get_session
from app.deps import get_current_user, require_admin
from app.models import Order, OrderItem, OrderStatus, Product, User
from app.schemas import CheckoutRequest, CheckoutResponse, OrderRead
from app.services.stripe_service import create_checkout_session

router = APIRouter(prefix="/api/orders", tags=["orders"])
admin_router = APIRouter(prefix="/api/admin/orders", tags=["admin-orders"])
logger = logging.getLogger(__name__)

MAX_PAGE_SIZE = 100


@router.post("/checkout", response_model=CheckoutResponse)
def checkout(
    payload: CheckoutRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CheckoutResponse:
    if not payload.items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cart is empty")

    order_items: list[OrderItem] = []
    total = Decimal("0")

    # Lock rows in a stable order (ascending product_id) across all callers so two
    # concurrent checkouts touching overlapping products can never deadlock on each other.
    for entry in sorted(payload.items, key=lambda e: e.product_id):
        # SELECT ... FOR UPDATE: blocks any other checkout on this product row until we
        # commit, so two simultaneous requests can never both read the same stale stock
        # count and oversell the last unit.
        product = session.get(Product, entry.product_id, with_for_update=True)
        if product is None or not product.is_active:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Product {entry.product_id} not found")
        if product.stock < entry.quantity:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Insufficient stock for '{product.name}' (available: {product.stock})",
            )

        # Reserve stock immediately so it can't be oversold while payment is pending.
        product.stock -= entry.quantity
        session.add(product)

        line_total = product.price * entry.quantity
        total += line_total
        order_items.append(
            OrderItem(
                product_id=product.id,
                product_name=product.name,
                unit_price=product.price,
                quantity=entry.quantity,
            )
        )

    # Order, its items, and the stock decrements above all land in one transaction: either
    # all of it is durable before we ever talk to Stripe, or none of it is.
    order = Order(user_id=user.id, status=OrderStatus.pending_payment, total_amount=total)
    order.items = order_items
    session.add(order)
    session.commit()
    session.refresh(order)

    try:
        stripe_session = create_checkout_session(order, order_items, user.email)
    except Exception as exc:  # noqa: BLE001 - surface Stripe errors, then roll back the reservation
        # The client only ever sees a generic 502 (never leak Stripe/account internals to
        # the browser), but the real cause - account restrictions, bad API key, network
        # failure, etc. - must be visible server-side or this is undebuggable in production.
        logger.exception("Stripe checkout session creation failed for order %s", order.id)
        for item in order_items:
            product = session.get(Product, item.product_id, with_for_update=True)
            product.stock += item.quantity
            session.add(product)
        order.status = OrderStatus.failed
        session.add(order)
        session.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Could not start payment session") from exc

    order.stripe_checkout_session_id = stripe_session.id
    session.add(order)
    session.commit()
    session.refresh(order)

    return CheckoutResponse(order_id=order.id, checkout_url=stripe_session.url)


@router.get("", response_model=list[OrderRead])
def list_my_orders(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    limit: int = Query(default=MAX_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
) -> list[Order]:
    # WHERE user_id = ? ORDER BY created_at DESC is served by the composite
    # ix_order_user_id_created_at index in one pass - no separate sort step.
    return session.exec(
        select(Order)
        .where(Order.user_id == user.id)
        .options(selectinload(Order.user), selectinload(Order.items))
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()


@router.get("/{order_id}", response_model=OrderRead)
def get_order(
    order_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> Order:
    order = session.get(Order, order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    if order.user_id != user.id and user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your order")
    return order


@admin_router.get("", response_model=list[OrderRead], dependencies=[Depends(require_admin)])
def admin_list_orders(
    session: Session = Depends(get_session),
    limit: int = Query(default=MAX_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
) -> list[Order]:
    return session.exec(
        select(Order)
        .options(selectinload(Order.user), selectinload(Order.items))
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
