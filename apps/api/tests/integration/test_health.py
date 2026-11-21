def test_health_answers_get_and_head(client):
    assert client.get("/api/v1/health").json() == {"status": "ok"}
    assert client.head("/api/v1/health").status_code == 200
