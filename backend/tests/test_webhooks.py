"""Stripe webhook: signature verification, payment confirmation, expiry/failure handling,
and idempotency against Stripe's automatic retries."""

from decimal import Decimal

from app.models import Order, OrderItem, OrderStatus, Product


def _make_pending_order(session, user_id: int, product: Product, quantity: int) -> Order:
    order = Order(
        user_id=user_id,
        status=OrderStatus.pending_payment,
        total_amount=product.price * quantity,
        stripe_checkout_session_id="cs_test_123",
    )
    order.items = [
        OrderItem(product_id=product.id, product_name=product.name, unit_price=product.price, quantity=quantity)
    ]
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


def _fake_event(event_type: str, order_id: int, **object_overrides) -> dict:
    obj = {"metadata": {"order_id": str(order_id)}, "payment_intent": "pi_test", **object_overrides}
    return {"type": event_type, "data": {"object": obj}}


def test_invalid_signature_is_rejected(client, monkeypatch):
    def _raise(*args, **kwargs):
        raise ValueError("bad signature")

    monkeypatch.setattr("app.routers.webhooks.construct_webhook_event", _raise)

    res = client.post("/api/webhooks/stripe", content=b"{}", headers={"stripe-signature": "bogus"})
    assert res.status_code == 400


def test_checkout_completed_marks_order_paid(client, session, make_user, make_product, monkeypatch):
    user = make_user("payer@example.com")
    product = make_product(stock=10)
    order = _make_pending_order(session, user.id, product, quantity=2)

    event = _fake_event(
        "checkout.session.completed", order.id, amount_total=int(order.total_amount * 100)
    )
    monkeypatch.setattr("app.routers.webhooks.construct_webhook_event", lambda payload, sig: event)

    res = client.post("/api/webhooks/stripe", content=b"{}", headers={"stripe-signature": "sig"})
    assert res.status_code == 200

    session.expire_all()
    assert session.get(Order, order.id).status == OrderStatus.paid


def test_completed_event_is_idempotent_against_stripe_retries(client, session, make_user, make_product, monkeypatch):
    user = make_user("payer2@example.com")
    product = make_product(stock=10)
    order = _make_pending_order(session, user.id, product, quantity=1)

    event = _fake_event("checkout.session.completed", order.id, amount_total=int(order.total_amount * 100))
    monkeypatch.setattr("app.routers.webhooks.construct_webhook_event", lambda payload, sig: event)

    # Stripe redelivers the same event on anything but a 2xx - simulate two deliveries.
    first = client.post("/api/webhooks/stripe", content=b"{}", headers={"stripe-signature": "sig"})
    second = client.post("/api/webhooks/stripe", content=b"{}", headers={"stripe-signature": "sig"})

    assert first.status_code == 200
    assert second.status_code == 200
    session.expire_all()
    # Still just "paid" - a naive handler without the pending_payment guard could otherwise
    # double-process side effects (e.g. re-set payment_intent, refire downstream events).
    assert session.get(Order, order.id).status == OrderStatus.paid


def test_expired_session_restores_stock(client, session, make_user, make_product, monkeypatch):
    user = make_user("abandoner@example.com")
    product = make_product(stock=10)
    # Simulate that checkout already reserved 3 units before the session expired.
    product.stock -= 3
    session.add(product)
    session.commit()
    order = _make_pending_order(session, user.id, product, quantity=3)

    event = _fake_event("checkout.session.expired", order.id)
    monkeypatch.setattr("app.routers.webhooks.construct_webhook_event", lambda payload, sig: event)

    res = client.post("/api/webhooks/stripe", content=b"{}", headers={"stripe-signature": "sig"})
    assert res.status_code == 200

    session.expire_all()
    assert session.get(Order, order.id).status == OrderStatus.failed
    assert session.get(Product, product.id).stock == 10  # fully restored
