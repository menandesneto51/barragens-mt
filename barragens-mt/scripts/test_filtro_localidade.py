"""Aceite rápido — dossiê por localidade (ex.: Cuiabá) + proxy ribeirinhos."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from st_app.localidade import (  # noqa: E402
    montar_dossie_localidade,
    municipios_vizinhos_vulneraveis,
    proxy_ribeirinhos_municipio,
)


def main() -> int:
    idap = pd.read_csv(
        ROOT / "dados/tratados/idap_estadual_mt.csv",
        sep=";",
        encoding="utf-8-sig",
        low_memory=False,
    )
    ok = 0
    total = 8

    d = montar_dossie_localidade("Cuiabá", idap)
    assert d["n_barragens"] > 0, "Cuiabá deve ter barragens sede/jusante"
    ok += 1
    assert d["n_sede"] > 0 and d["n_jusante"] > 0, "espera sede e jusante"
    ok += 1
    assert (d["populacao"] or {}).get("populacao"), "população IBGE"
    ok += 1
    assert len(d["quilombolas_palmares"]) >= 1, "Palmares em Cuiabá"
    ok += 1

    rib = d["ribeirinhos"]
    assert rib["disponivel"] is True, "Cuiabá no eixo: proxy ribeirinhos disponível"
    assert rib["tipo"] == "proxy_setores_eixo"
    assert rib["n_setores_eixo"] > 0
    assert rib["populacao_rural_eixo"] > 0, "setores rurais do eixo em Cuiabá"
    assert "não cadastro" in (rib.get("aviso") or "").lower() or "Não há" in (
        rib.get("aviso") or ""
    )
    ok += 1

    viz = municipios_vizinhos_vulneraveis("Cuiabá", d["sedes_montante"])
    assert not viz.empty, "vizinhos Otto com vulneráveis"
    ok += 1

    # Município fora do eixo Manso–Cuiabá: lacuna explícita (sem inventar número).
    fora = proxy_ribeirinhos_municipio("Alta Floresta")
    assert fora["disponivel"] is False, "fora do eixo = lacuna, não zero falso"
    assert fora["populacao_eixo"] == 0
    ok += 1

    # Município do eixo com sinal rural mais típico de margem.
    barao = proxy_ribeirinhos_municipio("Barão de Melgaço")
    assert barao["disponivel"] is True
    assert barao["n_setores_eixo"] > 0
    ok += 1

    print(
        f"OK {ok}/{total} — Cuiabá: {d['n_barragens']} barragens, "
        f"proxy rural eixo {rib['populacao_rural_eixo']} hab. "
        f"({rib['n_setores_rural_eixo']} setores)"
    )
    return 0 if ok == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
