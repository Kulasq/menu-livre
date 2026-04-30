from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.models.categoria import Categoria
from app.models.produto import Produto
from app.models.modificador import GrupoModificador, Modificador
from app.schemas.cardapio import (
    GrupoModificadorCreate, GrupoModificadorUpdate,
    ModificadorCreate, ModificadorUpdate,
    VincularGrupoRequest,
)
from app.services import cardapio_service


def _criar_produto(db, nome="Gorgonzolisson") -> Produto:
    cat = Categoria(nome="Épicos", ordem=1)
    db.add(cat)
    db.flush()
    prod = Produto(categoria_id=cat.id, nome=nome, preco=31.0)
    db.add(prod)
    db.flush()
    return prod


# ── Criar grupo (autônomo) ───────────────────────────────────────────────────

def test_criar_grupo_modificador(db_teste):
    dados = GrupoModificadorCreate(
        nome="Ponto da carne",
        obrigatorio=True,
        selecao_minima=1,
        selecao_maxima=1,
        modificadores=[
            ModificadorCreate(nome="Bem Passado"),
            ModificadorCreate(nome="No Ponto"),
            ModificadorCreate(nome="Mal Passado"),
        ],
    )

    grupo = cardapio_service.criar_grupo_modificador(dados, db_teste)

    assert grupo.nome == "Ponto da carne"
    assert grupo.obrigatorio is True
    assert len(grupo.modificadores) == 3


def test_criar_grupo_sem_modificadores(db_teste):
    dados = GrupoModificadorCreate(nome="Extras")
    grupo = cardapio_service.criar_grupo_modificador(dados, db_teste)

    assert grupo.nome == "Extras"
    assert len(grupo.modificadores) == 0


# ── Atualizar grupo ──────────────────────────────────────────────────────────

def test_atualizar_grupo_modificador(db_teste):
    dados = GrupoModificadorCreate(nome="Ponto", obrigatorio=False)
    grupo = cardapio_service.criar_grupo_modificador(dados, db_teste)

    update = GrupoModificadorUpdate(nome="Ponto (obrigatório)", obrigatorio=True)
    atualizado = cardapio_service.atualizar_grupo_modificador(grupo.id, update, db_teste)

    assert atualizado.nome == "Ponto (obrigatório)"
    assert atualizado.obrigatorio is True


def test_atualizar_grupo_inexistente(db_teste):
    with pytest.raises(HTTPException) as exc:
        cardapio_service.atualizar_grupo_modificador(999, GrupoModificadorUpdate(nome="Novo"), db_teste)
    assert exc.value.status_code == 404


# ── Deletar grupo ────────────────────────────────────────────────────────────

def test_deletar_grupo_modificador(db_teste):
    dados = GrupoModificadorCreate(
        nome="Extras",
        modificadores=[ModificadorCreate(nome="Bacon")],
    )
    grupo = cardapio_service.criar_grupo_modificador(dados, db_teste)
    grupo_id = grupo.id

    cardapio_service.deletar_grupo_modificador(grupo_id, db_teste)

    assert db_teste.get(GrupoModificador, grupo_id) is None


def test_deletar_grupo_cascata_modificadores(db_teste):
    dados = GrupoModificadorCreate(
        nome="Ponto",
        modificadores=[
            ModificadorCreate(nome="Bem Passado"),
            ModificadorCreate(nome="No Ponto"),
        ],
    )
    grupo = cardapio_service.criar_grupo_modificador(dados, db_teste)
    mod_ids = [m.id for m in grupo.modificadores]

    cardapio_service.deletar_grupo_modificador(grupo.id, db_teste)

    for mid in mod_ids:
        assert db_teste.get(Modificador, mid) is None


def test_deletar_grupo_inexistente(db_teste):
    with pytest.raises(HTTPException) as exc:
        cardapio_service.deletar_grupo_modificador(999, db_teste)
    assert exc.value.status_code == 404


# ── Vincular grupo a produtos ────────────────────────────────────────────────

