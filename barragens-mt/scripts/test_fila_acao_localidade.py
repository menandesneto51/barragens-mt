"""Aceite — fila de ação + IPAPD por localidade (ficha rápida)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from st_app.ficha_rapida import carregar_ficha_municipio, termos_ipapd_da_ficha  # noqa: E402
from st_app.localidade import (  # noqa: E402
    fila_acao_localidade,
    montar_dossie_localidade,
    pressao_assistencial_localidade,
    resumo_contatos_municipio,
)


def main() -> int:
    idap = pd.read_csv(
        ROOT / "dados/tratados/idap_estadual_mt.csv",
        sep=";",
        encoding="utf-8-sig",
        low_memory=False,
    )
    ok = 0
    total = 7

    ficha = carregar_ficha_municipio("Cuiabá")
    assert ficha is not None, "exemplo_cuiaba.json deve bater município"
    termos = termos_ipapd_da_ficha(ficha)
    assert "fracao_profissionais_presentes" in termos
    assert "atendimentos_observados" in termos
    ok += 1

    assert carregar_ficha_municipio("Alta Floresta") is None
    ok += 1

    d = montar_dossie_localidade("Cuiabá", idap)
    fila = fila_acao_localidade(d)
    assert len(fila) >= 2, "Cuiabá deve ter fila de ação"
    temas = {a["tema"] for a in fila}
    assert "Prontidão IDAP" in temas or "Impacto a jusante" in temas
    ok += 1

    assert any("Ficha rápida" in a["tema"] for a in fila)
    ok += 1

    ip = pressao_assistencial_localidade("Cuiabá", d)
    assert ip.get("ok"), "IPAPD deve calcular com ficha Cuiabá"
    assert ip.get("ficha", {}).get("encontrada")
    # A/P/C preenchidos via ficha
    termos_ip = ip.get("termos") or {}
    assert termos_ip.get("A") is not None and termos_ip.get("P") is not None
    assert termos_ip.get("C") is not None
    ok += 1

    d2 = montar_dossie_localidade("Chapada dos Guimarães", idap)
    ip2 = pressao_assistencial_localidade("Chapada dos Guimarães", d2)
    assert ip2.get("ficha", {}).get("encontrada"), "exemplo_manso.json"
    ok += 1

    cont = d.get("contatos") or resumo_contatos_municipio("Cuiabá")
    assert cont.get("disponivel"), "Cuiabá deve ter contatos no piloto"
    assert cont.get("n_total", 0) >= 4
    assert "Contatos" in " ".join(temas) or any("Contatos" in a["tema"] for a in fila) or (
        cont.get("n_criticos_com_fone", 0) >= 3
    )
    ok += 1

    print(
        f"OK {ok}/{total} — Cuiabá IPAPD={ip.get('ipapd')} "
        f"completude={ip.get('completude')} fila={len(fila)} "
        f"contatos={cont.get('n_criticos_com_fone')}/{cont.get('n_criticos')}"
    )
    return 0 if ok == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
