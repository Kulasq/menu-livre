"""
Testes de segurança — verifica se os headers HTTP de proteção estão presentes
em todas as respostas da API, independente do endpoint.

Cobertura:
  - X-Content-Type-Options  → previne MIME sniffing
  - X-Frame-Options          → previne clickjacking
  - Content-Security-Policy  → restringe origens de recursos
  - Referrer-Policy          → controla o header Referer
  - Permissions-Policy       → desativa APIs do browser desnecessárias
"""
from __future__ import annotations
import pytest


class TestSecurityHeaders:
    """Verifica presença e valor dos headers de segurança em respostas da API."""

    def test_x_content_type_options_presente(self, client):
        """nosniff impede que o browser interprete arquivos com MIME type errado."""
        r = client.get("/health")
        assert r.headers.get("x-content-type-options") == "nosniff"

    def test_x_frame_options_presente(self, client):
        """DENY impede que a página seja embutida em iframe (clickjacking)."""
        r = client.get("/health")
        assert r.headers.get("x-frame-options") == "DENY"

    def test_referrer_policy_presente(self, client):
        """strict-origin-when-cross-origin limita vazamento de URL nos requests."""
        r = client.get("/health")
        assert r.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    def test_permissions_policy_presente(self, client):
        """Desativa acesso à câmera, microfone e geolocalização."""
        r = client.get("/health")
        policy = r.headers.get("permissions-policy", "")
        assert "camera=()" in policy
        assert "microphone=()" in policy
        assert "geolocation=()" in policy

    def test_content_security_policy_presente(self, client):
        """CSP restringe origens de recursos; frame-ancestors previne embedding."""
        r = client.get("/health")
        csp = r.headers.get("content-security-policy", "")
        assert "frame-ancestors 'none'" in csp

    def test_headers_presentes_em_rota_autenticada(self, client, usuario_admin):
        """Headers de segurança devem aparecer em rotas protegidas também."""
        r = client.post("/api/auth/login", json={
            "email": "sara@paodeamao.com",
            "senha": "senha123",
        })
        assert r.status_code == 200
        assert r.headers.get("x-content-type-options") == "nosniff"
        assert r.headers.get("x-frame-options") == "DENY"
        assert "frame-ancestors 'none'" in r.headers.get("content-security-policy", "")

    def test_headers_presentes_em_rota_publica(self, client):
        """Headers de segurança devem aparecer em rotas públicas (cardápio)."""
        r = client.get("/api/configuracao")
        # A rota pode retornar 404 se não houver config, mas os headers sempre aparecem
        assert r.headers.get("x-content-type-options") == "nosniff"
        assert r.headers.get("x-frame-options") == "DENY"

    def test_headers_presentes_em_erro_404(self, client):
        """Headers de segurança devem aparecer mesmo em respostas de erro."""
        r = client.get("/rota-que-nao-existe")
        assert r.status_code == 404
        assert r.headers.get("x-content-type-options") == "nosniff"
        assert r.headers.get("x-frame-options") == "DENY"

    def test_hsts_ausente_em_modo_debug(self, client):
        """HSTS não deve ser enviado em modo DEBUG (desenvolvimento sem HTTPS)."""
        r = client.get("/health")
        # Em testes, DEBUG=True (default do config de teste)
        assert "strict-transport-security" not in r.headers
