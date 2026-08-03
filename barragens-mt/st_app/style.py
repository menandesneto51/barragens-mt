"""Tema institucional do VIGIBARRAGENS–MT.

A identidade visual separa três camadas:
- Governo de Mato Grosso / SES-MT: azul institucional e neutros;
- CIEVS-MT / Rede CIEVS: azul-marinho e laranja como assinatura de unidade;
- gravidade operacional: verde, amarelo, laranja, vermelho e roxo, preservados
  exclusivamente para comunicar risco e prontidão.

A faixa lateral aceita uma arte institucional local em ``assets``. Enquanto o
arquivo definitivo não estiver no repositório, a marca do Governo é carregada
de fonte pública oficial e a assinatura CIEVS é composta de forma tipográfica.
"""

AZUL_SES = "#1b3281"
PRETO_SES = "#231f20"
LARANJA_CIEVS = "#ed6b1a"

# Gravidade (não alterar: é leitura semântica do IDAP).
SEV_CORES = {
    "sev-ok": "#1e8449",
    "sev-atencao": "#b7950b",
    "sev-elevado": "#d35400",
    "sev-alto": "#c0392b",
    "sev-critico": "#5b2c6f",
    "sev-neutro": AZUL_SES,
}

CSS = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@600;700&family=Source+Sans+3:wght@400;600;700&display=swap');

:root {
  --ses-azul: #1b3281;
  --ses-azul-escuro: #10245f;
  --ses-azul-medio: #3d5194;
  --ses-azul-300: #98a3c6;
  --ses-azul-claro: #e8eaf2;
  --cievs-laranja: #ed6b1a;
  --cievs-laranja-claro: #fff0e5;
  --ink: #231f20;
  --muted: #57595a;
  --line: #dfe2ed;
  --canvas: #f7f8fb;
  --surface: #ffffff;
  --sev-ok: #1e8449;
  --sev-atencao: #b7950b;
  --sev-atencao-txt: #806500;
  --sev-elevado: #d35400;
  --sev-elevado-txt: #b94800;
  --sev-alto: #c0392b;
  --sev-alto-txt: #a92f23;
  --sev-critico: #5b2c6f;
  --shadow-sm: 0 1px 2px rgba(16,36,95,.06);
}

html, body, [class*="css"] {
  font-family: "Source Sans 3", "Segoe UI", Arial, sans-serif;
  color: var(--ink);
}
.stApp { background: var(--canvas); }
div[data-testid="stVerticalBlock"] { gap: .58rem; }
div[data-testid="stMainBlockContainer"] {
  max-width: 1540px;
  padding-top: 1.45rem;
  padding-bottom: 3.5rem;
}

/* Barra superior institucional comum a todas as telas. */
div[data-testid="stAppViewContainer"] > section.main::before {
  content: "GOVERNO DE MATO GROSSO  ·  SECRETARIA DE ESTADO DE SAÚDE  ·  CIEVS-MT";
  display: block;
  min-height: 28px;
  padding: 7px clamp(1rem, 4vw, 3rem) 6px;
  background: var(--ses-azul-escuro);
  border-bottom: 3px solid var(--cievs-laranja);
  color: #fff;
  font-family: "Montserrat", "Segoe UI", sans-serif;
  font-size: .66rem;
  font-weight: 700;
  letter-spacing: .105em;
  line-height: 1.25;
  text-transform: uppercase;
}

h1 {
  font-family: "Montserrat", "Segoe UI", sans-serif !important;
  font-size: clamp(1.45rem, 2vw, 1.72rem) !important;
  font-weight: 700 !important;
  letter-spacing: -.012em;
  color: var(--ses-azul) !important;
  margin: 0 0 2px !important;
  padding-bottom: 9px;
  border-bottom: 3px solid var(--ses-azul);
}
h1::after {
  content: "";
  display: block;
  width: 58px;
  height: 3px;
  margin-bottom: -12px;
  background: var(--cievs-laranja);
}
h2, h3 {
  font-family: "Montserrat", "Segoe UI", sans-serif !important;
  font-weight: 600 !important;
  letter-spacing: -.01em;
  color: var(--ink) !important;
}
h5 {
  margin: 10px 0 2px !important;
  color: var(--muted) !important;
  font-size: .79rem !important;
  font-weight: 700 !important;
  letter-spacing: .055em;
  text-transform: uppercase;
}
p, li { line-height: 1.5; }

