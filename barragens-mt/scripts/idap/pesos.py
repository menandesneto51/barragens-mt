"""Pesos, tetos e faixas de pontuação do IDAP-Barragens, em estrutura versionada.

Toda a calibração do índice está neste módulo. `calculo.py` só sabe interpretar as
estruturas declaradas aqui, de modo que recalibrar o IDAP — mudar um limiar de chuva,
redistribuir pontos dentro de uma dimensão, acrescentar uma categoria — não exige tocar
na lógica de cálculo, apenas publicar uma nova `VERSAO_PESOS`.

ATENÇÃO METODOLÓGICA: os valores da versão 0.1.0 são propostas fundamentadas em
referências públicas (limiares de chuva do INMET/Cemaden, escala de anomalias do SIGBM,
critério de 30 minutos da Zona de Autossalvamento na Resolução ANM nº 95/2022), mas
nenhum deles é oficial. Precisam de validação por painel de especialistas antes de
sustentar decisão operacional. Cada limiar está marcado como proposta em
`docs/03-idap.md`.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

VERSAO_PESOS = "0.1.0-metodologica"
DATA_VERSAO_PESOS = "2026-07-29"
STATUS_VERSAO_PESOS = (
    "proposta metodológica — pendente de validação por painel de especialistas em "
    "engenharia de barragens, hidrologia, meteorologia, epidemiologia, saúde ambiental, "
    "assistência, Defesa Civil e geoprocessamento"
)

TETOS: dict[str, int] = {"A": 30, "B": 30, "C": 25, "D": 15}
TETO_IDAP = 100

NOMES_DIMENSAO: dict[str, str] = {
    "A": "Pressão hidroclimática",
    "B": "Condição da barragem",
    "C": "Impacto sanitário potencial",
    "D": "Déficit de capacidade de resposta",
}

# Fronteiras das faixas de alerta: (limite inferior inclusivo, limite superior inclusivo).
INTERVALOS_NIVEL: dict[str, tuple[int, int]] = {
    "VERDE": (0, 19),
    "AMARELO": (20, 39),
    "LARANJA": (40, 59),
    "VERMELHO": (60, 79),
    "ROXO": (80, 100),
}

# Limiares usados pelas regras determinísticas de sobreposição (docs/03-idap.md, §7).
LIMIAR_CHUVA_EXTREMA_24H_MM = 100.0
LIMIAR_CHUVA_EXTREMA_72H_MM = 200.0
# Alinhado à faixa "previsão extrema" de A3 (pesos IND_A3).
LIMIAR_CHUVA_PREVISTA_EXTREMA_MM = 140.0
LIMIAR_ANOMALIA_ATIVA = 4.0
LIMIAR_SENSORES_CRITICOS_EM_FALHA = 2
LIMIAR_COMPLETUDE_INSUFICIENTE = 0.40

# Chuva diária mínima que caracteriza "dia adverso" na contagem de persistência (A7).
LIMIAR_DIA_ADVERSO_MM = 20.0


def normalizar_chave(texto: str) -> str:
    """Reduz uma categoria a uma chave comparável: sem acento, minúscula, espaço simples.

    Necessário porque os órgãos escrevem a mesma categoria de formas diferentes —
    `Médio`, `Medio` e `MÉDIO` convivem no SNISB, e o SIGBM usa `Alta`/`Média`/`Baixa`
    onde o SNISB usa `Alto`/`Médio`/`Baixo`.
    """
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return " ".join(sem_acento.lower().split())


@dataclass(frozen=True)
class FaixaPontuacao:
    """Intervalo semiaberto [minimo, maximo) associado a uma pontuação.

    `minimo=None` representa −infinito e `maximo=None` representa +infinito. O intervalo
    é semiaberto para que as fronteiras nunca fiquem ambíguas na documentação nem no
    código.
    """

    minimo: float | None
    maximo: float | None
    pontos: int
    rotulo: str

    def contem(self, valor: float) -> bool:
        if self.minimo is not None and valor < self.minimo:
            return False
        if self.maximo is not None and valor >= self.maximo:
            return False
        return True

    def descrever(self) -> str:
        if self.minimo is None and self.maximo is None:
            return "qualquer valor"
        if self.minimo is None:
            return f"< {_num(self.maximo)}"
        if self.maximo is None:
            return f">= {_num(self.minimo)}"
        return f"{_num(self.minimo)} a < {_num(self.maximo)}"


def _num(valor: float | None) -> str:
    if valor is None:
        return "-"
    return f"{valor:g}".replace(".", ",")


@dataclass(frozen=True)
class IndicadorNumerico:
    codigo: str
    nome: str
    dimensao: str
    teto: int
    unidade: str
    janela: str
    fonte: str
    recalculo: str
    faixas: tuple[FaixaPontuacao, ...]

    def avaliar(self, valor: float) -> FaixaPontuacao:
        for faixa in self.faixas:
            if faixa.contem(valor):
                return faixa
        raise ValueError(f"{self.codigo}: valor {valor!r} fora de todas as faixas declaradas")


@dataclass(frozen=True)
class IndicadorCategorico:
    codigo: str
    nome: str
    dimensao: str
    teto: int
    janela: str
    fonte: str
    recalculo: str
    # Categoria legível -> pontos. Sinônimos das fontes entram como chaves adicionais.
    pontos_por_categoria: dict[str, int]

    def avaliar(self, categoria: str) -> tuple[int, str]:
        chave = normalizar_chave(categoria)
        for rotulo, pontos in self.pontos_por_categoria.items():
            if normalizar_chave(rotulo) == chave:
                return pontos, rotulo
        raise KeyError(f"{self.codigo}: categoria {categoria!r} não prevista")

    def conhece(self, categoria: str) -> bool:
        try:
            self.avaliar(categoria)
        except KeyError:
            return False
        return True


# ---------------------------------------------------------------------------
# Dimensão A — Pressão hidroclimática (30 pontos)
# ---------------------------------------------------------------------------

FONTE_CHUVA = "INMET (estações automáticas), Cemaden (pluviômetros) e NASA GPM-IMERG"
FONTE_PREVISAO = "INMET, Cemaden (risco geo-hidrológico) e GloFAS como contexto regional"
FONTE_FLUVIAL = "ANA — Rede Hidrometeorológica Nacional / telemetria; réguas da Defesa Civil"

IND_A1 = IndicadorNumerico(
    codigo="A1",
    nome="Chuva acumulada em 24 h na bacia",
    dimensao="A",
    teto=5,
    unidade="mm",
    janela="24 h móveis",
    fonte=FONTE_CHUVA,
    recalculo="a cada 30 min (satélite) ou 1 h (estações)",
    faixas=(
        FaixaPontuacao(None, 10, 0, "chuva fraca ou ausente"),
        FaixaPontuacao(10, 30, 1, "chuva moderada"),
        FaixaPontuacao(30, 50, 2, "chuva forte"),
        FaixaPontuacao(50, 80, 3, "chuva muito forte"),
        FaixaPontuacao(80, 120, 4, "chuva extrema"),
        FaixaPontuacao(120, None, 5, "chuva excepcional"),
    ),
)

IND_A2 = IndicadorNumerico(
    codigo="A2",
    nome="Chuva acumulada em 72 h na bacia",
    dimensao="A",
    teto=5,
    unidade="mm",
    janela="72 h móveis",
    fonte=FONTE_CHUVA,
    recalculo="a cada 30 min (satélite) ou 1 h (estações)",
    faixas=(
        FaixaPontuacao(None, 25, 0, "acumulado baixo"),
        FaixaPontuacao(25, 60, 1, "acumulado moderado"),
        FaixaPontuacao(60, 100, 2, "acumulado alto"),
        FaixaPontuacao(100, 150, 3, "acumulado muito alto"),
        FaixaPontuacao(150, 250, 4, "acumulado extremo"),
        FaixaPontuacao(250, None, 5, "acumulado excepcional"),
    ),
)

IND_A3 = IndicadorNumerico(
    codigo="A3",
    nome="Chuva prevista para a janela de 24 a 72 h",
    dimensao="A",
    teto=5,
    unidade="mm previstos",
    janela="próximas 24 a 72 h",
    fonte=FONTE_PREVISAO,
    recalculo="a cada rodada de modelo (2 a 4 vezes por dia)",
    faixas=(
        FaixaPontuacao(None, 20, 0, "previsão sem relevância hidrológica"),
        FaixaPontuacao(20, 50, 1, "previsão moderada"),
        FaixaPontuacao(50, 90, 2, "previsão alta"),
        FaixaPontuacao(90, 140, 3, "previsão muito alta"),
        FaixaPontuacao(140, 200, 4, "previsão extrema"),
        FaixaPontuacao(200, None, 5, "previsão excepcional"),
    ),
)

IND_A4 = IndicadorNumerico(
    codigo="A4",
    nome="Percentil climatológico do acumulado observado",
    dimensao="A",
    teto=4,
    unidade="de percentil",
    janela="mesmo período do ano na série climatológica local",
    fonte="INMET (normais climatológicas) e série histórica das estações da bacia",
    recalculo="junto com A1 e A2",
    faixas=(
        FaixaPontuacao(None, 50, 0, "abaixo da mediana climatológica"),
        FaixaPontuacao(50, 75, 1, "acima da mediana"),
        FaixaPontuacao(75, 90, 2, "acima do percentil 75"),
        FaixaPontuacao(90, 98, 3, "acima do percentil 90"),
        FaixaPontuacao(98, None, 4, "evento raro para a época (>= p98)"),
    ),
)

IND_A5 = IndicadorNumerico(
    codigo="A5",
    nome="Saturação antecedente do solo na bacia",
    dimensao="A",
    teto=4,
    unidade="de índice (0 a 1)",
    janela="30 dias antecedentes",
    fonte="índice de precipitação antecedente derivado de IMERG/Cemaden; umidade de solo quando disponível",
    recalculo="diário",
    faixas=(
        FaixaPontuacao(None, 0.40, 0, "solo seco"),
        FaixaPontuacao(0.40, 0.60, 1, "solo parcialmente úmido"),
        FaixaPontuacao(0.60, 0.75, 2, "solo úmido"),
        FaixaPontuacao(0.75, 0.90, 3, "solo muito úmido"),
        FaixaPontuacao(0.90, None, 4, "solo saturado"),
    ),
)

IND_A6 = IndicadorNumerico(
    codigo="A6",
    nome="Nível ou vazão do rio a jusante frente à cota de alerta",
    dimensao="A",
    teto=4,
    unidade="x a cota de alerta",
    janela="última leitura telemétrica",
    fonte=FONTE_FLUVIAL,
    recalculo="a cada leitura telemétrica (15 min a 1 h)",
    faixas=(
        FaixaPontuacao(None, 0.70, 0, "nível normal"),
        FaixaPontuacao(0.70, 0.90, 1, "nível em elevação"),
        FaixaPontuacao(0.90, 1.00, 2, "aproximando-se da cota de alerta"),
        FaixaPontuacao(1.00, 1.20, 3, "acima da cota de alerta"),
        FaixaPontuacao(1.20, None, 4, "acima da cota de inundação"),
    ),
)

IND_A7 = IndicadorNumerico(
    codigo="A7",
    nome="Persistência da condição adversa",
    dimensao="A",
    teto=3,
    unidade=f"dias consecutivos com chuva >= {LIMIAR_DIA_ADVERSO_MM:g} mm",
    janela="10 dias antecedentes",
    fonte=FONTE_CHUVA,
    recalculo="diário",
    faixas=(
        FaixaPontuacao(None, 2, 0, "sem persistência"),
        FaixaPontuacao(2, 3, 1, "dois dias consecutivos"),
        FaixaPontuacao(3, 5, 2, "três a quatro dias consecutivos"),
        FaixaPontuacao(5, None, 3, "cinco dias ou mais"),
    ),
)

# ---------------------------------------------------------------------------
# Dimensão B — Condição da barragem (30 pontos)
# ---------------------------------------------------------------------------

IND_B1 = IndicadorCategorico(
    codigo="B1",
    nome="Categoria de Risco (CRI) oficial",
    dimensao="B",
    teto=5,
    janela="último cadastro publicado",
    fonte="SNISB/ANA (campo CATEGORIA_RISCO) e SIGBM/ANM (Categoria de Risco - CRI)",
    recalculo="a cada carga do inventário (diária)",
    pontos_por_categoria={
        "Alto": 5,
        "Alta": 5,
        "Médio": 3,
        "Média": 3,
        "Baixo": 1,
        "Baixa": 1,
        # A ausência de classificação é tratada como precaução intermediária: não se pode
        # afirmar risco baixo em estrutura que o órgão nunca classificou.
        "Não Classificado": 2,
        "Não Classificada": 2,
        "Não se Aplica": 1,
    },
)

IND_B2 = IndicadorCategorico(
    codigo="B2",
    nome="Nível oficial de emergência declarado",
    dimensao="B",
    teto=10,
    janela="declaração vigente",
    fonte="SIGBM/ANM (Nível de Emergência), SNISB (NIVEL_PERIGO) e comunicação do empreendedor",
    recalculo="a cada carga (diária) e imediatamente ao receber comunicação oficial",
    pontos_por_categoria={
        "Sem emergência": 0,
        "Normal": 0,
        "Atenção": 3,
        "Nível de Atenção": 3,
        "Alerta": 5,
        "Nível de Alerta": 5,
        "Emergência Nível 1": 7,
        "Emergência Nivel 1": 7,
        # O SNISB registra "Emergência" sem informar o nível; a leitura conservadora é
        # tratar como nível 1 e abrir pendência de confirmação junto ao fiscalizador.
        "Emergência": 7,
        "Emergência Nível 2": 9,
        "Emergência Nivel 2": 9,
        "Emergência Nível 3": 10,
        "Emergência Nivel 3": 10,
    },
)

# Categorias de B2 que caracterizam emergência oficial de nível 2 ou 3 (regra R01).
CATEGORIAS_EMERGENCIA_NIVEL_2_OU_3 = (
    "Emergência Nível 2",
    "Emergência Nivel 2",
    "Emergência Nível 3",
    "Emergência Nivel 3",
)

IND_B3 = IndicadorCategorico(
    codigo="B3",
    nome="Ausência de estabilidade declarada",
    dimensao="B",
    teto=5,
    janela="campanha de declaração vigente",
    fonte="SIGBM/ANM — Status DCE RISR, Status DCE RPSB e Status da DCO Atual",
    recalculo="a cada carga (diária)",
    pontos_por_categoria={
        "Atestada e vigente": 0,
        "Atestado": 0,
        "Não se aplica": 0,
        "Não se aplica a esse tipo de barragem": 0,
        "Atestada mas vencida": 3,
        "Sem informação": 3,
        "-": 3,
        "Atestada com ressalva": 5,
        "Não atestada": 5,
        "Não Enviado": 5,
        "Não enviada": 5,
    },
)

IND_B4 = IndicadorNumerico(
    codigo="B4",
    nome="Anomalia estrutural ativa",
    dimensao="B",
    teto=5,
    unidade="de nota (escala 0 a 10 do SIGBM)",
    janela="última declaração de condição de estabilidade ou inspeção",
    fonte=(
        "SIGBM/ANM — Percolação, Deformações e recalque, Deterioração dos taludes, "
        "Drenagem Interna e Confiabilidade das estruturas extravasoras"
    ),
    recalculo="a cada carga (diária) e a cada inspeção registrada",
    faixas=(
        FaixaPontuacao(None, 1, 0, "sem anomalia registrada"),
        FaixaPontuacao(1, 4, 2, "anomalia com medidas corretivas em implantação"),
        FaixaPontuacao(4, 7, 4, "anomalia sem medidas corretivas implantadas"),
        FaixaPontuacao(7, None, 5, "anomalia com potencial de comprometer a segurança"),
    ),
)

IND_B5 = IndicadorNumerico(
    codigo="B5",
    nome="Elevação anormal do reservatório",
    dimensao="B",
    teto=3,
    unidade="da capacidade total",
    janela="última leitura",
    fonte="telemetria do empreendedor; SIGBM (Volume atual x Capacidade Total do Reservatório)",
    recalculo="a cada leitura telemétrica; diário quando só houver declaração",
    faixas=(
        FaixaPontuacao(None, 0.80, 0, "reservatório em faixa operacional"),
        FaixaPontuacao(0.80, 0.90, 1, "reservatório alto"),
        FaixaPontuacao(0.90, 0.98, 2, "reservatório muito alto"),
        FaixaPontuacao(0.98, None, 3, "reservatório no limite ou vertendo"),
    ),
)

IND_B6 = IndicadorCategorico(
    codigo="B6",
    nome="Falha ou ausência de telemetria e instrumentação",
    dimensao="B",
    teto=2,
    janela="últimas 72 h de transmissão",
    fonte="SIGBM/ANM (campo Instrumentação) e monitoramento do fluxo de telemetria",
    recalculo="horário",
    pontos_por_categoria={
        "Conforme projeto e transmitindo": 0,
        "Existe instrumentação de acordo com o projeto técnico": 0,
        "Falha parcial ou dados desatualizados": 1,
        "Existe instrumentação em desacordo com o projeto, porém em processo de instalação": 1,
        "Barragem não instrumentada de acordo com o projeto": 1,
        "Ausente ou sem transmissão": 2,
        "Existe instrumentação em desacordo com o projeto sem processo de instalação": 2,
        "Barragem não instrumentada em desacordo com o projeto": 2,
    },
)

# ---------------------------------------------------------------------------
# Dimensão C — Impacto sanitário potencial (25 pontos)
# ---------------------------------------------------------------------------

FONTE_POPULACAO = "IBGE (setores censitários e malha municipal) recortados pela mancha de inundação"

IND_C1 = IndicadorNumerico(
    codigo="C1",
    nome="População residente na Zona de Autossalvamento",
    dimensao="C",
    teto=5,
    unidade="habitantes",
    janela="estático, revisto a cada atualização de mancha ou de setor censitário",
    fonte=FONTE_POPULACAO,
    recalculo="a cada atualização de mancha (ou anual)",
    faixas=(
        FaixaPontuacao(None, 1, 0, "nenhum residente identificado"),
        FaixaPontuacao(1, 50, 1, "até 49 residentes"),
        FaixaPontuacao(50, 200, 2, "50 a 199 residentes"),
        FaixaPontuacao(200, 1_000, 3, "200 a 999 residentes"),
        FaixaPontuacao(1_000, 5_000, 4, "1.000 a 4.999 residentes"),
        FaixaPontuacao(5_000, None, 5, "5.000 residentes ou mais"),
    ),
)

IND_C2 = IndicadorNumerico(
    codigo="C2",
    nome="Proporção de população vulnerável na ZAS",
    dimensao="C",
    teto=3,
    unidade="de proporção",
    janela="estático, revisto anualmente",
    fonte="IBGE, e-SUS APS, CNES (pacientes dependentes de tecnologia) e CadÚnico",
    recalculo="anual, ou a cada atualização de mancha",
    faixas=(
        FaixaPontuacao(None, 0.10, 0, "abaixo de 10%"),
        FaixaPontuacao(0.10, 0.20, 1, "10% a 19%"),
        FaixaPontuacao(0.20, 0.35, 2, "20% a 34%"),
        FaixaPontuacao(0.35, None, 3, "35% ou mais"),
    ),
)

IND_C3 = IndicadorCategorico(
    codigo="C3",
    nome="Unidades de saúde ameaçadas",
    dimensao="C",
    teto=4,
    janela="estático, revisto a cada atualização de mancha",
    fonte="CNES cruzado com a mancha de inundação e com as vias de acesso",
    recalculo="a cada atualização de mancha ou de carga do CNES",
    pontos_por_categoria={
        "Nenhuma unidade ameaçada": 0,
        "Uma unidade sem internação": 1,
        "Duas a três unidades sem internação": 2,
        "Quatro ou mais unidades sem internação": 3,
        "Unidade com internação ou urgência": 3,
        "Hospital de referência regional ou única unidade do município": 4,
    },
)

IND_C4 = IndicadorCategorico(
    codigo="C4",
    nome="Captações de água para consumo humano ameaçadas",
    dimensao="C",
    teto=3,
    janela="estático, revisto a cada atualização de mancha",
    fonte="Sisagua/Vigiagua, cadastro da concessionária e SNISB (corpo hídrico barrado)",
    recalculo="a cada atualização de mancha ou de carga do Sisagua",
    pontos_por_categoria={
        "Nenhuma": 0,
        "Sistema isolado ou rural": 1,
        "Sistema urbano de pequeno ou médio porte": 2,
        "Captação principal de sede municipal ou única captação": 3,
    },
)

IND_C5 = IndicadorNumerico(
    codigo="C5",
    nome="Serviços essenciais não assistenciais ameaçados",
    dimensao="C",
    teto=2,
    unidade="ativo(s) crítico(s)",
    janela="estático, revisto a cada atualização de mancha",
    fonte="cadastro estadual de infraestrutura crítica, Defesa Civil, concessionárias, INEP",
    recalculo="a cada atualização de mancha",
    faixas=(
        FaixaPontuacao(None, 1, 0, "nenhum ativo crítico"),
        FaixaPontuacao(1, 3, 1, "um a dois ativos críticos"),
        FaixaPontuacao(3, None, 2, "três ou mais ativos críticos"),
    ),
)

IND_C6 = IndicadorNumerico(
    codigo="C6",
    nome="Tempo de chegada da onda à primeira ocupação humana",
    dimensao="C",
    teto=4,
    unidade="minutos",
    janela="estático, resultado do estudo de dam break",
    fonte="estudo de ruptura hipotética do empreendedor (PAE/PAEBM); estimativa própria quando ausente",
    recalculo="a cada revisão do estudo de ruptura",
    faixas=(
        FaixaPontuacao(None, 30, 4, "menos de 30 min — evacuação assistida inviável"),
        FaixaPontuacao(30, 60, 3, "30 a 59 min"),
        FaixaPontuacao(60, 120, 2, "1 h a 2 h"),
        FaixaPontuacao(120, 360, 1, "2 h a 6 h"),
        FaixaPontuacao(360, None, 0, "mais de 6 h"),
    ),
)

IND_C7 = IndicadorCategorico(
    codigo="C7",
    nome="Possibilidade de isolamento rodoviário",
    dimensao="C",
    teto=2,
    janela="estático, revisto a cada atualização de mancha",
    fonte="malha viária (DNIT, Sinfra-MT, OpenStreetMap) cruzada com a mancha",
    recalculo="a cada atualização de mancha",
    pontos_por_categoria={
        "Rotas alternativas pavimentadas": 0,
        "Rota única com desvio precário": 1,
        "Acesso único sem alternativa": 2,
    },
)

IND_C8 = IndicadorCategorico(
    codigo="C8",
    nome="Presença de contaminantes ou rejeitos no reservatório",
    dimensao="C",
    teto=2,
    janela="último cadastro publicado",
    fonte="SIGBM/ANM — minério principal, produtos químicos, cianeto, classe do resíduo (NBR 10004)",
    recalculo="a cada carga (diária)",
    pontos_por_categoria={
        "Água sem rejeito": 0,
        "Rejeito inerte ou sedimento": 1,
        "Rejeito não inerte ou perigoso": 2,
    },
)

# ---------------------------------------------------------------------------
# Dimensão D — Déficit de capacidade de resposta (15 pontos)
# ---------------------------------------------------------------------------

IND_D1 = IndicadorCategorico(
    codigo="D1",
    nome="Ausência de plano de emergência",
    dimensao="D",
    teto=3,
    janela="situação vigente",
    fonte="SNISB (POSSUI_PAE), SIGBM (PAEBM e entrega às prefeituras), Defesa Civil estadual",
    recalculo="a cada carga (diária)",
    pontos_por_categoria={
        "Vigente, testado e articulado": 0,
        "Vigente sem articulação municipal": 1,
        "Em elaboração ou vencido": 2,
        "Inexistente": 3,
    },
)

IND_D2 = IndicadorNumerico(
    codigo="D2",
    nome="Tempo desde o último simulado",
    dimensao="D",
    teto=2,
    unidade="meses",
    janela="situação vigente",
    fonte="registros da Defesa Civil estadual e municipal; relatórios do empreendedor",
    recalculo="mensal",
    faixas=(
        FaixaPontuacao(None, 12, 0, "simulado nos últimos 12 meses"),
        FaixaPontuacao(12, 36, 1, "simulado entre 12 e 36 meses"),
        FaixaPontuacao(36, None, 2, "sem simulado há mais de 36 meses ou nunca realizado"),
    ),
)

IND_D3 = IndicadorNumerico(
    codigo="D3",
    nome="Cobertura do sistema de alerta sonoro na ZAS",
    dimensao="D",
    teto=3,
    unidade="da população da ZAS",
    janela="situação vigente",
    fonte="cadastro de sirenes do empreendedor e da Defesa Civil; testes periódicos",
    recalculo="mensal",
    faixas=(
        FaixaPontuacao(None, 0.30, 3, "menos de 30% coberta"),
        FaixaPontuacao(0.30, 0.60, 2, "30% a 59% coberta"),
        FaixaPontuacao(0.60, 0.90, 1, "60% a 89% coberta"),
        FaixaPontuacao(0.90, None, 0, "90% ou mais coberta"),
    ),
)

IND_D4 = IndicadorNumerico(
    codigo="D4",
    nome="Insuficiência de vagas em abrigos",
    dimensao="D",
    teto=2,
    unidade="de razão vagas/demanda",
    janela="situação vigente",
    fonte="cadastro de abrigos da Defesa Civil e da Assistência Social",
    recalculo="mensal, diário durante evento",
    faixas=(
        FaixaPontuacao(None, 0.50, 2, "menos de metade da demanda"),
        FaixaPontuacao(0.50, 1.00, 1, "entre metade e a totalidade da demanda"),
        FaixaPontuacao(1.00, None, 0, "vagas suficientes"),
    ),
)

IND_D5 = IndicadorNumerico(
    codigo="D5",
    nome="Disponibilidade de ambulâncias na área de resposta",
    dimensao="D",
    teto=1,
    unidade="por 10 mil habitantes",
    janela="situação vigente",
    fonte="CNES (veículos), SAMU e regulação estadual",
    recalculo="diário",
    faixas=(
        FaixaPontuacao(None, 1.00, 1, "menos de 1 ambulância por 10 mil habitantes"),
        FaixaPontuacao(1.00, None, 0, "1 ou mais ambulâncias por 10 mil habitantes"),
    ),
)

IND_D6 = IndicadorNumerico(
    codigo="D6",
    nome="Capacidade hospitalar frente à demanda estimada",
    dimensao="D",
    teto=2,
    unidade="de razão leitos/demanda",
    janela="situação vigente",
    fonte="CNES (leitos cadastrados) e SISREG/central estadual (leitos efetivamente vagos)",
    recalculo="diário, horário durante evento",
    faixas=(
        FaixaPontuacao(None, 0.50, 2, "menos de metade da demanda estimada"),
        FaixaPontuacao(0.50, 1.00, 1, "entre metade e a totalidade da demanda"),
        FaixaPontuacao(1.00, None, 0, "capacidade suficiente"),
    ),
)

IND_D7 = IndicadorCategorico(
    codigo="D7",
    nome="Ausência de rota alternativa de evacuação",
    dimensao="D",
    teto=1,
    janela="situação vigente",
    fonte="plano de evacuação municipal; malha viária cruzada com a mancha",
    recalculo="a cada atualização de mancha ou de plano",
    pontos_por_categoria={
        "Existe rota alternativa mapeada e transitável": 0,
        "Não existe rota alternativa": 1,
    },
)

IND_D8 = IndicadorCategorico(
    codigo="D8",
    nome="Contatos institucionais desatualizados",
    dimensao="D",
    teto=1,
    janela="últimos 90 dias",
    fonte="cadastro de contatos institucionais da plataforma",
    recalculo="diário",
    pontos_por_categoria={
        "Contatos validados nos últimos 90 dias": 0,
        "Contatos sem validação há mais de 90 dias": 1,
    },
)


INDICADORES: tuple[IndicadorNumerico | IndicadorCategorico, ...] = (
    IND_A1, IND_A2, IND_A3, IND_A4, IND_A5, IND_A6, IND_A7,
    IND_B1, IND_B2, IND_B3, IND_B4, IND_B5, IND_B6,
    IND_C1, IND_C2, IND_C3, IND_C4, IND_C5, IND_C6, IND_C7, IND_C8,
    IND_D1, IND_D2, IND_D3, IND_D4, IND_D5, IND_D6, IND_D7, IND_D8,
)

INDICADORES_POR_CODIGO = {indicador.codigo: indicador for indicador in INDICADORES}


def teto_por_dimensao(dimensao: str) -> int:
    """Soma dos tetos dos indicadores declarados na dimensão.

    Serve de trava: se a soma divergir de TETOS, a calibração está inconsistente.
    """
    return sum(i.teto for i in INDICADORES if i.dimensao == dimensao)


def validar_calibracao() -> None:
    """Garante que a calibração publicada fecha nos tetos e nas faixas declaradas."""
    for dimensao, teto in TETOS.items():
        soma = teto_por_dimensao(dimensao)
        if soma != teto:
            raise ValueError(
                f"dimensão {dimensao}: soma dos tetos dos indicadores é {soma}, "
                f"esperado {teto} (versão {VERSAO_PESOS})"
            )
    if sum(TETOS.values()) != TETO_IDAP:
        raise ValueError(f"soma dos tetos das dimensões != {TETO_IDAP}")

    for indicador in INDICADORES:
        if isinstance(indicador, IndicadorNumerico):
            maximo = max(faixa.pontos for faixa in indicador.faixas)
            minimo = min(faixa.pontos for faixa in indicador.faixas)
        else:
            maximo = max(indicador.pontos_por_categoria.values())
            minimo = min(indicador.pontos_por_categoria.values())
        if maximo != indicador.teto:
            raise ValueError(
                f"{indicador.codigo}: maior pontuação declarada é {maximo}, "
                f"teto é {indicador.teto}"
            )
        if minimo < 0:
            raise ValueError(f"{indicador.codigo}: pontuação negativa declarada")

    limites = [INTERVALOS_NIVEL[nome] for nome in ("VERDE", "AMARELO", "LARANJA", "VERMELHO", "ROXO")]
    for (_, fim), (inicio_seguinte, _) in zip(limites, limites[1:]):
        if inicio_seguinte != fim + 1:
            raise ValueError("faixas de alerta não são contíguas")


validar_calibracao()
