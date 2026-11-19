"""Modèles de données et schémas d'entrée / sortie (validation stricte des entrées)."""
from enum import Enum
from typing import List, Optional

from pydantic import field_validator
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, Relationship, SQLModel


# --- Utilisateurs -------------------------------------------------------------------
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str
    is_admin: bool = Field(default=False)


class UserCreate(SQLModel):
    username: str = Field(min_length=3, max_length=50, regex=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def robustesse(cls, v: str) -> str:
        classes = sum([any(c.islower() for c in v), any(c.isupper() for c in v),
                       any(c.isdigit() for c in v), any(not c.isalnum() for c in v)])
        if classes < 3:
            raise ValueError("Le mot de passe doit mélanger au moins 3 types de caractères "
                             "(minuscules, majuscules, chiffres, symboles)")
        return v


class UserRead(SQLModel):
    id: int
    username: str
    is_admin: bool


# --- Catalogue ------------------------------------------------------------------------
class ProductBase(SQLModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    image_urls: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))


class Product(ProductBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    variants: List["Variant"] = Relationship(back_populates="product", cascade_delete=True)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(SQLModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    image_urls: Optional[List[str]] = None


class ProductRead(ProductBase):
    id: int


class VariantBase(SQLModel):
    size: str = Field(index=True, max_length=20)
    color: str = Field(index=True, max_length=50)
    price: float = Field(gt=0)
    supplier_url: str = Field(max_length=500)          # donnée confidentielle : jamais exposée au public
    stock_quantity: int = Field(default=0, ge=0)
    product_id: int = Field(foreign_key="product.id", ondelete="CASCADE")


class Variant(VariantBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product: Product = Relationship(back_populates="variants")


class VariantCreate(VariantBase):
    pass


class VariantRead(SQLModel):
    """Vue PUBLIQUE : sans fournisseur ni stock."""
    id: int
    size: str
    color: str
    price: float
    product_id: int


class VariantReadAdmin(VariantBase):
    id: int


class ProductReadWithVariants(ProductRead):
    variants: List[VariantRead] = []


# --- Commandes ------------------------------------------------------------------------
class OrderStatus(str, Enum):
    en_attente = "en_attente"
    payee = "payee"
    expediee = "expediee"
    livree = "livree"
    annulee = "annulee"


class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    status: OrderStatus = Field(default=OrderStatus.en_attente, index=True)
    user_id: int = Field(foreign_key="user.id")
    user: User = Relationship()
    items: List["OrderItem"] = Relationship(back_populates="order")


class OrderItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    quantity: int = Field(gt=0)
    unit_price: float
    variant_id: int = Field(foreign_key="variant.id")
    order_id: int = Field(foreign_key="order.id")
    variant: Variant = Relationship()
    order: Order = Relationship(back_populates="items")


class OrderItemCreate(SQLModel):
    variant_id: int
    quantity: int = Field(gt=0, le=100)   # la version d'origine acceptait les quantités négatives


class OrderCreate(SQLModel):
    items: List[OrderItemCreate] = Field(min_length=1, max_length=50)


class OrderUpdate(SQLModel):
    status: OrderStatus


class OrderItemRead(SQLModel):
    id: int
    quantity: int
    unit_price: float
    variant: VariantRead


class OrderRead(SQLModel):
    id: int
    status: OrderStatus
    items: List[OrderItemRead] = []


class OrderItemReadAdmin(OrderItemRead):
    variant: VariantReadAdmin


class OrderReadAdmin(OrderRead):
    user: UserRead
    items: List[OrderItemReadAdmin] = []
