"""Cenário executável do IDAP-Barragens: `python scripts/idap/exemplo.py`.

Roda sem rede e sem arquivo de entrada. Monta quatro barragens fictícias, mas plausíveis
para Mato Grosso, em situações distintas, e imprime o IDAP, a faixa, as justificativas
por indicador e o alerta formatado de cada uma.

Os nomes e os empreendedores são inventados. Os municípios são reais e foram escolhidos
por concentrarem barragens no inventário coletado (Nossa Senhora do Livramento com 101,
Sorriso com 84, Poconé com 60 e Pontes e Lacerda com 24).
"""

from __future__ import annotations

from datetime import datetime

try:
    from .calculo import calcular_idap, formatar_numero
    from .modelo import (
        CapacidadeResposta,
        CondicaoEstrutura,
        EstadoBarragem,
        ExposicaoSanitaria,
        PressaoHidroclimatica,
        SinaisOperacionais,
    )
    from .pesos import STATUS_VERSAO_PESOS, VERSAO_PESOS
    from .regras import aplicar_regras
    from .relatorio import FUSO_CUIABA, montar_alerta, montar_resumo
except ImportError:  # python scripts/idap/exemplo.py
    from calculo import calcular_idap, formatar_numero  # type: ignore[no-redef]
    from modelo import (  # type: ignore[no-redef]
        CapacidadeResposta,
        CondicaoEstrutura,
        EstadoBarragem,
        ExposicaoSanitaria,
        PressaoHidroclimatica,
        SinaisOperacionais,
    )
    from pesos import STATUS_VERSAO_PESOS, VERSAO_PESOS  # type: ignore[no-redef]
    from regras import aplicar_regras  # type: ignore[no-redef]
    from relatorio import FUSO_CUIABA, montar_alerta, montar_resumo  # type: ignore[no-redef]

INSTANTE = datetime(2026, 7, 29, 15, 30, tzinfo=FUSO_CUIABA)


def cenario_verde() -> EstadoBarragem:
    """Barragem de irrigação em normalidade, com telemetria ausente como única ressalva."""
    return EstadoBarragem(
        id_barragem="MT-EX-0001",
        nome="Barragem Fazenda Alto do Teles",
        municipio="Sorriso",
        instante=INSTANTE,
        orgao_fiscalizador="MT - Secretaria de Estado do Meio Ambiente - SEMA",
        empreendedor="Agropecuária Alto do Teles Ltda. (fictícia)",
        uso_principal="Irrigação",
        municipios_zas=("Sorriso",),
        regiao_saude="Região de Saúde Teles Pires",
        pressao=PressaoHidroclimatica(
            chuva_24h_mm=6.0,
            chuva_72h_mm=18.0,
            chuva_prevista_24_72h_mm=12.0,
            percentil_climatologico=35.0,
            saturacao_antecedente=0.32,
            razao_nivel_cota_alerta=0.55,
            dias_consecutivos_chuva_intensa=0,
        ),
        estrutura=CondicaoEstrutura(
            categoria_risco="Baixo",
            nivel_emergencia="Sem emergência",
            situacao_estabilidade="Não se aplica",
            pior_nota_anomalia=0.0,
            razao_volume_capacidade=0.62,
            situacao_telemetria="Ausente ou sem transmissão",
        ),
        exposicao=ExposicaoSanitaria(
            populacao_zas=12,
            proporcao_vulneravel=0.14,
            unidades_saude_sem_internacao=0,
            unidades_saude_com_internacao=0,
            hospital_referencia_ameacado=False,
            captacao_ameacada="Nenhuma",
            servicos_essenciais_ameacados=0,
            tempo_chegada_onda_min=480.0,
            isolamento_rodoviario="Rotas alternativas pavimentadas",
            contaminante_predominante="Água sem rejeito",
        ),
        capacidade=CapacidadeResposta(
            situacao_plano_emergencia="Vigente sem articulação municipal",
            meses_desde_ultimo_simulado=20.0,
            cobertura_alerta_zas=0.95,
            razao_vagas_abrigo=1.4,
            ambulancias_por_10mil=1.2,
            razao_leitos_demanda=1.1,
            possui_rota_alternativa=True,
            contatos_validados_90d=True,
        ),
    )


