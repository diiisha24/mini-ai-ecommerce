from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from sqlalchemy import Index
from sqlmodel import Field, Relationship, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Role(str, Enum):
    customer = "customer"
    admin = "admin"


class OrderStatus(str, Enum):
    pending_payment = "pending_payment"
    paid = "paid"
    failed = "failed"
    cancelled = "cancelled"


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    google_sub: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    name: str
    picture: str | None = None
    role: Role = Field(default=Role.customer)
    created_at: datetime = Field(default_factory=utcnow)

    orders: list["Order"] = Relationship(back_populates="user")


class Product(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str = ""
    price: Decimal = Field(max_digits=10, decimal_places=2)
    image_url: str | None = None
    stock: int = Field(default=0)
    # Indexed: every storefront listing query filters WHERE is_active = true.
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Order(SQLModel, table=True):
    # Composite index instead of a single-column one on user_id: it still serves any
    # query that filters on user_id alone (leftmost-prefix), but also covers
    # list_my_orders' "WHERE user_id = ? ORDER BY created_at DESC" in one index scan
    # instead of an index lookup plus a separate sort.
    __table_args__ = (Index("ix_order_user_id_created_at", "user_id", "created_at"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    status: OrderStatus = Field(default=OrderStatus.pending_payment)
    total_amount: Decimal = Field(max_digits=10, decimal_places=2)
    stripe_checkout_session_id: str | None = Field(default=None, index=True)
    stripe_payment_intent_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    user: User = Relationship(back_populates="orders")
    items: list["OrderItem"] = Relationship(back_populates="order")

    @property
    def user_email(self) -> str:
        return self.user.email


class OrderItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id", index=True)
    # Indexed: without this, "which orders contain product X" (a natural admin/reporting
    # query, and what an inventory audit would run) does a full table scan. Postgres does
    # NOT auto-index foreign key columns the way it does primary keys.
    product_id: int = Field(foreign_key="product.id", index=True)
    product_name: str
    unit_price: Decimal = Field(max_digits=10, decimal_places=2)
    quantity: int

    order: Order = Relationship(back_populates="items")
