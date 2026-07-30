"""Tema visual do painel Streamlit — alinhado aos HTMLs operacionais."""

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
    radial-gradient(ellipse at 0% 0%, #d5e6dc 0%, transparent 42%),
    radial-gradient(ellipse at 100% 0%, #d4e0eb 0%, transparent 40%),
    #e9eef2;
}
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(255,255,255,.95), rgba(240,247,243,.92));
  border-right: 1px solid #d0d8e0;
}
section[data-testid="stSidebar"] .marca {
  font-size: 1.35rem;
  color: #15202b;
  margin: 0 0 2px;
}
section[data-testid="stSidebar"] .submarca {
  color: #5a6b7a;
  font-size: 0.82rem;
  margin: 0 0 12px;
}
div[data-testid="stMetric"] {
  background: #fff;
  border: 1px solid #d0d8e0;
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
  color: #5a6b7a !important;
}
.badge {
  display: inline-block;
  padding: 2px 8px;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
}
.nota {
  color: #5a6b7a;
  font-size: 0.92rem;
  line-height: 1.45;
  max-width: 48rem;
}
.bloco-interp {
  background: #fff;
  border: 1px solid #d0d8e0;
  border-left: 4px solid #0b6e4f;
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
  color: #5a6b7a;
  margin: 8px 0 4px;
}
</style>
"""
