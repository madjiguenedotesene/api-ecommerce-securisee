from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from app.config import DATABASE_URL

# echo=False : la version d'origine journalisait chaque requête SQL, empreintes de mots de passe comprises
_options = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True, connect_args=_options)

if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _cles_etrangeres(connexion, _):
        connexion.execute("PRAGMA foreign_keys=ON")  # SQLite n'applique pas les clés étrangères par défaut


def creer_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
