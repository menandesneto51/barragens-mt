"""Cálculo do IDAP-Barragens: funções puras, sem rede, sem arquivo e sem estado global.

O mesmo estado de entrada e a mesma versão de pesos produzem sempre o mesmo resultado,
inclusive as justificativas por indicador. É essa propriedade que permite auditar um
alerta emitido no passado: basta guardar o estado de entrada e a versão dos pesos.

Regra de leitura do resultado: `idap` é a soma bruta dos pontos efetivamente apurados.
Indicador sem dado rende zero, o que significa que um IDAP baixo com completude baixa
NÃO deve ser lido como situação tranquila. Para isso existem `completude`,
`confiabilidade` e `idap_projetado`, e a regra determinística R06 emite alerta técnico
quando a completude cai abaixo do mínimo aceitável.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime

try:
    from . import pesos
    from .modelo import (
        CapacidadeResposta,
        CondicaoEstrutura,
        EstadoBarragem,
        ExposicaoSanitaria,
        PressaoHidroclimatica,
    )
except ImportError:  # execução direta de um módulo do pacote
    import pesos  # type: ignore[no-redef]
    from modelo import (  # type: ignore[no-redef]
        CapacidadeResposta,
        CondicaoEstrutura,
        EstadoBarragem,
        ExposicaoSanitaria,
        PressaoHidroclimatica,
    )


class NivelAlerta(enum.IntEnum):
    """Faixas de alerta do IDAP. A ordem inteira permite comparar e elevar níveis."""

    VERDE = 0
    AMARELO = 1
    LARANJA = 2
    VERMELHO = 3
    ROXO = 4

    @property
    def rotulo(self) -> str:
        return {
            NivelAlerta.VERDE: "Verde",
            NivelAlerta.AMARELO: "Amarelo",
            NivelAlerta.LARANJA: "Laranja",
            NivelAlerta.VERMELHO: "Vermelho",
            NivelAlerta.ROXO: "Roxo",
        }[self]

    @property
    def significado(self) -> str:
        return {
            NivelAlerta.VERDE: "normalidade",
            NivelAlerta.AMARELO: "atenção",
            NivelAlerta.LARANJA: "mobilização",
            NivelAlerta.VERMELHO: "emergência potencial",
            NivelAlerta.ROXO: "resposta crítica",
        }[self]

    @property
    def intervalo(self) -> tuple[int, int]:
        return pesos.INTERVALOS_NIVEL[self.name]


def classificar(idap: int) -> NivelAlerta:
    """Converte a pontuação 0–100 na faixa de alerta correspondente."""
    if not 0 <= idap <= pesos.TETO_IDAP:
        raise ValueError(f"IDAP fora do intervalo 0–{pesos.TETO_IDAP}: {idap}")
    for nivel in NivelAlerta:
        inicio, fim = nivel.intervalo
        if inicio <= idap <= fim:
            return nivel
    raise AssertionError("faixas de alerta não cobrem o intervalo 0–100")


def formatar_numero(valor: float) -> str:
    """Formata número no padrão pt-BR, sem casas decimais desnecessárias."""
    if valor == int(valor) and abs(valor) < 1e15:
        texto = f"{int(valor):,}".replace(",", ".")
    else:
        texto = f"{valor:,.2f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return texto


@dataclass(frozen=True)
class PontuacaoIndicador:
    codigo: str
    nome: str
    dimensao: str
    pontos: int
    teto: int
    valor: str
    rotulo: str
    fonte: str
    ausente: bool
    observacao: str | None = None

    def justificativa(self) -> str:
        unidade = "ponto" if self.teto == 1 else "pontos"
        if self.ausente:
            return (
                f"[{self.codigo}] {self.nome}: dado indisponível — "
                f"0 de {self.teto} {unidade} apurados"
            )
        # Em indicador categórico o valor bruto já é o próprio rótulo da faixa; repetir os
        # dois deixaria a justificativa redundante no campo "Motivos" do alerta.
        descricao = self.valor if self.valor == self.rotulo else f"{self.valor} — {self.rotulo}"
        return (
            f"[{self.codigo}] {self.nome}: {descricao} "
            f"({self.pontos} de {self.teto} {unidade})"
        )


@dataclass(frozen=True)
class PontuacaoDimensao:
    codigo: str
    nome: str
    pontos: int
    teto: int
    indicadores: tuple[PontuacaoIndicador, ...]

    @property
    def teto_apurado(self) -> int:
        return sum(i.teto for i in self.indicadores if not i.ausente)

    @property
    def completude(self) -> float:
        return self.teto_apurado / self.teto if self.teto else 0.0

    @property
    def lacunas(self) -> tuple[str, ...]:
        return tuple(i.codigo for i in self.indicadores if i.ausente)


@dataclass(frozen=True)
class ResultadoIdap:
    id_barragem: str
    nome: str
    municipio: str
    instante: datetime
    versao_pesos: str
    dimensoes: tuple[PontuacaoDimensao, ...]

    @property
    def idap(self) -> int:
        return sum(d.pontos for d in self.dimensoes)

    @property
    def nivel(self) -> NivelAlerta:
        return classificar(self.idap)

    @property
    def teto_apurado(self) -> int:
        return sum(d.teto_apurado for d in self.dimensoes)

    @property
    def completude(self) -> float:
        return self.teto_apurado / pesos.TETO_IDAP

    @property
    def idap_projetado(self) -> float:
        """Índice reescalado pelos pontos efetivamente apuráveis.

        Serve apenas de contexto: indica onde o IDAP tenderia a cair se os indicadores
        ausentes se comportassem como a média dos apurados. Não classifica alerta, porque
        classificar por valor projetado equivaleria a inventar dado.
        """
        if self.teto_apurado == 0:
            return 0.0
        return round(100.0 * self.idap / self.teto_apurado, 1)

    @property
    def confiabilidade(self) -> str:
        if self.completude >= 0.80:
            return "suficiente"
        if self.completude >= pesos.LIMIAR_COMPLETUDE_INSUFICIENTE:
            return "parcial"
        return "insuficiente"

    @property
    def lacunas(self) -> tuple[str, ...]:
        return tuple(codigo for d in self.dimensoes for codigo in d.lacunas)

    @property
    def indicadores(self) -> tuple[PontuacaoIndicador, ...]:
        return tuple(i for d in self.dimensoes for i in d.indicadores)

    def dimensao(self, codigo: str) -> PontuacaoDimensao:
        for d in self.dimensoes:
            if d.codigo == codigo:
                return d
        raise KeyError(codigo)

    def justificativas(self, incluir_zerados: bool = False) -> tuple[str, ...]:
        """Motivos ordenados por peso, para alimentar o campo "Motivos" do alerta."""
        relevantes = [
            i for i in self.indicadores
            if not i.ausente and (incluir_zerados or i.pontos > 0)
        ]
        relevantes.sort(key=lambda i: (-i.pontos, i.codigo))
        return tuple(i.justificativa() for i in relevantes)


def _lacuna(indicador, motivo: str = "não informado") -> PontuacaoIndicador:
    return PontuacaoIndicador(
        codigo=indicador.codigo,
        nome=indicador.nome,
        dimensao=indicador.dimensao,
        pontos=0,
        teto=indicador.teto,
        valor="—",
        rotulo="dado indisponível",
        fonte=indicador.fonte,
        ausente=True,
        observacao=motivo,
    )


def avaliar_numerico(
    indicador: pesos.IndicadorNumerico, valor: float | int | None
) -> PontuacaoIndicador:
    if valor is None:
        return _lacuna(indicador)
    faixa = indicador.avaliar(float(valor))
    return PontuacaoIndicador(
        codigo=indicador.codigo,
        nome=indicador.nome,
        dimensao=indicador.dimensao,
        pontos=faixa.pontos,
        teto=indicador.teto,
        valor=f"{formatar_numero(float(valor))} {indicador.unidade}".strip(),
        rotulo=faixa.rotulo,
        fonte=indicador.fonte,
        ausente=False,
    )


def avaliar_categorico(
    indicador: pesos.IndicadorCategorico, categoria: str | None
) -> PontuacaoIndicador:
    if categoria is None or not str(categoria).strip():
        return _lacuna(indicador)
    try:
        pontos, rotulo = indicador.avaliar(str(categoria))
    except KeyError:
        # Categoria fora do domínio é lacuna, não zero silencioso: pontuar por
        # semelhança seria adivinhar, e o valor precisa aparecer como pendência.
        return _lacuna(indicador, motivo=f"categoria não prevista: {categoria!r}")
    return PontuacaoIndicador(
        codigo=indicador.codigo,
        nome=indicador.nome,
        dimensao=indicador.dimensao,
        pontos=pontos,
        teto=indicador.teto,
        valor=str(categoria),
        rotulo=rotulo,
        fonte=indicador.fonte,
        ausente=False,
    )


def _avaliar_booleano(
    indicador: pesos.IndicadorCategorico,
    valor: bool | None,
    rotulo_verdadeiro: str,
    rotulo_falso: str,
) -> PontuacaoIndicador:
    if valor is None:
        return _lacuna(indicador)
    return avaliar_categorico(indicador, rotulo_verdadeiro if valor else rotulo_falso)


def categoria_unidades_saude(exposicao: ExposicaoSanitaria) -> str | None:
    """Deriva a categoria de C3 a partir das contagens do CNES na mancha.

    Regra de precedência: a criticidade do estabelecimento pesa mais que a quantidade —
    perder o único hospital do município é pior que perder quatro postos de saúde.
    """
    if (
        exposicao.hospital_referencia_ameacado is None
        and exposicao.unidades_saude_com_internacao is None
        and exposicao.unidades_saude_sem_internacao is None
    ):
        return None
    if exposicao.hospital_referencia_ameacado:
        return "Hospital de referência regional ou única unidade do município"
    if (exposicao.unidades_saude_com_internacao or 0) >= 1:
        return "Unidade com internação ou urgência"
    sem_internacao = exposicao.unidades_saude_sem_internacao or 0
    if sem_internacao >= 4:
        return "Quatro ou mais unidades sem internação"
    if sem_internacao >= 2:
        return "Duas a três unidades sem internação"
    if sem_internacao == 1:
        return "Uma unidade sem internação"
    return "Nenhuma unidade ameaçada"


def pontuar_pressao(pressao: PressaoHidroclimatica) -> PontuacaoDimensao:
    """Dimensão A — 30 pontos."""
    indicadores = (
        avaliar_numerico(pesos.IND_A1, pressao.chuva_24h_mm),
        avaliar_numerico(pesos.IND_A2, pressao.chuva_72h_mm),
        avaliar_numerico(pesos.IND_A3, pressao.chuva_prevista_24_72h_mm),
        avaliar_numerico(pesos.IND_A4, pressao.percentil_climatologico),
        avaliar_numerico(pesos.IND_A5, pressao.saturacao_antecedente),
        avaliar_numerico(pesos.IND_A6, pressao.razao_nivel_cota_alerta),
        avaliar_numerico(pesos.IND_A7, pressao.dias_consecutivos_chuva_intensa),
    )
    return _montar_dimensao("A", indicadores)


def pontuar_estrutura(estrutura: CondicaoEstrutura) -> PontuacaoDimensao:
    """Dimensão B — 30 pontos."""
    indicadores = (
        avaliar_categorico(pesos.IND_B1, estrutura.categoria_risco),
        avaliar_categorico(pesos.IND_B2, estrutura.nivel_emergencia),
        avaliar_categorico(pesos.IND_B3, estrutura.situacao_estabilidade),
        avaliar_numerico(pesos.IND_B4, estrutura.pior_nota_anomalia),
        avaliar_numerico(pesos.IND_B5, estrutura.razao_volume_capacidade),
        avaliar_categorico(pesos.IND_B6, estrutura.situacao_telemetria),
    )
    return _montar_dimensao("B", indicadores)


def pontuar_exposicao(exposicao: ExposicaoSanitaria) -> PontuacaoDimensao:
    """Dimensão C — 25 pontos."""
    indicadores = (
        avaliar_numerico(pesos.IND_C1, exposicao.populacao_zas),
        avaliar_numerico(pesos.IND_C2, exposicao.proporcao_vulneravel),
        avaliar_categorico(pesos.IND_C3, categoria_unidades_saude(exposicao)),
        avaliar_categorico(pesos.IND_C4, exposicao.captacao_ameacada),
        avaliar_numerico(pesos.IND_C5, exposicao.servicos_essenciais_ameacados),
        avaliar_numerico(pesos.IND_C6, exposicao.tempo_chegada_onda_min),
        avaliar_categorico(pesos.IND_C7, exposicao.isolamento_rodoviario),
        avaliar_categorico(pesos.IND_C8, exposicao.contaminante_predominante),
    )
    return _montar_dimensao("C", indicadores)


def pontuar_capacidade(capacidade: CapacidadeResposta) -> PontuacaoDimensao:
    """Dimensão D — 15 pontos. Pontua o que falta, não o que existe."""
    indicadores = (
        avaliar_categorico(pesos.IND_D1, capacidade.situacao_plano_emergencia),
        avaliar_numerico(pesos.IND_D2, capacidade.meses_desde_ultimo_simulado),
        avaliar_numerico(pesos.IND_D3, capacidade.cobertura_alerta_zas),
        avaliar_numerico(pesos.IND_D4, capacidade.razao_vagas_abrigo),
        avaliar_numerico(pesos.IND_D5, capacidade.ambulancias_por_10mil),
        avaliar_numerico(pesos.IND_D6, capacidade.razao_leitos_demanda),
        _avaliar_booleano(
            pesos.IND_D7,
            capacidade.possui_rota_alternativa,
            "Existe rota alternativa mapeada e transitável",
            "Não existe rota alternativa",
        ),
        _avaliar_booleano(
            pesos.IND_D8,
            capacidade.contatos_validados_90d,
            "Contatos validados nos últimos 90 dias",
            "Contatos sem validação há mais de 90 dias",
        ),
    )
    return _montar_dimensao("D", indicadores)


def _montar_dimensao(
    codigo: str, indicadores: tuple[PontuacaoIndicador, ...]
) -> PontuacaoDimensao:
    teto = pesos.TETOS[codigo]
    pontos = sum(i.pontos for i in indicadores)
    if pontos > teto:
        raise AssertionError(
            f"dimensão {codigo} somou {pontos} pontos, acima do teto {teto} — "
            f"calibração inconsistente na versão {pesos.VERSAO_PESOS}"
        )
    return PontuacaoDimensao(
        codigo=codigo,
        nome=pesos.NOMES_DIMENSAO[codigo],
        pontos=pontos,
        teto=teto,
        indicadores=indicadores,
    )


def calcular_idap(estado: EstadoBarragem) -> ResultadoIdap:
    """Calcula o IDAP de uma barragem em um instante, com justificativa por indicador."""
    return ResultadoIdap(
        id_barragem=estado.id_barragem,
        nome=estado.nome,
        municipio=estado.municipio,
        instante=estado.instante,
        versao_pesos=pesos.VERSAO_PESOS,
        dimensoes=(
            pontuar_pressao(estado.pressao),
            pontuar_estrutura(estado.estrutura),
            pontuar_exposicao(estado.exposicao),
            pontuar_capacidade(estado.capacidade),
        ),
    )
