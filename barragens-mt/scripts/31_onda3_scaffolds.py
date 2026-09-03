"""Scaffolds Onda 3: manchas PAE, Sisagua, linha de base VIGIPÓS.

Gera esqueletos e documentação de ingestão — não inventa geometrias oficiais.
Saídas em dados/tratados/ e relatorios/.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

import comum

AGORA = datetime.now().isoformat(timespec="seconds")


def escrever_csv(caminho: Path, campos: list[str], rows: list[dict]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in campos})


def main() -> None:
    comum.DADOS_TRATADOS.mkdir(parents=True, exist_ok=True)
    rel = comum.RAIZ / "relatorios"
    rel.mkdir(parents=True, exist_ok=True)

    # PAE / ZAS — inventário de cobertura (vazio até SEMA/empreendedor entregar)
    pae_campos = [
        "id_snisb",
        "nome",
        "municipio_sede",
        "tem_pae",
        "tem_mancha_zas",
        "fonte_geometria",
        "caminho_geojson",
        "observacao",
    ]
    inv = comum.DADOS_TRATADOS / "inventario_barragens_mt.csv"
    rows_pae: list[dict] = []
    if inv.exists():
        with inv.open(encoding="utf-8-sig", newline="") as f:
            for i, r in enumerate(csv.DictReader(f, delimiter=";")):
                if i >= 50:
                    break
                rows_pae.append(
                    {
                        "id_snisb": r.get("id_snisb") or "",
                        "nome": r.get("nome") or "",
                        "municipio_sede": r.get("municipio") or "",
                        "tem_pae": "desconhecido",
                        "tem_mancha_zas": "não",
                        "fonte_geometria": "",
                        "caminho_geojson": "",
                        "observacao": "Aguardando mancha oficial — não usar proxy sem rótulo",
                    }
                )
    escrever_csv(comum.DADOS_TRATADOS / "pae_manchas_cobertura.csv", pae_campos, rows_pae)

    # Sisagua — captações / sistemas (esqueleto)
    sisagua_campos = [
        "municipio",
        "codigo_ibge",
        "tipo_captacao",
        "nome_sistema",
        "latitude",
        "longitude",
        "fonte",
        "observacao",
    ]
    escrever_csv(
        comum.DADOS_TRATADOS / "sisagua_captacoes_eixo_esqueleto.csv",
        sisagua_campos,
        [
            {
                "municipio": "Cuiabá",
                "codigo_ibge": "",
                "tipo_captacao": "superficial",
                "nome_sistema": "A preencher com export Sisagua",
                "latitude": "",
                "longitude": "",
                "fonte": "SISAGUA",
                "observacao": "Scaffold — importar planilha oficial SES/Vigiagua",
            }
        ],
    )

    # VIGIPÓS — linhas de base SINAN/SIM (agregado vazio)
    vigipos_campos = [
        "municipio",
        "ano",
        "agravo",
        "casos",
        "obitos",
        "fonte",
        "observacao",
    ]
    escrever_csv(
        comum.DADOS_TRATADOS / "vigipos_linha_base_esqueleto.csv",
        vigipos_campos,
        [
            {
                "municipio": "Cuiabá",
                "ano": "2024",
                "agravo": "exemplo_dengue",
                "casos": "",
                "obitos": "",
                "fonte": "SINAN",
                "observacao": "Substituir por série oficial antes de usar em painel",
            }
        ],
    )

    sisagua_real = comum.DADOS_TRATADOS / "sisagua_captacoes_eixo.csv"
    vigipos_real = comum.DADOS_TRATADOS / "vigipos_linha_base.csv"
    sisagua_status = "real" if sisagua_real.is_file() and sisagua_real.stat().st_size > 80 else "esqueleto"
    vigipos_status = "real" if vigipos_real.is_file() and vigipos_real.stat().st_size > 80 else "esqueleto"

    status = {
        "gerado": AGORA,
        "pae_linhas": len(rows_pae),
        "nota_pae": "Cobertura parcial já ajuda C1–C7; geometria oficial obrigatória.",
        "sisagua": sisagua_status,
        "vigipos": vigipos_status,
        "sisagua_arquivo": sisagua_real.name if sisagua_status == "real" else "sisagua_captacoes_eixo_esqueleto.csv",
        "vigipos_arquivo": vigipos_real.name if vigipos_status == "real" else "vigipos_linha_base_esqueleto.csv",
    }
    (comum.DADOS_TRATADOS / "onda3_dados_status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (rel / "onda3_dados_scaffolds.md").write_text(
        "\n".join(
            [
                "# Onda 3 — scaffolds de dados",
                "",
                f"Gerado em {AGORA}.",
                "",
                "## Manchas PAE / ZAS",
                "- Arquivo: `dados/tratados/pae_manchas_cobertura.csv`",
                "- Não inventar geometria: só registrar o que a SEMA/empreendedor entregar.",
                "",
                "## Sisagua / captações",
                f"- Status: **{sisagua_status}**",
                f"- Arquivo: `dados/tratados/{status['sisagua_arquivo']}`",
                "- Esqueleto residual: `sisagua_captacoes_eixo_esqueleto.csv` (fallback).",
                "",
                "## VIGIPÓS (SINAN/SIM)",
                f"- Status: **{vigipos_status}**",
                f"- Arquivo: `dados/tratados/{status['vigipos_arquivo']}`",
                "- Ver também `docs/05-vigipos-barragens.md`.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(
        f"PAE={len(rows_pae)} linhas; Sisagua={sisagua_status}; VIGIPÓS={vigipos_status}"
    )


if __name__ == "__main__":
    main()
