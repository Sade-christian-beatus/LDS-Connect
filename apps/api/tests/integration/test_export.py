import json

from lds_api.services.export import export_all


def test_export_masks_secrets_by_default(db, seeded, tmp_path):
    result = export_all(db, tmp_path)
    folder = tmp_path / result["directory"].split("/")[-1]
    assert result["teams"] == 20 and result["persons"] == 740
    assert "refresh_tokens" not in result
    persons = json.loads((folder / "persons.json").read_text(encoding="utf-8"))
    assert {p["cnib_number"] for p in persons} == {"***"}
    users = json.loads((folder / "users.json").read_text(encoding="utf-8"))
    assert "password_hash" not in users[0]
    assert (folder / "matches.csv").read_text(encoding="utf-8").startswith("id,")
    assert json.loads((folder / "manifest.json").read_text())["include_sensitive"] is False


def test_export_sensitive_decrypts(db, seeded, tmp_path):
    result = export_all(db, tmp_path, include_sensitive=True)
    folder = tmp_path / result["directory"].split("/")[-1]
    persons = json.loads((folder / "persons.json").read_text(encoding="utf-8"))
    assert all(p["cnib_number"].startswith("X") for p in persons)
