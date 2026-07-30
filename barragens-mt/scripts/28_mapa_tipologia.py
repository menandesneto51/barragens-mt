"""Mapa estadual de barragens por tipologia de uso — painel/tipologia.html."""

from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path
from typing import Any

import comum

SAIDA = comum.RAIZ / "painel"

# Agrupamento sanitário / operacional (rótulo curto → cor SES-friendly)
TIPOS: list[tuple[str, str, tuple[str, ...]]] = [
    ("Irrigação", "#2a4aad", ("irrig",)),
    ("Rejeito / mineração", "#b91c1c", ("rejeito", "sedimento", "miner")),
    ("Hidroelétrica", "#0e7490", ("hidroel", "hidrel")),
    ("Aquicultura", "#0369a1", ("aquicult",)),
    ("Abastecimento humano", "#1b3281", ("abastec", "humano")),
    ("Dessedentação animal", "#854d0e", ("dessedent",)),
    ("Recreação / paisagismo", "#64748b", ("recrea", "paisag")),
    ("Industrial / outros", "#475569", ()),
]


def _num(v: Any) -> float | None:
    if v in (None, "", "None"):
        return None
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def classificar_uso(uso: str) -> str:
    u = (uso or "").lower()
    for rotulo, _cor, chaves in TIPOS:
        if not chaves:
            continue
        if any(c in u for c in chaves):
            return rotulo
    return "Industrial / outros"


def cor_tipo(rotulo: str) -> str:
    for r, cor, _ in TIPOS:
        if r == rotulo:
            return cor
    return "#475569"


def montar() -> tuple[list[dict[str, Any]], dict[str, int]]:
    inv = list(
        csv.DictReader(
            (comum.DADOS_TRATADOS / "inventario_barragens_mt.csv").open(
                encoding="utf-8-sig", newline=""
            ),
            delimiter=";",
        )
    )
    idap = {
        r["id_snisb"]: r
        for r in csv.DictReader(
            (comum.DADOS_TRATADOS / "idap_estadual_mt.csv").open(
                encoding="utf-8-sig", newline=""
            ),
            delimiter=";",
        )
    }
    cont: dict[str, int] = {t[0]: 0 for t in TIPOS}
    pts: list[dict[str, Any]] = []
    for r in inv:
        la, lo = _num(r.get("latitude")), _num(r.get("longitude"))
        if la is None or lo is None:
            continue
        uso = r.get("uso_principal") or ""
        tip = classificar_uso(uso)
        cont[tip] = cont.get(tip, 0) + 1
        i = idap.get(r.get("id_snisb") or "", {})
        pts.append(
            {
                "id": r.get("id_snisb") or "",
                "no": r.get("nome") or "",
                "mu": r.get("municipio") or "",
                "uso": uso[:60],
                "tip": tip,
                "og": (r.get("orgao_fiscalizador") or "")[:40],
                "nv": i.get("nivel") or "",
                "idap": int(i["idap"]) if str(i.get("idap", "")).isdigit() else None,
                "la": round(la, 5),
                "lo": round(lo, 5),
            }
        )
    return pts, cont


