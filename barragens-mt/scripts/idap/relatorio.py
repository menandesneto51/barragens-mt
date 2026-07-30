"""Geração do texto do alerta a partir de um resultado de cálculo.

O formato reproduz o conteúdo mínimo definido em `docs/04-alertas.md`. O texto é gerado
por função pura para que o mesmo resultado sempre produza o mesmo alerta — condição para
auditar depois o que foi comunicado a cada gestor.

Fuso horário: Cuiabá está em UTC-4 e não adota horário de verão desde 2019, então o
deslocamento fixo é suficiente e evita depender do banco IANA, que o CPython não embarca
no Windows.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

try:
    from . import pesos
    from .calculo import NivelAlerta, ResultadoIdap, formatar_numero
    from .impacto_sanitario import (
        linhas_alerta,
        perfil_de,
    )
    from .modelo import EstadoBarragem
    from .regras import ResultadoFinal
except ImportError:  # execução direta de um módulo do pacote
    import pesos  # type: ignore[no-redef]
    from calculo import NivelAlerta, ResultadoIdap, formatar_numero  # type: ignore[no-redef]
    from impacto_sanitario import (  # type: ignore[no-redef]
        linhas_alerta,
        perfil_de,
    )
    from modelo import EstadoBarragem  # type: ignore[no-redef]
    from regras import ResultadoFinal  # type: ignore[no-redef]

FUSO_CUIABA = timezone(timedelta(hours=-4), "Cuiabá (UTC-4)")

RESSALVA_OBRIGATORIA = "Este alerta não constitui ordem de evacuação."

# Prazos de confirmação de recebimento por faixa, em minutos. Proposta a validar com a
# Defesa Civil e as regiões de saúde.
PRAZO_CONFIRMACAO_MIN: dict[NivelAlerta, int | None] = {
    NivelAlerta.VERDE: None,
    NivelAlerta.AMARELO: 120,
    NivelAlerta.LARANJA: 60,
    NivelAlerta.VERMELHO: 20,
    NivelAlerta.ROXO: 10,
}

ACOES_POR_NIVEL: dict[NivelAlerta, tuple[str, ...]] = {
    NivelAlerta.VERDE: (
        "Manter a rotina de monitoramento e a atualização cadastral da barragem.",
        "Revalidar os contatos institucionais da ZAS a cada 90 dias.",
    ),
    NivelAlerta.AMARELO: (
        "Acompanhar a evolução da chuva e do nível a jusante nas próximas 24 h.",
        "Confirmar com o empreendedor a condição da estrutura e da instrumentação.",
        "Verificar a vigência do plano de emergência e a lista de contatos dos municípios da ZAS.",
    ),
    NivelAlerta.LARANJA: (
        "Acionar a Vigilância em Saúde e a Defesa Civil dos municípios da ZAS.",
        "Conferir disponibilidade de leitos, ambulâncias, abrigos e estoques estratégicos.",
        "Ativar monitoramento reforçado da qualidade da água nas captações a jusante.",
        "Listar pacientes dependentes de tecnologia (diálise, oxigênio, acamados) na área exposta.",
        "Preparar, sem executar, a logística de transporte sanitário e de abrigos.",
    ),
    NivelAlerta.VERMELHO: (
        "Colocar a Sala de Situação em prontidão e definir o responsável de plantão.",
        "Notificar hospitais de referência, SAMU, CIEVS e concessionária de água.",
        "Pré-posicionar ambulâncias, kits de medicamento e água potável fora da mancha.",
        "Articular com a Defesa Civil a comunicação de risco à população da ZAS.",
        "Confirmar rotas alternativas e pontos de encontro previstos no plano.",
    ),
    NivelAlerta.ROXO: (
        "Ativar o COE estadual e o módulo VIGIPÓS-BARRAGENS.",
        "Iniciar a ficha rápida de saúde pós-desastre nos municípios atingidos.",
        "Acionar abrigos, transporte sanitário e reforço assistencial.",
        "Suspender captações comprometidas e iniciar abastecimento alternativo.",
        "Emitir o primeiro SITREP em até 1 h e mantê-lo em cadência definida pelo COE.",
    ),
}


def _agora_cuiaba(instante: datetime) -> datetime:
    if instante.tzinfo is None:
        return instante.replace(tzinfo=FUSO_CUIABA)
    return instante.astimezone(FUSO_CUIABA)


def identificador_alerta(estado: EstadoBarragem) -> str:
    momento = _agora_cuiaba(estado.instante)
    return f"ALERTA-{momento:%Y%m%d-%H%M}-{estado.id_barragem}"


def montar_resumo(final: ResultadoFinal) -> str:
    """Linha única para painel, log e lista de eventos."""
    r = final.resultado
    elevacao = (
        f" (elevado de {final.nivel_indice.rotulo} por regra determinística)"
        if final.elevado_por_regra
        else ""
    )
    return (
        f"{r.nome} ({r.municipio}) — IDAP {r.idap}/100 — "
        f"{final.nivel_final.rotulo}: {final.nivel_final.significado}{elevacao} — "
        f"completude {r.completude:.0%} ({r.confiabilidade})"
    )


def _perfil_estado(estado: EstadoBarragem):
    return perfil_de(
        estado.uso_principal,
        estado.orgao_fiscalizador,
        estado.exposicao.contaminante_predominante,
    )


def _estimativa_exposicao(estado: EstadoBarragem) -> dict | None:
    exposicao = estado.exposicao
    if exposicao.populacao_zas is None and exposicao.area_estimada_km2 is None:
        return None
    return {
        "populacao_estimada": exposicao.populacao_zas or 0,
        "metodo": exposicao.metodo_estimativa_populacao or "nao_informado",
        "detalhe": exposicao.detalhe_estimativa_populacao
        or "Estimativa injetada no estado operacional.",
        "area_km2": exposicao.area_estimada_km2,
        "densidade_hab_km2": None,
    }


def _bloco_impacto_sanitario(estado: EstadoBarragem) -> list[str]:
    perfil = _perfil_estado(estado)
    estimativa = _estimativa_exposicao(estado)
    return linhas_alerta(perfil, estimativa)


def _bloco_populacao(estado: EstadoBarragem) -> list[str]:
    exposicao = estado.exposicao
    linhas: list[str] = []
    if exposicao.populacao_zas is None:
        linhas.append(
            "   População na ZAS: não estimada no cadastro — ver bloco 5 (proxy área×densidade "
            "quando volume disponível no piloto/simulação)."
        )
    else:
        linhas.append(
            f"   População residente estimada na ZAS: "
            f"{formatar_numero(exposicao.populacao_zas)} pessoas."
        )
    if exposicao.proporcao_vulneravel is not None and exposicao.populacao_zas:
        vulneraveis = round(exposicao.populacao_zas * exposicao.proporcao_vulneravel)
        linhas.append(
            f"   Em grupos prioritários: cerca de {formatar_numero(vulneraveis)} pessoas "
            f"({exposicao.proporcao_vulneravel:.0%})."
        )
    if exposicao.tempo_chegada_onda_min is not None:
        linhas.append(
            f"   Tempo estimado de chegada da onda à primeira ocupação: "
            f"{formatar_numero(exposicao.tempo_chegada_onda_min)} min."
        )
    if exposicao.contaminante_predominante:
        linhas.append(
            f"   Material predominante no reservatório: {exposicao.contaminante_predominante}."
        )
    return linhas


def _bloco_saude(estado: EstadoBarragem) -> list[str]:
    exposicao = estado.exposicao
    linhas: list[str] = []
    sem_internacao = exposicao.unidades_saude_sem_internacao
    com_internacao = exposicao.unidades_saude_com_internacao
    if sem_internacao is None and com_internacao is None:
        linhas.append("   Não avaliado — cruzamento CNES x mancha de inundação pendente.")
        return linhas
    linhas.append(
        f"   Unidades sem internação na mancha ou sem via de acesso: {sem_internacao or 0}."
    )
    linhas.append(f"   Unidades com internação ou urgência: {com_internacao or 0}.")
    if exposicao.hospital_referencia_ameacado:
        linhas.append(
            "   ATENÇÃO: hospital de referência regional ou única unidade do município ameaçado."
        )
    if exposicao.captacao_ameacada and exposicao.captacao_ameacada != "Nenhuma":
        linhas.append(f"   Captação de água ameaçada: {exposicao.captacao_ameacada}.")
    return linhas


def montar_alerta(estado: EstadoBarragem, final: ResultadoFinal) -> str:
    """Monta o texto integral do alerta territorializado."""
    r: ResultadoIdap = final.resultado
    nivel = final.nivel_final
    momento = _agora_cuiaba(estado.instante)
    prazo = PRAZO_CONFIRMACAO_MIN[nivel]
    largura = 78

    linhas: list[str] = []
    linhas.append("=" * largura)
    linhas.append(
        f"ALERTA VIGIBARRAGENS-MT — NÍVEL {nivel.rotulo.upper()} ({nivel.significado.upper()})"
    )
    linhas.append("=" * largura)
    linhas.append(f"Identificador do alerta : {identificador_alerta(estado)}")
    linhas.append(f"Barragem                : {estado.nome} (código {estado.id_barragem})")
    linhas.append(f"Município da estrutura  : {estado.municipio} — MT")
    linhas.append(f"Órgão fiscalizador      : {estado.orgao_fiscalizador or 'não informado'}")
    linhas.append(f"Empreendedor            : {estado.empreendedor or 'não informado'}")
    linhas.append(f"Uso principal           : {estado.uso_principal or 'não informado'}")
    linhas.append(f"Região de saúde         : {estado.regiao_saude or 'não vinculada'}")
    linhas.append(f"Data e hora da emissão  : {momento:%d/%m/%Y %H:%M} (horário de Cuiabá, UTC-4)")
    linhas.append(
        f"IDAP                    : {r.idap} de {pesos.TETO_IDAP} pontos "
        f"(faixa {r.nivel.rotulo}: {r.nivel.significado})"
    )
    if final.elevado_por_regra:
        linhas.append(
            f"Nível final             : {nivel.rotulo} — elevado por regra determinística"
        )
    else:
        linhas.append(f"Nível final             : {nivel.rotulo}")
    linhas.append(
        f"Completude do cálculo   : {r.completude:.0%} "
        f"(confiabilidade {r.confiabilidade}; IDAP projetado {formatar_numero(r.idap_projetado)})"
    )
    linhas.append(f"Versão dos pesos        : {r.versao_pesos}")
    linhas.append("")

    linhas.append("1. MOTIVOS")
    justificativas = r.justificativas()
    if justificativas:
        linhas.extend(f"   - {texto}" for texto in justificativas)
    else:
        linhas.append("   - Nenhum indicador com pontuação acima de zero foi apurado.")
    linhas.append("")
    linhas.append("   Pontuação por dimensão:")
    for dimensao in r.dimensoes:
        linhas.append(
            f"   - {dimensao.codigo}. {dimensao.nome}: {dimensao.pontos}/{dimensao.teto} "
            f"(completude {dimensao.completude:.0%})"
        )
    linhas.append("")

    linhas.append("2. POPULAÇÃO POTENCIALMENTE EXPOSTA")
    linhas.extend(_bloco_populacao(estado))
    linhas.append("")

    linhas.append("3. UNIDADES DE SAÚDE EM RISCO DE INUNDAÇÃO OU ISOLAMENTO")
    linhas.extend(_bloco_saude(estado))
    linhas.append("")

    linhas.append("4. MUNICÍPIOS POTENCIALMENTE AFETADOS")
    if estado.municipios_zas:
        linhas.extend(f"   - {municipio}" for municipio in estado.municipios_zas)
    else:
        linhas.append("   - Vínculo territorial não cadastrado — pendência bloqueante para emissão.")
    if estado.sinais.municipios_zas_sem_confirmacao:
        linhas.append(
            "   Sem confirmação de recebimento: "
            + ", ".join(estado.sinais.municipios_zas_sem_confirmacao)
        )
    linhas.append("")

    linhas.append("5. IMPACTO SANITÁRIO POR TIPO DE ESTRUTURA")
    linhas.extend(_bloco_impacto_sanitario(estado))
    linhas.append("")

    linhas.append("6. REGRAS DETERMINÍSTICAS DISPARADAS")
    if final.regras_disparadas:
        linhas.extend(f"   - {regra.descrever()}" for regra in final.regras_disparadas)
    else:
        linhas.append("   - Nenhuma.")
    linhas.append("")

    linhas.append("7. AÇÕES RECOMENDADAS")
    linhas.extend(f"   - {acao}" for acao in ACOES_POR_NIVEL[nivel])
    perfil = _perfil_estado(estado)
    for acao in perfil.acoes_especificas[:4]:
        linhas.append(f"   - [perfil {perfil.codigo}] {acao}")
    if r.lacunas:
        linhas.append(
            "   - Sanar as lacunas de dado que subestimam o índice: "
            + ", ".join(r.lacunas)
            + "."
        )
    linhas.append("")

    linhas.append("8. FONTES DOS DADOS")
    fontes = sorted({i.fonte for i in r.indicadores if not i.ausente})
    if fontes:
        linhas.extend(f"   - {fonte}" for fonte in fontes)
    else:
        linhas.append("   - Nenhuma fonte apurada neste ciclo.")
    linhas.append("   - Perfil sanitário: scripts/idap/impacto_sanitario.py (água vs rejeito)")
    linhas.append("")

    linhas.append("9. RESSALVAS")
    linhas.append(f"   {RESSALVA_OBRIGATORIA} A determinação de evacuação é competência")
    linhas.append("   exclusiva da Defesa Civil e das autoridades responsáveis pela estrutura.")
    linhas.append("   O IDAP mede nível de atenção e prontidão do setor saúde; não estima")
    linhas.append("   probabilidade de rompimento, que depende de modelo de engenharia e de")
    linhas.append("   instrumentação da própria barragem.")
    linhas.append("   Área/população por lâmina equivalente e agravos listados são hipóteses")
    linhas.append("   de vigilância na ausência de mancha oficial — não são diagnóstico.")
    if prazo is not None:
        linhas.append(
            f"   Confirmação de recebimento obrigatória em até {prazo} min, com identificação"
        )
        linhas.append("   do responsável; a ausência de confirmação escalona o alerta (regra R09).")
    if r.confiabilidade != "suficiente":
        linhas.append(
            f"   Cálculo com completude {r.completude:.0%}: o IDAP está subestimado e não deve"
        )
        linhas.append("   ser interpretado como ausência de risco.")
    linhas.append("=" * largura)

    return "\n".join(linhas)
