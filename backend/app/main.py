from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_assets, routes_health, routes_simulate
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(title="crypto-trading", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_health.router)
app.include_router(routes_assets.router)
app.include_router(routes_simulate.router)
