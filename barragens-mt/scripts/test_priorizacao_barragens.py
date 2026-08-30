"""Aceite — priorização estadual (etapa 54)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    spec = importlib.util.spec_from_file_location(
        "prio54", ROOT / "scripts" / "54_priorizacao_barragens.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    r = {
        "id_snisb": "1",
        "nome": "Teste",
        "municipio_sede": "Cuiabá",
        "dano_potencial_associado": "Alto",
        "uso_principal": "Contenção de rejeitos industriais",
        "nivel": "Laranja",
        "idap": "40",
        "n_municipios_extraterritoriais": "2",
        "alertavel": "nao",
    }
    s = mod.score_linha(r, {"1": 5})
    assert s["pts_dpa"] == mod.PESOS["dpa_alto"]
    assert s["pts_rejeito"] == mod.PESOS["rejeito"]
    assert s["pts_nivel"] == mod.NIVEL_PTS["Laranja"]
    assert s["pts_pae"] == mod.PESOS["pae_lacunas"]
    assert s["pts_nao_alertavel"] == mod.PESOS["nao_alertavel"]
    assert s["score_prioridade"] == (
        s["pts_dpa"]
        + s["pts_rejeito"]
        + s["pts_nivel"]
        + s["pts_extraterritorial"]
        + s["pts_pae"]
        + s["pts_nao_alertavel"]
    )
    s2 = mod.score_linha(r, {"1": 5})
    assert s["score_prioridade"] == s2["score_prioridade"]

    mod.main()
    saida = ROOT / "dados/tratados/barragens_prioritarias_mt.csv"
    assert saida.is_file()
    df = pd.read_csv(saida, sep=";")
    assert len(df) >= 100
    assert int(df.iloc[0]["rank"]) == 1
    print(
        f"OK priorização: {len(df)} barragens top={df.iloc[0]['nome']} "
        f"score={df.iloc[0]['score_prioridade']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
