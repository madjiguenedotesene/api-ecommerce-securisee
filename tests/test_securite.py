"""Tests de non-régression des 7 vulnérabilités trouvées dans la version d'origine (voir docs/audit.md)."""
import logging

from app.securite import limiteur  # noqa: F401
from tests.conftest import MDP, jeton


def test_V1_inscription_ne_donne_jamais_les_droits_admin(client):
    r = client.post("/users/", json={"username": "premier_inscrit", "password": MDP})
    assert r.status_code == 201
    assert r.json()["is_admin"] is False


def test_V2_mot_de_passe_faible_refuse(client):
    for faible in ("x", "motdepasse", "motdepasselong"):
        r = client.post("/users/", json={"username": f"u_{len(faible)}", "password": faible})
        assert r.status_code == 422


def test_V3_un_client_ne_peut_pas_gerer_le_catalogue(client, cliente, variante):
    assert client.post("/products/", json={"name": "X"}, headers=cliente).status_code == 403
    assert client.patch(f"/products/{variante['product_id']}", json={"name": "Y"}, headers=cliente).status_code == 403
    assert client.delete(f"/products/{variante['product_id']}", headers=cliente).status_code == 403
    v = dict(variante, size="M")
    v.pop("id")
    assert client.post("/variants/", json=v, headers=cliente).status_code == 403
    assert client.get("/orders/", headers=cliente).status_code == 403


def test_V3_sans_jeton_aucune_ecriture(client, variante):
    assert client.post("/products/", json={"name": "X"}).status_code == 401
    assert client.post("/orders/", json={"items": [{"variant_id": variante["id"], "quantity": 1}]}).status_code == 401


def test_V4_quantite_negative_ou_nulle_refusee_et_stock_intact(client, admin, cliente, variante):
    for q in (-500, 0, 1000):
        r = client.post("/orders/", json={"items": [{"variant_id": variante["id"], "quantity": q}]}, headers=cliente)
        assert r.status_code == 422
    stock = [i for o in client.get("/orders/", headers=admin).json() for i in o["items"]
             if i["variant"]["id"] == variante["id"]]
    assert stock == []


def test_V5_commande_invalide_ne_laisse_aucune_trace(client, cliente, variante):
    avant = len(client.get("/orders/me", headers=cliente).json())
    r = client.post("/orders/", json={"items": [{"variant_id": variante["id"], "quantity": 2},
                                                {"variant_id": 999_999, "quantity": 1}]}, headers=cliente)
    assert r.status_code == 404
    assert len(client.get("/orders/me", headers=cliente).json()) == avant
    ok = client.post("/orders/", json={"items": [{"variant_id": variante["id"], "quantity": 10}]}, headers=cliente)
    assert ok.status_code == 201  # le stock complet (10) est toujours disponible : rien n'a été décrémenté


def test_V6_force_brute_bloquee(client):
    client.post("/users/", json={"username": "victime", "password": MDP})
    codes = [client.post("/token", data={"username": "victime", "password": f"essai{i}"}).status_code
             for i in range(8)]
    assert codes[:5] == [401] * 5 and set(codes[5:]) == {429}
    # même le bon mot de passe est refusé pendant le blocage
    assert client.post("/token", data={"username": "victime", "password": MDP}).status_code == 429


def test_V7_aucune_empreinte_dans_les_journaux(client, caplog):
    with caplog.at_level(logging.DEBUG):
        client.post("/users/", json={"username": "journal", "password": MDP})
        client.post("/token", data={"username": "journal", "password": MDP})
    assert "$2b$" not in caplog.text and MDP not in caplog.text


def test_jeton_falsifie_ou_alg_none_refuse(client):
    import jwt
    faux = jwt.encode({"sub": "admin", "exp": 4102444800}, "mauvaise-cle-" + "y" * 32, algorithm="HS256")
    assert client.get("/users/me", headers={"Authorization": f"Bearer {faux}"}).status_code == 401
    none = jwt.encode({"sub": "admin", "exp": 4102444800}, None, algorithm="none")
    assert client.get("/users/me", headers={"Authorization": f"Bearer {none}"}).status_code == 401


def test_entetes_de_securite(client):
    r = client.get("/products/")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
