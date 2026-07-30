"""Tema visual do painel Streamlit — alinhado aos HTMLs operacionais."""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=Source+Sans+3:wght@400;600;700&display=swap');
html, body, [class*="css"]  {
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
div[data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; }
.badge {
  display:inline-block; padding:2px 8px; color:#fff; font-size:12px; font-weight:600;
}
.nota {
  color:#5a6b7a; font-size:0.92rem; line-height:1.45; max-width:48rem;
}
</style>
"""
