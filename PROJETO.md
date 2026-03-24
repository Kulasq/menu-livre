# Pão de Mão — Sistema de Cardápio Digital

> Documento de referência completo para o Claude Code.
> Leia este arquivo inteiro antes de criar qualquer arquivo ou escrever qualquer código.

---

## Visão Geral

Sistema de cardápio digital com painel administrativo para a hamburgueria **Pão de Mão** (Bonito, PE).
Substitui o OlaClick com funcionalidades equivalentes ao plano mais completo, hospedado em
infraestrutura própria (VPS Hostinger + Nginx + Docker + Cloudflare).

**Arquitetura pensada para escalar:** o sistema foi projetado para ser exclusivo da Pão de Mão
inicialmente, mas com estrutura que permite no futuro servir múltiplos restaurantes (multi-tenant).
Não implementar multi-tenant agora — apenas garantir que o banco e os models não impeçam isso depois.

---

## Arquitetura — MVC adaptado para API

O projeto segue o padrão **MVC** com uma camada extra de serviços:

| Camada | Onde | Responsabilidade |
|---|---|---|
| **Model** | `models/` | Estrutura do banco (SQLAlchemy) |
| **View** | `frontend/` | Interface do usuário (HTML/CSS/JS) |
| **Controller** | `routers/` | Recebe a requisição, valida, chama o service |
| **Service** | `services/` | Lógica de negócio e regras |

A separação entre `routers` e `services` é intencional:
o router nunca contém lógica — só chama o service certo.
Isso facilita manutenção: você sempre sabe onde está cada coisa.

---



| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12 + FastAPI 0.115+ + Pydantic v2 |
| Banco de dados | SQLite com WAL mode + Alembic migrations |
| ORM | SQLAlchemy 2.0 (síncrono — single worker) |
| Autenticação | JWT (access token 15min + refresh token 30 dias) |
| Frontend | HTML + CSS + JavaScript vanilla (sem framework) |
| Tempo real | WebSocket (FastAPI nativo) para fila de pedidos |
| Containerização | Docker + Docker Compose |
| Servidor | Nginx (reverse proxy) |
| Deploy | VPS Hostinger KVM 1 — Brasil (São Paulo) |
| DNS/CDN | Cloudflare (gratuito) |

> **Por que SQLite e não PostgreSQL?**
> Volume de escrita de uma hamburgueria pequena é baixo (< 50 pedidos/dia).
> SQLite com WAL mode aguenta bem. Se o negócio crescer muito, migrar para PostgreSQL
> é simples com Alembic — os models não precisam mudar.

> **Por que JS vanilla e não React/Vue?**
> O cardápio precisa carregar rápido no celular de qualquer cliente, inclusive em conexões
> lentas do interior de PE. Sem bundle, sem hydration, sem overhead de framework.

---

## Estrutura de Pastas

```
paodeamao/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── nginx/
│   └── nginx.conf
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── deps.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── usuario.py
│       │   ├── cliente.py
│       │   ├── categoria.py
│       │   ├── produto.py
│       │   ├── modificador.py
│       │   ├── combo.py
│       │   ├── pedido.py
│       │   └── mesa.py
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── auth.py
│       │   ├── cliente.py
│       │   ├── cardapio.py
│       │   ├── pedido.py
│       │   └── relatorio.py
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── auth.py
│       │   ├── admin/
│       │   │   ├── __init__.py
│       │   │   ├── cardapio.py
│       │   │   ├── pedidos.py
│       │   │   ├── clientes.py
│       │   │   ├── configuracoes.py
│       │   │   ├── relatorios.py
│       │   │   └── mesas.py
│       │   └── publico/
│       │       ├── __init__.py
│       │       ├── cardapio.py
│       │       ├── pedidos.py
│       │       └── clientes.py
│       └── services/
│           ├── auth_service.py
│           ├── cardapio_service.py
│           ├── pedido_service.py
│           ├── whatsapp_service.py
│           ├── relatorio_service.py
│           └── backup_service.py
└── frontend/
    ├── publico/          ← cardápio do cliente
    │   ├── index.html
    │   ├── css/
    │   │   └── style.css
    │   └── js/
    │       ├── app.js
    │       ├── cardapio.js
    │       ├── carrinho.js
    │       └── pedido.js
    └── admin/            ← painel administrativo
        ├── index.html    ← login
        ├── dashboard.html
        ├── cardapio.html
        ├── pedidos.html
        ├── clientes.html
        ├── relatorios.html
        ├── mesas.html
        ├── configuracoes.html
        ├── css/
        │   └── admin.css
        └── js/
            ├── auth.js
            ├── dashboard.js
            ├── cardapio.js
            ├── pedidos.js
            ├── websocket.js
            └── relatorios.js
```

