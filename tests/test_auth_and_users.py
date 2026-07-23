from app.features.users.models import UserType


def test_register_ignores_client_supplied_user_type(client, make_user, auth_headers):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "hacker@example.com",
            "full_name": "Hacker Person",
            "password": "Str0ng!Pass1",
            "user_type": "ADMIN",
            "userType": "ADMIN",
        },
    )
    assert response.status_code == 201

    admin = make_user("suite-admin@example.com", user_type=UserType.ADMIN.value)
    listing = client.get(
        "/api/v1/users/",
        params={"search": "hacker@example.com"},
        headers=auth_headers(admin),
    )
    assert listing.status_code == 200
    users = listing.json()["data"]
    assert len(users) == 1
    assert users[0]["userType"] == UserType.CUSTOMER.value


def test_self_update_cannot_change_user_type(client, make_user, auth_headers):
    user = make_user("selfescalate@example.com", user_type=UserType.CUSTOMER.value)
    headers = auth_headers(user)

    response = client.patch(
        "/api/v1/users/me",
        json={"userType": "ADMIN", "fullName": "Still Customer"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["userType"] == UserType.CUSTOMER.value
    assert response.json()["fullName"] == "Still Customer"


def test_admin_role_endpoint_requires_admin(client, make_user, auth_headers):
    target = make_user("promote-target@example.com")
    non_admin = make_user("not-admin@example.com")
    headers = auth_headers(non_admin)

    response = client.patch(
        f"/api/v1/users/{target.id}/role",
        json={"userType": "ADMIN"},
        headers=headers,
    )
    assert response.status_code == 403


def test_admin_role_endpoint_promotes_user(client, make_user, auth_headers):
    admin = make_user("role-admin@example.com", user_type=UserType.ADMIN.value)
    target = make_user("role-target@example.com")

    response = client.patch(
        f"/api/v1/users/{target.id}/role",
        json={"userType": "VENDOR"},
        headers=auth_headers(admin),
    )
    assert response.status_code == 200
    assert response.json()["userType"] == UserType.VENDOR.value


def test_email_update_rejects_duplicate(client, make_user, auth_headers):
    make_user("taken@example.com")
    user_b = make_user("free@example.com")

    response = client.patch(
        "/api/v1/users/me",
        json={"email": "taken@example.com"},
        headers=auth_headers(user_b),
    )
    assert response.status_code == 409


def test_password_reset_invalidates_previously_issued_tokens(client, make_user, auth_headers, monkeypatch):
    import app.features.auth.service as auth_service

    monkeypatch.setattr(auth_service, "_generate_otp", lambda: "1234")

    user = make_user("resetme@example.com", password="Old!Passw0rd1")
    old_headers = auth_headers(user)

    assert client.get("/api/v1/users/me", headers=old_headers).status_code == 200

    resp = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": user.email, "type": "CUSTOMER"},
    )
    assert resp.status_code == 200
    flow_token = resp.json()["token"]

    resp = client.post(
        "/api/v1/auth/forgot-password/verification",
        json={"token": flow_token, "code": "1234"},
    )
    assert resp.status_code == 200
    verified_token = resp.json()["token"]

    resp = client.post(
        "/api/v1/auth/reset-password",
        json={"token": verified_token, "password": "New!Passw0rd2"},
    )
    assert resp.status_code == 200

    # The token issued before the reset must no longer work.
    assert client.get("/api/v1/users/me", headers=old_headers).status_code == 401

    # A fresh login with the new password works and yields a valid token.
    login_resp = client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "New!Passw0rd2"}
    )
    assert login_resp.status_code == 200
    new_token = login_resp.json()["token"]
    resp = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {new_token}"})
    assert resp.status_code == 200


def test_self_service_password_change_invalidates_old_tokens(client, make_user, auth_headers):
    user = make_user("selfpasschange@example.com", password="Old!Passw0rd1")
    old_headers = auth_headers(user)

    response = client.patch(
        "/api/v1/users/me",
        json={"password": "New!Passw0rd2"},
        headers=old_headers,
    )
    assert response.status_code == 200

    assert client.get("/api/v1/users/me", headers=old_headers).status_code == 401

    login_resp = client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "New!Passw0rd2"}
    )
    assert login_resp.status_code == 200
