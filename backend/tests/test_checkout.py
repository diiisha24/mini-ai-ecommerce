"""Checkout business logic: stock reservation, insufficient-stock rejection, and rollback
when the downstream Stripe call fails."""

from types import SimpleNamespace

from app.models import OrderStatus, Product, Role


def _fake_stripe_session(order_id: int) -> SimpleNamespace:
    return SimpleNamespace(id=f"cs_test_{order_id}", url=f"https://checkout.stripe.com/test/{order_id}")


def test_checkout_reserves_stock_and_returns_checkout_url(client, session, make_user, make_product, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "app.routers.orders.create_checkout_session",
        lambda order, items, email: _fake_stripe_session(order.id),
    )

    customer = make_user("buyer@example.com", role=Role.customer)
    product = make_product(name="Widget", price=9.99, stock=5)

    res = client.post(
        "/api/orders/checkout",
        json={"items": [{"product_id": product.id, "quantity": 2}]},
        headers=auth_headers(customer),
    )

    assert res.status_code == 200
    body = res.json()
    assert body["checkout_url"].startswith("https://checkout.stripe.com/")

    session.expire_all()
    refreshed_product = session.get(Product, product.id)
    assert refreshed_product.stock == 3  # 5 - 2, reserved immediately


def test_checkout_rejects_insufficient_stock_without_touching_it(client, session, make_user, make_product, auth_headers):
    customer = make_user("buyer2@example.com", role=Role.customer)
    product = make_product(name="Scarce Widget", price=5, stock=1)

    res = client.post(
        "/api/orders/checkout",
        json={"items": [{"product_id": product.id, "quantity": 2}]},
        headers=auth_headers(customer),
    )

    assert res.status_code == 400
    session.expire_all()
    assert session.get(Product, product.id).stock == 1  # untouched


def test_checkout_rolls_back_stock_when_stripe_fails(client, session, make_user, make_product, auth_headers, monkeypatch):
    def _boom(order, items, email):
        raise RuntimeError("stripe is down")

    monkeypatch.setattr("app.routers.orders.create_checkout_session", _boom)

    customer = make_user("buyer3@example.com", role=Role.customer)
    product = make_product(name="Flaky Widget", price=20, stock=4)

    res = client.post(
        "/api/orders/checkout",
        json={"items": [{"product_id": product.id, "quantity": 3}]},
        headers=auth_headers(customer),
    )

    assert res.status_code == 502
    session.expire_all()
    assert session.get(Product, product.id).stock == 4  # fully restored

    orders = client.get("/api/orders", headers=auth_headers(customer)).json()
    assert orders[0]["status"] == OrderStatus.failed.value


def test_checkout_requires_nonempty_cart(client, make_user, auth_headers):
    customer = make_user("buyer4@example.com", role=Role.customer)
    res = client.post("/api/orders/checkout", json={"items": []}, headers=auth_headers(customer))
    assert res.status_code == 400
