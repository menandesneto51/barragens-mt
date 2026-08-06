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
    DENSIDADE_PADRAO,
    PERFIL_AGUA,
    PERFIL_REJEITO,
    _carregar_densidades_ibge,
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


def cnes_pontos(*, so_prioritarios: bool = False) -> list[dict[str, Any]]:
    """Pontos CNES com coordenada (eixo Cuiabá).

    Por padrão inclui **todas** as US georreferenciadas no buffer da simulação.
    Hospitais/UPA/UBS ficam marcados para destaque visual.
    """
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
        if so_prioritarios and not cls["prioritario"]:
            continue
        pontos.append(
            {
                "la": round(lat, 5),
                "lo": round(lon, 5),
                "h": 1 if cls["hospitalar"] else 0,
                "upa": 1 if cls["upa_ps"] else 0,
                "ubs": 1 if cls["ubs_esf"] else 0,
                "prio": 1 if cls["prioritario"] else 0,
                "tp": cls["tipo"],
                "pr": cls["prioridade"],
                "no": nome[:80],
                "mu": (props.get("municipio") or "").strip(),
            }
        )
    pontos.sort(key=lambda p: (p["pr"], p["no"]))
    return pontos


def _ana_por_barragem() -> dict[str, list[dict[str, Any]]]:
    """Estações ANA vinculadas (contexto fluvial — não altera mancha)."""
    out: dict[str, list[dict[str, Any]]] = {}
    for r in ler_csv("ana_estacoes_barragem.csv"):
        bid = (r.get("id_snisb") or "").strip()
        if not bid:
            continue
        la, lo = num(r.get("lat")), num(r.get("lon"))
        item = {
            "cod": r.get("codigo_estacao") or "",
            "no": r.get("nome_estacao") or "",
            "rio": r.get("nome_rio") or "",
            "rel": r.get("relacao") or "",
            "dist": num(r.get("dist_barragem_km")),
            "cota": num(r.get("cota_cm")),
            "vazao": num(r.get("vazao_m3s")),
            "alerta": num(r.get("cota_alerta_cm")),
            "razao": num(r.get("razao_nivel_cota_alerta")),
            "a6": r.get("a6_fonte") or "",
            "dt": r.get("data_ultima") or "",
            "la": round(la, 5) if la is not None else None,
            "lo": round(lo, 5) if lo is not None else None,
        }
        out.setdefault(bid, []).append(item)
    for bid, itens in out.items():
        itens.sort(key=lambda x: x.get("dist") if x.get("dist") is not None else 999)
    return out