/* Assinatura lateral. A imagem GOV-MT é publicada pelo portal MT Criativo. */
section[data-testid="stSidebar"] {
  background: var(--surface);
  border-right: 1px solid var(--line);
}
section[data-testid="stSidebar"] > div {
  padding-top: .55rem;
}
.assinatura-gov {
  position: relative;
  display: grid;
  grid-template-columns: 1fr;
  gap: 0;
  min-height: 150px;
  margin: -8px -14px 14px;
  padding: 82px 15px 12px;
  overflow: hidden;
  background: #fff;
  border-bottom: 1px solid var(--line);
}
.assinatura-gov::before {
  content: "";
  position: absolute;
  inset: 11px 14px auto 14px;
  height: 62px;
  background-image: url("https://www.mtcriativo.mt.gov.br/wp-content/uploads/2024/06/secel_marca_horizontal_branco_page-0001.jpg");
  background-position: left center;
  background-repeat: no-repeat;
  background-size: contain;
}
.assinatura-gov::after {
  content: "CIEVS-MT   |   REDE CIEVS";
  display: block;
  margin-top: 8px;
  padding: 8px 10px 7px;
  background: var(--ses-azul-escuro);
  border-left: 5px solid var(--cievs-laranja);
  color: #fff;
  font-family: "Montserrat", "Segoe UI", sans-serif;
  font-size: .72rem;
  font-weight: 700;
  letter-spacing: .055em;
  line-height: 1.2;
}
.assinatura-gov .gov {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0,0,0,0);
  white-space: nowrap;
  border: 0;
}
.assinatura-gov .secretaria {
  display: block;
  color: var(--ses-azul-escuro);
  font-size: .72rem;
  font-weight: 700;
  letter-spacing: .025em;
  line-height: 1.25;
}
section[data-testid="stSidebar"] .marca {
  margin: 0 0 2px;
  color: var(--ses-azul);
  font-family: "Montserrat", "Segoe UI", sans-serif;
  font-size: 1.08rem;
  font-weight: 700;
  letter-spacing: -.01em;
}
section[data-testid="stSidebar"] .submarca {
  margin: 0 0 11px;
  padding-bottom: 11px;
  border-bottom: 2px solid var(--ses-azul);
  color: var(--muted);
  font-size: .76rem;
  line-height: 1.4;
}
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
  color: #3e4351;
  font-weight: 600;
}
section[data-testid="stSidebar"] [role="radiogroup"] label {
  border-radius: 3px;
}
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
  background: var(--ses-azul-claro);
}

/* Foco e controles: azul institucional, laranja apenas como realce. */
button:focus-visible, a:focus-visible, input:focus-visible,
[role="button"]:focus-visible, [tabindex]:focus-visible {
  outline: 3px solid rgba(237,107,26,.42) !important;
  outline-offset: 2px !important;
}
.stButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"] {
  background: var(--ses-azul) !important;
  border-color: var(--ses-azul) !important;
  color: #fff !important;
}
.stButton > button[kind="primary"]:hover,
.stDownloadButton > button[kind="primary"]:hover {
  background: var(--ses-azul-escuro) !important;
  border-color: var(--ses-azul-escuro) !important;
}
.stButton > button:not([kind="primary"]),
.stDownloadButton > button:not([kind="primary"]) {
  border-color: var(--ses-azul-300);
}
.stButton > button:not([kind="primary"]):hover,
.stDownloadButton > button:not([kind="primary"]):hover {
  border-color: var(--ses-azul);
  color: var(--ses-azul);
}

/* Faixas de leitura operacional. */
.faixa-titulo {
  margin: 17px 0 7px;
  padding: 0 0 6px 11px;
  border-left: 4px solid var(--ses-azul);
  border-bottom: 1px solid var(--line);
}
.faixa-titulo .kicker {
  display: inline-block;
  margin-bottom: 1px;
  color: var(--cievs-laranja);
  font-size: .67rem;
  font-weight: 700;
  letter-spacing: .11em;
  text-transform: uppercase;
}
.faixa-titulo .titulo {
  display: block;
  color: var(--ink);
  font-family: "Montserrat", "Segoe UI", sans-serif;
  font-size: 1.08rem;
  font-weight: 700;
  letter-spacing: -.01em;
  line-height: 1.2;
}
.faixa-titulo .sub {
  display: block;
  margin-top: 1px;
  color: var(--muted);
  font-size: .82rem;
  font-weight: 400;
}

