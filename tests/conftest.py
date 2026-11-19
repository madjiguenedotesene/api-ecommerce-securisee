import os
import tempfile

import pytest

os.environ["SECRET_KEY"] = "cle-de-test-uniquement-" + "x" * 32
os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mktemp(suffix='.db')}")
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "Admin-Test-2026!"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.securite import limiteur  # noqa: E402

MDP = "Client-Test-2026!"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def reinitialiser_limiteur():
    limiteur.echecs.clear()


def jeton(client, username, password):
    r = client.post("/token", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def admin(client):
    return jeton(client, "admin", "Admin-Test-2026!")


@pytest.fixture(scope="session")
def cliente(client):
    client.post("/users/", json={"username": "cliente", "password": MDP})
    return jeton(client, "cliente", MDP)


@pytest.fixture
def variante(client, admin):
    p = client.post("/products/", json={"name": "Robe courte"}, headers=admin).json()
    v = client.post("/variants/", json={"size": "S", "color": "kaki", "price": 25.99,
                                        "supplier_url": "https://fournisseur.example/robe", "stock_quantity": 10,
                                        "product_id": p["id"]}, headers=admin)
    assert v.status_code == 201, v.text
    return v.json()