def montar_dados() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    inv = {r["id_snisb"]: r for r in ler_csv("inventario_barragens_mt.csv")}
    idap = {r["id_snisb"]: r for r in ler_csv("idap_estadual_mt.csv")}
    piloto_ids = {r["id_snisb"] for r in ler_csv("piloto_manso_cuiaba.csv")}
    ana = _ana_por_barragem()
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
                "ana": ana.get(bid, [])[:5],
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
:root{--ink:#15202b;--muted:#4a5d73;--paper:#e6ecf7;--card:#fff;--line:#c5d0e0;--accent:#1b3281;--warn:#9a3412}
*{box-sizing:border-box}
@keyframes fadeInUs{to{opacity:1}}
@keyframes pulseRing{0%{opacity:.55}50%{opacity:.28}100%{opacity:.55}}
.mancha-pulse{animation:pulseRing 1.4s ease-in-out infinite}
body{margin:0;font-family:"Source Sans 3",system-ui,sans-serif;color:var(--ink);
background:linear-gradient(180deg,#1b3281 0%,#243f9a 16%,var(--paper) 16%)}
header{padding:18px 22px 12px;border-bottom:1px solid rgba(255,255,255,.18);background:transparent;
display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:flex-end}
.marca{font-family:"Fraunces",Georgia,serif;font-size:1.65rem;margin:0 0 4px;font-weight:600;color:#fff}
header h1{font-family:"Fraunces",Georgia,serif;font-size:1.6rem;margin:0;color:#fff}
header p{margin:4px 0 0;color:rgba(255,255,255,.85);max-width:40rem;line-height:1.4;font-size:13.5px}
nav a{color:#fff;font-weight:600;font-size:13px;margin-left:10px;text-decoration:none;
padding:4px 8px;border:1px solid rgba(255,255,255,.35);background:rgba(255,255,255,.12)}
.selo{background:#1b3281;color:#fff;font-size:11px;font-weight:700;letter-spacing:.06em;
text-transform:uppercase;padding:4px 8px;display:inline-block;margin-bottom:6px;border:1px solid rgba(255,255,255,.4)}
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
  <div class="aviso" style="background:#eef4fb;border-color:#1b3281;margin-top:10px">
    <strong>Geometria:</strong> círculo (todo o estado) e <strong>relevo HAND</strong>
    no eixo Manso–Cuiabá (SRTM proxy). Setores/Sisagua/desvio C7 completos ficam no
    Streamlit (<code>rodar_local.ps1</code>). Bases: __KPIS_EIXO__.
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
      <label>Geometria da mancha</label>
      <select id="geom">
        <option value="circular">Circular (volume→área)</option>
        <option value="ambos">Circular + relevo (HAND)</option>
        <option value="hand">Só relevo (HAND)</option>
      </select>
      <label>Fração do volume liberado: <span class="val" id="vFrac">50%</span></label>
      <input type="range" id="frac" min="5" max="100" step="5" value="50">
      <label>Profundidade / lâmina HAND (m): <span class="val" id="vProf">2,0</span></label>
      <input type="range" id="prof" min="0.5" max="8" step="0.5" value="2">
      <p style="margin:6px 0 0;font-size:12px;color:var(--muted)">
        HAND usa o limiar SRTM mais próximo da lâmina (piloto Manso–Cuiabá).
        Fora do eixo a camada HAND fica vazia — use o círculo.
      </p>
      <div style="margin-top:12px;display:flex;flex-wrap:wrap;gap:8px">
        <button type="button" id="btnPlay" style="padding:8px 12px;border:0;background:#9a3412;color:#fff;font:inherit;font-weight:600;cursor:pointer">▶ Animar no mapa</button>
        <button type="button" id="btnStop" style="padding:8px 12px;border:0;background:#e4e9ef;color:#15202b;font:inherit;font-weight:600;cursor:pointer">Parar</button>
      </div>
      <p style="margin:8px 0 0;font-size:12px;color:var(--muted)">Animação leve no mapa (sem GIF). Expande a mancha e revela US no buffer.</p>
      <div class="kpis">
        <div class="kpi"><div class="n" id="kVol">—</div><div class="r">Volume cadastro (hm³)</div></div>
        <div class="kpi"><div class="n" id="kLib">—</div><div class="r">Volume liberado (hm³)</div></div>
        <div class="kpi"><div class="n" id="kArea">—</div><div class="r">Área equivalente (km²)</div></div>
        <div class="kpi"><div class="n" id="kPop">—</div><div class="r">População estimada</div></div>
        <div class="kpi"><div class="n" id="kRaio">—</div><div class="r">Raio equivalente (km)</div></div>
        <div class="kpi"><div class="n" id="kMun">—</div><div class="r">Municípios a jusante</div></div>
        <div class="kpi" id="kpiPerfil"><div class="n" id="kPerfil">—</div><div class="r">Perfil sanitário</div></div>
        <div class="kpi"><div class="n" id="kUs">—</div><div class="r">US no buffer (CNES)</div></div>
        <div class="kpi"><div class="n" id="kCap">—</div><div class="r">Captações Sisagua</div></div>
        <div class="kpi"><div class="n" id="kSet">—</div><div class="r">Pop. setores (IBGE)</div></div>
        <div class="kpi"><div class="n" id="kEsc">—</div><div class="r">Escolas (INEP/OSM)</div></div>
        <div class="kpi"><div class="n" id="kAtv">—</div><div class="r">Ativos essenciais</div></div>
        <div class="kpi"><div class="n" id="kAna">—</div><div class="r">Estações ANA (contexto)</div></div>
      </div>
      <div class="perfil" id="boxAna" style="max-height:140px"></div>
      <div class="perfil" id="boxPerfil"></div>
      <div class="lista-us" id="listaUs"></div>
      <div class="lista" id="detalhe"></div>
      <p class="formula">
        área_km² = (capacidade_hm³ × fração) / profundidade_m<br>
        população: SIGBM (se houver) senão área × densidade municipal média<br>
        US: <b>todas</b> as unidades CNES com coordenada no raio equivalente<br>
        (não o município inteiro). Fundo = imagem satélite + mancha proxy.
      </p>
    </div>
    <div>
      <div class="mapa-wrap">
        <div id="mapa"></div>
        <div class="legenda-mapa">
          <div><i style="background:#fb923c;opacity:.85;border-radius:2px;width:14px"></i>Área circular (proxy)</div>
          <div><i style="background:#0ea5e9;opacity:.75;border-radius:2px;width:14px"></i>Relevo HAND (proxy)</div>
          <div><i style="background:#0891b2;border:2px solid #fff;box-sizing:border-box"></i>Captação Sisagua</div>
          <div><i style="background:#0f766e;border:2px solid #fff;box-sizing:border-box"></i>Setor censitário (centróide)</div>
          <div><i style="background:#7c3aed;border:2px solid #fff;box-sizing:border-box"></i>Escola</div>
          <div><i style="background:#ca8a04;border:2px solid #fff;box-sizing:border-box"></i>Ativo essencial</div>
          <div><i style="background:#dc2626;border:2px solid #fff;box-sizing:border-box"></i>Hospital</div>
          <div><i style="background:#ea580c;border:2px solid #fff;box-sizing:border-box"></i>UPA / pronto-socorro</div>
          <div><i style="background:#2563eb;border:2px solid #fff;box-sizing:border-box"></i>UBS / ESF / posto</div>
          <div><i style="background:#64748b;border:2px solid #fff;box-sizing:border-box"></i>Demais US CNES</div>
          <div><i style="background:#ea580c"></i>Barragem</div>
          <div><i style="background:#0369a1;border:2px solid #fff;box-sizing:border-box"></i>Estação ANA (rio)</div>
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
const SISAGUA = __SISAGUA__;
const SETORES = __SETORES__;
const ESCOLAS = __ESCOLAS__;
const ATIVOS = __ATIVOS__;
const DENS = __DENS__;
const DENS_PADRAO = __DENS_PADRAO__;
const PERFIS = __PERFIS__;
const HAND_GEO = __HAND_GEO__;
const HAND_LIMIARES = __HAND_LIMIARES__;

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
mapa.createPane('hand');
mapa.getPane('hand').style.zIndex = 360;
mapa.getPane('hand').style.pointerEvents = 'none';
mapa.createPane('us');
mapa.getPane('us').style.zIndex = 450;
mapa.createPane('barragem');
mapa.getPane('barragem').style.zIndex = 460;

const camadaMancha = L.layerGroup().addTo(mapa);
const camadaHand = L.layerGroup().addTo(mapa);
const camadaExtras = L.layerGroup().addTo(mapa);
const camadaUs = L.layerGroup().addTo(mapa);
const camadaBar = L.layerGroup().addTo(mapa);
let manchaAtual = null;
let ultimoCentro = null;

function limiarHand(prof) {
  const lims = (HAND_LIMIARES && HAND_LIMIARES.length) ? HAND_LIMIARES : [2,5,8,10,15,20,30];
  const p = Math.max(0.5, Number(prof) || 2);
  let best = lims[0], bestD = Infinity;
  for (const L of lims) {
    const d = Math.abs(L - p);
    if (d < bestD) { bestD = d; best = L; }
  }
  return best;
}

function featureHand(limiar) {
  if (!HAND_GEO || !HAND_GEO.features) return null;
  const alvo = Number(limiar);
  let hit = null;
  for (const f of HAND_GEO.features) {
    const hm = Number((f.properties || {}).hand_max_m);
    if (hm === alvo) { hit = f; break; }
  }
  return hit;
}

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

function listarPontosNoBuffer(lista, d, raioKm) {
  if (d.la == null || d.lo == null || !(raioKm > 0) || !lista || !lista.length)
    return {itens: [], total: 0};
  const itens = [];
  for (const p of lista) {
    if (p.la == null || p.lo == null) continue;
    const dist = haversineKm(d.la, d.lo, p.la, p.lo);
    if (dist <= raioKm) itens.push({...p, dist});
  }
  itens.sort((a,b) => a.dist - b.dist);
  return {itens, total: itens.length};
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
    html: `<div style="opacity:0;animation:fadeIn .4s forwards">${html}</div>`,
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
  const capBuf = listarPontosNoBuffer(SISAGUA, d, raio);
  const setBuf = listarPontosNoBuffer(SETORES, d, raio);
  const popSet = setBuf.itens.reduce((s, p) => s + (Number(p.pop) || 0), 0);
  const escBuf = listarPontosNoBuffer(ESCOLAS, d, raio);
  const atvBuf = listarPontosNoBuffer(ATIVOS, d, raio);
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
  document.getElementById('kCap').textContent = String(capBuf.total);
  document.getElementById('kSet').textContent = setBuf.total
    ? `${fmt(popSet, 0)} (${setBuf.total} set.)`
    : '0';
  document.getElementById('kEsc').textContent = String(escBuf.total);
  document.getElementById('kAtv').textContent = String(atvBuf.total);
  const ana = d.ana || [];
  const anaCota = ana.filter(a => a.cota != null).length;
  const anaAcima = ana.filter(a => a.razao != null && a.razao >= 1).length;
  const anaA6 = ana.filter(a => a.a6 === 'cota_medida').length;
  document.getElementById('kAna').textContent = ana.length
    ? `${ana.length} (${anaCota} cota${anaAcima ? ', ' + anaAcima + ' ≥ alerta' : ''}${anaA6 ? ', A6 medido ' + anaA6 : ''})`
    : '0';
  document.getElementById('kPerfil').textContent = d.rej ? 'REJEITO' : 'ÁGUA';
  document.getElementById('kpiPerfil').className = 'kpi' + (d.rej ? ' tox' : '');

  const boxAna = document.getElementById('boxAna');
  if (ana.length) {
    boxAna.innerHTML = `<h3>Contexto fluvial ANA/SisClima</h3>
      <div style="color:#4a5d73;margin-bottom:6px">Cota/vazão observadas — <b>não</b> alteram a mancha proxy.</div>` +
      ana.map(a => `<div><b>${a.cod}</b> ${a.no || ''} · ${a.rio || '—'} · ${a.rel || ''}
        · ${a.dist != null ? a.dist.toFixed(1) + ' km' : '—'}
        · cota ${a.cota != null ? fmt(a.cota, 0) + ' cm' : '—'}
        · Q ${a.vazao != null ? fmt(a.vazao, 1) + ' m³/s' : '—'}
        ${a.alerta != null ? ' · alerta ' + fmt(a.alerta, 0) + ' cm' : ''}
        ${a.razao != null ? ' · razão ' + fmt(a.razao, 2) : ''}
        ${a.a6 ? ' · ' + a.a6 : ''}
      </div>`).join('');
  } else {
    boxAna.innerHTML = `<h3>Contexto fluvial ANA/SisClima</h3>
      <div style="color:#5a6b7a">Sem estação vinculada — rode <code>python executar.py 52 53</code>.</div>`;
  }

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
    const maxLista = 80;
    const mostrados = usBuf.itens.slice(0, maxLista);
    const nPrio = usBuf.itens.filter(p => p.prio || p.h || p.upa || p.ubs).length;
    listaUsEl.innerHTML = `<h3>US no buffer (${usBuf.total}) · prioritárias ${nPrio}</h3>` +
      mostrados.map(p => {
        const tag = p.h ? 'Hospital' : (p.upa ? 'UPA/PS' : (p.ubs ? 'UBS/ESF' : (p.tp||'US')));
        return `<div class="${p.h||p.upa?'hosp':''}"><b>${tag}</b> — ${p.no || 'sem nome'} · ${p.mu || '—'}
         <span style="color:#5a6b7a"> · ${p.dist.toFixed(1)} km</span></div>`;
      }).join('') +
      (usBuf.total > maxLista
        ? `<div style="color:#5a6b7a;margin-top:4px">… e mais ${usBuf.total - maxLista} (todas no mapa)</div>`
        : '');
  } else {
    listaUsEl.innerHTML = `<h3>Unidades de saúde no buffer</h3>
      <div style="color:#5a6b7a">Nenhuma US CNES com coordenada neste raio
      (rede do eixo Cuiabá; fora da região o contador fica vazio).</div>`;
  }

  const limPrev = limiarHand(prof);
  const featPrev = featureHand(limPrev);
  document.getElementById('detalhe').innerHTML = `
    <strong>${d.no}</strong> (SNISB ${d.id})
    · <a href="barragem.html?id=${encodeURIComponent(d.id)}">ficha 360°</a><br>
    Sede: ${d.mu} · Uso: ${d.uso || '—'} · CRI ${d.cri||'—'} · DPA ${d.dpa||'—'}<br>
    IDAP: ${d.idap ?? '—'} (${d.nv||'—'}) · Método pop.: ${est.metodo}<br>
    Geometria: <b>${document.getElementById('geom').selectedOptions[0].text}</b>
    · HAND ≤ ${limPrev} m
    (${featPrev && featPrev.properties ? (featPrev.properties.n_celulas + ' células') : 'sem polígono no limiar'})<br>
    US no buffer: ${usBuf.total != null ? usBuf.total + ' (' + usBuf.metodo + ')' : '—'}
    · eixo municipal (ref.): ${d.ust || 0}<br>
    Municípios a jusante:<br>${(d.af||[]).join(' · ') || '—'}<br>
    Estações ANA (contexto): ${(d.ana||[]).length}
  `;

  // Mancha permanece como camada de fundo (pane baixo); US e barragem por cima.
  camadaMancha.clearLayers();
  camadaHand.clearLayers();
  camadaExtras.clearLayers();
  camadaUs.clearLayers();
  camadaBar.clearLayers();
  manchaAtual = null;

  const geom = document.getElementById('geom').value;
  const mostrarCircular = geom === 'circular' || geom === 'ambos';
  const mostrarHand = geom === 'hand' || geom === 'ambos';
  const limH = limiarHand(prof);
  let handLayer = null;

  if (mostrarHand) {
    const feat = featureHand(limH);
    if (feat) {
      handLayer = L.geoJSON(feat, {
        pane: 'hand',
        style: {
          color: '#0369a1',
          weight: 2,
          fillColor: '#0ea5e9',
          fillOpacity: 0.28,
          opacity: 0.85
        }
      }).bindPopup(
        `<b>Relevo HAND ≤ ${limH} m</b><br>` +
        `${(feat.properties && feat.properties.rotulo) || ''}<br>` +
        `Células: ${(feat.properties && feat.properties.n_celulas) || '—'}<br>` +
        `<small>Proxy SRTM — não é mancha PAE / tempo de chegada.</small>`
      ).addTo(camadaHand);
    }
  }

  if (d.la != null && d.lo != null) {
    if (mostrarCircular) {
      manchaAtual = L.circle([d.la, d.lo], {
        pane: 'mancha',
        radius: raio * 1000,
        color: corMancha,
        weight: 2,
        fillColor: fillMancha,
        fillOpacity: 0.22 + 0.28 * Math.min(1, Math.max(0.15, frac)),
        opacity: 0.7 + 0.25 * Math.min(1, frac),
        className: 'mancha-pulse'
      }).bindPopup(
        `<b>Área atingida (proxy circular)</b><br>${fmt(area)} km² · raio ${fmt(raio,2)} km<br>` +
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
    }

    L.circleMarker([d.la, d.lo], {
      pane: 'barragem',
      radius: 9, color: '#fff', weight: 2,
      fillColor: d.rej ? '#b91c1c' : '#ea580c', fillOpacity: 1
    }).bindPopup(`<b>${d.no}</b><br>${perfil.rotulo}<br>Pop. est. ${fmt(est.pop,0)}`).addTo(camadaBar);

    for (const a of (d.ana || [])) {
      if (a.la == null || a.lo == null) continue;
      L.circleMarker([a.la, a.lo], {
        pane: 'us',
        radius: 7, color: '#fff', weight: 2,
        fillColor: '#0369a1', fillOpacity: 0.95
      }).bindPopup(
        `<b>Estação ANA ${a.cod}</b><br>${a.no || ''}<br>${a.rio || '—'} · ${a.rel || ''}<br>` +
        `Cota ${a.cota != null ? fmt(a.cota,0) + ' cm' : '—'} · ` +
        `Q ${a.vazao != null ? fmt(a.vazao,1) + ' m³/s' : '—'}<br>` +
        `<small>Contexto fluvial — não define a mancha.</small>`
      ).addTo(camadaUs);
    }

    // Todas as US no buffer — ícone completo para prioritárias; círculo leve para as demais.
    for (const p of usBuf.itens) {
      if (p.h || p.upa || p.ubs || p.prio) {
        L.marker([p.la, p.lo], {
          pane: 'us',
          icon: iconeUs(p),
          zIndexOffset: p.h ? 300 : (p.upa ? 200 : 100)
        }).bindPopup(
          `<b style="color:${p.h?'#dc2626':(p.upa?'#ea580c':'#2563eb')}">${(p.tp||'US').toUpperCase()}</b><br>` +
          `${p.no || 'sem nome'}<br>${p.mu || '—'}<br>${p.dist.toFixed(1)} km da barragem`
        ).addTo(camadaUs);
      } else {
        L.circleMarker([p.la, p.lo], {
          pane: 'us',
          radius: 4,
          color: '#fff',
          weight: 1,
          fillColor: '#64748b',
          fillOpacity: 0.85
        }).bindPopup(
          `<b>${(p.tp||'US').toUpperCase()}</b><br>${p.no || 'sem nome'}<br>${p.mu || '—'}<br>${p.dist.toFixed(1)} km`
        ).addTo(camadaUs);
      }
    }

    const extras = [
      [capBuf.itens.slice(0, 120), '#0891b2', 'Captação Sisagua'],
      [setBuf.itens.slice(0, 80), '#0f766e', 'Setor censitário'],
      [escBuf.itens.slice(0, 120), '#7c3aed', 'Escola'],
      [atvBuf.itens.slice(0, 120), '#ca8a04', 'Ativo essencial'],
    ];
    for (const [itens, cor, tipo] of extras) {
      for (const p of itens) {
        L.circleMarker([p.la, p.lo], {
          pane: 'us',
          radius: 5,
          color: '#fff',
          weight: 1,
          fillColor: cor,
          fillOpacity: 0.9
        }).bindPopup(
          `<b>${tipo}</b><br>${p.no || 'sem nome'}<br>${p.mu || '—'}` +
          (p.cat ? `<br>${p.cat}` : '') +
          (p.pop != null ? `<br>Pop. ${Number(p.pop).toLocaleString('pt-BR')}` : '') +
          `<br>${p.dist.toFixed(1)} km`
        ).addTo(camadaExtras);
      }
    }

    const centro = [d.la, d.lo];
    const mudou = !ultimoCentro || ultimoCentro[0] !== centro[0] || ultimoCentro[1] !== centro[1];
    ultimoCentro = centro;
    if (mudou || !timerAnim) {
      let bounds = null;
      if (manchaAtual) bounds = manchaAtual.getBounds();
      if (handLayer) {
        const hb = handLayer.getBounds();
        bounds = bounds ? bounds.extend(hb) : hb;
      }
      if (bounds && bounds.isValid && bounds.isValid()) {
        mapa.fitBounds(bounds.pad(0.25), {animate: !timerAnim, maxZoom: 13});
      } else if (bounds) {
        mapa.fitBounds(bounds.pad(0.25), {animate: !timerAnim, maxZoom: 13});
      } else {
        mapa.setView(centro, 11, {animate: !timerAnim});
      }
    }
  }
}

['recorte'].forEach(id => document.getElementById(id).onchange = () => { preencherSelect(); desenhar(); });
['barragem','frac','prof','geom'].forEach(id => document.getElementById(id).oninput = desenhar);
document.getElementById('geom').onchange = desenhar;
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
  }, 160);
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


def _kpis_eixo_resumo() -> str:
    """Contagens estáticas das bases avançadas (HTML aponta ao Streamlit)."""
    parts: list[str] = []
    hand_meta = comum.DADOS_TRATADOS / "hand_piloto_manso_cuiaba_meta.json"
    if hand_meta.exists():
        try:
            meta = json.loads(hand_meta.read_text(encoding="utf-8"))
            parts.append(f"HAND {meta.get('n_celulas', '?')} células")
        except (OSError, json.JSONDecodeError):
            pass
    for nome, rotulo in (
        ("setores_censitarios_eixo_cuiaba.csv", "setores"),
        ("sisagua_captacoes_eixo.csv", "Sisagua"),
        ("escolas_eixo_cuiaba.csv", "escolas"),
        ("mapbiomas_pressao_eixo_cuiaba.csv", "MapBiomas mun."),
    ):
        path = comum.DADOS_TRATADOS / nome
        if path.exists():
            try:
                with path.open(encoding="utf-8-sig", newline="") as f:
                    n = max(0, sum(1 for _ in f) - 1)
                parts.append(f"{rotulo} {n}")
            except OSError:
                pass
    return " · ".join(parts) if parts else "rode etapas 35–41"


def pontos_csv(
    nome: str,
    *,
    nome_campo: str = "nome",
    mun_campo: str = "municipio",
    cat_campo: str | None = None,
    pop_campo: str | None = None,
    limite: int = 800,
) -> list[dict[str, Any]]:
    caminho = comum.DADOS_TRATADOS / nome
    if not caminho.exists():
        return []
    out: list[dict[str, Any]] = []
    with caminho.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            la, lo = num(r.get("latitude")), num(r.get("longitude"))
            if la is None or lo is None:
                continue
            item = {
                "la": la,
                "lo": lo,
                "no": (r.get(nome_campo) or r.get("nome_sistema") or "").strip() or "—",
                "mu": (r.get(mun_campo) or "").strip(),
            }
            if cat_campo:
                item["cat"] = (r.get(cat_campo) or "").strip()
            if pop_campo:
                pop_v = num(r.get(pop_campo))
                item["pop"] = int(pop_v) if pop_v is not None else 0
            out.append(item)
            if len(out) >= limite:
                break
    return out


def _carregar_hand_geo() -> tuple[dict[str, Any], list[float]]:
    path = comum.DADOS_TRATADOS / "hand_piloto_manso_cuiaba.geojson"
    meta_path = comum.DADOS_TRATADOS / "hand_piloto_manso_cuiaba_meta.json"
    geo: dict[str, Any] = {"type": "FeatureCollection", "features": []}
    limiares: list[float] = [2.0, 5.0, 8.0, 10.0, 15.0, 20.0, 30.0]
    if path.exists():
        try:
            geo = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            lims = meta.get("limiares_m") or []
            if lims:
                limiares = [float(x) for x in lims]
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    return geo, limiares


def main() -> None:
    dados, pontos_cnes = montar_dados()
    hand_geo, hand_lims = _carregar_hand_geo()
    sisagua = pontos_csv(
        "sisagua_captacoes_eixo.csv",
        nome_campo="nome_sistema",
        cat_campo="tipo_captacao",
    )
    setores = pontos_csv(
        "setores_censitarios_eixo_cuiaba.csv",
        nome_campo="codigo_setor",
        pop_campo="populacao",
        limite=2500,
    )
    escolas = pontos_csv("escolas_eixo_cuiaba.csv", nome_campo="nome")
    ativos = pontos_csv(
        "ativos_essenciais_osm_eixo.csv",
        nome_campo="nome",
        cat_campo="categoria",
    )
    print(
        f"Simulação — {len(dados)} barragens · {len(pontos_cnes)} US · "
        f"HAND {len(hand_geo.get('features') or [])} · Sisagua {len(sisagua)} · "
        f"setores {len(setores)} · escolas {len(escolas)} · ativos {len(ativos)}"
    )
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
        .replace("__SISAGUA__", json.dumps(sisagua, ensure_ascii=False, separators=(",", ":")))
        .replace("__SETORES__", json.dumps(setores, ensure_ascii=False, separators=(",", ":")))
        .replace("__ESCOLAS__", json.dumps(escolas, ensure_ascii=False, separators=(",", ":")))
        .replace("__ATIVOS__", json.dumps(ativos, ensure_ascii=False, separators=(",", ":")))
        .replace("__DENS__", json.dumps(_carregar_densidades_ibge(), ensure_ascii=False, separators=(",", ":")))
        .replace("__DENS_PADRAO__", str(DENSIDADE_PADRAO))
        .replace("__PERFIS__", json.dumps(perfis, ensure_ascii=False, separators=(",", ":")))
        .replace("__HAND_GEO__", json.dumps(hand_geo, ensure_ascii=False, separators=(",", ":")))
        .replace("__HAND_LIMIARES__", json.dumps(hand_lims, separators=(",", ":")))
        .replace("__GERADO__", dt.datetime.now().strftime("%d/%m/%Y %H:%M"))
        .replace("__KPIS_EIXO__", _kpis_eixo_resumo())
    )
    SAIDA.mkdir(parents=True, exist_ok=True)
    destino = SAIDA / "simulacao.html"
    destino.write_text(html, encoding="utf-8")
    print(f"  gravado {destino.relative_to(comum.RAIZ)} ({destino.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
