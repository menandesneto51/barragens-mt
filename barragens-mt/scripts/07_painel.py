"""Gera o painel de monitoramento interativo das barragens de Mato Grosso.

Produz um unico arquivo HTML autocontido (painel/index.html) com os dados embutidos:
abre com duplo clique, sem servidor, e pode ser enviado por e-mail ou publicado como
pagina estatica. Leaflet e Chart.js vem de CDN.

O painel tem mapa filtravel, indicadores, graficos por categoria de risco, dano
potencial, orgao fiscalizador e uso principal, fila de priorizacao de fiscalizacao e
tabela pesquisavel com exportacao para CSV.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
from typing import Any

import comum

SAIDA = comum.RAIZ / "painel"

# Chaves curtas reduzem o tamanho do JSON embutido em cerca de 40%.
CAMPOS = {
    "id_snisb": "id",
    "nome": "no",
    "municipio": "mu",
    "mesorregiao": "me",
    "orgao_fiscalizador": "og",
    "empreendedor": "em",
    "tipo_empreendedor": "te",
    "latitude": "la",
    "longitude": "lo",
    "categoria_risco": "cri",
    "dano_potencial_associado": "dpa",
    "classe_cnrh": "cl",
    "prioridade_fiscalizacao": "pr",
    "uso_principal": "us",
    "tipo_material": "tm",
    "altura_m": "al",
    "capacidade_hm3": "cap",
    "comprimento_coroamento_m": "cc",
    "fase_de_vida": "fa",
    "regulada_pelo_pnsb": "pn",
    "possui_pae": "pae",
    "possui_plano_de_seguranca": "pse",
    "possui_revisao_periodica": "prv",
    "completude_cadastro": "co",
    "data_ultima_inspecao": "din",
    "data_ultima_fiscalizacao": "dfi",
    "data_ultima_autuacao": "dau",
    "barragem_autuada": "au",
    "corpo_hidrico": "ch",
    "regiao_hidrografica": "rh",
    "nivel_de_perigo": "np",
    "sigbm_metodo_construtivo": "smc",
    "sigbm_tipo_alteamento": "sta",
    "sigbm_nivel_emergencia": "sne",
    "sigbm_pessoas_afetadas": "spa",
}

NUMERICOS = {"la", "lo", "al", "cap", "cc", "pr", "spa"}


def ler_inventario() -> list[dict[str, Any]]:
    caminho = comum.DADOS_TRATADOS / "inventario_barragens_mt.csv"
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def compactar(barragens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compactadas = []
    for origem in barragens:
        registro: dict[str, Any] = {}
        for campo, apelido in CAMPOS.items():
            valor = origem.get(campo)
            if valor in (None, "", "None"):
                continue
            if apelido in NUMERICOS:
                try:
                    numero = float(valor)
                except (TypeError, ValueError):
                    continue
                registro[apelido] = round(numero, 5)
            else:
                registro[apelido] = valor
        compactadas.append(registro)
    return compactadas


def simplificar_malha(geojson: dict[str, Any], casas: int = 3) -> dict[str, Any]:
    """Enxuga a malha municipal ja generalizada do IBGE antes de embutir no HTML.

    Arredondar para 3 casas decimais equivale a cerca de 110 m no terreno, resolucao
    mais que suficiente para um mapa estadual, e permite descartar vertices que se
    tornam coincidentes. Tambem remove as propriedades, que o painel nao usa.
    """

    def limpar(anel: list[list[float]]) -> list[list[float]]:
        saida: list[list[float]] = []
        for x, y in anel:
            ponto = [round(x, casas), round(y, casas)]
            if not saida or saida[-1] != ponto:
                saida.append(ponto)
        return saida

    feicoes = []
    for feicao in geojson.get("features", []):
        geometria = feicao.get("geometry") or {}
        tipo = geometria.get("type")
        coordenadas = geometria.get("coordinates", [])
        if tipo == "Polygon":
            novas = [limpar(anel) for anel in coordenadas]
            novas = [anel for anel in novas if len(anel) >= 4]
        elif tipo == "MultiPolygon":
            novas = []
            for parte in coordenadas:
                aneis = [limpar(anel) for anel in parte]
                aneis = [anel for anel in aneis if len(anel) >= 4]
                if aneis:
                    novas.append(aneis)
        else:
            continue
        if not novas:
            continue
        feicoes.append(
            {
                "type": "Feature",
                "properties": {},
                "geometry": {"type": tipo, "coordinates": novas},
            }
        )
    return {"type": "FeatureCollection", "features": feicoes}


MODELO = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Inventário / fiscalização — VIGIBARRAGENS–MT</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root{
    --tinta:#12263a; --tinta-2:#1d3a57; --papel:#f4f6f8; --branco:#fff;
    --linha:#dde3ea; --texto:#243b53; --suave:#627d98;
    --alto:#d7191c; --medio:#f08c25; --baixo:#f5c518; --nc:#7b8794; --na:#c3ccd6;
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:"Segoe UI",system-ui,-apple-system,sans-serif;
       background:var(--papel);color:var(--texto);font-size:14px}
  header{background:linear-gradient(100deg,var(--tinta),var(--tinta-2));color:#fff;
         padding:16px 24px;display:flex;justify-content:space-between;align-items:center;
         flex-wrap:wrap;gap:12px}
  header h1{margin:0;font-size:19px;font-weight:600;letter-spacing:.2px}
  header p{margin:3px 0 0;font-size:12px;opacity:.8}
  .selo{background:rgba(255,255,255,.14);padding:6px 14px;border-radius:20px;
        font-size:12px;text-align:right;line-height:1.5}
  main{padding:18px 24px 40px;max-width:1800px;margin:0 auto}
  .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(158px,1fr));gap:12px;margin-bottom:16px}
  .kpi{background:var(--branco);border:1px solid var(--linha);border-radius:10px;padding:13px 15px;
       border-left:4px solid var(--tinta-2)}
  .kpi.risco{border-left-color:var(--alto)} .kpi.atencao{border-left-color:var(--medio)}
  .kpi.ok{border-left-color:#2e9e6b}
  .kpi .n{font-size:26px;font-weight:700;color:var(--tinta);line-height:1.1}
  .kpi .r{font-size:11.5px;color:var(--suave);margin-top:4px;line-height:1.35}
  .filtros{background:var(--branco);border:1px solid var(--linha);border-radius:10px;
           padding:14px 16px;margin-bottom:16px;display:grid;
           grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;align-items:end}
  .filtros label{display:block;font-size:11px;font-weight:600;color:var(--suave);
                 text-transform:uppercase;letter-spacing:.4px;margin-bottom:5px}
  select,input[type=text]{width:100%;padding:7px 9px;border:1px solid var(--linha);
       border-radius:6px;font-size:13px;background:#fff;color:var(--texto);font-family:inherit}
  button{padding:8px 15px;border:0;border-radius:6px;background:var(--tinta-2);color:#fff;
         font-size:13px;cursor:pointer;font-family:inherit;font-weight:500}
  button:hover{background:var(--tinta)}
  button.limpo{background:#e4e9ef;color:var(--texto)}
  button.limpo:hover{background:#d3dae2}
  .grade{display:grid;grid-template-columns:1.35fr 1fr;gap:16px;margin-bottom:16px}
  @media(max-width:1180px){.grade{grid-template-columns:1fr}}
  .cartao{background:var(--branco);border:1px solid var(--linha);border-radius:10px;overflow:hidden}
  .cartao h2{margin:0;padding:11px 16px;font-size:13px;font-weight:600;
             border-bottom:1px solid var(--linha);background:#fafbfc;
             text-transform:uppercase;letter-spacing:.4px;color:var(--suave)}
  .cartao .corpo{padding:14px 16px}
  #mapa{height:600px}
  .graficos{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  @media(max-width:640px){.graficos{grid-template-columns:1fr}}
  .cx{position:relative;height:196px}
  .cx-alta{height:290px}
  table{width:100%;border-collapse:collapse;font-size:12.5px}
  th,td{padding:7px 10px;text-align:left;border-bottom:1px solid #eef1f5;white-space:nowrap}
  th{background:#fafbfc;font-weight:600;color:var(--suave);font-size:11px;
     text-transform:uppercase;letter-spacing:.3px;cursor:pointer;position:sticky;top:0;z-index:2}
  th:hover{color:var(--tinta)}
  tbody tr:hover{background:#f7f9fb;cursor:pointer}
  .rolagem{max-height:460px;overflow:auto}
  .etq{display:inline-block;padding:2px 8px;border-radius:11px;font-size:11px;
       font-weight:600;color:#fff;white-space:nowrap}
  .num{text-align:right;font-variant-numeric:tabular-nums}
  .barra-legenda{display:flex;gap:14px;flex-wrap:wrap;padding:0 16px 12px;font-size:11.5px;color:var(--suave)}
  .barra-legenda span{display:flex;align-items:center;gap:5px}
  .bolinha{width:11px;height:11px;border-radius:50%;border:1px solid rgba(0,0,0,.3)}
  .rodape{margin-top:22px;padding-top:14px;border-top:1px solid var(--linha);
          font-size:11.5px;color:var(--suave);line-height:1.7}
  .leaflet-popup-content{font-size:12.5px;line-height:1.6;margin:11px 13px}
  .leaflet-popup-content b{color:var(--tinta)}
  .vazio{padding:26px;text-align:center;color:var(--suave)}
</style>
</head>
<body>
<header>
  <div>
    <h1>Inventário / fiscalização — Mato Grosso</h1>
    <p>Cadastro SNISB/SIGBM · priorização CRI×DPA ·
    <a href="index.html" style="color:#9fd3ff">← Comando estadual (IDAP)</a></p>
  </div>
  <div class="selo">
    <div><b id="selo-total">—</b> barragens cadastradas</div>
    <div>Extração dos dados: __DATA__</div>
  </div>
</header>

<main>
  <div class="kpis" id="kpis"></div>

  <div class="filtros">
    <div><label>Município</label><select id="f-municipio"></select></div>
    <div><label>Órgão fiscalizador</label><select id="f-orgao"></select></div>
    <div><label>Categoria de risco</label><select id="f-cri"></select></div>
    <div><label>Dano potencial</label><select id="f-dpa"></select></div>
    <div><label>Uso principal</label><select id="f-uso"></select></div>
    <div><label>Regulada pela PNSB</label><select id="f-pnsb"></select></div>
    <div><label>Buscar por nome ou empreendedor</label><input type="text" id="f-busca" placeholder="Ex.: Manso"></div>
    <div style="display:flex;gap:8px">
      <button id="b-exportar">Exportar CSV</button>
      <button id="b-limpar" class="limpo">Limpar</button>
    </div>
  </div>

  <div class="grade">
    <div class="cartao">
      <h2>Distribuição territorial</h2>
      <div class="barra-legenda" id="legenda-mapa"></div>
      <div id="mapa"></div>
    </div>
    <div style="display:flex;flex-direction:column;gap:16px">
      <div class="cartao">
        <h2>Classificação de risco</h2>
        <div class="corpo graficos">
          <div class="cx"><canvas id="g-cri"></canvas></div>
          <div class="cx"><canvas id="g-dpa"></canvas></div>
        </div>
      </div>
      <div class="cartao">
        <h2>Órgão fiscalizador e uso principal</h2>
        <div class="corpo graficos">
          <div class="cx"><canvas id="g-orgao"></canvas></div>
          <div class="cx"><canvas id="g-uso"></canvas></div>
        </div>
      </div>
    </div>
  </div>

  <div class="grade">
    <div class="cartao">
      <h2>Municípios com maior número de barragens</h2>
      <div class="corpo"><div class="cx cx-alta"><canvas id="g-municipio"></canvas></div></div>
    </div>
    <div class="cartao">
      <h2>Instrumentos de segurança exigidos pela PNSB</h2>
      <div class="corpo"><div class="cx cx-alta"><canvas id="g-conformidade"></canvas></div></div>
    </div>
  </div>

  <div class="cartao" style="margin-bottom:16px">
    <h2>Fila de priorização — maior risco combinado (CRI × DPA)</h2>
    <div class="rolagem" id="area-prioridade"></div>
  </div>

  <div class="cartao">
    <h2>Inventário detalhado — <span id="conta-tabela">0</span> barragens</h2>
    <div class="rolagem" id="area-tabela"></div>
  </div>

  <div class="rodape">
    <b>Fontes:</b> SNISB — Sistema Nacional de Informações sobre Segurança de Barragens (ANA),
    incluindo o serviço geoespacial do SNIRH e o modelo do painel público;
    SIGBM — Sistema Integrado de Gestão de Barragens de Mineração (ANM); malha territorial do IBGE.<br>
    <b>Notas:</b> a capacidade do reservatório é apresentada em hm³ (milhões de m³).
    A classe CNRH resulta do cruzamento entre Categoria de Risco e Dano Potencial Associado,
    conforme a Resolução CNRH nº 143/2012. Barragens sem classificação não entram na fila de priorização.
  </div>
</main>

<script>
const DADOS = __DADOS__;
const MALHA = __MALHA__;

const CORES_CRI = {"Alto":"#d7191c","Médio":"#f08c25","Baixo":"#f5c518",
                   "Não Classificado":"#7b8794","Não se Aplica":"#c3ccd6"};
const CORES_DPA = {"Alto":"#b2182b","Médio":"#ef8a62","Baixo":"#fddbc7",
                   "Não Classificado":"#9aa5b1"};
const CORES_ORGAO = {"MT - Secretaria de Estado do Meio Ambiente - SEMA":"#1b7837",
                     "Agência Nacional de Mineração - ANM":"#762a83",
                     "Agência Nacional de Energia Elétrica - ANEEL":"#2166ac",
                     "Agência Nacional de Águas e Saneamento Básico - ANA":"#e08214"};
const SIGLA_ORGAO = {"MT - Secretaria de Estado do Meio Ambiente - SEMA":"SEMA-MT",
                     "Agência Nacional de Mineração - ANM":"ANM",
                     "Agência Nacional de Energia Elétrica - ANEEL":"ANEEL",
                     "Agência Nacional de Águas e Saneamento Básico - ANA":"ANA"};
const ORDEM_RISCO = ["Alto","Médio","Baixo","Não Classificado","Não se Aplica"];

let filtradas = DADOS.slice();
const graficos = {};
let mapa, camadaPontos;

const unicos = (chave, ordem) => {
  const conjunto = [...new Set(DADOS.map(d => d[chave]).filter(Boolean))];
  if (ordem) return ordem.filter(v => conjunto.includes(v));
  return conjunto.sort((a,b) => a.localeCompare(b,'pt-BR'));
};

function preencherSelect(id, chave, rotuloTodos, ordem, formatador) {
  const alvo = document.getElementById(id);
  alvo.innerHTML = `<option value="">${rotuloTodos}</option>` +
    unicos(chave, ordem).map(v =>
      `<option value="${v.replace(/"/g,'&quot;')}">${formatador ? formatador(v) : v}</option>`
    ).join('');
}

function aplicarFiltros() {
  const municipio = document.getElementById('f-municipio').value;
  const orgao = document.getElementById('f-orgao').value;
  const cri = document.getElementById('f-cri').value;
  const dpa = document.getElementById('f-dpa').value;
  const uso = document.getElementById('f-uso').value;
  const pnsb = document.getElementById('f-pnsb').value;
  const busca = document.getElementById('f-busca').value.trim().toLowerCase();

  filtradas = DADOS.filter(d =>
    (!municipio || d.mu === municipio) &&
    (!orgao || d.og === orgao) &&
    (!cri || d.cri === cri) &&
    (!dpa || d.dpa === dpa) &&
    (!uso || d.us === uso) &&
    (!pnsb || d.pn === pnsb) &&
    (!busca || (d.no||'').toLowerCase().includes(busca) || (d.em||'').toLowerCase().includes(busca))
  );
  desenharTudo();
}

const contar = (lista, chave) => lista.reduce((acc,d) => {
  const v = d[chave] || 'Não informado';
  acc[v] = (acc[v]||0) + 1; return acc;
}, {});

function desenharKpis() {
  const n = filtradas.length;
  const criAlto = filtradas.filter(d => d.cri === 'Alto').length;
  const dpaAlto = filtradas.filter(d => d.dpa === 'Alto').length;
  const classeA = filtradas.filter(d => d.cl === 'A').length;
  const semClasse = filtradas.filter(d => !d.cri || d.cri === 'Não Classificado').length;
  const comPae = filtradas.filter(d => d.pae === 'Sim').length;
  const comPse = filtradas.filter(d => d.pse === 'Sim').length;
  const volume = filtradas.reduce((s,d) => s + (d.cap||0), 0);
  const pct = x => n ? Math.round(100*x/n) + '%' : '—';

  document.getElementById('kpis').innerHTML = [
    ['', n.toLocaleString('pt-BR'), 'Barragens no recorte atual'],
    ['risco', criAlto.toLocaleString('pt-BR'), `Categoria de risco alta (${pct(criAlto)})`],
    ['risco', dpaAlto.toLocaleString('pt-BR'), `Dano potencial alto (${pct(dpaAlto)})`],
    ['risco', classeA.toLocaleString('pt-BR'), 'Classe A — maior exigência legal'],
    ['atencao', semClasse.toLocaleString('pt-BR'), `Sem categoria de risco (${pct(semClasse)})`],
    ['ok', comPse.toLocaleString('pt-BR'), `Com plano de segurança (${pct(comPse)})`],
    ['ok', comPae.toLocaleString('pt-BR'), `Com plano de emergência (${pct(comPae)})`],
    ['', volume.toLocaleString('pt-BR',{maximumFractionDigits:0}), 'Volume acumulado (hm³)'],
  ].map(([classe,valor,rotulo]) =>
    `<div class="kpi ${classe}"><div class="n">${valor}</div><div class="r">${rotulo}</div></div>`
  ).join('');
  document.getElementById('selo-total').textContent = DADOS.length.toLocaleString('pt-BR');
}

function grafico(id, tipo, rotulos, valores, cores, opcoes) {
  if (graficos[id]) graficos[id].destroy();
  graficos[id] = new Chart(document.getElementById(id), {
    type: tipo,
    data: {labels: rotulos, datasets: [{data: valores, backgroundColor: cores,
           borderWidth: tipo === 'doughnut' ? 2 : 0, borderColor:'#fff',
           borderRadius: tipo === 'bar' ? 3 : 0}]},
    options: Object.assign({
      responsive:true, maintainAspectRatio:false,
      plugins:{legend:{display: tipo === 'doughnut',
                       position:'right',
                       labels:{boxWidth:11,font:{size:10.5},padding:8}}},
    }, opcoes || {})
  });
}

const OPCOES_BARRA_H = {indexAxis:'y', scales:{x:{beginAtZero:true,ticks:{font:{size:10}}},
                        y:{ticks:{font:{size:10.5}}}}, plugins:{legend:{display:false}}};
const OPCOES_BARRA_V = {scales:{y:{beginAtZero:true,ticks:{font:{size:10}}},
                        x:{ticks:{font:{size:10.5}}}}, plugins:{legend:{display:false}}};

function desenharGraficos() {
  const cri = contar(filtradas,'cri');
  const rotulosCri = ORDEM_RISCO.filter(v => cri[v]);
  grafico('g-cri','doughnut', rotulosCri, rotulosCri.map(v=>cri[v]),
          rotulosCri.map(v=>CORES_CRI[v]||'#9aa5b1'));

  const dpa = contar(filtradas,'dpa');
  const rotulosDpa = ORDEM_RISCO.filter(v => dpa[v]);
  grafico('g-dpa','doughnut', rotulosDpa, rotulosDpa.map(v=>dpa[v]),
          rotulosDpa.map(v=>CORES_DPA[v]||'#9aa5b1'));

  const orgao = contar(filtradas,'og');
  const chavesOrgao = Object.keys(orgao).sort((a,b)=>orgao[b]-orgao[a]);
  grafico('g-orgao','bar', chavesOrgao.map(v=>SIGLA_ORGAO[v]||v),
          chavesOrgao.map(v=>orgao[v]), chavesOrgao.map(v=>CORES_ORGAO[v]||'#627d98'),
          OPCOES_BARRA_V);

  const uso = contar(filtradas,'us');
  const chavesUso = Object.keys(uso).sort((a,b)=>uso[b]-uso[a]).slice(0,7);
  grafico('g-uso','bar', chavesUso.map(v=>v.length>26?v.slice(0,25)+'…':v),
          chavesUso.map(v=>uso[v]), '#2166ac', OPCOES_BARRA_H);

  const municipio = contar(filtradas,'mu');
  const chavesMunicipio = Object.keys(municipio).sort((a,b)=>municipio[b]-municipio[a]).slice(0,15);
  grafico('g-municipio','bar', chavesMunicipio, chavesMunicipio.map(v=>municipio[v]),
          '#1d3a57', OPCOES_BARRA_H);

  const n = filtradas.length || 1;
  const conformidade = [
    ['Plano de segurança', filtradas.filter(d=>d.pse==='Sim').length],
    ['Plano de emergência (PAE)', filtradas.filter(d=>d.pae==='Sim').length],
    ['Revisão periódica', filtradas.filter(d=>d.prv==='Sim').length],
    ['Inspeção registrada', filtradas.filter(d=>d.din).length],
    ['Classificada quanto ao risco', filtradas.filter(d=>d.cri&&d.cri!=='Não Classificado').length],
  ];
  grafico('g-conformidade','bar', conformidade.map(c=>c[0]),
          conformidade.map(c=>Math.round(100*c[1]/n)),
          conformidade.map(c => {
            const p = 100*c[1]/n;
            return p < 25 ? '#d7191c' : p < 60 ? '#f08c25' : '#2e9e6b';
          }),
          {indexAxis:'y',
           scales:{x:{beginAtZero:true,max:100,ticks:{callback:v=>v+'%',font:{size:10}}},
                   y:{ticks:{font:{size:10.5}}}},
           plugins:{legend:{display:false},
                    tooltip:{callbacks:{label:c=>c.parsed.x+'% do recorte'}}}});
}

function desenharMapa() {
  if (!mapa) {
    mapa = L.map('mapa', {preferCanvas:true}).setView([-12.7,-55.9], 6);
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
      attribution:'Tiles &copy; Esri — Source: Esri, TomTom, Garmin, FAO, NOAA, USGS', maxZoom:16
    }).addTo(mapa);
    L.geoJSON(MALHA, {style:{color:'#94a3b3',weight:.6,fill:false,interactive:false}}).addTo(mapa);
    document.getElementById('legenda-mapa').innerHTML = ORDEM_RISCO.map(v =>
      `<span><i class="bolinha" style="background:${CORES_CRI[v]}"></i>${v}</span>`).join('');
  }
  if (camadaPontos) mapa.removeLayer(camadaPontos);

  const texto = (r,c) => r ? `<br><b>${c}:</b> ${r}` : '';
  camadaPontos = L.layerGroup(filtradas.filter(d=>d.la&&d.lo).map(d =>
    L.circleMarker([d.la,d.lo], {
      radius: d.cri==='Alto' ? 6 : 4.5,
      fillColor: CORES_CRI[d.cri] || '#7b8794',
      color:'#333', weight:.7, opacity:.9, fillOpacity:.85
    }).bindPopup(
      `<b>${d.no||'(sem nome)'}</b><br>${d.mu||''}` +
      texto(d.em,'Empreendedor') +
      texto(SIGLA_ORGAO[d.og]||d.og,'Fiscalizador') +
      texto(d.cri,'Categoria de risco') +
      texto(d.dpa,'Dano potencial') +
      texto(d.cl,'Classe CNRH') +
      texto(d.us,'Uso principal') +
      texto(d.al ? d.al.toLocaleString('pt-BR')+' m' : '','Altura') +
      texto(d.cap ? d.cap.toLocaleString('pt-BR')+' hm³' : '','Capacidade') +
      texto(d.pse,'Plano de segurança') +
      texto(d.pae,'PAE') +
      texto(d.din,'Última inspeção') +
      texto(d.sne,'Nível de emergência (ANM)')
    )
  )).addTo(mapa);
}

const etiqueta = (valor, paleta) => valor
  ? `<span class="etq" style="background:${paleta[valor]||'#9aa5b1'};` +
    `${valor==='Baixo'?'color:#4a3b00':''}">${valor}</span>`
  : '<span style="color:#9aa5b1">—</span>';

function desenharPrioridade() {
  const fila = filtradas.filter(d => d.pr).sort((a,b) =>
    b.pr - a.pr || (b.cap||0) - (a.cap||0)).slice(0,25);
  const area = document.getElementById('area-prioridade');
  if (!fila.length) { area.innerHTML = '<div class="vazio">Nenhuma barragem classificada no recorte atual.</div>'; return; }
  area.innerHTML = `<table><thead><tr>
      <th>#</th><th>Barragem</th><th>Município</th><th>Fiscalizador</th>
      <th>Risco</th><th>Dano potencial</th><th>Classe</th>
      <th class="num">Altura (m)</th><th class="num">Capac. (hm³)</th>
      <th>Plano seg.</th><th>PAE</th></tr></thead><tbody>` +
    fila.map((d,i) => `<tr>
      <td class="num">${i+1}</td><td><b>${d.no||'—'}</b></td><td>${d.mu||'—'}</td>
      <td>${SIGLA_ORGAO[d.og]||'—'}</td>
      <td>${etiqueta(d.cri,CORES_CRI)}</td><td>${etiqueta(d.dpa,CORES_DPA)}</td>
      <td><b>${d.cl||'—'}</b></td>
      <td class="num">${d.al?d.al.toLocaleString('pt-BR'):'—'}</td>
      <td class="num">${d.cap?d.cap.toLocaleString('pt-BR'):'—'}</td>
      <td>${d.pse||'—'}</td><td>${d.pae||'—'}</td></tr>`).join('') +
    '</tbody></table>';
}

const COLUNAS = [
  ['no','Barragem'], ['mu','Município'], ['og','Fiscalizador'], ['em','Empreendedor'],
  ['us','Uso principal'], ['cri','Risco'], ['dpa','Dano potencial'], ['cl','Classe'],
  ['al','Altura (m)'], ['cap','Capac. (hm³)'], ['fa','Fase de vida'], ['co','Completude'],
];
let ordenacao = {coluna:'no', crescente:true};

function desenharTabela() {
  const linhas = filtradas.slice().sort((a,b) => {
    const x = a[ordenacao.coluna], y = b[ordenacao.coluna];
    if (x == null) return 1;
    if (y == null) return -1;
    const cmp = typeof x === 'number' ? x - y : String(x).localeCompare(String(y),'pt-BR');
    return ordenacao.crescente ? cmp : -cmp;
  });
  document.getElementById('conta-tabela').textContent = linhas.length.toLocaleString('pt-BR');

  const area = document.getElementById('area-tabela');
  if (!linhas.length) { area.innerHTML = '<div class="vazio">Nenhuma barragem atende aos filtros.</div>'; return; }

  const seta = c => ordenacao.coluna === c ? (ordenacao.crescente ? ' ▲' : ' ▼') : '';
  area.innerHTML = `<table><thead><tr>` +
    COLUNAS.map(([c,r]) => `<th data-col="${c}">${r}${seta(c)}</th>`).join('') +
    `</tr></thead><tbody>` +
    linhas.slice(0,400).map(d => `<tr>
      <td><b>${d.no||'—'}</b></td><td>${d.mu||'—'}</td><td>${SIGLA_ORGAO[d.og]||'—'}</td>
      <td>${(d.em||'—').slice(0,38)}</td><td>${d.us||'—'}</td>
      <td>${etiqueta(d.cri,CORES_CRI)}</td><td>${etiqueta(d.dpa,CORES_DPA)}</td>
      <td>${d.cl||'—'}</td>
      <td class="num">${d.al?d.al.toLocaleString('pt-BR'):'—'}</td>
      <td class="num">${d.cap?d.cap.toLocaleString('pt-BR'):'—'}</td>
      <td>${d.fa||'—'}</td><td>${d.co||'—'}</td></tr>`).join('') +
    '</tbody></table>' +
    (linhas.length > 400
      ? `<div class="vazio">Exibindo as 400 primeiras de ${linhas.length.toLocaleString('pt-BR')}. Refine os filtros ou exporte o CSV.</div>`
      : '');

  area.querySelectorAll('th').forEach(th => th.onclick = () => {
    const coluna = th.dataset.col;
    ordenacao = {coluna, crescente: ordenacao.coluna === coluna ? !ordenacao.crescente : true};
    desenharTabela();
  });
}

function exportarCsv() {
  const cabecalho = COLUNAS.map(c => c[1]);
  const corpo = filtradas.map(d => COLUNAS.map(([c]) => {
    const v = d[c];
    return v == null ? '' : `"${String(v).replace(/"/g,'""')}"`;
  }).join(';'));
  // BOM garante que o Excel em pt-BR abra os acentos corretamente.
  const blob = new Blob(['\ufeff' + [cabecalho.join(';'), ...corpo].join('\r\n')],
                        {type:'text/csv;charset=utf-8'});
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = 'barragens_mt_filtrado.csv';
  link.click();
  URL.revokeObjectURL(link.href);
}

function desenharTudo() {
  desenharKpis(); desenharGraficos(); desenharMapa();
  desenharPrioridade(); desenharTabela();
}

preencherSelect('f-municipio','mu','Todos os municípios');
preencherSelect('f-orgao','og','Todos os órgãos', null, v => SIGLA_ORGAO[v] || v);
preencherSelect('f-cri','cri','Todas as categorias', ORDEM_RISCO);
preencherSelect('f-dpa','dpa','Todos os níveis', ORDEM_RISCO);
preencherSelect('f-uso','us','Todos os usos');
preencherSelect('f-pnsb','pn','Todas');

['f-municipio','f-orgao','f-cri','f-dpa','f-uso','f-pnsb'].forEach(id =>
  document.getElementById(id).addEventListener('change', aplicarFiltros));
document.getElementById('f-busca').addEventListener('input', aplicarFiltros);
document.getElementById('b-exportar').addEventListener('click', exportarCsv);
document.getElementById('b-limpar').addEventListener('click', () => {
  ['f-municipio','f-orgao','f-cri','f-dpa','f-uso','f-pnsb'].forEach(id =>
    document.getElementById(id).value = '');
  document.getElementById('f-busca').value = '';
  aplicarFiltros();
});

desenharTudo();
</script>
</body>
</html>
"""


