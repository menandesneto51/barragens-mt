"""Aba de simulação de cenário — volume liberado → área atingida (proxy).

NÃO é dam break oficial nem mancha do PAE. É estimativa geométrica para treino
e priorização enquanto não houver estudo de ruptura (docs/08 Fase 4 / roadmap 1.2).

Fórmula (rótulo obrigatório de simulação):
  área_km² ≈ (capacidade_hm³ × fração liberada) / profundidade_média_m
  porque 1 hm³ espalhado com 1 m de lâmina cobre 1 km².

Saída: painel/simulacao.html
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

import comum

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from idap.impacto_sanitario import (  # noqa: E402
    DENSIDADE_HAB_KM2,
    DENSIDADE_PADRAO,
    PERFIL_AGUA,
    PERFIL_REJEITO,
    eh_rejeito,
)


def num(valor: Any) -> float | None:
    if valor in (None, "", "None"):
        return None
    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return None


def ler_csv(nome: str) -> list[dict[str, Any]]:
    caminho = comum.DADOS_TRATADOS / nome
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


SAIDA = comum.RAIZ / "painel"


def cnes_por_municipio() -> dict[str, dict[str, int]]:
    cont: dict[str, dict[str, int]] = {}
    for r in ler_csv("cnes_estabelecimentos_regiao_cuiaba.csv"):
        mun = (r.get("municipio") or "").strip()
        if not mun:
            continue
        slot = cont.setdefault(mun, {"total": 0, "hosp": 0})
        slot["total"] += 1
        if (r.get("atendimento_hospitalar") or "").strip().lower() == "sim":
            slot["hosp"] += 1
    return cont


def cnes_pontos() -> list[dict[str, Any]]:
    """Pontos CNES prioritários (UBS/ESF/UPA/hospital) com coordenada."""
    from cnes_tipos import classificar_estabelecimento

    caminho = comum.DADOS_TRATADOS / "cnes_estabelecimentos_regiao_cuiaba.geojson"
    if not caminho.exists():
        return []
    geo = json.loads(caminho.read_text(encoding="utf-8"))
    pontos: list[dict[str, Any]] = []
    for feicao in geo.get("features") or []:
        geom = feicao.get("geometry") or {}
        props = feicao.get("properties") or {}
        if geom.get("type") != "Point":
            continue
        coords = geom.get("coordinates") or []
        if len(coords) < 2:
            continue
        lon, lat = float(coords[0]), float(coords[1])
        nome = (props.get("nome_fantasia") or props.get("nome_razao_social") or "").strip()
        cls = classificar_estabelecimento(
            codigo_tipo=props.get("codigo_tipo_unidade"),
            nome=nome,
            atendimento_hospitalar=props.get("atendimento_hospitalar"),
        )
        if not cls["prioritario"]:
            continue
        pontos.append(
            {
                "la": round(lat, 5),
                "lo": round(lon, 5),
                "h": 1 if cls["hospitalar"] else 0,
                "upa": 1 if cls["upa_ps"] else 0,
                "ubs": 1 if cls["ubs_esf"] else 0,
                "tp": cls["tipo"],
                "pr": cls["prioridade"],
                "no": nome[:80],
                "mu": (props.get("municipio") or "").strip(),
            }
        )
    pontos.sort(key=lambda p: (p["pr"], p["no"]))
    return pontos


def montar_dados() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    inv = {r["id_snisb"]: r for r in ler_csv("inventario_barragens_mt.csv")}
    idap = {r["id_snisb"]: r for r in ler_csv("idap_estadual_mt.csv")}
    piloto_ids = {r["id_snisb"] for r in ler_csv("piloto_manso_cuiaba.csv")}
    cnes = cnes_por_municipio()
    pontos = cnes_pontos()

    saida: list[dict[str, Any]] = []
    for bid, r in inv.items():
        vol = num(r.get("capacidade_hm3"))
        if vol is None or vol <= 0:
            continue
        i = idap.get(bid, {})
        la = num(r.get("latitude"))
        lo = num(r.get("longitude"))
        afetados = [
            p.strip()
            for p in (i.get("municipios_potencialmente_afetados") or "").split("|")
            if p.strip()
        ]
        # Fallback municipal (eixo) — o painel prioriza contagem no raio equivalente.
        us_total = sum(cnes.get(m, {}).get("total", 0) for m in afetados)
        us_hosp = sum(cnes.get(m, {}).get("hosp", 0) for m in afetados)
        rejeito = eh_rejeito(r.get("uso_principal"), r.get("orgao_fiscalizador"))
        saida.append(
            {
                "id": bid,
                "no": r.get("nome") or "",
                "mu": r.get("municipio") or "",
                "vol": round(vol, 3),
                "alt": num(r.get("altura_m")),
                "uso": r.get("uso_principal") or "",
                "og": r.get("orgao_fiscalizador") or "",
                "cri": r.get("categoria_risco") or "",
                "dpa": r.get("dano_potencial_associado") or "",
                "popj": num(r.get("sigbm_populacao_jusante")),
                "popa": num(r.get("sigbm_pessoas_afetadas")),
                "la": round(la, 5) if la is not None else None,
                "lo": round(lo, 5) if lo is not None else None,
                "idap": int(i["idap"]) if str(i.get("idap", "")).isdigit() else None,
                "nv": i.get("nivel") or "",
                "af": afetados,
                "pi": 1 if bid in piloto_ids else 0,
                "ust": us_total,
                "ush": us_hosp,
                "rej": 1 if rejeito else 0,
            }
        )
    saida.sort(key=lambda x: (-x["vol"], x["no"]))
    return saida, pontos


MODELO = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Simulação de cenário — VIGIBARRAGENS–MT</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root{--ink:#15202b;--muted:#5a6b7a;--paper:#e9eef2;--card:#fff;--line:#d0d8e0;--accent:#0b6e4f;--warn:#9a3412}
*{box-sizing:border-box}
body{margin:0;font-family:"Source Sans 3",system-ui,sans-serif;color:var(--ink);
background:radial-gradient(ellipse at 0% 0%,#fde8d8,transparent 42%),var(--paper)}
header{padding:18px 22px 12px;border-bottom:1px solid var(--line);background:rgba(255,255,255,.9);
display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:flex-end}
.marca{font-family:"Fraunces",Georgia,serif;font-size:1.65rem;margin:0 0 4px;font-weight:600}
header p{margin:0;color:var(--muted);max-width:40rem;line-height:1.4;font-size:13.5px}
nav a{color:var(--accent);font-weight:600;font-size:13px;margin-left:10px;text-decoration:none}
.selo{background:#9a3412;color:#fff;font-size:11px;font-weight:700;letter-spacing:.06em;
text-transform:uppercase;padding:4px 8px;display:inline-block;margin-bottom:6px}
main{padding:14px 22px 40px;max-width:1400px;margin:0 auto}
.aviso{background:#fff7ed;border-left:4px solid var(--warn);padding:10px 12px;margin-bottom:14px;
font-size:13px;color:#7c2d12;line-height:1.45}
.grade{display:grid;grid-template-columns:340px 1fr;gap:14px}
@media(max-width:960px){.grade{grid-template-columns:1fr}}
.painel{background:var(--card);border:1px solid var(--line);padding:14px}
.painel h2{margin:0 0 10px;font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
label{display:block;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;margin:10px 0 4px}
select,input[type=range]{width:100%}
select{padding:7px 8px;border:1px solid var(--line);font:inherit}
.val{font-variant-numeric:tabular-nums;font-weight:700}
.kpis{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}
.kpi{background:#f7f9fb;border:1px solid var(--line);padding:8px 10px}
.kpi .n{font-size:18px;font-weight:700}.kpi .r{font-size:11px;color:var(--muted)}
.kpi.tox{border-left:3px solid #9a3412}
.perfil{margin-top:12px;font-size:12.5px;line-height:1.45;max-height:180px;overflow:auto;
border:1px solid var(--line);padding:8px 10px;background:#fffdf9}
.perfil h3{margin:0 0 6px;font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--warn)}
#mapa{height:560px;border:1px solid var(--line);background:#1a2330}
.mapa-wrap{position:relative}
.legenda-mapa{position:absolute;z-index:500;left:10px;bottom:10px;background:rgba(255,255,255,.92);
border:1px solid var(--line);padding:8px 10px;font-size:11.5px;line-height:1.55;max-width:220px}
.legenda-mapa i{display:inline-block;width:11px;height:11px;margin-right:5px;vertical-align:middle;border-radius:50%}
.lista{max-height:140px;overflow:auto;font-size:12.5px;margin-top:8px;line-height:1.45}
.lista-us{max-height:160px;overflow:auto;font-size:12px;margin-top:10px;border:1px solid var(--line);
padding:8px 10px;background:#f7fbf9;line-height:1.4}
.lista-us h3{margin:0 0 6px;font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--accent)}
.lista-us .hosp{color:#9a3412;font-weight:700}
.formula{font-size:12px;color:var(--muted);margin-top:12px;line-height:1.45}
.leaflet-cross-icon{background:transparent;border:0}
</style>
</head>
<body>
<header>
  <div>
    <div class="selo">Simulação — não é previsão de rompimento</div>
    <h1 class="marca">Cenário por volume e área</h1>
    <p>Proxy geométrico até existir mancha oficial (PAE/dam break). Gerado __GERADO__.</p>
  </div>
  <nav>
    <a href="index.html">Comando</a>
    <a href="barragem.html">Barragem 360°</a>
    <a href="piloto_manso_cuiaba.html">Piloto</a>
    <a href="hidro.html">Hidro</a>
    <a href="alertas.html">Alertas</a>
  </nav>
</header>
<main>
  <div class="aviso">
    Este módulo <strong>não calcula probabilidade de falha</strong> e <strong>não substitui</strong>
    o estudo de ruptura do empreendedor. A “área atingida” é uma lâmina equivalente
    (volume ÷ profundidade), não a geometria real da onda. Use para treino, priorização e
    diálogo com Defesa Civil / SES — nunca como ordem operacional de evacuação.
  </div>
  <div class="grade">
    <div class="painel">
      <h2>Parâmetros do cenário</h2>
      <label>Recorte</label>
      <select id="recorte">
        <option value="piloto">Piloto Manso–Cuiabá</option>
        <option value="top">Estado — 40 maiores volumes</option>
        <option value="todas">Estado — todas com volume</option>
      </select>
      <label>Barragem</label>
      <select id="barragem"></select>
      <label>Fração do volume liberado: <span class="val" id="vFrac">50%</span></label>
      <input type="range" id="frac" min="5" max="100" step="5" value="50">
      <label>Profundidade média da lâmina (m): <span class="val" id="vProf">2,0</span></label>
      <input type="range" id="prof" min="0.5" max="8" step="0.5" value="2">
      <div style="margin-top:12px;display:flex;flex-wrap:wrap;gap:8px">
        <button type="button" id="btnPlay" style="padding:8px 12px;border:0;background:#9a3412;color:#fff;font:inherit;font-weight:600;cursor:pointer">▶ Animar no mapa</button>
        <button type="button" id="btnStop" style="padding:8px 12px;border:0;background:#e4e9ef;color:#15202b;font:inherit;font-weight:600;cursor:pointer">Parar</button>
      </div>
      <div class="kpis">
        <div class="kpi"><div class="n" id="kVol">—</div><div class="r">Volume cadastro (hm³)</div></div>
        <div class="kpi"><div class="n" id="kLib">—</div><div class="r">Volume liberado (hm³)</div></div>
        <div class="kpi"><div class="n" id="kArea">—</div><div class="r">Área equivalente (km²)</div></div>
        <div class="kpi"><div class="n" id="kPop">—</div><div class="r">População estimada</div></div>
        <div class="kpi"><div class="n" id="kRaio">—</div><div class="r">Raio equivalente (km)</div></div>
        <div class="kpi"><div class="n" id="kMun">—</div><div class="r">Municípios a jusante</div></div>
        <div class="kpi" id="kpiPerfil"><div class="n" id="kPerfil">—</div><div class="r">Perfil sanitário</div></div>
        <div class="kpi"><div class="n" id="kUs">—</div><div class="r">US no buffer (CNES)</div></div>
      </div>
      <div class="perfil" id="boxPerfil"></div>
      <div class="lista-us" id="listaUs"></div>
      <div class="lista" id="detalhe"></div>
      <p class="formula">
        área_km² = (capacidade_hm³ × fração) / profundidade_m<br>
        população: SIGBM (se houver) senão área × densidade municipal média<br>
        US: estabelecimentos CNES com coordenada dentro do raio equivalente<br>
        (não o município inteiro). Fundo = imagem satélite + mancha proxy.
      </p>
    </div>
    <div>
      <div class="mapa-wrap">
        <div id="mapa"></div>
        <div class="legenda-mapa">
          <div><i style="background:#fb923c;opacity:.85;border-radius:2px;width:14px"></i>Área atingida (proxy)</div>
          <div><i style="background:#dc2626;border:2px solid #fff;box-sizing:border-box"></i>Hospital</div>
          <div><i style="background:#ea580c;border:2px solid #fff;box-sizing:border-box"></i>UPA / pronto-socorro</div>
          <div><i style="background:#2563eb;border:2px solid #fff;box-sizing:border-box"></i>UBS / ESF / posto</div>
          <div><i style="background:#ea580c"></i>Barragem</div>
        </div>
      </div>
      <div style="margin-top:10px;background:#fff;border:1px solid var(--line);padding:10px 12px">
        <div style="font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin-bottom:6px">Vídeo / GIF gerado (Manso)</div>
        <img id="gifSim" src="media/simulacao_manso_volume_area.gif" alt="Animação simulação Manso"
             style="max-width:100%;height:auto;border:1px solid var(--line)"
             onerror="this.style.display='none'; this.nextElementSibling.style.display='block'">
        <p style="display:none;font-size:13px;color:var(--muted);margin:0">
          GIF ainda não gerado. Rode <code>python scripts/24_video_simulacao.py</code>
          (ou etapa 24 do pipeline).
        </p>
      </div>
    </div>
  </div>
</main>
<script>
const DADOS = __DADOS__;
const CNES = __CNES__;
const DENS = __DENS__;
const DENS_PADRAO = __DENS_PADRAO__;
const PERFIS = __PERFIS__;

const mapa = L.map('mapa', {zoomControl: true}).setView([-14.9, -55.8], 8);
// Imagem de satélite ao fundo — a mancha proxy fica sobre o terreno real.
const sat = L.tileLayer(
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
  {attribution: 'Tiles &copy; Esri', maxZoom: 18}
).addTo(mapa);
const rotulos = L.tileLayer(
  'https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png',
  {attribution: '&copy; OSM &copy; CARTO', pane: 'shadowPane', opacity: 0.85, maxZoom: 18}
).addTo(mapa);

mapa.createPane('mancha');
mapa.getPane('mancha').style.zIndex = 350;
mapa.getPane('mancha').style.pointerEvents = 'none';
mapa.createPane('us');
mapa.getPane('us').style.zIndex = 450;
mapa.createPane('barragem');
mapa.getPane('barragem').style.zIndex = 460;

const camadaMancha = L.layerGroup().addTo(mapa);
const camadaUs = L.layerGroup().addTo(mapa);
const camadaBar = L.layerGroup().addTo(mapa);
let manchaAtual = null;
let ultimoCentro = null;

function densMedia(d) {
  const munis = (d.af && d.af.length) ? d.af : [d.mu];
  if (!munis.length) return DENS_PADRAO;
  let s = 0;
  munis.forEach(m => { s += (DENS[m] != null ? DENS[m] : DENS_PADRAO); });
  return s / munis.length;
}

function haversineKm(la1, lo1, la2, lo2) {
  const R = 6371, toRad = Math.PI / 180;
  const dLat = (la2 - la1) * toRad, dLon = (lo2 - lo1) * toRad;
  const a = Math.sin(dLat/2)**2 + Math.cos(la1*toRad)*Math.cos(la2*toRad)*Math.sin(dLon/2)**2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

function listarCnesNoBuffer(d, raioKm) {
  if (d.la == null || d.lo == null || !(raioKm > 0) || !CNES.length)
    return {itens: [], total: null, hosp: null, metodo: 'indisponível'};
  const itens = [];
  for (const p of CNES) {
    const dist = haversineKm(d.la, d.lo, p.la, p.lo);
    if (dist <= raioKm) itens.push({...p, dist});
  }
  itens.sort((a,b) => (b.h - a.h) || a.dist - b.dist);
  const hosp = itens.filter(p => p.h).length;
  return {itens, total: itens.length, hosp, metodo: `raio ${raioKm.toFixed(2)} km`};
}

function estimarPop(d, area, frac) {
  if (d.popa != null && d.popa > 0)
    return {pop: Math.round(d.popa * Math.max(0.05, Math.min(1, frac))), metodo: 'SIGBM pessoas afetadas'};
  if (d.popj != null && d.popj > 0)
    return {pop: Math.round(d.popj * Math.max(0.05, Math.min(1, frac))), metodo: 'SIGBM pop. jusante'};
  const dens = densMedia(d);
  return {pop: Math.round(area * dens), metodo: `área × densidade (${dens.toFixed(1)} hab/km²)`};
}

function listaBarragens() {
  const rec = document.getElementById('recorte').value;
  let L = DADOS.slice();
  if (rec === 'piloto') L = L.filter(d => d.pi === 1);
  else if (rec === 'top') L = L.slice(0, 40);
  return L;
}

function preencherSelect() {
  const sel = document.getElementById('barragem');
  const atual = sel.value;
  const L = listaBarragens();
  sel.innerHTML = L.map(d =>
    `<option value="${d.id}">${d.rej ? '⚠ ' : ''}${d.no} — ${d.mu} (${d.vol.toLocaleString('pt-BR')} hm³)</option>`
  ).join('');
  if ([...sel.options].some(o => o.value === atual)) sel.value = atual;
  else if (L.length) {
    const manso = L.find(d => /Leito do Rio/i.test(d.no)) || L[0];
    sel.value = manso.id;
  }
}

function atual() {
  const id = document.getElementById('barragem').value;
  return DADOS.find(d => d.id === id);
}

function fmt(n, casas=1) {
  if (n == null || Number.isNaN(n)) return '—';
  return n.toLocaleString('pt-BR', {maximumFractionDigits: casas});
}

function iconeUs(p) {
  const hosp = !!p.h, upa = !!p.upa;
  const cor = hosp ? '#dc2626' : (upa ? '#ea580c' : '#2563eb');
  const borda = '#fff';
  const cruz = hosp || upa
    ? `<path d="M10 4v4H6v4h4v4h4v-4h4V8h-4V4z" fill="#fff"/>`
    : `<circle cx="12" cy="12" r="4" fill="#fff"/>`;
  const html = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
    <circle cx="12" cy="12" r="11" fill="${cor}" stroke="${borda}" stroke-width="2"/>
    ${cruz}
  </svg>`;
  return L.divIcon({
    className: 'leaflet-cross-icon',
    html,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -12]
  });
}

function desenhar() {
  const d = atual();
  if (!d) return;
  const frac = Number(document.getElementById('frac').value) / 100;
  const prof = Number(document.getElementById('prof').value);
  document.getElementById('vFrac').textContent = Math.round(frac*100) + '%';
  document.getElementById('vProf').textContent = fmt(prof, 1);

  const liberado = d.vol * frac;
  const area = liberado / prof;
  const raio = Math.sqrt(area / Math.PI);
  const est = estimarPop(d, area, frac);
  const usBuf = listarCnesNoBuffer(d, raio);
  const perfil = d.rej ? PERFIS.rejeito : PERFIS.agua;
  const corMancha = d.rej ? '#7f1d1d' : '#c2410c';
  const fillMancha = d.rej ? '#ef4444' : '#fb923c';

  document.getElementById('kVol').textContent = fmt(d.vol, 1);
  document.getElementById('kLib').textContent = fmt(liberado, 1);
  document.getElementById('kArea').textContent = fmt(area, 1);
  document.getElementById('kPop').textContent = fmt(est.pop, 0);
  document.getElementById('kRaio').textContent = fmt(raio, 2);
  document.getElementById('kMun').textContent = (d.af||[]).length;
  document.getElementById('kUs').textContent = usBuf.total != null
    ? `${usBuf.total} (${usBuf.hosp} hosp.)`
    : (d.ust ? `${d.ust} eixo` : '—');
  document.getElementById('kPerfil').textContent = d.rej ? 'REJEITO' : 'ÁGUA';
  document.getElementById('kpiPerfil').className = 'kpi' + (d.rej ? ' tox' : '');

  document.getElementById('boxPerfil').innerHTML = `
    <h3>${perfil.rotulo}</h3>
    <div><b>Material:</b> ${perfil.material}</div>
    <div style="margin-top:6px"><b>Agravos a vigiar:</b><ul style="margin:4px 0 0 16px;padding:0">
      ${perfil.agravos.map(a => `<li>${a}</li>`).join('')}
    </ul></div>
    <div style="margin-top:6px"><b>Ações sanitárias:</b><ul style="margin:4px 0 0 16px;padding:0">
      ${perfil.acoes.map(a => `<li>${a}</li>`).join('')}
    </ul></div>
  `;

  const listaUsEl = document.getElementById('listaUs');
  if (usBuf.itens && usBuf.itens.length) {
    const maxLista = 40;
    const mostrados = usBuf.itens.slice(0, maxLista);
    listaUsEl.innerHTML = `<h3>US prioritárias no buffer (${usBuf.total})</h3>` +
      mostrados.map(p => {
        const tag = p.h ? 'Hospital' : (p.upa ? 'UPA/PS' : (p.ubs ? 'UBS/ESF' : (p.tp||'US')));
        return `<div class="${p.h||p.upa?'hosp':''}"><b>${tag}</b> — ${p.no || 'sem nome'} · ${p.mu || '—'}
         <span style="color:#5a6b7a"> · ${p.dist.toFixed(1)} km</span></div>`;
      }).join('') +
      (usBuf.total > maxLista
        ? `<div style="color:#5a6b7a;margin-top:4px">… e mais ${usBuf.total - maxLista} no mapa</div>`
        : '');
  } else {
    listaUsEl.innerHTML = `<h3>Unidades de saúde no buffer</h3>
      <div style="color:#5a6b7a">Nenhuma US CNES com coordenada neste raio
      (rede do eixo Cuiabá; fora da região o contador fica vazio).</div>`;
  }

  document.getElementById('detalhe').innerHTML = `
    <strong>${d.no}</strong> (SNISB ${d.id})
    · <a href="barragem.html?id=${encodeURIComponent(d.id)}">ficha 360°</a><br>
    Sede: ${d.mu} · Uso: ${d.uso || '—'} · CRI ${d.cri||'—'} · DPA ${d.dpa||'—'}<br>
    IDAP: ${d.idap ?? '—'} (${d.nv||'—'}) · Método pop.: ${est.metodo}<br>
    US no buffer: ${usBuf.total != null ? usBuf.total + ' (' + usBuf.metodo + ')' : '—'}
    · eixo municipal (ref.): ${d.ust || 0}<br>
    Municípios a jusante:<br>${(d.af||[]).join(' · ') || '—'}
  `;

  // Mancha permanece como camada de fundo (pane baixo); US e barragem por cima.
  camadaMancha.clearLayers();
  camadaUs.clearLayers();
  camadaBar.clearLayers();
  manchaAtual = null;

  if (d.la != null && d.lo != null) {
    manchaAtual = L.circle([d.la, d.lo], {
      pane: 'mancha',
      radius: raio * 1000,
      color: corMancha,
      weight: 2,
      fillColor: fillMancha,
      fillOpacity: 0.38,
      opacity: 0.95
    }).bindPopup(
      `<b>Área atingida (proxy)</b><br>${fmt(area)} km² · raio ${fmt(raio,2)} km<br>` +
      `Pop. est. ${fmt(est.pop,0)}` +
      (usBuf.total != null ? `<br>US afetadas: <b>${usBuf.total}</b> (${usBuf.hosp} hosp.)` : '') +
      `<br><small>Não é mancha oficial do PAE.</small>`
    ).addTo(camadaMancha);

    // Halo externo suave para reforçar a área no satélite
    L.circle([d.la, d.lo], {
      pane: 'mancha',
      radius: raio * 1000,
      color: corMancha,
      weight: 8,
      opacity: 0.18,
      fill: false
    }).addTo(camadaMancha);

    L.circleMarker([d.la, d.lo], {
      pane: 'barragem',
      radius: 9, color: '#fff', weight: 2,
      fillColor: d.rej ? '#b91c1c' : '#ea580c', fillOpacity: 1
    }).bindPopup(`<b>${d.no}</b><br>${perfil.rotulo}<br>Pop. est. ${fmt(est.pop,0)}`).addTo(camadaBar);

    // Destacar todas as US no buffer (hospitais sempre; demais se ≤150)
    const desenharTodas = usBuf.itens.length <= 150;
    const paraMapa = desenharTodas
      ? usBuf.itens
      : usBuf.itens.filter(p => p.h).concat(usBuf.itens.filter(p => !p.h).slice(0, 40));
    for (const p of paraMapa) {
      L.marker([p.la, p.lo], {
        pane: 'us',
        icon: iconeUs(p),
        zIndexOffset: p.h ? 300 : (p.upa ? 200 : 100)
      }).bindPopup(
        `<b style="color:${p.h?'#dc2626':(p.upa?'#ea580c':'#2563eb')}">${(p.tp||'US').toUpperCase()}</b><br>` +
        `${p.no || 'sem nome'}<br>${p.mu || '—'}<br>${p.dist.toFixed(1)} km da barragem`
      ).addTo(camadaUs);
    }

    const centro = [d.la, d.lo];
    const mudou = !ultimoCentro || ultimoCentro[0] !== centro[0] || ultimoCentro[1] !== centro[1];
    ultimoCentro = centro;
    if (mudou || !timerAnim) {
      const b = manchaAtual.getBounds();
      mapa.fitBounds(b.pad(0.25), {animate: !timerAnim, maxZoom: 13});
    }
  }
}

['recorte'].forEach(id => document.getElementById(id).onchange = () => { preencherSelect(); desenhar(); });
['barragem','frac','prof'].forEach(id => document.getElementById(id).oninput = desenhar);
let timerAnim = null;
document.getElementById('btnPlay').onclick = () => {
  if (timerAnim) clearInterval(timerAnim);
  const fracEl = document.getElementById('frac');
  let f = 5;
  fracEl.value = f;
  desenhar();
  timerAnim = setInterval(() => {
    f += 5;
    if (f > 100) { clearInterval(timerAnim); timerAnim = null; desenhar(); return; }
    fracEl.value = f;
    desenhar();
  }, 180);
};
document.getElementById('btnStop').onclick = () => {
  if (timerAnim) { clearInterval(timerAnim); timerAnim = null; }
};
preencherSelect();
desenhar();
</script>
</body>
</html>
"""


