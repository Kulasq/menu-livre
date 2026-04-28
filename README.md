# Menu Livre — Cardápio Digital

Sistema web completo para gestão de pedidos e cardápio digital em restaurantes. O cliente acessa pelo celular, monta o pedido com modificadores e finaliza diretamente via WhatsApp. O administrador gerencia tudo pelo painel: cardápio, pedidos em tempo real, clientes, histórico e configurações.

> Desenvolvido como produto próprio para uso por clientes reais. Estrutura preparada para multi-tenant no futuro — múltiplos restaurantes na mesma instância.

---

## Por que esse projeto?

A maioria dos sistemas de cardápio digital cobra assinatura mensal cara por funcionalidades simples. Este projeto entrega o mesmo — e mais — com hospedagem própria, custo fixo baixo e controle total dos dados.

---

## Stack

| Camada | Tecnologia | Decisão |
|---|---|---|
| Backend | Python 3.12 + FastAPI 0.115 + Pydantic v2 | Performance, tipagem forte, OpenAPI automático |
| Banco | SQLite + WAL mode + Alembic migrations | Suficiente para restaurantes pequenos; migração para PostgreSQL é trivial com Alembic |
| ORM | SQLAlchemy 2.0 (sync) | Queries explícitas, sem magic assíncrono desnecessário |
| Auth | JWT — access 15min + refresh 7d | Segurança real sem depender de Redis ou sessão server-side |
| Frontend | HTML + CSS + JavaScript vanilla | Zero bundle, carrega rápido em conexões lentas de qualquer celular |
| Imagens | Pillow | Redimensionamento e otimização automática no upload |
| Infra | Docker + Nginx + VPS Ubuntu 24.04 | ~R$50/mês, controle total, sem vendor lock-in |

---

## Funcionalidades

### Cardápio público (cliente)
- Listagem por categoria com fotos, descrições e seção de **destaques** no topo
- **Modificadores** por produto — grupos de opcionais e obrigatórios (ex: ponto da carne, adicionais)
- Carrinho persistente com resumo de valores e drawer animado com drag-to-close no mobile
- Identificação por telefone — sem senha, sem cadastro obrigatório
- **Endereços salvos** — cliente escolhe um endereço anterior ou digita um novo no checkout
- Checkout multi-step: identificação → endereço → agendamento → pagamento → observação
- Pagamento em dinheiro com **campo de troco** calculado automaticamente
- **Pix completo**: QR code com valor exato gerado dinamicamente + botão "Copia e Cola"
- Mensagem WhatsApp formatada automaticamente ao finalizar o pedido
- **Histórico de pedidos** — o cliente consulta todos os pedidos pelo celular; botão "Pedir igual" refaz um pedido anterior
- Se a loja estiver fechada: pedido é **agendado automaticamente** para a próxima abertura

### Painel administrativo
- Login com JWT — access token em memória, refresh token em localStorage
- **Minha conta** — alterar nome, e-mail e senha diretamente pelo avatar no header
- **Modo escuro** — toggle de 3 estados (claro / escuro / sistema) ao lado do avatar, sem flash ao navegar entre páginas; persiste em localStorage e sincroniza entre abas
- Gestão completa de categorias, produtos e **grupos de modificadores** (drag & drop de ordem)
- Upload de fotos com redimensionamento automático (Pillow) — salvo com UUID
- **Fila de pedidos** com atualização automática a cada 5s + **notificação sonora em qualquer tela** do painel
- Fluxo de status: Pendente → Confirmado → Preparando → Pronto → Entregue / Cancelado
- **PDV split-screen** — admin abre pedidos de Balcão, Retirada ou Delivery diretamente pelo painel, sem depender do cliente; busca de cliente por nome com autocomplete
- **Histórico de pedidos** com filtro por período (calendário), seleção múltipla e exclusão em lote
- Impressão de cupom térmico 80mm ou 57mm direto pelo navegador, com layout otimizado
- **Gestão de clientes** — tabela com busca, filtros por segmento RFM, histórico de pedidos e endereços salvos por cliente; cadastro e edição pelo painel
- **Segmentação RFM automática** — 6 segmentos (Campeão, Leal, Novo, Em risco, Inativo, Comum) calculados a cada pedido
- Controle de horários de funcionamento por dia da semana
- Fechar loja manualmente com um clique; aceitar agendamentos fora do horário (configurável)
- Configurações: taxa de entrega, pedido mínimo, tempo estimado, chave Pix, Instagram, mensagem de fechado
- **Aparência configurável** — logo, banner, paleta de cores completa (primária, secundária, fundo, fonte, banner); zero hardcode no frontend público
- Dashboard com resumo do dia: pedidos, faturamento, ticket médio e status por tipo

