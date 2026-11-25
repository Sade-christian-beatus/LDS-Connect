"""TOTP (RFC 6238) : vecteurs officiels et règles de vérification."""

import base64

from lds_api.domain import totp

# Secret des vecteurs de test de la RFC 6238 (SHA-1) : « 12345678901234567890 »
RFC_SECRET = base64.b32encode(b"12345678901234567890").decode()


def test_rfc6238_vectors():
    # Codes à 8 chiffres de la RFC, dont on garde les 6 derniers
    for t, expected in [(59, "94287082"), (1111111109, "07081804"), (2000000000, "69279037")]:
        assert totp.code_at(RFC_SECRET, totp.step_for(t)) == expected[-6:]


def test_verify_window_and_replay():
    secret = totp.new_secret()
    t = 1_800_000_000
    code = totp.code_at(secret, totp.step_for(t))
    step = totp.verify(secret, code, t)
    assert step == totp.step_for(t)
    assert totp.verify(secret, code, t + 30) == step  # horloge en avance d'un pas : toléré
    assert totp.verify(secret, code, t + 90) is None  # trop ancien
    assert totp.verify(secret, code, t, last_step=step) is None  # rejeu refusé
    assert totp.verify(secret, "12 34", t) is None
    assert totp.verify(secret, f"{code[:3]} {code[3:]}", t) == step  # espaces tolérés


def test_provisioning_uri():
    uri = totp.provisioning_uri("ABC", "admin@lds.bf")
    assert uri.startswith("otpauth://totp/LDS%20Connect%3Aadmin%40lds.bf?")
    assert "secret=ABC" in uri and "issuer=LDS+Connect" in uri
