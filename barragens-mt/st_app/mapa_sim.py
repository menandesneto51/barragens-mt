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
    vias: list[dict[str, Any]] | None = None,
    pontes: list[dict[str, Any]] | None = None,
    us_atingidas: list[dict[str, Any]] | None = None,
    us_isoladas: list[dict[str, Any]] | None = None,
    municipios_isolados: list[dict[str, Any]] | None = None,
    isolamento: dict[str, Any] | None = None,
    trajeto: dict[str, Any] | None = None,
    mostrar_circular: bool = True,
    mostrar_trajeto: bool = False,
    altura: int = 480,
    autoplay: bool = False,
) -> str:
    """Mapa: mancha + US atingidas + vias/pontes + pessoas isoladas."""
    iso = isolamento or {}
    tr = trajeto or {}
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
        "vias": vias or [],
        "pontes": pontes or [],
        "usAt": us_atingidas or iso.get("us_atingidas") or [],
        "usIso": us_isoladas or [],
        "munIso": municipios_isolados or iso.get("municipios_isolados") or [],
        "isoN": iso.get("nivel_c7_proxy"),
        "isoR": iso.get("rotulo_c7") or "",
        "isoP": iso.get("n_pontes_comprometidas"),
        "isoV": iso.get("n_vias_interrompidas"),
        "isoU": iso.get("n_us_isoladas"),
        "isoUA": iso.get("n_us_atingidas"),
        "isoPop": iso.get("pessoas_isoladas_proxy"),
        "isoMun": iso.get("n_municipios_isolados"),
        "isoG": iso.get("geom") or "",
        "trPoly": tr.get("polyline") or [],
        "trW": float(tr.get("largura_km") or 0),
        "trL": float(tr.get("comprimento_km") or 0),
        "trOk": bool(tr.get("ok")),
        "showC": bool(mostrar_circular),
        "showT": bool(mostrar_trajeto),
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
    border:1px solid #d0d8e0;padding:8px 10px;font-size:12px;line-height:1.35;max-width:230px}}
  .hud b{{font-variant-numeric:tabular-nums}}
  .leg{{position:absolute;z-index:1000;left:10px;bottom:10px;background:rgba(255,255,255,.9);
    border:1px solid #d0d8e0;padding:6px 8px;font-size:11px;line-height:1.4}}
  .leg i{{display:inline-block;width:14px;height:3px;margin-right:4px;vertical-align:middle}}
</style>
</head><body>
<div id="wrap">
  <div class="ctrl">
    <button class="play" id="btnPlay" type="button">▶ Animar</button>
    <button class="stop" id="btnStop" type="button">Parar</button>
  </div>
  <div class="hud" id="hud">—</div>
  <div class="leg">
    <div><i style="background:#dc2626"></i>Rodovia interrompida</div>
    <div><i style="background:#f59e0b"></i>Ponte atingida</div>
    <div>● US atingida (na mancha)</div>
    <div>● US isolada (sem rota)</div>
    <div>■ Sede mun. isolada (pop.)</div>
  </div>
  <div id="mapa"></div>
</div>
<script>
const S = {dados};
const mapa = L.map('mapa', {{zoomControl:true}}).setView([S.la, S.lo], 10);
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',
  {{attribution:'Esri', maxZoom:18}}).addTo(mapa);
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_only_labels/{{z}}/{{x}}/{{y}}{{r}}.png',
  {{opacity:0.85, maxZoom:18}}).addTo(mapa);
