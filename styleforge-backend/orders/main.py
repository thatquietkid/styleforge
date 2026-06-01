"""
Orders Microservice
Manages shopping carts, order placement, status updates, and order history.
"""
import sys
import os
from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.database import get_db
from common.models import Cart, CartItem, Order, OrderItem, OrderStatus, Product
from common.audit_client import fire_audit

app = FastAPI(title="Styleforge Orders Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://localhost:3000",
        "http://127.0.0.1:3000",
        "https://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CartItemAdd(BaseModel):
    product_id: int
    quantity: int

    @field_validator("quantity")
    @classmethod
    def positive_qty(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Quantity must be at least 1")
        return v

class CartItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    product_name: str
    unit_price: float
    subtotal: float

class CartResponse(BaseModel):
    cart_id: int
    items: List[CartItemResponse]
    total: float

class OrderItemOut(BaseModel):
    product_id: int
    quantity: int
    price: float

class OrderOut(BaseModel):
    id: int
    total_amount: float
    status: str
    created_at: datetime
    items: List[OrderItemOut]

class OrderCreate(BaseModel):
    """Place an order directly (no cart required)."""
    items: List[CartItemAdd]

class StatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        allowed = {s.value for s in OrderStatus}
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_user_id(request: Request) -> int:
    uid = request.headers.get("x-user-id")
    if not uid:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        return int(uid)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid x-user-id header")

async def _get_or_create_cart(user_id: int, db: AsyncSession) -> Cart:
    result = await db.execute(select(Cart).where(Cart.user_id == user_id))
    cart = result.scalar_one_or_none()
    if not cart:
        cart = Cart(user_id=user_id)
        db.add(cart)
        await db.commit()
        await db.refresh(cart)
    return cart

async def _build_cart_response(cart: Cart, db: AsyncSession) -> dict:
    items_result = await db.execute(select(CartItem).where(CartItem.cart_id == cart.id))
    cart_items = items_result.scalars().all()

    enriched = []
    total = 0.0
    for ci in cart_items:
        prod_result = await db.execute(select(Product).where(Product.id == ci.product_id))
        product = prod_result.scalar_one_or_none()
        if product:
            subtotal = round(product.price * ci.quantity, 2)
            total += subtotal
            enriched.append({
                "id": ci.id,
                "product_id": ci.product_id,
                "quantity": ci.quantity,
                "product_name": product.name,
                "unit_price": product.price,
                "subtotal": subtotal,
            })

    return {"cart_id": cart.id, "items": enriched, "total": round(total, 2)}

# ---------------------------------------------------------------------------
# Cart endpoints
# ---------------------------------------------------------------------------

@app.get("/api/v1/orders/cart")
async def get_cart(request: Request, db: AsyncSession = Depends(get_db)):
    """Return the current user's shopping cart."""
    user_id = _get_user_id(request)
    cart = await _get_or_create_cart(user_id, db)
    return await _build_cart_response(cart, db)


@app.post("/api/v1/orders/cart/items", status_code=201)
async def add_to_cart(body: CartItemAdd, request: Request, db: AsyncSession = Depends(get_db)):
    """Add a product to the cart. Increments quantity if already present."""
    user_id = _get_user_id(request)

    prod_result = await db.execute(select(Product).where(Product.id == body.product_id))
    if not prod_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Product not found")

    cart = await _get_or_create_cart(user_id, db)

    existing = await db.execute(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == body.product_id)
    )
    item = existing.scalar_one_or_none()
    if item:
        item.quantity += body.quantity
    else:
        item = CartItem(cart_id=cart.id, product_id=body.product_id, quantity=body.quantity)
        db.add(item)

    await db.commit()
    return await _build_cart_response(cart, db)


@app.put("/api/v1/orders/cart/items/{item_id}")
async def update_cart_item(item_id: int, body: CartItemAdd, request: Request, db: AsyncSession = Depends(get_db)):
    """Update quantity of a cart item (set to 0 to remove)."""
    user_id = _get_user_id(request)
    cart = await _get_or_create_cart(user_id, db)

    result = await db.execute(select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    if body.quantity == 0:
        await db.delete(item)
    else:
        item.quantity = body.quantity

    await db.commit()
    return await _build_cart_response(cart, db)


@app.delete("/api/v1/orders/cart/items/{item_id}", status_code=204)
async def remove_from_cart(item_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """Remove a specific item from the cart."""
    user_id = _get_user_id(request)
    cart = await _get_or_create_cart(user_id, db)

    result = await db.execute(select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    await db.delete(item)
    await db.commit()


@app.delete("/api/v1/orders/cart", status_code=204)
async def clear_cart(request: Request, db: AsyncSession = Depends(get_db)):
    """Remove all items from the cart."""
    user_id = _get_user_id(request)
    cart = await _get_or_create_cart(user_id, db)
    items_result = await db.execute(select(CartItem).where(CartItem.cart_id == cart.id))
    for item in items_result.scalars().all():
        await db.delete(item)
    await db.commit()

# ---------------------------------------------------------------------------
# Order endpoints
# ---------------------------------------------------------------------------

@app.post("/api/v1/orders/place", status_code=201)
async def place_order(body: OrderCreate, request: Request, db: AsyncSession = Depends(get_db)):
    """Place an order directly with a list of items."""
    user_id = _get_user_id(request)

    total = 0.0
    order_items = []

    for line in body.items:
        prod_result = await db.execute(select(Product).where(Product.id == line.product_id))
        product = prod_result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {line.product_id} not found")
        subtotal = product.price * line.quantity
        total += subtotal
        order_items.append(OrderItem(product_id=product.id, quantity=line.quantity, price=product.price))

    order = Order(user_id=user_id, total_amount=round(total, 2), status=OrderStatus.pending)
    db.add(order)
    await db.commit()
    await db.refresh(order)

    for oi in order_items:
        oi.order_id = order.id
        db.add(oi)
    await db.commit()

    fire_audit("orders", "INFO", "Order placed", {"user_id": user_id, "order_id": order.id, "total": total})
    return {"id": order.id, "total_amount": order.total_amount, "status": order.status.value}


@app.post("/api/v1/orders/checkout", status_code=201)
async def checkout(request: Request, db: AsyncSession = Depends(get_db)):
    """Convert current cart into an order and clear the cart."""
    user_id = _get_user_id(request)
    cart = await _get_or_create_cart(user_id, db)

    items_result = await db.execute(select(CartItem).where(CartItem.cart_id == cart.id))
    cart_items = items_result.scalars().all()

    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    total = 0.0
    order_items = []
    for ci in cart_items:
        prod_result = await db.execute(select(Product).where(Product.id == ci.product_id))
        product = prod_result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {ci.product_id} no longer exists")
        subtotal = product.price * ci.quantity
        total += subtotal
        order_items.append(OrderItem(product_id=product.id, quantity=ci.quantity, price=product.price))

    order = Order(user_id=user_id, total_amount=round(total, 2), status=OrderStatus.pending)
    db.add(order)
    await db.commit()
    await db.refresh(order)

    for oi in order_items:
        oi.order_id = order.id
        db.add(oi)

    # Clear cart
    for ci in cart_items:
        await db.delete(ci)

    await db.commit()
    fire_audit("orders", "INFO", "Checkout completed", {"user_id": user_id, "order_id": order.id})
    return {"id": order.id, "total_amount": order.total_amount, "status": order.status.value}


@app.get("/api/v1/orders/me")
async def get_my_orders(
    request: Request,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Return paginated list of the current user's orders with items."""
    user_id = _get_user_id(request)
    result = await db.execute(
        select(Order)
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    orders = result.scalars().all()

    out = []
    for order in orders:
        items_result = await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))
        items = [
            {"product_id": i.product_id, "quantity": i.quantity, "price": i.price}
            for i in items_result.scalars().all()
        ]
        out.append({
            "id": order.id,
            "total_amount": order.total_amount,
            "status": order.status.value,
            "created_at": order.created_at.isoformat(),
            "items": items,
        })
    return out


@app.get("/api/v1/orders/{order_id}")
async def get_order(order_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """Get a single order by ID (must belong to the requesting user)."""
    user_id = _get_user_id(request)
    result = await db.execute(select(Order).where(Order.id == order_id, Order.user_id == user_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    items_result = await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    items = [
        {"product_id": i.product_id, "quantity": i.quantity, "price": i.price}
        for i in items_result.scalars().all()
    ]
    return {
        "id": order.id,
        "total_amount": order.total_amount,
        "status": order.status.value,
        "created_at": order.created_at.isoformat(),
        "items": items,
    }


@app.patch("/api/v1/orders/{order_id}/status")
async def update_order_status(order_id: int, body: StatusUpdate, db: AsyncSession = Depends(get_db)):
    """Update order status (admin/system use)."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = OrderStatus(body.status)
    await db.commit()
    fire_audit("orders", "INFO", "Order status updated", {"order_id": order_id, "status": body.status})
    return {"id": order.id, "status": order.status.value}


# ---------------------------------------------------------------------------
# Global error handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def _global(request: Request, exc: Exception):
    fire_audit("orders", "ERROR", str(exc), {"path": request.url.path})
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