def main() -> None:
    barragens = ler_inventario()
    compactadas = compactar(barragens)
    print(f"Montando painel com {len(compactadas)} barragens")

    malha = json.loads(
        (comum.DADOS_TRATADOS / "ibge_malha_municipios_mt_simplificada.geojson").read_text(
            encoding="utf-8"
        )
    )
    simplificada = simplificar_malha(malha)

    dados_json = json.dumps(compactadas, ensure_ascii=False, separators=(",", ":"))
    malha_json = json.dumps(simplificada, ensure_ascii=False, separators=(",", ":"))
    print(f"  dados {len(dados_json) / 1024:.0f} KB | malha {len(malha_json) / 1024:.0f} KB")

    html = (
        MODELO.replace("__DADOS__", dados_json)
        .replace("__MALHA__", malha_json)
        .replace("__DATA__", dt.date.today().strftime("%d/%m/%Y"))
    )

    SAIDA.mkdir(parents=True, exist_ok=True)
    destino = SAIDA / "inventario.html"
    destino.write_text(html, encoding="utf-8")
    print(f"  gravado {destino.relative_to(comum.RAIZ)} ({destino.stat().st_size / 1024:.0f} KB)")
    print("  (comando operacional: rode a etapa 20 → painel/index.html)")


if __name__ == "__main__":
    main()
