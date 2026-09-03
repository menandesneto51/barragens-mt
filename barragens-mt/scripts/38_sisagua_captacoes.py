"""Captações de água Sisagua (aberto) + fallback OSM no eixo.

1. Baixa o cadastro oficial de pontos de captação (Dados Abertos SUS / S3).
2. Grava **MT estadual** (municípios com barragem) e o recorte do **eixo** Manso–Cuiabá.
3. Se o zip oficial falhar, usa OpenStreetMap (intake / water_works) no bbox do eixo.

Saídas:
  dados/tratados/sisagua_captacoes_mt.csv
  dados/tratados/sisagua_captacoes_eixo.csv
  relatorios/sisagua_captacoes_eixo.md

Uso:
  python scripts/38_sisagua_captacoes.py
  python executar.py 38
"""

from __future__ import annotations

import csv
import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import comum

SAIDA_EIXO = comum.DADOS_TRATADOS / "sisagua_captacoes_eixo.csv"
SAIDA_MT = comum.DADOS_TRATADOS / "sisagua_captacoes_mt.csv"
# Alias legado (mesmo arquivo do eixo).
SAIDA = SAIDA_EIXO
REL = comum.RELATORIOS / "sisagua_captacoes_eixo.md"
BRUTOS = comum.DADOS_BRUTOS / "sisagua"
INTERESSE = comum.DADOS_TRATADOS / "cuiaba_municipios_de_interesse.json"
INV = comum.DADOS_TRATADOS / "inventario_barragens_mt.csv"
IBGE_MUN = comum.DADOS_TRATADOS / "ibge_municipios_mt.csv"
EIXO_GEO = comum.DADOS_TRATADOS / "eixo_hidrografico_manso_cuiaba.geojson"

ZIP_OFICIAL = BRUTOS / "cadastro_pontos_captacao_csv.zip"
URL_CSV_ZIP = (
    "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SISAGUA/"
    "cadastro_pontos_captacao_csv.zip"
)

OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
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


def municipios_com_barragem() -> dict[str, str]:
    """IBGE7 → nome para municípios sede de barragem no inventário."""
    if not INV.exists():
        return {}
    out: dict[str, str] = {}
    with INV.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            mun = (r.get("municipio") or "").strip()
            cod = (r.get("codigo_ibge") or "").strip()
            if mun and cod:
                out[cod] = mun
    return out


def _ibge6(cod: str) -> str:
    d = "".join(ch for ch in str(cod) if ch.isdigit())
    if len(d) >= 6:
        return d[:6]
    return d


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
    return (-16.15, -56.55, -15.20, -55.55)


def garantir_zip_oficial() -> Path | None:
    BRUTOS.mkdir(parents=True, exist_ok=True)
    if ZIP_OFICIAL.exists() and ZIP_OFICIAL.stat().st_size > 1_000_000:
        print(f"  reusando {ZIP_OFICIAL.name} ({ZIP_OFICIAL.stat().st_size // 1_000_000} MB)")
        return ZIP_OFICIAL
    print(f"  baixando cadastro oficial Sisagua…", flush=True)
    try:
        req = urllib.request.Request(URL_CSV_ZIP, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=180) as resp, ZIP_OFICIAL.open("wb") as out:
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                out.write(chunk)
        print(f"  gravado {ZIP_OFICIAL.relative_to(comum.RAIZ)}")
        return ZIP_OFICIAL
    except Exception as exc:  # noqa: BLE001
        print(f"  falha download Sisagua oficial: {exc}")
        if ZIP_OFICIAL.exists():
            ZIP_OFICIAL.unlink(missing_ok=True)
        return None


