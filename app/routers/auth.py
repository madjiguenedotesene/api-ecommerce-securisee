from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.database import get_session
from app.securite import authentifier, creer_jeton, limiteur

router = APIRouter(tags=["Authentification"])


@router.post("/token")
def connexion(request: Request, form: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    limiteur.verifier(request, form.username)
    user = authentifier(session, form.username, form.password)
    if user is None:
        limiteur.echec(request, form.username)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiant ou mot de passe incorrect",
                            headers={"WWW-Authenticate": "Bearer"})
    limiteur.succes(request, form.username)
    # « bearer » est le type de jeton OAuth2, pas un mot de passe (faux positif de bandit)
    return {"access_token": creer_jeton(user.username), "token_type": "bearer"}  # nosec B105