def test_vincular_todos_os_produtos(db_teste):
    prod1 = _criar_produto(db_teste, "Burger A")
    prod2 = _criar_produto(db_teste, "Burger B")
    grupo = cardapio_service.criar_grupo_modificador(
        GrupoModificadorCreate(nome="Molho extra"), db_teste
    )

    criados = cardapio_service.vincular_grupo_a_produtos(
        grupo.id, VincularGrupoRequest(modo="todos"), db_teste
    )

    assert criados == 2
    db_teste.refresh(prod1)
    db_teste.refresh(prod2)
    assert any(g.id == grupo.id for g in prod1.grupos_modificadores)
    assert any(g.id == grupo.id for g in prod2.grupos_modificadores)


def test_vincular_por_categoria(db_teste):
    prod1 = _criar_produto(db_teste, "Burger A")

    # Produto em outra categoria
    cat2 = Categoria(nome="Bebidas", ordem=2)
    db_teste.add(cat2)
    db_teste.flush()
    prod_bebida = Produto(categoria_id=cat2.id, nome="Suco", preco=8.0)
    db_teste.add(prod_bebida)
    db_teste.flush()

    grupo = cardapio_service.criar_grupo_modificador(
        GrupoModificadorCreate(nome="Tamanho"), db_teste
    )

    criados = cardapio_service.vincular_grupo_a_produtos(
        grupo.id,
        VincularGrupoRequest(modo="categoria", categoria_id=prod1.categoria_id),
        db_teste,
    )

    assert criados == 1
    db_teste.refresh(prod1)
    db_teste.refresh(prod_bebida)
    assert any(g.id == grupo.id for g in prod1.grupos_modificadores)
    assert not any(g.id == grupo.id for g in prod_bebida.grupos_modificadores)


def test_vincular_produtos_especificos(db_teste):
    prod1 = _criar_produto(db_teste, "Burger A")
    prod2 = _criar_produto(db_teste, "Burger B")
    grupo = cardapio_service.criar_grupo_modificador(
        GrupoModificadorCreate(nome="Extras"), db_teste
    )

    criados = cardapio_service.vincular_grupo_a_produtos(
        grupo.id,
        VincularGrupoRequest(modo="produtos", produtos_ids=[prod1.id]),
        db_teste,
    )

    assert criados == 1
    db_teste.refresh(prod1)
    db_teste.refresh(prod2)
    assert any(g.id == grupo.id for g in prod1.grupos_modificadores)
    assert not any(g.id == grupo.id for g in prod2.grupos_modificadores)


def test_vincular_ignora_duplicatas(db_teste):
    prod = _criar_produto(db_teste)
    grupo = cardapio_service.criar_grupo_modificador(
        GrupoModificadorCreate(nome="Extras"), db_teste
    )

    # Vincula pela primeira vez
    cardapio_service.vincular_grupo_a_produtos(
        grupo.id, VincularGrupoRequest(modo="todos"), db_teste
    )
    # Segunda vez não deve lançar erro nem duplicar
    criados2 = cardapio_service.vincular_grupo_a_produtos(
        grupo.id, VincularGrupoRequest(modo="todos"), db_teste
    )

    assert criados2 == 0
    db_teste.refresh(prod)
    assert sum(1 for g in prod.grupos_modificadores if g.id == grupo.id) == 1


def test_vincular_grupo_inexistente(db_teste):
    with pytest.raises(HTTPException) as exc:
        cardapio_service.vincular_grupo_a_produtos(
            999, VincularGrupoRequest(modo="todos"), db_teste
        )
    assert exc.value.status_code == 404


def test_vincular_categoria_inexistente(db_teste):
    grupo = cardapio_service.criar_grupo_modificador(
        GrupoModificadorCreate(nome="Geral"), db_teste
    )
    with pytest.raises(HTTPException) as exc:
        cardapio_service.vincular_grupo_a_produtos(
            grupo.id, VincularGrupoRequest(modo="categoria", categoria_id=999), db_teste
        )
    assert exc.value.status_code == 404


# ── Desvincular grupo de produto ─────────────────────────────────────────────

def test_desvincular_grupo_de_produto(db_teste):
    prod = _criar_produto(db_teste)
    grupo = cardapio_service.criar_grupo_modificador(
        GrupoModificadorCreate(nome="Extras"), db_teste
    )
    cardapio_service.vincular_grupo_a_produtos(
        grupo.id, VincularGrupoRequest(modo="todos"), db_teste
    )

    cardapio_service.desvincular_grupo_de_produto(grupo.id, prod.id, db_teste)

    db_teste.refresh(prod)
    assert not any(g.id == grupo.id for g in prod.grupos_modificadores)


