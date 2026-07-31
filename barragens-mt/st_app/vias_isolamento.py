"""Vias e pontes no buffer da simulação — proxy de isolamento rodoviário (C7).

Usa OpenStreetMap via Overpass. Não é análise oficial de PAE/dam break:
trechos cuja geometria cruza o círculo equivalente são marcados como
interrompidos; US fora da mancha que perdem caminho até um hub de referência
são marcadas como potencialmente isoladas.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

# Hub sanitário de referência no eixo (Cuiabá / Hospital Geral).
HUB_REF = {"la": -15.5989, "lo": -56.0949, "nome": "Cuiabá (hub ref.)"}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))

OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
)

# Estruturantes + pontes; evita malha residencial densa (Overpass lento).
HIGHWAY_REGEX = "motorway|trunk|primary|secondary|tertiary"

CACHE_DIR = (
    Path(__file__).resolve().parents[1] / "dados" / "tratados" / "cache_osm_vias"
)


def _bucket_raio(raio_km: float) -> float:
    """Arredonda o raio de busca para reaproveitar cache entre sliders próximos."""
    passo = 5.0 if raio_km >= 15 else 2.0
    return max(passo, round(raio_km / passo) * passo)


def _cache_path(lat: float, lon: float, raio_busca_km: float) -> Path:
    chave = f"{lat:.3f}_{lon:.3f}_{raio_busca_km:.1f}"
    digest = hashlib.sha1(chave.encode()).hexdigest()[:12]
    return CACHE_DIR / f"osm_{chave}_{digest}.json"


def _overpass_query(lat: float, lon: float, raio_m: int) -> str:
    return f"""
