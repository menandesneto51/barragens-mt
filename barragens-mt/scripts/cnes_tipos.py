"""Tipos CNES prioritários para exposição sanitária a barragens.

Códigos `codigo_tipo_unidade` (DATASUS / CNES). Prioridade 0 = mais crítica.
"""

from __future__ import annotations

from typing import Any

# Prioridade crescente (0 = primeiro a listar / maior peso assistencial).
TIPOS_PRIORITARIOS: dict[str, tuple[str, int]] = {
    "05": ("hospital_geral", 0),
    "5": ("hospital_geral", 0),
    "62": ("hospital_especializado", 0),
    "73": ("upa", 1),
    "20": ("pronto_socorro_geral", 1),
    "21": ("pronto_socorro_especializado", 1),
    "15": ("unidade_mista", 2),
    "02": ("ubs", 2),
    "2": ("ubs", 2),
    "01": ("posto_saude", 3),
    "1": ("posto_saude", 3),
}

# Nomes / palavras que reforçam ESF mesmo quando o tipo é UBS/posto.
MARCADORES_ESF = ("esf", "estratégia saúde da família", "estrategia saude da familia", "psf")


def normalizar_tipo(codigo: Any) -> str:
    texto = str(codigo or "").strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    if texto.isdigit():
        return str(int(texto))  # "02" → "2" para bater no mapa; mantemos chaves duplicadas
    return texto


def classificar_estabelecimento(
    *,
    codigo_tipo: Any = None,
    nome: str | None = None,
    atendimento_hospitalar: str | None = None,
) -> dict[str, Any]:
    """Devolve flags de prioridade para buffer / C3."""
    tipo = normalizar_tipo(codigo_tipo)
    rotulo, prio = TIPOS_PRIORITARIOS.get(tipo, ("outro", 9))
    # Aliases com zero à esquerda
    if rotulo == "outro":
        rotulo, prio = TIPOS_PRIORITARIOS.get(tipo.zfill(2), ("outro", 9))

    nome_l = (nome or "").lower()
    esf = any(m in nome_l for m in MARCADORES_ESF) or rotulo in {"ubs", "posto_saude"}
    if any(m in nome_l for m in MARCADORES_ESF):
        rotulo = "esf"
        prio = min(prio, 2)

    hosp_flag = (atendimento_hospitalar or "").strip().lower() == "sim"
    if hosp_flag and rotulo == "outro":
        rotulo, prio = "hospital_geral", 0

    prioritario = prio <= 3 and rotulo != "outro"
    if hosp_flag:
        prioritario = True
        prio = min(prio, 0)

    return {
        "tipo": rotulo,
        "codigo_tipo": tipo,
        "prioridade": prio,
        "prioritario": prioritario,
        "hospitalar": hosp_flag or rotulo.startswith("hospital"),
        "ubs_esf": rotulo in {"ubs", "esf", "posto_saude"},
        "upa_ps": rotulo in {"upa", "pronto_socorro_geral", "pronto_socorro_especializado"},
    }
