def test_metrics_endpoint(client):
    client.post("/shorten", json={"long_url": "https://example.com/metrics"})
    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.json()
    assert "redirect_count" in body
    assert "cache_hit_rate" in body
    assert body["urls_created_count"] >= 1
