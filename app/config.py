"""Configuration lue dans l'environnement : aucun secret ni valeur par défaut dangereuse dans le code."""
import os


class ErreurConfiguration(RuntimeError):
    pass


def _obligatoire(nom: str) -> str:
    valeur = os.environ.get(nom)
    if not valeur:
        raise ErreurConfiguration(f"Variable d'environnement {nom} manquante (voir .env.example)")
    return valeur


SECRET_KEY = _obligatoire("SECRET_KEY")
if len(SECRET_KEY) < 32:
    raise ErreurConfiguration("SECRET_KEY doit faire au moins 32 caractères (python -c \"import secrets; print(secrets.token_urlsafe(48))\")")
DATABASE_URL = _obligatoire("DATABASE_URL")

ALGORITHME_JWT = "HS256"
DUREE_JETON_MINUTES = int(os.environ.get("DUREE_JETON_MINUTES", "30"))

# Protection contre la force brute sur /token
ECHECS_MAX = int(os.environ.get("ECHECS_CONNEXION_MAX", "5"))
FENETRE_ECHECS_SECONDES = int(os.environ.get("FENETRE_ECHECS_SECONDES", "900"))

# Compte administrateur créé au démarrage s'il n'existe pas (jamais par simple inscription)
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

ORIGINES_CORS = [o for o in os.environ.get("ORIGINES_CORS", "").split(",") if o]
