from fastapi import FastAPI
from app.api.routes import auth, businesses, customers, products

app = FastAPI(
    title="Mercura API",
    description="Multi-Tenant Business Operations and Commerce Platform API",
    version="0.1.0"
)

app.include_router(auth.router)

app.include_router(
    businesses.router,
    prefix="/businesses",
    tags=["businesses"]
)

app.include_router(
    customers.router,
    prefix="/businesses/{business_id}/customers",
    tags=["customers"]
)

app.include_router(
    products.router,
    prefix="/businesses/{business_id}/products",
    tags=["products"]
)


@app.get("/")
async def root():
    return {
        "message": "Mercura API is running"
    }


@app.get("/health")
async def health():
    return {
        "service": "mercura_api",
        "status": "healthy"
    }