mapa.createPane('vias'); mapa.getPane('vias').style.zIndex=340;
mapa.createPane('mancha'); mapa.getPane('mancha').style.zIndex=350;
mapa.getPane('mancha').style.pointerEvents='none';
mapa.createPane('trajeto'); mapa.getPane('trajeto').style.zIndex=360;
mapa.createPane('us'); mapa.getPane('us').style.zIndex=450;
mapa.createPane('barragem'); mapa.getPane('barragem').style.zIndex=460;
const camadaV = L.layerGroup().addTo(mapa);
const camadaM = L.layerGroup().addTo(mapa);
const camadaT = L.layerGroup().addTo(mapa);
const camadaU = L.layerGroup().addTo(mapa);
const camadaB = L.layerGroup().addTo(mapa);
const camadaI = L.layerGroup().addTo(mapa);
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
function iconeIso(p){{
  return L.divIcon({{
    className:'',
    html:`<div style="width:14px;height:14px;border-radius:50%;background:#7c2d12;border:2px solid #fde68a;box-shadow:0 0 0 3px rgba(124,45,18,.35)"></div>`,
    iconSize:[14,14], iconAnchor:[7,7]
  }});
}}
function iconeAtingida(p){{
  const c = p.h ? '#b91c1c' : (p.upa ? '#c2410c' : '#1d4ed8');
  return L.divIcon({{
    className:'',
    html:`<div style="width:13px;height:13px;border-radius:50%;background:${{c}};border:2px solid #fff;box-shadow:0 0 0 2px ${{c}}"></div>`,
    iconSize:[13,13], iconAnchor:[6,6]
  }});
}}
function iconeMun(p){{
  const pop = (p.populacao||0).toLocaleString('pt-BR');
  return L.divIcon({{
    className:'',
    html:`<div style="display:flex;flex-direction:column;align-items:center">` +
      `<div style="width:12px;height:12px;background:#4c1d95;border:2px solid #e9d5ff;transform:rotate(45deg)"></div>` +
      `<span style="margin-top:3px;padding:1px 4px;background:rgba(255,255,255,.92);border:1px solid #c4b5fd;font:600 10px system-ui;color:#4c1d95;white-space:nowrap">${{pop}}</span></div>`,
    iconSize:[60,28], iconAnchor:[30,8]
  }});
}}
const style = document.createElement('style');
style.textContent = '@keyframes fadeIn{{to{{opacity:1}}}} @keyframes pulseRing{{0%{{opacity:.55}}50%{{opacity:.28}}100%{{opacity:.55}}}}';
document.head.appendChild(style);

function truncarPolyline(poly, fracLen){{
  if (!poly || poly.length < 2) return poly||[];
  if (fracLen >= 0.999) return poly;
  let total = 0;
  const segs = [];
  for (let i=1;i<poly.length;i++){{
    const d = haversine(poly[i-1][0],poly[i-1][1],poly[i][0],poly[i][1]);
    segs.push(d); total += d;
  }}
  const alvo = total * Math.max(0.05, fracLen);
  const out = [poly[0]];
  let acc = 0;
  for (let i=1;i<poly.length;i++){{
    const d = segs[i-1];
    if (acc + d <= alvo) {{ out.push(poly[i]); acc += d; }}
    else {{
      const t = (alvo - acc) / d;
      out.push([
        poly[i-1][0] + t*(poly[i][0]-poly[i-1][0]),
        poly[i-1][1] + t*(poly[i][1]-poly[i-1][1])
      ]);
      break;
    }}
  }}
  return out;
}}

function viaNoBuffer(v, raio){{
  if (!v.coords) return false;
  for (const c of v.coords) {{
    if (haversine(S.la,S.lo,c[0],c[1]) <= raio) return true;
  }}
  return !!v.cut;
}}

