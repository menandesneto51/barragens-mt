"""Carrega manchas PAE/ZAS oficiais (GeoJSON ou ZIP) — gancho sem PostGIS.

Entrada (quando existir):
  dados/brutos/pae_manchas/*.geojson
  dados/brutos/pae_manchas/*.json
  dados/brutos/pae_manchas/*.zip (GeoJSON interno)

Associa `id_snisb` via propriedades do feature ou nome do arquivo
(`34145.geojson`, `pae_34145.geojson`).

Valida CRS aproximado (EPSG:4326 / lon-lat no envelope do Brasil).
Sem arquivos: documenta 0 manchas e não falha o pipeline.

Saídas:
  dados/tratados/pae_manchas_index.csv
  dados/tratados/pae_manchas_cobertura.csv (atualiza tem_mancha_zas=sim)
  dados/tratados/pae_manchas_status.json
  relatorios/pae_manchas_carregar.md

Uso:
  python scripts/58_pae_manchas_carregar.py
  python executar.py 58
"""

from __future__ import annotations

import csv
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import comum

BRUTOS = comum.DADOS_BRUTOS / "pae_manchas"
INDEX = comum.DADOS_TRATADOS / "pae_manchas_index.csv"
COBERTURA = comum.DADOS_TRATADOS / "pae_manchas_cobertura.csv"
STATUS = comum.DADOS_TRATADOS / "pae_manchas_status.json"
REL = comum.RELATORIOS / "pae_manchas_carregar.md"
COPIA = comum.DADOS_TRATADOS / "pae_manchas"

CAMPOS_IDX = [
    "id_snisb",
    "nome_arquivo",
    "caminho_geojson",
    "crs",
    "n_poligonos",
    "fonte",
    "observacao",
]

BBOX_BR = (-75.0, -35.0, -30.0, 6.0)  # lon_min, lat_min, lon_max, lat_max


def _extrair_id(nome: str, props: dict[str, Any] | None = None) -> str:
    props = props or {}
    for k in (
        "id_snisb",
        "codigo_snisb",
        "COD_SNISB",
        "cod_snisb",
        "snisb",
        "ID_SNISB",
    ):
        v = str(props.get(k) or "").strip()
        if v.isdigit():
            return v
    stem = Path(nome).stem
    m = re.search(r"(\d{3,})", stem)
    return m.group(1) if m else ""


def _coords_ok_4326(coords: Any, profundidade: int = 0) -> tuple[bool, str]:
    """Heurística: números no envelope do Brasil → EPSG:4326."""
    if profundidade > 6:
        return True, "EPSG:4326?"
    if isinstance(coords, (list, tuple)) and coords:
        if (
            len(coords) >= 2
            and isinstance(coords[0], (int, float))
            and isinstance(coords[1], (int, float))
        ):
            lon, lat = float(coords[0]), float(coords[1])
            if BBOX_BR[0] <= lon <= BBOX_BR[2] and BBOX_BR[1] <= lat <= BBOX_BR[3]:
                return True, "EPSG:4326"
            if abs(lon) > 180 or abs(lat) > 90:
                return False, "coordenadas fora de lon/lat — reprojete para EPSG:4326"
            return False, f"ponto ({lon},{lat}) fora do envelope BR — confira CRS"
        ok_all = True
        crs = "EPSG:4326"
        for c in coords[:20]:
            ok, crs = _coords_ok_4326(c, profundidade + 1)
            if not ok:
                return False, crs
        return ok_all, crs
    return True, "EPSG:4326?"


def _n_poligonos(geom: dict[str, Any] | None) -> int:
    if not geom:
        return 0
    t = geom.get("type")
    if t == "Polygon":
        return 1
    if t == "MultiPolygon":
        return len(geom.get("coordinates") or [])
    if t == "GeometryCollection":
        return sum(_n_poligonos(g) for g in (geom.get("geometries") or []))
    return 0


