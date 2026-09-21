"""Google login: registration, existing-user login, and the admin allow-list, including
retroactive promotion when an email is added to ADMIN_EMAILS after the account existed.

Google's `verify_oauth2_token` is monkeypatched throughout - it's a static, network-calling
signature check we don't want to depend on for unit tests. The rest of the login logic
(user creation, JWT issuance, role assignment) runs for real.
"""

from app.models import Role, User


def _fake_claims(sub: str, email: str, name: str = "Test User"):
    return {"sub": sub, "email": email, "name": name, "picture": None}


def test_new_user_registers_as_customer_by_default(client, monkeypatch):
    monkeypatch.setattr("app.routers.auth.settings.google_client_id", "dummy-client-id")
    monkeypatch.setattr(
        "app.routers.auth.google_id_token.verify_oauth2_token",
        lambda token, request, client_id: _fake_claims("sub-1", "newcustomer@example.com"),
    )

    res = client.post("/api/auth/google", json={"id_token": "whatever"})
    assert res.status_code == 200
    body = res.json()
    assert body["user"]["email"] == "newcustomer@example.com"
    assert body["user"]["role"] == "customer"
    assert body["access_token"]


def test_admin_allowlist_grants_admin_on_registration(client, monkeypatch):
    monkeypatch.setattr("app.routers.auth.settings.google_client_id", "dummy-client-id")
    monkeypatch.setattr("app.routers.auth.settings.admin_emails", "boss@example.com")
    monkeypatch.setattr(
        "app.routers.auth.google_id_token.verify_oauth2_token",
        lambda token, request, client_id: _fake_claims("sub-2", "boss@example.com"),
    )

    res = client.post("/api/auth/google", json={"id_token": "whatever"})
    assert res.json()["user"]["role"] == "admin"


def test_admin_allowlist_promotes_existing_user_on_next_login(client, session, monkeypatch):
    # Account was created before its email was ever added to ADMIN_EMAILS.
    user = User(google_sub="sub-3", email="latecomer@example.com", name="Late", role=Role.customer)
    session.add(user)
    session.commit()

    monkeypatch.setattr("app.routers.auth.settings.google_client_id", "dummy-client-id")
    monkeypatch.setattr("app.routers.auth.settings.admin_emails", "latecomer@example.com")
    monkeypatch.setattr(
        "app.routers.auth.google_id_token.verify_oauth2_token",
        lambda token, request, client_id: _fake_claims("sub-3", "latecomer@example.com"),
    )

    res = client.post("/api/auth/google", json={"id_token": "whatever"})
    assert res.json()["user"]["role"] == "admin"


def test_get_me_requires_valid_token(client):
    assert client.get("/api/auth/me").status_code == 401
