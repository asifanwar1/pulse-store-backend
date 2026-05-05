from fastapi import FastAPI
from app.features.auth.router import router as auth_router
from app.features.users.router import router as users_router
from app.features.categories.router import router as categories_router
from app.features.products.router import router as products_router
from app.features.orders.router import router as orders_router
from app.features.cart.router import router as cart_router

app = FastAPI(title="Pulse Store API", version="1.0.0")

app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])
app.include_router(categories_router, prefix="/api/v1/categories", tags=["Categories"])
app.include_router(products_router, prefix="/api/v1/products", tags=["Products"])
app.include_router(orders_router, prefix="/api/v1/orders", tags=["Orders"])
app.include_router(cart_router, prefix="/api/v1/cart", tags=["Cart"])


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Pulse Store API is running"}
