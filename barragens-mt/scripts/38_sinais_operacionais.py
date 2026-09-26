"""Mantém o cadastro persistente de sinais operacionais das barragens.

O script NÃO gera fatos operacionais. Apenas:
- adiciona barragens novas ao cadastro;
- preserva valores já existentes;
- mantém campos de proveniência explícitos;
- nunca transforma campo vazio em confirmação de segurança.

Saída:
  dados/tratados/sinais_operacionais_mt.csv
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import comum

OUT = comum.DADOS_TRATADOS / "sinais_operacionais_mt.csv"
INVENTARIO = comum.DADOS_TRATADOS / "inventario_barragens_mt.csv"

FIELDS = [
    "id_snisb",
    "nome",
    "municipio_sede",
    "rompimento_confirmado",
    "perda_subita_de_nivel",
    "evacuacao_determinada",
    "sensores_criticos_em_falha",
    "mancha_atinge_unidade_estrategica",
    "mancha_atinge_captacao",
    "municipios_zas_sem_confirmacao",
    "fonte_observacional",
    "referencia_temporal",
    "documento_referencia",
    "observacao",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def main() -> None:
    comum.preparar_diretorios()
    inventario = read_csv(INVENTARIO)
    if not inventario:
        raise SystemExit("inventário ausente; execute a etapa 05.")

    existentes = {
        str(r.get("id_snisb") or "").strip(): r
        for r in read_csv(OUT)
        if str(r.get("id_snisb") or "").strip()
    }

    rows: list[dict[str, Any]] = []
    novos = 0
    for b in inventario:
        bid = str(b.get("id_snisb") or "").strip()
        if not bid:
            continue
        anterior = existentes.get(bid, {})
        row = {field: anterior.get(field, "") for field in FIELDS}
        row["id_snisb"] = bid
        row["nome"] = b.get("nome") or row.get("nome") or ""
        row["municipio_sede"] = b.get("municipio") or row.get("municipio_sede") or ""
        if bid not in existentes:
            novos += 1
        rows.append(row)

    rows.sort(key=lambda r: (str(r.get("municipio_sede") or ""), str(r.get("nome") or "")))
    comum.salvar_csv(OUT, rows, FIELDS)
    print(
        f"Sinais operacionais: {len(rows)} barragens · {novos} nova(s). "
        "Campos factuais permanecem vazios até evidência explícita."
    )


if __name__ == "__main__":
    main()
