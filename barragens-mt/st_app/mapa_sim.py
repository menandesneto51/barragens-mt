"""Snippet Leaflet embutido (Streamlit components.html) para simulação animada."""

from __future__ import annotations

import json
from typing import Any


def html_mapa_simulacao(
    *,
    lat: float,
    lon: float,
    nome: str,
    volume_hm3: float,
    fracao: float,
    profundidade_m: float,
    pop_est: int | None,
    metodo_pop: str,
    cnes: list[dict[str, Any]],
    altura: int = 480,
    autoplay: bool = False,
) -> str:
    """Mapa satélite + mancha proxy + US + botões Animar/Parar (leve, sem GIF)."""
    payload = {
        "la": lat,
        "lo": lon,
        "no": nome,
        "vol": volume_hm3,
        "frac0": fracao,
        "prof": profundidade_m,
        "pop": pop_est,
        "metodo": metodo_pop,
        "cnes": cnes,
        "autoplay": autoplay,
    }
    dados = json.dumps(payload, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html,body{{margin:0;height:100%;font-family:"Source Sans 3",system-ui,sans-serif}}
  #wrap{{position:relative;height:{altura}px;width:100%}}
  #mapa{{height:100%;width:100%;background:#1a2330}}
  .ctrl{{position:absolute;z-index:1000;left:10px;top:10px;display:flex;gap:6px}}
  .ctrl button{{border:0;padding:8px 12px;font:600 13px system-ui;cursor:pointer}}
  .play{{background:#9a3412;color:#fff}}
  .stop{{background:#fff;color:#15202b;border:1px solid #d0d8e0 !important}}
  .hud{{position:absolute;z-index:1000;right:10px;top:10px;background:rgba(255,255,255,.92);
    border:1px solid #d0d8e0;padding:8px 10px;font-size:12px;line-height:1.35;max-width:200px}}
  .hud b{{font-variant-numeric:tabular-nums}}
</style>
</head><body>
<div id="wrap">
  <div class="ctrl">
    <button class="play" id="btnPlay" type="button">▶ Animar</button>
    <button class="stop" id="btnStop" type="button">Parar</button>
  </div>
  <div class="hud" id="hud">—</div>
  <div id="mapa"></div>
</div>
<script>
const S = {dados};
const mapa = L.map('mapa', {{zoomControl:true}}).setView([S.la, S.lo], 10);
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',
  {{attribution:'Esri', maxZoom:18}}).addTo(mapa);
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_only_labels/{{z}}/{{x}}/{{y}}{{r}}.png',
  {{opacity:0.85, maxZoom:18}}).addTo(mapa);
mapa.createPane('mancha'); mapa.getPane('mancha').style.zIndex=350;
mapa.getPane('mancha').style.pointerEvents='none';
mapa.createPane('us'); mapa.getPane('us').style.zIndex=450;
mapa.createPane('barragem'); mapa.getPane('barragem').style.zIndex=460;
const camadaM = L.layerGroup().addTo(mapa);
const camadaU = L.layerGroup().addTo(mapa);
const camadaB = L.layerGroup().addTo(mapa);
let timer = null;
let frac = Math.round((S.frac0||0.5)*100);

function haversine(la1,lo1,la2,lo2){{
  const R=6371, to=Math.PI/180;
  const dLat=(la2-la1)*to, dLon=(lo2-lo1)*to;
  const a=Math.sin(dLat/2)**2 + Math.cos(la1*to)*Math.cos(la2*to)*Math.sin(dLon/2)**2;
  return 2*R*Math.asin(Math.sqrt(a));
}}
function icone(p){{
  const c = p.h ? '#dc2626' : (p.upa ? '#ea580c' : '#2563eb');
  return L.divIcon({{
    className:'',
    html:`<div style="width:12px;height:12px;border-radius:50%;background:${{c}};border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.45);opacity:0;animation:fadeIn .35s forwards"></div>`,
    iconSize:[12,12], iconAnchor:[6,6]
  }});
}}
const style = document.createElement('style');
style.textContent = '@keyframes fadeIn{{to{{opacity:1}}}} @keyframes pulseRing{{0%{{opacity:.55}}50%{{opacity:.28}}100%{{opacity:.55}}}}';
document.head.appendChild(style);

function desenhar(fPct){{
  const f = fPct/100;
  const liberado = S.vol * f;
  const area = liberado / S.prof;
  const raio = Math.sqrt(area / Math.PI);
  const progress = Math.min(1, Math.max(0.15, f));
  document.getElementById('hud').innerHTML =
    `<b>${{fPct}}%</b> liberado<br>Área <b>${{area.toFixed(1)}}</b> km²<br>` +
    `Raio <b>${{raio.toFixed(2)}}</b> km<br>` +
    (S.pop!=null ? `Pop. ref. <b>${{S.pop.toLocaleString('pt-BR')}}</b><br><small>${{S.metodo||''}}</small>` : '');
  camadaM.clearLayers(); camadaU.clearLayers(); camadaB.clearLayers();
  const mancha = L.circle([S.la,S.lo], {{
    pane:'mancha', radius: raio*1000, color:'#c2410c', weight:2,
    fillColor:'#fb923c', fillOpacity: 0.22 + 0.28*progress,
    opacity: 0.7 + 0.25*progress,
    className: 'mancha-anim'
  }}).addTo(camadaM);
  try {{
    const el = mancha.getElement && mancha.getElement();
    if (el) el.style.animation = 'pulseRing 1.2s ease-in-out infinite';
  }} catch(e) {{}}
  L.circleMarker([S.la,S.lo], {{
    pane:'barragem', radius:9, color:'#fff', weight:2,
    fillColor:'#ea580c', fillOpacity:1
  }}).bindPopup(`<b>${{S.no}}</b>`).addTo(camadaB);
  const noBuf = [];
  for (const p of (S.cnes||[])) {{
    const d = haversine(S.la,S.lo,p.la,p.lo);
    if (d <= raio) noBuf.push({{...p, dist:d}});
  }}
  noBuf.sort((a,b)=> (a.pr-b.pr) || (a.dist-b.dist));
  const lim = noBuf.length <= 80 ? noBuf : noBuf.filter(p=>p.h).concat(noBuf.filter(p=>!p.h).slice(0,30));
  for (const p of lim) {{
    L.marker([p.la,p.lo], {{pane:'us', icon:icone(p), zIndexOffset: p.h?300:100}})
      .bindPopup(`<b>${{(p.tp||'US').toUpperCase()}}</b><br>${{p.no||''}}<br>${{p.dist.toFixed(1)}} km`)
      .addTo(camadaU);
  }}
  if (!timer) mapa.fitBounds(mancha.getBounds().pad(0.2), {{maxZoom:13, animate:false}});
}}

document.getElementById('btnPlay').onclick = () => {{
  if (timer) clearInterval(timer);
  frac = 5;
  desenhar(frac);
  timer = setInterval(() => {{
    frac += 5;
    if (frac > 100) {{ clearInterval(timer); timer=null; desenhar(100); return; }}
    desenhar(frac);
  }}, 160);
}};
document.getElementById('btnStop').onclick = () => {{
  if (timer) {{ clearInterval(timer); timer=null; }}
}};
desenhar(frac);
if (S.autoplay) document.getElementById('btnPlay').click();
</script>
</body></html>"""
