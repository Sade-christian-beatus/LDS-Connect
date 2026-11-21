import pytest
from cryptography.exceptions import InvalidTag

from lds_api.core.crypto import (
    cnib_index,
    get_cipher,
    normalize_identifier,
    normalize_phone,
    phone_index,
)


def test_encrypt_roundtrip_and_random_nonce():
    c = get_cipher()
    a, b = c.encrypt("B12345678"), c.encrypt("B12345678")
    assert a != b  # nonce aléatoire : deux chiffrements différents
    assert c.decrypt(a) == c.decrypt(b) == "B12345678"
    assert b"B12345678" not in a


def test_tampered_ciphertext_is_rejected():
    blob = bytearray(get_cipher().encrypt("70 00 00 00"))
    blob[-1] ^= 0x01
    with pytest.raises(InvalidTag):
        get_cipher().decrypt(bytes(blob))


@pytest.mark.parametrize(
    "raw",
    ["70 12 34 56", "+226 70 12 34 56", "0022670123456", "226-70-12-34-56"],
)
def test_phone_normalization(raw):
    assert normalize_phone(raw) == "+22670123456"


def test_phone_index_is_stable_across_formats():
    assert phone_index("70 12 34 56") == phone_index("+22670123456")
    assert phone_index("70 12 34 56") != phone_index("70 12 34 57")


def test_cnib_index_ignores_format_and_purpose_separates_domains():
    assert normalize_identifier("b 1234-5678") == "B12345678"
    assert cnib_index("b 1234-5678") == cnib_index("B12345678")
    assert cnib_index("70123456") != phone_index("70123456")
