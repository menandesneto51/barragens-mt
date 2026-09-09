"""Cartobase compartilhada (Leaflet / Folium).

CARTO raster (`basemaps.cartocdn.com` / `CartoDB positron`) passou a exigir API key
e devolve tiles com watermark — os mapas ficavam em branco. Usamos Esri Canvas
(cinza claro) + World Imagery, sem chave, já usados na simulação.
"""

from __future__ import annotations

from typing import Any

# Esri usa ordem {z}/{y}/{x} (não z/x/y do OSM).
TILE_LIGHT = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
)
TILE_SAT = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/{z}/{y}/{x}"
)
TILE_LABELS = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
)

ATTR_ESRI = (
    "Tiles &copy; Esri — Source: Esri, TomTom, Garmin, FAO, NOAA, USGS, "
    "&copy; OpenStreetMap contributors"
)

# Snippets JS (Leaflet) — escapar {{ }} quando o HTML for f-string Python.
LEAFLET_LIGHT = (
    f"L.tileLayer('{TILE_LIGHT}', {{attribution: '{ATTR_ESRI}', maxZoom: 16}})"
)
LEAFLET_SAT = (
    f"L.tileLayer('{TILE_SAT}', {{attribution: 'Esri World Imagery', maxZoom: 18}})"
)
LEAFLET_LABELS = (
    f"L.tileLayer('{TILE_LABELS}', "
    f"{{attribution: 'Esri', maxZoom: 16, opacity: 0.9, pane: 'overlayPane'}})"
)


def mapa_folium(
    location: list[float] | tuple[float, float],
    *,
    zoom_start: int = 5,
    **kwargs: Any,
) -> Any:
    """Folium.Map com base clara Esri (substitui CartoDB positron)."""
    import folium

    m = folium.Map(
        location=list(location),
        zoom_start=zoom_start,
        tiles=None,
        **kwargs,
    )
    folium.TileLayer(
        tiles=TILE_LIGHT,
        attr=ATTR_ESRI,
        name="Base",
        control=False,
        max_zoom=16,
    ).add_to(m)
    return m
