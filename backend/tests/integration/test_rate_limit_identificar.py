from __future__ import annotations

# O endpoint público /api/clientes/identificar não exige auth e devolve dados do
# cliente por telefone. O rate limit (10/min por IP) protege contra enumeração em
# massa da base de clientes. O conftest reseta o storage do limiter a cada teste.


def test_identificar_respeita_rate_limit(client, db_teste):
    """A 11ª chamada no mesmo minuto (limite 10/min) deve retornar 429."""
    body = {"telefone": "81999990000", "nome": "Cliente Rate"}

    for i in range(10):
        r = client.post("/api/clientes/identificar", json=body)
        assert r.status_code == 200, f"chamada {i + 1} deveria passar, veio {r.status_code}"

    r = client.post("/api/clientes/identificar", json=body)
    assert r.status_code == 429
