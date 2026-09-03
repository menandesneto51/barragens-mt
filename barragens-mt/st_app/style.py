"""Tema visual do painel Streamlit.

Paleta institucional GOV/SES-MT (Manual da Marca GOV-MT): azul #1b3281
(CMYK 100/90/0/20 · Pantone 2758C) e preto #231F20, com neutros derivados do
azul. As cores de **gravidade** (roxo/vermelho/laranja/amarelo/verde) e os
números dos KPIs não entram na paleta de cromo: continuam sendo semânticas.
"""

# Cromo institucional — só moldura, fundo, texto e bordas.
AZUL_SES = "#1b3281"
PRETO_SES = "#231f20"

# Gravidade (não alterar: é leitura semântica do IDAP).
SEV_CORES = {
    "sev-ok": "#1e8449",
    "sev-atencao": "#b7950b",
    "sev-elevado": "#d35400",
    "sev-alto": "#c0392b",
    "sev-critico": "#5b2c6f",
    "sev-neutro": AZUL_SES,
}

CSS = """
<style>
/* Montserrat aproxima a Nexa/Uni Neue (títulos) e Source Sans 3 o Calibri (corpo);
   nenhuma das duas oficiais é distribuível pelo Google Fonts. */
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@600;700&family=Source+Sans+3:wght@400;600;700&display=swap');

:root {
  /* Escala derivada do azul institucional #1b3281 (nada de neutro "a olho"). */
  --ses-azul: #1b3281;
  --ses-azul-escuro: #1e2b5f;
  --ses-azul-medio: #3d5194;
  --ses-azul-300: #98a3c6;
  --ses-azul-claro: #e8eaf2;
  --ink: #231f20;
  --muted: #5b6b80;
  --line: #dfe2ed;
  --canvas: #f7f8fb;
  --surface: #ffffff;
  /* Gravidade (semântica — não é cromo) */
  --sev-ok: #1e8449;
  --sev-atencao: #b7950b;
  --sev-atencao-txt: #92740a;
  --sev-elevado: #d35400;
  --sev-elevado-txt: #c2410c;
  --sev-alto: #c0392b;
  --sev-alto-txt: #b91c1c;
  --sev-critico: #5b2c6f;
}

html, body, [class*="css"] {
  font-family: "Source Sans 3", system-ui, sans-serif;
  color: var(--ink);
}
.stApp { background: var(--canvas); }

/* Respiro menor entre blocos: menos rolagem, mesma informação. */
div[data-testid="stVerticalBlock"] { gap: 0.55rem; }
div[data-testid="stMainBlockContainer"] { padding-top: 2.2rem; padding-bottom: 3rem; }

h1 {
  font-family: "Montserrat", "Source Sans 3", system-ui, sans-serif !important;
  font-size: 1.55rem !important;
  font-weight: 700 !important;
  letter-spacing: -0.01em;
  color: var(--ses-azul) !important;
  margin: 0 0 2px !important;
  padding-bottom: 8px;
  border-bottom: 3px solid var(--ses-azul);
}
h2, h3 {
  font-family: "Montserrat", "Source Sans 3", system-ui, sans-serif !important;
  font-weight: 600 !important;
  letter-spacing: -0.01em;
  color: var(--ink) !important;
}
h5 {
  font-size: 0.82rem !important;
  font-weight: 700 !important;
  text-transform: uppercase;
  letter-spacing: .05em;
  color: var(--muted) !important;
  margin: 10px 0 2px !important;
}

/* ---- Sidebar: assinatura institucional (marca do governo + secretaria) ---- */
section[data-testid="stSidebar"] {
  background: var(--surface);
  border-right: 1px solid var(--line);
}
.assinatura-gov {
  background: var(--ses-azul);
  color: #fff;
  padding: 12px 14px 11px;
  margin: -8px -14px 12px;
}
.assinatura-gov .gov {
  display: block;
  font-family: "Montserrat", sans-serif;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .14em;  /* entreletras da marca, conforme manual */
  line-height: 1.25;
}
.assinatura-gov .secretaria {
  display: block;
  font-size: 0.72rem;
  color: rgba(255,255,255,.88);
  letter-spacing: .04em;
  margin-top: 3px;
  padding-top: 3px;
  border-top: 1px solid rgba(255,255,255,.35);
}
section[data-testid="stSidebar"] .marca {
  font-family: "Montserrat", "Source Sans 3", sans-serif;
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--ses-azul);
  margin: 0 0 2px;
}
section[data-testid="stSidebar"] .submarca {
  color: var(--muted);
  font-size: 0.76rem;
  line-height: 1.35;
  margin: 0 0 10px;
  padding-bottom: 10px;
  border-bottom: 2px solid var(--ses-azul);
}

/* ---- Faixas: hierarquia tipográfica, sem caixa ---- */
.faixa-titulo {
  margin: 16px 0 6px;
  padding-bottom: 5px;
  border-bottom: 1px solid var(--line);
}
.faixa-titulo .kicker {
  display: inline-block;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: var(--ses-azul);
  margin-bottom: 1px;
}
.faixa-titulo .titulo {
  display: block;
  font-family: "Montserrat", "Source Sans 3", sans-serif;
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--ink);
  line-height: 1.2;
}
.faixa-titulo .sub {
  display: block;
  font-size: 0.82rem;
  font-weight: 400;
  color: var(--muted);
  margin-top: 1px;
}

/* ---- KPI: moldura neutra, cor só no número e no topo ---- */
.grade-kpis {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(158px, 1fr));
  gap: 8px;
  margin-bottom: 10px;
}
.kpi-card {
  background: var(--surface);
  border: 1px solid var(--line);
  border-top: 3px solid var(--ses-azul);
  padding: 10px 12px;
  min-height: 76px;
}
.kpi-card .kpi-val {
  font-size: 1.45rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
  color: var(--ses-azul);
}
.kpi-card .kpi-tit {
  font-size: 0.74rem;
  text-transform: uppercase;
  letter-spacing: .04em;
  color: var(--muted);
  margin-top: 4px;
  line-height: 1.25;
}
.kpi-card .kpi-delta { font-size: 0.78rem; font-weight: 600; margin-top: 3px; }
.kpi-card .kpi-nota { font-size: 0.72rem; color: var(--muted); margin-top: 2px; }
.kpi-card.sev-ok { border-top-color: var(--sev-ok); }
.kpi-card.sev-ok .kpi-val { color: var(--sev-ok); }
.kpi-card.sev-atencao { border-top-color: var(--sev-atencao); }
.kpi-card.sev-atencao .kpi-val { color: var(--sev-atencao-txt); }
.kpi-card.sev-elevado { border-top-color: var(--sev-elevado); }
.kpi-card.sev-elevado .kpi-val { color: var(--sev-elevado-txt); }
.kpi-card.sev-alto { border-top-color: var(--sev-alto); }
.kpi-card.sev-alto .kpi-val { color: var(--sev-alto-txt); }
.kpi-card.sev-critico { border-top-color: var(--sev-critico); }
.kpi-card.sev-critico .kpi-val { color: var(--sev-critico); }
.kpi-card.sev-neutro { border-top-color: var(--ses-azul); }
.kpi-card.sev-neutro .kpi-val { color: var(--ses-azul); }

div[data-testid="stMetric"] {
  background: var(--surface);
  border: 1px solid var(--line);
  border-top: 3px solid var(--ses-azul);
  padding: 10px 12px 8px;
}
div[data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; font-weight: 700 !important; }
div[data-testid="stMetricLabel"] {
  text-transform: uppercase;
  letter-spacing: .04em;
  font-size: 0.7rem !important;
  color: var(--muted) !important;
}

/* ---- Blocos de texto ---- */
.badge {
  display: inline-block;
  padding: 2px 8px;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
}
/* Faixas claras (amarelo) pedem texto escuro: branco fica em 2,9:1. */
.badge.claro { color: var(--ink); }
.nota {
  color: var(--muted);
  font-size: 0.88rem;
  line-height: 1.45;
  max-width: 52rem;
  background: transparent;
  border: 0;
  border-left: 3px solid var(--ses-azul-claro);
  padding: 2px 0 2px 10px;
  margin: 0 0 8px;
}
.tend-box {
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-left: 3px solid var(--ses-azul);
  background: var(--surface);
  margin: 6px 0 10px;
  line-height: 1.45;
  font-size: 0.9rem;
}
.tend-box.sev-ok { border-left-color: var(--sev-ok); }
.tend-box.sev-atencao { border-left-color: var(--sev-atencao); }
.tend-box.sev-elevado { border-left-color: var(--sev-elevado); }
.tend-box.sev-alto, .tend-box.sev-critico { border-left-color: var(--sev-alto); }
.bloco-interp {
  background: var(--surface);
  border: 1px solid var(--line);
  border-left: 3px solid var(--ses-azul);
  padding: 12px 14px;
  margin: 0 0 10px;
}
.bloco-interp h3 { margin: 0 0 6px !important; font-size: 1rem !important; }
.bloco-interp p { margin: 0; color: #334155; line-height: 1.45; font-size: 0.92rem; }
.lista-us-titulo {
  font-size: 0.74rem;
  text-transform: uppercase;
  letter-spacing: .04em;
  color: var(--muted);
  margin: 8px 0 4px;
}

/* ---- Chips (frescor, legendas): pílula leve com ponto colorido ---- */
.frescor-chips { display: flex; flex-wrap: wrap; gap: 6px; margin: 4px 0 8px; }
.frescor-chips .chip {
  background: var(--ses-azul-claro);
  border: 0;
  border-radius: 2px;
  padding: 3px 9px 3px 8px;
  font-size: 11.5px;
  color: #35405a;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.frescor-chips .chip::before {
  content: "";
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--muted);
  flex: none;
}
.frescor-chips .chip.ok::before { background: var(--sev-ok); }
.frescor-chips .chip.velho::before { background: var(--sev-elevado); }
.frescor-chips .chip.morto::before { background: var(--sev-alto); }
.atalhos-cmd { display: flex; flex-wrap: wrap; gap: 8px; margin: 6px 0 10px; }

/* Distribuição por faixa: uma linha em vez de um card por nível. */
.dist { display: flex; flex-wrap: wrap; gap: 14px; margin: 0 0 8px; font-size: 0.8rem; color: var(--muted); }
.dist-item { display: inline-flex; align-items: center; gap: 5px; }
.dist-item i { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
.dist-item b { color: var(--ink); font-variant-numeric: tabular-nums; }

/* ---- Expanders: cabeçalho discreto, sem competir com as faixas ---- */
details[data-testid="stExpander"] {
  border: 1px solid var(--line) !important;
  background: var(--surface);
}
details[data-testid="stExpander"] summary {
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .04em;
  color: var(--muted);
}

/* ---- Tabelas e abas ---- */
div[data-testid="stDataFrame"] { border: 1px solid var(--line); }
button[data-baseweb="tab"] { font-weight: 600; }

/* ---- Faixa de logos institucionais ---- */
.faixa-logos {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  background: #f4f6fa;
  border-bottom: 1px solid var(--line);
}
.faixa-logos .logo-inst {
  height: 42px;
  width: auto;
  max-width: 160px;
  object-fit: contain;
  border-radius: 4px;
  box-shadow: 0 1px 2px rgba(15, 39, 79, 0.08);
}
.faixa-logos-sidebar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0 0 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255,255,255,.2);
}
.faixa-logos-sidebar .logo-inst {
  height: 34px;
  width: auto;
  max-width: 48%;
  border-radius: 3px;
  background: #fff;
}

/* ---- Cabeçalho institucional (área principal) ---- */
.cab-inst {
  background: var(--surface);
  border: 1px solid var(--line);
  border-left: 4px solid var(--ses-azul);
  padding: 0;
  margin: 0 0 10px;
}
.cab-inst-topo {
  background: var(--ses-azul);
  color: #fff;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: .08em;
  text-transform: uppercase;
  padding: 6px 14px;
}
.cab-inst-linha {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px 10px;
  align-items: flex-start;
}
.cab-inst-nome {
  font-family: "Montserrat", sans-serif;
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--ses-azul);
  letter-spacing: -0.01em;
  line-height: 1.15;
}
.cab-inst-tag {
  color: var(--muted);
  font-size: 0.88rem;
  margin-top: 2px;
  max-width: 36rem;
  line-height: 1.35;
}
.cab-inst-meta {
  text-align: right;
  font-size: 0.82rem;
  color: var(--muted);
  line-height: 1.55;
}
.cab-inst-sit {
  display: inline-block;
  color: #fff;
  font-weight: 700;
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 2px;
  margin-left: 4px;
}
.barra-ctx {
  background: var(--ses-azul-claro);
  border: 1px solid var(--line);
  padding: 8px 12px;
  font-size: 0.84rem;
  color: #35405a;
  margin: 0 0 12px;
}
.tut-box {
  background: var(--surface);
  border: 1px solid var(--line);
  border-left: 4px solid var(--ses-azul);
  padding: 14px 16px;
  margin: 0 0 12px;
}
.tut-box .tut-passo {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: var(--ses-azul);
  margin-bottom: 4px;
}
.tut-box h3 {
  margin: 0 0 6px !important;
  font-size: 1.05rem !important;
  color: var(--ink) !important;
  border: 0 !important;
  padding: 0 !important;
}
.tut-box p { margin: 0; color: #334155; line-height: 1.45; }
.motivo-box {
  background: #fff8e8;
  border: 1px solid #f0e0b8;
  border-left: 4px solid var(--sev-atencao);
  padding: 12px 14px;
  margin: 0 0 12px;
  font-size: 0.95rem;
  line-height: 1.45;
}
</style>
"""