def cenario_laranja() -> EstadoBarragem:
    """Barragem de rejeito sob chuva persistente, em nível de alerta declarado."""
    return EstadoBarragem(
        id_barragem="MT-EX-0002",
        nome="Barragem de Rejeito Serra do Tombador",
        municipio="Nossa Senhora do Livramento",
        instante=INSTANTE,
        orgao_fiscalizador="Agência Nacional de Mineração - ANM",
        empreendedor="Tombador Mineração SPE Ltda. (fictícia)",
        uso_principal="Contenção de rejeitos de mineração",
        municipios_zas=("Nossa Senhora do Livramento", "Poconé"),
        regiao_saude="Região de Saúde Baixada Cuiabana",
        pressao=PressaoHidroclimatica(
            chuva_24h_mm=38.0,
            chuva_72h_mm=72.0,
            chuva_prevista_24_72h_mm=30.0,
            percentil_climatologico=78.0,
            saturacao_antecedente=0.68,
            razao_nivel_cota_alerta=0.82,
            dias_consecutivos_chuva_intensa=2,
        ),
        estrutura=CondicaoEstrutura(
            categoria_risco="Média",
            nivel_emergencia="Nível de Alerta",
            situacao_estabilidade="Atestado",
            pior_nota_anomalia=2.0,
            razao_volume_capacidade=0.85,
            situacao_telemetria=(
                "Existe instrumentação em desacordo com o projeto, porém em processo de instalação"
            ),
        ),
        exposicao=ExposicaoSanitaria(
            populacao_zas=340,
            proporcao_vulneravel=0.22,
            unidades_saude_sem_internacao=1,
            unidades_saude_com_internacao=0,
            hospital_referencia_ameacado=False,
            captacao_ameacada="Sistema isolado ou rural",
            servicos_essenciais_ameacados=1,
            tempo_chegada_onda_min=45.0,
            isolamento_rodoviario="Rota única com desvio precário",
            contaminante_predominante="Rejeito não inerte ou perigoso",
        ),
        capacidade=CapacidadeResposta(
            situacao_plano_emergencia="Vigente sem articulação municipal",
            meses_desde_ultimo_simulado=40.0,
            cobertura_alerta_zas=0.55,
            razao_vagas_abrigo=0.60,
            ambulancias_por_10mil=0.70,
            razao_leitos_demanda=0.80,
            possui_rota_alternativa=True,
            contatos_validados_90d=False,
        ),
    )


def cenario_vermelho_por_regra() -> EstadoBarragem:
    """Índice na faixa amarela, elevado a vermelho pela regra R01 (emergência nível 2).

    É o caso que justifica a camada determinística: a bacia está calma, a exposição é
    pequena e a capacidade de resposta é boa, mas o empreendedor declarou emergência de
    nível 2. Um índice ponderado sozinho diluiria o sinal mais grave.
    """
    return EstadoBarragem(
        id_barragem="MT-EX-0003",
        nome="Barragem de Rejeitos São Bento II",
        municipio="Poconé",
        instante=INSTANTE,
        orgao_fiscalizador="Agência Nacional de Mineração - ANM",
        empreendedor="São Bento Extração Mineral Ltda. (fictícia)",
        uso_principal="Contenção de rejeitos de mineração",
        municipios_zas=("Poconé",),
        regiao_saude="Região de Saúde Baixada Cuiabana",
        pressao=PressaoHidroclimatica(
            chuva_24h_mm=15.0,
            chuva_72h_mm=40.0,
            chuva_prevista_24_72h_mm=25.0,
            percentil_climatologico=60.0,
            saturacao_antecedente=0.50,
            razao_nivel_cota_alerta=0.60,
            dias_consecutivos_chuva_intensa=1,
        ),
        estrutura=CondicaoEstrutura(
            categoria_risco="Média",
            nivel_emergencia="Emergência Nivel 2",
            situacao_estabilidade="Atestada mas vencida",
            pior_nota_anomalia=3.0,
            razao_volume_capacidade=0.70,
            situacao_telemetria="Existe instrumentação de acordo com o projeto técnico",
        ),
        exposicao=ExposicaoSanitaria(
            populacao_zas=150,
            proporcao_vulneravel=0.18,
            unidades_saude_sem_internacao=1,
            unidades_saude_com_internacao=0,
            hospital_referencia_ameacado=False,
            captacao_ameacada="Nenhuma",
            servicos_essenciais_ameacados=0,
            tempo_chegada_onda_min=90.0,
            isolamento_rodoviario="Rotas alternativas pavimentadas",
            contaminante_predominante="Rejeito não inerte ou perigoso",
        ),
        capacidade=CapacidadeResposta(
            situacao_plano_emergencia="Vigente, testado e articulado",
            meses_desde_ultimo_simulado=8.0,
            cobertura_alerta_zas=0.92,
            razao_vagas_abrigo=1.20,
            ambulancias_por_10mil=1.50,
            razao_leitos_demanda=1.30,
            possui_rota_alternativa=True,
            contatos_validados_90d=True,
        ),
    )


