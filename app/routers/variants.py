from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.models import Product, User, Variant, VariantCreate, VariantRead, VariantReadAdmin
from app.securite import audit, exiger_admin

router = APIRouter(prefix="/variants", tags=["Variantes"])


@router.post("/", response_model=VariantReadAdmin, status_code=status.HTTP_201_CREATED)
def creer(donnees: VariantCreate, session: Session = Depends(get_session), admin: User = Depends(exiger_admin)):
    if not session.get(Product, donnees.product_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Produit non trouvé")
    variante = Variant.model_validate(donnees)
    session.add(variante)
    session.commit()
    session.refresh(variante)
    audit.info("variante_creee id=%s par=%s", variante.id, admin.username)
    return variante


@router.get("/{variant_id}", response_model=VariantRead)
def lire(variant_id: int, session: Session = Depends(get_session)):
    variante = session.get(Variant, variant_id)
    if not variante:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Variante non trouvée")
    return variante
