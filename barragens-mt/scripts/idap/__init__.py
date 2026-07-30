"""IDAP-Barragens — implementação de referência do Índice Dinâmico de Alerta e Prontidão.

Este pacote torna executável a especificação de `docs/03-idap.md`. Ele não acessa rede
nem arquivos: recebe o estado de uma barragem em um instante, devolve a pontuação por
indicador, o índice 0–100, a faixa de alerta, as regras determinísticas disparadas e o
texto do alerta no formato de `docs/04-alertas.md`.

Uso mínimo:

    from scripts.idap import calcular_idap, aplicar_regras, montar_alerta

Os pesos e as faixas de pontuação vivem em `pesos.py` e são versionados por
`VERSAO_PESOS`. Alterar a calibração não exige mexer na lógica de cálculo.

Aviso metodológico: as faixas da versão 0.1.0 são propostas a validar por painel de
especialistas. Nenhum valor deste pacote substitui laudo de engenharia, decisão de
evacuação ou declaração de estabilidade de barragem.
"""

from __future__ import annotations

try:
    from .modelo import (
        CapacidadeResposta,
        CondicaoEstrutura,
        EstadoBarragem,
        ExposicaoSanitaria,
        PressaoHidroclimatica,
        SinaisOperacionais,
    )
    from .pesos import VERSAO_PESOS, TETOS, TETO_IDAP
    from .calculo import (
        NivelAlerta,
        PontuacaoDimensao,
        PontuacaoIndicador,
        ResultadoIdap,
        calcular_idap,
        classificar,
    )
    from .regras import RegraDisparada, ResultadoFinal, aplicar_regras
    from .relatorio import montar_alerta, montar_resumo
except ImportError:  # execução direta de um módulo do pacote (python scripts/idap/x.py)
    from modelo import (  # type: ignore[no-redef]
        CapacidadeResposta,
        CondicaoEstrutura,
        EstadoBarragem,
        ExposicaoSanitaria,
        PressaoHidroclimatica,
        SinaisOperacionais,
    )
    from pesos import VERSAO_PESOS, TETOS, TETO_IDAP  # type: ignore[no-redef]
    from calculo import (  # type: ignore[no-redef]
        NivelAlerta,
        PontuacaoDimensao,
        PontuacaoIndicador,
        ResultadoIdap,
        calcular_idap,
        classificar,
    )
    from regras import RegraDisparada, ResultadoFinal, aplicar_regras  # type: ignore[no-redef]
    from relatorio import montar_alerta, montar_resumo  # type: ignore[no-redef]

__all__ = [
    "VERSAO_PESOS",
    "TETOS",
    "TETO_IDAP",
    "PressaoHidroclimatica",
    "CondicaoEstrutura",
    "ExposicaoSanitaria",
    "CapacidadeResposta",
    "SinaisOperacionais",
    "EstadoBarragem",
    "NivelAlerta",
    "PontuacaoIndicador",
    "PontuacaoDimensao",
    "ResultadoIdap",
    "calcular_idap",
    "classificar",
    "RegraDisparada",
    "ResultadoFinal",
    "aplicar_regras",
    "montar_alerta",
    "montar_resumo",
]
