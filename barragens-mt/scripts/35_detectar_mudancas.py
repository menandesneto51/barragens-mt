"""Gera e classifica eventos entre os dois snapshots mais recentes do IDAP estadual."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
import sys

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from vigibarragens.history import detect_changes, write_change_events  # noqa: E402
from vigibarragens.intelligence.change_classifier import classify_change, sort_changes  # noqa: E402

HISTORICO = RAIZ / "dados" / "tratados" / "historico_idap"
TRATADOS = RAIZ / "dados" / "tratados"
SAIDA_RAW = TRATADOS / "eventos_mudanca_idap.jsonl"
SAIDA_CSV = TRATADOS / "mudancas_recentes.csv"
SAIDA_JSON = TRATADOS / "mudancas_recentes_resumo.json"
CAMPOS = (
    "categoria_risco", "dano_potencial_associado", "nivel", "completude",
    "confiabilidade", "idap", "alertavel", "contatos_validados_90d",
    "municipios_potencialmente_afetados",
)


def ler_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep=";", dtype=str, encoding="utf-8-sig").fillna("")


def escrever_classificados(rows: list[dict]) -> None:
    fields = ["id_snisb", "field", "previous", "current", "detected_at", "event_type", "criticidade_evento", "direcao", "razao_classificacao"]
    with SAIDA_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter=";")
        w.writeheader(); w.writerows(rows)
    counts = Counter(r["criticidade_evento"] for r in rows)
    summary = {
        "contrato": "vigibarragens-mudancas-v2.2",
        "n_eventos": len(rows),
        "por_criticidade": {k: counts.get(k, 0) for k in ("emergencial", "critica", "atencao", "informativa")},
        "n_agravamentos": sum(r["direcao"] == "piora" for r in rows),
        "n_expansoes_territoriais": sum(r["direcao"] == "expansao_territorial" for r in rows),
        "nota": "Criticidade do evento não substitui nem recalcula o nível operacional IDAP.",
    }
    SAIDA_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    snapshots = sorted(HISTORICO.glob("idap_*.csv"))
    if len(snapshots) < 2:
        print("Histórico insuficiente: são necessários ao menos dois snapshots IDAP.")
        write_change_events([], SAIDA_RAW); escrever_classificados([]); return
    anterior, atual = snapshots[-2], snapshots[-1]
    eventos = detect_changes(ler_csv(anterior), ler_csv(atual), id_col="id_snisb", fields=CAMPOS)
    write_change_events(eventos, SAIDA_RAW)
    classificados = sort_changes([classify_change(e.to_dict()) for e in eventos])
    escrever_classificados(classificados)
    print(f"Mudanças IDAP: {len(classificados)} evento(s) entre {anterior.name} e {atual.name}")
    print(f"  classificados: {SAIDA_CSV.relative_to(RAIZ)}")
    print(f"  resumo: {SAIDA_JSON.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
