def test_redirect_success(client):
    created = client.post("/shorten", json={"long_url": "https://example.com/target"}).json()
    response = client.get(f"/{created['short_code']}", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/target"


def test_unknown_code_returns_404(client):
    response = client.get("/does-not-exist", follow_redirects=False)
    assert response.status_code == 404


def test_cache_hit_on_second_redirect(client, cache):
    created = client.post("/shorten", json={"long_url": "https://example.com/cache"}).json()
    code = created["short_code"]

    first = client.get(f"/{code}", follow_redirects=False)
    assert first.headers.get("X-Cache-Hit") == "false"

    second = client.get(f"/{code}", follow_redirects=False)
    assert second.headers.get("X-Cache-Hit") == "true"
    assert cache.is_cached(code)
