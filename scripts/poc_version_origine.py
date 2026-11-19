"""Preuves de concept contre la version d'origine (v1) de l'API.

Tout se passe en local, sur une base SQLite jetable : aucun serveur n'est attaqué.
Usage : python scripts/poc_version_origine.py <dossier du code de la v1>
"""
import io, logging, os, sys, tempfile
db = tempfile.mktemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{db}"
sys.path.insert(0, sys.argv[1])
journal = io.StringIO()
from fastapi.testclient import TestClient
import main, database
from models import Variant, Order
from sqlmodel import Session, select
for h in list(logging.getLogger("sqlalchemy.engine.Engine").handlers):
    logging.getLogger("sqlalchemy.engine.Engine").removeHandler(h)
logging.getLogger("sqlalchemy.engine.Engine").addHandler(logging.StreamHandler(journal))
c = TestClient(main.app, raise_server_exceptions=False); c.__enter__()

def token(u, p):
    return {"Authorization": "Bearer " + c.post("/token", data={"username": u, "password": p}).json()["access_token"]}

r = c.post("/users/", json={"username": "attaquant", "password": "x"})
print(f"V1 | Le premier inscrit devient administrateur | is_admin={r.json()['is_admin']}")
print(f"V2 | Mot de passe d'un caractère accepté | HTTP {r.status_code}")
c.post("/users/", json={"username": "client", "password": "client123"})
h = token("client", "client123")
p = c.post("/products/", json={"name": "Robe"}, headers=h)
print(f"V3 | Un simple client crée un produit | HTTP {p.status_code}")
v = c.post("/variants/", json={"size": "S", "color": "noir", "price": 25, "alibaba_source_url": "https://fournisseur.example/x",
                               "stock_quantity": 10, "product_id": p.json()["id"]}, headers=h)
print(f"V3 | Un simple client crée une variante | HTTP {v.status_code}")
o = c.post("/orders/", json={"items": [{"variant_id": v.json()["id"], "quantity": -500}]}, headers=h)
with Session(database.engine) as s:
    stock = s.get(Variant, v.json()["id"]).stock_quantity
print(f"V4 | Commande de quantité -500 | HTTP {o.status_code}, stock passé de 10 à {stock}")
c.post("/orders/", json={"items": [{"variant_id": 999, "quantity": 1}]}, headers=h)
with Session(database.engine) as s:
    vides = [x for x in s.exec(select(Order)).all() if not x.items]
print(f"V5 | Commande invalide refusée mais enregistrée vide | {len(vides)} commande(s) vide(s) en base")
p2 = c.post("/products/", json={"name": "Produit sans variante"}, headers=h)
d = c.delete(f"/products/{p2.json()['id']}", headers=h)
print(f"V3 | Un simple client supprime un produit | HTTP {d.status_code}")
codes = {c.post("/token", data={"username": "client", "password": f"essai{i}"}).status_code for i in range(30)}
print(f"V6 | 30 mots de passe faux d'affilée | codes {sorted(codes)} (aucun blocage)")
print(f"V7 | Empreintes de mots de passe écrites dans les journaux | {journal.getvalue().count('$2b$12$')} occurrence(s)")
