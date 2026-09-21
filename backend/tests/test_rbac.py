"""RBAC and ownership enforcement - the backend must reject unauthorized access on its own,
never relying on the frontend to hide a button."""

from app.models import Role


def test_unauthenticated_requests_are_rejected(client):
    assert client.get("/api/orders").status_code == 401
    assert client.get("/api/admin/products").status_code == 401
    assert client.get("/api/admin/orders").status_code == 401


def test_customer_cannot_reach_admin_routes(client, make_user, auth_headers):
    customer = make_user("customer@example.com", role=Role.customer)
    headers = auth_headers(customer)

    assert client.get("/api/admin/products", headers=headers).status_code == 403
    assert client.get("/api/admin/orders", headers=headers).status_code == 403
    assert (
        client.post("/api/admin/products", json={"name": "x", "price": 1}, headers=headers).status_code
        == 403
    )


def test_admin_can_reach_admin_routes(client, make_user, auth_headers):
    admin = make_user("admin@example.com", role=Role.admin)
    headers = auth_headers(admin)

    assert client.get("/api/admin/products", headers=headers).status_code == 200
    assert client.get("/api/admin/orders", headers=headers).status_code == 200


def test_products_are_publicly_readable(client, make_product):
    make_product(name="Public Widget")
    res = client.get("/api/products")
    assert res.status_code == 200
    assert any(p["name"] == "Public Widget" for p in res.json())
