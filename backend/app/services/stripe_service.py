import time

import stripe

from app.config import get_settings
from app.models import Order, OrderItem

settings = get_settings()
stripe.api_key = settings.stripe_secret_key

# Stock is reserved as soon as checkout starts (see routers/orders.py), so an abandoned
# session shouldn't lock inventory for Stripe's 24h default. 30 minutes is the shortest
# window Stripe allows and comfortably covers a customer who's actually paying.
CHECKOUT_SESSION_LIFETIME_SECONDS = 30 * 60


def create_checkout_session(order: Order, items: list[OrderItem], customer_email: str) -> stripe.checkout.Session:
    line_items = [
        {
            "price_data": {
                "currency": settings.stripe_currency,
                "product_data": {"name": item.product_name},
                "unit_amount": int(item.unit_price * 100),
            },
            "quantity": item.quantity,
        }
        for item in items
    ]

    return stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        customer_email=customer_email,
        line_items=line_items,
        metadata={"order_id": str(order.id)},
        expires_at=int(time.time()) + CHECKOUT_SESSION_LIFETIME_SECONDS,
        success_url=f"{settings.frontend_url}/orders/{order.id}?checkout=success",
        cancel_url=f"{settings.frontend_url}/orders/{order.id}?checkout=cancelled",
    )


def construct_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
    return stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
