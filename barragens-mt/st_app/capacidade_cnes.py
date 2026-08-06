"""Capacidade assistencial sob pressão na mancha (D6).

Camadas:
  1. Tipologia CNES (hospital / UPA / UBS) — sempre disponível na API aberta.
  2. Leitos + ocupação IndicaSUS/DW — quando `indicasus_leitos_mt.csv` existir.
  3. Leitos cadastrados CNES LT (SAU-01) — `cnes_leitos_cadastrados_mt.csv` (fallback).
"""

from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from st_app.relevo_hand import ponto_na_mancha_hand
from st_app.trajeto_hidraulico import ponto_no_corredor

_TRATADOS = Path(__file__).resolve().parents[1] / "dados" / "tratados"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(min(1.0, a)))


def _digitos_cnes(valor: Any) -> str:
    return "".join(c for c in str(valor or "") if c.isdigit())[:7]


@lru_cache(maxsize=1)
def _carregar_leitos_cadastrados() -> dict[str, float]:
    path = _TRATADOS / "cnes_leitos_cadastrados_mt.csv"
    if not path.is_file():
        return {}
    df = pd.read_csv(path, sep=";", dtype=str, low_memory=False)
    if df.empty or "codigo_cnes" not in df.columns:
        return {}
    out: dict[str, float] = {}
    for _, r in df.iterrows():
        key = _digitos_cnes(r.get("codigo_cnes"))
        if not key:
            continue
        try:
            out[key] = float(str(r.get("leitos_cadastrados") or "0").replace(",", "."))
        except ValueError:
            continue
    return out


