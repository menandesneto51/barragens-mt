"""Regras determinísticas de sobreposição do IDAP-Barragens.

As regras agem DEPOIS do índice e nunca dependem dele. A razão é operacional: há fatos
que obrigam a resposta independentemente da pontuação — uma emergência de nível 3
declarada pelo empreendedor exige alerta vermelho mesmo que a bacia esteja seca e a
população a jusante seja pequena. Sem esta camada, um índice ponderado poderia diluir
justamente o sinal mais grave.

Cada regra pode elevar a faixa final (`nivel_minimo`) e/ou disparar uma ação automática.
Regras com `nivel_minimo=None` não mexem no nível: apenas acionam um fluxo paralelo,
como o alerta técnico de sensores ou o escalonamento por falta de confirmação.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

try:
    from . import pesos
    from .calculo import NivelAlerta, ResultadoIdap
    from .modelo import EstadoBarragem
except ImportError:  # execução direta de um módulo do pacote
    import pesos  # type: ignore[no-redef]
    from calculo import NivelAlerta, ResultadoIdap  # type: ignore[no-redef]
    from modelo import EstadoBarragem  # type: ignore[no-redef]


def _anomalia_ativa(estado: EstadoBarragem) -> bool:
    nota = estado.estrutura.pior_nota_anomalia
    return nota is not None and nota >= pesos.LIMIAR_ANOMALIA_ATIVA


def _chuva_extrema(estado: EstadoBarragem) -> bool:
    chuva_24h = estado.pressao.chuva_24h_mm
    chuva_72h = estado.pressao.chuva_72h_mm
    return (
        chuva_24h is not None and chuva_24h >= pesos.LIMIAR_CHUVA_EXTREMA_24H_MM
    ) or (
        chuva_72h is not None and chuva_72h >= pesos.LIMIAR_CHUVA_EXTREMA_72H_MM
    )


def _nivel_sis_alto(estado: EstadoBarragem) -> bool:
    nivel = (estado.sinais.nivel_alerta_integrado_sis or "").strip().lower()
    return nivel in {"laranja", "vermelha", "vermelho", "roxa", "roxo"}


def _alerta_externo_hidro(estado: EstadoBarragem) -> bool:
    return (
        estado.sinais.alerta_cemaden_hidrologico
        or estado.sinais.alerta_ana_acima_atencao
        or estado.sinais.chuva_prevista_extrema
    )


def _emergencia_nivel_2_ou_3(estado: EstadoBarragem) -> bool:
    declarado = estado.estrutura.nivel_emergencia
    if not declarado:
        return False
    chave = pesos.normalizar_chave(declarado)
    return any(
        chave == pesos.normalizar_chave(categoria)
        for categoria in pesos.CATEGORIAS_EMERGENCIA_NIVEL_2_OU_3
    )


@dataclass(frozen=True)
class Regra:
    codigo: str
    nome: str
    condicao: Callable[[EstadoBarragem, ResultadoIdap], bool]
    nivel_minimo: NivelAlerta | None
    acao: str
    fundamento: str


@dataclass(frozen=True)
class RegraDisparada:
    codigo: str
    nome: str
    nivel_minimo: NivelAlerta | None
    acao: str

    def descrever(self) -> str:
        elevacao = (
            f"eleva o alerta a no mínimo {self.nivel_minimo.rotulo}"
            if self.nivel_minimo is not None
            else "não altera a faixa"
        )
        return f"[{self.codigo}] {self.nome} — {elevacao}; ação: {self.acao}"


REGRAS: tuple[Regra, ...] = (
    Regra(
        codigo="R01",
        nome="Emergência oficial de nível 2 ou 3 declarada",
        condicao=lambda estado, _: _emergencia_nivel_2_ou_3(estado),
        nivel_minimo=NivelAlerta.VERMELHO,
        acao=(
            "notificar imediatamente Defesa Civil estadual e municipal, CIEVS, SAMU e "
            "gestores da ZAS; colocar a Sala de Situação em prontidão"
        ),
        fundamento="Resolução ANM nº 95/2022 — níveis 2 e 3 implicam evacuação da ZAS",
    ),
    Regra(
        codigo="R02",
        nome="Rompimento confirmado",
        condicao=lambda estado, _: estado.sinais.rompimento_confirmado,
        nivel_minimo=NivelAlerta.ROXO,
        acao=(
            "ativar imediatamente a resposta: COE em funcionamento, acionamento do "
            "VIGIPÓS-BARRAGENS, abertura de evento e SITREP inicial em até 1 h"
        ),
        fundamento="fato consumado — a resposta não pode depender de pontuação",
    ),
    Regra(
        codigo="R03",
        nome="Perda súbita de nível do reservatório associada a anomalia ativa",
        condicao=lambda estado, _: estado.sinais.perda_subita_de_nivel and _anomalia_ativa(estado),
        nivel_minimo=NivelAlerta.ROXO,
        acao=(
            "emitir alerta crítico para validação em campo em até 30 min pelo "
            "empreendedor e pelo órgão fiscalizador; suspeita de brecha em formação"
        ),
        fundamento="queda de nível sem vertimento é assinatura clássica de ruptura incipiente",
    ),
    Regra(
        codigo="R04",
        nome="Chuva extrema simultânea a anomalia estrutural ativa",
        condicao=lambda estado, _: _chuva_extrema(estado) and _anomalia_ativa(estado),
        nivel_minimo=NivelAlerta.VERMELHO,
        acao=(
            "alerta vermelho aos municípios da ZAS; exigir inspeção extraordinária e "
            "informe de condição da estrutura em até 6 h"
        ),
        fundamento=(
            f"chuva >= {pesos.LIMIAR_CHUVA_EXTREMA_24H_MM:g} mm/24 h ou "
            f">= {pesos.LIMIAR_CHUVA_EXTREMA_72H_MM:g} mm/72 h sobre estrutura com anomalia "
            f"de nota >= {pesos.LIMIAR_ANOMALIA_ATIVA:g}"
        ),
    ),
    Regra(
        codigo="R05",
        nome="Evacuação determinada pela autoridade competente",
        condicao=lambda estado, _: estado.sinais.evacuacao_determinada,
        nivel_minimo=NivelAlerta.ROXO,
        acao=(
            "ativar a Sala de Situação, acionar abrigos e transporte sanitário, iniciar "
            "registro de desalojados e desabrigados"
        ),
        fundamento="a decisão é da autoridade; a plataforma apenas se alinha a ela",
    ),
    Regra(
        codigo="R06",
        nome="Falha simultânea de sensores críticos ou cadastro insuficiente",
        condicao=lambda estado, resultado: (
            estado.sinais.sensores_criticos_em_falha >= pesos.LIMIAR_SENSORES_CRITICOS_EM_FALHA
            or resultado.dimensao("B").completude < pesos.LIMIAR_COMPLETUDE_INSUFICIENTE
        ),
        nivel_minimo=None,
        acao=(
            "emitir alerta técnico ao empreendedor e ao órgão fiscalizador; registrar que "
            "o IDAP está subestimado e não pode ser lido como normalidade"
        ),
        fundamento="ausência de dado não é ausência de risco",
    ),
    Regra(
        codigo="R07",
        nome="Mancha de inundação atingindo unidade de saúde estratégica",
        condicao=lambda estado, _: estado.sinais.mancha_atinge_unidade_estrategica,
        nivel_minimo=NivelAlerta.LARANJA,
        acao=(
            "alerta assistencial: acionar regulação estadual para remanejamento de leitos "
            "e pacientes, avaliar transferência de rede de frio e de pacientes críticos"
        ),
        fundamento="perda do nó assistencial multiplica o dano do evento",
    ),
    Regra(
        codigo="R08",
        nome="Mancha de inundação atingindo captação de água para consumo humano",
        condicao=lambda estado, _: estado.sinais.mancha_atinge_captacao,
        nivel_minimo=NivelAlerta.LARANJA,
        acao=(
            "alerta Vigiagua: suspender captação, iniciar coleta de amostras, acionar plano "
            "de abastecimento alternativo e comunicação de risco à população"
        ),
        fundamento="contaminação de captação transforma evento agudo em crise sanitária prolongada",
    ),
    Regra(
        codigo="R09",
        nome="Município da ZAS sem confirmação de recebimento no prazo",
        condicao=lambda estado, _: bool(estado.sinais.municipios_zas_sem_confirmacao),
        nivel_minimo=None,
        acao=(
            "escalonar o alerta: acionar o contato substituto, o gestor regional de saúde "
            "e a Defesa Civil estadual; registrar a falha de comunicação no evento"
        ),
        fundamento="alerta não confirmado é alerta não entregue",
    ),
    Regra(
        codigo="R10",
        nome="Alerta Cemaden/ANA hidrológico na área da barragem",
        condicao=lambda estado, _: (
            estado.sinais.alerta_cemaden_hidrologico or estado.sinais.alerta_ana_acima_atencao
        ),
        nivel_minimo=NivelAlerta.AMARELO,
        acao=(
            "cruzar com IDAP e hidro SisClima; confirmar condição da estrutura com o "
            "empreendedor; reforçar monitoramento de chuva/nível nas próximas 24–72 h"
        ),
        fundamento="análise SisClima dos alertas Cemaden/ANA — pressão externa já declarada",
    ),
    Regra(
        codigo="R11",
        nome="Alerta integrado SIS/TITAN hidrológico elevado",
        condicao=lambda estado, _: _nivel_sis_alto(estado),
        nivel_minimo=NivelAlerta.AMARELO,
        acao=(
            "considerar o estágio integrado hidrológico/solo/chuva na priorização; "
            "alertas só de calor do SIS não elevam barragem"
        ),
        fundamento="alerta_integrado_sis_titan filtrado para componentes hidro/solo/chuva",
    ),
    Regra(
        codigo="R12",
        nome="Previsão de chuva extrema (24–72 h) na bacia",
        condicao=lambda estado, _: estado.sinais.chuva_prevista_extrema,
        nivel_minimo=NivelAlerta.AMARELO,
        acao=(
            "antecipar prontidão: revisar PAE, contatos da ZAS e capacidade assistencial "
            "antes da janela prevista; acompanhar atualizações do modelo"
        ),
        fundamento="A3 — previsão ECMWF/Open-Meteo (contexto Copernicus/C3S) ≥ limiar extremo",
    ),
)

REGRAS_POR_CODIGO = {regra.codigo: regra for regra in REGRAS}


@dataclass(frozen=True)
class ResultadoFinal:
    resultado: ResultadoIdap
    nivel_indice: NivelAlerta
    nivel_final: NivelAlerta
    regras_disparadas: tuple[RegraDisparada, ...]

    @property
    def elevado_por_regra(self) -> bool:
        return self.nivel_final > self.nivel_indice

    @property
    def acoes_automaticas(self) -> tuple[str, ...]:
        return tuple(regra.acao for regra in self.regras_disparadas)

    @property
    def regras_que_elevaram(self) -> tuple[RegraDisparada, ...]:
        return tuple(
            regra
            for regra in self.regras_disparadas
            if regra.nivel_minimo is not None and regra.nivel_minimo > self.nivel_indice
        )


def aplicar_regras(estado: EstadoBarragem, resultado: ResultadoIdap) -> ResultadoFinal:
    """Aplica as regras de sobreposição e devolve o nível final com as ações automáticas."""
    nivel_indice = resultado.nivel
    nivel_final = nivel_indice
    disparadas: list[RegraDisparada] = []

    for regra in REGRAS:
        if not regra.condicao(estado, resultado):
            continue
        disparadas.append(
            RegraDisparada(
                codigo=regra.codigo,
                nome=regra.nome,
                nivel_minimo=regra.nivel_minimo,
                acao=regra.acao,
            )
        )
        if regra.nivel_minimo is not None and regra.nivel_minimo > nivel_final:
            nivel_final = regra.nivel_minimo

    return ResultadoFinal(
        resultado=resultado,
        nivel_indice=nivel_indice,
        nivel_final=nivel_final,
        regras_disparadas=tuple(disparadas),
    )
