"""Tela 3 — Barragem 360° (docs/07-telas.md §7.3).

Uma página SPA: busca por id/nome e monta a ficha completa com o que já existe
no cadastro + IDAP + hidro + histórico. Sem sensores/mancha oficial ainda.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path
from typing import Any

import comum
from idap.impacto_sanitario import perfil_de

SAIDA = comum.RAIZ / "painel"


def ler_csv(nome: str) -> list[dict[str, Any]]:
    caminho = comum.DADOS_TRATADOS / nome
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def num(valor: Any) -> float | None:
    if valor in (None, "", "None"):
        return None
    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return None


def ler_historico_por_barragem(limite_snapshots: int = 30) -> dict[str, list[dict[str, Any]]]:
    """Série IDAP por barragem a partir dos snapshots append-only."""
    pasta = comum.DADOS_TRATADOS / "historico_idap"
    indice_path = pasta / "indice.csv"
    if not indice_path.exists():
        return {}
    with indice_path.open(encoding="utf-8-sig", newline="") as arquivo:
        indice = list(csv.DictReader(arquivo, delimiter=";"))
    series: dict[str, list[dict[str, Any]]] = {}
    for linha in indice[-limite_snapshots:]:
        arq = pasta / (linha.get("arquivo") or "")
        if not arq.exists():
            continue
        instante = linha.get("instante") or ""
        with arq.open(encoding="utf-8-sig", newline="") as arquivo:
            for r in csv.DictReader(arquivo, delimiter=";"):
                bid = (r.get("id_snisb") or "").strip()
                if not bid:
                    continue
                series.setdefault(bid, []).append(
                    {
                        "t": instante,
                        "idap": int(r["idap"]) if str(r.get("idap", "")).isdigit() else None,
                        "nv": r.get("nivel") or "",
                    }
                )
    return series


def _rotulo_regulada(valor: object, texto_pnsb: object = None) -> str:
    txt = str(texto_pnsb or "").strip()
    if txt and txt.lower() not in ("nan", "none", ""):
        return txt
    try:
        n = int(float(str(valor).replace(",", ".")))
    except (TypeError, ValueError):
        s = str(valor or "").strip()
        return "—" if not s or s.lower() in ("nan", "none") else s
    return {1: "Sim (regulada PNSB)", 2: "Não regulada PNSB", 3: "Não classificada"}.get(
        n, str(valor)
    )


def montar_registros() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    inv = {r["id_snisb"]: r for r in ler_csv("inventario_barragens_mt.csv")}
    idap = {r["id_snisb"]: r for r in ler_csv("idap_estadual_mt.csv")}
    hidro = {r["id_snisb"]: r for r in ler_csv("hidro_barragens_mt.csv")}
    piloto = {r["id_snisb"] for r in ler_csv("piloto_manso_cuiaba.csv")}
    alertab = {r["id_snisb"]: r for r in ler_csv("alertabilidade_piloto.csv")}
    hist = ler_historico_por_barragem()

    saida: list[dict[str, Any]] = []
    for bid, r in inv.items():
        i = idap.get(bid, {})
        h = hidro.get(bid, {})
        a = alertab.get(bid, {})
        la, lo = num(r.get("latitude")), num(r.get("longitude"))
        perfil = perfil_de(r.get("uso_principal"), r.get("orgao_fiscalizador"))
        afetados = [
            p.strip()
            for p in (i.get("municipios_potencialmente_afetados") or "").split("|")
            if p.strip()
        ]
        saida.append(
            {
                "id": bid,
                "no": r.get("nome") or "",
                "mu": r.get("municipio") or "",
                "emp": r.get("empreendedor") or "",
                "og": r.get("orgao_fiscalizador") or "",
                "uso": r.get("uso_principal") or "",
                "fase": r.get("fase_de_vida") or "",
                "alt": num(r.get("altura_m")),
                "vol": num(r.get("capacidade_hm3")),
                "cri": r.get("categoria_risco") or "",
                "dpa": r.get("dano_potencial_associado") or "",
                "cls": r.get("classe_cnrh") or r.get("classe") or "",
                "pae": r.get("possui_pae") or "",
                "reg": _rotulo_regulada(
                    r.get("indicador_regulada"), r.get("regulada_pelo_pnsb")
                ),
                "aut": r.get("barragem_autuada") or "",
                "insp": r.get("data_ultima_inspecao") or "",
                "fisc": r.get("data_ultima_fiscalizacao") or "",
                "otto": r.get("codigo_trecho_curso_dagua") or "",
                "curso": r.get("curso_dagua") or r.get("corpo_hidrico") or "",
                "la": round(la, 5) if la is not None else None,
                "lo": round(lo, 5) if lo is not None else None,
                "nem": r.get("sigbm_nivel_emergencia") or r.get("nivel_de_perigo") or "",
                "dce": r.get("sigbm_status_dce") or "",
                "met": r.get("sigbm_metodo_construtivo") or "",
                "altm": r.get("sigbm_tipo_alteamento") or "",
                "min": r.get("sigbm_minerio") or "",
                "popj": num(r.get("sigbm_populacao_jusante")),
                "popa": num(r.get("sigbm_pessoas_afetadas")),
                "idap": int(i["idap"]) if str(i.get("idap", "")).isdigit() else None,
                "nv": i.get("nivel") or "",
                "comp": i.get("completude") or "",
                "conf": i.get("confiabilidade") or "",
                "pa": int(i.get("pontos_a") or 0) if i else 0,
                "pb": int(i.get("pontos_b") or 0) if i else 0,
                "pc": int(i.get("pontos_c") or 0) if i else 0,
                "pd": int(i.get("pontos_d") or 0) if i else 0,
                "regras": i.get("regras_disparadas") or "",
                "lac": i.get("lacunas") or "",
                "af": afetados,
                "ind": [
                    p.strip()
                    for p in (i.get("municipios_posicao_indeterminada") or "").split("|")
                    if p.strip()
                ],
                "al": i.get("alertavel") or a.get("alertavel") or "não avaliado",
                "c24": num(h.get("chuva_24h_mm")),
                "c72": num(h.get("chuva_72h_mm")),
                "sat": h.get("saturacao_antecedente") or "",
                "nh": h.get("nivel_alerta_hidro") or "",
                "aprox": h.get("aproximacao_espacial") or "",
                "dh": h.get("data_referencia") or "",
                "pi": 1 if bid in piloto else 0,
                "perfil": perfil.codigo,
                "hist": hist.get(bid, []),
            }
        )
    saida.sort(key=lambda x: ((x.get("nv") or "Verde"), -(x.get("idap") or 0), x["no"]))
    meta = {
        "gerado": dt.datetime.now().strftime("%d/%m/%Y %H:%M"),
        "total": len(saida),
        "com_hist": sum(1 for r in saida if r["hist"]),
    }
    return saida, meta


MODELO = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Barragem 360° — VIGIBARRAGENS–MT</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root{--ink:#15202b;--muted:#5a6b7a;--paper:#e9eef2;--card:#fff;--line:#d0d8e0;--accent:#0b6e4f;
--roxo:#5b2c6f;--verm:#c0392b;--lar:#d35400;--ama:#b7950b;--verd:#1e8449}
*{box-sizing:border-box}
body{margin:0;font-family:"Source Sans 3",system-ui,sans-serif;color:var(--ink);
background:radial-gradient(ellipse at 10% 0%,#d7e8df,transparent 40%),var(--paper);font-size:14px}
header{padding:18px 22px 12px;border-bottom:1px solid var(--line);background:rgba(255,255,255,.92);
display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:flex-end}
.marca{font-family:"Fraunces",Georgia,serif;font-size:1.55rem;margin:0 0 4px;font-weight:600}
header p{margin:0;color:var(--muted);max-width:38rem;line-height:1.4;font-size:13px}
nav a{color:var(--accent);font-weight:600;font-size:13px;margin-left:10px;text-decoration:none}
main{padding:14px 22px 40px;max-width:1200px;margin:0 auto}
.busca{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}
.busca input{flex:1;min-width:220px;padding:9px 10px;border:1px solid var(--line);font:inherit}
.busca button{padding:9px 14px;border:0;background:var(--accent);color:#fff;font:inherit;font-weight:600;cursor:pointer}
.sug{background:var(--card);border:1px solid var(--line);max-height:180px;overflow:auto;margin-top:-10px;margin-bottom:14px}
.sug div{padding:8px 10px;cursor:pointer;border-bottom:1px solid #eef1f5;font-size:13px}
.sug div:hover{background:#f3f8f5}
.etq{display:inline-block;padding:2px 8px;color:#fff;font-size:12px;font-weight:600}
.Roxo{background:var(--roxo)}.Vermelho{background:var(--verm)}.Laranja{background:var(--lar)}
.Amarelo{background:var(--ama)}.Verde{background:var(--verd)}
.grade{display:grid;grid-template-columns:1.1fr .9fr;gap:12px}
@media(max-width:900px){.grade{grid-template-columns:1fr}}
.bloco{background:var(--card);border:1px solid var(--line);padding:12px 14px;margin-bottom:12px}
.bloco h2{margin:0 0 8px;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.bloco h1{margin:0 0 6px;font-family:"Fraunces",Georgia,serif;font-size:1.45rem;font-weight:600}
.kv{display:grid;grid-template-columns:140px 1fr;gap:4px 10px;font-size:13px}
.kv span:first-child{color:var(--muted)}
.bars{display:grid;gap:6px;margin-top:8px}
.bar{display:grid;grid-template-columns:28px 1fr 36px;gap:8px;align-items:center;font-size:12px}
.bar i{display:block;height:10px;background:#c5d4c8}
.bar i b{display:block;height:100%;background:var(--accent)}
#mapa{height:280px;border:1px solid var(--line)}
.spark{height:56px;width:100%;display:block}
.lista{font-size:13px;line-height:1.5}
.links a{margin-right:12px;color:var(--accent);font-weight:600;font-size:13px;text-decoration:none}
.aviso{font-size:12px;color:var(--muted);line-height:1.45;margin-top:8px}
.vazio{padding:40px;text-align:center;color:var(--muted)}
</style>
</head>
<body>
<header>
  <div>
    <h1 class="marca">Barragem 360°</h1>
    <p>Ficha operacional por estrutura — cadastro, IDAP, hidro e histórico. Gerado __GERADO__.</p>
  </div>
  <nav>
    <a href="index.html">Comando</a>
    <a href="simulacao.html">Simulação</a>
    <a href="alertas.html">Alertas</a>
    <a href="piloto_manso_cuiaba.html">Eixo Manso–Cuiabá</a>
  </nav>
</header>
<main>
  <div class="busca">
    <input id="q" type="search" placeholder="Nome, id SNISB, município ou empreendedor" autocomplete="off">
    <button type="button" id="btn">Abrir</button>
  </div>
  <div class="sug" id="sug" style="display:none"></div>
  <div id="ficha" class="vazio">Busque uma barragem ou abra com <code>?id=SNISB</code>.</div>
</main>
<script>
const DADOS = __DADOS__;
const CORES = {Roxo:'#5b2c6f',Vermelho:'#c0392b',Laranja:'#d35400',Amarelo:'#b7950b',Verde:'#1e8449'};
const porId = Object.fromEntries(DADOS.map(d => [d.id, d]));
let mapa, marcador;

function fmt(n,c=1){ if(n==null||Number.isNaN(n)) return '—'; return n.toLocaleString('pt-BR',{maximumFractionDigits:c}); }
function esc(s){ return String(s??'').replace(/[&<>"']/g, m=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[m])); }

function buscar(termo){
  const t = (termo||'').trim().toLowerCase();
  if(!t) return [];
  return DADOS.filter(d => (`${d.id} ${d.no} ${d.mu} ${d.emp}`).toLowerCase().includes(t)).slice(0,12);
}

function sparkSVG(hist){
  if(!hist || hist.length < 1) return '<p class="aviso">Sem snapshots de histórico ainda.</p>';
  const vals = hist.map(h => h.idap).filter(v => v!=null);
  if(!vals.length) return '<p class="aviso">Histórico sem IDAP numérico.</p>';
  const w=320,h=56,pad=4;
  const min=Math.min(...vals,0), max=Math.max(...vals,100);
  const xs = hist.map((_,i)=> pad + i*((w-2*pad)/Math.max(hist.length-1,1)));
  const ys = hist.map(p => {
    const v = p.idap==null ? min : p.idap;
    return h-pad - ((v-min)/(max-min||1))*(h-2*pad);
  });
  let d = xs.map((x,i)=> (i?'L':'M')+x.toFixed(1)+','+ys[i].toFixed(1)).join(' ');
  const last = hist[hist.length-1];
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" role="img" aria-label="Série IDAP">
    <path d="${d}" fill="none" stroke="#0b6e4f" stroke-width="2"/>
    <circle cx="${xs.at(-1)}" cy="${ys.at(-1)}" r="3.5" fill="${CORES[last.nv]||'#0b6e4f'}"/>
  </svg>
  <div class="aviso">${hist.length} ponto(s) · último IDAP ${last.idap ?? '—'} (${esc(last.nv)}) · ${esc((last.t||'').slice(0,19))}</div>`;
}

function bar(rotulo, pts, max){
  const pct = Math.min(100, Math.round(100*pts/Math.max(max,1)));
  return `<div class="bar"><span>${rotulo}</span><i><b style="width:${pct}%"></b></i><span>${pts}</span></div>`;
}

function render(d){
  if(!d){ document.getElementById('ficha').innerHTML = '<div class="vazio">Barragem não encontrada.</div>'; return; }
  const url = new URL(location.href); url.searchParams.set('id', d.id); history.replaceState(null,'',url);
  document.title = `${d.no} — Barragem 360°`;
  const nv = d.nv || 'Verde';
  document.getElementById('ficha').innerHTML = `
  <div class="bloco">
    <h2>Identificação</h2>
    <h1>${esc(d.no)}</h1>
    <div style="margin-bottom:8px">
      <span class="etq ${nv}">${nv}</span>
      <strong style="margin-left:8px">IDAP ${d.idap ?? '—'}/100</strong>
      ${d.pi ? ' · eixo Manso–Cuiabá' : ''}
      ${d.perfil==='rejeito' ? ' · <strong style="color:#9a3412">rejeito</strong>' : ''}
    </div>
    <div class="kv">
      <span>SNISB</span><span>${esc(d.id)}</span>
      <span>Município sede</span><span>${esc(d.mu)}</span>
      <span>Empreendedor</span><span>${esc(d.emp)||'—'}</span>
      <span>Órgão</span><span>${esc(d.og)||'—'}</span>
      <span>Uso</span><span>${esc(d.uso)||'—'}</span>
      <span>Fase</span><span>${esc(d.fase)||'—'}</span>
      <span>Altura / volume</span><span>${fmt(d.alt,1)} m · ${fmt(d.vol,2)} hm³</span>
      <span>Otto / curso</span><span>${esc(d.otto)||'—'} · ${esc(d.curso)||'—'}</span>
    </div>
    <p class="links" style="margin-top:10px">
      <a href="simulacao.html?id=${encodeURIComponent(d.id)}">Simulação de cenário</a>
      <a href="alertas.html">Fila de alertas</a>
      <a href="ficha_rapida.html">Ficha rápida</a>
      <a href="index.html">Voltar ao comando</a>
    </p>
  </div>
  <div class="grade">
    <div>
      <div class="bloco">
        <h2>Classificação e fiscalização</h2>
        <div class="kv">
          <span>CRI / DPA</span><span>${esc(d.cri)||'—'} / ${esc(d.dpa)||'—'}</span>
          <span>Classe</span><span>${esc(d.cls)||'—'}</span>
          <span>PAE</span><span>${esc(d.pae)||'—'}</span>
          <span>Regulada PNSB</span><span>${esc(d.reg)||'—'}</span>
          <span>Autuada</span><span>${esc(d.aut)||'—'}</span>
          <span>Última inspeção</span><span>${esc(d.insp)||'—'}</span>
          <span>Última fiscalização</span><span>${esc(d.fisc)||'—'}</span>
          <span>Nível emergência</span><span>${esc(d.nem)||'—'}</span>
          <span>Status DCE</span><span>${esc(d.dce)||'—'}</span>
          <span>Método / alteamento</span><span>${esc(d.met)||'—'} / ${esc(d.altm)||'—'}</span>
          <span>Minério</span><span>${esc(d.min)||'—'}</span>
          <span>Pop. SIGBM</span><span>jusante ${fmt(d.popj,0)} · afetadas ${fmt(d.popa,0)}</span>
        </div>
      </div>
      <div class="bloco">
        <h2>IDAP detalhado</h2>
        <div>Completude ${esc(d.comp)} · confiabilidade ${esc(d.conf)} · alertável: <b>${esc(d.al)}</b></div>
        <div class="bars">
          ${bar('A', d.pa||0, 30)}${bar('B', d.pb||0, 30)}${bar('C', d.pc||0, 25)}${bar('D', d.pd||0, 15)}
        </div>
        <p class="aviso"><b>Regras:</b> ${esc(d.regras)||'—'}</p>
        <p class="aviso"><b>Lacunas:</b> ${esc(d.lac)||'—'}</p>
      </div>
      <div class="bloco">
        <h2>Impacto territorial (Otto)</h2>
        <div class="lista"><b>Potencialmente afetados:</b><br>${(d.af||[]).map(esc).join(' · ') || '—'}</div>
        <div class="lista" style="margin-top:8px"><b>Posição indeterminada (CONTEM):</b><br>${(d.ind||[]).map(esc).join(' · ') || '—'}</div>
        <p class="aviso">Proxy de drenagem — não é mancha de inundação do PAE.</p>
      </div>
    </div>
    <div>
      <div class="bloco">
        <h2>Localização</h2>
        <div id="mapa"></div>
      </div>
      <div class="bloco">
        <h2>Hidro SisClima/TITAN</h2>
        <div class="kv">
          <span>Chuva 24h / 72h</span><span>${fmt(d.c24,1)} / ${fmt(d.c72,1)} mm</span>
          <span>Saturação</span><span>${esc(d.sat)||'—'}</span>
          <span>Nível hidro</span><span>${esc(d.nh)||'—'}</span>
          <span>Aproximação</span><span>${esc(d.aprox)||'—'}</span>
          <span>Referência</span><span>${esc(d.dh)||'—'}</span>
        </div>
      </div>
      <div class="bloco">
        <h2>Histórico IDAP</h2>
        ${sparkSVG(d.hist)}
      </div>
    </div>
  </div>`;

  if(mapa){ mapa.remove(); mapa=null; }
  if(d.la!=null && d.lo!=null){
    mapa = L.map('mapa').setView([d.la,d.lo], 10);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'&copy; OSM',maxZoom:14}).addTo(mapa);
    L.circleMarker([d.la,d.lo],{
      radius:10, color:'#111', weight:2, fillColor:CORES[nv]||'#888', fillOpacity:0.95
    }).bindPopup(`<b>${esc(d.no)}</b><br>IDAP ${d.idap??'—'}`).addTo(mapa);
    setTimeout(()=>mapa.invalidateSize(), 80);
  } else {
    document.getElementById('mapa').innerHTML = '<p class="aviso" style="padding:12px">Sem coordenada no cadastro.</p>';
  }
}

const sug = document.getElementById('sug');
const q = document.getElementById('q');
function mostrarSug(){
  const L = buscar(q.value);
  if(!L.length){ sug.style.display='none'; return; }
  sug.style.display='block';
  sug.innerHTML = L.map(d => `<div data-id="${d.id}"><b>${esc(d.no)}</b> · ${esc(d.mu)} · SNISB ${d.id}
    ${d.nv?` · <span class="etq ${d.nv}">${d.nv}</span>`:''}</div>`).join('');
  sug.querySelectorAll('div').forEach(el => el.onclick = () => {
    sug.style.display='none'; q.value = porId[el.dataset.id].no; render(porId[el.dataset.id]);
  });
}
q.addEventListener('input', mostrarSug);
q.addEventListener('keydown', e => {
  if(e.key==='Enter'){ e.preventDefault(); const L=buscar(q.value); if(L[0]){ sug.style.display='none'; render(L[0]); } }
});
document.getElementById('btn').onclick = () => { const L=buscar(q.value); if(L[0]) render(L[0]); };

const idUrl = new URLSearchParams(location.search).get('id');
if(idUrl && porId[idUrl]){ q.value = porId[idUrl].no; render(porId[idUrl]); }
else {
  const am = DADOS.find(d => d.nv && d.nv!=='Verde') || DADOS[0];
  if(am){ q.value = am.no; render(am); }
}
</script>
</body>
</html>
"""


def main() -> None:
    dados, meta = montar_registros()
    print(f"Barragem 360° — {meta['total']} fichas · {meta['com_hist']} com histórico")
    for r in dados:
        for k in list(r):
            if r[k] is None:
                del r[k]
            elif r[k] == [] and k in {"hist", "af", "ind"}:
                pass
    html = (
        MODELO.replace(
            "__DADOS__",
            json.dumps(dados, ensure_ascii=False, separators=(",", ":")),
        ).replace("__GERADO__", meta["gerado"])
    )
    SAIDA.mkdir(parents=True, exist_ok=True)
    destino = SAIDA / "barragem.html"
    destino.write_text(html, encoding="utf-8")
    print(f"  gravado {destino.relative_to(comum.RAIZ)} ({destino.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