### Segurança
- XSS: `esc()` com `textContent` em todo output de dados dinâmicos
- Security headers: `X-Content-Type-Options`, `X-Frame-Options`, `CSP` via middleware FastAPI
- CORS restrito ao domínio em produção (`CORS_ORIGINS` no `.env`)
- JWT access token em memória (não persiste entre reloads sem o refresh)
- Rate limiting por IP nas rotas de autenticação (slowapi)
- Uploads: validação de MIME type real, nome UUID, limite de 5MB

### Deploy
- VPS Ubuntu 24.04, Nginx em Docker (portas separadas para cardápio e admin)
- Uvicorn como systemd service (porta 8000, sem expor diretamente)
- SSL via Nginx Proxy Manager nas portas 80/443
- Script de deploy automatizado: `git pull` → `pip install` → `alembic upgrade head` → `systemctl restart` → `docker compose restart nginx`

---

## Arquitetura

```
backend/app/
├── models/     → SQLAlchemy — estrutura do banco
├── schemas/    → Pydantic v2 — validação e serialização
├── services/   → toda a lógica de negócio aqui (nunca nos routers)
└── routers/    → recebem, validam e delegam ao service

frontend/
├── admin/      → painel administrativo (HTML + CSS + JS vanilla)
│   └── js/icons.js  → biblioteca de ícones SVG centralizada (Heroicons)
└── publico/    → cardápio do cliente
```

O projeto segue arquitetura **Fat Server / Thin Client** com camada de service separada. Routers nunca contêm lógica de negócio — apenas recebem, validam e delegam. Isso garante que os testes unitários cubram 100% das regras sem depender de HTTP.

---

## Rodando localmente

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

```bash
# Frontend
cd frontend && python -m http.server 3000
# Admin:   http://localhost:3000/admin/
# Público: http://localhost:3000/publico/
```

### Variáveis de ambiente

Copie `.env.example` para `.env` e preencha:

```env
SECRET_KEY=          # python -c "import secrets; print(secrets.token_hex(32))"
REFRESH_SECRET_KEY=  # valor diferente do anterior
DATABASE_URL=sqlite:///./data/cardapio.db
WHATSAPP_NUMBER=     # com DDI, sem espaços (ex: 5581999999999)
CARDAPIO_URL=        # URL pública do cardápio (aparece no topo da mensagem WhatsApp)
CORS_ORIGINS=["http://localhost:3000"]
DEBUG=true
```

---

## Testes

```bash
cd backend && pytest tests/ -v
```

361 testes (unitários + integração). Os testes de integração rodam com SQLite em memória — sem banco real, sem estado compartilhado entre testes.

---

## Em desenvolvimento

- **Grupos de modificadores reutilizáveis** entre múltiplos produtos
- **Múltiplos horários por dia** — intervalos como 11h–14h e 18h–22h
- **Selos de produto** — ícones de "picante", "vegetariano", "low carb" etc. ao lado do nome
- **Pagamento por link de cartão** com taxa de 5% calculada automaticamente
- **Acompanhamento de pedido** — página pública para o cliente consultar o status em tempo real
- **Busca no cardápio** — filtro client-side de itens em tempo real
- **Controle de estoque** — produto fica indisponível automaticamente ao zerar
- **Relatórios avançados** — faturamento por período, produtos mais vendidos, horário de pico
- **Programa de fidelidade** — estrutura de pontos e níveis (bronze/prata/ouro)

---

## Licença

MIT — use, adapte e distribua livremente.
