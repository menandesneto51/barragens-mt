"""Rede CNES na simulação: geolocalização, distância à barragem e papel no atendimento.

Distância = haversine (km) entre coordenada da US e da barragem.
Situação na mancha vem do cruzamento geométrico (círculo / corredor / HAND)
já calculado em `vias_isolamento` — este módulo só organiza a leitura operacional.
"""

from __future__ import annotations

from typing import Any


def _chave(la: float, lo: float) -> tuple[float, float]:
    return (round(float(la), 5), round(float(lo), 5))


def _prio_score(p: dict[str, Any]) -> tuple[int, float]:
    """Hospital > UPA > UBS/prioritário > demais; depois distância."""
    if p.get("h"):
        classe = 0
    elif p.get("upa"):
        classe = 1
    elif p.get("ubs") or p.get("prio"):
        classe = 2
    else:
        classe = 3
    try:
        dist = float(p.get("dist") if p.get("dist") is not None else p.get("dist_km") or 9e9)
    except (TypeError, ValueError):
        dist = 9e9
    return (classe, dist)


def classificar_rede_cnes(
    *,
    cnes_perto: list[dict[str, Any]],
    us_atingidas: list[dict[str, Any]] | None = None,
    us_isoladas: list[dict[str, Any]] | None = None,
    max_apoio: int = 50,
    max_contexto: int = 200,
) -> dict[str, Any]:
    """Separa US na mancha, isoladas e de apoio (fora da mancha, com rota potencial).

    `cnes_perto` deve trazer la/lo/no/mu/tp/dist (ou dist_km) e flags h/upa/ubs/prio.
    """
    ating = list(us_atingidas or [])
    isol = list(us_isoladas or [])
    keys_at = {_chave(p["la"], p["lo"]) for p in ating if "la" in p and "lo" in p}
    keys_iso = {_chave(p["la"], p["lo"]) for p in isol if "la" in p and "lo" in p}

    apoio: list[dict[str, Any]] = []
    contexto: list[dict[str, Any]] = []
    for p in cnes_perto or []:
        try:
            la, lo = float(p["la"]), float(p["lo"])
        except (KeyError, TypeError, ValueError):
            continue
        chave = _chave(la, lo)
        dist = p.get("dist")
        if dist is None:
            dist = p.get("dist_km")
        try:
            dist_f = round(float(dist), 2) if dist is not None else None
        except (TypeError, ValueError):
            dist_f = None
        item = {
            "la": la,
            "lo": lo,
            "no": p.get("no") or p.get("nome") or "US",
            "mu": p.get("mu") or p.get("municipio") or "",
            "tp": p.get("tp") or p.get("tipo") or "US",
            "dist": dist_f,
            "h": 1 if p.get("h") else 0,
            "upa": 1 if p.get("upa") else 0,
            "ubs": 1 if p.get("ubs") else 0,
            "prio": 1 if p.get("prio") else 0,
        }
        if chave in keys_at:
            item["situacao"] = "na_mancha"
            contexto.append(item)
            continue
        if chave in keys_iso:
            item["situacao"] = "isolada"
            contexto.append(item)
            continue
        item["situacao"] = "apoio"
        apoio.append(item)
        contexto.append(item)

    apoio_ord = sorted(apoio, key=_prio_score)[:max_apoio]
    # Prioriza hospital/UPA no contexto do mapa
    contexto_ord = sorted(contexto, key=_prio_score)[:max_contexto]

    n_hosp_apoio = sum(1 for p in apoio_ord if p.get("h"))
    n_upa_apoio = sum(1 for p in apoio_ord if p.get("upa"))

    return {
        "na_mancha": ating,
        "isoladas": isol,
        "apoio": apoio_ord,
        "contexto_mapa": contexto_ord,
        "n_perto": len(cnes_perto or []),
        "n_na_mancha": len(ating),
        "n_isoladas": len(isol),
        "n_apoio": len(apoio_ord),
        "n_hosp_apoio": n_hosp_apoio,
        "n_upa_apoio": n_upa_apoio,
        "nota": (
            "Distância = haversine (km) até a barragem. "
            "Na mancha = coordenada intersecta círculo/corredor/HAND. "
            "Apoio = fora da mancha (candidatas a atendimento/evacuação). "
            "Isolada = fora da mancha mas sem rota terrestre ao hub após corte de vias."
        ),
    }


def dataframe_linhas(itens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Linhas amigáveis para st.dataframe."""
    out = []
    for p in itens:
        out.append(
            {
                "Nome": p.get("no") or p.get("nome") or "—",
                "Tipo": p.get("tp") or p.get("tipo") or "—",
                "Município": p.get("mu") or p.get("municipio") or "—",
                "Dist. barragem (km)": p.get("dist") if p.get("dist") is not None else p.get("dist_km"),
                "Situação": {
                    "na_mancha": "Na mancha (afetada)",
                    "isolada": "Isolada (sem rota)",
                    "apoio": "Apoio (fora da mancha)",
                }.get(str(p.get("situacao") or ""), p.get("situacao") or "—"),
                "Hospital": "Sim" if p.get("h") else "",
                "UPA/PS": "Sim" if p.get("upa") else "",
                "UBS/ESF": "Sim" if p.get("ubs") else "",
            }
        )
    return out
