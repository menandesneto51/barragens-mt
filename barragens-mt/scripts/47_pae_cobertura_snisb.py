"""Cobertura de PAE a partir do SNISB (substitui scaffold da etapa 31).

Preenche `tem_pae` com Sim/Não/desconhecido a partir de `possui_pae` do inventário.
`tem_mancha_zas` continua **não** até existir geometria oficial (SEMA/empreendedor).

Saídas:
  dados/tratados/pae_manchas_cobertura.csv
  dados/tratados/pae_cobertura_status.json
  relatorios/pae_cobertura_snisb.md

Uso:
  python scripts/47_pae_cobertura_snisb.py
  python executar.py 47
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import comum

INV = comum.DADOS_TRATADOS / "inventario_barragens_mt.csv"
SAIDA = comum.DADOS_TRATADOS / "pae_manchas_cobertura.csv"
STATUS = comum.DADOS_TRATADOS / "pae_cobertura_status.json"
REL = comum.RELATORIOS / "pae_cobertura_snisb.md"

CAMPOS = [
    "id_snisb",
    "nome",
    "municipio_sede",
    "tem_pae",
    "tem_mancha_zas",
    "fonte_geometria",
    "caminho_geojson",
    "observacao",
]


def _norm_pae(valor: Any) -> str:
    t = str(valor or "").strip().lower()
    if t in {"sim", "s", "yes", "true", "1"}:
        return "sim"
    if t in {"não", "nao", "n", "no", "false", "0"}:
        return "nao"
    return "desconhecido"


def main() -> None:
    comum.preparar_diretorios()
    if not INV.exists():
        raise SystemExit(f"base ausente: {INV.name}. Rode o pipeline até a etapa 05.")

    rows: list[dict[str, str]] = []
    with INV.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            tem = _norm_pae(r.get("possui_pae"))
            obs = {
                "sim": "PAE declarado no SNISB — geometria ZAS/mancha ainda não ingerida",
                "nao": "SNISB indica ausência de PAE",
                "desconhecido": "Campo possui_pae vazio no SNISB — lacuna cadastral",
            }[tem]
            rows.append(
                {
                    "id_snisb": (r.get("id_snisb") or "").strip(),
                    "nome": (r.get("nome") or "").strip(),
                    "municipio_sede": (r.get("municipio") or "").strip(),
                    "tem_pae": tem,
                    "tem_mancha_zas": "nao",
                    "fonte_geometria": "",
                    "caminho_geojson": "",
                    "observacao": obs,
                }
            )

    comum.salvar_csv(SAIDA, rows, CAMPOS)
    cont = Counter(r["tem_pae"] for r in rows)
    payload = {
        "ok": True,
        "n_barragens": len(rows),
        "tem_pae_sim": cont.get("sim", 0),
        "tem_pae_nao": cont.get("nao", 0),
        "tem_pae_desconhecido": cont.get("desconhecido", 0),
        "tem_mancha_zas": 0,
        "fonte": "SNISB possui_pae via inventario_barragens_mt.csv",
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "nota": "Manchas oficiais permanecem pendentes (SEMA/empreendedor/ANM).",
    }
    STATUS.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    REL.write_text(
        "\n".join(
            [
                "# Cobertura de PAE (SNISB)",
                "",
                f"- Barragens: **{len(rows)}**",
                f"- PAE = sim: **{cont.get('sim', 0)}**",
                f"- PAE = não: **{cont.get('nao', 0)}**",
                f"- PAE desconhecido (campo vazio): **{cont.get('desconhecido', 0)}**",
                f"- Com geometria ZAS/mancha ingerida: **0**",
                "",
                "Fonte: `possui_pae` do inventário SNISB. Não inventa mancha oficial.",
                f"Arquivo: `{SAIDA.relative_to(comum.RAIZ)}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(
        f"  PAE sim={cont.get('sim', 0)} não={cont.get('nao', 0)} "
        f"desconhecido={cont.get('desconhecido', 0)} / {len(rows)}"
    )


if __name__ == "__main__":
    main()
