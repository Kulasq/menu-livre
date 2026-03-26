from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth
from app.routers.admin import cardapio as admin_cardapio
from app.routers.admin import pedidos as admin_pedidos
from app.routers.publico import cardapio as publico_cardapio
from app.routers.publico import cliente as publico_clientes
from app.routers.publico import pedidos as publico_pedidos


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=settings.APP_NAME,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin_cardapio.router)
app.include_router(admin_pedidos.router)
app.include_router(publico_cardapio.router)
app.include_router(publico_clientes.router)
app.include_router(publico_pedidos.router)


@app.get("/health")
def health():
    return {"status": "ok"}