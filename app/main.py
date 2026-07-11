from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.limiter import limiter
from app.features.auth.router import router as auth_router
from app.features.users.router import router as users_router
from app.features.categories.router import router as categories_router
from app.features.media.router import router as media_router
from app.features.products.router import router as products_router
from app.features.orders.router import router as orders_router
from app.features.cart.router import router as cart_router
from app.features.shipments.router import router as shipments_router
from app.features.revenue.router import router as revenue_router
from app.features.dashboard.router import router as dashboard_router
from app.features.offers.router import router as offers_router
from app.features.wallet.router import router as wallet_router
from app.features.favourites.router import router as favourites_router
from app.features.reviews.router import router as reviews_router

app = FastAPI(title="Pulse Store API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5176"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate-limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])
app.include_router(categories_router,
                   prefix="/api/v1/categories", tags=["Categories"])
app.include_router(media_router, prefix="/api/v1/media", tags=["Media"])
app.include_router(
    products_router, prefix="/api/v1/products", tags=["Products"])
app.include_router(orders_router, prefix="/api/v1/orders", tags=["Orders"])
app.include_router(
    shipments_router, prefix="/api/v1/shipments", tags=["Shipments"])
app.include_router(revenue_router, prefix="/api/v1/revenue", tags=["Revenue"])
app.include_router(
    dashboard_router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(cart_router, prefix="/api/v1/cart", tags=["Cart"])
app.include_router(offers_router, prefix="/api/v1/offers", tags=["Offers"])
app.include_router(wallet_router, prefix="/api/v1/wallet", tags=["Wallet"])
app.include_router(favourites_router,
                   prefix="/api/v1/favourites", tags=["Favourites"])
app.include_router(reviews_router, prefix="/api/v1/reviews", tags=["Reviews"])


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Pulse Store API is running"}
