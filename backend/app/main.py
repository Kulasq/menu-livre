import os
from fastapi.staticfiles import StaticFiles
from app.routers.admin import upload as admin_upload
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.routers import auth
from app.routers.admin import cardapio as admin_cardapio
from app.routers.admin import pedidos as admin_pedidos
from app.routers.admin import dashboard as admin_dashboard
from app.routers.admin import configuracoes as admin_configuracoes
from app.routers.publico import cardapio as publico_cardapio
from app.routers.publico import cliente as publico_clientes
from app.routers.publico import pedidos as publico_pedidos


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adiciona headers de segurança HTTP em todas as respostas da API.
    Primeira linha de defesa contra XSS, clickjacking e MIME sniffing.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # CSP: a API serve JSON — não renderiza HTML com scripts externos.
        # Em produção, o Nginx adiciona CSP mais restrito para o frontend.
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        if not settings.DEBUG:
            # HSTS só em produção (HTTPS obrigatório)
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=settings.APP_NAME,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Ordem importa: SecurityHeaders antes do CORS para garantir aplicação em todas as respostas
app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    # Em desenvolvimento (DEBUG=true) permite qualquer origem — cobre file://, Live Server, etc.
    # Em produção (DEBUG=false) exige que CORS_ORIGINS esteja configurado com o domínio real.
    allow_origins=["*"] if settings.DEBUG else settings.CORS_ORIGINS,
    allow_credentials=not settings.DEBUG,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(admin_cardapio.router)
app.include_router(admin_pedidos.router)
app.include_router(admin_upload.router)
app.include_router(admin_dashboard.router)
app.include_router(admin_configuracoes.router)
app.include_router(publico_cardapio.router)
app.include_router(publico_clientes.router)
app.include_router(publico_pedidos.router)


@app.get("/health")
def health():
    return {"status": "ok"}

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")