"""Sedes municipais (centroide da malha) + população IBGE — proxy de isolamento."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from st_app.data import TRATADOS, carregar_populacao

MALHA = TRATADOS / "ibge_malha_municipios_mt_simplificada.geojson"
INTERESSE = TRATADOS / "cuiaba_municipios_de_interesse.json"


def _centroide_coords(geometria: dict[str, Any]) -> tuple[float, float] | None:
    """Média dos vértices (lon, lat) — suficiente para snap OSM."""
    tipo = geometria.get("type")
    coords = geometria.get("coordinates")
    if not coords:
        return None
    pts: list[tuple[float, float]] = []

    def descer(no: Any) -> None:
        if (
            isinstance(no, (list, tuple))
            and len(no) >= 2
            and all(isinstance(v, (int, float)) for v in no[:2])
        ):
            pts.append((float(no[0]), float(no[1])))
            return
        if isinstance(no, (list, tuple)):
            for f in no:
                descer(f)

    if tipo == "Point":
        return float(coords[0]), float(coords[1])
    descer(coords)
    if not pts:
        return None
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


@lru_cache(maxsize=1)
def _codigos_eixo() -> frozenset[str]:
    if not INTERESSE.exists():
        return frozenset()
    try:
        data = json.loads(INTERESSE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return frozenset()
    return frozenset(
        str(m.get("codigo_ibge") or "")
        for m in (data.get("municipios") or [])
        if m.get("codigo_ibge")
    )


@lru_cache(maxsize=1)
def carregar_sedes_com_populacao() -> tuple[dict[str, Any], ...]:
    """Lista imutável de sedes: codigo_ibge, municipio, la, lo, populacao, no_eixo."""
    pop = carregar_populacao()
    pop_map: dict[str, tuple[str, int]] = {}
    if not pop.empty:
        for row in pop.itertuples():
            cod = str(getattr(row, "codigo_ibge", "") or "").strip()
            if not cod:
                continue
            nome = str(getattr(row, "municipio", "") or "").strip()
            try:
                n = int(float(getattr(row, "populacao", 0) or 0))
            except (TypeError, ValueError):
                n = 0
            pop_map[cod] = (nome, n)

    if not MALHA.exists():
        return tuple()
    try:
        geo = json.loads(MALHA.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return tuple()

    eixo = _codigos_eixo()
    out: list[dict[str, Any]] = []
    for feicao in geo.get("features") or []:
        props = feicao.get("properties") or {}
        cod = str(props.get("codarea") or "").strip()
        if not cod:
            continue
        c = _centroide_coords(feicao.get("geometry") or {})
        if c is None:
            continue
        lon, lat = c
        nome, n = pop_map.get(cod, ("", 0))
        if not nome:
            nome = cod
        out.append(
            {
                "codigo_ibge": cod,
                "municipio": nome,
                "la": round(lat, 5),
                "lo": round(lon, 5),
                "populacao": n,
                "no_eixo": 1 if cod in eixo else 0,
            }
        )
    return tuple(out)


def sedes_candidatas(
    *,
    municipios_afetados: list[str] | None = None,
    so_eixo: bool = False,
    lat: float | None = None,
    lon: float | None = None,
    raio_km: float | None = None,
) -> list[dict[str, Any]]:
    """Sedes para isolamento: próximas da barragem e/ou listadas como afetadas.

    Por padrão (so_eixo=False) serve a qualquer barragem do estado: inclui
    municípios no raio de busca OSM e os nominados em municipios_afetados.
    """
    from st_app.trajeto_hidraulico import haversine_km

    todas = [dict(s) for s in carregar_sedes_com_populacao()]
    if not todas:
        return []
    nomes = {(m or "").strip().casefold() for m in (municipios_afetados or []) if m}
    raio = float(raio_km) if raio_km and raio_km > 0 else None
    out: list[dict[str, Any]] = []
    for s in todas:
        nome_ok = bool(nomes and s["municipio"].casefold() in nomes)
        eixo_ok = bool(s.get("no_eixo"))
        perto = False
        if lat is not None and lon is not None and raio is not None:
            perto = haversine_km(lat, lon, float(s["la"]), float(s["lo"])) <= raio
        if so_eixo:
            if eixo_ok or nome_ok:
                out.append(s)
            continue
        if perto or nome_ok or (eixo_ok and raio is None):
            out.append(s)
    if not out and so_eixo:
        out = [s for s in todas if s.get("no_eixo")]
    if not out and lat is not None and lon is not None:
        # fallback: 8 sedes mais próximas
        ranked = sorted(
            todas,
            key=lambda s: haversine_km(lat, lon, float(s["la"]), float(s["lo"])),
        )
        out = ranked[:8]
    return out
