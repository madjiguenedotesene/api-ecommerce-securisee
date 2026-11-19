"""Authentification : bcrypt, jetons JWT (PyJWT), rôles et protection contre la force brute."""
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from app import config
from app.database import get_session
from app.models import User

audit = logging.getLogger("audit")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Empreinte factice : vérifiée quand l'utilisateur n'existe pas, pour que le temps de réponse
# ne révèle pas si un identifiant existe (énumération par mesure du temps)
_EMPREINTE_FACTICE = bcrypt.hashpw(b"factice", bcrypt.gensalt()).decode()


def hacher(mot_de_passe: str) -> str:
    return bcrypt.hashpw(mot_de_passe.encode(), bcrypt.gensalt()).decode()


def verifier(mot_de_passe: str, empreinte: str) -> bool:
    return bcrypt.checkpw(mot_de_passe.encode(), empreinte.encode())


def get_user(session: Session, username: str):
    return session.exec(select(User).where(User.username == username)).first()


def authentifier(session: Session, username: str, mot_de_passe: str):
    user = get_user(session, username)
    if user is None:
        verifier(mot_de_passe, _EMPREINTE_FACTICE)
        return None
    return user if verifier(mot_de_passe, user.hashed_password) else None


def creer_jeton(username: str) -> str:
    maintenant = datetime.now(timezone.utc)
    charge = {"sub": username, "iat": maintenant,
              "exp": maintenant + timedelta(minutes=config.DUREE_JETON_MINUTES)}
    return jwt.encode(charge, config.SECRET_KEY, algorithm=config.ALGORITHME_JWT)


def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    erreur = HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiants invalides",
                           headers={"WWW-Authenticate": "Bearer"})
    try:
        charge = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHME_JWT],
                            options={"require": ["exp", "sub"]})
    except jwt.PyJWTError:
        raise erreur
    user = get_user(session, charge["sub"])
    if user is None:
        raise erreur
    return user


def exiger_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        audit.warning("refus_admin utilisateur=%s", user.username)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Droits administrateur requis")
    return user


class LimiteurConnexions:
    """Bloque un couple (identifiant, IP) après N échecs dans une fenêtre glissante.

    En mémoire : suffisant pour un seul processus. En production multi-instances,
    le même principe s'appuie sur Redis.
    """

    def __init__(self):
        self.echecs = defaultdict(deque)

    def _cle(self, request: Request, username: str):
        return (username.lower(), request.client.host if request.client else "?")

    def _purger(self, cle):
        limite = time.monotonic() - config.FENETRE_ECHECS_SECONDES
        while self.echecs[cle] and self.echecs[cle][0] < limite:
            self.echecs[cle].popleft()

    def verifier(self, request: Request, username: str):
        cle = self._cle(request, username)
        self._purger(cle)
        if len(self.echecs[cle]) >= config.ECHECS_MAX:
            audit.warning("connexion_bloquee utilisateur=%s ip=%s", *cle)
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                                "Trop de tentatives. Réessayez plus tard.",
                                headers={"Retry-After": str(config.FENETRE_ECHECS_SECONDES)})

    def echec(self, request: Request, username: str):
        cle = self._cle(request, username)
        self.echecs[cle].append(time.monotonic())
        audit.info("connexion_echouee utilisateur=%s ip=%s", *cle)

    def succes(self, request: Request, username: str):
        self.echecs.pop(self._cle(request, username), None)


limiteur = LimiteurConnexions()
