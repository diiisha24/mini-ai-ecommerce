from langchain_core.tools import StructuredTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.config import get_settings
from app.models import Order, Product, User

settings = get_settings()

# Built once per process, not per request: the model client just wraps a stateless HTTP
# transport/config, so recreating it on every chat message paid needless client/transport
# construction cost. What's per-request is the *tool set* below (that's what scopes the
# agent to the calling user), not the model client itself.
_model = ChatGoogleGenerativeAI(
    model=settings.gemini_model,
    google_api_key=settings.google_api_key,
    temperature=0,
)

SYSTEM_PROMPT = (
    "You are a helpful e-commerce support assistant. Answer questions about product "
    "availability, prices, and the current customer's own orders. Always call the "
    "provided tools to look up real data instead of guessing, and never reveal or guess "
    "information about another customer's orders. If the customer asks about 'my order' "
    "without giving an id, call list_my_orders first to find it. If something isn't found "
    "via the tools, say so plainly instead of making it up."
)


def _list_products(session: Session) -> str:
    products = session.exec(select(Product).where(Product.is_active == True)).all()  # noqa: E712
    if not products:
        return "No products are currently available."
    return "\n".join(f"- {p.name}: ${p.price} ({p.stock} in stock)" for p in products)


def _get_product_price(session: Session, product_name: str) -> str:
    products = session.exec(select(Product).where(Product.is_active == True)).all()  # noqa: E712
    match = next((p for p in products if product_name.lower() in p.name.lower()), None)
    if match is None:
        return f"I couldn't find a product matching '{product_name}'."
    return f"{match.name} costs ${match.price} and has {match.stock} units in stock."


def _describe_order(order: Order) -> str:
    item_lines = ", ".join(f"{i.quantity}x {i.product_name}" for i in order.items)
    return f"Order #{order.id} is '{order.status.value}'. Items: {item_lines}. Total: ${order.total_amount}."


def _get_order_status(session: Session, user: User, order_id: int) -> str:
    order = session.get(Order, order_id)
    if order is None or order.user_id != user.id:
        return f"I couldn't find an order #{order_id} on your account."
    return _describe_order(order)


def _list_my_orders(session: Session, user: User) -> str:
    orders = session.exec(
        select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc())
    ).all()
    if not orders:
        return "You don't have any orders yet."
    return "\n".join(_describe_order(o) for o in orders)


class ProductNameInput(BaseModel):
    product_name: str = Field(description="Name (or partial name) of the product to look up")


class OrderIdInput(BaseModel):
    order_id: int = Field(description="The numeric order id to look up")


def _build_tools(session: Session, user: User) -> list[StructuredTool]:
    # Tools are built per-request, closing over the authenticated user and DB session,
    # so the agent can only ever see that user's own orders - never another customer's.
    return [
        StructuredTool.from_function(
            func=lambda: _list_products(session),
            name="list_products",
            description="List all currently available products with their price and stock.",
        ),
        StructuredTool.from_function(
            func=lambda product_name: _get_product_price(session, product_name),
            name="get_product_price",
            description="Get the price and stock for a specific product by name.",
            args_schema=ProductNameInput,
        ),
        StructuredTool.from_function(
            func=lambda: _list_my_orders(session, user),
            name="list_my_orders",
            description=(
                "List all of the current customer's own orders with their status and total. "
                "Use this when the customer asks about 'my order' without giving a specific order id."
            ),
        ),
        StructuredTool.from_function(
            func=lambda order_id: _get_order_status(session, user, order_id),
            name="get_order_status",
            description="Get the status and items of one of the current customer's own orders, by order id.",
            args_schema=OrderIdInput,
        ),
    ]


def _extract_text(content: str | list) -> str:
    """Newer Gemini models return `.content` as a list of structured blocks
    (e.g. [{"type": "text", "text": "..."}]) rather than a plain string - normalize
    either shape down to plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return ""


def run_chat(session: Session, user: User, message: str) -> str:
    agent = create_react_agent(_model, _build_tools(session, user))
    result = agent.invoke({"messages": [("system", SYSTEM_PROMPT), ("user", message)]})
    reply = _extract_text(result["messages"][-1].content)
    return reply or "Sorry, I wasn't able to come up with a response to that. Could you rephrase?"