def _ler_geojson(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_arquivos() -> list[Path]:
    if not BRUTOS.is_dir():
        return []
    outs: list[Path] = []
    for p in sorted(BRUTOS.iterdir()):
        if p.suffix.lower() in {".geojson", ".json"}:
            outs.append(p)
        elif p.suffix.lower() == ".zip":
            outs.append(p)
    return outs


def _materializar(path: Path) -> list[tuple[Path, dict[str, Any], str]]:
    """Retorna lista (path_tratado, geojson, obs)."""
    COPIA.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".zip":
        resultados: list[tuple[Path, dict[str, Any], str]] = []
        with zipfile.ZipFile(path, "r") as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                if not info.filename.lower().endswith((".geojson", ".json")):
                    continue
                raw = zf.read(info.filename)
                dest = COPIA / f"{path.stem}__{Path(info.filename).name}"
                dest.write_bytes(raw)
                try:
                    gj = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    print(f"  ignorado {info.filename} no zip: {exc}")
                    continue
                resultados.append((dest, gj, f"extraído de {path.name}"))
        return resultados
    dest = COPIA / path.name
    dest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return [(dest, _ler_geojson(path), "cópia de brutos/pae_manchas")]


def _features(gj: dict[str, Any]) -> list[dict[str, Any]]:
    if gj.get("type") == "FeatureCollection":
        return list(gj.get("features") or [])
    if gj.get("type") == "Feature":
        return [gj]
    return [{"type": "Feature", "properties": {}, "geometry": gj}]


def main() -> int:
    comum.preparar_diretorios()
    BRUTOS.mkdir(parents=True, exist_ok=True)

    arquivos = _iter_arquivos()
    linhas: list[dict[str, str]] = []
    avisos: list[str] = []

    for path in arquivos:
        try:
            materiais = _materializar(path)
        except (OSError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
            avisos.append(f"{path.name}: {exc}")
            continue
        for dest, gj, obs in materiais:
            feats = _features(gj)
            # CRS declarado
            crs_decl = ""
            if isinstance(gj.get("crs"), dict):
                crs_decl = str((gj["crs"].get("properties") or {}).get("name") or "")
            for feat in feats:
                props = feat.get("properties") or {}
                geom = feat.get("geometry") or {}
                bid = _extrair_id(dest.name, props)
                if not bid and len(feats) == 1:
                    bid = _extrair_id(path.name, props)
                ok_crs, crs_h = _coords_ok_4326(geom.get("coordinates"))
                if crs_decl and "4326" not in crs_decl and "CRS84" not in crs_decl.upper():
                    ok_crs = False
                    crs_h = crs_decl
                if not ok_crs:
                    avisos.append(f"{dest.name} id={bid or '?'}: CRS inválido ({crs_h})")
                    continue
                npoly = _n_poligonos(geom)
                if npoly <= 0:
                    continue
                if not bid:
                    avisos.append(f"{dest.name}: feature sem id_snisb — ignorada")
                    continue
                rel = str(dest.relative_to(comum.RAIZ))
                # evita duplicar mesmo caminho+id
                if any(r["id_snisb"] == bid and r["caminho_geojson"] == rel for r in linhas):
                    continue
                linhas.append(
                    {
                        "id_snisb": bid,
                        "nome_arquivo": dest.name,
                        "caminho_geojson": rel,
                        "crs": "EPSG:4326",
                        "n_poligonos": str(npoly),
                        "fonte": "PAE/ZAS oficial (brutos/pae_manchas)",
                        "observacao": obs,
                    }
                )

    comum.salvar_csv(INDEX, linhas, CAMPOS_IDX)

    # Atualiza cobertura se existir
    n_zas = 0
    if COBERTURA.is_file():
        cob_rows: list[dict[str, str]] = []
        with COBERTURA.open(encoding="utf-8-sig", newline="") as f:
            cob_rows = list(csv.DictReader(f, delimiter=";"))
        by_id = {r["id_snisb"]: r for r in linhas}
        for r in cob_rows:
            bid = (r.get("id_snisb") or "").strip()
            if bid in by_id:
                info = by_id[bid]
                r["tem_mancha_zas"] = "sim"
                r["fonte_geometria"] = info["fonte"]
                r["caminho_geojson"] = info["caminho_geojson"]
                r["observacao"] = "Mancha PAE/ZAS ingerida pela etapa 58"
                n_zas += 1
        if cob_rows:
            campos = list(cob_rows[0].keys())
            comum.salvar_csv(COBERTURA, cob_rows, campos)
    else:
        n_zas = len({r["id_snisb"] for r in linhas})

    payload = {
        "ok": True,
        "n_arquivos_brutos": len(arquivos),
        "n_manchas_indexadas": len(linhas),
        "n_ids": len({r["id_snisb"] for r in linhas}),
        "n_cobertura_atualizada": n_zas,
        "avisos": avisos[:50],
        "pasta_brutos": str(BRUTOS.relative_to(comum.RAIZ)),
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "nota": (
            "Sem GeoJSON em dados/brutos/pae_manchas/ o índice fica vazio — "
            "estado esperado até SEMA/empreendedor entregar a mancha."
        ),
    }
    STATUS.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    REL.write_text(
        "\n".join(
            [
                "# Manchas PAE — carga (etapa 58)",
                "",
                f"- Arquivos em brutos: **{len(arquivos)}**",
                f"- Manchas indexadas: **{len(linhas)}**",
                f"- IDs SNISB distintos: **{len({r['id_snisb'] for r in linhas})}**",
                f"- Cobertura atualizada (`tem_mancha_zas=sim`): **{n_zas}**",
                "",
                "Coloque GeoJSON (EPSG:4326) ou ZIP em `dados/brutos/pae_manchas/`.",
                "Propriedade `id_snisb` no feature ou nome `NNN.geojson`.",
                "",
                f"Índice: `{INDEX.relative_to(comum.RAIZ)}`",
                "",
                *(["## Avisos", ""] + [f"- {a}" for a in avisos[:30]] if avisos else []),
            ]
        ),
        encoding="utf-8",
    )
    print(
        f"  pae_manchas: arquivos={len(arquivos)} indexadas={len(linhas)} "
        f"cobertura_sim={n_zas} avisos={len(avisos)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
