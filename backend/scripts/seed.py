from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.models.usuario import Usuario
from app.models.configuracao import Configuracao
from app.services.auth_service import hash_senha


def seed_usuario(db) -> None:
    existe = db.query(Usuario).filter_by(email="sara@paodemao.com.br").first()
    if existe:
        print("  [ok] Superadmin já existe — pulando.")
        return

    usuario = Usuario(
        nome="Sara",
        email="sara@paodemao.com.br",
        senha_hash=hash_senha("paodemao2026"),
        role="superadmin",
        ativo=True,
    )
    db.add(usuario)
    db.commit()
    print("  [criado] Superadmin: sara@paodemao.com.br / senha: paodemao2026")


def seed_configuracao(db) -> None:
    existe = db.query(Configuracao).filter_by(id=1).first()
    if existe:
        print("  [ok] Configuração já existe — pulando.")
        return

    config = Configuracao(
        id=1,
        nome_loja="Pão de Mão",
        whatsapp="5581996008571",
        instagram_url="https://instagram.com/paodemao",
        taxa_entrega=0.0,
        pedido_minimo=0.0,
        tempo_entrega_min=30,
        tempo_entrega_max=50,
        aceitar_pedidos=True,
        mensagem_fechado="Estamos fechados no momento. Volte em breve! 🍔",
    )
    db.add(config)
    db.commit()
    print("  [criado] Configuração inicial da loja.")


def main() -> None:
    print("\n🍞 Pão de Mão — Seed inicial\n")

    db = SessionLocal()
    try:
        print("→ Usuário admin:")
        seed_usuario(db)

        print("→ Configuração da loja:")
        seed_configuracao(db)
    finally:
        db.close()

    print("\n✅ Seed concluído.\n")


if __name__ == "__main__":
    main()