---

## Banco de Dados — Models

### usuarios
Usuários do painel admin (dona + futuros funcionários).
```
id              INTEGER PK
nome            TEXT NOT NULL
email           TEXT UNIQUE NOT NULL
senha_hash      TEXT NOT NULL
role            TEXT DEFAULT 'admin'   -- 'superadmin' | 'admin' | 'operador'
ativo           BOOLEAN DEFAULT TRUE
criado_em       DATETIME
ultimo_acesso   DATETIME
```

### clientes
Clientes que fazem pedidos pelo cardápio público.
**Sem senha** — identificação exclusiva pelo telefone. Sem atrito no cadastro.
```
id              INTEGER PK
nome            TEXT NOT NULL
telefone        TEXT UNIQUE NOT NULL   -- identificador único, índice
endereco_padrao TEXT                   -- endereço salvo (sugerido nos próximos pedidos)
pontos          INTEGER DEFAULT 0      -- programa de fidelidade (futuro — já estruturado)
nivel_fidelidade TEXT DEFAULT 'bronze' -- 'bronze'|'prata'|'ouro' (futuro)
total_pedidos   INTEGER DEFAULT 0
total_gasto     REAL DEFAULT 0.0
segmento        TEXT DEFAULT 'novo'    -- calculado automaticamente (ver regras de negócio)
ativo           BOOLEAN DEFAULT TRUE
criado_em       DATETIME
ultimo_pedido   DATETIME
```

### categorias
```
id              INTEGER PK
nome            TEXT NOT NULL
descricao       TEXT
ordem           INTEGER DEFAULT 0      -- ordem de exibição no cardápio
ativo           BOOLEAN DEFAULT TRUE
criado_em       DATETIME
```

### produtos
```
id              INTEGER PK
categoria_id    INTEGER FK → categorias.id
nome            TEXT NOT NULL
descricao       TEXT
preco           REAL NOT NULL
foto_url        TEXT
disponivel      BOOLEAN DEFAULT TRUE
destaque        BOOLEAN DEFAULT FALSE  -- aparece em "Destaques"
controle_estoque BOOLEAN DEFAULT FALSE
estoque_atual   INTEGER DEFAULT 0
estoque_minimo  INTEGER DEFAULT 0
ordem           INTEGER DEFAULT 0
criado_em       DATETIME
atualizado_em   DATETIME
```

### variantes
Variações de um produto (ex: Pavê Pequeno / Pavê Médio).
```
id              INTEGER PK
produto_id      INTEGER FK → produtos.id
nome            TEXT NOT NULL          -- "Pequeno 110g" | "Médio 220g"
preco           REAL NOT NULL
disponivel      BOOLEAN DEFAULT TRUE
ordem           INTEGER DEFAULT 0
```

### grupos_modificadores
Grupos de opcionais (ex: "Ponto da carne", "Adicionais").
```
id              INTEGER PK
produto_id      INTEGER FK → produtos.id  -- NULL = global (reutilizável)
nome            TEXT NOT NULL              -- "Ponto da carne"
obrigatorio     BOOLEAN DEFAULT FALSE
selecao_minima  INTEGER DEFAULT 0
selecao_maxima  INTEGER DEFAULT 1          -- 1=radio, >1=checkbox
ordem           INTEGER DEFAULT 0
```

### modificadores
Opções dentro de um grupo (ex: "Mal passado", "Ao ponto", "Bem passado").
```
id              INTEGER PK
grupo_id        INTEGER FK → grupos_modificadores.id
nome            TEXT NOT NULL
preco_adicional REAL DEFAULT 0.0          -- 0 = sem custo extra
disponivel      BOOLEAN DEFAULT TRUE
ordem           INTEGER DEFAULT 0
```

### combos
```
id              INTEGER PK
nome            TEXT NOT NULL
descricao       TEXT
preco           REAL NOT NULL             -- preço total do combo
foto_url        TEXT
disponivel      BOOLEAN DEFAULT TRUE
destaque        BOOLEAN DEFAULT FALSE
ordem           INTEGER DEFAULT 0
criado_em       DATETIME
```

