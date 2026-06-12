from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator
import json

# Valores padrão de desenvolvimento — proibidos em produção (DEBUG=false)
_DEV_SECRET_KEY = "dev-secret-key-troque-em-producao"
_DEV_REFRESH_SECRET_KEY = "dev-refresh-key-troque-em-producao"


class Settings(BaseSettings):
    # Aplicação
    APP_NAME: str = "Menu Livre"
    DEBUG: bool = False

    # Segurança
    SECRET_KEY: str = _DEV_SECRET_KEY
    REFRESH_SECRET_KEY: str = _DEV_REFRESH_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Banco
    DATABASE_URL: str = "sqlite:///./data/cardapio.db"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:8080", "http://localhost:3000"]

    # WhatsApp
    WHATSAPP_NUMBER: str = ""
    CARDAPIO_URL: str = ""

    # Uploads
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 5

    # Backup
    BACKUP_DIR: str = "./backups"
    BACKUP_HOUR: int = 3

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return [v]
        return v

    @model_validator(mode="after")
    def _exigir_secrets_em_producao(self):
        # Em produção (DEBUG=false) os secrets padrão de dev são proibidos:
        # com eles, qualquer um forjaria JWTs válidos. Falha alto na inicialização.
        if not self.DEBUG and (
            self.SECRET_KEY == _DEV_SECRET_KEY
            or self.REFRESH_SECRET_KEY == _DEV_REFRESH_SECRET_KEY
        ):
            raise ValueError(
                "SECRET_KEY/REFRESH_SECRET_KEY estão com os valores padrão de "
                "desenvolvimento e DEBUG=false. Defina chaves reais no .env de produção "
                "(gere com: python -c \"import secrets; print(secrets.token_hex(32))\")."
            )
        return self

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()