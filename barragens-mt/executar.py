"""Executa o pipeline completo, da coleta ao painel.

Uso:
    python executar.py            # roda todas as etapas padrão, na ordem
    python executar.py 05 06 07   # roda apenas as etapas indicadas

A etapa 04 (painel Power BI do SNISB) está fora do conjunto padrão: o Produto 04
classifica a fonte como não conforme. Ela só roda quando nomeada explicitamente, e
mesmo assim o próprio script exige confirmação.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
SCRIPTS = RAIZ / "scripts"

# (código, arquivo, descrição, entra no conjunto padrão)
ETAPAS = [
    ("01", "01_snisb_mt.py", "Inventário SNISB (ANA) para MT", True),
    ("02", "02_sigbm_anm.py", "Barragens de mineração (SIGBM/ANM)", True),
    ("03", "03_ibge_mt.py", "Base territorial do IBGE", True),
    ("26", "26_ibge_populacao.py", "População municipal IBGE (Censo/estimativa)", True),
    ("04", "04_powerbi_snisb.py", "Painel SNISB — FONTE NÃO CONFORME (PBI-01)", False),
    ("05", "05_consolidar_inventario.py", "Inventário consolidado", True),
    ("06", "06_mapas.py", "Mapas cartográficos", True),
    ("07", "07_painel.py", "Painel inventário / fiscalização", True),
    ("08", "08_diagnostico.py", "Relatório de diagnóstico", True),
    ("09", "09_hidrografia_ana.py", "Hidrografia ottocodificada (BHO/ANA)", True),
    ("10", "10_populacoes_vulneraveis.py", "Populações vulneráveis (FUNAI, INCRA, Palmares)", True),
    # A etapa 12 vem antes da 11 de propósito: é ela que publica o recorte territorial
    # por topologia de drenagem, e a coleta do CNES precisa saber quais municípios pedir.
    # A ordem de execução é a desta lista, não a do número da etapa.
    ("12", "12_analise_cuiaba.py", "Exposição de Cuiabá por posição na bacia", True),
    ("11", "11_cnes_rede_saude.py", "Rede de saúde (CNES) na região de Cuiabá", True),
    ("13", "13_exposicao_populacoes.py", "Exposição de populações e da rede ao eixo", True),
    ("14", "14_mapas_cuiaba.py", "Mapas de Cuiabá, Manso e entorno", True),
    ("15", "15_relatorio_produto04.py", "Relatório Produto 04 (.docx ABNT)", True),
    # Hidro antes do IDAP: a dimensão A consome hidro_barragens_mt.csv.
    ("17", "17_hidro_sisclima_titan.py", "Hidro SisClima/TITAN → IDAP dimensão A", True),
    # Contatos antes do IDAP: alimenta D8 e a flag alertável do piloto.
    ("19", "19_contatos_alertabilidade.py", "Contatos e alertabilidade do piloto", True),
    ("16", "16_idap_estadual.py", "IDAP estadual (todas as barragens de MT)", True),
    ("18", "18_piloto_manso_cuiaba.py", "Piloto operacional Manso–Cuiabá", True),
    ("20", "20_painel_comando.py", "Painel comando estadual (Tela 1)", True),
    ("21", "21_painel_hidro.py", "Painel hidro municipal (Tela 2 leve)", True),
    ("22", "22_fila_alertas.py", "Fila de alertas do piloto (Tela 4 leve)", True),
    ("23", "23_simulacao_cenario.py", "Simulação volume → área atingida (proxy)", True),
    ("24", "24_video_simulacao.py", "GIF animado da simulação (Manso)", True),
    ("25", "25_barragem_360.py", "Barragem 360° (Tela 3)", True),
    ("27", "27_glossario_painel.py", "Interpretação / KPIs (glossário operacional)", True),
    ("28", "28_mapa_tipologia.py", "Mapa estadual por tipologia de uso", True),
    ("29", "29_despacho_alertas.py", "Despacho alertas (dry-run Telegram/e-mail)", True),
    ("30", "30_cnes_estadual_scaffold.py", "Scaffold CNES estadual (municípios-alvo)", True),
    ("31", "31_onda3_scaffolds.py", "Scaffolds PAE / Sisagua / VIGIPÓS", True),
    ("32", "32_rag_indice_docs.py", "Índice documental RAG leve", True),
    ("33", "33_cnes_estadual.py", "Coleta CNES estadual (municípios com barragem)", True),
    (
        "34",
        "34_contatos_validacao_exercicio.py",
        "Validação exercício de contatos do eixo (D8/alertável)",
        False,
    ),
    (
        "35",
        "35_mde_hand_piloto.py",
        "MDE/HAND piloto Manso–Cuiabá (OpenTopoData/SRTM)",
        False,
    ),
    (
        "36",
        "36_contatos_importar_emails.py",
        "Importar e-mails validados para contatos do eixo",
        False,
    ),
    (
        "37",
        "37_ibge_setores_eixo.py",
        "Setores censitários IBGE 2022 no eixo Manso–Cuiabá",
        False,
    ),
    (
        "38",
        "38_sisagua_captacoes.py",
        "Captações Sisagua/OSM no eixo (KPI C4)",
        False,
    ),
    (
        "39",
        "39_telemetria_hidro_a.py",
        "Telemetria pontual INMET/Open-Meteo → dimensão A",
        False,
    ),
    (
        "40",
        "40_escolas_inep_eixo.py",
        "Escolas INEP/OSM no eixo (KPI C5)",
        False,
    ),
    (
        "41",
        "41_mapbiomas_eixo.py",
        "MapBiomas pressão urbana no eixo Manso–Cuiabá",
        False,
    ),
    (
        "42",
        "42_malha_dnit_osm_eixo.py",
        "Malha BR/MT no eixo (proxy DNIT via OSM)",
        False,
    ),
    (
        "43",
        "43_indicasus_leitos_dw.py",
        "IndicaSUS/DW — leitos e ocupação (D6)",
        False,
    ),
    (
        "44",
        "44_dw_extrair.py",
        "DW genérico — SIH/SIA/SISREG/SINAN",
        False,
    ),
    (
        "45",
        "45_cnes_leitos_cadastrados.py",
        "CNES LT — leitos cadastrados (SAU-01)",
        False,
    ),
    (
        "46",
        "46_ativos_essenciais_osm_eixo.py",
        "Ativos essenciais OSM no eixo (C5 ETA/ETE/energia/abrigos)",
        False,
    ),
]


def main() -> None:
    escolhidas = set(sys.argv[1:])
    if escolhidas:
        etapas = [e for e in ETAPAS if e[0] in escolhidas]
    else:
        etapas = [e for e in ETAPAS if e[3]]
    if not etapas:
        sys.exit(f"nenhuma etapa corresponde a {sorted(escolhidas)}")

    falhas: list[str] = []
    for codigo, arquivo, descricao, _ in etapas:
        print(f"\n{'=' * 78}\n[{codigo}] {descricao}\n{'=' * 78}")
        inicio = time.time()
        resultado = subprocess.run([sys.executable, str(SCRIPTS / arquivo)], cwd=RAIZ)
        duracao = time.time() - inicio
        if resultado.returncode == 0:
            print(f"  concluído em {duracao:.1f}s")
        else:
            print(f"  FALHOU (código {resultado.returncode})")
            falhas.append(codigo)

    print(f"\n{'=' * 78}")
    if falhas:
        print(f"etapas com falha: {', '.join(falhas)}")
        sys.exit(1)
    print(f"pipeline concluído — {len(etapas)} etapa(s)")
    print("  comando:     painel/index.html")
    print("  barragem:    painel/barragem.html")
    print("  hidro:       painel/hidro.html")
    print("  alertas:     painel/alertas.html")
    print("  simulação:   painel/simulacao.html")
    print("  inventário:  painel/inventario.html")
    print("  piloto:      painel/piloto_manso_cuiaba.html")
    print("  ficha:       painel/ficha_rapida.html")
    print("  mapas:       figuras/")
    print("  diagnóstico: relatorios/diagnostico_barragens_mt.md")
    print("  produto 04:  produtos/produto-04/")


if __name__ == "__main__":
    main()