def main() -> None:
    pts, cont = montar()
    cores = {t[0]: t[1] for t in TIPOS}
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Barragens por tipologia — VIGIBARRAGENS–MT</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root{{--ink:#15202b;--muted:#4a5d73;--paper:#e6ecf7;--card:#fff;--line:#c5d0e0;--accent:#1b3281}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:"Source Sans 3",system-ui,sans-serif;color:var(--ink);
background:linear-gradient(180deg,#1b3281 0%,#243f9a 18%,var(--paper) 18%);font-size:14px}}
header{{padding:20px 24px 12px;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:flex-end}}
.marca{{font-family:"Fraunces",Georgia,serif;font-size:1.7rem;font-weight:600;margin:0;color:#fff}}
header p{{margin:4px 0 0;color:rgba(255,255,255,.85);max-width:40rem}}
nav a{{color:#fff;text-decoration:none;font-size:13px;font-weight:600;padding:6px 10px;
border:1px solid rgba(255,255,255,.35);background:rgba(255,255,255,.12);margin-left:6px}}
main{{padding:14px 24px 40px;max-width:1400px;margin:0 auto}}
.grade{{display:grid;grid-template-columns:280px 1fr;gap:14px}}
@media(max-width:900px){{.grade{{grid-template-columns:1fr}}}}
.painel{{background:var(--card);border:1px solid var(--line);padding:12px 14px}}
.painel h2{{font-family:"Fraunces",Georgia,serif;font-size:1.05rem;margin:0 0 10px}}
.kpi{{display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--line);font-size:13px}}
.kpi:last-child{{border-bottom:0}}
.kpi i{{display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:8px;vertical-align:middle}}
#mapa{{height:620px;border:1px solid var(--line);background:#1a2330}}
label{{display:block;font-size:12px;color:var(--muted);margin:10px 0 4px;text-transform:uppercase;letter-spacing:.04em}}
select{{width:100%;padding:8px;font:inherit;border:1px solid var(--line)}}
.nota{{font-size:12px;color:var(--muted);line-height:1.45;margin-top:10px}}
</style>
</head>
<body>
<header>
  <div>
    <p class="marca">Barragens por tipologia</p>
    <p>Uso principal do cadastro (SNISB) — visão estadual para SES-MT. Gerado {dt.datetime.now().strftime("%d/%m/%Y %H:%M")}.</p>
  </div>
  <nav>
    <a href="index.html">Comando</a>
    <a href="simulacao.html">Simulação</a>
    <a href="inventario.html">Inventário</a>
  </nav>
</header>
<main>
  <div class="grade">
    <div class="painel">
      <h2>Tipologias</h2>
      <div id="contagens"></div>
      <label>Filtrar tipologia</label>
      <select id="filtro"><option value="">Todas</option></select>
      <p class="nota">Cores por uso principal. Clique no ponto para ficha 360°. Contagens só com coordenada.</p>
    </div>
    <div id="mapa"></div>
  </div>
</main>
<script>
const DADOS = {json.dumps(pts, ensure_ascii=False, separators=(",", ":"))};
const CORES = {json.dumps(cores, ensure_ascii=False)};
const CONT = {json.dumps(cont, ensure_ascii=False)};

const contEl = document.getElementById('contagens');
const filtro = document.getElementById('filtro');
Object.entries(CONT).sort((a,b)=>b[1]-a[1]).forEach(([k,v]) => {{
  const d = document.createElement('div');
  d.className = 'kpi';
  d.innerHTML = `<span><i style="background:${{CORES[k]||'#888'}}"></i>${{k}}</span><b>${{v}}</b>`;
  contEl.appendChild(d);
  const o = document.createElement('option');
  o.value = k; o.textContent = `${{k}} (${{v}})`;
  filtro.appendChild(o);
}});

const mapa = L.map('mapa').setView([-13.0, -55.8], 6);
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
  attribution: '&copy; OSM &copy; CARTO', maxZoom: 18
}}).addTo(mapa);
const camada = L.layerGroup().addTo(mapa);

function desenhar() {{
  camada.clearLayers();
  const f = filtro.value;
  const pts = DADOS.filter(d => !f || d.tip === f);
  pts.forEach(d => {{
    L.circleMarker([d.la, d.lo], {{
      radius: 5, color: '#fff', weight: 1,
      fillColor: CORES[d.tip] || '#888', fillOpacity: 0.9
    }}).bindPopup(
      `<b>${{d.no}}</b><br>${{d.tip}}<br>${{d.uso||'—'}}<br>${{d.mu}} · ${{d.og||'—'}}` +
      (d.nv ? `<br>IDAP ${{d.idap??'—'}} (${{d.nv}})` : '') +
      `<br><a href="barragem.html?id=${{encodeURIComponent(d.id)}}">Barragem 360°</a>`
    ).addTo(camada);
  }});
}}
filtro.onchange = desenhar;
desenhar();
</script>
</body>
</html>
"""
    SAIDA.mkdir(parents=True, exist_ok=True)
    destino = SAIDA / "tipologia.html"
    destino.write_text(html, encoding="utf-8")
    print(
        f"Tipologia — {len(pts)} com coordenada · gravado {destino.relative_to(comum.RAIZ)} "
        f"({destino.stat().st_size/1024:.0f} KB)"
    )


if __name__ == "__main__":
    main()
