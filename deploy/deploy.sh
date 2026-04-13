#!/bin/bash
# =============================================================================
# deploy.sh — Atualização do Menu Livre na VPS
# Rodar como deploy: bash /var/www/menu-livre/deploy/deploy.sh
# =============================================================================
set -e

REPO_DIR="/var/www/menu-livre"
BACKEND_DIR="$REPO_DIR/backend"

echo ""
echo "=== Atualizando Menu Livre ==="

# Puxa código novo
cd "$REPO_DIR"
git pull origin main

# Instala novas dependências (rápido se não mudou nada)
cd "$BACKEND_DIR"
source .venv/bin/activate
pip install -r requirements.txt --quiet

# Roda migrations (seguro mesmo sem novas migrations)
alembic upgrade head

# Reinicia o serviço
sudo systemctl restart cardapio

echo "=== ✅ Deploy concluído! ==="
echo ""
