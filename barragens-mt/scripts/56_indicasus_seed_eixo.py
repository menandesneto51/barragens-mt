"""Seed IndicaSUS municipal para o eixo piloto (termo O do IPAPD).

Agrega o exemplo versionado em dados/config/exemplos/indicasus_leitos.exemplo.csv
para municípios do eixo Manso–Cuiabá quando o extrato DW estiver vazio.

Não inventa dados estaduais: só popula o eixo a partir do exemplo institucional
de desenvolvimento, com fonte rotulada.

Saídas:
  dados/tratados/indicasus_leitos_municipio.csv (se vazio ou --force)
  dados/tratados/indicasus_leitos_mt.csv (se vazio ou --force)
  dados/tratados/indicasus_leitos_status.json

Uso:
  python scripts/56_indicasus_seed_eixo.py
  python executar.py 56
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import comum

EXEMPLO = comum.RAIZ / "dados" / "config" / "exemplos" / "indicasus_leitos.exemplo.csv"
PILOTO = comum.DADOS_TRATADOS / "piloto_manso_cuiaba.csv"
OUT_MUN = comum.DADOS_TRATADOS / "indicasus_leitos_municipio.csv"
OUT_MT = comum.DADOS_TRATADOS / "indicasus_leitos_mt.csv"
STATUS = comum.DADOS_TRATADOS / "indicasus_leitos_status.json"


def _ler(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        amostra = f.read(2048)
        f.seek(0)
        delim = ";" if amostra.count(";") >= amostra.count(",") else ","
        return list(csv.DictReader(f, delimiter=delim))


def _vazio(path: Path) -> bool:
    if not path.is_file():
        return True
    rows = _ler(path)
    return len(rows) == 0


def municipios_piloto() -> set[str]:
    nomes: set[str] = set()
    for r in _ler(PILOTO):
        for col in ("municipio_sede", "municipio"):
            v = (r.get(col) or "").strip()
            if v:
                nomes.add(v.casefold())
    # Afetados típicos do eixo
    for extra in ("Cuiabá", "Várzea Grande", "Chapada dos Guimarães", "Acorizal", "Barão de Melgaço"):
        nomes.add(extra.casefold())
    return nomes


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="Sobrescreve CSVs mesmo se não vazios")
    args = ap.parse_args()
    comum.preparar_diretorios()

    if not EXEMPLO.is_file():
        print(f"exemplo ausente: {EXEMPLO}")
        STATUS.write_text(
            json.dumps(
                {
                    "ok": False,
                    "motivo": "exemplo IndicaSUS ausente",
                    "fonte": str(EXEMPLO),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return

    if not args.force and not _vazio(OUT_MUN) and not _vazio(OUT_MT):
        print("IndicaSUS já populado — use --force para regenerar a partir do exemplo")
        STATUS.write_text(
            json.dumps(
                {
                    "ok": True,
                    "motivo": "já populado (seed não aplicado)",
                    "fonte": "existente",
                    "n_municipio": len(_ler(OUT_MUN)),
                    "n_estabelecimentos": len(_ler(OUT_MT)),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return

    alvo = municipios_piloto()
    rows = _ler(EXEMPLO)
    # Filtra eixo; se nenhum bater, usa todas as linhas do exemplo
    filtrados = [
        r
        for r in rows
        if (r.get("municipio") or "").strip().casefold() in alvo
    ] or rows

    # MT detalhado
    campos_mt = [
        "codigo_cnes",
        "nome_estabelecimento",
        "codigo_municipio_ibge",
        "municipio",
        "tipo_leito",
        "leitos_cadastrados",
        "leitos_operacionais",
        "leitos_ocupados",
        "leitos_disponiveis",
        "taxa_ocupacao",
        "atualizado_em",
        "fonte",
    ]
    with OUT_MT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos_mt, delimiter=";", extrasaction="ignore")
        w.writeheader()
        for r in filtrados:
            r = dict(r)
            r["fonte"] = "seed_exemplo_eixo"
            if not r.get("atualizado_em"):
                r["atualizado_em"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            w.writerow(r)

    # Agrega município (tipo total preferencial)
    agg: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "leitos_operacionais": 0.0,
            "leitos_ocupados": 0.0,
            "leitos_disponiveis": 0.0,
            "n_estabelecimentos": 0.0,
        }
    )
    meta: dict[str, dict[str, str]] = {}
    vistos_cnes: dict[str, set[str]] = defaultdict(set)
    for r in filtrados:
        tipo = str(r.get("tipo_leito") or "").casefold()
        if tipo and tipo != "total":
            continue
        mun = (r.get("municipio") or "").strip()
        if not mun:
            continue
        cod = (r.get("codigo_municipio_ibge") or "").strip()
        meta[mun] = {"codigo_municipio_ibge": cod, "municipio": mun}
        for col in ("leitos_operacionais", "leitos_ocupados", "leitos_disponiveis"):
            try:
                agg[mun][col] += float(str(r.get(col) or 0).replace(",", "."))
            except ValueError:
                pass
        cnes = str(r.get("codigo_cnes") or "")
        if cnes and cnes not in vistos_cnes[mun]:
            vistos_cnes[mun].add(cnes)
            agg[mun]["n_estabelecimentos"] += 1

    campos_mun = [
        "codigo_municipio_ibge",
        "municipio",
        "leitos_operacionais",
        "leitos_ocupados",
        "leitos_disponiveis",
        "taxa_ocupacao",
        "n_estabelecimentos",
        "fonte",
    ]
    with OUT_MUN.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos_mun, delimiter=";", extrasaction="ignore")
        w.writeheader()
        for mun, vals in sorted(agg.items()):
            op = vals["leitos_operacionais"]
            oc = vals["leitos_ocupados"]
            taxa = round(100.0 * oc / op, 1) if op > 0 else ""
            w.writerow(
                {
                    "codigo_municipio_ibge": meta[mun]["codigo_municipio_ibge"],
                    "municipio": mun,
                    "leitos_operacionais": int(op) if op == int(op) else op,
                    "leitos_ocupados": int(oc) if oc == int(oc) else oc,
                    "leitos_disponiveis": int(vals["leitos_disponiveis"])
                    if vals["leitos_disponiveis"] == int(vals["leitos_disponiveis"])
                    else vals["leitos_disponiveis"],
                    "taxa_ocupacao": taxa,
                    "n_estabelecimentos": int(vals["n_estabelecimentos"]),
                    "fonte": "seed_exemplo_eixo",
                }
            )

    status = {
        "ok": True,
        "motivo": "seed a partir do exemplo do eixo (substituir por extrato IndicaSUS/DW)",
        "fonte": str(EXEMPLO.relative_to(comum.RAIZ)),
        "n_estabelecimentos": len(filtrados),
        "n_municipio": len(agg),
        "gerado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "checklist": [
            "Obter extrato IndicaSUS/DW com leitos operacionais e ocupados por município",
            "Substituir CSVs seed (fonte=seed_exemplo_eixo) pelo extrato oficial",
            "Rodar python executar.py 43 quando o conector DW estiver disponível",
        ],
    }
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"escrito {OUT_MT.relative_to(comum.RAIZ)} ({len(filtrados)} linhas)")
    print(f"escrito {OUT_MUN.relative_to(comum.RAIZ)} ({len(agg)} municípios)")
    print(f"escrito {STATUS.relative_to(comum.RAIZ)}")


if __name__ == "__main__":
    main()
