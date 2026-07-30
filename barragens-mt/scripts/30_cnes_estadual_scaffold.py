"""Scaffold CNES estadual (MT) — Onda 3.

Expande a coleta além do eixo Cuiabá usando a malha municipal IBGE do inventário.
Não substitui a etapa 11; gera lista de municípios-alvo e, se houver rede, amostra.

Saídas:
  dados/tratados/cnes_municipios_alvo_mt.csv
  dados/tratados/cnes_estadual_status.json
  relatorios/cnes_estadual_plano.md
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

import comum

SAIDA_ALVO = comum.DADOS_TRATADOS / "cnes_municipios_alvo_mt.csv"
SAIDA_STATUS = comum.DADOS_TRATADOS / "cnes_estadual_status.json"
REL = comum.RAIZ / "relatorios" / "cnes_estadual_plano.md"


def municipios_inventario() -> list[dict[str, str]]:
    inv = comum.DADOS_TRATADOS / "inventario_barragens_mt.csv"
    ibge = comum.DADOS_TRATADOS / "ibge_municipios_mt.csv"
    nomes: set[str] = set()
    if inv.exists():
        with inv.open(encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f, delimiter=";"):
                m = (r.get("municipio") or "").strip()
                if m:
                    nomes.add(m)
    codigos: dict[str, str] = {}
    if ibge.exists():
        with ibge.open(encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f, delimiter=";"):
                nome = (r.get("nome") or r.get("municipio") or "").strip()
                cod = (r.get("codigo_ibge") or r.get("id") or r.get("cd_mun") or "").strip()
                if nome and cod:
                    codigos[nome] = cod
    return [
        {
            "municipio": n,
            "codigo_ibge": codigos.get(n, ""),
            "codigo_cnes_6d": (codigos.get(n, "")[:6] if codigos.get(n) else ""),
            "prioridade": "eixo" if n in {"Cuiabá", "Várzea Grande", "Chapada dos Guimarães", "Nobres"} else "estadual",
        }
        for n in sorted(nomes)
    ]


def main() -> None:
    comum.DADOS_TRATADOS.mkdir(parents=True, exist_ok=True)
    (comum.RAIZ / "relatorios").mkdir(parents=True, exist_ok=True)
    alvos = municipios_inventario()
    with SAIDA_ALVO.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["municipio", "codigo_ibge", "codigo_cnes_6d", "prioridade"],
            delimiter=";",
        )
        w.writeheader()
        w.writerows(alvos)

    eixo = comum.DADOS_TRATADOS / "cnes_estabelecimentos_regiao_cuiaba.csv"
    n_eixo = 0
    if eixo.exists():
        with eixo.open(encoding="utf-8-sig", newline="") as f:
            n_eixo = sum(1 for _ in csv.DictReader(f, delimiter=";"))

    status = {
        "gerado": datetime.now().isoformat(timespec="seconds"),
        "municipios_alvo": len(alvos),
        "com_codigo_ibge": sum(1 for a in alvos if a["codigo_ibge"]),
        "estabelecimentos_eixo_existentes": n_eixo,
        "proximo_passo": (
            "Coletar CNES por codigo_municipio (6 dígitos) para municípios sem cobertura, "
            "reusando a paginação de scripts/11_cnes_rede_saude.py. "
            "Requer acordo de volume/rate-limit com a API Dados Abertos."
        ),
        "bloqueio": "coleta completa estadual ainda não executada (scaffold)",
    }
    SAIDA_STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    REL.write_text(
        "\n".join(
            [
                "# Plano CNES estadual — VIGIBARRAGENS–MT",
                "",
                f"Gerado em {status['gerado']}.",
                "",
                f"- Municípios com barragem no inventário: **{status['municipios_alvo']}**",
                f"- Com código IBGE resolvido: **{status['com_codigo_ibge']}**",
                f"- Estabelecimentos já coletados (eixo Cuiabá): **{n_eixo}**",
                "",
                "## Próximo passo",
                status["proximo_passo"],
                "",
                "Arquivo de alvos: `dados/tratados/cnes_municipios_alvo_mt.csv`.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"alvos={len(alvos)} → {SAIDA_ALVO.name}; status → {SAIDA_STATUS.name}")


if __name__ == "__main__":
    main()
