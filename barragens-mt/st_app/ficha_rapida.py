"""Leitura de fichas rápidas exportadas (JSON) para alimentar IPAPD A/P/C."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TRATADOS = Path(__file__).resolve().parents[1] / "dados" / "tratados"
DIR_FICHAS = TRATADOS / "fichas_rapidas"


def listar_fichas() -> list[Path]:
    if not DIR_FICHAS.is_dir():
        return []
    return sorted(DIR_FICHAS.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)


def carregar_ficha(path: Path | None = None) -> dict[str, Any] | None:
    """Carrega a ficha mais recente ou um caminho explícito."""
    if path is None:
        fichas = listar_fichas()
        if not fichas:
            return None
        path = fichas[0]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    data["_arquivo"] = path.name
    return data


def termos_ipapd_da_ficha(ficha: dict[str, Any] | None) -> dict[str, Any]:
    """Extrai insumos A/P/C (e opcionalmente O) a partir da ficha §5.4."""
    if not ficha:
        return {}
    out: dict[str, Any] = {"fonte_ficha": ficha.get("_arquivo") or "ficha"}

    try:
        prof_d = float(ficha.get("prof_disp") or 0)
        prof_e = float(ficha.get("prof_escala") or 0)
        if prof_e > 0:
            out["fracao_profissionais_presentes"] = max(0.0, min(1.0, prof_d / prof_e))
    except (TypeError, ValueError):
        pass

    horas = []
    for k in ("aut_energia", "aut_agua", "aut_o2"):
        try:
            horas.append(float(ficha.get(k) or 0))
        except (TypeError, ValueError):
            continue
    if horas:
        out["autonomia_min_horas"] = min(horas)

    # A: sem linha de base oficial — usa razão atendimentos sindrômicos vs pop atingida como proxy fraco
    try:
        pop = float(ficha.get("pop_atingida") or 0)
        atend = sum(
            float(ficha.get(k) or 0)
            for k in (
                "afogamentos",
                "hipotermia",
                "intoxicacao",
                "diarreia",
                "febre",
                "respiratorio",
                "pele",
                "psiquico",
            )
        )
        if pop > 0 and atend >= 0:
            out["atendimentos_observados"] = atend
            # esperado provisório: 1% da pop em 7 dias (proposta a validar / placeholder)
            out["atendimentos_esperados"] = max(1.0, 0.01 * pop)
    except (TypeError, ValueError):
        pass

    try:
        us_ab = float(ficha.get("us_abertas") or 0)
        us_fe = float(ficha.get("us_fechadas") or 0)
        us_da = float(ficha.get("us_danificadas") or 0)
        total = us_ab + us_fe + us_da
        if total > 0:
            out["fracao_us_interrompidas"] = (us_fe + us_da) / total
    except (TypeError, ValueError):
        pass

    return out


def termos_irs_da_ficha(ficha: dict[str, Any] | None) -> dict[str, Any]:
    """Extrai dimensões do IRS (§5.5.7) a partir da ficha rápida."""
    if not ficha:
        return {}
    out: dict[str, Any] = {"fonte_ficha": ficha.get("_arquivo") or "ficha"}
    base = termos_ipapd_da_ficha(ficha)

    if "fracao_us_interrompidas" in base:
        out["fracao_aps_funcionando"] = max(
            0.0, 1.0 - float(base["fracao_us_interrompidas"])
        )
    if "fracao_profissionais_presentes" in base:
        out["fracao_profissionais_presentes"] = base["fracao_profissionais_presentes"]
    if "autonomia_min_horas" in base:
        # preferência: autonomia de água explícita
        try:
            if ficha.get("aut_agua") not in (None, ""):
                out["autonomia_agua_horas"] = float(ficha.get("aut_agua"))
        except (TypeError, ValueError):
            pass

    # Campos opcionais explícitos da ficha (quando o formulário evoluir)
    for src, dst in (
        ("fracao_agua_ok", "fracao_agua_ok"),
        ("fracao_vias_ok", "fracao_vias_ok"),
        ("fracao_leitos_operacionais", "fracao_leitos_operacionais"),
        ("fracao_rede_frio", "fracao_rede_frio"),
        ("fracao_cronicos_ok", "fracao_cronicos_ok"),
        ("fracao_saude_mental", "fracao_saude_mental"),
        ("fracao_ambiental_ok", "fracao_ambiental_ok"),
        ("controle_agravos", "controle_agravos"),
    ):
        if ficha.get(src) not in (None, ""):
            try:
                out[dst] = float(ficha.get(src))
            except (TypeError, ValueError):
                pass

    try:
        atual = float(ficha.get("abrigados_atual") or 0)
        pico = float(ficha.get("abrigados_pico") or 0)
        if pico > 0:
            out["fracao_saida_abrigos"] = max(0.0, min(1.0, 1.0 - (atual / pico)))
    except (TypeError, ValueError):
        pass

    return out