function desenharVias(raio){{
  camadaV.clearLayers();
  let nCut = 0, nPonte = 0;
  for (const v of (S.vias||[])) {{
    if (!v.coords || v.coords.length < 2) continue;
    // Com trajeto, confia na classificação do servidor (cut); no circular, reavalia.
    const cut = S.showT && S.isoG === 'corredor' ? !!v.cut : viaNoBuffer(v, raio);
    const ponte = !!v.ponte;
    if (cut) nCut++;
    if (cut && ponte) nPonte++;
    L.polyline(v.coords, {{
      pane:'vias',
      color: cut ? (ponte ? '#f59e0b' : '#dc2626') : '#94a3b8',
      weight: cut ? (ponte ? 5 : 3.5) : 2,
      opacity: cut ? 0.9 : 0.45,
      dashArray: cut ? null : '6 6'
    }}).bindPopup(
      `<b>${{v.nome||'Via'}}</b><br>${{v.hw||''}}` +
      (cut ? '<br><b>Interrompida na mancha (proxy)</b>' : '<br>Intacta') +
      (ponte ? '<br>Ponte/viaduto' : '')
    ).addTo(camadaV);
  }}
  for (const p of (S.pontes||[])) {{
    if (S.showC && !S.showT) {{
      const d = haversine(S.la,S.lo,p.la,p.lo);
      if (d > raio) continue;
    }}
    L.circleMarker([p.la,p.lo], {{
      pane:'vias', radius:7, color:'#78350f', weight:2,
      fillColor:'#f59e0b', fillOpacity:0.95
    }}).bindPopup(`<b>Ponte</b><br>${{p.nome||''}}<br>${{p.hw||''}}`).addTo(camadaV);
  }}
  return {{nCut, nPonte}};
}}

