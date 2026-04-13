#!/bin/bash
# =============================================================================
# setup.sh — Instalação inicial do Menu Livre na VPS
# Rodar UMA VEZ como root: bash deploy/setup.sh
# =============================================================================
set -e

REPO_DIR="/var/www/menu-livre"
BACKEND_DIR="$REPO_DIR/backend"
DEPLOY_USER="deploy"
DOMAIN="cardapio.paodemao.com.br"
REPO_URL="https://github.com/Kulasq/menu-livre.git"

echo ""
echo "============================================"
echo "  Setup Menu Livre — $DOMAIN"
echo "============================================"
echo ""

# 1. Atualizar sistema
echo "[1/9] Atualizando sistema..."
apt update -qq && apt upgrade -y -qq

# 2. Instalar dependências
echo "[2/9] Instalando dependências..."
apt install -y -qq python3.12 python3.12-venv python3-pip nginx certbot python3-certbot-nginx git

# 3. Clonar repositório
echo "[3/9] Clonando repositório..."
mkdir -p /var/www
if [ -d "$REPO_DIR" ]; then
    echo "  → Diretório já existe, pulando clone."
else
    git clone "$REPO_URL" "$REPO_DIR"
fi
chown -R "$DEPLOY_USER":"$DEPLOY_USER" "$REPO_DIR"

# 4. Criar virtualenv e instalar dependências Python
echo "[4/9] Criando virtualenv e instalando pacotes..."
cd "$BACKEND_DIR"
sudo -u "$DEPLOY_USER" python3.12 -m venv .venv
sudo -u "$DEPLOY_USER" .venv/bin/pip install --upgrade pip -q
sudo -u "$DEPLOY_USER" .venv/bin/pip install -r requirements.txt -q

# 5. Criar diretórios de dados
echo "[5/9] Criando diretórios de dados..."
sudo -u "$DEPLOY_USER" mkdir -p data uploads backups

# 6. Configurar .env
echo "[6/9] Configurando variáveis de ambiente..."
if [ ! -f "$BACKEND_DIR/.env" ]; then
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    echo ""
    echo "  ⚠️  ATENÇÃO: edite o arquivo antes de continuar:"
    echo "      nano $BACKEND_DIR/.env"
    echo ""
    echo "  Campos obrigatórios:"
    echo "    SECRET_KEY        → gere com: python3 -c \"import secrets; print(secrets.token_hex(32))\""
    echo "    REFRESH_SECRET_KEY → idem"
    echo "    WHATSAPP_NUMBER   → ex: 5581999999999"
    echo ""
    read -p "  Pressione ENTER após editar o .env para continuar..."
fi

# 7. Rodar migrations
echo "[7/9] Rodando migrations do banco..."
cd "$BACKEND_DIR"
sudo -u "$DEPLOY_USER" .venv/bin/alembic upgrade head

# 8. Instalar e iniciar serviço systemd
echo "[8/9] Configurando serviço systemd..."
cp "$REPO_DIR/deploy/cardapio.service" /etc/systemd/system/cardapio.service
systemctl daemon-reload
systemctl enable cardapio
systemctl start cardapio
echo "  → Status: $(systemctl is-active cardapio)"

# 9. Configurar Nginx + SSL
echo "[9/9] Configurando Nginx e SSL..."
cp "$REPO_DIR/deploy/nginx.conf" /etc/nginx/sites-available/cardapio
ln -sf /etc/nginx/sites-available/cardapio /etc/nginx/sites-enabled/cardapio
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo "  → Obtendo certificado SSL (Let's Encrypt)..."
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "lucas@resultadoefetivo.com.br" --redirect

echo ""
echo "============================================"
echo "  ✅ Setup concluído!"
echo "  Acesse: https://$DOMAIN/publico/"
echo "  Admin:  https://$DOMAIN/admin/"
echo "============================================"
echo ""
