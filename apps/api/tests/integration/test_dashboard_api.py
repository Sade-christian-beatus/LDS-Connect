"""Tableau de bord de l'administration (B5)."""


def test_dashboard(client, as_admin, as_club, seeded):
    assert client.get("/api/v1/admin/dashboard", headers=as_club).status_code == 403
    r = client.get("/api/v1/admin/dashboard", headers=as_admin)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["season"] == seeded.name
    c = body["counts"]
    assert c["matches_total"] > 0 and c["licences_active"] > 0
    assert set(c) >= {"tickets_sold", "revenue_fcfa", "refunds_due", "votes_flagged"}
