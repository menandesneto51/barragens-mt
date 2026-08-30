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
    hand_poligonos: list[list[list[float]]] | None = None,
    hand_limiar_m: float | None = None,
    mostrar_hand: bool = False,
    vulneraveis: list[dict[str, Any]] | None = None,
    escolas: list[dict[str, Any]] | None = None,
    ativos: list[dict[str, Any]] | None = None,
    us_apoio: list[dict[str, Any]] | None = None,
    estacoes_ana: list[dict[str, Any]] | None = None,
    altura: int = 480,
    autoplay: bool = False,
) -> str:
    """Mapa: mancha + US atingidas/apoio + vulneráveis + vias/pontes + ANA."""
    iso = isolamento or {}
    tr = trajeto or {}
    # Limita polígonos HAND no browser (células proxy)
    hand_poly = list(hand_poligonos or [])
    if len(hand_poly) > 900:
        hand_poly = hand_poly[:900]
    vulns = list(vulneraveis or [])[:400]
    esc = list(escolas or [])[:200]
    atv = list(ativos or [])[:200]
    apoio = list(us_apoio or [])[:80]
    ana = list(estacoes_ana or [])[:12]
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
        "usApoio": apoio,
        "ana": ana,
        "munIso": municipios_isolados or iso.get("municipios_isolados") or [],
        "vuln": vulns,
        "escolas": esc,
        "ativos": atv,
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
        "showH": bool(mostrar_hand),
        "handPoly": hand_poly,
        "handLim": float(hand_limiar_m or 0),
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
    border:1px solid #d0d8e0;padding:6px 8px;font-size:11px;line-height:1.4;max-width:280px}}
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
    <div><i style="background:#0e7490;height:10px;width:10px;opacity:.45"></i>Relevo HAND</div>
    <div>● US na mancha (afetada)</div>
    <div>○ US de apoio (fora — atendimento)</div>
    <div>● US isolada (sem rota)</div>
    <div>● Aldeia / TI / quilombo / assentamento</div>
    <div>■ Sede mun. isolada (pop.)</div>
    <div>● Escola (C5)</div>
    <div>● Ativo essencial (ETA/ETE/energia/abrigo)</div>
    <div>● Estação ANA (contexto fluvial)</div>
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
mapa.createPane('hand'); mapa.getPane('hand').style.zIndex=355;
mapa.getPane('hand').style.pointerEvents='none';
mapa.createPane('us'); mapa.getPane('us').style.zIndex=450;
mapa.createPane('ana'); mapa.getPane('ana').style.zIndex=455;
mapa.createPane('vuln'); mapa.getPane('vuln').style.zIndex=440;
mapa.createPane('c5'); mapa.getPane('c5').style.zIndex=435;
mapa.createPane('barragem'); mapa.getPane('barragem').style.zIndex=460;
const camadaV = L.layerGroup().addTo(mapa);
const camadaM = L.layerGroup().addTo(mapa);
const camadaT = L.layerGroup().addTo(mapa);
const camadaH = L.layerGroup().addTo(mapa);
const camadaVuln = L.layerGroup().addTo(mapa);
const camadaC5 = L.layerGroup().addTo(mapa);
const camadaU = L.layerGroup().addTo(mapa);
const camadaAna = L.layerGroup().addTo(mapa);
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
    // Com mancha não-circular (corredor/HAND/união), confia no cut do servidor.
    const cut = (!S.showC || S.showT || S.showH || (S.isoG&&S.isoG!=='circular'))
      ? !!v.cut : viaNoBuffer(v, raio);
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
  let handLinha = '';
  if (S.showH) {{
    handLinha = `<br>HAND ≤ <b>${{S.handLim}}</b> m · ${{(S.handPoly||[]).length}} células`;
  }}
  document.getElementById('hud').innerHTML =
    `<b>${{fPct}}%</b> liberado · área <b>${{area.toFixed(1)}}</b> km²` +
    (S.showC ? `<br>Raio circ. <b>${{raio.toFixed(2)}}</b> km` : '') +
    trLinha + handLinha + '<br>' + isoLinha;

  camadaM.clearLayers(); camadaT.clearLayers(); camadaH.clearLayers();
  camadaVuln.clearLayers(); camadaC5.clearLayers();
  camadaU.clearLayers(); camadaAna.clearLayers();
  camadaB.clearLayers(); camadaI.clearLayers();

  let bounds = null;
  if (S.showC) {{
    const mancha = L.circle([S.la,S.lo], {{
      pane:'mancha', radius: raio*1000, color:'#c2410c', weight:2,
      fillColor:'#fb923c',
      fillOpacity: (S.showT || S.showH) ? 0.10 : (0.22 + 0.28*progress),
      opacity: (S.showT || S.showH) ? 0.55 : (0.7 + 0.25*progress),
      dashArray: (S.showT || S.showH) ? '6 8' : null,
      className: 'mancha-anim'
    }}).addTo(camadaM);
    try {{
      const el = mancha.getElement && mancha.getElement();
      if (el && !S.showT && !S.showH) el.style.animation = 'pulseRing 1.2s ease-in-out infinite';
    }} catch(e) {{}}
    bounds = mancha.getBounds();
  }}

  if (S.showH && (S.handPoly||[]).length) {{
    for (const ring of S.handPoly) {{
      if (!ring || ring.length < 3) continue;
      const poly = L.polygon(ring, {{
        pane:'hand', color:'#0e7490', weight:0.6,
        fillColor:'#06b6d4', fillOpacity:0.28, opacity:0.55
      }}).addTo(camadaH);
      const pb = poly.getBounds();
      bounds = bounds ? bounds.extend(pb) : pb;
    }}
    if (!timer) {{
      // popup único na primeira célula
      const first = S.handPoly[0];
      if (first && first.length) {{
        L.circleMarker(first[0], {{radius:1, opacity:0, fillOpacity:0}}).bindPopup(
          `<b>Relevo HAND (proxy SRTM)</b><br>Células com HAND ≤ ${{S.handLim}} m<br>` +
          `Não é mancha PAE / dam break.`
        ).addTo(camadaH);
      }}
    }}
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

  for (const a of (S.ana||[])) {{
    if (a.la==null || a.lo==null) continue;
    const acima = a.razao != null && Number(a.razao) >= 1;
    L.circleMarker([a.la,a.lo], {{
      pane:'ana', radius:7, color:'#fff', weight:2,
      fillColor: acima ? '#b91c1c' : '#0369a1', fillOpacity:0.95
    }}).bindPopup(
      `<b>Estação ANA ${{a.cod||''}}</b><br>${{a.no||''}}<br>${{a.rio||'—'}} · ${{a.rel||''}}` +
      (a.dist!=null ? `<br>Dist. barragem: <b>${{Number(a.dist).toFixed(1)}} km</b>` : '') +
      `<br>Cota ${{a.cota!=null ? Number(a.cota).toFixed(0)+' cm' : '—'}}` +
      ` · Q ${{a.vazao!=null ? Number(a.vazao).toFixed(1)+' m³/s' : '—'}}` +
      (a.alerta!=null ? `<br>Cota alerta: ${{Number(a.alerta).toFixed(0)}} cm` : '') +
      `<br><small>Contexto fluvial — não define a mancha.</small>`
    ).addTo(camadaAna);
    if (bounds) bounds.extend([a.la,a.lo]);
    else bounds = L.latLngBounds([[a.la,a.lo]]);
  }}

  function corVuln(cat){{
    const c = (cat||'').toLowerCase();
    if (c.includes('aldeia') || c.includes('indígena') || c.includes('indigena') || c.includes('terra indígena') || c.includes('terra indigena')) return '#166534';
    if (c.includes('quilom')) return '#7c3aed';
    if (c.includes('assent')) return '#a16207';
    if (c.includes('saúde') || c.includes('saude') || c.includes('estabelecimento')) return '#1d4ed8';
    return '#0f766e';
  }}
  for (const p of (S.vuln||[])) {{
    if (p.la==null || p.lo==null) continue;
    L.circleMarker([p.la,p.lo], {{
      pane:'vuln', radius:6, color:'#fff', weight:1.5,
      fillColor: corVuln(p.cat), fillOpacity:0.92
    }}).bindPopup(
      `<b>${{p.no||'Comunidade'}}</b><br>${{p.cat||''}}<br>${{p.mu||''}}` +
      (p.fam!=null ? `<br>Famílias: ${{p.fam}}` : '') +
      (p.dist!=null ? `<br>Dist. barragem: <b>${{Number(p.dist).toFixed(1)}} km</b>` : '')
    ).addTo(camadaVuln);
  }}

  for (const p of (S.escolas||[])) {{
    if (p.la==null || p.lo==null) continue;
    L.circleMarker([p.la,p.lo], {{
      pane:'c5', radius:5, color:'#fff', weight:1,
      fillColor:'#ca8a04', fillOpacity:0.9
    }}).bindPopup(`<b>Escola</b><br>${{p.no||''}}<br>${{p.mu||''}}`).addTo(camadaC5);
  }}
  const corAt = {{
    eta_agua:'#0284c7', ete_esgoto:'#0f766e', subestacao_energia:'#b45309',
    abrigo:'#7c3aed', base_ambulancia:'#dc2626'
  }};
  for (const p of (S.ativos||[])) {{
    if (p.la==null || p.lo==null) continue;
    L.circleMarker([p.la,p.lo], {{
      pane:'c5', radius:5, color:'#fff', weight:1,
      fillColor: corAt[p.cat] || '#64748b', fillOpacity:0.92
    }}).bindPopup(
      `<b>${{p.rotulo||p.cat||'Ativo'}}</b><br>${{p.no||''}}<br>${{p.mu||''}}`
    ).addTo(camadaC5);
  }}

  // US reais atingidas (CNES na mancha do cenário — servidor).
  const usAt = S.usAt || [];
  for (const p of usAt) {{
    const dTxt = (p.dist!=null) ? `<br>Dist. barragem: <b>${{Number(p.dist).toFixed(1)}} km</b>` : '';
    if (p.h || p.upa || p.ubs || p.prio) {{
      L.marker([p.la,p.lo], {{pane:'us', icon:iconeAtingida(p), zIndexOffset: p.h?350:200}})
        .bindPopup(`<b>US NA MANCHA</b><br>${{(p.tp||'US').toUpperCase()}} — ${{p.no||''}}<br>${{p.mu||''}}${{dTxt}}`)
        .addTo(camadaU);
    }} else {{
      L.circleMarker([p.la,p.lo], {{
        pane:'us', radius:5, color:'#fff', weight:1,
        fillColor:'#2563eb', fillOpacity:0.9
      }}).bindPopup(`<b>US NA MANCHA</b><br>${{(p.tp||'US').toUpperCase()}} — ${{p.no||''}}${{dTxt}}`)
        .addTo(camadaU);
    }}
  }}

  // US de apoio — fora da mancha (candidatas a atendimento).
  for (const p of (S.usApoio||[])) {{
    if (p.la==null || p.lo==null) continue;
    const dTxt = (p.dist!=null) ? `<br>Dist. barragem: <b>${{Number(p.dist).toFixed(1)}} km</b>` : '';
    const cor = p.h ? '#b91c1c' : (p.upa ? '#c2410c' : '#059669');
    L.circleMarker([p.la,p.lo], {{
      pane:'us', radius:6, color:cor, weight:2,
      fillColor:'#fff', fillOpacity:0.85
    }}).bindPopup(
      `<b>US DE APOIO</b> (fora da mancha)<br>${{(p.tp||'US').toUpperCase()}} — ${{p.no||''}}` +
      `<br>${{p.mu||''}}${{dTxt}}<br><small>Candidata a atendimento / evacuação</small>`
    ).addTo(camadaU);
  }}

  // Fallback: se servidor não mandou usAt e há círculo, usa CNES no raio.
  if (!usAt.length && S.showC) {{
    for (const p of (S.cnes||[])) {{
      const d = haversine(S.la,S.lo,p.la,p.lo);
      if (d > raio) continue;
      if (p.h || p.upa || p.ubs || p.prio) {{
        L.marker([p.la,p.lo], {{pane:'us', icon:icone(p)}})
          .bindPopup(`<b>US</b><br>${{p.no||''}}<br>Dist. barragem: <b>${{d.toFixed(1)}} km</b>`).addTo(camadaU);
      }}
    }}
  }}

  if (Math.abs(fPct - Math.round((S.frac0||0.5)*100)) < 1 || !timer) {{
    for (const p of (S.usIso||[])) {{
      const dTxt = (p.dist!=null) ? `<br>Dist. barragem: <b>${{Number(p.dist).toFixed(1)}} km</b>` : '';
      L.marker([p.la,p.lo], {{pane:'us', icon:iconeIso(p), zIndexOffset:400}})
        .bindPopup(`<b>US ISOLADA</b><br>${{p.no||''}}<br>${{p.mu||''}}${{dTxt}}<br>Sem rota terrestre ao hub após corte de vias/pontes.`)
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