def cenario_roxo() -> EstadoBarragem:
    """Rompimento confirmado, com duas lacunas de dado para exercitar a completude."""
    return EstadoBarragem(
        id_barragem="MT-EX-0004",
        nome="Barragem Córrego do Tenente",
        municipio="Pontes e Lacerda",
        instante=INSTANTE,
        orgao_fiscalizador="Agência Nacional de Mineração - ANM",
        empreendedor="Tenente Recursos Minerais Ltda. (fictícia)",
        uso_principal="Contenção de rejeitos de mineração",
        municipios_zas=("Pontes e Lacerda", "Vale de São Domingos", "Jauru"),
        regiao_saude="Região de Saúde Oeste",
        pressao=PressaoHidroclimatica(
            chuva_24h_mm=134.0,
            chuva_72h_mm=210.0,
            # Previsão e percentil climatológico indisponíveis neste ciclo: entram como
            # lacuna e reduzem a completude, sem inflar a pontuação.
            chuva_prevista_24_72h_mm=None,
            percentil_climatologico=None,
            saturacao_antecedente=0.94,
            razao_nivel_cota_alerta=1.35,
            dias_consecutivos_chuva_intensa=5,
        ),
        estrutura=CondicaoEstrutura(
            categoria_risco="Alta",
            nivel_emergencia="Emergência Nivel 3",
            situacao_estabilidade="Não Enviado",
            pior_nota_anomalia=8.0,
            razao_volume_capacidade=1.02,
            situacao_telemetria="Ausente ou sem transmissão",
        ),
        exposicao=ExposicaoSanitaria(
            populacao_zas=2_100,
            proporcao_vulneravel=0.31,
            unidades_saude_sem_internacao=3,
            unidades_saude_com_internacao=1,
            hospital_referencia_ameacado=True,
            captacao_ameacada="Captação principal de sede municipal ou única captação",
            servicos_essenciais_ameacados=4,
            tempo_chegada_onda_min=22.0,
            isolamento_rodoviario="Acesso único sem alternativa",
            contaminante_predominante="Rejeito não inerte ou perigoso",
        ),
        capacidade=CapacidadeResposta(
            situacao_plano_emergencia="Inexistente",
            meses_desde_ultimo_simulado=None,
            cobertura_alerta_zas=0.10,
            razao_vagas_abrigo=0.30,
            ambulancias_por_10mil=0.40,
            razao_leitos_demanda=0.35,
            possui_rota_alternativa=False,
            contatos_validados_90d=False,
        ),
        sinais=SinaisOperacionais(
            rompimento_confirmado=True,
            perda_subita_de_nivel=True,
            evacuacao_determinada=True,
            sensores_criticos_em_falha=3,
            mancha_atinge_unidade_estrategica=True,
            mancha_atinge_captacao=True,
            municipios_zas_sem_confirmacao=("Vale de São Domingos",),
        ),
    )


CENARIOS = (
    ("Cenário 1 — normalidade", cenario_verde),
    ("Cenário 2 — mobilização por pontuação", cenario_laranja),
    ("Cenário 3 — elevação por regra determinística", cenario_vermelho_por_regra),
    ("Cenário 4 — rompimento confirmado", cenario_roxo),
)


def main() -> None:
    print("IDAP-Barragens — cenário demonstrativo")
    print(f"Versão dos pesos: {VERSAO_PESOS}")
    print(f"Situação da calibração: {STATUS_VERSAO_PESOS}")
    print(f"Instante de referência: {INSTANTE:%d/%m/%Y %H:%M} (horário de Cuiabá, UTC-4)")

    finais = []
    for titulo, construtor in CENARIOS:
        estado = construtor()
        resultado = calcular_idap(estado)
        final = aplicar_regras(estado, resultado)
        finais.append((titulo, estado, final))

        print()
        print("-" * 78)
        print(f"{titulo}: {estado.nome} — {estado.municipio}")
        print("-" * 78)
        print(
            f"IDAP {resultado.idap}/100 | faixa do índice: {resultado.nivel.rotulo} | "
            f"nível final: {final.nivel_final.rotulo} ({final.nivel_final.significado})"
        )
        print(
            f"Completude {resultado.completude:.0%} ({resultado.confiabilidade}) | "
            f"IDAP projetado {formatar_numero(resultado.idap_projetado)} | lacunas: "
            f"{', '.join(resultado.lacunas) if resultado.lacunas else 'nenhuma'}"
        )
        for dimensao in resultado.dimensoes:
            print(
                f"  {dimensao.codigo}. {dimensao.nome:<34s} "
                f"{dimensao.pontos:>3d}/{dimensao.teto:<3d} "
                f"completude {dimensao.completude:>4.0%}"
            )
        print("  Justificativas (indicadores com pontuação acima de zero):")
        for justificativa in resultado.justificativas():
            print(f"    - {justificativa}")
        if final.regras_disparadas:
            print("  Regras determinísticas disparadas:")
            for regra in final.regras_disparadas:
                print(f"    - {regra.descrever()}")

    print()
    print("=" * 78)
    print("RESUMO PARA A SALA DE SITUAÇÃO")
    print("=" * 78)
    for _, _, final in finais:
        print(f"  {montar_resumo(final)}")

    for titulo, estado, final in finais:
        print()
        print(f"### Alerta formatado — {titulo}")
        print()
        print(montar_alerta(estado, final))


if __name__ == "__main__":
    main()
