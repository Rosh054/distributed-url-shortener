from datetime import datetime, timedelta


def test_create_short_url(client):
    response = client.post("/shorten", json={"long_url": "https://example.com/page"})
    assert response.status_code == 201
    body = response.json()
    assert body["short_code"]
    assert body["long_url"] == "https://example.com/page"
    assert body["custom_alias"] is False
    assert body["short_url"].endswith(f"/{body['short_code']}")


def test_invalid_url_rejected(client):
    response = client.post("/shorten", json={"long_url": "not-a-url"})
    assert response.status_code == 422


def test_invalid_scheme_rejected(client):
    response = client.post("/shorten", json={"long_url": "ftp://example.com"})
    assert response.status_code in (400, 422)


def test_custom_alias(client):
    response = client.post(
        "/shorten",
        json={"long_url": "https://example.com/custom", "custom_alias": "my-link"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["short_code"] == "my-link"
    assert body["custom_alias"] is True


def test_duplicate_custom_alias_rejected(client):
    payload = {"long_url": "https://example.com/a", "custom_alias": "dup-alias"}
    first = client.post("/shorten", json=payload)
    assert first.status_code == 201
    second = client.post("/shorten", json={"long_url": "https://example.com/b", "custom_alias": "dup-alias"})
    assert second.status_code == 409


def test_get_url_metadata(client):
    created = client.post("/shorten", json={"long_url": "https://example.com/meta"}).json()
    response = client.get(f"/urls/{created['short_code']}")
    assert response.status_code == 200
    body = response.json()
    assert body["long_url"] == "https://example.com/meta"
    assert body["active"] is True


def test_delete_url(client):
    created = client.post("/shorten", json={"long_url": "https://example.com/delete"}).json()
    deleted = client.delete(f"/urls/{created['short_code']}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
    redirect = client.get(f"/{created['short_code']}", follow_redirects=False)
    assert redirect.status_code == 404


def test_expired_url(client):
    expired_at = (datetime.utcnow() - timedelta(minutes=1)).isoformat()
    created = client.post(
        "/shorten",
        json={"long_url": "https://example.com/expired", "expires_at": expired_at},
    ).json()
    response = client.get(f"/{created['short_code']}", follow_redirects=False)
    assert response.status_code == 410
