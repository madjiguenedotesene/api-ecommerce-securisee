import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlmodel import Session, SQLModel

from app import config
from app.database import engine
from app.models import User
from app.routers import auth, orders, products, users, variants
from app.securite import get_user, hacher

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("app")


def initialiser():
    """Crée les tables et l'administrateur initial (ADMIN_USERNAME / ADMIN_PASSWORD) s'il n'existe pas.

    Avec plusieurs processus (gunicorn -w 2), chaque processus exécute ce code au démarrage :
    sous PostgreSQL, un verrou consultatif sérialise l'initialisation pour éviter une
    double création (bug constaté lors des essais : le second processus plantait).
    """
    with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            conn.execute(text("SELECT pg_advisory_xact_lock(424242)"))
        SQLModel.metadata.create_all(conn)
        if config.ADMIN_USERNAME and config.ADMIN_PASSWORD:
            with Session(bind=conn) as s:
                if get_user(s, config.ADMIN_USERNAME) is None:
                    s.add(User(username=config.ADMIN_USERNAME, hashed_password=hacher(config.ADMIN_PASSWORD),
                               is_admin=True))
                    s.flush()
                    log.info("Administrateur initial créé : %s", config.ADMIN_USERNAME)


@asynccontextmanager
async def cycle_de_vie(app: FastAPI):
    initialiser()
    yield


app = FastAPI(title="API e-commerce sécurisée", version="2.0.0", lifespan=cycle_de_vie,
              description="Catalogue, variantes et commandes ; authentification JWT et rôles client / administrateur.")

if config.ORIGINES_CORS:
    app.add_middleware(CORSMiddleware, allow_origins=config.ORIGINES_CORS, allow_credentials=True,
                       allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"])


@app.middleware("http")
async def entetes_securite(request: Request, call_next):
    reponse = await call_next(request)
    reponse.headers["X-Content-Type-Options"] = "nosniff"
    reponse.headers["X-Frame-Options"] = "DENY"
    reponse.headers["Referrer-Policy"] = "no-referrer"
    reponse.headers["Cache-Control"] = "no-store"
    return reponse


for r in (auth, users, products, variants, orders):
    app.include_router(r.router)


@app.get("/", include_in_schema=False)
def accueil():
    return {"message": "API e-commerce : documentation sur /docs"}
