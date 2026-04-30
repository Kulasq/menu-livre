from __future__ import annotations
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, delete, func
from fastapi import HTTPException

from app.models.categoria import Categoria
from app.models.produto import Produto
from app.models.modificador import GrupoModificador, Modificador, produto_grupo_modificador
from app.schemas.cardapio import (
    CategoriaCreate, CategoriaUpdate,
    ProdutoCreate, ProdutoUpdate,
    GrupoModificadorCreate, GrupoModificadorUpdate,
    ModificadorCreate, ModificadorUpdate,
    VincularGrupoRequest,
)


# ── Categorias ───────────────────────────────────────────────────────────────

def listar_categorias(db: Session, apenas_ativas: bool = False) -> list[Categoria]:
    q = db.query(Categoria)
    if apenas_ativas:
        q = q.filter(Categoria.ativo == True)
    return q.order_by(Categoria.ordem, Categoria.nome).all()


def criar_categoria(dados: CategoriaCreate, db: Session) -> Categoria:
    categoria = Categoria(**dados.model_dump())
    db.add(categoria)
    db.commit()
    categoria_id = categoria.id
    db.expire(categoria)
    return db.get(Categoria, categoria_id)


def atualizar_categoria(categoria_id: int, dados: CategoriaUpdate, db: Session) -> Categoria:
    categoria = db.get(Categoria, categoria_id)
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(categoria, campo, valor)
    db.commit()
    return db.get(Categoria, categoria_id)


def deletar_categoria(categoria_id: int, db: Session) -> None:
    categoria = db.get(Categoria, categoria_id)
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    count = db.query(Produto).filter(Produto.categoria_id == categoria_id).count()
    if count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível excluir: categoria tem {count} produto(s)",
        )
    db.delete(categoria)
    db.commit()


# ── Produtos ─────────────────────────────────────────────────────────────────

def listar_produtos(db: Session, apenas_disponiveis: bool = False) -> list[Produto]:
    q = db.query(Produto).options(
        joinedload(Produto.grupos_modificadores).joinedload(GrupoModificador.modificadores)
    )
    if apenas_disponiveis:
        q = q.filter(Produto.disponivel == True)
    return q.order_by(Produto.ordem, Produto.nome).all()