### combo_itens
```
id              INTEGER PK
combo_id        INTEGER FK → combos.id
produto_id      INTEGER FK → produtos.id
quantidade      INTEGER DEFAULT 1
```

### mesas
```
id              INTEGER PK
numero          INTEGER UNIQUE NOT NULL
nome            TEXT                      -- "Mesa 1", "Balcão", etc.
qrcode_url      TEXT                      -- URL do QR code gerado
ativa           BOOLEAN DEFAULT TRUE
criado_em       DATETIME
```

### pedidos
```
id              INTEGER PK
numero          TEXT UNIQUE NOT NULL      -- "PDM-0001" (Pão de Mão)
cliente_id      INTEGER FK → clientes.id
mesa_id         INTEGER FK → mesas.id    -- NULL se delivery/retirada
tipo            TEXT NOT NULL             -- 'delivery'|'retirada'|'mesa'
status          TEXT DEFAULT 'pendente'   -- ver fluxo abaixo
endereco_entrega TEXT                     -- endereço confirmado no pedido
subtotal        REAL NOT NULL
taxa_entrega    REAL DEFAULT 0.0
total           REAL NOT NULL
metodo_pagamento TEXT                     -- 'pix'|'dinheiro'|'cartao'
status_pagamento TEXT DEFAULT 'pendente'  -- 'pendente'|'pago'
observacao      TEXT
agendado_para   DATETIME                  -- NULL = pedido imediato
pontos_gerados  INTEGER DEFAULT 0         -- fidelidade (futuro)
criado_em       DATETIME
atualizado_em   DATETIME
```

**Fluxo de status do pedido:**
`pendente` → `confirmado` → `em_preparo` → `pronto` → `entregue` | `cancelado`

### pedido_itens
```
id              INTEGER PK
pedido_id       INTEGER FK → pedidos.id
produto_id      INTEGER FK → produtos.id  -- NULL se for combo
combo_id        INTEGER FK → combos.id    -- NULL se for produto
variante_id     INTEGER FK → variantes.id -- NULL se produto sem variante
nome_snapshot   TEXT NOT NULL             -- nome na hora do pedido
preco_snapshot  REAL NOT NULL             -- preço na hora do pedido
quantidade      INTEGER DEFAULT 1
subtotal        REAL NOT NULL
observacao      TEXT
```

### pedido_item_modificadores
```
id              INTEGER PK
pedido_item_id  INTEGER FK → pedido_itens.id
modificador_id  INTEGER FK → modificadores.id
nome_snapshot   TEXT NOT NULL
preco_snapshot  REAL NOT NULL
```

### configuracoes
Configurações gerais da loja.
```
id              INTEGER PK DEFAULT 1       -- sempre 1 linha
nome_loja       TEXT DEFAULT 'Pão de Mão'
logo_url        TEXT
banner_url      TEXT
whatsapp        TEXT NOT NULL
chave_pix       TEXT
tipo_chave_pix  TEXT                       -- 'celular'|'cpf'|'email'|'aleatoria'
taxa_entrega    REAL DEFAULT 0.0
pedido_minimo   REAL DEFAULT 0.0
tempo_entrega_min INTEGER DEFAULT 30
tempo_entrega_max INTEGER DEFAULT 50
aceitar_pedidos BOOLEAN DEFAULT TRUE
mensagem_fechado TEXT DEFAULT 'Estamos fechados no momento.'
instagram_url   TEXT
horarios_json   TEXT                       -- JSON com horários por dia da semana
atualizado_em   DATETIME
```

---

## Regras de Negócio

### Cardápio público (cliente)

1. **Identificação por telefone (sem senha):** cliente informa apenas nome + telefone.
   - Se telefone já existe → recupera cadastro automaticamente, sem perguntar nada
   - Se não existe → cria cadastro na hora
   - Sistema retorna token de sessão temporário (JWT, 24h) para manter o cliente identificado
   - Sem senha, sem "esqueci minha senha", sem fricção de nenhum tipo
2. **Endereço por pedido:** ao finalizar, cliente sempre confirma o endereço de entrega.
   Se tiver endereço salvo no cadastro, aparece pré-preenchido — mas pode trocar livremente.
   Para retirada, campo de endereço some completamente.
