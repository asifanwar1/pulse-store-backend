def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_make_user_and_auth_headers(client, make_user, auth_headers):
    user = make_user("smoke@example.com")
    headers = auth_headers(user)
    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "smoke@example.com"
