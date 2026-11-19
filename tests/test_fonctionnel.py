"""Parcours métier : catalogue public, commande, gestion par l'administrateur."""


def test_le_public_ne_voit_ni_fournisseur_ni_stock(client, variante):
    produits = client.get("/products/").json()
    v = [x for p in produits for x in p["variants"] if x["id"] == variante["id"]][0]
    assert "supplier_url" not in v and "stock_quantity" not in v
    assert "supplier_url" not in client.get(f"/variants/{variante['id']}").json()


def test_commande_complete(client, admin, cliente, variante):
    r = client.post("/orders/", json={"items": [{"variant_id": variante["id"], "quantity": 3}]}, headers=cliente)
    assert r.status_code == 201
    commande = r.json()
    assert commande["status"] == "en_attente" and commande["items"][0]["unit_price"] == 25.99
    assert "supplier_url" not in commande["items"][0]["variant"]

    vue_admin = [o for o in client.get("/orders/", headers=admin).json() if o["id"] == commande["id"]][0]
    assert vue_admin["items"][0]["variant"]["stock_quantity"] == 7
    assert vue_admin["user"]["username"] == "cliente"

    r = client.patch(f"/orders/{commande['id']}", json={"status": "expediee"}, headers=admin)
    assert r.status_code == 200 and r.json()["status"] == "expediee"
    assert client.patch(f"/orders/{commande['id']}", json={"status": "n_importe_quoi"}, headers=admin).status_code == 422


def test_stock_insuffisant(client, cliente, variante):
    r = client.post("/orders/", json={"items": [{"variant_id": variante["id"], "quantity": 11}]}, headers=cliente)
    assert r.status_code == 409


def test_suppression_produit_par_admin(client, admin, variante):
    assert client.delete(f"/products/{variante['product_id']}", headers=admin).status_code == 204
    assert client.get(f"/products/{variante['product_id']}").status_code == 404


def test_produit_deja_commande_non_supprimable(client, admin, cliente, variante):
    client.post("/orders/", json={"items": [{"variant_id": variante["id"], "quantity": 1}]}, headers=cliente)
    assert client.delete(f"/products/{variante['product_id']}", headers=admin).status_code == 409
