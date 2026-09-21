"""A customer must only ever see their own orders; admins can see any order."""

from decimal import Decimal

from app.models import Order, OrderStatus, Role


def _make_order(session, user_id: int) -> Order:
    order = Order(user_id=user_id, status=OrderStatus.paid, total_amount=Decimal("19.99"))
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


def test_owner_can_view_own_order(client, session, make_user, auth_headers):
    owner = make_user("owner@example.com")
    order = _make_order(session, owner.id)

    res = client.get(f"/api/orders/{order.id}", headers=auth_headers(owner))
    assert res.status_code == 200
    assert res.json()["id"] == order.id


def test_other_customer_cannot_view_someone_elses_order(client, session, make_user, auth_headers):
    owner = make_user("owner2@example.com")
    other = make_user("other2@example.com")
    order = _make_order(session, owner.id)

    res = client.get(f"/api/orders/{order.id}", headers=auth_headers(other))
    assert res.status_code == 403


def test_admin_can_view_any_order(client, session, make_user, auth_headers):
    owner = make_user("owner3@example.com")
    admin = make_user("admin3@example.com", role=Role.admin)
    order = _make_order(session, owner.id)

    res = client.get(f"/api/orders/{order.id}", headers=auth_headers(admin))
    assert res.status_code == 200


def test_missing_order_is_404(client, make_user, auth_headers):
    user = make_user("nobody@example.com")
    res = client.get("/api/orders/999999", headers=auth_headers(user))
    assert res.status_code == 404


def test_list_my_orders_excludes_other_customers(client, session, make_user, auth_headers):
    owner = make_user("owner4@example.com")
    other = make_user("other4@example.com")
    _make_order(session, owner.id)

    res = client.get("/api/orders", headers=auth_headers(other))
    assert res.status_code == 200
    assert res.json() == []
