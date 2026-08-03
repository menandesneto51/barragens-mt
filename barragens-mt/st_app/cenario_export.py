"""Exporta KPIs do cenário de simulação em CSV (sep ;)."""

from __future__ import annotations

import csv
import io
from typing import Any


def montar_csv_cenario(cenario: dict[str, Any]) -> str:
    """Uma linha de cabeçalho + uma linha de valores (operacional)."""
    ordem = [
        ("barragem", "Barragem"),
        ("municipio", "Município"),
        ("id_snisb", "ID SNISB"),
        ("geometria", "Geometria ativa"),
        ("pop_exposta", "População exposta"),
        ("n_setores", "Setores na mancha"),
        ("n_captacoes", "Captações"),
        ("n_escolas", "Escolas"),
        ("n_ativos", "Ativos essenciais"),
        ("n_us_atingidas", "US atingidas"),
        ("n_us_isoladas", "US isoladas"),
        ("n_vias", "Vias"),
        ("n_pontes", "Pontes"),
        ("pessoas_isoladas", "Pessoas isoladas (proxy)"),
        ("n_sedes_sem_rota", "Sedes sem rota"),
        ("n_sedes_com_desvio", "Sedes com desvio"),
        ("delta_km_medio_desvio", "Desvio médio km"),
        ("nivel_c7", "Nível C7"),
        ("mapbiomas_ha_urbana", "MapBiomas urbana sede ha"),
        ("mapbiomas_ha_drenagem_baixa", "MapBiomas urbana drenagem baixa ha"),
        ("mapbiomas_pct_drenagem_baixa", "MapBiomas % drenagem baixa"),
        ("chuva_24h_mm", "Chuva 24h mm"),
        ("chuva_72h_mm", "Chuva 72h mm"),
        ("chuva_prevista_mm", "Chuva prevista 24-72h mm"),
        ("percentil_climatologico", "Percentil climatológico"),
        ("fonte_telemetria", "Fonte telemetria A"),
        ("aproximacao_espacial", "Aproximação espacial A"),
        ("pressao_estrutural", "Pressão estrutural CNES"),
        ("leitos_disponiveis", "Leitos disponíveis"),
        ("demanda_internacao", "Demanda internação"),
        ("demanda_agua", "Demanda água L/dia"),
        ("ipapd", "IPAPD"),
        ("ipapd_rotulo", "IPAPD rótulo"),
        ("ipapd_completude", "IPAPD completude"),
        ("irs", "IRS"),
        ("irs_rotulo", "IRS rótulo"),
        ("irs_completude", "IRS completude"),
        ("pae_status", "PAE SNISB"),
        ("pae_lacunas", "Itens PAE lacuna/não"),
    ]
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\n")
    w.writerow([lab for _, lab in ordem])
    w.writerow([cenario.get(k, "") for k, _ in ordem])
    return buf.getvalue()