def test_desvincular_vinculo_inexistente(db_teste):
    prod = _criar_produto(db_teste)
    grupo = cardapio_service.criar_grupo_modificador(
        GrupoModificadorCreate(nome="Extras"), db_teste
    )

    with pytest.raises(HTTPException) as exc:
        cardapio_service.desvincular_grupo_de_produto(grupo.id, prod.id, db_teste)
    assert exc.value.status_code == 404


# ── Listar grupos com contagem ───────────────────────────────────────────────

def test_listar_grupos_com_contagem(db_teste):
    prod1 = _criar_produto(db_teste, "A")
    prod2 = _criar_produto(db_teste, "B")

    grupo1 = cardapio_service.criar_grupo_modificador(
        GrupoModificadorCreate(nome="Ponto"), db_teste
    )
    grupo2 = cardapio_service.criar_grupo_modificador(
        GrupoModificadorCreate(nome="Molho"), db_teste
    )

    cardapio_service.vincular_grupo_a_produtos(
        grupo1.id, VincularGrupoRequest(modo="todos"), db_teste
    )
    cardapio_service.vincular_grupo_a_produtos(
        grupo2.id, VincularGrupoRequest(modo="produtos", produtos_ids=[prod1.id]), db_teste
    )

    lista = cardapio_service.listar_grupos_modificadores(db_teste)

    g1 = next(g for g in lista if g["id"] == grupo1.id)
    g2 = next(g for g in lista if g["id"] == grupo2.id)
    assert g1["total_produtos"] == 2
    assert g2["total_produtos"] == 1


# ── Criar modificador individual ─────────────────────────────────────────────

def test_criar_modificador(db_teste):
    grupo = cardapio_service.criar_grupo_modificador(
        GrupoModificadorCreate(nome="Extras"), db_teste
    )

    dados = ModificadorCreate(nome="Bacon extra", preco_adicional=5.0)
    mod = cardapio_service.criar_modificador(grupo.id, dados, db_teste)

    assert mod.nome == "Bacon extra"
    assert mod.preco_adicional == 5.0
    assert mod.grupo_id == grupo.id


def test_criar_modificador_grupo_inexistente(db_teste):
    with pytest.raises(HTTPException) as exc:
        cardapio_service.criar_modificador(999, ModificadorCreate(nome="Bacon"), db_teste)
    assert exc.value.status_code == 404


# ── Atualizar modificador ────────────────────────────────────────────────────

def test_atualizar_modificador(db_teste):
    grupo = cardapio_service.criar_grupo_modificador(
        GrupoModificadorCreate(
            nome="Extras",
            modificadores=[ModificadorCreate(nome="Bacon", preco_adicional=5.0)],
        ),
        db_teste,
    )

    mod = grupo.modificadores[0]
    atualizado = cardapio_service.atualizar_modificador(
        mod.id, ModificadorUpdate(nome="Bacon duplo", preco_adicional=8.0), db_teste
    )

    assert atualizado.nome == "Bacon duplo"
    assert atualizado.preco_adicional == 8.0


def test_atualizar_modificador_inexistente(db_teste):
    with pytest.raises(HTTPException) as exc:
        cardapio_service.atualizar_modificador(999, ModificadorUpdate(nome="Novo"), db_teste)
    assert exc.value.status_code == 404


# ── Deletar modificador ──────────────────────────────────────────────────────

def test_deletar_modificador(db_teste):
    grupo = cardapio_service.criar_grupo_modificador(
        GrupoModificadorCreate(
            nome="Extras",
            modificadores=[ModificadorCreate(nome="Bacon")],
        ),
        db_teste,
    )

    mod_id = grupo.modificadores[0].id
    cardapio_service.deletar_modificador(mod_id, db_teste)

    assert db_teste.get(Modificador, mod_id) is None


def test_deletar_modificador_inexistente(db_teste):
    with pytest.raises(HTTPException) as exc:
        cardapio_service.deletar_modificador(999, db_teste)
    assert exc.value.status_code == 404
