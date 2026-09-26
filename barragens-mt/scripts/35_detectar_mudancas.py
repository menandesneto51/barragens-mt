"""Gera eventos de mudança entre os dois snapshots mais recentes do IDAP estadual."""

from __future__ import annotations

import csv
from pathlib import Path
import sys

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from vigibarragens.history import detect_changes, write_change_events  # noqa: E402

HISTORICO = RAIZ / "dados" / "tratados" / "historico_idap"
SAIDA = RAIZ / "dados" / "tratados" / "eventos_mudanca_idap.jsonl"
CAMPOS = (
    "categoria_risco",
    "dano_potencial_associado",
    "nivel",
    "completude",
    "confiabilidade",
    "idap",
    "alertavel",
    "contatos_validados_90d",
    "municipios_potencialmente_afetados",
)


def ler_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep=";", dtype=str, encoding="utf-8-sig").fillna("")


def main() -> None:
    snapshots = sorted(HISTORICO.glob("idap_*.csv"))
    if len(snapshots) < 2:
        print("Histórico insuficiente: são necessários ao menos dois snapshots IDAP.")
        write_change_events([], SAIDA)
        return
    anterior, atual = snapshots[-2], snapshots[-1]
    eventos = detect_changes(ler_csv(anterior), ler_csv(atual), id_col="id_snisb", fields=CAMPOS)
    write_change_events(eventos, SAIDA)
    print(f"Mudanças IDAP: {len(eventos)} evento(s) entre {anterior.name} e {atual.name}")
    print(f"  saída: {SAIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
