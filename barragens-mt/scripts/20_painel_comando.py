"""Gera a Tela 1 — Comando estadual (docs/07-telas.md §7.1).

Painel operacional autocontido com IDAP, hidro SisClima/TITAN e alertabilidade.
Substitui `painel/index.html` como entrada principal do sistema.
O painel de inventário/fiscalização fica em `painel/inventario.html` (etapa 07).
"""

from __future__ import annotations

import csv
import datetime as dt
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import comum

SAIDA = comum.RAIZ / "painel"


def _carregar_07():
    caminho = Path(__file__).resolve().parent / "07_painel.py"
    spec = importlib.util.spec_from_file_location("painel_inventario", caminho)
    if spec is None or spec.loader is None:
        raise SystemExit("não foi possível carregar 07_painel.py")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["painel_inventario"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def ler_csv(nome: str) -> list[dict[str, Any]]:
    caminho = comum.DADOS_TRATADOS / nome
    if not caminho.exists():
        raise SystemExit(f"base ausente: {nome}. Rode as etapas 05, 16 e 17.")
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def num(valor: Any) -> float | None:
    if valor in (None, "", "None"):
        return None
    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return None


def idade_arquivo(nome: str) -> dict[str, Any]:
    caminho = comum.DADOS_TRATADOS / nome
    if not caminho.exists():
        return {"arquivo": nome, "existe": False, "idade_h": None, "mtime": ""}
    mtime = dt.datetime.fromtimestamp(caminho.stat().st_mtime)
    idade_h = round((dt.datetime.now() - mtime).total_seconds() / 3600, 1)
    return {
        "arquivo": nome,
        "existe": True,
        "idade_h": idade_h,
        "mtime": mtime.strftime("%d/%m/%Y %H:%M"),
    }


def ler_historico_comando(limite: int = 30) -> dict[str, Any]:
    """Índice estadual + série IDAP das barragens não-Verde (sparklines)."""
    pasta = comum.DADOS_TRATADOS / "historico_idap"
    indice_path = pasta / "indice.csv"
    if not indice_path.exists():
        return {"indice": [], "series": {}}
    with indice_path.open(encoding="utf-8-sig", newline="") as arquivo:
        indice = list(csv.DictReader(arquivo, delimiter=";"))[-limite:]
    series: dict[str, list[dict[str, Any]]] = {}
    for linha in indice:
        arq = pasta / (linha.get("arquivo") or "")
        if not arq.exists():
            continue
        instante = (linha.get("instante") or "")[:19]
        with arq.open(encoding="utf-8-sig", newline="") as arquivo:
            for r in csv.DictReader(arquivo, delimiter=";"):
                nv = r.get("nivel") or "Verde"
                if nv == "Verde":
                    continue
                bid = (r.get("id_snisb") or "").strip()
                if not bid:
                    continue
                series.setdefault(bid, []).append(
                    {
                        "t": instante,
                        "idap": int(r["idap"]) if str(r.get("idap", "")).isdigit() else 0,
                        "nv": nv,
                    }
                )
    return {
        "indice": [
            {
                "t": (x.get("instante") or "")[:19],
                "ama": int(x.get("amarelo") or 0),
                "lar": int(x.get("laranja") or 0),
                "ver": int(x.get("vermelho") or 0),
                "rox": int(x.get("roxo") or 0),
                "n": int(x.get("n_barragens") or 0),
            }
            for x in indice
        ],
        "series": series,
    }


def montar_registros() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    inventario = {r["id_snisb"]: r for r in ler_csv("inventario_barragens_mt.csv")}
    idap = ler_csv("idap_estadual_mt.csv")
    hidro = {r["id_snisb"]: r for r in ler_csv("hidro_barragens_mt.csv")}
    piloto_path = comum.DADOS_TRATADOS / "piloto_manso_cuiaba.csv"
    piloto_ids: set[str] = set()
    if piloto_path.exists():
        with piloto_path.open(encoding="utf-8-sig", newline="") as arquivo:
            piloto_ids = {
                (r.get("id_snisb") or "").strip()
                for r in csv.DictReader(arquivo, delimiter=";")
            }

    registros: list[dict[str, Any]] = []
    for linha in idap:
        bid = linha["id_snisb"]
        inv = inventario.get(bid, {})
        h = hidro.get(bid, {})
        la = num(inv.get("latitude"))
        lo = num(inv.get("longitude"))
        registros.append(
            {
                "id": bid,
                "no": linha.get("nome") or inv.get("nome") or "",
                "mu": linha.get("municipio_sede") or inv.get("municipio") or "",
                "og": linha.get("orgao_fiscalizador") or "",
                "us": linha.get("uso_principal") or "",
                "cri": linha.get("categoria_risco") or "",
                "dpa": linha.get("dano_potencial_associado") or "",
                "la": round(la, 5) if la is not None else None,
                "lo": round(lo, 5) if lo is not None else None,
                "idap": int(linha["idap"]) if str(linha.get("idap", "")).isdigit() else 0,
                "nv": linha.get("nivel") or "Verde",
                "comp": linha.get("completude") or "",
                "conf": linha.get("confiabilidade") or "",
                "pa": int(linha.get("pontos_a") or 0),
                "pb": int(linha.get("pontos_b") or 0),
                "pc": int(linha.get("pontos_c") or 0),
                "pd": int(linha.get("pontos_d") or 0),
                "al": linha.get("alertavel") or "não avaliado",
                "reg": linha.get("regras_disparadas") or "",
                "lac": linha.get("lacunas") or "",
                "af": linha.get("municipios_potencialmente_afetados") or "",
                "nex": int(linha.get("n_municipios_extraterritoriais") or 0),
                "pi": 1 if bid in piloto_ids else 0,
                "c24": num(h.get("chuva_24h_mm")),
                "c72": num(h.get("chuva_72h_mm")),
                "cprev": num(h.get("chuva_prevista_24_72h_mm")),
                "pct": num(h.get("percentil_climatologico")),
                "sat": h.get("saturacao_antecedente") or "",
                "satn": num(h.get("saturacao_antecedente")),
                "nh": h.get("nivel_alerta_hidro") or "",
                "cem": h.get("alerta_cemaden_nivel") or "",
                "cemt": h.get("alerta_cemaden") or "",
                "aint": h.get("nivel_alerta_integrado") or "",
                "glofas": num(h.get("vazao_prevista_glofas_m3s")),
                "aprox": h.get("aproximacao_espacial") or "",
                "dh": h.get("data_referencia") or "",
                "inst": linha.get("instante") or "",
            }
        )

    niveis = Counter(r["nv"] for r in registros)
    frescor = [
        idade_arquivo("idap_estadual_mt.csv"),
        idade_arquivo("hidro_barragens_mt.csv"),
        idade_arquivo("hidro_municipios_mt.csv"),
        idade_arquivo("inventario_barragens_mt.csv"),
        idade_arquivo("piloto_manso_cuiaba.csv"),
        idade_arquivo("alertabilidade_piloto.csv"),
    ]

    def _max(campo: str) -> float | None:
        vals = [r[campo] for r in registros if r.get(campo) is not None]
        return round(max(vals), 1) if vals else None

    def _media(campo: str) -> float | None:
        vals = [float(r[campo]) for r in registros if r.get(campo) is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    idaps = [r["idap"] for r in registros]
    amarelo_mais = sum(
        niveis.get(n, 0) for n in ("Amarelo", "Laranja", "Vermelho", "Roxo")
    )
    meta = {
        "gerado": dt.datetime.now().strftime("%d/%m/%Y %H:%M"),
        "total": len(registros),
        "niveis": {k: niveis.get(k, 0) for k in ("Roxo", "Vermelho", "Laranja", "Amarelo", "Verde")},
        "com_coord": sum(1 for r in registros if r["la"] is not None and r["lo"] is not None),
        "alertaveis": sum(1 for r in registros if r["al"] == "sim"),
        "nao_alertaveis": sum(1 for r in registros if r["al"] == "não"),
        "extraterritoriais": sum(1 for r in registros if r["nex"] > 0),
        "piloto": sum(1 for r in registros if r["pi"] == 1),
        "instante_idap": next((r["inst"] for r in registros if r["inst"]), ""),
        "data_hidro": next((r["dh"] for r in registros if r["dh"]), ""),
        "frescor": frescor,
        "risco": {
            "amarelo_mais": amarelo_mais,
            "idap_max": max(idaps) if idaps else 0,
            "idap_medio": round(sum(idaps) / len(idaps), 1) if idaps else 0,
            "com_pressao_a": sum(1 for r in registros if r["pa"] > 0),
            "a_medio": _media("pa") or 0,
            "b_medio": _media("pb") or 0,
            "c_medio": _media("pc") or 0,
            "d_medio": _media("pd") or 0,
            "chuva24_max": _max("c24"),
            "chuva72_max": _max("c72"),
            "prevista_max": _max("cprev"),
            "percentil_max": _max("pct"),
            "cemaden_ativos": sum(
                1
                for r in registros
                if r.get("cem") and str(r["cem"]).lower() not in {"", "verde"}
            ),
            "integrado_alto": sum(
                1
                for r in registros
                if str(r.get("aint") or "").lower()
                in {"laranja", "vermelha", "vermelho", "roxa", "roxo"}
            ),
            "regras_r10": sum(1 for r in registros if "R10" in (r.get("reg") or "")),
            "regras_r11": sum(1 for r in registros if "R11" in (r.get("reg") or "")),
            "regras_r12": sum(1 for r in registros if "R12" in (r.get("reg") or "")),
            "cri_alto": sum(
                1 for r in registros if (r.get("cri") or "").strip().lower() == "alto"
            ),
            "dpa_alto": sum(
                1 for r in registros if (r.get("dpa") or "").strip().lower() == "alto"
            ),
            "rejeito": sum(
                1
                for r in registros
                if "rejeito" in (r.get("us") or "").lower()
                or "miner" in (r.get("og") or "").lower()
            ),
        },
    }
    for faixa in ("Roxo", "Vermelho", "Laranja", "Amarelo", "Verde"):
        if meta["niveis"].get(faixa, 0) > 0:
            meta["semaforo"] = faixa
            break
    else:
        meta["semaforo"] = "Verde"
    return registros, meta


MODELO = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Comando estadual — VIGIBARRAGENS–MT</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root{
  --ink:#15202b; --muted:#5a6b7a; --paper:#e9eef2; --card:#fff; --line:#d0d8e0;
  --accent:#0b6e4f;
  --roxo:#5b2c6f; --verm:#c0392b; --lar:#d35400; --ama:#b7950b; --verd:#1e8449;
}
*{box-sizing:border-box}
body{margin:0;font-family:"Source Sans 3",system-ui,sans-serif;color:var(--ink);
background:radial-gradient(ellipse at 0% 0%,#d5e6dc 0%,transparent 42%),
radial-gradient(ellipse at 100% 0%,#d4e0eb 0%,transparent 40%),var(--paper);font-size:14px}
header{padding:22px 24px 14px;border-bottom:1px solid var(--line);
background:linear-gradient(180deg,rgba(255,255,255,.9),rgba(255,255,255,.55));
display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;align-items:flex-end}
.marca{font-family:"Fraunces",Georgia,serif;font-size:clamp(1.5rem,2.5vw,1.9rem);
font-weight:600;margin:0 0 4px;letter-spacing:-.02em}
header p{margin:0;color:var(--muted);max-width:36rem;line-height:1.4}
nav{display:flex;flex-wrap:wrap;gap:8px}
nav a{color:var(--accent);text-decoration:none;font-size:13px;font-weight:600;
padding:6px 10px;border:1px solid var(--line);background:#fff}
nav a:hover{background:#f0f7f3}
main{padding:16px 24px 40px;max-width:1600px;margin:0 auto}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(118px,1fr));gap:10px;margin-bottom:14px}
.kpi{background:var(--card);border:1px solid var(--line);padding:11px 12px;
box-shadow:0 1px 0 rgba(21,32,43,.04)}
.kpi .n{font-size:22px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1.1}
.kpi .r{font-size:10.5px;color:var(--muted);margin-top:3px;text-transform:uppercase;letter-spacing:.04em}
section h2{font-family:"Fraunces",Georgia,serif;font-size:1.15rem;font-weight:600;margin:18px 0 8px;
letter-spacing:-.02em}
.semaforo{display:flex;align-items:center;gap:10px;padding:10px 14px;margin-bottom:10px;
background:var(--card);border:1px solid var(--line)}
.semaforo .luz{width:18px;height:18px;border-radius:50%}
.frescor{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px}
.frescor .chip{background:var(--card);border:1px solid var(--line);padding:6px 10px;font-size:12px}
.frescor .ok{border-left:3px solid var(--verd)}
.frescor .velho{border-left:3px solid var(--lar)}
.frescor .morto{border-left:3px solid var(--verm)}
.filtros{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;
background:var(--card);border:1px solid var(--line);padding:12px 14px;margin-bottom:14px;align-items:end}
.filtros label{display:block;font-size:11px;font-weight:600;color:var(--muted);
text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px}
select,input[type=text],input[type=number]{width:100%;padding:7px 8px;border:1px solid var(--line);
font:inherit;background:#fff}
button{padding:8px 12px;border:0;background:var(--accent);color:#fff;font:inherit;font-weight:600;cursor:pointer}
button.sec{background:#e4e9ef;color:var(--ink)}
.grade{display:grid;grid-template-columns:1.4fr 1fr;gap:14px;margin-bottom:14px}
@media(max-width:1100px){.grade{grid-template-columns:1fr}}
.cartao{background:var(--card);border:1px solid var(--line);overflow:hidden}
.cartao h2{margin:0;padding:10px 14px;font-size:12px;text-transform:uppercase;letter-spacing:.05em;
color:var(--muted);border-bottom:1px solid var(--line);background:#f7f9fb}
#mapa{height:560px}
.rolagem{max-height:560px;overflow:auto}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th,td{padding:7px 9px;border-bottom:1px solid #eef1f5;text-align:left;white-space:nowrap}
th{position:sticky;top:0;background:#f7f9fb;font-size:11px;color:var(--muted);
text-transform:uppercase;letter-spacing:.03em;cursor:pointer}
tbody tr{cursor:pointer} tbody tr:hover{background:#f3f8f5}
.etq{display:inline-block;padding:2px 7px;color:#fff;font-size:11px;font-weight:600}
.Roxo{background:var(--roxo)}.Vermelho{background:var(--verm)}.Laranja{background:var(--lar)}
.Amarelo{background:var(--ama)}.Verde{background:var(--verd)}
.legenda{display:flex;flex-wrap:wrap;gap:12px;padding:8px 14px;font-size:12px;color:var(--muted)}
.legenda i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:4px}
.nota{margin-top:14px;font-size:12.5px;color:var(--muted);line-height:1.55;max-width:52rem}
.leaflet-popup-content{font-size:12.5px;line-height:1.55}
</style>
</head>
<body>
<header>
  <div>
    <h1 class="marca">VIGIBARRAGENS–MT</h1>
    <p>Comando estadual — como está Mato Grosso agora e onde olhar primeiro.
    IDAP + hidro SisClima/TITAN · __GERADO__</p>
  </div>
  <nav>
    <a href="hidro.html">Hidro municipal</a>
    <a href="barragem.html">Barragem 360°</a>
    <a href="simulacao.html">Simulação volume/área</a>
    <a href="glossario.html">Interpretação / KPIs</a>
    <a href="piloto_manso_cuiaba.html">Piloto Manso–Cuiabá</a>
    <a href="alertas.html">Fila de alertas</a>
    <a href="ficha_rapida.html">Ficha rápida</a>
    <a href="confirmacao_alerta.html">Confirmação</a>
    <a href="inventario.html">Inventário</a>
  </nav>
</header>
<main>
  <div class="semaforo" id="semaforo"></div>
  <div class="frescor" id="frescor"></div>
  <div class="kpis" id="kpis"></div>
  <div class="cartao" style="margin-bottom:14px">
    <h2>Indicadores de risco (estadual)</h2>
    <div class="kpis" id="riscoKpis" style="padding:12px 14px;margin:0"></div>
    <p style="margin:0 14px 12px;font-size:12px;color:var(--muted);line-height:1.45">
      IDAP e dimensões A–D vêm do cálculo estadual. Chuva/previsão = máximo entre barragens
      (SisClima + ECMWF). Cemaden/integrado = sede com alerta acima de verde. Regras R10–R12
      elevam faixa por alerta externo ou previsão extrema.
    </p>
  </div>
  <div class="cartao" style="margin-bottom:14px">
    <h2>Histórico IDAP (snapshots)</h2>
    <div id="histEstado" style="padding:10px 14px"></div>
    <div class="rolagem" style="max-height:160px"><table>
      <thead><tr><th>Barragem</th><th>Nível</th><th>Série</th><th>Último IDAP</th></tr></thead>
      <tbody id="histBarragens"></tbody>
    </table></div>
  </div>
  <div class="filtros">
    <div><label>Nível IDAP</label>
      <select id="fNivel"><option value="">Todos</option>
        <option>Roxo</option><option>Vermelho</option><option>Laranja</option>
        <option>Amarelo</option><option>Verde</option></select></div>
    <div><label>Município sede</label><input type="text" id="fMun" placeholder="parte do nome"></div>
    <div><label>Órgão</label><input type="text" id="fOrg" placeholder="SEMA, ANM…"></div>
    <div><label>Alertável</label>
      <select id="fAl"><option value="">Todos</option><option value="sim">sim</option>
        <option value="não">não</option><option value="não avaliado">não avaliado</option></select></div>
    <div><label>Recorte</label>
      <select id="fPi"><option value="">Estado todo</option><option value="1">Só piloto Manso–Cuiabá</option></select></div>
    <div><label>Só extraterritorial</label>
      <select id="fExt"><option value="">Não</option><option value="1">Sim</option></select></div>
    <div><label>Busca</label><input type="text" id="fBusca" placeholder="nome ou id SNISB"></div>
    <div><button type="button" id="btnFiltrar">Filtrar</button>
      <button type="button" class="sec" id="btnLimpar">Limpar</button>
      <button type="button" class="sec" id="btnAmarelo" title="Filtra e enquadra no mapa">Focar Amarelo+</button></div>
  </div>
  <div class="cartao" style="margin-bottom:14px">
    <h2>Risco × pressão climática (dimensão A + hidro SisClima/TITAN)</h2>
    <div class="rolagem" style="max-height:220px"><table>
      <thead><tr>
        <th>Nível</th><th>IDAP</th><th>A</th><th>Chuva 24h</th><th>Chuva 72h</th>
        <th>Prevista</th><th>Saturação</th><th>Cemaden</th><th>Barragem</th><th>Sede</th>
      </tr></thead>
      <tbody id="clima"></tbody>
    </table></div>
    <p style="margin:8px 14px 12px;font-size:12px;color:var(--muted)">
      Lista: nível ≠ Verde <em>ou</em> pontos A &gt; 0. Clique na linha para ir ao mapa.
      A = pressão hidroclimática do IDAP; chuva/saturação/previsão vêm do coletor 17.
    </p>
  </div>
  <div class="grade">
    <div class="cartao">
      <h2>Mapa por faixa IDAP</h2>
      <div id="mapa"></div>
      <div class="legenda" id="legenda"></div>
    </div>
    <div class="cartao">
      <h2>Top 10 por IDAP (olhar primeiro)</h2>
      <div class="rolagem"><table>
        <thead><tr>
          <th data-k="idap">IDAP</th><th>Nível</th><th>A</th><th>Barragem</th><th>Sede</th>
          <th>Comp.</th><th>Chuva 24h</th><th>Alertável</th>
        </tr></thead>
        <tbody id="top"></tbody>
      </table></div>
    </div>
  </div>
  <div class="cartao">
    <h2>Fila operacional (<span id="nFila">0</span>)</h2>
    <div class="rolagem"><table>
      <thead><tr>
        <th data-k="idap">IDAP</th><th>Nível</th><th>A</th><th>B</th><th>C</th><th>D</th>
        <th>Barragem</th><th>Sede</th><th>Afetados</th><th>Chuva 72h</th><th>Alertável</th>
      </tr></thead>
      <tbody id="fila"></tbody>
    </table></div>
  </div>
  <p class="nota">
    Completude baixa não é “verde seguro”: leia lacunas no popup. Hidro = máximo sede+montante (Otto).
    C3 no eixo Cuiabá é proxy CNES (sem mancha). Alertável exige contatos validados (etapa 19).
    Instantâneo IDAP: <code>__INSTANTE__</code> · hidro ref.: <code>__DATA_HIDRO__</code>.
  </p>
</main>
<script>
const DADOS = __DADOS__;
const MALHA = __MALHA__;
const META = __META__;
const HIST = __HIST__;
const CORES = {Roxo:'#5b2c6f',Vermelho:'#c0392b',Laranja:'#d35400',Amarelo:'#b7950b',Verde:'#1e8449'};

function sparkMini(pts){
  if(!pts || !pts.length) return '—';
  const w=90,h=22,pad=2;
  const vals=pts.map(p=>p.idap);
  const min=Math.min(...vals,0), max=Math.max(...vals,20);
  const xs=pts.map((_,i)=>pad+i*((w-2*pad)/Math.max(pts.length-1,1)));
  const ys=pts.map(p=>h-pad-((p.idap-min)/(max-min||1))*(h-2*pad));
  const d=xs.map((x,i)=>(i?'L':'M')+x.toFixed(1)+','+ys[i].toFixed(1)).join(' ');
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><path d="${d}" fill="none" stroke="#0b6e4f" stroke-width="1.5"/></svg>`;
}

(function renderHist(){
  const ind = HIST.indice||[];
  const el = document.getElementById('histEstado');
  if(!ind.length){ el.textContent = 'Sem snapshots ainda (rode a etapa 16).'; return; }
  const ultimo = ind[ind.length-1];
  el.innerHTML = `<div style="font-size:13px;line-height:1.5">
    ${ind.length} snapshot(s) · último <code>${ultimo.t||'—'}</code>:
    Amarelo <b>${ultimo.ama||0}</b> · Laranja <b>${ultimo.lar||0}</b> ·
    Vermelho <b>${ultimo.ver||0}</b> · Roxo <b>${ultimo.rox||0}</b>
    <div style="margin-top:6px;color:var(--muted);font-size:12px">
      Contagem estadual por rodada:
      ${ind.map(x=>`${(x.t||'').slice(5,16)}→A${x.ama}`).join(' · ')}
    </div>
  </div>`;
  const ids = Object.keys(HIST.series||{});
  const linhas = ids.map(id => {
    const s = HIST.series[id];
    const d = porIdBase(id);
    const last = s[s.length-1];
    return {id, s, no: d?d.no:id, nv: last.nv, idap: last.idap};
  }).sort((a,b)=>b.idap-a.idap);
  document.getElementById('histBarragens').innerHTML = linhas.map(r =>
    `<tr data-id="${r.id}"><td><a href="barragem.html?id=${encodeURIComponent(r.id)}" style="color:var(--accent);font-weight:600;text-decoration:none">${r.no}</a></td>
     <td><span class="etq ${r.nv}">${r.nv}</span></td>
     <td>${sparkMini(r.s)}</td><td>${r.idap}</td></tr>`
  ).join('') || '<tr><td colspan="4">Nenhuma barragem acima de Verde nos snapshots.</td></tr>';
})();

function porIdBase(id){ return DADOS.find(d=>d.id===id); }

document.getElementById('semaforo').innerHTML =
  `<div class="luz" style="background:${CORES[META.semaforo]}"></div>
   <div><strong>Prontidão estadual: ${META.semaforo}</strong>
   — maior faixa vigente · ${META.total} barragens · piloto ${META.piloto||0}</div>`;

const frescorEl = document.getElementById('frescor');
(META.frescor||[]).forEach(f => {
  const h = f.idade_h;
  let cls = 'morto';
  if (f.existe && h != null && h <= 24) cls = 'ok';
  else if (f.existe && h != null && h <= 72) cls = 'velho';
  const d = document.createElement('div');
  d.className = 'chip ' + cls;
  d.textContent = f.existe
    ? `${f.arquivo.replace('.csv','')}: ${h} h (${f.mtime})`
    : `${f.arquivo}: ausente`;
  frescorEl.appendChild(d);
});

const kpis = document.getElementById('kpis');
[['Monitoradas', META.total],
 ...Object.entries(META.niveis),
 ['Piloto', META.piloto||0],
 ['Alertáveis', META.alertaveis],
 ['Não alertáveis', META.nao_alertaveis],
 ['Impacto fora da sede', META.extraterritoriais]
].forEach(([r,n]) => {
  const d = document.createElement('div');
  d.className = 'kpi';
  d.innerHTML = `<div class="n">${n}</div><div class="r">${r}</div>`;
  kpis.appendChild(d);
});

(function renderRisco(){
  const R = META.risco || {};
  const fmt = (v, s='') => (v==null || v==='') ? '—' : (typeof v==='number' ? String(v).replace('.',',')+s : v);
  const el = document.getElementById('riscoKpis');
  if (!el) return;
  [
    ['Amarelo+', R.amarelo_mais],
    ['IDAP máx.', R.idap_max],
    ['IDAP médio', R.idap_medio],
    ['Com pressão A', R.com_pressao_a],
    ['A médio', R.a_medio],
    ['B médio', R.b_medio],
    ['C médio', R.c_medio],
    ['D médio', R.d_medio],
    ['Chuva 24h máx.', fmt(R.chuva24_max,' mm')],
    ['Chuva 72h máx.', fmt(R.chuva72_max,' mm')],
    ['Prevista 24–72h máx.', fmt(R.prevista_max,' mm')],
    ['Percentil máx.', fmt(R.percentil_max)],
    ['Cemaden ativos (sede)', R.cemaden_ativos],
    ['Integrado alto (sede)', R.integrado_alto],
    ['Regras R10', R.regras_r10],
    ['Regras R11', R.regras_r11],
    ['Regras R12', R.regras_r12],
    ['CRI Alto', R.cri_alto],
    ['DPA Alto', R.dpa_alto],
    ['Rejeito / mineração', R.rejeito],
  ].forEach(([rotulo, val]) => {
    const d = document.createElement('div');
    d.className = 'kpi';
    d.innerHTML = `<div class="n">${val==null?'—':val}</div><div class="r">${rotulo}</div>`;
    el.appendChild(d);
  });
})();

document.getElementById('legenda').innerHTML = Object.entries(CORES).map(
  ([n,c]) => `<span><i style="background:${c}"></i>${n}</span>`
).join('');

const mapa = L.map('mapa').setView([-13.0, -55.8], 6);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap', maxZoom: 12
}).addTo(mapa);
L.geoJSON(MALHA, {style:{color:'#8aa0b2',weight:0.6,fillOpacity:0.04}}).addTo(mapa);
const camada = L.layerGroup().addTo(mapa);
const porId = Object.fromEntries(DADOS.map(d => [d.id, d]));

function filtrados() {
  const nv = document.getElementById('fNivel').value;
  const mu = document.getElementById('fMun').value.trim().toLowerCase();
  const og = document.getElementById('fOrg').value.trim().toLowerCase();
  const al = document.getElementById('fAl').value;
  const pi = document.getElementById('fPi').value;
  const ext = document.getElementById('fExt').value;
  const q = document.getElementById('fBusca').value.trim().toLowerCase();
  return DADOS.filter(d => {
    if (nv && d.nv !== nv) return false;
    if (mu && !(d.mu||'').toLowerCase().includes(mu)) return false;
    if (og && !(d.og||'').toLowerCase().includes(og)) return false;
    if (al && d.al !== al) return false;
    if (pi && !(d.pi === 1)) return false;
    if (ext && !(d.nex > 0)) return false;
    if (q && !(`${d.no} ${d.id}`).toLowerCase().includes(q)) return false;
    return true;
  });
}

function popup(d) {
  return `<b>${d.no}</b><br>IDAP ${d.idap}/100 — <b>${d.nv}</b><br>
  Completude ${d.comp} (${d.conf})<br>
  Dimensões A${d.pa} B${d.pb} C${d.pc} D${d.pd}<br>
  Sede: ${d.mu}<br>
  <b>Clima</b> — chuva 24h/72h: ${d.c24 ?? '—'} / ${d.c72 ?? '—'} mm<br>
  Prevista 24–72h: ${d.cprev ?? '—'} mm · percentil: ${d.pct ?? '—'}<br>
  Saturação: ${d.sat || '—'} · estágio hidro: ${d.nh || '—'}<br>
  Cemaden: ${d.cem || '—'} · integrado SIS: ${d.aint || '—'}<br>
  Aprox. espacial hidro: ${d.aprox || '—'}<br>
  Alertável: ${d.al}<br>
  Afetados: ${d.af || '—'}<br>
  ${d.reg ? 'Regras: '+d.reg+'<br>' : ''}
  <small>${(d.lac||'').slice(0,160)}</small><br>
  <a href="barragem.html?id=${encodeURIComponent(d.id)}">Abrir Barragem 360°</a>`;
}

const ORDEM_NV = {Roxo:0,Vermelho:1,Laranja:2,Amarelo:3,Verde:4};

function render() {
  const lista = filtrados().slice().sort((a,b) => b.idap - a.idap || a.no.localeCompare(b.no));
  camada.clearLayers();
  const desenho = lista.slice().sort((a,b) => (ORDEM_NV[b.nv]??9) - (ORDEM_NV[a.nv]??9));
  desenho.forEach(d => {
    if (d.la == null || d.lo == null) return;
    const critico = d.nv !== 'Verde';
    const m = L.circleMarker([d.la, d.lo], {
      radius: critico ? 10 : (d.pi ? 5 : 3.5),
      color: critico ? '#111' : (d.pi ? '#0b6e4f' : '#555'),
      weight: critico ? 2 : (d.pi ? 1.2 : 0.4),
      fillColor: CORES[d.nv] || '#888',
      fillOpacity: critico ? 0.95 : 0.55
    });
    m.bindPopup(popup(d));
    m.on('click', () => destacar(d.id));
    camada.addLayer(m);
  });

  const top = lista.slice(0, 10);
  document.getElementById('top').innerHTML = top.map(d => `<tr data-id="${d.id}">
    <td>${d.idap}</td><td><span class="etq ${d.nv}">${d.nv}</span></td>
    <td>${d.pa}</td>
    <td><a href="barragem.html?id=${encodeURIComponent(d.id)}" onclick="event.stopPropagation()"
      style="color:inherit;font-weight:600">${d.no}</a></td>
    <td>${d.mu}</td><td>${d.comp}</td>
    <td>${d.c24 ?? '—'}</td><td>${d.al}</td></tr>`).join('');

  document.getElementById('nFila').textContent = lista.length;
  document.getElementById('fila').innerHTML = lista.map(d => `<tr data-id="${d.id}">
    <td>${d.idap}</td><td><span class="etq ${d.nv}">${d.nv}</span></td>
    <td>${d.pa}</td><td>${d.pb}</td><td>${d.pc}</td><td>${d.pd}</td>
    <td title="${d.id}"><a href="barragem.html?id=${encodeURIComponent(d.id)}"
      onclick="event.stopPropagation()" style="color:inherit">${d.no}</a></td>
    <td>${d.mu}</td>
    <td title="${d.af}">${d.af ? d.af.split(' | ').length : 0}</td>
    <td>${d.c72 ?? '—'}</td><td>${d.al}</td></tr>`).join('');

  const climaEl = document.getElementById('clima');
  if (climaEl) {
    const clima = DADOS.filter(d => d.nv !== 'Verde' || (d.pa||0) > 0)
      .slice().sort((a,b) => b.idap - a.idap || (b.pa||0)-(a.pa||0));
    climaEl.innerHTML = clima.slice(0, 80).map(d => `<tr data-id="${d.id}">
      <td><span class="etq ${d.nv}">${d.nv}</span></td>
      <td>${d.idap}</td><td>${d.pa}</td>
      <td>${d.c24 ?? '—'}</td><td>${d.c72 ?? '—'}</td>
      <td>${d.cprev ?? '—'}</td>
      <td>${d.sat || '—'}</td><td>${d.cem || d.nh || '—'}</td>
      <td>${d.no}</td><td>${d.mu}</td></tr>`).join('')
      || '<tr><td colspan="10">Nenhuma barragem com pressão A ou nível acima de Verde.</td></tr>';
  }

  document.querySelectorAll('tbody tr[data-id]').forEach(tr => {
    tr.onclick = () => {
      const d = porId[tr.dataset.id];
      if (d && d.la != null) {
        mapa.setView([d.la, d.lo], 11);
        destacar(d.id);
      }
    };
  });
}

function destacar(id) {
  document.querySelectorAll('tbody tr').forEach(tr => {
    tr.style.background = tr.dataset.id === id ? '#e7f3ec' : '';
  });
}

document.getElementById('btnFiltrar').onclick = render;
document.getElementById('btnLimpar').onclick = () => {
  ['fNivel','fMun','fOrg','fAl','fPi','fExt','fBusca'].forEach(id => {
    const el = document.getElementById(id); el.value = '';
  });
  render();
  mapa.setView([-13.0, -55.8], 6);
};
const btnAm = document.getElementById('btnAmarelo');
if (btnAm) btnAm.onclick = () => {
  const pts = DADOS.filter(d => d.nv !== 'Verde' && d.la != null && d.lo != null);
  if (!pts.length) { alert('Nenhuma barragem Amarelo+ com coordenada nesta rodada.'); return; }
  document.getElementById('fNivel').value = '';
  document.getElementById('fPi').value = '';
  document.getElementById('fMun').value = '';
  render();
  camada.clearLayers();
  pts.forEach(d => {
    const m = L.circleMarker([d.la, d.lo], {
      radius: 12, color:'#111', weight:2.5,
      fillColor: CORES[d.nv], fillOpacity:0.95
    });
    m.bindPopup(popup(d));
    camada.addLayer(m);
  });
  mapa.fitBounds(L.latLngBounds(pts.map(d => [d.la, d.lo])).pad(0.4));
};
['fNivel','fAl','fPi','fExt'].forEach(id => document.getElementById(id).onchange = render);
['fMun','fOrg','fBusca'].forEach(id => {
  document.getElementById(id).addEventListener('keydown', e => { if (e.key==='Enter') render(); });
});
render();
(function destacarCriticosInicial() {
  const pts = DADOS.filter(d => d.nv !== 'Verde' && d.la != null);
  if (pts.length && pts.length <= 40) {
    setTimeout(() => mapa.fitBounds(L.latLngBounds(pts.map(d => [d.la, d.lo])).pad(0.55)), 350);
  }
})();
</script>
</body>
</html>
"""


def main() -> None:
    painel07 = _carregar_07()
    registros, meta = montar_registros()
    hist = ler_historico_comando()
    print(f"Comando estadual — {meta['total']} barragens · semáforo {meta['semaforo']}")
    print(f"  histórico: {len(hist['indice'])} snapshots · {len(hist['series'])} séries Amarelo+")

    malha = json.loads(
        (comum.DADOS_TRATADOS / "ibge_malha_municipios_mt_simplificada.geojson").read_text(
            encoding="utf-8"
        )
    )
    simplificada = painel07.simplificar_malha(malha)

    # Remove None para JSON mais enxuto (JS trata undefined via ??)
    for r in registros:
        for k in list(r):
            if r[k] is None:
                del r[k]

    dados_json = json.dumps(registros, ensure_ascii=False, separators=(",", ":"))
    malha_json = json.dumps(simplificada, ensure_ascii=False, separators=(",", ":"))
    meta_json = json.dumps(meta, ensure_ascii=False, separators=(",", ":"))
    hist_json = json.dumps(hist, ensure_ascii=False, separators=(",", ":"))
    print(f"  dados {len(dados_json)/1024:.0f} KB | malha {len(malha_json)/1024:.0f} KB")

    html = (
        MODELO.replace("__DADOS__", dados_json)
        .replace("__MALHA__", malha_json)
        .replace("__META__", meta_json)
        .replace("__HIST__", hist_json)
        .replace("__GERADO__", meta["gerado"])
        .replace("__INSTANTE__", meta["instante_idap"] or "—")
        .replace("__DATA_HIDRO__", meta["data_hidro"] or "—")
    )

    SAIDA.mkdir(parents=True, exist_ok=True)
    destino = SAIDA / "index.html"
    destino.write_text(html, encoding="utf-8")
    # Cópia nomeada para link estável
    (SAIDA / "comando.html").write_text(html, encoding="utf-8")
    print(f"  gravado {destino.relative_to(comum.RAIZ)}")
    print(f"  gravado painel/comando.html")


if __name__ == "__main__":
    main()
