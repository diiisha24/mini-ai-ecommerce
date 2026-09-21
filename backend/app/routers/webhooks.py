import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from app.db import get_session
from app.models import Order, OrderStatus, Product
from app.services.stripe_service import construct_webhook_event

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


def _restore_stock(order: Order, session: Session) -> None:
    for item in order.items:
        product = session.get(Product, item.product_id, with_for_update=True)
        if product is not None:
            product.stock += item.quantity
            session.add(product)


@router.post("/stripe")
async def stripe_webhook(request: Request, session: Session = Depends(get_session)) -> dict:
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = construct_webhook_event(payload, sig_header)
    except (stripe.error.SignatureVerificationError, ValueError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid webhook signature") from exc

    data = event["data"]["object"]
    order_id = data.get("metadata", {}).get("order_id")

    # Idempotency: only act if the order is still pending_payment. Stripe retries webhook
    # delivery on anything but a 2xx, so this guard is what makes replayed events safe -
    # but only under a row lock. Without with_for_update, two genuinely concurrent
    # deliveries of the same event (Stripe does send overlapping retries under latency)
    # could both read pending_payment under READ COMMITTED before either commits.
    if event["type"] == "checkout.session.completed":
        order = session.get(Order, int(order_id), with_for_update=True) if order_id else None
        if order and order.status == OrderStatus.pending_payment:
            amount_total = data.get("amount_total")
            expected_cents = int(order.total_amount * 100)
            if amount_total is not None and amount_total != expected_cents:
                # Defense-in-depth only: line items are always server-constructed today,
                # so this should never fire. Still honor the real, already-collected
                # payment - refusing it would be worse for the customer - but log loudly
                # so a future change that lets pricing drift doesn't fail silently.
                logger.warning(
                    "Stripe amount_total (%s) != expected order total (%s) for order %s",
                    amount_total,
                    expected_cents,
                    order.id,
                )
            order.status = OrderStatus.paid
            order.stripe_payment_intent_id = data.get("payment_intent")
            session.add(order)
            session.commit()

    elif event["type"] in ("checkout.session.expired", "checkout.session.async_payment_failed"):
        order = session.get(Order, int(order_id), with_for_update=True) if order_id else None
        if order and order.status == OrderStatus.pending_payment:
            order.status = OrderStatus.failed
            _restore_stock(order, session)
            session.add(order)
            session.commit()

    return {"received": True}
