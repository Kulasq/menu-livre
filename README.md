# Cardápio Digital

Sistema web completo para gestão de pedidos e cardápio digital em restaurantes. O cliente acessa pelo celular, monta o pedido com modificadores e finaliza diretamente via WhatsApp. O administrador gerencia tudo pelo painel: cardápio, pedidos em tempo real, horários e configurações.

> Desenvolvido como produto próprio para uso por clientes. Estrutura preparada para multi-tenant no futuro — múltiplos restaurantes na mesma instância.

---

## Por que esse projeto?

A maioria dos sistemas de cardápio digital cobra assinatura mensal cara por funcionalidades simples. Este projeto entrega o mesmo (e mais) com hospedagem própria, custo fixo baixo e controle total dos dados.

---

## Stack

| Camada | Tecnologia | Decisão |
|---|---|---|
| Backend | Python 3.12 + FastAPI + Pydantic v2 | Performance, tipagem forte, docs automáticas |
| Banco | SQLite + WAL mode + Alembic | Suficiente para restaurantes pequenos; migração para PostgreSQL é trivial com Alembic |
| Auth | JWT (access 15min + refresh 30d) | Segurança real sem depender de Redis |
| Frontend | HTML + CSS + JavaScript vanilla | Zero bundle, carrega rápido em conexões lentas de qualquer celular |
| Infra | Docker + Nginx + VPS | Custo ~R$50/mês, controle total, sem lock-in |

---

## Funcionalidades

### Cardápio público (cliente)
- Listagem por categoria com fotos e descrições
- Modificadores por produto (ex: ponto da carne, adicionais) — obrigatórios ou opcionais
- Carrinho persistente com resumo de valores
- Identificação por telefone — sem senha, sem fricção
- Endereço salvo e pré-preenchido nos próximos pedidos
- Checkout gera mensagem WhatsApp formatada automaticamente
- Se loja estiver fechada: pedido é agendado para a próxima abertura

### Painel administrativo
- Login com JWT — access token em memória, refresh em cookie/localStorage
- Gestão completa de categorias, produtos, modificadores (drag & drop de ordem)
- Upload de fotos com redimensionamento automático (Pillow)
- Fila de pedidos com atualização automática a cada 5s + notificação sonora
- Fluxo de status: Pendente → Confirmado → Preparando → Pronto → Entregue
- Impressão de cupom térmico 80mm direto pelo navegador
- Controle de horários de funcionamento por dia da semana
- Fechar loja manualmente com um clique
- Configurações: taxa de entrega, pedido mínimo, chave PIX, mensagem de fechado
- Dashboard com resumo do dia: pedidos, faturamento, ticket médio, status por tipo

### Segurança
- XSS: `esc()` com `textContent` no frontend público
- Security headers: `X-Content-Type-Options`, `X-Frame-Options`, `CSP` via middleware
- CORS restrito ao domínio em produção
- JWT access token em memória (não persiste entre reloads sem o refresh)
- Rate limiting por IP nas rotas de login
- Uploads: validação de MIME type real, nome UUID, máx 5MB

---

## Em desenvolvimento

- **Controle de estoque** — produto fica indisponível automaticamente ao zerar
- **Pedidos pelo painel** — admin registra pedidos de balcão/mesa diretamente
- **Clientes** — página dedicada com histórico de pedidos e segmentação automática
- **Relatórios avançados** — faturamento por período, produtos mais vendidos, horário de pico
- **Aparência** — personalização de logo, banner e cores do cardápio
- **Fidelidade** — estrutura de pontos e níveis (bronze/prata/ouro)
- **Deploy** — Docker Compose + Nginx + VPS com SSL automático

---

## Arquitetura

```
backend/
├── models/     → SQLAlchemy (estrutura do banco)
├── schemas/    → Pydantic v2 (validação e serialização)
├── services/   → toda a lógica de negócio aqui
└── routers/    → apenas recebem, validam e delegam ao service

frontend/
├── admin/      → painel administrativo (HTML + CSS + JS)
│   └── js/icons.js  → biblioteca de ícones SVG (Heroicons)
└── publico/    → cardápio do cliente
```

O projeto segue MVC com camada de service separada. Routers nunca contêm lógica — apenas chamam o service correto. Isso garante que os testes unitários cubram 100% das regras de negócio sem depender de HTTP.

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

Abra `frontend/admin/index.html` no navegador. A API estará em `http://localhost:8000`.

### Variáveis de ambiente

Copie `.env.example` para `.env` e preencha:

```env
SECRET_KEY=          # python -c "import secrets; print(secrets.token_hex(32))"
REFRESH_SECRET_KEY=  # outro valor diferente do anterior
DATABASE_URL=sqlite:///./data/cardapio.db
WHATSAPP_NUMBER=     # com DDI, sem espaços (ex: 5581999999999)
CORS_ORIGINS=["http://localhost:3000"]
DEBUG=true
```

---

## Testes

```bash
cd backend
pytest tests/ -v
```

213 testes (unit + integration). Os testes de integração rodam com SQLite em memória — sem banco real, sem estado compartilhado entre testes.

---

## Licença

MIT — use, adapte e distribua livremente.
