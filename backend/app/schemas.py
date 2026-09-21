from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models import OrderStatus, Role


# ---- Auth ----
class GoogleLoginRequest(BaseModel):
    id_token: str


class UserRead(BaseModel):
    id: int
    email: str
    name: str
    picture: str | None
    role: Role

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
    # True only on the request that actually created the account, so the frontend can
    # show new-user-registration vs existing-user-login as distinct, observable outcomes
    # of the same Google Sign-In flow.
    is_new_user: bool


# ---- Products ----
class ProductRead(BaseModel):
    id: int
    name: str
    description: str
    price: Decimal
    image_url: str | None
    stock: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    name: str
    description: str = ""
    price: Decimal = Field(gt=0)
    image_url: str | None = None
    stock: int = Field(ge=0, default=0)
    is_active: bool = True


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0)
    image_url: str | None = None
    stock: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


# ---- Orders ----
class CheckoutItem(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class CheckoutRequest(BaseModel):
    items: list[CheckoutItem]


class CheckoutResponse(BaseModel):
    order_id: int
    checkout_url: str


class OrderItemRead(BaseModel):
    product_id: int
    product_name: str
    unit_price: Decimal
    quantity: int

    model_config = ConfigDict(from_attributes=True)


class OrderRead(BaseModel):
    id: int
    status: OrderStatus
    total_amount: Decimal
    created_at: datetime
    user_email: str
    items: list[OrderItemRead]

    model_config = ConfigDict(from_attributes=True)


# ---- AI Agent ----
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    reply: str
