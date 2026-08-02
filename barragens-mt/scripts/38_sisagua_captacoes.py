"""Captações de água no eixo Manso–Cuiabá (Sisagua aberto + fallback OSM).

Tenta obter pontos do portal aberto Sisagua/dados.gov; se indisponível,
consulta OpenStreetMap (waterway=intake, man_made=water_works, landuse=reservoir
com nome de ETA/captação) no bbox do eixo.

Saídas:
  dados/tratados/sisagua_captacoes_eixo.csv
  relatorios/sisagua_captacoes_eixo.md

Uso:
  python scripts/38_sisagua_captacoes.py
  python executar.py 38
"""

from __future__ import annotations

import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import comum

SAIDA = comum.DADOS_TRATADOS / "sisagua_captacoes_eixo.csv"
REL = comum.RELATORIOS / "sisagua_captacoes_eixo.md"
BRUTOS = comum.DADOS_BRUTOS / "sisagua"
INTERESSE = comum.DADOS_TRATADOS / "cuiaba_municipios_de_interesse.json"
EIXO_GEO = comum.DADOS_TRATADOS / "eixo_hidrografico_manso_cuiaba.geojson"

OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
)

# Tentativas de datasets abertos (podem 403/timeout neste ambiente).
URLS_SISAGUA = (
    "https://dados.gov.br/api/3/action/package_search?q=sisagua+captacao",
    "https://sisagua.saude.gov.br/sisagua/dados_abertos/",
)

UA = "VIGIBARRAGENS-MT/1.0 (SES-MT; captacoes eixo Manso-Cuiaba)"

CAMPOS = [
    "municipio",
    "codigo_ibge",
    "tipo_captacao",
    "nome_sistema",
    "latitude",
    "longitude",
    "fonte",
    "observacao",
]


def municipios_eixo() -> dict[str, str]:
    if not INTERESSE.exists():
        return {}
    data = json.loads(INTERESSE.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for m in data.get("municipios") or []:
        cod = str(m.get("codigo_ibge") or "").strip()
        nome = str(m.get("nome") or "").strip()
        if cod and nome:
            out[cod] = nome
    return out


def bbox_eixo() -> tuple[float, float, float, float]:
    """south, west, north, east — folga ao redor do eixo Manso–Cuiabá."""
    if EIXO_GEO.exists():
        try:
            gj = json.loads(EIXO_GEO.read_text(encoding="utf-8"))
            lats: list[float] = []
            lons: list[float] = []

            def _walk(coords: Any) -> None:
                if isinstance(coords, (list, tuple)) and coords:
                    if isinstance(coords[0], (int, float)):
                        lons.append(float(coords[0]))
                        lats.append(float(coords[1]))
                    else:
                        for c in coords:
                            _walk(c)

            for f in gj.get("features") or []:
                _walk((f.get("geometry") or {}).get("coordinates"))
            if lats and lons:
                pad = 0.15
                return (
                    min(lats) - pad,
                    min(lons) - pad,
                    max(lats) + pad,
                    max(lons) + pad,
                )
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    # Fallback aproximado Manso → Leverger
    return (-16.15, -56.55, -15.20, -55.55)


def tentar_sisagua_aberto() -> list[dict[str, Any]]:
    """Placeholder de ingestão oficial — grava bruto se algum endpoint responder."""
    BRUTOS.mkdir(parents=True, exist_ok=True)
    munis = municipios_eixo()
    nomes = {n.casefold() for n in munis.values()}
    coletados: list[dict[str, Any]] = []

    for url in URLS_SISAGUA:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25) as resp:
                raw = resp.read()
            destino = BRUTOS / ("probe_" + urllib.parse.quote(url, safe="")[-40:] + ".bin")
            destino.write_bytes(raw[:500_000])
            # CKAN package_search
            if b"result" in raw[:200] or raw[:1] == b"{":
                try:
                    data = json.loads(raw.decode("utf-8", errors="replace"))
                    packs = ((data.get("result") or {}).get("results")) or []
                    for p in packs[:5]:
                        for res in p.get("resources") or []:
                            rurl = res.get("url") or ""
                            if not rurl or not any(
                                rurl.lower().endswith(ext) for ext in (".csv", ".xlsx", ".json")
                            ):
                                continue
                            print(f"  Sisagua recurso encontrado (não baixado em lote): {rurl}")
                except json.JSONDecodeError:
                    pass
            print(f"  aviso: portal Sisagua respondeu em {url[:60]}… sem parser de pontos")
        except Exception as exc:  # noqa: BLE001
            print(f"  Sisagua aberto indisponível ({url[:50]}…): {exc}")
        time.sleep(0.5)

    # CSV local em brutos com lat/lon (export manual Sisagua/SES).
    for path in sorted(BRUTOS.glob("*.csv")):
        try:
            sample = path.read_text(encoding="utf-8-sig", errors="replace")[:4096]
            delim = ";" if sample.count(";") >= sample.count(",") else ","
            with path.open(encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f, delimiter=delim):
                    mun = (row.get("municipio") or row.get("Municipio") or "").strip()
                    if nomes and mun.casefold() not in nomes:
                        continue
                    try:
                        la = float(
                            str(row.get("latitude") or row.get("Latitude") or "").replace(
                                ",", "."
                            )
                        )
                        lo = float(
                            str(row.get("longitude") or row.get("Longitude") or "").replace(
                                ",", "."
                            )
                        )
                    except ValueError:
                        continue
                    coletados.append(
                        {
                            "municipio": mun,
                            "codigo_ibge": row.get("codigo_ibge") or row.get("ibge") or "",
                            "tipo_captacao": row.get("tipo_captacao")
                            or row.get("tipo")
                            or "superficial",
                            "nome_sistema": row.get("nome_sistema")
                            or row.get("nome")
                            or path.stem,
                            "latitude": f"{la:.6f}",
                            "longitude": f"{lo:.6f}",
                            "fonte": "SISAGUA",
                            "observacao": f"importado de {path.name}",
                        }
                    )
        except OSError:
            continue
    return coletados


