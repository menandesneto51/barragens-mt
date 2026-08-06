"""Aceite rápido — dossiê por localidade (ex.: Cuiabá)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from st_app.localidade import montar_dossie_localidade, municipios_vizinhos_vulneraveis  # noqa: E402


def main() -> int:
    idap = pd.read_csv(
        ROOT / "dados/tratados/idap_estadual_mt.csv",
        sep=";",
        encoding="utf-8-sig",
        low_memory=False,
    )
    ok = 0
    total = 6

    d = montar_dossie_localidade("Cuiabá", idap)
    assert d["n_barragens"] > 0, "Cuiabá deve ter barragens sede/jusante"
    ok += 1
    assert d["n_sede"] > 0 and d["n_jusante"] > 0, "espera sede e jusante"
    ok += 1
    assert (d["populacao"] or {}).get("populacao"), "população IBGE"
    ok += 1
    assert len(d["quilombolas_palmares"]) >= 1, "Palmares em Cuiabá"
    ok += 1
    assert d["ribeirinhos"]["disponivel"] is False, "ribeirinhos = lacuna explícita"
    ok += 1
    viz = municipios_vizinhos_vulneraveis("Cuiabá", d["sedes_montante"])
    assert not viz.empty, "vizinhos Otto com vulneráveis"
    ok += 1

    print(f"OK {ok}/{total} — Cuiabá: {d['n_barragens']} barragens, pop {d['populacao']['populacao']}")
    return 0 if ok == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
