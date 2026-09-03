"""Escolas no eixo Manso–Cuiabá (INEP Censo Escolar + OSM espacial).

Os microdados recentes do Censo Escolar (2023/2024) **não publicam**
latitude/longitude (LGPD). Por isso:

1. Baixa INEP e gera contagem municipal de escolas em atividade no eixo.
2. Usa OpenStreetMap (`amenity=school|kindergarten|college`) para a camada
   espacial da Simulação (KPI C5 na mancha).

Saídas:
  dados/tratados/escolas_eixo_cuiaba.csv              — pontos (OSM)
  dados/tratados/escolas_inep_contagem_municipio.csv  — contagem INEP
  relatorios/escolas_eixo_cuiaba.md

Uso:
  python scripts/40_escolas_inep_eixo.py
  python executar.py 40
"""

from __future__ import annotations

import csv
import io
import json
import ssl
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import comum

# Cadeia TLS do download.inep.gov.br costuma falhar com CA do sistema.
_SSL_CTX = ssl._create_unverified_context()

SAIDA = comum.DADOS_TRATADOS / "escolas_eixo_cuiaba.csv"
SAIDA_CONTAGEM = comum.DADOS_TRATADOS / "escolas_inep_contagem_municipio.csv"
REL = comum.RELATORIOS / "escolas_eixo_cuiaba.md"
BRUTOS = comum.DADOS_BRUTOS / "inep_escolas"
INTERESSE = comum.DADOS_TRATADOS / "cuiaba_municipios_de_interesse.json"
EIXO_GEO = comum.DADOS_TRATADOS / "eixo_hidrografico_manso_cuiaba.geojson"

URLS_INEP = (
    "https://download.inep.gov.br/dados_abertos/microdados_censo_escolar_2024.zip",
    "https://download.inep.gov.br/dados_abertos/microdados_censo_escolar_2023.zip",
)

OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
)

UA = "VIGIBARRAGENS-MT/1.0 (SES-MT; escolas eixo Manso-Cuiaba)"

CAMPOS = [
    "codigo_inep",
    "nome",
    "municipio",
    "codigo_ibge",
    "dependencia",
    "localizacao",
    "situacao",
    "latitude",
    "longitude",
    "fonte",
    "observacao",
]

DEP_MAP = {
    "1": "federal",
    "2": "estadual",
    "3": "municipal",
    "4": "privada",
}
LOC_MAP = {"1": "urbana", "2": "rural"}
SIT_MAP = {
    "1": "em_atividade",
    "2": "paralisada",
    "3": "extinta",
    "4": "extinta_ano",
}


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


def _ibge6(cod: str) -> str:
    d = "".join(ch for ch in str(cod) if ch.isdigit())
    return d[:6] if len(d) >= 6 else d


def bbox_eixo() -> tuple[float, float, float, float]:
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
                pad = 0.12
                return (
                    min(lats) - pad,
                    min(lons) - pad,
                    max(lats) + pad,
                    max(lons) + pad,
                )
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    return (-16.15, -56.55, -15.20, -55.55)


