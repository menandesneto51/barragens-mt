"""Gera painel/glossario.html — interpretação operacional dos KPIs.

Fonte: docs/10-glossario.md + resumo alinhado à aba Streamlit «Interpretação / KPIs».
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import comum

SAIDA = comum.RAIZ / "painel"
DOCS = comum.RAIZ / "docs" / "10-glossario.md"

BLOCOS = [
    (
        "IDAP (0–100)",
        "Índice Dinâmico de Alerta e Prontidão para o setor saúde. "
        "Não estima probabilidade de rompimento: mede atenção e prontidão. "
        "Faixas: Verde 0–19, Amarelo 20–39, Laranja 40–59, Vermelho 60–79, Roxo 80–100.",
    ),
    (
        "Eixo A — Pressão hidroclimática",
        "Chuva observada (24h/72h), previsão ECMWF, percentil espacial, saturação do solo "
        "e alertas Cemaden/ANA/integrado na sede. Regras R10–R12 elevam o nível quando há "
        "alerta oficial ou chuva prevista extrema (≥140 mm).",
    ),
    (
        "Eixo B — Condição da barragem",
        "CRI, situação cadastral e sinais estruturais disponíveis no SNISB/SIGBM "
        "(emergência oficial, DCE etc.). Lacunas baixam a completude do IDAP.",
    ),
    (
        "Eixo C — Impacto sanitário potencial",
        "DPA, população a jusante, municípios Otto a jusante e exposição da rede de saúde. "
        "Quanto maior a exposição humana e assistencial, maior a pressão neste eixo.",
    ),
    (
        "Eixo D — Déficit de capacidade de resposta",
        "Contatos, alertabilidade e lacunas de articulação local. "
        "Sem canal confirmado, o território fica menos preparado mesmo com IDAP moderado.",
    ),
    (
        "Amarelo+ / semáforo estadual",
        "Contagem de barragens em Amarelo ou acima. Define a prontidão agregada do estado "
        "no comando (pior nível presente na base).",
    ),
    (
        "População estimada (simulação)",
        "Cascata: SIGBM pessoas afetadas → SIGBM pop. jusante → área × densidade municipal. "
        "É ordem de grandeza para planejamento sanitário, não censo da mancha oficial.",
    ),
    (
        "US no buffer (CNES)",
        "Estabelecimentos prioritários (hospital, UPA, UBS/ESF) com coordenada dentro do "
        "raio equivalente da simulação. Indicam capacidade de resposta local sob risco de "
        "interdição ou sobrecarga — não o município inteiro.",
    ),
    (
        "CRI e DPA",
        "CRI = probabilidade relativa de acidente (estado da estrutura). "
        "DPA = consequência de um eventual rompimento (volume, população, ambiente). "
        "São classificações oficiais do cadastro, não o IDAP.",
    ),
    (
        "Completude e confiabilidade",
        "Completude: % dos pontos do IDAP com dado disponível. "
        "Baixa completude exige cautela na leitura do número — o IDAP projetado mostra o "
        "pior caso compatível com as lacunas.",
    ),
    (
        "PAE declarado (SNISB)",
        "Contagem de barragens com possui_pae = Sim no inventário. Em MT a maior parte "
        "está em lacuna cadastral (campo vazio ≠ “não possui”). Mancha ZAS oficial ainda "
        "não ingerida — o proxy da simulação não substitui o PAE.",
    ),
    (
        "Checklist PAE / PAEBM",
        "Oito itens por barragem (PAE-01…08): PAE SNISB, plano de segurança, revisão "
        "periódica, mancha ZAS, canal de alerta e campos SIGBM de PAEBM/cópias. "
        "Status: ok / atenção / não / lacuna. CSV na Simulação e ficha 360°; ranking etapa 48.",
    ),
    (
        "IPAPD proxy",
        "Índice de Pressão Assistencial Pós-Desastre (proposta a validar). Combina O "
        "(ocupação), A (atendimentos), P (profissionais), E (acesso), C (autonomia) e S "
        "(serviços). Termos sem dado ficam lacuna — não entram como zero. "
        "A/P/C vêm da ficha rápida JSON.",
    ),
    (
        "IRS proxy",
        "Índice de Recuperação Sanitária (§5.5.7). Escala 0–1 onde 1 = recuperado. "
        "Média das dimensões disponíveis (APS, hospitalar, água, vias, equipes, abrigos, "
        "agravos, rede de frio, crônicos, saúde mental, ambiental). "
        "Critério proposto de encerramento: IRS ≥ 0,90 por 4 semanas.",
    ),
    (
        "VIGIPÓS O/E",
        "Razão observado/esperado e canal endêmico (§5.6). Exemplo normativo: leptospirose "
        "12 vs 1,8 (limite 4) → O/E 6,7, sinal crítico. A IA explica o sinal; não o produz. "
        "Tela Streamlit «VIGIPÓS O/E»; etapa 50.",
    ),
    (
        "SITREP de cenário",
        "Markdown gerado na Simulação com exposição na mancha proxy, isolamento C7, "
        "demanda, IPAPD e status PAE. Há também CSV dos mesmos KPIs para planilha/COE.",
    ),
    (
        "HAND / relevo (simulação)",
        "Height Above Nearest Drainage — lâmina proxy a partir de MDE. Prioriza áreas "
        "baixas na mancha geométrica; não é estudo de dam break nem tempo de chegada "
        "da onda do PAE.",
    ),
]


def _blocos_html() -> str:
    partes = []
    for titulo, texto in BLOCOS:
        partes.append(
            f'<article class="bloco"><h2>{titulo}</h2><p>{texto}</p></article>'
        )
    return "\n".join(partes)


def main() -> None:
    glossario_md = ""
    if DOCS.exists():
        # Escape mínimo para <pre>: não usamos HTML bruto do markdown completo
        glossario_md = DOCS.read_text(encoding="utf-8")
        glossario_md = (
            glossario_md.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Interpretação / KPIs — VIGIBARRAGENS–MT</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root{{--ink:#15202b;--muted:#4a5d73;--paper:#e6ecf7;--card:#fff;--line:#c5d0e0;--accent:#1b3281}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:"Source Sans 3",system-ui,sans-serif;color:var(--ink);
background:radial-gradient(ellipse at 12% -10%,rgba(42,74,173,.35),transparent 45%),
linear-gradient(180deg,#1b3281 0%,#243f9a 22%,var(--paper) 22%);font-size:15px}}
header{{padding:22px 24px 14px;border-bottom:1px solid rgba(255,255,255,.18);
background:transparent;
display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;align-items:flex-end}}
.marca{{font-family:"Fraunces",Georgia,serif;font-size:clamp(1.4rem,2.4vw,1.85rem);
font-weight:600;margin:0 0 4px;letter-spacing:-.02em;color:#fff}}
header p{{margin:0;color:rgba(255,255,255,.82);max-width:40rem;line-height:1.4}}
nav a{{color:#fff;text-decoration:none;font-size:13px;font-weight:600;
padding:6px 10px;border:1px solid rgba(255,255,255,.35);background:rgba(255,255,255,.12)}}
nav a:hover{{background:rgba(255,255,255,.22)}}
main{{padding:18px 24px 48px;max-width:920px;margin:0 auto}}
.bloco{{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);
padding:14px 16px;margin:0 0 12px}}
.bloco h2{{font-family:"Fraunces",Georgia,serif;font-size:1.08rem;margin:0 0 6px;font-weight:600}}
.bloco p{{margin:0;color:#334155;line-height:1.45}}
details{{background:var(--card);border:1px solid var(--line);padding:12px 14px;margin-top:18px}}
details summary{{cursor:pointer;font-weight:600;color:var(--accent)}}
pre{{white-space:pre-wrap;font-size:12.5px;line-height:1.4;color:#334155;margin:12px 0 0}}
footer{{color:var(--muted);font-size:12px;margin-top:20px}}
</style>
</head>
<body>
<header>
  <div>
    <p class="marca">Interpretação dos indicadores</p>
    <p>Leitura operacional dos KPIs do comando, do IDAP e da simulação —
    para quem não é especialista em barragens.</p>
  </div>
  <nav>
    <a href="index.html">Comando estadual</a>
    <a href="simulacao.html">Simulação</a>
    <a href="barragem.html">Barragem 360°</a>
  </nav>
</header>
<main>
{_blocos_html()}
<details>
  <summary>Glossário completo (documentação)</summary>
  <pre>{glossario_md or "Arquivo docs/10-glossario.md ausente."}</pre>
</details>
<footer>Gerado em {dt.datetime.now().strftime("%d/%m/%Y %H:%M")} · VIGIBARRAGENS–MT / Saúde 360</footer>
</main>
</body>
</html>
"""
    SAIDA.mkdir(parents=True, exist_ok=True)
    destino = SAIDA / "glossario.html"
    destino.write_text(html, encoding="utf-8")
    print(f"Glossário — gravado {destino.relative_to(comum.RAIZ)} ({destino.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
