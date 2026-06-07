def test_rate_limit_exceeded(client, rate_limiter):
    created = client.post("/shorten", json={"long_url": "https://example.com/rate"}).json()
    code = created["short_code"]

    statuses = []
    for _ in range(6):
        response = client.get(f"/{code}", follow_redirects=False)
        statuses.append(response.status_code)

    assert statuses.count(302) == 5
    assert statuses.count(429) == 1

    metrics = client.get("/metrics").json()
    assert metrics["rate_limited_count"] >= 1