3. **Horário:** se loja estiver fechada (`aceitar_pedidos = false` ou fora do horário configurado),
   cliente navega e monta o carrinho normalmente, mas ao finalizar o sistema exibe aviso e
   registra o pedido com `agendado_para` = próxima abertura.
4. **Modificadores obrigatórios:** se grupo tiver `obrigatorio = true`, botão de finalizar
   fica desabilitado até o cliente selecionar uma opção.
5. **WhatsApp:** ao confirmar pedido, sistema gera a mensagem formatada e abre
   `https://wa.me/55NUMERO?text=MENSAGEM` em nova aba. Pedido salvo no banco simultaneamente.

### Mensagem WhatsApp (formato)
```
🍔 *Pão de Mão* — Novo Pedido!

📋 Pedido: PDM-0001
👤 Cliente: Lucas
📱 Telefone: 81 99999-9999

🚚 *Tipo:* Delivery
📍 *Endereço:* Rua das Flores, 123

🛍️ *Produtos:*
• 1x Bacontentão — R$ 44,00
  └ Ponto: Ao ponto
  └ + Bacon extra (+R$ 3,00)
• 1x Combo Clássico — R$ 35,00

💰 *Resumo:*
Subtotal: R$ 82,00
Entrega: R$ 5,00
*Total: R$ 87,00*

💳 *Pagamento:* PIX
🔑 Chave: 81 99600-8571

⏰ Pedido às 22:16
```

### Painel admin

1. **Autenticação:** JWT. Access token expira em 15min, refresh token em 30 dias. Login com email + senha (bcrypt rounds=12).
2. **Fila de pedidos em tempo real:** WebSocket. Quando chega novo pedido via API pública, o servidor transmite para todos os clientes admin conectados. Som de notificação no navegador.
3. **Impressão:** botão "Imprimir" no pedido gera uma página de impressão formatada (CSS print). Não requer impressora especial — funciona com qualquer impressora conectada ao computador/celular via navegador.
4. **Status do pedido:** admin pode avançar o status manualmente. Cada mudança de status atualiza `atualizado_em`.
5. **Controle de estoque:** se produto tiver `controle_estoque = true`, ao confirmar pedido o sistema decrementa `estoque_atual`. Se chegar a 0, produto fica `disponivel = false` automaticamente.
6. **Segmentação de clientes** (calculada automaticamente):
   - `novo`: 1 pedido
   - `frequente`: 2-5 pedidos, último pedido < 30 dias
   - `elite`: > 5 pedidos, último pedido < 30 dias
   - `dormindo`: último pedido entre 30-60 dias
   - `em_risco`: último pedido > 60 dias
7. **Migração de clientes:** endpoint `POST /admin/clientes/importar` aceita CSV com colunas `nome,telefone,total_pedidos`. Valida e importa sem duplicar telefones.

### Programa de fidelidade (estrutura futura — não implementar lógica agora)
- Campos já existem no banco: `pontos`, `nivel_fidelidade`, `pontos_gerados` no pedido
- No painel admin: seção "Fidelidade" visível mas com banner "Em breve"
- Quando ativado no futuro: admin configura pontos por pedido e recompensas

---

## API — Rotas

### Públicas (sem autenticação)

```
GET  /api/cardapio                     → categorias + produtos ativos
GET  /api/cardapio/destaques           → produtos com destaque=true
GET  /api/cardapio/combos              → combos ativos
GET  /api/configuracoes/publica        → nome, logo, horários, taxa entrega, status aberto/fechado

POST /api/clientes/identificar        → { telefone, nome? } → cria ou recupera cliente + retorna token 24h
PUT  /api/clientes/{id}                → atualizar nome/endereço (requer token do cliente)

POST /api/pedidos                      → criar pedido (retorna pedido + mensagem WhatsApp formatada)
GET  /api/pedidos/{id}                 → status de um pedido específico

WS   /ws/pedidos                       → apenas admin (token via query param)
```

### Admin (requer JWT)