def cruzar_capacidade_mancha(
    cnes: pd.DataFrame,
    *,
    lat0: float,
    lon0: float,
    raio_km: float,
    mostrar_circular: bool = True,
    trajeto: dict[str, Any] | None = None,
    mostrar_trajeto: bool = False,
    hand_limiar: float | None = None,
    usar_hand: bool = False,
    us_isoladas: list[dict[str, Any]] | None = None,
    pop_exposta: float | None = None,
) -> dict[str, Any]:
    """Conta capacidade estrutural e, se houver IndicaSUS, leitos/ocupação na mancha."""
    vazio = {
        "disponivel": False,
        "n_us_mancha": 0,
        "n_hospitalar_mancha": 0,
        "n_upa_mancha": 0,
        "n_ubs_mancha": 0,
        "n_prioritaria_mancha": 0,
        "n_hospitalar_isolada": 0,
        "n_upa_isolada": 0,
        "n_ubs_isolada": 0,
        "pressao_estrutural": 0,
        "rotulo_pressao": "indisponível",
        "leitos_ok": False,
        "leitos_operacionais_mancha": 0,
        "leitos_ocupados_mancha": 0,
        "leitos_disponiveis_mancha": 0,
        "leitos_cadastrados_mancha": 0,
        "cadastrados_ok": False,
        "taxa_ocupacao_mancha": None,
        "razao_leitos_demanda": None,
        "fonte": "CNES (tipologia; sem leitos na API aberta)",
    }
    if cnes is None or cnes.empty:
        return vazio

    from st_app.leitos_indicasus import agregar_por_cnes, status_indicasus

    leitos_cnes = agregar_por_cnes()
    leitos_map: dict[str, dict[str, Any]] = {}
    if not leitos_cnes.empty:
        for row in leitos_cnes.itertuples():
            key = _digitos_cnes(getattr(row, "codigo_cnes", ""))
            if key:
                leitos_map[key] = {
                    "op": float(getattr(row, "leitos_operacionais", 0) or 0),
                    "oc": float(getattr(row, "leitos_ocupados", 0) or 0),
                    "disp": float(getattr(row, "leitos_disponiveis", 0) or 0),
                }
    cad_map = _carregar_leitos_cadastrados()

    na_mancha_rows: list[dict[str, Any]] = []
    for row in cnes.itertuples():
        try:
            la, lo = float(row.latitude), float(row.longitude)
        except (TypeError, ValueError):
            continue
        ok = False
        if mostrar_circular and _haversine_km(lat0, lon0, la, lo) <= raio_km:
            ok = True
        if mostrar_trajeto and trajeto and trajeto.get("ok") and trajeto.get("polyline"):
            ok = ok or ponto_no_corredor(
                la,
                lo,
                trajeto["polyline"],
                float(trajeto.get("largura_km") or 2.0),
            )
        if usar_hand and hand_limiar is not None:
            ok = ok or ponto_na_mancha_hand(la, lo, float(hand_limiar))
        if not ok:
            continue
        cnes_cod = _digitos_cnes(getattr(row, "codigo_cnes", ""))
        lit = leitos_map.get(cnes_cod) or {}
        na_mancha_rows.append(
            {
                "codigo_cnes": cnes_cod,
                "nome": getattr(row, "nome", ""),
                "municipio": getattr(row, "municipio", ""),
                "tipo": getattr(row, "tipo", ""),
                "hospitalar": bool(getattr(row, "hospitalar", False)),
                "upa_ps": bool(getattr(row, "upa_ps", False)),
                "ubs_esf": bool(getattr(row, "ubs_esf", False)),
                "prioritario": bool(getattr(row, "prioritario", False)),
                "leitos_operacionais": lit.get("op"),
                "leitos_ocupados": lit.get("oc"),
                "leitos_disponiveis": lit.get("disp"),
                "leitos_cadastrados": cad_map.get(cnes_cod),
            }
        )

    n_h = sum(1 for r in na_mancha_rows if r["hospitalar"])
    n_upa = sum(1 for r in na_mancha_rows if r["upa_ps"])
    n_ubs = sum(1 for r in na_mancha_rows if r["ubs_esf"])
    n_prio = sum(1 for r in na_mancha_rows if r["prioritario"])

    iso = us_isoladas or []
    n_h_iso = sum(1 for u in iso if u.get("h"))
    n_upa_iso = sum(1 for u in iso if u.get("upa"))
    n_ubs_iso = sum(1 for u in iso if u.get("ubs"))

    pressao = (
        3 * (n_h + n_h_iso)
        + 2 * (n_upa + n_upa_iso)
        + 1 * (n_ubs + n_ubs_iso)
    )
    if pressao >= 12:
        rotulo = "alta — vários nós assistenciais sob risco/isolamento"
    elif pressao >= 5:
        rotulo = "moderada — capacidade local comprometida"
    elif pressao >= 1:
        rotulo = "baixa — poucos pontos críticos"
    else:
        rotulo = "mínima — sem hospital/UPA/UBS na mancha ou isolados"

    op_m = sum(float(r["leitos_operacionais"] or 0) for r in na_mancha_rows)
    oc_m = sum(float(r["leitos_ocupados"] or 0) for r in na_mancha_rows)
    disp_m = sum(float(r["leitos_disponiveis"] or 0) for r in na_mancha_rows)
    cad_m = sum(float(r["leitos_cadastrados"] or 0) for r in na_mancha_rows)
    leitos_ok = bool(leitos_map) and (op_m > 0 or disp_m > 0 or oc_m > 0)
    cadastrados_ok = bool(cad_map) and cad_m > 0
    taxa = round(100.0 * oc_m / op_m, 1) if op_m > 0 else None

    razao = None
    if leitos_ok and pop_exposta and pop_exposta > 0:
        demanda = 0.02 * float(pop_exposta)  # docs/03-idap.md §3.6.7
        if demanda > 0:
            razao = round(disp_m / demanda, 3)

    st = status_indicasus()
    partes = ["CNES tipologia"]
    if leitos_ok:
        partes.append(
            f"IndicaSUS ocupação ({st.get('fonte') or 'indicasus_leitos_mt.csv'})"
        )
    if cadastrados_ok:
        partes.append("CNES LT cadastrado (SAU-01)")
    if not leitos_ok and not cadastrados_ok:
        partes.append("sem leitos — rode etapas 43 e/ou 45")
    fonte = " + ".join(partes)

    return {
        "disponivel": True,
        "n_us_mancha": len(na_mancha_rows),
        "n_hospitalar_mancha": n_h,
        "n_upa_mancha": n_upa,
        "n_ubs_mancha": n_ubs,
        "n_prioritaria_mancha": n_prio,
        "n_hospitalar_isolada": n_h_iso,
        "n_upa_isolada": n_upa_iso,
        "n_ubs_isolada": n_ubs_iso,
        "pressao_estrutural": pressao,
        "rotulo_pressao": rotulo,
        "leitos_ok": leitos_ok,
        "leitos_operacionais_mancha": int(op_m),
        "leitos_ocupados_mancha": int(oc_m),
        "leitos_disponiveis_mancha": int(disp_m),
        "leitos_cadastrados_mancha": int(cad_m),
        "cadastrados_ok": cadastrados_ok,
        "taxa_ocupacao_mancha": taxa,
        "razao_leitos_demanda": razao,
        "itens_mancha": na_mancha_rows[:40],
        "fonte": fonte,
    }
