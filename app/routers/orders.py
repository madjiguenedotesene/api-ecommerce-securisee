from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.models import Order, OrderCreate, OrderItem, OrderRead, OrderReadAdmin, OrderUpdate, User, Variant
from app.securite import audit, exiger_admin, get_current_user

router = APIRouter(prefix="/orders", tags=["Commandes"])


@router.post("/", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def commander(donnees: OrderCreate, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    """Transaction unique : toutes les lignes sont vérifiées AVANT toute écriture.
    En cas d'erreur, rien n'est enregistré (ni commande vide, ni stock modifié)."""
    quantites = {}
    for ligne in donnees.items:
        quantites[ligne.variant_id] = quantites.get(ligne.variant_id, 0) + ligne.quantity
    variantes = {}
    for variant_id, qte in quantites.items():
        # FOR UPDATE : verrouille la ligne de stock sous PostgreSQL (deux commandes simultanées)
        v = session.exec(select(Variant).where(Variant.id == variant_id).with_for_update()).first()
        if v is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Variante {variant_id} non trouvée")
        if v.stock_quantity < qte:
            raise HTTPException(status.HTTP_409_CONFLICT, f"Stock insuffisant pour la variante {variant_id}")
        variantes[variant_id] = v

    commande = Order(user_id=user.id)
    session.add(commande)
    for variant_id, qte in quantites.items():
        v = variantes[variant_id]
        v.stock_quantity -= qte
        session.add(OrderItem(order=commande, variant=v, quantity=qte, unit_price=v.price))
    session.commit()
    session.refresh(commande)
    return commande


@router.get("/me", response_model=List[OrderRead])
def mes_commandes(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    return session.exec(select(Order).where(Order.user_id == user.id)).all()


@router.get("/", response_model=List[OrderReadAdmin])
def toutes(session: Session = Depends(get_session), admin: User = Depends(exiger_admin)):
    return session.exec(select(Order)).all()


@router.patch("/{order_id}", response_model=OrderReadAdmin)
def changer_statut(order_id: int, donnees: OrderUpdate, session: Session = Depends(get_session),
                   admin: User = Depends(exiger_admin)):
    commande = session.get(Order, order_id)
    if not commande:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Commande non trouvée")
    commande.status = donnees.status
    session.add(commande)
    session.commit()
    session.refresh(commande)
    audit.info("commande_statut id=%s statut=%s par=%s", order_id, donnees.status.value, admin.username)
    return commande
