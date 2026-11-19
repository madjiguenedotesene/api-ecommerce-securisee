from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.models import User, UserCreate, UserRead
from app.securite import get_current_user, get_user, hacher

router = APIRouter(prefix="/users", tags=["Utilisateurs"])


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def inscription(donnees: UserCreate, session: Session = Depends(get_session)):
    """Crée un compte CLIENT. Un administrateur ne peut jamais être créé par inscription."""
    if get_user(session, donnees.username):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ce nom d'utilisateur est déjà pris")
    user = User(username=donnees.username, hashed_password=hacher(donnees.password), is_admin=False)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.get("/me", response_model=UserRead)
def mon_compte(user: User = Depends(get_current_user)):
    return user
