import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from lds_api.domain.signed_token import (
    LICENCE_PREFIX,
    TokenError,
    b64url_decode,
    b64url_encode,
    public_key_raw,
    sign,
    verify,
)

KEY = Ed25519PrivateKey.generate()
KEYS = {"k1": public_key_raw(KEY)}
PAYLOAD = {"kid": "k1", "n": "LDS27-00001", "nm": "Adama Ouédraogo", "vu": "2027-06-30"}


def test_sign_and_verify_roundtrip():
    token = sign(PAYLOAD, KEY, prefix=LICENCE_PREFIX)
    assert token.startswith("LDS1.")
    assert verify(token, KEYS, prefix=LICENCE_PREFIX) == PAYLOAD


def test_signature_is_deterministic_and_compact():
    a = sign(PAYLOAD, KEY, prefix=LICENCE_PREFIX)
    assert a == sign(dict(reversed(PAYLOAD.items())), KEY, prefix=LICENCE_PREFIX)
    assert len(a) < 300  # tient dans un QR de taille raisonnable


def test_tampered_payload_is_rejected():
    token = sign(PAYLOAD, KEY, prefix=LICENCE_PREFIX)
    prefix, body, sig = token.split(".")
    forged = b64url_decode(body).replace(b"2027-06-30", b"2099-06-30")
    with pytest.raises(TokenError, match="Signature invalide"):
        verify(f"{prefix}.{b64url_encode(forged)}.{sig}", KEYS, prefix=LICENCE_PREFIX)


def test_wrong_key_is_rejected():
    other = Ed25519PrivateKey.generate()
    token = sign(PAYLOAD, other, prefix=LICENCE_PREFIX)
    with pytest.raises(TokenError, match="Signature invalide"):
        verify(token, KEYS, prefix=LICENCE_PREFIX)


def test_unknown_kid_is_rejected():
    token = sign({**PAYLOAD, "kid": "k2"}, KEY, prefix=LICENCE_PREFIX)
    with pytest.raises(TokenError, match="inconnue"):
        verify(token, KEYS, prefix=LICENCE_PREFIX)


def test_key_rotation_old_tokens_still_verify():
    new_key = Ed25519PrivateKey.generate()
    old_token = sign(PAYLOAD, KEY, prefix=LICENCE_PREFIX)
    new_token = sign({**PAYLOAD, "kid": "k2"}, new_key, prefix=LICENCE_PREFIX)
    keys = {"k1": public_key_raw(KEY), "k2": public_key_raw(new_key)}
    assert verify(old_token, keys, prefix=LICENCE_PREFIX)["kid"] == "k1"
    assert verify(new_token, keys, prefix=LICENCE_PREFIX)["kid"] == "k2"


@pytest.mark.parametrize("bad", ["", "LDS1", "LDS1.abc", "XXX1.a.b", "LDS1.!!!.???", "LDS1.a.b.c"])
def test_malformed_tokens(bad):
    with pytest.raises(TokenError):
        verify(bad, KEYS, prefix=LICENCE_PREFIX)


def test_prefix_mismatch_is_rejected():
    token = sign(PAYLOAD, KEY, prefix="TKT1")
    with pytest.raises(TokenError):
        verify(token, KEYS, prefix=LICENCE_PREFIX)
