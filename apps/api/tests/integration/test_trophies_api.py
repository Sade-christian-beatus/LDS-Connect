"""Course aux trophées (cinq distinctions) et nom de la saison."""

from sqlalchemy import delete, select

from lds_api.models import Player, PlayerStat, SquadMembership
from lds_api.models.enums import Position


def _stat(db, season, player, **values):
    m = db.scalar(select(SquadMembership).where(SquadMembership.person_id == player.person_id))
    db.add(PlayerStat(season_id=season.id, person_id=player.person_id, team_id=m.team_id, **values))


def test_trophy_race(client, db, seeded):
    db.execute(delete(PlayerStat))
    gk = db.scalars(select(Player).where(Player.position == Position.GOALKEEPER).limit(3)).all()
    fw = db.scalar(select(Player).where(Player.position == Position.FORWARD).limit(1))
    _stat(db, seeded, gk[0], appearances=4, clean_sheets=2)
    _stat(db, seeded, gk[1], appearances=5, clean_sheets=2)  # même total, plus de matchs : devant
    _stat(db, seeded, gk[2], appearances=3, clean_sheets=0, man_of_the_match=1)
    _stat(db, seeded, fw, appearances=4, clean_sheets=3, man_of_the_match=2)  # pas un gardien
    db.commit()
    r = client.get("/api/v1/trophies")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["season"] == "Saison 2026-2027"
    codes = [t["code"] for t in body["trophies"]]
    assert codes == ["winner", "top_scorer", "goalkeeper", "man_of_the_match", "best_player"]
    by = {t["code"]: t for t in body["trophies"]}

    # Vainqueur : finale non jouée → leaders des deux poules
    assert by["winner"]["status"] == "provisional" and len(by["winner"]["leaders"]) == 2

    # Buteurs : mêmes données que la page Statistiques
    stats = client.get("/api/v1/stats?limit=5").json()["scorers"]
    assert [c["display_name"] for c in by["top_scorer"]["contenders"]] == [
        s["display_name"] for s in stats
    ]

    # Gardiens : uniquement des gardiens, clean sheets puis matchs joués
    keepers = by["goalkeeper"]["contenders"]
    ids = [k["person_id"] for k in keepers]
    assert ids == [str(gk[1].person_id), str(gk[0].person_id), str(gk[2].person_id)]
    assert [k["rank"] for k in keepers] == [1, 2, 3]
    assert [k["person_id"] for k in by["goalkeeper"]["leaders"]] == [str(gk[1].person_id)]

    # Homme du match : nombre de distinctions, tous postes
    motm = by["man_of_the_match"]["contenders"]
    assert [m["value"] for m in motm] == [2, 1]
    assert motm[0]["person_id"] == str(fw.person_id)

    # Meilleur joueur : scrutin « joueur de la saison » (ou vote à venir)
    assert by["best_player"]["status"] in {"upcoming", "vote_open", "vote_closed", "awarded"}

    # Aucune donnée privée : nom d'usage seulement
    for t in body["trophies"]:
        for c in t["contenders"]:
            assert set(c) <= {"rank", "person_id", "display_name", "team", "value", "detail"}


def test_rename_season(client, as_admin, seeded):
    r = client.patch(
        f"/api/v1/admin/seasons/{seeded.id}",
        json={"name": "Saison 2026-2027 (bis)"},
        headers=as_admin,
    )
    assert r.status_code == 200 and r.json()["name"] == "Saison 2026-2027 (bis)"
    assert client.get("/api/v1/seasons/current").json()["name"] == "Saison 2026-2027 (bis)"