def obter_produto(produto_id: int, db: Session) -> Produto:
    produto = db.query(Produto).options(
        joinedload(Produto.grupos_modificadores).joinedload(GrupoModificador.modificadores)
    ).filter(Produto.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return produto


def criar_produto(dados: ProdutoCreate, db: Session) -> Produto:
    categoria = db.get(Categoria, dados.categoria_id)
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    produto = Produto(**dados.model_dump())
    db.add(produto)
    db.commit()
    produto_id = produto.id
    return obter_produto(produto_id, db)


def atualizar_produto(produto_id: int, dados: ProdutoUpdate, db: Session) -> Produto:
    produto = db.get(Produto, produto_id)
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if dados.categoria_id:
        if not db.get(Categoria, dados.categoria_id):
            raise HTTPException(status_code=404, detail="Categoria não encontrada")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(produto, campo, valor)
    db.commit()
    return obter_produto(produto_id, db)


def deletar_produto(produto_id: int, db: Session) -> None:
    produto = db.get(Produto, produto_id)
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    db.delete(produto)
    db.commit()


# ── Cardápio público ──────────────────────────────────────────────────────────

def obter_cardapio_publico(db: Session) -> dict:
    categorias = listar_categorias(db, apenas_ativas=True)
    produtos = listar_produtos(db, apenas_disponiveis=True)

    produtos_por_categoria: dict[int, list] = {}
    destaques = []

    for produto in produtos:
        # Filtra grupos inativos — não expõe ao cliente grupos desativados pelo admin.
        # Mutação em memória é segura: sem commit, sessão expira ao fim do request.
        produto.grupos_modificadores = [
            g for g in (produto.grupos_modificadores or []) if g.ativo
        ]
        produtos_por_categoria.setdefault(produto.categoria_id, []).append(produto)
        if produto.destaque:
            destaques.append(produto)

    resultado = []
    for cat in categorias:
        resultado.append({
            "id": cat.id,
            "nome": cat.nome,
            "descricao": cat.descricao,
            "ordem": cat.ordem,
            "produtos": produtos_por_categoria.get(cat.id, []),
        })

    return {"categorias": resultado, "destaques": destaques}


# ── Grupos de Modificadores (autônomos) ──────────────────────────────────────

def _carregar_grupo(grupo_id: int, db: Session) -> GrupoModificador:
    grupo = db.query(GrupoModificador).options(
        joinedload(GrupoModificador.modificadores)
    ).filter(GrupoModificador.id == grupo_id).first()
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo de modificador não encontrado")
    return grupo


def listar_grupos_modificadores(db: Session) -> list[dict]:
    """Retorna todos os grupos com contagem de produtos vinculados."""
    grupos = db.query(GrupoModificador).options(
        joinedload(GrupoModificador.modificadores)
    ).order_by(GrupoModificador.nome).all()

    # Contagem de produtos por grupo via subquery
    contagens_raw = db.execute(
        select(
            produto_grupo_modificador.c.grupo_id,
            func.count().label("total")
        ).group_by(produto_grupo_modificador.c.grupo_id)
    ).all()
    contagens = {row.grupo_id: row.total for row in contagens_raw}

    resultado = []
    for g in grupos:
        resultado.append({
            "id": g.id,
            "nome": g.nome,
            "obrigatorio": g.obrigatorio,
            "selecao_minima": g.selecao_minima,
            "selecao_maxima": g.selecao_maxima,
            "ativo": g.ativo,
            "modificadores": g.modificadores,
            "total_produtos": contagens.get(g.id, 0),
        })
    return resultado


def criar_grupo_modificador(dados: GrupoModificadorCreate, db: Session) -> GrupoModificador:
    grupo = GrupoModificador(
        nome=dados.nome,
        obrigatorio=dados.obrigatorio,
        selecao_minima=dados.selecao_minima,
        selecao_maxima=dados.selecao_maxima,
        ativo=dados.ativo,
    )
    db.add(grupo)
    db.flush()

    for mod_dados in dados.modificadores:
        mod = Modificador(
            grupo_id=grupo.id,
            nome=mod_dados.nome,
            preco_adicional=mod_dados.preco_adicional,
            disponivel=mod_dados.disponivel,
            ordem=mod_dados.ordem,
        )
        db.add(mod)

    db.commit()
    return _carregar_grupo(grupo.id, db)


def atualizar_grupo_modificador(
    grupo_id: int, dados: GrupoModificadorUpdate, db: Session
) -> GrupoModificador:
    grupo = db.get(GrupoModificador, grupo_id)
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo de modificador não encontrado")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(grupo, campo, valor)

    db.commit()
    return _carregar_grupo(grupo_id, db)


def deletar_grupo_modificador(grupo_id: int, db: Session) -> None:
    grupo = db.get(GrupoModificador, grupo_id)
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo de modificador não encontrado")

    # Antes de deletar, anula referências históricas em pedido_item_modificadores
    # para os modificadores deste grupo. A FK não tem ondelete no SQLite (limitação
    # de batch_alter sem constraint nomeada), então zeramos via ORM antes do delete.
    # Os snapshots (nome_snapshot, preco_snapshot) preservam o histórico visual.
    from app.models.pedido import PedidoItemModificador
    ids_mods = [m.id for m in grupo.modificadores]
    if ids_mods:
        db.query(PedidoItemModificador).filter(
            PedidoItemModificador.modificador_id.in_(ids_mods)
        ).update({"modificador_id": None}, synchronize_session=False)

    db.delete(grupo)
    db.commit()


def contar_produtos_do_grupo(grupo_id: int, db: Session) -> int:
    row = db.execute(
        select(func.count()).where(produto_grupo_modificador.c.grupo_id == grupo_id)
    ).scalar()
    return row or 0


# ── Vínculos produto ↔ grupo ──────────────────────────────────────────────────

def vincular_grupo_a_produtos(
    grupo_id: int, dados: VincularGrupoRequest, db: Session
) -> int:
    """Vincula o grupo a um conjunto de produtos. Ignora duplicatas. Retorna qtd de vínculos criados."""
    grupo = db.get(GrupoModificador, grupo_id)
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo de modificador não encontrado")

    if dados.modo == "todos":
        produto_ids = [r[0] for r in db.query(Produto.id).all()]
    elif dados.modo == "categoria":
        if not dados.categoria_id:
            raise HTTPException(status_code=422, detail="categoria_id obrigatório para modo 'categoria'")
        if not db.get(Categoria, dados.categoria_id):
            raise HTTPException(status_code=404, detail="Categoria não encontrada")
        produto_ids = [
            r[0] for r in db.query(Produto.id).filter(Produto.categoria_id == dados.categoria_id).all()
        ]
    else:  # "produtos"
        if not dados.produtos_ids:
            raise HTTPException(status_code=422, detail="produtos_ids obrigatório para modo 'produtos'")
        produto_ids = dados.produtos_ids

    if not produto_ids:
        return 0

    # Filtra os que já estão vinculados para não violar UNIQUE
    ja_vinculados = set(
        r[0] for r in db.execute(
            select(produto_grupo_modificador.c.produto_id).where(
                produto_grupo_modificador.c.grupo_id == grupo_id,
                produto_grupo_modificador.c.produto_id.in_(produto_ids),
            )
        ).all()
    )

    novos = [pid for pid in produto_ids if pid not in ja_vinculados]
    if not novos:
        return 0

    # Calcula a próxima ordem para cada produto (append ao final)
    ordens_atuais = dict(
        db.execute(
            select(
                produto_grupo_modificador.c.produto_id,
                func.max(produto_grupo_modificador.c.ordem).label("max_ordem"),
            ).where(produto_grupo_modificador.c.produto_id.in_(novos))
            .group_by(produto_grupo_modificador.c.produto_id)
        ).all()
    )

    rows = [
        {"produto_id": pid, "grupo_id": grupo_id, "ordem": (ordens_atuais.get(pid) or 0) + 1}
        for pid in novos
    ]
    db.execute(produto_grupo_modificador.insert(), rows)
    db.commit()
    return len(rows)


def desvincular_grupo_de_produto(grupo_id: int, produto_id: int, db: Session) -> None:
    if not db.get(GrupoModificador, grupo_id):
        raise HTTPException(status_code=404, detail="Grupo de modificador não encontrado")
    if not db.get(Produto, produto_id):
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    result = db.execute(
        delete(produto_grupo_modificador).where(
            produto_grupo_modificador.c.grupo_id == grupo_id,
            produto_grupo_modificador.c.produto_id == produto_id,
        )
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Vínculo não encontrado")


def vinculos_do_produto(produto_id: int, db: Session) -> list[int]:
    """Retorna lista de grupo_ids vinculados a um produto."""
    rows = db.execute(
        select(produto_grupo_modificador.c.grupo_id).where(
            produto_grupo_modificador.c.produto_id == produto_id
        ).order_by(produto_grupo_modificador.c.ordem)
    ).all()
    return [r[0] for r in rows]


# ── Modificadores (opções individuais) ────────────────────────────────────────

def criar_modificador(grupo_id: int, dados: ModificadorCreate, db: Session) -> Modificador:
    grupo = db.get(GrupoModificador, grupo_id)
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo de modificador não encontrado")

    mod = Modificador(
        grupo_id=grupo_id,
        nome=dados.nome,
        preco_adicional=dados.preco_adicional,
        disponivel=dados.disponivel,
        ordem=dados.ordem,
    )
    db.add(mod)
    db.commit()
    mod_id = mod.id
    return db.get(Modificador, mod_id)


def atualizar_modificador(
    modificador_id: int, dados: ModificadorUpdate, db: Session
) -> Modificador:
    mod = db.get(Modificador, modificador_id)
    if not mod:
        raise HTTPException(status_code=404, detail="Modificador não encontrado")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(mod, campo, valor)

    db.commit()
    return db.get(Modificador, modificador_id)


def deletar_modificador(modificador_id: int, db: Session) -> None:
    mod = db.get(Modificador, modificador_id)
    if not mod:
        raise HTTPException(status_code=404, detail="Modificador não encontrado")
    db.delete(mod)
    db.commit()