def captacoes_sisagua_oficial(munis: dict[str, str], *, rotulo: str = "filtro") -> list[dict[str, Any]]:
    """Lê o CSV nacional em streaming e filtra pelos municípios informados."""
    zpath = garantir_zip_oficial()
    if zpath is None:
        return []

    if not munis:
        print(f"  aviso: municípios ({rotulo}) ausentes")
        return []
    ibge6_para_7 = {_ibge6(c): c for c in munis}
    nomes = {n.casefold(): c for c, n in munis.items()}

    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    n_lidos = 0

    with zipfile.ZipFile(zpath) as zf:
        nomes_zip = zf.namelist()
        csv_nome = next((n for n in nomes_zip if n.lower().endswith(".csv")), None)
        if not csv_nome:
            print("  zip sem CSV")
            return []
        with zf.open(csv_nome) as raw:
            # Arquivo nacional vem em Latin-1/CP1252 (não UTF-8).
            text = io.TextIOWrapper(raw, encoding="latin-1", newline="")
            reader = csv.DictReader(text, delimiter=";")
            for row in reader:
                n_lidos += 1
                uf = (row.get("SG_UF") or "").strip().upper()
                if uf and uf != "MT":
                    continue
                cod6 = _ibge6(row.get("CO_MUNICIPIO_IBGE") or "")
                mun_nome = (row.get("NO_MUNICIPIO") or "").strip()
                cod7 = ibge6_para_7.get(cod6) or nomes.get(mun_nome.casefold())
                if not cod7:
                    continue
                lat_s = (row.get("NU_LATITUDE") or "").strip().replace(",", ".")
                lon_s = (row.get("NU_LONGITUDE") or "").strip().replace(",", ".")
                try:
                    la, lo = float(lat_s), float(lon_s)
                except ValueError:
                    continue
                if not (-18.5 <= la <= -7.0 and -62.0 <= lo <= -50.0):
                    continue
                tipo = (row.get("TP_CAPTACAO") or "").strip().lower() or "nao_informado"
                nome = (
                    (row.get("NO_PONTO_CAPTACAO") or "").strip()
                    or (row.get("NO_ETA") or "").strip()
                    or (row.get("NO_SOLUCAO_ABASTECIMENTO") or "").strip()
                    or (row.get("NO_MANANCIAL") or "").strip()
                    or "Captação Sisagua"
                )
                ano = (row.get("NU_ANO") or "").strip()
                key = (cod7, f"{la:.5f}", f"{lo:.5f}")
                if key in seen:
                    continue
                seen.add(key)
                out.append(
                    {
                        "municipio": munis[cod7],
                        "codigo_ibge": cod7,
                        "tipo_captacao": tipo,
                        "nome_sistema": nome,
                        "latitude": f"{la:.6f}",
                        "longitude": f"{lo:.6f}",
                        "fonte": "SISAGUA",
                        "observacao": (
                            f"cadastro pontos de captação Dados Abertos SUS"
                            + (f" · ano {ano}" if ano else "")
                        ),
                    }
                )
                if n_lidos % 200_000 == 0:
                    print(f"  … lidos {n_lidos:,} · {rotulo} {len(out)}", flush=True)

    print(f"  Sisagua oficial: {len(out)} pontos ({rotulo}) de {n_lidos:,} linhas")
    return out


def _post_overpass(q: str) -> dict[str, Any] | None:
    data = urllib.parse.urlencode({"data": q}).encode()
    for url in OVERPASS_URLS:
        try:
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    "User-Agent": UA,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
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
        tipo = tags.get("waterway") or tags.get("man_made") or "captacao"
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
                "observacao": "Fallback espacial — preferir cadastro Sisagua oficial",
            }
        )
    return out


def main() -> None:
    comum.preparar_diretorios()
    print("Coletando captações (Sisagua oficial → OSM)…", flush=True)
    mun_eixo = municipios_eixo()
    mun_mt = municipios_com_barragem()
    print(f"  municípios eixo: {len(mun_eixo)} · com barragem (MT): {len(mun_mt)}")

    regs_mt = captacoes_sisagua_oficial(mun_mt, rotulo="MT sedes")
    fonte_principal = "SISAGUA"
    if regs_mt:
        comum.salvar_csv(SAIDA_MT, regs_mt, CAMPOS)
        print(f"  gravado {SAIDA_MT.relative_to(comum.RAIZ)} ({len(regs_mt)})")
    else:
        print("  aviso: Sisagua estadual vazio — mantendo só eixo/OSM")

    # Eixo: subset do estadual quando possível; senão releitura / OSM.
    if regs_mt and mun_eixo:
        cods_eixo = set(mun_eixo)
        nomes_eixo = {n.casefold() for n in mun_eixo.values()}
        regs = [
            r
            for r in regs_mt
            if r.get("codigo_ibge") in cods_eixo
            or (r.get("municipio") or "").casefold() in nomes_eixo
        ]
    else:
        regs = captacoes_sisagua_oficial(mun_eixo, rotulo="eixo") if mun_eixo else []

    if not regs:
        regs = captacoes_osm()
        fonte_principal = "OSM"
    if not regs:
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

    comum.salvar_csv(SAIDA_EIXO, regs, CAMPOS)
    n_coord = sum(1 for r in regs if r.get("latitude") and r.get("longitude"))
    n_mt = len(regs_mt)
    REL.write_text(
        "\n".join(
            [
                "# Captações Sisagua — eixo e estadual",
                "",
                f"- Eixo Manso–Cuiabá: **{len(regs)}** ({n_coord} com coordenada)",
                f"- MT (sedes com barragem): **{n_mt}**",
                f"- Fonte principal desta execução: **{fonte_principal}**",
                f"- Arquivos: `{SAIDA_EIXO.relative_to(comum.RAIZ)}`, "
                f"`{SAIDA_MT.relative_to(comum.RAIZ)}`",
                f"- Origem oficial: `{URL_CSV_ZIP}`",
                "",
                "KPI C4 na Simulação (eixo): contagem na mancha proxy.",
                "Proxies IDAP (etapa 49) usam o estadual quando disponível.",
                "OSM só entra se o cadastro Sisagua falhar no eixo.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"  gravado {REL.relative_to(comum.RAIZ)}")
    print(f"  eixo {len(regs)} · MT {n_mt} · fonte={fonte_principal}")


if __name__ == "__main__":
    main()
