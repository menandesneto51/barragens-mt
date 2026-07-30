"""Coleta CNES estadual (MT) a partir de cnes_municipios_alvo_mt.csv.

Reusa a paginação e armadilhas do endpoint descobertas na etapa 11
(codigo IBGE 6 dígitos; limit máx. 20).

Saídas:
  dados/tratados/cnes_estabelecimentos_mt.csv
  dados/tratados/cnes_estabelecimentos_mt.geojson
  dados/tratados/cnes_estadual_status.json

Uso:
  python scripts/33_cnes_estadual.py
  python scripts/33_cnes_estadual.py --limite 5          # teste
  python scripts/33_cnes_estadual.py --so-faltantes      # pula mun. já no CSV
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import comum

# Reaproveita paginação/normalização da etapa 11 sem executar o main dela.
_SCRIPTS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("cnes11", _SCRIPTS / "11_cnes_rede_saude.py")
if spec is None or spec.loader is None:
    raise SystemExit("não foi possível carregar 11_cnes_rede_saude.py")
cnes11 = importlib.util.module_from_spec(spec)
sys.modules["cnes11"] = cnes11
spec.loader.exec_module(cnes11)

SAIDA_CSV = comum.DADOS_TRATADOS / "cnes_estabelecimentos_mt.csv"
SAIDA_GEO = comum.DADOS_TRATADOS / "cnes_estabelecimentos_mt.geojson"
STATUS = comum.DADOS_TRATADOS / "cnes_estadual_status.json"
ALVOS = comum.DADOS_TRATADOS / "cnes_municipios_alvo_mt.csv"
EIXO = comum.DADOS_TRATADOS / "cnes_estabelecimentos_regiao_cuiaba.csv"

COLUNAS = [
    "codigo_cnes",
    "nome_fantasia",
    "nome_razao_social",
    "codigo_municipio",
    "municipio",
    "no_eixo_montante",
    "no_eixo_jusante",
    "bairro_estabelecimento",
    "endereco_estabelecimento",
    "descricao_esfera_administrativa",
    "descricao_nivel_hierarquia",
    "descricao_turno_atendimento",
    "codigo_tipo_unidade",
    "tipo_gestao",
    "atendimento_hospitalar",
    "atendimento_ambulatorial",
    "ambulatorial_sus",
    "centro_cirurgico",
    "centro_obstetrico",
    "centro_neonatal",
    "servico_apoio",
    "latitude",
    "longitude",
    "numero_telefone_estabelecimento",
    "data_atualizacao",
    "origem_coleta",
]


def ler_alvos() -> list[dict[str, str]]:
    if not ALVOS.exists():
        raise SystemExit("rode antes: python scripts/30_cnes_estadual_scaffold.py")
    with ALVOS.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def ler_existente() -> list[dict[str, Any]]:
    if not SAIDA_CSV.exists():
        # Bootstrap a partir do eixo, se houver.
        if EIXO.exists():
            with EIXO.open(encoding="utf-8-sig", newline="") as f:
                rows = list(csv.DictReader(f, delimiter=";"))
            for r in rows:
                r.setdefault("origem_coleta", "eixo_cuiaba")
            return rows
        return []
    with SAIDA_CSV.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def main() -> None:
    parser = argparse.ArgumentParser(description="CNES estadual MT")
    parser.add_argument("--limite", type=int, default=0, help="Máx. municípios a coletar (0=todos)")
    parser.add_argument(
        "--so-faltantes",
        action="store_true",
        help="Pula municípios que já têm registros no CSV estadual",
    )
    args = parser.parse_args()

    comum.preparar_diretorios()
    # Garante alvos atualizados.
    if not ALVOS.exists():
        from importlib import import_module

        # fallback: gera scaffold inline
        sys.path.insert(0, str(_SCRIPTS.parent))
        mod = importlib.util.spec_from_file_location(
            "cnes30", _SCRIPTS / "30_cnes_estadual_scaffold.py"
        )
        if mod and mod.loader:
            m = importlib.util.module_from_spec(mod)
            mod.loader.exec_module(m)
            m.main()

    alvos = ler_alvos()
    existentes = ler_existente()
    munis_ok = {r.get("municipio") for r in existentes}
    por_cnes: dict[str, dict[str, Any]] = {}
    for r in existentes:
        chave = str(r.get("codigo_cnes") or "")
        if chave:
            por_cnes[chave] = r

    a_coletar = []
    for a in alvos:
        nome = (a.get("municipio") or "").strip()
        codigo = (a.get("codigo_cnes_6d") or "").strip()
        if not codigo:
            continue
        if args.so_faltantes and nome in munis_ok:
            continue
        a_coletar.append(a)
    if args.limite and args.limite > 0:
        a_coletar = a_coletar[: args.limite]

    print(f"CNES estadual — {len(a_coletar)} município(s) a coletar (base atual {len(por_cnes)} US)")
    novos = 0
    with comum.cliente(verificar_tls=False) as cli:
        cli.headers.update(cnes11.NAVEGADOR)
        for a in a_coletar:
            nome = a["municipio"]
            codigo = a["codigo_cnes_6d"]
            mun_meta = {
                "nome": nome,
                "no_eixo_montante": False,
                "no_eixo_jusante": False,
            }
            lote = [cnes11.normalizar(item, mun_meta) for item in cnes11.paginar(cli, codigo)]
            for r in lote:
                r["origem_coleta"] = "estadual"
                chave = str(r.get("codigo_cnes") or "")
                if not chave:
                    continue
                if chave not in por_cnes:
                    novos += 1
                por_cnes[chave] = r
            hosp = sum(1 for r in lote if r.get("atendimento_hospitalar") == "Sim")
            print(f"  {nome:<32} {len(lote):>5} est. | {hosp:>3} hosp.")

    registros = list(por_cnes.values())
    comum.salvar_csv(SAIDA_CSV, registros, COLUNAS)

    def _float(v: Any) -> float | None:
        if v in (None, "", "None"):
            return None
        try:
            return float(str(v).replace(",", "."))
        except (TypeError, ValueError):
            return None

    geo: list[dict[str, Any]] = []
    for r in registros:
        lon = _float(r.get("longitude"))
        lat = _float(r.get("latitude"))
        if lon is None or lat is None:
            continue
        if not comum.dentro_do_bbox(lon, lat):
            continue
        item = dict(r)
        item["longitude"] = lon
        item["latitude"] = lat
        geo.append(item)
    comum.salvar_geojson(SAIDA_GEO, geo, "longitude", "latitude")

    status = {
        "gerado": datetime.now().isoformat(timespec="seconds"),
        "municipios_alvo": len(alvos),
        "municipios_coletados_nesta_rodada": len(a_coletar),
        "estabelecimentos": len(registros),
        "com_coordenada_mt": len(geo),
        "novos_nesta_rodada": novos,
        "arquivo_csv": SAIDA_CSV.name,
        "arquivo_geojson": SAIDA_GEO.name,
        "bloqueio": None,
    }
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"\nTotal: {len(registros)} estabelecimentos ({len(geo)} com coord.) · "
        f"+{novos} novos → {SAIDA_CSV.name}"
    )


if __name__ == "__main__":
    main()
