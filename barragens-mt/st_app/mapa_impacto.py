"""Mapa interativo de impacto extraterritorial (sede → municípios a jusante).

Usa Otto/IDAP já calculados — não é mancha PAE nem hidrodinâmica de ruptura.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import folium
import pandas as pd
from branca.element import MacroElement, Template

from st_app.data import CORES_NIVEL, TRATADOS, carregar_idap

MALHA_PATH = TRATADOS / "ibge_malha_municipios_mt_simplificada.geojson"
IBGE_MUN = TRATADOS / "ibge_municipios_mt.csv"
POP_MUN = TRATADOS / "ibge_populacao_municipios_mt.csv"

# Pressão = nº de barragens a montante cujo Otto aponta para o município.
_CORES_PRESSAO = [
    (0, "#e8eef7"),
    (1, "#c5d4f0"),
    (5, "#7ea0d4"),
    (20, "#3d5fa8"),
    (50, "#1b3281"),
    (100, "#9a3412"),
]


def _num(v: Any) -> float | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip().replace(",", ".")
    if not s or s.lower() in ("nan", "none"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _norm_nome(s: Any) -> str:
    return " ".join(str(s or "").strip().split())


@lru_cache(maxsize=1)
def _catalogo_ibge() -> pd.DataFrame:
    if not IBGE_MUN.is_file():
        return pd.DataFrame()
    df = pd.read_csv(IBGE_MUN, sep=";", dtype=str)
    df["codigo_ibge"] = df["codigo_ibge"].astype(str).str.replace(".0", "", regex=False)
    df["municipio"] = df["municipio"].map(_norm_nome)
    if POP_MUN.is_file():
        pop = pd.read_csv(POP_MUN, sep=";", dtype=str)
        pop["codigo_ibge"] = pop["codigo_ibge"].astype(str).str.replace(".0", "", regex=False)
        pop["populacao"] = pd.to_numeric(
            pop.get("populacao", pd.Series(dtype=str)).astype(str).str.replace(",", "."),
            errors="coerce",
        )
        df = df.merge(pop[["codigo_ibge", "populacao"]], on="codigo_ibge", how="left")
    return df


@lru_cache(maxsize=1)
def _malha_com_nomes() -> dict[str, Any]:
    """GeoJSON com properties: codarea, municipio, lat, lon (centróide aproximado)."""
    if not MALHA_PATH.is_file():
        return {"type": "FeatureCollection", "features": []}
    geo = json.loads(MALHA_PATH.read_text(encoding="utf-8"))
    cat = _catalogo_ibge()
    nome_por_cod = {
        str(r["codigo_ibge"]): str(r["municipio"])
        for _, r in cat.iterrows()
        if r.get("codigo_ibge")
    }
    features = []
    for feat in geo.get("features") or []:
        props = dict(feat.get("properties") or {})
        cod = str(props.get("codarea") or "").strip()
        nome = nome_por_cod.get(cod, "")
        geom = feat.get("geometry") or {}
        lat_c, lon_c = _centroid_geom(geom)
        props.update(
            {
                "codarea": cod,
                "municipio": nome,
                "lat": lat_c,
                "lon": lon_c,
            }
        )
        features.append({"type": "Feature", "properties": props, "geometry": geom})
    return {"type": "FeatureCollection", "features": features}


def _centroid_geom(geom: dict[str, Any]) -> tuple[float | None, float | None]:
    coords: list[tuple[float, float]] = []

    def walk(obj: Any) -> None:
        if not isinstance(obj, (list, tuple)) or not obj:
            return
        if isinstance(obj[0], (int, float)) and len(obj) >= 2:
            coords.append((float(obj[1]), float(obj[0])))  # lat, lon
            return
        for item in obj:
            walk(item)

    walk(geom.get("coordinates"))
    if not coords:
        return None, None
    lat = sum(c[0] for c in coords) / len(coords)
    lon = sum(c[1] for c in coords) / len(coords)
    return lat, lon


def centroides_municipios() -> dict[str, tuple[float, float]]:
    """Nome do município → (lat, lon) do centróide da malha IBGE."""
    out: dict[str, tuple[float, float]] = {}
    for feat in (_malha_com_nomes().get("features") or []):
        p = feat.get("properties") or {}
        nome = _norm_nome(p.get("municipio"))
        la, lo = p.get("lat"), p.get("lon")
        if nome and la is not None and lo is not None:
            out[nome] = (float(la), float(lo))
    return out


def agregar_pressao_destino(impacto: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por município potencialmente afetado."""
    if impacto.empty:
        return pd.DataFrame()
    df = impacto.copy()
    df["municipio_potencialmente_afetado"] = df["municipio_potencialmente_afetado"].map(
        _norm_nome
    )
    df["idap_n"] = pd.to_numeric(df.get("idap"), errors="coerce")
    df["atencao"] = df.get("nivel", pd.Series(dtype=str)).isin(
        ["Amarelo", "Laranja", "Vermelho", "Roxo"]
    )
    g = (
        df.groupby("municipio_potencialmente_afetado", dropna=False)
        .agg(
            n_barragens_montante=("id_snisb", "nunique"),
            n_pares=("id_snisb", "size"),
            n_atencao=("atencao", "sum"),
            idap_max=("idap_n", "max"),
            niveis=("nivel", lambda s: ", ".join(sorted({str(x) for x in s if x}))),
        )
        .reset_index()
        .rename(columns={"municipio_potencialmente_afetado": "municipio"})
    )
    cat = _catalogo_ibge()
    if not cat.empty:
        g = g.merge(
            cat[["municipio", "codigo_ibge", "populacao"]],
            on="municipio",
            how="left",
        )
    return g.sort_values(
        ["n_atencao", "n_barragens_montante", "idap_max"],
        ascending=False,
    ).reset_index(drop=True)


