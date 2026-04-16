from pydantic import BaseModel, EmailStr, field_validator


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    usuario_nome: str
    usuario_role: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Minha Conta ──────────────────────────────────────────────────────────────

class UsuarioMeResponse(BaseModel):
    id: int
    nome: str
    email: str
    role: str

    model_config = {"from_attributes": True}


class UsuarioMeUpdate(BaseModel):
    nome: str
    email: EmailStr

    @field_validator("nome")
    @classmethod
    def nome_nao_vazio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nome não pode ser vazio")
        if len(v) > 100:
            raise ValueError("Nome muito longo (máx. 100 caracteres)")
        return v


class AlterarSenhaRequest(BaseModel):
    senha_atual: str
    senha_nova: str
    confirmar_senha: str

    @field_validator("senha_nova")
    @classmethod
    def senha_minima(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("A nova senha deve ter pelo menos 8 caracteres")
        return v

    @field_validator("confirmar_senha")
    @classmethod
    def senhas_conferem(cls, v: str, info) -> str:
        if "senha_nova" in info.data and v != info.data["senha_nova"]:
            raise ValueError("As senhas não conferem")
        return v