def _num(v: Any) -> float | None:
    if v is None:
        return None
    s = str(v).strip().replace(",", ".")
    if not s or s.lower() in {"nan", "none", "null"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _baixar_por_faixas(url: str, destino: Path, *, bloco: int = 512_000) -> bool:
    """Download por Range — o host INEP derruba conexões longas sem faixas."""
    # Descobre tamanho
    req0 = urllib.request.Request(
        url, headers={"User-Agent": UA, "Range": "bytes=0-0"}, method="GET"
    )
    try:
        with urllib.request.urlopen(req0, timeout=60, context=_SSL_CTX) as resp:
            cr = resp.headers.get("Content-Range") or ""
            total = int(cr.split("/")[-1]) if "/" in cr else int(
                resp.headers.get("Content-Length") or 0
            )
            resp.read()
    except Exception as exc:  # noqa: BLE001
        print(f"  não foi possível obter tamanho: {exc}")
        return False
    if total <= 0:
        return False

    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("wb") as out:
        inicio = 0
        while inicio < total:
            fim = min(inicio + bloco - 1, total - 1)
            req = urllib.request.Request(
                url,
                headers={"User-Agent": UA, "Range": f"bytes={inicio}-{fim}"},
            )
            ok = False
            for tentativa in range(1, 5):
                try:
                    with urllib.request.urlopen(req, timeout=120, context=_SSL_CTX) as resp:
                        chunk = resp.read()
                    if not chunk:
                        raise RuntimeError("faixa vazia")
                    out.write(chunk)
                    ok = True
                    break
                except Exception as exc:  # noqa: BLE001
                    print(f"  faixa {inicio}-{fim} tentativa {tentativa}: {exc}")
                    time.sleep(1.5 * tentativa)
            if not ok:
                return False
            inicio = fim + 1
            if inicio % (bloco * 20) < bloco:
                print(f"  … {inicio // 1_000_000}/{total // 1_000_000} MB", flush=True)
    return destino.stat().st_size >= max(1_000_000, int(total * 0.98))


def garantir_zip_inep() -> Path | None:
    BRUTOS.mkdir(parents=True, exist_ok=True)
    for url in URLS_INEP:
        nome = url.rstrip("/").split("/")[-1]
        destino = BRUTOS / nome
        if destino.exists() and destino.stat().st_size > 1_000_000:
            print(f"  reusando {destino.name}")
            return destino
        print(f"  baixando {nome} (faixas)…", flush=True)
        if _baixar_por_faixas(url, destino):
            print(
                f"  gravado {destino.relative_to(comum.RAIZ)} "
                f"({destino.stat().st_size // 1_000_000} MB)"
            )
            return destino
        print(f"  falha download por faixas: {nome}")
        destino.unlink(missing_ok=True)
    return None


def _pick_csv_member(names: list[str]) -> str | None:
    prefer = [
        n
        for n in names
        if n.lower().endswith(".csv")
        and ("escola" in n.lower() or "ed_basica" in n.lower() or "microdados" in n.lower())
    ]
    if prefer:
        # Prefer smaller escolas-only if present
        escolas = [n for n in prefer if "escola" in n.lower() and "matricula" not in n.lower()]
        return sorted(escolas or prefer, key=len)[0]
    csvs = [n for n in names if n.lower().endswith(".csv")]
    return csvs[0] if csvs else None


def processar_inep() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Retorna (pontos com lat/lon, contagem municipal)."""
    zpath = garantir_zip_inep()
    if zpath is None:
        return [], []
    munis = municipios_eixo()
    if not munis:
        return [], []
    ibge6 = {_ibge6(c): c for c in munis}
    pontos: list[dict[str, Any]] = []
    contagem: dict[str, dict[str, Any]] = {
        c: {
            "municipio": n,
            "codigo_ibge": c,
            "n_escolas_atividade": 0,
            "n_escolas_total": 0,
            "n_federal": 0,
            "n_estadual": 0,
            "n_municipal": 0,
            "n_privada": 0,
            "fonte": "INEP",
            "arquivo": zpath.name,
        }
        for c, n in munis.items()
    }
    seen: set[str] = set()

    with zipfile.ZipFile(zpath) as zf:
        member = _pick_csv_member(zf.namelist())
        if not member:
            print("  zip INEP sem CSV utilizável")
            return [], []
        print(f"  lendo {member}", flush=True)
        with zf.open(member) as raw:
            sample = raw.read(4096)
            raw.seek(0)
            enc = "utf-8-sig"
            try:
                sample.decode("utf-8-sig")
            except UnicodeDecodeError:
                enc = "latin-1"
            text = io.TextIOWrapper(raw, encoding=enc, errors="replace", newline="")
            head = text.readline()
            delim = "|" if head.count("|") >= head.count(";") else ";"
            text.seek(0)
            reader = csv.DictReader(text, delimiter=delim)
            for row in reader:
                uf = (row.get("SG_UF") or row.get("sg_uf") or "").strip().upper()
                if uf and uf != "MT":
                    continue
                cod_mun = _ibge6(
                    row.get("CO_MUNICIPIO")
                    or row.get("CO_MUNICIPIO_IBGE")
                    or row.get("co_municipio")
                    or ""
                )
                cod7 = ibge6.get(cod_mun)
                if not cod7:
                    continue
                codigo = str(
                    row.get("CO_ENTIDADE")
                    or row.get("CO_ESCOLA")
                    or row.get("co_entidade")
                    or ""
                ).strip()
                if codigo and codigo in seen:
                    continue
                if codigo:
                    seen.add(codigo)
                sit = str(
                    row.get("TP_SITUACAO_FUNCIONAMENTO")
                    or row.get("tp_situacao_funcionamento")
                    or ""
                ).strip()
                dep = str(
                    row.get("TP_DEPENDENCIA") or row.get("tp_dependencia") or ""
                ).strip()
                loc = str(
                    row.get("TP_LOCALIZACAO") or row.get("tp_localizacao") or ""
                ).strip()
                ativa = sit in {"", "1"} or SIT_MAP.get(sit) == "em_atividade"
                slot = contagem[cod7]
                slot["n_escolas_total"] += 1
                if ativa:
                    slot["n_escolas_atividade"] += 1
                    dep_nome = DEP_MAP.get(dep, "")
                    if dep_nome == "federal":
                        slot["n_federal"] += 1
                    elif dep_nome == "estadual":
                        slot["n_estadual"] += 1
                    elif dep_nome == "municipal":
                        slot["n_municipal"] += 1
                    elif dep_nome == "privada":
                        slot["n_privada"] += 1

                la = _num(
                    row.get("NU_LATITUDE")
                    or row.get("LATITUDE")
                    or row.get("nu_latitude")
                    or row.get("DS_LATITUDE")
                )
                lo = _num(
                    row.get("NU_LONGITUDE")
                    or row.get("LONGITUDE")
                    or row.get("nu_longitude")
                    or row.get("DS_LONGITUDE")
                )
                if la is None or lo is None or not ativa:
                    continue
                if not (-18.5 <= la <= -7.0 and -62.0 <= lo <= -50.0):
                    continue
                nome = (
                    row.get("NO_ENTIDADE")
                    or row.get("NO_ESCOLA")
                    or row.get("no_entidade")
                    or f"Escola {codigo or 'INEP'}"
                )
                pontos.append(
                    {
                        "codigo_inep": codigo,
                        "nome": str(nome).strip(),
                        "municipio": munis[cod7],
                        "codigo_ibge": cod7,
                        "dependencia": DEP_MAP.get(dep, dep or ""),
                        "localizacao": LOC_MAP.get(loc, loc or ""),
                        "situacao": SIT_MAP.get(sit, sit or "em_atividade"),
                        "latitude": f"{la:.6f}",
                        "longitude": f"{lo:.6f}",
                        "fonte": "INEP",
                        "observacao": f"Censo Escolar · arquivo {zpath.name}",
                    }
                )
    cont_rows = list(contagem.values())
    print(
        f"  INEP: {sum(r['n_escolas_atividade'] for r in cont_rows)} escolas "
        f"em atividade no eixo; {len(pontos)} com coordenada"
    )
    return pontos, cont_rows


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


def escolas_osm() -> list[dict[str, Any]]:
    south, west, north, east = bbox_eixo()
    q = f"""
[out:json][timeout:70];
(
  node["amenity"~"^(school|kindergarten|college)$"]({south},{west},{north},{east});
  way["amenity"~"^(school|kindergarten|college)$"]({south},{west},{north},{east});
);
out center tags;
""".strip()
    print(f"  OSM escolas bbox {south:.3f},{west:.3f},{north:.3f},{east:.3f}", flush=True)
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
        amenity = tags.get("amenity") or "school"
        nome = tags.get("name") or tags.get("official_name") or f"OSM {amenity}"
        mun = tags.get("addr:city") or tags.get("is_in:city") or ""
        out.append(
            {
                "codigo_inep": str(tags.get("ref:inep") or tags.get("inep:code") or ""),
                "nome": nome,
                "municipio": mun,
                "codigo_ibge": nome_por_ibge.get(mun, ""),
                "dependencia": tags.get("operator:type") or "",
                "localizacao": "",
                "situacao": "em_atividade",
                "latitude": f"{la:.6f}",
                "longitude": f"{lo:.6f}",
                "fonte": "OSM",
                "observacao": "Fallback espacial — preferir microdados INEP quando o download estiver disponível",
            }
        )
    print(f"  OSM: {len(out)} escolas/creches no bbox")
    return out


def main() -> None:
    comum.preparar_diretorios()
    print("Coletando escolas (INEP contagem + OSM espacial)…", flush=True)
    pontos_inep, contagem = processar_inep()
    if contagem:
        comum.salvar_csv(
            SAIDA_CONTAGEM,
            contagem,
            [
                "municipio",
                "codigo_ibge",
                "n_escolas_atividade",
                "n_escolas_total",
                "n_federal",
                "n_estadual",
                "n_municipal",
                "n_privada",
                "fonte",
                "arquivo",
            ],
        )

    if pontos_inep:
        regs = pontos_inep
        fonte = "INEP"
    else:
        print("  INEP sem coordenadas — usando OSM para a mancha", flush=True)
        regs = escolas_osm()
        fonte = "OSM"
    if not regs:
        raise SystemExit("nenhuma escola espacial coletada")

    comum.salvar_csv(SAIDA, regs, CAMPOS)
    n_ativ_inep = sum(int(r.get("n_escolas_atividade") or 0) for r in contagem)
    REL.write_text(
        "\n".join(
            [
                "# Escolas no eixo Manso–Cuiabá",
                "",
                f"- Pontos espaciais: **{len(regs)}** (`{fonte}`)",
                f"- Contagem INEP (atividade no eixo): **{n_ativ_inep}**",
                f"- Arquivo espacial: `{SAIDA.relative_to(comum.RAIZ)}`",
                f"- Arquivo contagem: `{SAIDA_CONTAGEM.relative_to(comum.RAIZ)}`",
                f"- Microdados: `{URLS_INEP[0]}`",
                "",
                "Os microdados 2023/2024 não trazem lat/lon (LGPD). A Simulação usa OSM",
                "para o KPI C5 na mancha; a contagem INEP municipal fica como referência.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"  gravado {REL.relative_to(comum.RAIZ)}")
    print(f"  {len(regs)} pontos · fonte={fonte} · INEP atividade={n_ativ_inep}")


if __name__ == "__main__":
    main()
