from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.database import get_session
from app.models import Product, ProductCreate, ProductRead, ProductReadWithVariants, ProductUpdate, User
from app.securite import audit, exiger_admin

router = APIRouter(prefix="/products", tags=["Produits"])


@router.get("/", response_model=List[ProductReadWithVariants])
def lister(session: Session = Depends(get_session)):
    return session.exec(select(Product)).all()


@router.get("/{product_id}", response_model=ProductReadWithVariants)
def lire(product_id: int, session: Session = Depends(get_session)):
    produit = session.get(Product, product_id)
    if not produit:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Produit non trouvé")
    return produit


@router.post("/", response_model=ProductReadWithVariants, status_code=status.HTTP_201_CREATED)
def creer(donnees: ProductCreate, session: Session = Depends(get_session), admin: User = Depends(exiger_admin)):
    produit = Product.model_validate(donnees)
    session.add(produit)
    session.commit()
    session.refresh(produit)
    audit.info("produit_cree id=%s par=%s", produit.id, admin.username)
    return produit


@router.patch("/{product_id}", response_model=ProductRead)
def modifier(product_id: int, donnees: ProductUpdate, session: Session = Depends(get_session),
             admin: User = Depends(exiger_admin)):
    produit = session.get(Product, product_id)
    if not produit:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Produit non trouvé")
    produit.sqlmodel_update(donnees.model_dump(exclude_unset=True))
    session.add(produit)
    session.commit()
    session.refresh(produit)
    audit.info("produit_modifie id=%s par=%s", product_id, admin.username)
    return produit


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer(product_id: int, session: Session = Depends(get_session), admin: User = Depends(exiger_admin)):
    produit = session.get(Product, product_id)
    if not produit:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Produit non trouvé")
    session.delete(produit)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Produit présent dans des commandes : impossible de le supprimer")
    audit.info("produit_supprime id=%s par=%s", product_id, admin.username)
