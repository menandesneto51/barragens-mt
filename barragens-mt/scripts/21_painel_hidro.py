"""Gera o painel hidrometeorológico municipal (Tela 2 leve).

Choropleth da chuva 24h/72h e saturação do solo a partir de
`hidro_municipios_mt.csv` (SisClima/TITAN), sobre a malha IBGE.
"""

from __future__ import annotations

import csv
import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import comum

SAIDA = comum.RAIZ / "painel"


def _carregar_07():
    caminho = Path(__file__).resolve().parent / "07_painel.py"
    spec = importlib.util.spec_from_file_location("painel_inv", caminho)
    if spec is None or spec.loader is None:
        raise SystemExit("07_painel.py ausente")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["painel_inv"] = mod
    spec.loader.exec_module(mod)
    return mod


def ler_hidro_munis() -> list[dict[str, Any]]:
    caminho = comum.DADOS_TRATADOS / "hidro_municipios_mt.csv"
    if not caminho.exists():
        raise SystemExit("hidro_municipios_mt.csv ausente — rode a etapa 17")
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def num(valor: Any) -> float | None:
    if valor in (None, ""):
        return None
    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return None


MODELO = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hidro municipal — VIGIBARRAGENS–MT</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root{--ink:#15202b;--muted:#5a6b7a;--paper:#e9eef2;--card:#fff;--line:#d0d8e0;--accent:#0b6e4f}
*{box-sizing:border-box}
body{margin:0;font-family:"Source Sans 3",system-ui,sans-serif;color:var(--ink);
background:radial-gradient(ellipse at 80% 0%,#d4e0eb,transparent 40%),var(--paper)}
header{padding:20px 24px 12px;border-bottom:1px solid var(--line);background:rgba(255,255,255,.85);
display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:flex-end}
.marca{font-family:"Fraunces",Georgia,serif;font-size:1.7rem;font-weight:600;margin:0 0 4px}
header p{margin:0;color:var(--muted);max-width:34rem;line-height:1.4;font-size:14px}
nav a{color:var(--accent);font-weight:600;font-size:13px;margin-left:10px;text-decoration:none}
main{padding:14px 24px 40px;max-width:1400px;margin:0 auto}
.ctrl{display:flex;flex-wrap:wrap;gap:10px;align-items:end;margin-bottom:12px;
background:var(--card);border:1px solid var(--line);padding:12px}
label{font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;display:block;margin-bottom:4px}
select{padding:7px 8px;border:1px solid var(--line);font:inherit}
#mapa{height:620px;border:1px solid var(--line);background:#fff}
.legenda{margin-top:8px;font-size:12px;color:var(--muted)}
.legenda span{display:inline-block;width:28px;height:12px;margin:0 4px 0 10px;vertical-align:middle}
.nota{margin-top:12px;font-size:12.5px;color:var(--muted);line-height:1.5;max-width:48rem}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin-bottom:12px}
.kpi{background:var(--card);border:1px solid var(--line);padding:10px}
.kpi .n{font-size:20px;font-weight:700}.kpi .r{font-size:11px;color:var(--muted)}
</style>
</head>
<body>
<header>
  <div>
    <h1 class="marca">Pressão hidroclimática</h1>
    <p>Choropleth municipal — SisClima/TITAN · gerado __GERADO__ · ref. __DATA_REF__</p>
  </div>
  <nav>
    <a href="index.html">Comando</a>
    <a href="piloto_manso_cuiaba.html">Piloto</a>
  </nav>
</header>
<main>
  <div class="kpis" id="kpis"></div>
  <div class="ctrl">
    <div><label>Camada</label>
      <select id="camada">
        <option value="c24">Chuva 24 h (mm)</option>
        <option value="c72" selected>Chuva 72 h (mm)</option>
        <option value="sat">Saturação do solo (0–1)</option>
        <option value="dias">Dias consecutivos chuva intensa</option>
      </select>
    </div>
  </div>
  <div id="mapa"></div>
  <div class="legenda" id="legenda"></div>
  <p class="nota">
    Valores municipais do contrato SisClima/TITAN (não pixel IMERG). Agregação por barragem
    usa o máximo sede+montante (etapa 17). Estações pontuais INMET/Cemaden/ANA continuam
    no SIS — este painel não recoleta APIs.
  </p>
</main>
<script>
const HIDRO = __HIDRO__;
const MALHA = __MALHA__;
const porIbge = Object.fromEntries(HIDRO.map(h => [String(h.ibge), h]));

const kpis = document.getElementById('kpis');
const comChuva = HIDRO.filter(h => (h.c72||0) > 0).length;
const max72 = Math.max(0, ...HIDRO.map(h => h.c72||0));
const comSolo = HIDRO.filter(h => h.sat != null).length;
[['Municípios', HIDRO.length],['Com chuva 72h > 0', comChuva],
 ['Máx. 72h (mm)', max72.toFixed(1)],['Com saturação', comSolo]
].forEach(([r,n]) => {
  const d=document.createElement('div'); d.className='kpi';
  d.innerHTML=`<div class="n">${n}</div><div class="r">${r}</div>`;
  kpis.appendChild(d);
});

const mapa = L.map('mapa').setView([-13.0,-55.8],6);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{
  attribution:'&copy; OSM', maxZoom:11
}).addTo(mapa);

function escala(campo, v) {
  if (v == null) return '#dfe4ea';
  if (campo === 'sat') {
    if (v < 0.3) return '#c7e9c0';
    if (v < 0.5) return '#74c476';
    if (v < 0.7) return '#fdae6b';
    return '#e6550d';
  }
  if (campo === 'dias') {
    if (v <= 0) return '#dfe4ea';
    if (v === 1) return '#fdae6b';
    if (v === 2) return '#e6550d';
    return '#a63603';
  }
  // chuva mm
  if (v <= 0) return '#dfe4ea';
  if (v < 5) return '#c6dbef';
  if (v < 20) return '#6baed6';
  if (v < 50) return '#2171b5';
  return '#08306b';
}

let camadaGeo = null;
function desenhar() {
  const campo = document.getElementById('camada').value;
  if (camadaGeo) mapa.removeLayer(camadaGeo);
  camadaGeo = L.geoJSON(MALHA, {
    style: f => {
      const cod = String((f.properties||{}).codarea||'');
      const h = porIbge[cod];
      const v = h ? h[campo] : null;
      return {color:'#6a7a88', weight:0.7, fillColor:escala(campo,v), fillOpacity:0.72};
    },
    onEachFeature: (f, layer) => {
      const cod = String((f.properties||{}).codarea||'');
      const h = porIbge[cod];
      if (!h) { layer.bindPopup('Sem hidro SisClima'); return; }
      layer.bindPopup(`<b>${h.nome||cod}</b><br>
        Chuva 24h: ${h.c24??'—'} mm<br>Chuva 72h: ${h.c72??'—'} mm<br>
        Saturação: ${h.sat??'—'}<br>Dias adversos: ${h.dias??'—'}<br>
        Nível hidro: ${h.nh||'—'}<br><small>${h.data||''}</small>`);
    }
  }).addTo(mapa);

  const LGD = {
    c24: '0 · &lt;5 · &lt;20 · &lt;50 · ≥50 mm',
    c72: '0 · &lt;5 · &lt;20 · &lt;50 · ≥50 mm',
    sat: '&lt;0,3 · &lt;0,5 · &lt;0,7 · ≥0,7',
    dias: '0 · 1 · 2 · ≥3 dias ≥20 mm'
  };
  document.getElementById('legenda').innerHTML =
    'Escala: ' + (LGD[campo]||'') +
    ' <span style="background:#dfe4ea"></span><span style="background:#c6dbef"></span>'+
    '<span style="background:#6baed6"></span><span style="background:#2171b5"></span>'+
    '<span style="background:#08306b"></span>';
}
document.getElementById('camada').onchange = desenhar;
desenhar();
</script>
</body>
</html>
"""


def main() -> None:
    painel07 = _carregar_07()
    munis = ler_hidro_munis()
    import csv as _csv

    nomes_ibge: dict[str, str] = {}
    ibge_csv = comum.DADOS_TRATADOS / "ibge_municipios_mt.csv"
    if ibge_csv.exists():
        with ibge_csv.open(encoding="utf-8-sig", newline="") as f_ib:
            for row in _csv.DictReader(f_ib, delimiter=";"):
                cod = str(row.get("codigo_ibge") or "").strip().replace(".0", "")
                mun = (row.get("municipio") or "").strip()
                if cod and mun:
                    nomes_ibge[cod] = mun
    compactos = []
    for r in munis:
        cod = str(r.get("codigo_ibge") or "").strip().replace(".0", "")
        nome = (r.get("municipio") or "").strip() or nomes_ibge.get(cod, "")
        compactos.append(
            {
                "ibge": cod,
                "nome": nome,
                "data": r.get("data_referencia") or "",
                "c24": num(r.get("chuva_24h_mm")),
                "c72": num(r.get("chuva_72h_mm")),
                "sat": num(r.get("saturacao_antecedente")),
                "dias": num(r.get("dias_consecutivos_chuva_intensa")),
                "nh": r.get("nivel_alerta_hidro") or "",
            }
        )
    data_ref = next((c["data"] for c in compactos if c["data"]), "—")

    malha = json.loads(
        (comum.DADOS_TRATADOS / "ibge_malha_municipios_mt_simplificada.geojson").read_text(
            encoding="utf-8"
        )
    )
    # Manter codarea nas propriedades
    simplificada = {"type": "FeatureCollection", "features": []}
    for feicao in malha.get("features", []):
        limpa = painel07.simplificar_malha(
            {"type": "FeatureCollection", "features": [feicao]}
        )
        if not limpa["features"]:
            continue
        props = {"codarea": (feicao.get("properties") or {}).get("codarea")}
        limpa["features"][0]["properties"] = props
        simplificada["features"].append(limpa["features"][0])

    html = (
        MODELO.replace("__HIDRO__", json.dumps(compactos, ensure_ascii=False, separators=(",", ":")))
        .replace("__MALHA__", json.dumps(simplificada, ensure_ascii=False, separators=(",", ":")))
        .replace("__GERADO__", dt.datetime.now().strftime("%d/%m/%Y %H:%M"))
        .replace("__DATA_REF__", data_ref)
    )
    SAIDA.mkdir(parents=True, exist_ok=True)
    destino = SAIDA / "hidro.html"
    destino.write_text(html, encoding="utf-8")
    print(f"Hidro municipal — {len(compactos)} municípios")
    print(f"  gravado {destino.relative_to(comum.RAIZ)} ({destino.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