```
POST /api/auth/login                   → { email, senha } → tokens
POST /api/auth/refresh                 → { refresh_token } → novo access token
POST /api/auth/logout                  → invalida refresh token

# Cardápio
GET    /api/admin/categorias
POST   /api/admin/categorias
PUT    /api/admin/categorias/{id}
DELETE /api/admin/categorias/{id}

GET    /api/admin/produtos
POST   /api/admin/produtos             → multipart/form-data (com foto)
PUT    /api/admin/produtos/{id}
DELETE /api/admin/produtos/{id}
PATCH  /api/admin/produtos/{id}/disponibilidade

GET    /api/admin/modificadores
POST   /api/admin/modificadores
PUT    /api/admin/modificadores/{id}
DELETE /api/admin/modificadores/{id}

GET    /api/admin/combos
POST   /api/admin/combos
PUT    /api/admin/combos/{id}
DELETE /api/admin/combos/{id}

# Pedidos
GET    /api/admin/pedidos              → filtros: status, tipo, data, page
GET    /api/admin/pedidos/{id}
PATCH  /api/admin/pedidos/{id}/status  → { status }
PATCH  /api/admin/pedidos/{id}/pagamento → { status_pagamento }

# Clientes
GET    /api/admin/clientes             → filtros: segmento, busca, page
GET    /api/admin/clientes/{id}
PUT    /api/admin/clientes/{id}
POST   /api/admin/clientes/importar    → CSV upload

# Relatórios
GET    /api/admin/relatorios/resumo    → ?periodo=hoje|semana|mes|custom&de=&ate=
GET    /api/admin/relatorios/produtos  → ranking de produtos vendidos
GET    /api/admin/relatorios/horarios  → pedidos por hora (heatmap)
GET    /api/admin/relatorios/clientes  → resumo de segmentação

# Mesas
GET    /api/admin/mesas
POST   /api/admin/mesas
PUT    /api/admin/mesas/{id}
DELETE /api/admin/mesas/{id}
GET    /api/admin/mesas/{id}/qrcode    → retorna QR code como imagem

# Configurações
GET    /api/admin/configuracoes
PUT    /api/admin/configuracoes
POST   /api/admin/configuracoes/logo   → upload logo
POST   /api/admin/configuracoes/banner → upload banner
```

---

## Segurança

### Dois níveis distintos de acesso

**Cliente (cardápio público) — sem senha, máxima simplicidade:**
- Identificação só por telefone
- Token de sessão temporário (JWT, 24h) gerado automaticamente no cadastro/login
- Token salvo no `localStorage` do navegador
- Sem acesso a dados de outros clientes — cada token só enxerga seus próprios pedidos
- Rate limiting: 10 pedidos/minuto por IP (evita spam)

**Admin (painel) — segurança completa, sem abrir mão de nada:**
- Login com email + senha (bcrypt rounds=12)
- JWT: access token 15min + refresh token 30 dias armazenado no banco
- Rate limiting no login: 5 tentativas/minuto por IP (bloqueia força bruta)
- Toda rota `/api/admin/*` exige JWT válido — verificado em `deps.py`
- WebSocket admin: token JWT obrigatório via query param `?token=`
- Logout real: refresh token é invalidado no banco
- Logs de auditoria: login com falha, mudança de status de pedido, alterações no cardápio

### Regras gerais (ambos os níveis)
- **SQL:** sempre via ORM ou parâmetros nomeados. Nunca f-string em queries.
- **Uploads:** validar MIME type real (não só extensão). Aceitar JPEG/PNG/WebP. Máximo 5MB. Salvar com nome UUID.
- **CORS:** apenas domínio da loja em produção.
- **Headers de segurança:** X-Content-Type-Options, X-Frame-Options, Referrer-Policy via middleware.
- **Produção:** `DEBUG=False`, `/docs` e `/redoc` desabilitados.
- **Secrets:** mínimo 32 chars aleatórios. Nunca hardcodados. Sempre em `.env`.

### Migrations — alterações no banco em produção

O projeto usa **Alembic** para controle de versão do banco de dados.
Qualquer alteração futura (nova coluna, nova tabela, índice) é feita via migration:

```bash
# Exemplo: ativar programa de fidelidade no futuro
alembic revision --autogenerate -m "ativar fidelidade — adicionar recompensas"
alembic upgrade head
```

O Alembic gera o SQL correto, aplica sem perder dados e permite reverter com `downgrade -1`.
**Nunca alterar o banco manualmente em produção** — sempre via migration versionada.

---

## Fases de Desenvolvimento