def _cor_pressao(n: int) -> str:
    cor = _CORES_PRESSAO[0][1]
    for limiar, c in _CORES_PRESSAO:
        if n >= limiar:
            cor = c
    return cor


def _fmt(v: Any, suf: str = "") -> str:
    n = _num(v)
    if n is None:
        return "—"
    if abs(n - int(n)) < 1e-9:
        return f"{int(n)}{suf}"
    return f"{n:.1f}{suf}".replace(".", ",")


class _Legend(MacroElement):
    def __init__(self, html: str) -> None:
        super().__init__()
        self._template = Template(
            """
            {% macro html(this, kwargs) %}
            <div style="position:fixed;bottom:24px;left:24px;z-index:9999;
              background:rgba(255,255,255,.94);border:1px solid #c5d0e0;
              padding:10px 12px;font:12px/1.45 system-ui,sans-serif;
              max-width:240px;box-shadow:0 2px 8px rgba(0,0,0,.12)">
            """
            + html
            + """
            </div>
            {% endmacro %}
            """
        )


def montar_mapa_impacto(
    impacto: pd.DataFrame,
    *,
    municipio_destino: str | None = None,
    id_snisb: str | None = None,
    so_atencao: bool = False,
    max_ligacoes: int = 180,
) -> tuple[folium.Map | None, dict[str, Any]]:
    """Mapa coroplético + ligações sede→destino filtráveis."""
    meta: dict[str, Any] = {
        "n_ligacoes": 0,
        "n_destinos": 0,
        "n_origens": 0,
        "pressao": pd.DataFrame(),
    }
    if impacto.empty:
        return None, meta

    view = impacto.copy()
    view["municipio_potencialmente_afetado"] = view[
        "municipio_potencialmente_afetado"
    ].map(_norm_nome)
    view["municipio_sede"] = view["municipio_sede"].map(_norm_nome)
    if so_atencao and "nivel" in view.columns:
        view = view[view["nivel"].isin(["Amarelo", "Laranja", "Vermelho", "Roxo"])]
    if municipio_destino:
        view = view[view["municipio_potencialmente_afetado"] == _norm_nome(municipio_destino)]
    if id_snisb:
        view = view[view["id_snisb"].astype(str) == str(id_snisb)]

    pressao = agregar_pressao_destino(view)
    meta["pressao"] = pressao
    meta["n_destinos"] = int(pressao["municipio"].nunique()) if not pressao.empty else 0

    idap = carregar_idap()
    coords_bar: dict[str, tuple[float, float]] = {}
    info_bar: dict[str, dict[str, Any]] = {}
    if not idap.empty and "latitude" in idap.columns:
        for _, r in idap.dropna(subset=["latitude", "longitude"]).iterrows():
            bid = str(r.get("id_snisb") or "")
            la, lo = _num(r.get("latitude")), _num(r.get("longitude"))
            if not bid or la is None or lo is None:
                continue
            coords_bar[bid] = (la, lo)
            info_bar[bid] = {
                "nome": r.get("nome") or r.get("nome_barragem") or "",
                "cri": r.get("categoria_risco") or "—",
                "dpa": r.get("dano_potencial_associado") or "—",
                "vol": r.get("capacidade_hm3"),
                "uso": r.get("uso_principal") or "—",
                "nivel": r.get("nivel") or "—",
                "idap": r.get("idap"),
                "n_af": r.get("n_municipios_afetados"),
            }

    centros = centroides_municipios()
    # Fallback: média das barragens do município-sede
    if not idap.empty and "latitude" in idap.columns:
        g = (
            idap.dropna(subset=["latitude", "longitude"])
            .assign(_sede=idap["municipio_sede"].fillna("").map(_norm_nome))
            .groupby("_sede")
            .agg(latitude=("latitude", "mean"), longitude=("longitude", "mean"))
        )
        for i, row in g.iterrows():
            if i and i not in centros:
                centros[str(i)] = (float(row.latitude), float(row.longitude))

    pressao_por_nome = {
        _norm_nome(r["municipio"]): r
        for _, r in pressao.iterrows()
        if r.get("municipio")
    }

    m = folium.Map(location=[-13.2, -55.8], zoom_start=5, tiles="CartoDB positron")
    folium.TileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Satélite",
        overlay=False,
        control=True,
        show=False,
    ).add_to(m)

    grp_mun = folium.FeatureGroup(name="Municípios sob pressão (jusante)", show=True)
    malha = _malha_com_nomes()
    for feat in malha.get("features") or []:
        p = feat.get("properties") or {}
        nome = _norm_nome(p.get("municipio"))
        pr = pressao_por_nome.get(nome)
        n = int(pr["n_barragens_montante"]) if pr is not None else 0
        if n <= 0 and not (municipio_destino and nome == _norm_nome(municipio_destino)):
            # Contorno leve do estado (só destinos sob pressão no recorte)
            continue
        fill = _cor_pressao(n)
        destaque = municipio_destino and nome == _norm_nome(municipio_destino)
        pop_txt = _fmt(pr["populacao"]) if pr is not None else "—"
        html = (
            f"<b>{nome}</b><br>"
            f"Barragens a montante (Otto): <b>{n}</b><br>"
            f"Em atenção+: {_fmt(pr['n_atencao']) if pr is not None else '—'}<br>"
            f"IDAP máx. montante: {_fmt(pr['idap_max']) if pr is not None else '—'}<br>"
            f"População (IBGE): {pop_txt}<br>"
            f"<small>Proxy de exposição territorial — não é mancha PAE.</small>"
        )
        folium.GeoJson(
            feat,
            style_function=lambda _f, fill=fill, destaque=destaque: {
                "fillColor": fill,
                "color": "#9a3412" if destaque else "#1b3281",
                "weight": 3 if destaque else 1,
                "fillOpacity": 0.72 if n else 0.15,
                "opacity": 0.9,
            },
            tooltip=folium.Tooltip(f"{nome}: {n} barragem(ns) a montante"),
            popup=folium.Popup(html, max_width=320),
        ).add_to(grp_mun)
    grp_mun.add_to(m)

    grp_lig = folium.FeatureGroup(name="Ligações sede → afetado", show=True)
    grp_bar = folium.FeatureGroup(name="Barragens de origem", show=True)
    destinos_marcados: set[str] = set()
    amostra = view.head(max_ligacoes)
    for _, r in amostra.iterrows():
        bid = str(r.get("id_snisb") or "")
        dest = _norm_nome(r.get("municipio_potencialmente_afetado"))
        origem = coords_bar.get(bid)
        destino = centros.get(dest)
        if not origem or not destino:
            continue
        cor = CORES_NIVEL.get(str(r.get("nivel") or ""), "#1b3281")
        extra = info_bar.get(bid, {})
        html = (
            f"<b>{r.get('nome_barragem') or extra.get('nome') or 'Barragem'}</b><br>"
            f"SNISB {bid}<br>"
            f"<b>{r.get('municipio_sede')}</b> → <b>{dest}</b><br>"
            f"Nível {r.get('nivel') or '—'} · IDAP {r.get('idap') or '—'}<br>"
            f"CRI/DPA: {extra.get('cri')} / {extra.get('dpa')}<br>"
            f"Uso: {extra.get('uso')}<br>"
            f"Volume {_fmt(extra.get('vol'), ' hm³')}<br>"
            f"Municípios Otto: {extra.get('n_af') or '—'}<br>"
            f"<small>Rota esquemática (não é trajeto da onda).</small>"
        )
        popup = folium.Popup(html, max_width=340)
        folium.PolyLine(
            [origem, destino],
            color=cor,
            weight=2.2 if not id_snisb else 3.5,
            opacity=0.55 if not id_snisb else 0.85,
            popup=popup,
            tooltip=f"{r.get('nome_barragem')}: {r.get('municipio_sede')} → {dest}",
        ).add_to(grp_lig)
        folium.CircleMarker(
            origem,
            radius=6 if id_snisb else 5,
            color="#111",
            weight=1,
            fill=True,
            fill_color=cor,
            fill_opacity=0.95,
            popup=popup,
            tooltip=str(r.get("nome_barragem") or bid),
        ).add_to(grp_bar)
        if dest not in destinos_marcados:
            destinos_marcados.add(dest)
            folium.CircleMarker(
                destino,
                radius=7,
                color="#1b3281",
                weight=2,
                fill=True,
                fill_color="#fff",
                fill_opacity=0.95,
                popup=folium.Popup(
                    f"<b>{dest}</b><br>Município potencialmente afetado a jusante",
                    max_width=260,
                ),
                tooltip=dest,
            ).add_to(grp_lig)
        meta["n_ligacoes"] += 1

    meta["n_origens"] = len({str(x) for x in amostra["id_snisb"].tolist() if x})
    grp_lig.add_to(m)
    grp_bar.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    legenda_html = (
        "<b>Pressão a jusante</b><br>"
        "Nº de barragens a montante (Otto)<br>"
        '<span style="display:inline-block;width:12px;height:12px;background:#c5d4f0;border:1px solid #888"></span> 1–4<br>'
        '<span style="display:inline-block;width:12px;height:12px;background:#7ea0d4;border:1px solid #888"></span> 5–19<br>'
        '<span style="display:inline-block;width:12px;height:12px;background:#3d5fa8;border:1px solid #888"></span> 20–49<br>'
        '<span style="display:inline-block;width:12px;height:12px;background:#1b3281;border:1px solid #888"></span> 50–99<br>'
        '<span style="display:inline-block;width:12px;height:12px;background:#9a3412;border:1px solid #888"></span> ≥100<br>'
        "<small>Linhas = ligação sede→afetado (esquemática).</small>"
    )
    m.get_root().add_child(_Legend(legenda_html))

    # Enquadrar
    pts: list[list[float]] = []
    for feat in malha.get("features") or []:
        p = feat.get("properties") or {}
        nome = _norm_nome(p.get("municipio"))
        if nome in pressao_por_nome and p.get("lat") is not None:
            pts.append([float(p["lat"]), float(p["lon"])])
    for bid in amostra["id_snisb"].astype(str):
        if bid in coords_bar:
            pts.append(list(coords_bar[bid]))
    if len(pts) >= 2:
        lats = [p[0] for p in pts]
        lons = [p[1] for p in pts]
        m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(28, 28))
    elif len(pts) == 1:
        m.location = pts[0]
        m.zoom_start = 8

    return m, meta
