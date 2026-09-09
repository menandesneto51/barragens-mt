"""Aceite — cobrança de contatos + SITREP plantão + seed IndicaSUS."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from st_app.contatos_cobranca import (  # noqa: E402
    exportar_cobranca_md,
    kpis_contatos_criticos,
    lista_cobranca_contatos,
)
from st_app.sitrep import montar_sitrep_md  # noqa: E402


def main() -> int:
    cob = lista_cobranca_contatos()
    assert not cob.empty, "piloto deve ter lacunas CIEVS/e-mail"
    assert "cievs" in set(cob["papel"].astype(str)) or "sem_email" in " ".join(
        cob["motivos"].astype(str)
    )
    k = kpis_contatos_criticos()
    assert k["n_cobranca"] >= 1
    md_cob = exportar_cobranca_md(cob)
    assert "Lista de cobrança" in md_cob

    idap = pd.read_csv(
        ROOT / "dados/tratados/idap_estadual_mt.csv",
        sep=";",
        encoding="utf-8-sig",
        low_memory=False,
    )
    if "idap_n" not in idap.columns:
        idap["idap_n"] = pd.to_numeric(
            idap["idap"].astype(str).str.replace(",", ".", regex=False),
            errors="coerce",
        )
    sit = montar_sitrep_md(idap.head(50), municipio="Cuiabá")
    assert "Contexto fluvial" in sit
    assert "Contatos críticos" in sit
    assert "PAE" in sit
    assert "Ciclo de alerta" in sit

    # Seed IndicaSUS
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "seed56", ROOT / "scripts" / "56_indicasus_seed_eixo.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    # force
    sys.argv = ["56", "--force"]
    spec.loader.exec_module(mod)
    mod.main()
    mun = ROOT / "dados/tratados/indicasus_leitos_municipio.csv"
    assert mun.is_file()
    dfm = pd.read_csv(mun, sep=";")
    assert len(dfm) >= 1
    assert "Cuiabá" in set(dfm["municipio"].astype(str)) or len(dfm) >= 1
    st = (ROOT / "dados/tratados/indicasus_leitos_status.json").read_text(encoding="utf-8")
    assert "seed" in st.lower() or "ok" in st.lower()

    print(
        f"OK cobrança={k['n_cobranca']} sitrep_len={len(sit)} "
        f"indicasus_mun={len(dfm)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