/* KPIs: cromo neutro; gravidade aparece somente no topo e no número. */
.grade-kpis {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(165px, 1fr));
  gap: 9px;
  margin-bottom: 10px;
}
.kpi-card {
  min-height: 80px;
  padding: 11px 12px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-top: 3px solid var(--ses-azul);
  border-radius: 3px;
  box-shadow: var(--shadow-sm);
}
.kpi-card .kpi-val {
  color: var(--ses-azul);
  font-size: 1.48rem;
  font-variant-numeric: tabular-nums;
  font-weight: 700;
  line-height: 1.08;
}
.kpi-card .kpi-tit {
  margin-top: 4px;
  color: var(--muted);
  font-size: .73rem;
  letter-spacing: .04em;
  line-height: 1.25;
  text-transform: uppercase;
}
.kpi-card .kpi-delta { margin-top: 3px; font-size: .78rem; font-weight: 600; }
.kpi-card .kpi-nota { margin-top: 2px; color: var(--muted); font-size: .72rem; }
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
  padding: 10px 12px 8px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-top: 3px solid var(--ses-azul);
  border-radius: 3px;
  box-shadow: var(--shadow-sm);
}
div[data-testid="stMetricValue"] {
  font-variant-numeric: tabular-nums;
  font-weight: 700 !important;
}
div[data-testid="stMetricLabel"] {
  color: var(--muted) !important;
  font-size: .7rem !important;
  letter-spacing: .04em;
  text-transform: uppercase;
}

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 2px;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
}
.badge.claro { color: var(--ink); }
.nota {
  max-width: 57rem;
  margin: 0 0 8px;
  padding: 3px 0 3px 10px;
  background: transparent;
  border: 0;
  border-left: 3px solid var(--cievs-laranja);
  color: var(--muted);
  font-size: .88rem;
  line-height: 1.48;
}
.tend-box {
  margin: 6px 0 10px;
  padding: 10px 12px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-left: 4px solid var(--ses-azul);
  border-radius: 2px;
  box-shadow: var(--shadow-sm);
  font-size: .9rem;
  line-height: 1.45;
}
.tend-box.sev-ok { border-left-color: var(--sev-ok); }
.tend-box.sev-atencao { border-left-color: var(--sev-atencao); }
.tend-box.sev-elevado { border-left-color: var(--sev-elevado); }
.tend-box.sev-alto, .tend-box.sev-critico { border-left-color: var(--sev-alto); }
.bloco-interp {
  margin: 0 0 10px;
  padding: 12px 14px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-left: 4px solid var(--ses-azul);
  border-radius: 2px;
  box-shadow: var(--shadow-sm);
}
.bloco-interp h3 { margin: 0 0 6px !important; font-size: 1rem !important; }
.bloco-interp p { margin: 0; color: #334155; font-size: .92rem; line-height: 1.48; }
.lista-us-titulo {
  margin: 8px 0 4px;
  color: var(--muted);
  font-size: .74rem;
  letter-spacing: .04em;
  text-transform: uppercase;
}

.frescor-chips { display: flex; flex-wrap: wrap; gap: 6px; margin: 4px 0 8px; }
.frescor-chips .chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 9px 3px 8px;
  background: var(--ses-azul-claro);
  border: 0;
  border-radius: 999px;
  color: #35405a;
  font-size: 11.5px;
}
.frescor-chips .chip::before {
  content: "";
  width: 7px;
  height: 7px;
  flex: none;
  background: var(--muted);
  border-radius: 50%;
}
.frescor-chips .chip.ok::before { background: var(--sev-ok); }
.frescor-chips .chip.velho::before { background: var(--sev-elevado); }
.frescor-chips .chip.morto::before { background: var(--sev-alto); }
.atalhos-cmd { display: flex; flex-wrap: wrap; gap: 8px; margin: 6px 0 10px; }
.dist {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin: 0 0 8px;
  color: var(--muted);
  font-size: .8rem;
}
.dist-item { display: inline-flex; align-items: center; gap: 5px; }
.dist-item i { display: inline-block; width: 9px; height: 9px; border-radius: 50%; }
.dist-item b { color: var(--ink); font-variant-numeric: tabular-nums; }

details[data-testid="stExpander"] {
  background: var(--surface);
  border: 1px solid var(--line) !important;
  border-radius: 3px !important;
}
details[data-testid="stExpander"] summary {
  color: var(--muted);
  font-size: .79rem;
  font-weight: 600;
  letter-spacing: .04em;
  text-transform: uppercase;
}
div[data-testid="stDataFrame"] {
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 3px;
}
button[data-baseweb="tab"] { font-weight: 600; }
button[data-baseweb="tab"][aria-selected="true"] {
  color: var(--ses-azul) !important;
}

/* Mapas e iframes ficam visualmente integrados ao sistema. */
div[data-testid="stIFrame"], iframe {
  border-radius: 3px;
}

/* Rodapé visual não intrusivo no fim da área principal. */
div[data-testid="stMainBlockContainer"]::after {
  content: "VIGIBARRAGENS–MT  ·  CIEVS-MT  ·  SECRETARIA DE ESTADO DE SAÚDE  ·  GOVERNO DE MATO GROSSO";
  display: block;
  margin-top: 2.4rem;
  padding: 13px 4px 0;
  border-top: 1px solid var(--line);
  color: var(--muted);
  font-family: "Montserrat", "Segoe UI", sans-serif;
  font-size: .62rem;
  font-weight: 600;
  letter-spacing: .075em;
  text-align: center;
}

@media (max-width: 900px) {
  div[data-testid="stMainBlockContainer"] { padding-top: 1rem; }
  div[data-testid="stAppViewContainer"] > section.main::before {
    padding-inline: 1rem;
    font-size: .58rem;
    letter-spacing: .07em;
  }
  .grade-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 560px) {
  div[data-testid="stAppViewContainer"] > section.main::before {
    content: "SES-MT  ·  CIEVS-MT";
  }
  h1 { font-size: 1.35rem !important; }
  .grade-kpis { grid-template-columns: 1fr; }
  .faixa-titulo { padding-left: 8px; }
  .assinatura-gov { min-height: 142px; }
}

@media print {
  section[data-testid="stSidebar"], header[data-testid="stHeader"] { display: none !important; }
  div[data-testid="stAppViewContainer"] > section.main::before { position: static; }
  .stApp { background: #fff; }
  .kpi-card, .tend-box, .bloco-interp { box-shadow: none; break-inside: avoid; }
}
</style>
"""
