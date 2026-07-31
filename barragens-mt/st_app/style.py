"""Tema visual do painel Streamlit — azul institucional GOV/SES-MT (#1b3281)."""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=Source+Sans+3:wght@400;600;700&display=swap');

html, body, [class*="css"] {
  font-family: "Source Sans 3", system-ui, sans-serif;
}
h1, h2, h3, .marca {
  font-family: "Fraunces", Georgia, serif !important;
  font-weight: 600 !important;
  letter-spacing: -0.02em;
}
.stApp {
  background:
    radial-gradient(ellipse at 10% -5%, rgba(42,74,173,.38), transparent 42%),
    linear-gradient(180deg, #1b3281 0%, #243f9a 22%, #e6ecf7 22%);
}
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #1b3281 0%, #243f9a 18%, #f3f6fb 18%);
  border-right: 1px solid #c5d0e0;
}
section[data-testid="stSidebar"] .marca {
  font-size: 1.35rem;
  color: #fff;
  margin: 0 0 2px;
}
section[data-testid="stSidebar"] .submarca {
  color: rgba(255,255,255,.82);
  font-size: 0.82rem;
  margin: 0 0 12px;
}
div[data-testid="stMetric"] {
  background: #fff;
  border: 1px solid #c5d0e0;
  border-top: 3px solid #1b3281;
  padding: 10px 12px 8px;
}
div[data-testid="stMetricValue"] {
  font-variant-numeric: tabular-nums;
  font-weight: 700 !important;
}
div[data-testid="stMetricLabel"] {
  text-transform: uppercase;
  letter-spacing: .04em;
  font-size: 0.72rem !important;
  color: #4a5d73 !important;
}
.badge {
  display: inline-block;
  padding: 2px 8px;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
}
.nota {
  color: #4a5d73;
  font-size: 0.92rem;
  line-height: 1.45;
  max-width: 48rem;
  background: rgba(255,255,255,.88);
  border: 1px solid #c5d0e0;
  padding: 10px 12px;
}
.bloco-interp {
  background: #fff;
  border: 1px solid #c5d0e0;
  border-left: 4px solid #1b3281;
  padding: 14px 16px;
  margin: 0 0 12px;
}
.bloco-interp h3 {
  margin: 0 0 6px !important;
  font-size: 1.05rem !important;
}
.bloco-interp p {
  margin: 0;
  color: #334155;
  line-height: 1.45;
  font-size: 0.95rem;
}
.lista-us-titulo {
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: .04em;
  color: #4a5d73;
  margin: 8px 0 4px;
}
.kpi-card {
  background: #fff;
  border: 1px solid #c5d0e0;
  border-left: 5px solid #94a3b8;
  padding: 10px 12px;
  margin-bottom: 8px;
  min-height: 78px;
}
.kpi-card .kpi-val {
  font-size: 1.45rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}
.kpi-card .kpi-tit {
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: .03em;
  color: #4a5d73;
  margin-top: 4px;
  line-height: 1.25;
}
.kpi-card .kpi-delta { font-size: 0.8rem; font-weight: 600; margin-top: 3px; }
.kpi-card .kpi-nota { font-size: 0.75rem; color: #64748b; margin-top: 2px; }
.kpi-card.sev-ok { border-left-color: #1e8449; }
.kpi-card.sev-ok .kpi-val { color: #1e8449; }
.kpi-card.sev-atencao { border-left-color: #b7950b; }
.kpi-card.sev-atencao .kpi-val { color: #92740a; }
.kpi-card.sev-elevado { border-left-color: #d35400; }
.kpi-card.sev-elevado .kpi-val { color: #c2410c; }
.kpi-card.sev-alto { border-left-color: #c0392b; }
.kpi-card.sev-alto .kpi-val { color: #b91c1c; }
.kpi-card.sev-critico { border-left-color: #5b2c6f; }
.kpi-card.sev-critico .kpi-val { color: #5b2c6f; }
.kpi-card.sev-neutro { border-left-color: #1b3281; }
.kpi-card.sev-neutro .kpi-val { color: #1b3281; }
.tend-box {
  padding: 12px 14px;
  border: 1px solid #c5d0e0;
  border-left: 5px solid #1b3281;
  background: #fff;
  margin: 8px 0 14px;
  line-height: 1.45;
}
.tend-box.sev-ok { border-left-color: #1e8449; }
.tend-box.sev-atencao { border-left-color: #b7950b; }
.tend-box.sev-elevado { border-left-color: #d35400; }
.tend-box.sev-alto, .tend-box.sev-critico { border-left-color: #c0392b; }
.grade-kpis {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}
.faixa-titulo {
  font-family: "Fraunces", Georgia, serif !important;
  font-size: 1.05rem !important;
  font-weight: 600 !important;
  letter-spacing: -0.02em;
  color: #1b3281;
  margin: 18px 0 8px;
  /* Fundo próprio: a faixa 1 fica sobre o azul do topo do app. */
  background: rgba(255,255,255,.94);
  border: 1px solid #c5d0e0;
  border-left: 5px solid #1b3281;
  padding: 8px 12px;
}
.faixa-titulo span {
  display: block;
  font-family: "Source Sans 3", system-ui, sans-serif !important;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: .04em;
  text-transform: uppercase;
  color: #4a5d73;
  margin-bottom: 2px;
}
.frescor-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 6px 0 10px;
}
.frescor-chips .chip {
  background: #fff;
  border: 1px solid #c5d0e0;
  padding: 4px 8px;
  font-size: 11px;
  color: #334155;
}
.frescor-chips .chip.ok { border-left: 3px solid #1e8449; }
.frescor-chips .chip.velho { border-left: 3px solid #d35400; }
.frescor-chips .chip.morto { border-left: 3px solid #c0392b; }
.atalhos-cmd {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 8px 0 14px;
}
</style>
"""
