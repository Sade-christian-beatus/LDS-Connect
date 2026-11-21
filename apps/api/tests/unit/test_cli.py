import base64

from cryptography.hazmat.primitives.serialization import load_pem_private_key

from lds_api.cli import generate_keys, main


def test_generate_keys_are_valid():
    keys = generate_keys()
    assert len(base64.b64decode(keys["FIELD_ENCRYPTION_KEY"])) == 32
    assert len(base64.b64decode(keys["BLIND_INDEX_KEY"])) == 32
    load_pem_private_key(base64.b64decode(keys["LICENCE_SIGNING_KEY"]), password=None)
    assert len(keys["JWT_SECRET"]) >= 32


def test_write_only_fills_empty_values(tmp_path):
    env = tmp_path / ".env"
    env.write_text("JWT_SECRET=deja-defini\nFIELD_ENCRYPTION_KEY=\nAUTRE=1\n", encoding="utf-8")
    main(["gen-keys", "--write", str(env)])
    content = env.read_text(encoding="utf-8")
    assert "JWT_SECRET=deja-defini\n" in content
    assert "FIELD_ENCRYPTION_KEY=\n" not in content
    assert "AUTRE=1" in content
