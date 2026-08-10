from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import auth, businesses, customers, products, invoices, payments, dashboard, assistant

app = FastAPI(
    title="Mercura API",
    description="Multi-Tenant Business Operations and Commerce Platform API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

app.include_router(
    invoices.router,
    prefix="/businesses/{business_id}/invoices",
    tags=["invoices"]
)

app.include_router(
    payments.router,
    prefix="/businesses/{business_id}",
    tags=["payments"]
)

app.include_router(
    dashboard.router,
    prefix="/businesses/{business_id}/dashboard",
    tags=["dashboard"]
)

app.include_router(
    assistant.router,
    prefix="/businesses/{business_id}/assistant",
    tags=["assistant"]
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