function desenhar(fPct){{
  const f = fPct/100;
  const liberado = S.vol * f;
  const area = liberado / S.prof;
  const raio = Math.sqrt(area / Math.PI);
  const progress = Math.min(1, Math.max(0.15, f));
  const fracLen = Math.max(0.08, f / Math.max(0.05, S.frac0||0.5));
  const fracLenClamped = Math.min(1, fracLen * (S.frac0||0.5));
  // Durante animação cresce com f; no cenário parado usa polyline completa do servidor.
  const polyAnim = (!timer) ? (S.trPoly||[]) : truncarPolyline(S.trPoly||[], f);

  const vv = desenharVias(raio);
  const nUsAt = (S.usAt||[]).length || S.isoUA || 0;
  let isoLinha = '';
  if (S.isoN!=null) {{
    isoLinha =
      `US atingidas <b>${{nUsAt}}</b> · isoladas <b>${{S.isoU??0}}</b>` +
      `<br>Vias <b>${{S.isoV??vv.nCut}}</b> · pontes <b>${{S.isoP??vv.nPonte}}</b>` +
      `<br>Pessoas isol. <b>${{(S.isoPop||0).toLocaleString('pt-BR')}}</b>` +
      ` <small>(${{S.isoMun??0}} mun.)</small>` +
      `<br><small>C7 ${{S.isoN}} · ${{S.isoG||''}}</small>`;
  }}
  let trLinha = '';
  if (S.showT && S.trOk) {{
    trLinha = `<br>Corredor ±<b>${{S.trW}}</b> km · ~<b>${{S.trL}}</b> km`;
  }}
  document.getElementById('hud').innerHTML =
    `<b>${{fPct}}%</b> liberado · área <b>${{area.toFixed(1)}}</b> km²` +
    (S.showC ? `<br>Raio circ. <b>${{raio.toFixed(2)}}</b> km` : '') +
    trLinha + '<br>' + isoLinha;

  camadaM.clearLayers(); camadaT.clearLayers();
  camadaU.clearLayers(); camadaB.clearLayers(); camadaI.clearLayers();

  let bounds = null;
  if (S.showC) {{
    const mancha = L.circle([S.la,S.lo], {{
      pane:'mancha', radius: raio*1000, color:'#c2410c', weight:2,
      fillColor:'#fb923c', fillOpacity: S.showT ? 0.10 : (0.22 + 0.28*progress),
      opacity: S.showT ? 0.55 : (0.7 + 0.25*progress),
      dashArray: S.showT ? '6 8' : null,
      className: 'mancha-anim'
    }}).addTo(camadaM);
    try {{
      const el = mancha.getElement && mancha.getElement();
      if (el && !S.showT) el.style.animation = 'pulseRing 1.2s ease-in-out infinite';
    }} catch(e) {{}}
    bounds = mancha.getBounds();
  }}

  if (S.showT && S.trOk && polyAnim.length >= 2) {{
    const wPx = Math.max(10, Math.min(28, 8 + (S.trW||2)*4));
    L.polyline(polyAnim, {{
      pane:'trajeto', color:'#67e8f9', weight:wPx, opacity:0.28, lineCap:'round', lineJoin:'round'
    }}).addTo(camadaT);
    const talvegue = L.polyline(polyAnim, {{
      pane:'trajeto', color:'#0891b2', weight:3.5, opacity:0.95
    }}).bindPopup(
      `<b>Trajeto hidráulico (proxy)</b><br>Calha Manso–Cuiabá<br>` +
      `Semi-largura ±${{S.trW}} km<br>Não é mancha PAE / dam break.`
    ).addTo(camadaT);
    const tb = talvegue.getBounds();
    bounds = bounds ? bounds.extend(tb) : tb;
  }}

  L.circleMarker([S.la,S.lo], {{
    pane:'barragem', radius:9, color:'#fff', weight:2,
    fillColor:'#ea580c', fillOpacity:1
  }}).bindPopup(`<b>${{S.no}}</b>`).addTo(camadaB);

  // US reais atingidas (CNES na mancha do cenário — servidor).
  const usAt = S.usAt || [];
  for (const p of usAt) {{
    if (p.h || p.upa || p.ubs || p.prio) {{
      L.marker([p.la,p.lo], {{pane:'us', icon:iconeAtingida(p), zIndexOffset: p.h?350:200}})
        .bindPopup(`<b>US ATINGIDA</b><br>${{(p.tp||'US').toUpperCase()}} — ${{p.no||''}}<br>${{p.mu||''}}<br>${{(p.dist||0).toFixed(1)}} km`)
        .addTo(camadaU);
    }} else {{
      L.circleMarker([p.la,p.lo], {{
        pane:'us', radius:5, color:'#fff', weight:1,
        fillColor:'#2563eb', fillOpacity:0.9
      }}).bindPopup(`<b>US ATINGIDA</b><br>${{(p.tp||'US').toUpperCase()}} — ${{p.no||''}}`)
        .addTo(camadaU);
    }}
  }}

  // Fallback: se servidor não mandou usAt e há círculo, usa CNES no raio.
  if (!usAt.length && S.showC) {{
    for (const p of (S.cnes||[])) {{
      const d = haversine(S.la,S.lo,p.la,p.lo);
      if (d > raio) continue;
      if (p.h || p.upa || p.ubs || p.prio) {{
        L.marker([p.la,p.lo], {{pane:'us', icon:icone(p)}})
          .bindPopup(`<b>US</b><br>${{p.no||''}}<br>${{d.toFixed(1)}} km`).addTo(camadaU);
      }}
    }}
  }}

  if (Math.abs(fPct - Math.round((S.frac0||0.5)*100)) < 1 || !timer) {{
    for (const p of (S.usIso||[])) {{
      L.marker([p.la,p.lo], {{pane:'us', icon:iconeIso(p), zIndexOffset:400}})
        .bindPopup(`<b>US ISOLADA</b><br>${{p.no||''}}<br>${{p.mu||''}}<br>Sem rota terrestre ao hub após corte de vias/pontes.`)
        .addTo(camadaI);
    }}
    for (const m of (S.munIso||[])) {{
      L.marker([m.la,m.lo], {{pane:'us', icon:iconeMun(m), zIndexOffset:500}})
        .bindPopup(
          `<b>Município isolado (proxy)</b><br>${{m.municipio||''}}` +
          `<br>População IBGE: <b>${{(m.populacao||0).toLocaleString('pt-BR')}}</b>` +
          `<br>Sede sem rota ao hub após vias/pontes na mancha.`
        ).addTo(camadaI);
      if (bounds) bounds.extend([m.la,m.lo]);
    }}
  }}
  if (!timer && bounds) mapa.fitBounds(bounds.pad(0.25), {{maxZoom:12, animate:false}});
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
  desenhar(frac);
}};
desenhar(frac);
if (S.autoplay) document.getElementById('btnPlay').click();
</script>
</body></html>"""
