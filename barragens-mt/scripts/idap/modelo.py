"""Estado de uma barragem em um instante, na forma consumida pelo cálculo do IDAP.

Todo campo mensurável é opcional. `None` significa "não medido / não informado" e é
tratado como lacuna: rende zero ponto e reduz a completude do cálculo. Isso é diferente
de uma categoria declarada de desconhecimento (por exemplo `categoria_risco="Não
Classificado"`, que existe de fato no SNISB), a qual tem pontuação própria de precaução.
A distinção está documentada em `docs/03-idap.md`, seção de tratamento de dado ausente.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class PressaoHidroclimatica:
    """Dimensão A — o gatilho externo, medido na bacia contribuinte da barragem."""

    chuva_24h_mm: float | None = None
    chuva_72h_mm: float | None = None
    chuva_prevista_24_72h_mm: float | None = None
    percentil_climatologico: float | None = None
    saturacao_antecedente: float | None = None
    razao_nivel_cota_alerta: float | None = None
    dias_consecutivos_chuva_intensa: int | None = None


@dataclass(frozen=True)
class CondicaoEstrutura:
    """Dimensão B — o que os órgãos fiscalizadores e a instrumentação declaram."""

    categoria_risco: str | None = None
    nivel_emergencia: str | None = None
    situacao_estabilidade: str | None = None
    # Pior nota entre percolação, deformação/recalque, deterioração de taludes, drenagem
    # interna e confiabilidade do extravasor, na escala 0–10 do formulário do SIGBM.
    pior_nota_anomalia: float | None = None
    razao_volume_capacidade: float | None = None
    situacao_telemetria: str | None = None


@dataclass(frozen=True)
class ExposicaoSanitaria:
    """Dimensão C — quem e o que está na mancha de inundação e na Zona de Autossalvamento."""

    populacao_zas: int | None = None
    proporcao_vulneravel: float | None = None
    unidades_saude_sem_internacao: int | None = None
    unidades_saude_com_internacao: int | None = None
    hospital_referencia_ameacado: bool | None = None
    captacao_ameacada: str | None = None
    servicos_essenciais_ameacados: int | None = None
    tempo_chegada_onda_min: float | None = None
    isolamento_rodoviario: str | None = None
    contaminante_predominante: str | None = None
    # Proxies até existir mancha oficial (simulação / alerta).
    area_estimada_km2: float | None = None
    metodo_estimativa_populacao: str | None = None
    detalhe_estimativa_populacao: str | None = None


@dataclass(frozen=True)
class CapacidadeResposta:
    """Dimensão D — o que falta para responder. Pontua o déficit, não a capacidade."""

    situacao_plano_emergencia: str | None = None
    meses_desde_ultimo_simulado: float | None = None
    cobertura_alerta_zas: float | None = None
    razao_vagas_abrigo: float | None = None
    ambulancias_por_10mil: float | None = None
    razao_leitos_demanda: float | None = None
    possui_rota_alternativa: bool | None = None
    contatos_validados_90d: bool | None = None


@dataclass(frozen=True)
class SinaisOperacionais:
    """Fatos operacionais que alimentam as regras determinísticas de sobreposição.

    Não entram na soma do índice: agem depois dele, podendo elevar a faixa final.
    """

    rompimento_confirmado: bool = False
    perda_subita_de_nivel: bool = False
    evacuacao_determinada: bool = False
    sensores_criticos_em_falha: int = 0
    mancha_atinge_unidade_estrategica: bool = False
    mancha_atinge_captacao: bool = False
    municipios_zas_sem_confirmacao: tuple[str, ...] = ()
    # Análises SisClima/TITAN sobre alertas externos (ANA / INMET / Cemaden).
    alerta_cemaden_hidrologico: bool = False
    alerta_inmet_relevante: bool = False
    alerta_ana_acima_atencao: bool = False
    nivel_alerta_integrado_sis: str | None = None
    chuva_prevista_extrema: bool = False

@dataclass(frozen=True)
class EstadoBarragem:
    """Fotografia completa de uma barragem no instante `instante`."""

    id_barragem: str
    nome: str
    municipio: str
    instante: datetime
    orgao_fiscalizador: str | None = None
    empreendedor: str | None = None
    uso_principal: str | None = None
    municipios_zas: tuple[str, ...] = ()
    regiao_saude: str | None = None
    pressao: PressaoHidroclimatica = field(default_factory=PressaoHidroclimatica)
    estrutura: CondicaoEstrutura = field(default_factory=CondicaoEstrutura)
    exposicao: ExposicaoSanitaria = field(default_factory=ExposicaoSanitaria)
    capacidade: CapacidadeResposta = field(default_factory=CapacidadeResposta)
    sinais: SinaisOperacionais = field(default_factory=SinaisOperacionais)
