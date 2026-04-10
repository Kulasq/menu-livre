from pydantic_settings import BaseSettings
from pydantic import field_validator
import json


class Settings(BaseSettings):
    # Aplicação
    APP_NAME: str = "Menu Livre"
    DEBUG: bool = False

    # Segurança
    SECRET_KEY: str = "dev-secret-key-troque-em-producao"
    REFRESH_SECRET_KEY: str = "dev-refresh-key-troque-em-producao"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Banco
    DATABASE_URL: str = "sqlite:///./data/paodeamao.db"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:8080", "http://localhost:3000"]

    # WhatsApp
    WHATSAPP_NUMBER: str = "5581996008571"

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

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()