[out:json][timeout:45];
(
  way["highway"~"^({HIGHWAY_REGEX})$"](around:{raio_m},{lat},{lon});
  way["bridge"~"yes|viaduct|aqueduct"]["highway"](around:{raio_m},{lat},{lon});
);
(._;>;);
out body;
""".strip()


def buscar_malha_osm(
    lat: float,
    lon: float,
    raio_busca_km: float,
    *,
    forcar: bool = False,
) -> dict[str, Any]:
    """Baixa (ou lê do cache) ways+nodes OSM ao redor do ponto."""
    raio_busca_km = _bucket_raio(max(5.0, min(float(raio_busca_km), 45.0)))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(lat, lon, raio_busca_km)
    if path.exists() and not forcar:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass

    q = _overpass_query(lat, lon, int(raio_busca_km * 1000))
    body = urllib.parse.urlencode({"data": q}).encode("utf-8")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "User-Agent": "VIGIBARRAGENS-MT/1.0 (simulacao-isolamento; SES-MT)",
    }
    data: bytes | None = None
    ultimo_erro = ""
    for url in OVERPASS_URLS:
        try:
            req = urllib.request.Request(
                url,
                data=body,
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=55) as resp:
                data = resp.read()
            break
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            ultimo_erro = str(exc)
            time.sleep(0.8)
    if data is None:
        return {"elements": [], "erro": ultimo_erro or "overpass indisponível"}

    try:
        payload = json.loads(data.decode("utf-8"))
    except json.JSONDecodeError as exc:
        return {"elements": [], "erro": f"JSON inválido: {exc}"}

    payload["_meta"] = {
        "lat": lat,
        "lon": lon,
        "raio_busca_km": raio_busca_km,
        "baixado_em": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    try:
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return payload


def _dist_ponto_segmento_km(
    lat: float,
    lon: float,
    a_lat: float,
    a_lon: float,
    b_lat: float,
    b_lon: float,
) -> float:
    """Distância aproximada ponto–segmento em km (plano local equiretangular)."""
    # metros por grau no centro do segmento
    mid_lat = (a_lat + b_lat) / 2.0
    m_lat = 111_320.0
    m_lon = 111_320.0 * max(0.2, math.cos(math.radians(mid_lat)))
    ax = (a_lon - lon) * m_lon
    ay = (a_lat - lat) * m_lat
    bx = (b_lon - lon) * m_lon
    by = (b_lat - lat) * m_lat
    # vetor A→B e projeção de origem (ponto) sobre AB, com A e B relativos ao ponto
    # reancorar: A e B absolutos no plano com origem no ponto P=0
    abx, aby = bx - ax, by - ay
    # vetor P→A = (ax, ay) se P é origem... wait: we set coords relative to P already
    # A = (ax,ay), B = (bx,by), P = (0,0)
    apx, apy = -ax, -ay  # P - A
    ab2 = abx * abx + aby * aby
    if ab2 <= 1e-6:
        return math.hypot(ax, ay) / 1000.0
    t = max(0.0, min(1.0, (apx * abx + apy * aby) / ab2))
    cx = ax + t * abx
    cy = ay + t * aby
    return math.hypot(cx, cy) / 1000.0


def _comprimento_km(coords: list[tuple[float, float]]) -> float:
    total = 0.0
    for i in range(1, len(coords)):
        total += haversine_km(coords[i - 1][0], coords[i - 1][1], coords[i][0], coords[i][1])
    return total


def _segmento_no_buffer(
    coords: list[tuple[float, float]],
    lat0: float,
    lon0: float,
    raio_km: float,
) -> bool:
    if not coords:
        return False
    for la, lo in coords:
        if haversine_km(lat0, lon0, la, lo) <= raio_km:
            return True
    for i in range(1, len(coords)):
        a_la, a_lo = coords[i - 1]
        b_la, b_lo = coords[i]
        if _dist_ponto_segmento_km(lat0, lon0, a_la, a_lo, b_la, b_lo) <= raio_km:
            return True
    return False


def analisar_isolamento(
    *,
    lat: float,
    lon: float,
    raio_km: float,
    cnes: list[dict[str, Any]] | None = None,
    hub: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Retorna vias/pontes no buffer e US potencialmente isoladas (proxy)."""
    raio_km = float(raio_km)
    if raio_km <= 0 or math.isnan(raio_km):
        return _vazio("raio inválido")

    # Malha um pouco além do buffer para testar conectividade.
    raio_busca = min(45.0, max(10.0, raio_km * 1.35 + 6.0))
    bruto = buscar_malha_osm(lat, lon, raio_busca)
    if bruto.get("erro") and not bruto.get("elements"):
        return _vazio(str(bruto.get("erro")))

    nodes: dict[int, tuple[float, float]] = {}
    ways: list[dict[str, Any]] = []
    for el in bruto.get("elements") or []:
        if el.get("type") == "node" and "lat" in el and "lon" in el:
            nodes[int(el["id"])] = (float(el["lat"]), float(el["lon"]))
        elif el.get("type") == "way":
            ways.append(el)

    vias_mapa: list[dict[str, Any]] = []
    pontes_mapa: list[dict[str, Any]] = []
    km_interrompidos = 0.0
    n_vias_cortadas = 0
    n_pontes = 0
    n_arteriais = 0

    # Grafo: nó OSM id → vizinhos (só arestas NÃO interrompidas para o corte)
    viz_cheio: dict[int, set[int]] = defaultdict(set)
    viz_corte: dict[int, set[int]] = defaultdict(set)
    # Arestas interrompidas para desenho fino
    arestas_cut: list[tuple[int, int]] = []

    for way in ways:
        tags = way.get("tags") or {}
        highway = str(tags.get("highway") or "")
        bridge = str(tags.get("bridge") or "").lower()
        eh_ponte = bridge in {"yes", "viaduct", "aqueduct"}
        if highway == "proposed":
            continue
        nds = [int(n) for n in (way.get("nodes") or []) if int(n) in nodes]
        if len(nds) < 2:
            continue
        coords = [nodes[n] for n in nds]
        no_buf = _segmento_no_buffer(coords, lat, lon, raio_km)
        comp = _comprimento_km(coords)
        nome = (tags.get("name") or tags.get("ref") or highway or "via").strip()
        arterial = highway in {"motorway", "trunk", "primary", "secondary"}

        # Classifica arestas consecutivas
        way_cut = False
        for i in range(1, len(nds)):
            a, b = nds[i - 1], nds[i]
            a_la, a_lo = nodes[a]
            b_la, b_lo = nodes[b]
            corta = _dist_ponto_segmento_km(lat, lon, a_la, a_lo, b_la, b_lo) <= raio_km
            viz_cheio[a].add(b)
            viz_cheio[b].add(a)
            if corta:
                way_cut = True
                arestas_cut.append((a, b))
            else:
                viz_corte[a].add(b)
                viz_corte[b].add(a)

        if no_buf or way_cut:
            n_vias_cortadas += 1
            km_interrompidos += comp
            if arterial:
                n_arteriais += 1
            vias_mapa.append(
                {
                    "coords": [[la, lo] for la, lo in coords],
                    "nome": nome,
                    "hw": highway,
                    "ponte": 1 if eh_ponte else 0,
                    "cut": 1,
                    "art": 1 if arterial else 0,
                }
            )
            if eh_ponte:
                n_pontes += 1
                mid = coords[len(coords) // 2]
                pontes_mapa.append(
                    {
                        "la": mid[0],
                        "lo": mid[1],
                        "nome": nome,
                        "hw": highway,
                    }
                )
        elif arterial:
            vias_mapa.append(
                {
                    "coords": [[la, lo] for la, lo in coords],
                    "nome": nome,
                    "hw": highway,
                    "ponte": 1 if eh_ponte else 0,
                    "cut": 0,
                    "art": 1,
                }
            )

    hub = hub or HUB_REF
    hub_la, hub_lo = float(hub["la"]), float(hub["lo"])
    # Anexa hub ao nó OSM mais próximo
    if not nodes:
        return {
            "ok": True,
            "fonte": "OpenStreetMap/Overpass",
            "raio_km": raio_km,
            "raio_busca_km": raio_busca,
            "n_vias_interrompidas": 0,
            "n_pontes_comprometidas": 0,
            "n_arteriais_cortadas": 0,
            "km_vias_no_buffer": 0.0,
            "n_us_isoladas": 0,
            "nivel_c7_proxy": 0,
            "rotulo_c7": "Sem malha OSM na área",
            "vias": [],
            "pontes": [],
            "us_isoladas": [],
            "hub": hub,
            "aviso": "Nenhuma via estruturante retornada pelo Overpass.",
        }

    # Grade ~0.01° (~1 km) para snap O(1) aproximado.
    grade: dict[tuple[int, int], list[int]] = defaultdict(list)
    for nid, (nla, nlo) in nodes.items():
        grade[(int(nla * 100), int(nlo * 100))].append(nid)

    def _snap(la: float, lo: float) -> int:
        ci, cj = int(la * 100), int(lo * 100)
        candidatos: list[int] = []
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                candidatos.extend(grade.get((ci + di, cj + dj), ()))
        if not candidatos:
            candidatos = list(nodes.keys())
        melhor = candidatos[0]
        dmin = 1e18
        for nid in candidatos:
            nla, nlo = nodes[nid]
            d = (nla - la) ** 2 + (nlo - lo) ** 2
            if d < dmin:
                dmin = d
                melhor = nid
        return melhor

    hub_node = _snap(hub_la, hub_lo)

    def _alcancaveis(grafo: dict[int, set[int]], origem: int) -> set[int]:
        vistos = {origem}
        fila: deque[int] = deque([origem])
        while fila:
            u = fila.popleft()
            for v in grafo.get(u, ()):
                if v not in vistos:
                    vistos.add(v)
                    fila.append(v)
        return vistos

    reach_cheio = _alcancaveis(viz_cheio, hub_node)
    reach_corte = _alcancaveis(viz_corte, hub_node)

    us_isoladas: list[dict[str, Any]] = []
    cnes = cnes or []
    # Anel: fora da mancha, mas ainda na zona de busca
    for p in cnes:
        try:
            pla, plo = float(p["la"]), float(p["lo"])
        except (KeyError, TypeError, ValueError):
            continue
        d = haversine_km(lat, lon, pla, plo)
        if d <= raio_km:
            continue  # inundada / no buffer — não conta como isolada
        if d > raio_busca:
            continue
        # Só prioriza US assistenciais para o KPI de isolamento
        if not (p.get("h") or p.get("upa") or p.get("ubs") or p.get("prio")):
            continue
        nodo = _snap(pla, plo)
        if nodo in reach_cheio and nodo not in reach_corte:
            us_isoladas.append(
                {
                    "la": pla,
                    "lo": plo,
                    "no": p.get("no") or p.get("nome") or "US",
                    "mu": p.get("mu") or p.get("municipio") or "",
                    "tp": p.get("tp") or p.get("tipo") or "US",
                    "dist": round(d, 2),
                }
            )

    # Nível proxy alinhado à escala C7 (0–2)
    if n_pontes >= 1 or (n_arteriais >= 2 and len(us_isoladas) >= 1):
        nivel = 2
        rotulo = "Acesso único / isolamento potencial (proxy)"
    elif n_vias_cortadas >= 1 or n_arteriais >= 1:
        nivel = 1
        rotulo = "Rota comprometida com possível desvio (proxy)"
    else:
        nivel = 0
        rotulo = "Rotas alternativas aparentes (proxy)"

    # Limita geometrias enviadas ao browser
    vias_mapa.sort(key=lambda v: (-v["cut"], -v["art"], -v["ponte"]))
    vias_mapa = vias_mapa[:180]
    pontes_mapa = pontes_mapa[:80]
    us_isoladas = sorted(us_isoladas, key=lambda u: u["dist"])[:60]

    return {
        "ok": True,
        "fonte": "OpenStreetMap/Overpass",
        "raio_km": raio_km,
        "raio_busca_km": raio_busca,
        "n_vias_interrompidas": n_vias_cortadas,
        "n_pontes_comprometidas": n_pontes,
        "n_arteriais_cortadas": n_arteriais,
        "km_vias_no_buffer": round(km_interrompidos, 1),
        "n_us_isoladas": len(us_isoladas),
        "nivel_c7_proxy": nivel,
        "rotulo_c7": rotulo,
        "vias": vias_mapa,
        "pontes": pontes_mapa,
        "us_isoladas": us_isoladas,
        "hub": {"la": hub_la, "lo": hub_lo, "nome": hub.get("nome") or "Hub"},
        "aviso": None,
        "n_ways_osm": len(ways),
        "n_arestas_cortadas": len(arestas_cut),
    }


def _vazio(motivo: str) -> dict[str, Any]:
    return {
        "ok": False,
        "fonte": "OpenStreetMap/Overpass",
        "raio_km": 0.0,
        "raio_busca_km": 0.0,
        "n_vias_interrompidas": 0,
        "n_pontes_comprometidas": 0,
        "n_arteriais_cortadas": 0,
        "km_vias_no_buffer": 0.0,
        "n_us_isoladas": 0,
        "nivel_c7_proxy": 0,
        "rotulo_c7": "Indisponível",
        "vias": [],
        "pontes": [],
        "us_isoladas": [],
        "hub": HUB_REF,
        "aviso": motivo,
    }


def analisar_isolamento_json(
    lat: float,
    lon: float,
    raio_km: float,
    cnes_json: str,
) -> dict[str, Any]:
    """Variante com CNES serializado — adequada a st.cache_data."""
    try:
        cnes = json.loads(cnes_json) if cnes_json else []
    except json.JSONDecodeError:
        cnes = []
    return analisar_isolamento(lat=lat, lon=lon, raio_km=raio_km, cnes=cnes)
