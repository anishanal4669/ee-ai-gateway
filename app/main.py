from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.v1 import endpoints
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.rate_limiter import get_rate_limiter
from app.routing.router import _get_model_router
from app.config import get_settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    settings = get_settings()
    print("Initializing resources...")
    print(f"Starting Enterprise AI Gateway Mini on {settings.server_host}:{settings.server_port}")
    print(f" Tenant ID: {settings.tenant_id}")
    print(f" Issuer: {settings.issuer}")
    print(f" Audience: {settings.audience}")
    print(f" Redis URL: {settings.redis_url}")
    yield
    # Shutdown actions
    print("Shutting down Enterprise AI Gateway Mini")

    rate_limiter = get_rate_limiter()
    await rate_limiter.close()

    router = _get_model_router()
    await router.close()

    print("Connected resources closed.")

app = FastAPI(
    title="Enterprise AI Gateway Mini",
    version="1.0.0",
    description="A mini version of the Enterprise AI Gateway for routing requests to AI models.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)

app.include_router(endpoints.router, prefix="/api/v1", tags=["chat"])

@app.get("/")
async def root():
    return {
        "name": "Enterprise AI Gateway Mini",
        "version": "1.0.0",
        "description": "A mini version of the Enterprise AI Gateway for routing requests to AI models",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",     
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8088)