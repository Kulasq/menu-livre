from __future__ import annotations

import io
import os

from app.services.auth_service import hash_senha


def obter_token(client, usuario_admin) -> str:
    response = client.post("/api/auth/login", json={
        "email": "sara@paodeamao.com",
        "senha": "senha123",
    })
    return response.json()["access_token"]


# ── Upload ───────────────────────────────────────────────────────────────────

def test_upload_imagem_jpeg(client, usuario_admin, tmp_path, monkeypatch):
    """Upload de JPEG válido deve retornar URL."""
    monkeypatch.setattr("app.config.settings.UPLOAD_DIR", str(tmp_path))

    token = obter_token(client, usuario_admin)

    # Criar um JPEG mínimo válido (header JFIF)
    jpeg_header = b'\xff\xd8\xff\xe0' + b'\x00' * 100
    response = client.post(
        "/api/admin/upload",
        files={"file": ("foto.jpg", io.BytesIO(jpeg_header), "image/jpeg")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert data["url"].startswith("/uploads/")
    assert data["url"].endswith(".jpg")

    # Verificar que o arquivo foi salvo em disco
    filename = data["url"].split("/")[-1]
    assert os.path.exists(os.path.join(str(tmp_path), filename))


def test_upload_imagem_png(client, usuario_admin, tmp_path, monkeypatch):
    """Upload de PNG válido deve retornar URL."""
    monkeypatch.setattr("app.config.settings.UPLOAD_DIR", str(tmp_path))

    token = obter_token(client, usuario_admin)

    png_bytes = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
    response = client.post(
        "/api/admin/upload",
        files={"file": ("foto.png", io.BytesIO(png_bytes), "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["url"].endswith(".png")


def test_upload_tipo_invalido(client, usuario_admin, tmp_path, monkeypatch):
    """Upload de tipo não permitido deve retornar 400."""
    monkeypatch.setattr("app.config.settings.UPLOAD_DIR", str(tmp_path))

    token = obter_token(client, usuario_admin)

    response = client.post(
        "/api/admin/upload",
        files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert "não permitido" in response.json()["detail"].lower()


def test_upload_arquivo_grande(client, usuario_admin, tmp_path, monkeypatch):
    """Upload acima do limite deve retornar 400."""
    monkeypatch.setattr("app.config.settings.UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr("app.config.settings.MAX_UPLOAD_SIZE_MB", 1)

    token = obter_token(client, usuario_admin)

    # Criar arquivo de ~1.5MB (acima do limite de 1MB)
    big_file = b'\xff\xd8\xff\xe0' + b'\x00' * (1_500_000)
    response = client.post(
        "/api/admin/upload",
        files={"file": ("grande.jpg", io.BytesIO(big_file), "image/jpeg")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert "grande" in response.json()["detail"].lower()


def test_upload_sem_autenticacao(client, tmp_path, monkeypatch):
    """Upload sem token deve retornar 403."""
    monkeypatch.setattr("app.config.settings.UPLOAD_DIR", str(tmp_path))

    response = client.post(
        "/api/admin/upload",
        files={"file": ("foto.jpg", io.BytesIO(b'\xff\xd8\xff\xe0'), "image/jpeg")},
    )

    assert response.status_code == 403


def test_upload_e_associar_produto(client, usuario_admin, tmp_path, monkeypatch):
    """Fluxo completo: upload → criar produto com foto_url."""
    monkeypatch.setattr("app.config.settings.UPLOAD_DIR", str(tmp_path))

    token = obter_token(client, usuario_admin)
    headers = {"Authorization": f"Bearer {token}"}

    # Upload da foto
    jpeg_header = b'\xff\xd8\xff\xe0' + b'\x00' * 100
    upload_res = client.post(
        "/api/admin/upload",
        files={"file": ("burger.jpg", io.BytesIO(jpeg_header), "image/jpeg")},
        headers=headers,
    )
    assert upload_res.status_code == 200
    foto_url = upload_res.json()["url"]

    # Criar categoria
    cat = client.post(
        "/api/admin/categorias",
        json={"nome": "Hambúrgueres"},
        headers=headers,
    ).json()

    # Criar produto com foto_url
    produto_res = client.post(
        "/api/admin/produtos",
        json={
            "categoria_id": cat["id"],
            "nome": "Gorgonzolisson",
            "preco": 31.00,
            "foto_url": foto_url,
        },
        headers=headers,
    )

    assert produto_res.status_code == 201
    data = produto_res.json()
    assert data["foto_url"] == foto_url
    assert data["nome"] == "Gorgonzolisson"