### Fase 1 — Core (mínimo para largar o OlaClick)
- [ ] Estrutura do projeto + Docker + banco de dados + migrations
- [ ] Cardápio público: listagem por categoria, produto com modificadores, combos
- [ ] Carrinho de compras (localStorage)
- [ ] Cadastro de cliente por telefone
- [ ] Finalização do pedido → salva no banco → gera mensagem WhatsApp
- [ ] Painel admin: login + gestão completa de produtos/categorias/modificadores/combos
- [ ] Deploy no servidor

### Fase 2 — Operação
- [ ] Fila de pedidos em tempo real (WebSocket) com notificação sonora
- [ ] Fluxo de status dos pedidos
- [ ] Impressão de pedido pelo navegador
- [ ] Controle de estoque
- [ ] Importação dos 872 clientes do OlaClick (via CSV)
- [ ] Gestão de mesas + QR code por mesa

### Fase 3 — Inteligência
- [ ] Relatórios: faturamento por período, produtos mais vendidos, horário de pico, ticket médio
- [ ] Segmentação automática de clientes
- [ ] Página de perfil do cliente (histórico de pedidos)
- [ ] Agendamento de pedidos fora do horário

### Fase 4 — Personalização
- [ ] Página de boas-vindas configurável (logo, banner, botões)
- [ ] Configurações completas: horários por dia, taxa de entrega, PIX, mensagem de fechado
- [ ] Seção "Fidelidade" no painel (estrutura visível, lógica em breve)

---

## Variáveis de Ambiente (.env)

```env
# Aplicação
APP_NAME=Pão de Mão
DEBUG=false
SECRET_KEY=                  # gerar: python -c "import secrets; print(secrets.token_hex(32))"
REFRESH_SECRET_KEY=          # outro secret diferente

# Banco
DATABASE_URL=sqlite:///./data/paodeamao.db

# CORS
CORS_ORIGINS=["https://paodeamao.com.br","https://www.paodeamao.com.br"]

# WhatsApp
WHATSAPP_NUMBER=5581996008571

# Uploads
UPLOAD_DIR=/app/uploads
MAX_UPLOAD_SIZE_MB=5

# Backup
BACKUP_DIR=/app/backups
BACKUP_HOUR=03               # hora do backup automático (madrugada)
```

---

## Docker Compose (produção)

```yaml
services:
  backend:
    build: ./backend
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./data:/app/data        # banco SQLite
      - ./uploads:/app/uploads  # fotos dos produtos
      - ./backups:/app/backups  # backups automáticos
    expose:
      - "8000"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      retries: 3

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./frontend:/usr/share/nginx/html    # serve os arquivos estáticos
      - ./certbot/conf:/etc/letsencrypt
    depends_on:
      - backend
```

---

## Nginx — Roteamento

```
/api/*          → proxy_pass para backend:8000
/ws/*           → proxy_pass para backend:8000 (WebSocket upgrade)
/uploads/*      → servir arquivos estáticos (fotos dos produtos)
/*              → servir frontend/publico/index.html
/admin/*        → servir frontend/admin/
```

---

## Backup Automático

- Backup diário às 3h via `schedule` dentro do backend
- Usar API nativa do SQLite (não `cp` simples — evita corrupção com WAL)
- Manter últimos 30 backups, deletar os mais antigos automaticamente
- Backup comprimido em `.gz`
- Log de cada backup realizado

---

## Convenções de Código

- **Python:** snake_case para variáveis e funções, PascalCase para classes
- **Endpoints:** sempre em português (ex: `/pedidos`, `/clientes`, `/cardapio`)
- **Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`)
- **Erros da API:** sempre retornar `{ "detail": "mensagem clara em português" }`
- **Datas:** sempre UTC no banco, converter para horário de Brasília (UTC-3) na exibição
- **Numeração de pedidos:** formato `PDM-XXXX` com zero-fill (PDM-0001, PDM-0042)
- **Fotos:** salvar com UUID como nome (`uuid4().hex + extensão`), nunca o nome original

---

## Informações da Loja

```
Nome:       Pão de Mão
Tipo:       Hamburgueria caseira
Cidade:     Bonito, PE
WhatsApp:   +55 81 99600-8571
Instagram:  @paodemao
Tipos:      Delivery + Retirada (Mesas: fase 2)
```

---

*Documento gerado em março de 2026. Atualizar conforme o projeto evoluir.*
