from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.models.categoria import Categoria
from app.models.produto import Produto
from app.models.modificador import GrupoModificador, Modificador
from app.schemas.cardapio import (
    GrupoModificadorCreate, GrupoModificadorUpdate,
    ModificadorCreate, ModificadorUpdate,
)
from app.services import cardapio_service


def _criar_produto(db) -> Produto:
    """Helper: cria categoria + produto no banco de teste."""
    cat = Categoria(nome="Épicos", ordem=1)
    db.add(cat)
    db.flush()
    prod = Produto(categoria_id=cat.id, nome="Gorgonzolisson", preco=31.0)
    db.add(prod)
    db.flush()
    return prod


# ── Criar grupo ──────────────────────────────────────────────────────────────

def test_criar_grupo_modificador(db_teste):
    produto = _criar_produto(db_teste)

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

    grupo = cardapio_service.criar_grupo_modificador(produto.id, dados, db_teste)

    assert grupo.nome == "Ponto da carne"
    assert grupo.obrigatorio is True
    assert grupo.produto_id == produto.id
    assert len(grupo.modificadores) == 3


def test_criar_grupo_produto_inexistente(db_teste):
    dados = GrupoModificadorCreate(nome="Ponto")

    with pytest.raises(HTTPException) as exc:
        cardapio_service.criar_grupo_modificador(999, dados, db_teste)
    assert exc.value.status_code == 404


def test_criar_grupo_sem_modificadores(db_teste):
    produto = _criar_produto(db_teste)
    dados = GrupoModificadorCreate(nome="Extras")

    grupo = cardapio_service.criar_grupo_modificador(produto.id, dados, db_teste)

    assert grupo.nome == "Extras"
    assert len(grupo.modificadores) == 0


# ── Atualizar grupo ──────────────────────────────────────────────────────────

def test_atualizar_grupo_modificador(db_teste):
    produto = _criar_produto(db_teste)
    dados = GrupoModificadorCreate(nome="Ponto", obrigatorio=False)
    grupo = cardapio_service.criar_grupo_modificador(produto.id, dados, db_teste)

    update = GrupoModificadorUpdate(nome="Ponto (obrigatório)", obrigatorio=True)
    atualizado = cardapio_service.atualizar_grupo_modificador(grupo.id, update, db_teste)

    assert atualizado.nome == "Ponto (obrigatório)"
    assert atualizado.obrigatorio is True


def test_atualizar_grupo_inexistente(db_teste):
    update = GrupoModificadorUpdate(nome="Novo nome")

    with pytest.raises(HTTPException) as exc:
        cardapio_service.atualizar_grupo_modificador(999, update, db_teste)
    assert exc.value.status_code == 404


# ── Deletar grupo ────────────────────────────────────────────────────────────

def test_deletar_grupo_modificador(db_teste):
    produto = _criar_produto(db_teste)
    dados = GrupoModificadorCreate(
        nome="Extras",
        modificadores=[ModificadorCreate(nome="Bacon")],
    )
    grupo = cardapio_service.criar_grupo_modificador(produto.id, dados, db_teste)
    grupo_id = grupo.id

    cardapio_service.deletar_grupo_modificador(grupo_id, db_teste)

    assert db_teste.get(GrupoModificador, grupo_id) is None


def test_deletar_grupo_cascata_modificadores(db_teste):
    """Deletar o grupo deve deletar os modificadores filhos."""
    produto = _criar_produto(db_teste)
    dados = GrupoModificadorCreate(
        nome="Ponto",
        modificadores=[
            ModificadorCreate(nome="Bem Passado"),
            ModificadorCreate(nome="No Ponto"),
        ],
    )
    grupo = cardapio_service.criar_grupo_modificador(produto.id, dados, db_teste)
    mod_ids = [m.id for m in grupo.modificadores]

    cardapio_service.deletar_grupo_modificador(grupo.id, db_teste)

    for mid in mod_ids:
        assert db_teste.get(Modificador, mid) is None


def test_deletar_grupo_inexistente(db_teste):
    with pytest.raises(HTTPException) as exc:
        cardapio_service.deletar_grupo_modificador(999, db_teste)
    assert exc.value.status_code == 404


# ── Criar modificador individual ─────────────────────────────────────────────

def test_criar_modificador(db_teste):
    produto = _criar_produto(db_teste)
    grupo = cardapio_service.criar_grupo_modificador(
        produto.id, GrupoModificadorCreate(nome="Extras"), db_teste
    )

    dados = ModificadorCreate(nome="Bacon extra", preco_adicional=5.0)
    mod = cardapio_service.criar_modificador(grupo.id, dados, db_teste)

    assert mod.nome == "Bacon extra"
    assert mod.preco_adicional == 5.0
    assert mod.grupo_id == grupo.id


def test_criar_modificador_grupo_inexistente(db_teste):
    dados = ModificadorCreate(nome="Bacon")

    with pytest.raises(HTTPException) as exc:
        cardapio_service.criar_modificador(999, dados, db_teste)
    assert exc.value.status_code == 404


# ── Atualizar modificador ────────────────────────────────────────────────────

def test_atualizar_modificador(db_teste):
    produto = _criar_produto(db_teste)
    grupo = cardapio_service.criar_grupo_modificador(
        produto.id,
        GrupoModificadorCreate(
            nome="Extras",
            modificadores=[ModificadorCreate(nome="Bacon", preco_adicional=5.0)],
        ),
        db_teste,
    )

    mod = grupo.modificadores[0]
    update = ModificadorUpdate(nome="Bacon duplo", preco_adicional=8.0)
    atualizado = cardapio_service.atualizar_modificador(mod.id, update, db_teste)

    assert atualizado.nome == "Bacon duplo"
    assert atualizado.preco_adicional == 8.0


def test_atualizar_modificador_inexistente(db_teste):
    update = ModificadorUpdate(nome="Novo")

    with pytest.raises(HTTPException) as exc:
        cardapio_service.atualizar_modificador(999, update, db_teste)
    assert exc.value.status_code == 404


# ── Deletar modificador ──────────────────────────────────────────────────────

def test_deletar_modificador(db_teste):
    produto = _criar_produto(db_teste)
    grupo = cardapio_service.criar_grupo_modificador(
        produto.id,
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