"""Adresse réelle du visiteur derrière un reverse proxy (et refus des en-têtes falsifiés)."""

from types import SimpleNamespace

from lds_api.core.deps import client_ip


def req(peer, xff=None):
    headers = {"x-forwarded-for": xff} if xff else {}
    return SimpleNamespace(client=SimpleNamespace(host=peer), headers=headers)


def test_direct_connection_ignores_forwarded_header():
    # Un visiteur qui joint l'API directement ne peut pas choisir son adresse
    assert client_ip(req("41.207.10.5", "1.2.3.4")) == "41.207.10.5"


def test_behind_trusted_proxy_uses_forwarded_address():
    assert client_ip(req("172.18.0.5", "41.207.10.5")) == "41.207.10.5"
    assert client_ip(req("127.0.0.1", "41.207.10.5")) == "41.207.10.5"


def test_rightmost_untrusted_hop_wins_against_spoofing():
    # Le visiteur ajoute un faux en-tête ; le proxy ajoute la vraie adresse à droite
    assert client_ip(req("172.18.0.5", "9.9.9.9, 41.207.10.5")) == "41.207.10.5"
    # Chaîne de proxys internes : on remonte jusqu'à la première adresse publique
    assert client_ip(req("172.18.0.5", "41.207.10.5, 10.0.0.7")) == "41.207.10.5"


def test_proxy_without_header_and_garbage():
    assert client_ip(req("172.18.0.5")) == "172.18.0.5"
    assert client_ip(req("172.18.0.5", "pas-une-ip")) == "172.18.0.5"
    assert client_ip(req("testclient", "1.2.3.4")) == "testclient"
