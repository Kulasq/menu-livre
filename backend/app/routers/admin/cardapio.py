from __future__ import annotations
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_admin
from app.schemas.cardapio import (
    CategoriaCreate, CategoriaUpdate, CategoriaResponse,
    ProdutoCreate, ProdutoUpdate, ProdutoResponse,
    GrupoModificadorCreate, GrupoModificadorUpdate,
    GrupoModificadorResponse, GrupoModificadorAdminResponse,
    ModificadorCreate, ModificadorUpdate, ModificadorResponse,
    VincularGrupoRequest,
)
from app.schemas.cardapio import EstoqueAjusteRequest
from app.services import cardapio_service
from app.services import estoque_service

router = APIRouter(prefix="/api/admin", tags=["admin-cardapio"])


# ── Categorias ───────────────────────────────────────────────────────────────

@router.get("/categorias", response_model=list[CategoriaResponse])
def listar_categorias(
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cardapio_service.listar_categorias(db)


@router.post("/categorias", response_model=CategoriaResponse, status_code=201)
def criar_categoria(
    dados: CategoriaCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cardapio_service.criar_categoria(dados, db)


@router.put("/categorias/{categoria_id}", response_model=CategoriaResponse)
def atualizar_categoria(
    categoria_id: int,
    dados: CategoriaUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cardapio_service.atualizar_categoria(categoria_id, dados, db)


@router.delete("/categorias/{categoria_id}", status_code=204)
def deletar_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    cardapio_service.deletar_categoria(categoria_id, db)


# ── Produtos ─────────────────────────────────────────────────────────────────

@router.get("/produtos", response_model=list[ProdutoResponse])
def listar_produtos(
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cardapio_service.listar_produtos(db)


@router.post("/produtos", response_model=ProdutoResponse, status_code=201)
def criar_produto(
    dados: ProdutoCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cardapio_service.criar_produto(dados, db)


@router.put("/produtos/{produto_id}", response_model=ProdutoResponse)
def atualizar_produto(
    produto_id: int,
    dados: ProdutoUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cardapio_service.atualizar_produto(produto_id, dados, db)


@router.delete("/produtos/{produto_id}", status_code=204)
def deletar_produto(
    produto_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    cardapio_service.deletar_produto(produto_id, db)


# ── Grupos de Modificadores (autônomos) ──────────────────────────────────────

@router.get("/grupos-modificadores", response_model=list[GrupoModificadorAdminResponse])
def listar_grupos_modificadores(
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cardapio_service.listar_grupos_modificadores(db)


@router.post("/grupos-modificadores", response_model=GrupoModificadorResponse, status_code=201)
def criar_grupo_modificador(
    dados: GrupoModificadorCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cardapio_service.criar_grupo_modificador(dados, db)


@router.put("/grupos-modificadores/{grupo_id}", response_model=GrupoModificadorResponse)
def atualizar_grupo_modificador(
    grupo_id: int,
    dados: GrupoModificadorUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cardapio_service.atualizar_grupo_modificador(grupo_id, dados, db)


@router.delete("/grupos-modificadores/{grupo_id}", status_code=204)
def deletar_grupo_modificador(
    grupo_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    cardapio_service.deletar_grupo_modificador(grupo_id, db)


@router.post("/grupos-modificadores/{grupo_id}/vincular", status_code=200)
def vincular_grupo(
    grupo_id: int,
    dados: VincularGrupoRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    criados = cardapio_service.vincular_grupo_a_produtos(grupo_id, dados, db)
    return {"vinculados": criados}


@router.delete("/grupos-modificadores/{grupo_id}/vinculos/{produto_id}", status_code=204)
def desvincular_grupo(
    grupo_id: int,
    produto_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    cardapio_service.desvincular_grupo_de_produto(grupo_id, produto_id, db)


# ── Modificadores (opções individuais) ───────────────────────────────────────

@router.post(
    "/grupos-modificadores/{grupo_id}/opcoes",
    response_model=ModificadorResponse,
    status_code=201,
)
def criar_modificador(
    grupo_id: int,
    dados: ModificadorCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cardapio_service.criar_modificador(grupo_id, dados, db)


@router.put(
    "/modificadores/opcoes/{modificador_id}",
    response_model=ModificadorResponse,
)
def atualizar_modificador(
    modificador_id: int,
    dados: ModificadorUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cardapio_service.atualizar_modificador(modificador_id, dados, db)


@router.delete("/modificadores/opcoes/{modificador_id}", status_code=204)
def deletar_modificador(
    modificador_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    cardapio_service.deletar_modificador(modificador_id, db)


# ── Compat: rota antiga de adicionar grupo via produto (mantida para não quebrar) ──
# Redireciona para a criação autônoma + vínculo automático com o produto

@router.post(
    "/produtos/{produto_id}/modificadores",
    response_model=GrupoModificadorResponse,
    status_code=201,
)
def criar_grupo_via_produto(
    produto_id: int,
    dados: GrupoModificadorCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Cria grupo e o vincula imediatamente ao produto."""
    from app.models.produto import Produto
    from app.models.modificador import produto_grupo_modificador as pgm
    from sqlalchemy import func, select as sa_select

    produto = db.get(Produto, produto_id)
    if not produto:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    grupo = cardapio_service.criar_grupo_modificador(dados, db)

    # Determina próxima ordem para este produto
    max_ordem = db.execute(
        sa_select(func.max(pgm.c.ordem)).where(pgm.c.produto_id == produto_id)
    ).scalar() or 0

    db.execute(pgm.insert().values(
        produto_id=produto_id, grupo_id=grupo.id, ordem=max_ordem + 1
    ))
    db.commit()
    return grupo


# Compat: rota antiga de editar grupo (por /modificadores/{id})
@router.put(
    "/modificadores/{grupo_id}",
    response_model=GrupoModificadorResponse,
)
def atualizar_grupo_compat(
    grupo_id: int,
    dados: GrupoModificadorUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cardapio_service.atualizar_grupo_modificador(grupo_id, dados, db)


# Compat: rota antiga de deletar grupo (por /modificadores/{id})
@router.delete("/modificadores/{grupo_id}", status_code=204)
def deletar_grupo_compat(
    grupo_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    cardapio_service.deletar_grupo_modificador(grupo_id, db)


# Compat: rota antiga de criar opção (por /modificadores/{grupo_id}/opcoes)
@router.post(
    "/modificadores/{grupo_id}/opcoes",
    response_model=ModificadorResponse,
    status_code=201,
)
def criar_modificador_compat(
    grupo_id: int,
    dados: ModificadorCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cardapio_service.criar_modificador(grupo_id, dados, db)


# ── Estoque — Produtos ────────────────────────────────────────────────────────

@router.patch("/produtos/{produto_id}/estoque", response_model=ProdutoResponse)
def ajustar_estoque_produto(
    produto_id: int,
    dados: EstoqueAjusteRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Ajusta estoque_atual de um produto.

    Operações: definir | incrementar | decrementar | zerar
    """
    return estoque_service.ajustar_estoque_produto(produto_id, dados, db)


# ── Estoque — Opções de Modificador ──────────────────────────────────────────

@router.patch("/modificadores/opcoes/{opcao_id}/estoque", response_model=ModificadorResponse)
def ajustar_estoque_modificador(
    opcao_id: int,
    dados: EstoqueAjusteRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Ajusta estoque_atual de uma opção de modificador.

    Operações: definir | incrementar | decrementar | zerar
    """
    return estoque_service.ajustar_estoque_modificador(opcao_id, dados, db)
