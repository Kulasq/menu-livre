#!/bin/bash
# =============================================================================
# setup.sh — Instalação inicial do Menu Livre na VPS
# Rodar UMA VEZ como root: bash deploy/setup.sh
#
# Pré-requisitos:
#   - Docker + Docker Compose v2 instalados
#   - Nginx Proxy Manager (NPM) rodando como container (porta 80/443)
#   - Usuário 'deploy' criado com acesso ao repo e permissão para systemctl
# =============================================================================
set -e

REPO_DIR="/var/www/menu-livre"
BACKEND_DIR="$REPO_DIR/backend"
DOCKER_DIR="$REPO_DIR/deploy/docker"
DEPLOY_USER="deploy"
REPO_URL="https://github.com/Kulasq/menu-livre.git"

echo ""
echo "============================================"
echo "  Setup Menu Livre"
echo "============================================"
echo ""

# 1. Atualizar sistema
echo "[1/9] Atualizando sistema..."
apt update -qq && apt upgrade -y -qq

# 2. Instalar dependências
echo "[2/9] Instalando dependências..."
apt install -y -qq python3.12 python3.12-venv python3-pip git

# 3. Configurar firewall (UFW)
echo "[3/9] Configurando firewall..."
ufw allow OpenSSH
ufw allow 80
ufw allow 443
# Permite containers Docker acessarem o uvicorn (Nginx container → API)
ufw allow from 172.16.0.0/12 to any port 8000 comment "Docker -> uvicorn"
ufw --force enable
echo "  → UFW: $(ufw status | head -1)"

# 4. Clonar repositório
echo "[4/9] Clonando repositório..."
mkdir -p /var/www
if [ -d "$REPO_DIR" ]; then
    echo "  → Diretório já existe, pulando clone."
else
    git clone "$REPO_URL" "$REPO_DIR"
fi
chown -R "$DEPLOY_USER":"$DEPLOY_USER" "$REPO_DIR"

# 5. Criar virtualenv e instalar dependências Python
echo "[5/9] Criando virtualenv e instalando pacotes..."
cd "$BACKEND_DIR"
sudo -u "$DEPLOY_USER" python3.12 -m venv .venv
sudo -u "$DEPLOY_USER" .venv/bin/pip install --upgrade pip -q
sudo -u "$DEPLOY_USER" .venv/bin/pip install -r requirements.txt -q

# 6. Criar diretórios de dados
echo "[6/9] Criando diretórios de dados..."
sudo -u "$DEPLOY_USER" mkdir -p data uploads backups

# 7. Configurar .env
echo "[7/9] Configurando variáveis de ambiente..."
if [ ! -f "$BACKEND_DIR/.env" ]; then
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    echo ""
    echo "  ⚠️  ATENÇÃO: edite o arquivo antes de continuar:"
    echo "      nano $BACKEND_DIR/.env"
    echo ""
    echo "  Campos obrigatórios:"
    echo "    SECRET_KEY         → gere com: python3 -c \"import secrets; print(secrets.token_hex(32))\""
    echo "    REFRESH_SECRET_KEY → idem"
    echo "    WHATSAPP_NUMBER    → ex: 5581999999999"
    echo "    CORS_ORIGINS       → ex: [\"https://cardapio.seudominio.com.br\",\"https://admin.seudominio.com.br\"]"
    echo ""
    read -p "  Pressione ENTER após editar o .env para continuar..."
fi

# 8. Rodar migrations e seed
echo "[8/9] Rodando migrations do banco..."
cd "$BACKEND_DIR"
sudo -u "$DEPLOY_USER" .venv/bin/alembic upgrade head

echo "  → Criando dados iniciais (admin + configuração)..."
sudo -u "$DEPLOY_USER" .venv/bin/python scripts/seed.py

# Garante que todos os arquivos do banco (incluindo WAL) pertencem ao deploy
chown -R "$DEPLOY_USER":"$DEPLOY_USER" "$BACKEND_DIR/data/"
chmod 640 "$BACKEND_DIR/data/"*.db 2>/dev/null || true

# 9. Instalar serviço systemd + subir container Nginx
echo "[9/9] Configurando serviços..."

# Backend (systemd)
cp "$REPO_DIR/deploy/cardapio.service" /etc/systemd/system/cardapio.service
systemctl daemon-reload
systemctl enable cardapio
systemctl start cardapio
echo "  → Backend: $(systemctl is-active cardapio)"

# Frontend (Docker)
cd "$DOCKER_DIR"
docker compose up -d
echo "  → Frontend (Nginx container): $(docker inspect -f '{{.State.Status}}' menu-livre-nginx)"

echo ""
echo "============================================"
echo "  ✅ Setup concluído!"
echo ""
echo "  Próximos passos:"
echo "  1. No NPM, configure os dois proxy hosts apontando para a porta 8080:"
echo "     cardapio.seudominio.com.br → http://172.17.0.1:8080"
echo "     admin.seudominio.com.br    → http://172.17.0.1:8080"
echo "  2. Ative SSL (Let's Encrypt) em cada proxy host no NPM."
echo "  3. Acesse https://admin.seudominio.com.br e faça login:"
echo "     Email: admin@exemplo.com | Senha: senha123"
echo "  4. Atualize email, senha e configurações da loja no painel."
echo "============================================"
echo ""