def _post_overpass(q: str) -> dict[str, Any] | None:
    data = urllib.parse.urlencode({"data": q}).encode()
    for url in OVERPASS_URLS:
        try:
            req = urllib.request.Request(
                url,
                data=data,
                headers={"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"  Overpass {url}: {exc}")
            time.sleep(2)
    return None


def captacoes_osm() -> list[dict[str, Any]]:
    south, west, north, east = bbox_eixo()
    q = f"""
[out:json][timeout:60];
(
  node["waterway"="intake"]({south},{west},{north},{east});
  node["man_made"="water_works"]({south},{west},{north},{east});
  node["man_made"="water_tower"]({south},{west},{north},{east});
  node["pipeline"="intake"]({south},{west},{north},{east});
  way["man_made"="water_works"]({south},{west},{north},{east});
  way["waterway"="intake"]({south},{west},{north},{east});
);
out center tags;
""".strip()
    print(f"  OSM Overpass bbox {south:.3f},{west:.3f},{north:.3f},{east:.3f}", flush=True)
    raw = _post_overpass(q)
    if not raw:
        return []

    munis = municipios_eixo()
    # mapa reverso nome→ibge aproximado não geocodificado; deixa código vazio
    nome_por_ibge = {v: k for k, v in munis.items()}

    out: list[dict[str, Any]] = []
    seen: set[tuple[float, float]] = set()
    for el in raw.get("elements") or []:
        tags = el.get("tags") or {}
        if "lat" in el and "lon" in el:
            la, lo = float(el["lat"]), float(el["lon"])
        elif "center" in el:
            la, lo = float(el["center"]["lat"]), float(el["center"]["lon"])
        else:
            continue
        key = (round(la, 5), round(lo, 5))
        if key in seen:
            continue
        seen.add(key)
        nome = (
            tags.get("name")
            or tags.get("operator")
            or tags.get("ref")
            or f"OSM {el.get('type')}/{el.get('id')}"
        )
        tipo = tags.get("waterway") or tags.get("man_made") or tags.get("pipeline") or "captacao"
        mun = tags.get("addr:city") or tags.get("is_in:city") or ""
        cod = nome_por_ibge.get(mun, "")
        out.append(
            {
                "municipio": mun,
                "codigo_ibge": cod,
                "tipo_captacao": tipo,
                "nome_sistema": nome,
                "latitude": f"{la:.6f}",
                "longitude": f"{lo:.6f}",
                "fonte": "OSM",
                "observacao": "Fallback espacial — substituir por export Sisagua oficial quando disponível",
            }
        )
    return out


def main() -> None:
    comum.preparar_diretorios()
    print("Coletando captações (Sisagua aberto → OSM)…", flush=True)
    regs = tentar_sisagua_aberto()
    fonte_principal = "SISAGUA"
    if not regs:
        regs = captacoes_osm()
        fonte_principal = "OSM"
    if not regs:
        # Mantém esqueleto utilizável
        regs = [
            {
                "municipio": "Cuiabá",
                "codigo_ibge": "5103403",
                "tipo_captacao": "superficial",
                "nome_sistema": "A preencher — Sisagua/OSM indisponíveis nesta execução",
                "latitude": "",
                "longitude": "",
                "fonte": "SISAGUA",
                "observacao": "Scaffold — reexecute etapa 38 com rede",
            }
        ]
        fonte_principal = "esqueleto"

    comum.salvar_csv(SAIDA, regs, CAMPOS)
    n_coord = sum(1 for r in regs if r.get("latitude") and r.get("longitude"))
    REL.write_text(
        "\n".join(
            [
                "# Captações no eixo Manso–Cuiabá",
                "",
                f"- Registros: **{len(regs)}** ({n_coord} com coordenada)",
                f"- Fonte principal desta execução: **{fonte_principal}**",
                f"- Arquivo: `{SAIDA.relative_to(comum.RAIZ)}`",
                "",
                "KPI C4 na Simulação: contagem de pontos com lat/lon dentro da mancha proxy.",
                "Preferência: planilha oficial Sisagua/Vigiagua SES; OSM é proxy espacial.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"  gravado {REL.relative_to(comum.RAIZ)}")
    print(f"  {len(regs)} registros · fonte={fonte_principal}")


if __name__ == "__main__":
    main()
