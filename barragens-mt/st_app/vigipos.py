"""VIGIPÓS — detecção de excesso (O/E + canal endêmico).

Métodos reproduzíveis (§5.6). A IA não gera o sinal — só explica.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence


@dataclass(frozen=True)
class SinalEpidemiologico:
    agravo: str
    municipio: str
    janela: str
    observado: float
    esperado: float
    limite_superior: float
    razao_oe: float
    excesso: float
    metodo: str
    classificacao: str
    parametros: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "agravo": self.agravo,
            "municipio": self.municipio,
            "janela": self.janela,
            "observado": self.observado,
            "esperado": round(self.esperado, 3),
            "limite_superior": round(self.limite_superior, 3),
            "razao_oe": round(self.razao_oe, 3),
            "excesso": round(self.excesso, 3),
            "metodo": self.metodo,
            "classificacao": self.classificacao,
            "parametros": self.parametros,
        }


def classificar_sinal(
    *,
    observado: float,
    esperado: float,
    limite_superior: float,
    razao_oe: float,
) -> str:
    """Classificação operacional — proposta a validar (§5.6.4)."""
    if observado <= limite_superior:
        if esperado > 0 and razao_oe >= 1.5:
            return "atenção"
        return "dentro do esperado"
    excesso = observado - limite_superior
    if razao_oe >= 5.0 or excesso >= 5.0:
        return "sinal epidemiológico crítico"
    if razao_oe >= 2.0 or excesso >= 2.0:
        return "alerta"
    return "atenção"


def canal_endemico_media_dp(
    serie_historica: Sequence[float],
    *,
    k_dp: float = 1.96,
) -> tuple[float, float, dict[str, Any]]:
    """Esperado = média; limite superior ≈ média + k·dp (canal endêmico simples)."""
    vals = [float(x) for x in serie_historica if x is not None]
    n = len(vals)
    if n == 0:
        return 0.0, 0.0, {"n": 0, "k_dp": k_dp}
    media = sum(vals) / n
    if n == 1:
        dp = 0.0
    else:
        var = sum((x - media) ** 2 for x in vals) / (n - 1)
        dp = var**0.5
    limite = media + k_dp * dp
    # evita limite < média
    limite = max(limite, media)
    return media, limite, {"n": n, "media": media, "dp": dp, "k_dp": k_dp}


def avaliar_oe(
    *,
    observado: float,
    esperado: float,
    limite_superior: float,
    agravo: str = "",
    municipio: str = "",
    janela: str = "",
    metodo: str = "canal_endemico_media_dp",
    parametros: dict[str, Any] | None = None,
) -> SinalEpidemiologico:
    obs = float(observado)
    esp = float(esperado)
    lim = float(limite_superior)
    razao = (obs / esp) if esp > 0 else (float("inf") if obs > 0 else 0.0)
    excesso = max(0.0, obs - lim)
    cls = classificar_sinal(
        observado=obs, esperado=esp, limite_superior=lim, razao_oe=razao
    )
    return SinalEpidemiologico(
        agravo=agravo,
        municipio=municipio,
        janela=janela,
        observado=obs,
        esperado=esp,
        limite_superior=lim,
        razao_oe=razao if razao != float("inf") else 999.0,
        excesso=excesso,
        metodo=metodo,
        classificacao=cls,
        parametros=parametros or {},
    )


def avaliar_oe_por_serie(
    *,
    observado: float,
    serie_historica: Sequence[float],
    agravo: str = "",
    municipio: str = "",
    janela: str = "",
    k_dp: float = 1.96,
) -> SinalEpidemiologico:
    esp, lim, params = canal_endemico_media_dp(serie_historica, k_dp=k_dp)
    return avaliar_oe(
        observado=observado,
        esperado=esp,
        limite_superior=lim,
        agravo=agravo,
        municipio=municipio,
        janela=janela,
        metodo="canal_endemico_media_dp",
        parametros=params,
    )


def exemplo_leptospirose_564() -> SinalEpidemiologico:
    """Reproduz o exemplo trabalhado da §5.6.4 (aceitação C3 do roadmap)."""
    return avaliar_oe(
        observado=12,
        esperado=1.8,
        limite_superior=4,
        agravo="leptospirose",
        municipio="exemplo",
        janela="7 dias",
        metodo="linha_base_historica_documentada",
        parametros={
            "fonte": "docs/05-vigipos-barragens.md §5.6.4",
            "excesso_sobre_limite": 8,
        },
    )


def fracao_sindromes_sob_controle(sinais: Iterable[SinalEpidemiologico]) -> float | None:
    """Dimensão IRS «controle dos agravos»: fração dentro do esperado / atenção baixa."""
    itens = list(sinais)
    if not itens:
        return None
    ok = sum(
        1
        for s in itens
        if s.classificacao in {"dentro do esperado", "atenção"}
    )
    return ok / len(itens)