def _perfil_json(perfil) -> dict[str, Any]:
    return {
        "rotulo": perfil.rotulo,
        "material": perfil.material,
        "agravos": list(perfil.agravos_a_vigiar),
        "acoes": list(perfil.acoes_especificas),
    }


def main() -> None:
    dados, pontos_cnes = montar_dados()
    print(f"Simulação — {len(dados)} barragens com volume · {len(pontos_cnes)} US CNES com coordenada")
    perfis = {
        "agua": _perfil_json(PERFIL_AGUA),
        "rejeito": _perfil_json(PERFIL_REJEITO),
    }
    html = (
        MODELO.replace(
            "__DADOS__",
            json.dumps(dados, ensure_ascii=False, separators=(",", ":")),
        )
        .replace(
            "__CNES__",
            json.dumps(pontos_cnes, ensure_ascii=False, separators=(",", ":")),
        )
        .replace("__DENS__", json.dumps(DENSIDADE_HAB_KM2, ensure_ascii=False, separators=(",", ":")))
        .replace("__DENS_PADRAO__", str(DENSIDADE_PADRAO))
        .replace("__PERFIS__", json.dumps(perfis, ensure_ascii=False, separators=(",", ":")))
        .replace("__GERADO__", dt.datetime.now().strftime("%d/%m/%Y %H:%M"))
    )
    SAIDA.mkdir(parents=True, exist_ok=True)
    destino = SAIDA / "simulacao.html"
    destino.write_text(html, encoding="utf-8")
    print(f"  gravado {destino.relative_to(comum.RAIZ)} ({destino.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
