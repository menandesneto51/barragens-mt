"""Aceite — classificação CNES na mancha / apoio / isolada."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from st_app.us_atendimento import classificar_rede_cnes, dataframe_linhas  # noqa: E402


def main() -> int:
    cnes = [
        {"la": -15.6, "lo": -56.1, "no": "Hosp A", "mu": "Cuiabá", "tp": "HOSPITAL", "dist": 2.0, "h": 1},
        {"la": -15.7, "lo": -56.2, "no": "UBS B", "mu": "Cuiabá", "tp": "UBS", "dist": 8.0, "ubs": 1, "prio": 1},
        {"la": -15.55, "lo": -56.05, "no": "UPA C", "mu": "VG", "tp": "UPA", "dist": 12.0, "upa": 1},
    ]
    ating = [cnes[0]]
    isol = [cnes[1]]
    rede = classificar_rede_cnes(cnes_perto=cnes, us_atingidas=ating, us_isoladas=isol)
    assert rede["n_na_mancha"] == 1
    assert rede["n_isoladas"] == 1
    assert rede["n_apoio"] == 1
    assert rede["apoio"][0]["no"] == "UPA C"
    assert rede["apoio"][0]["situacao"] == "apoio"
    linhas = dataframe_linhas(rede["apoio"])
    assert linhas[0]["Dist. barragem (km)"] == 12.0
    assert "haversine" in (rede.get("nota") or "")
    print("OK us_atendimento — mancha/apoio/isolada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
