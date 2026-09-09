"""Ranking estadual de lacunas do checklist PAE/PAEBM.

Entrada:
  dados/tratados/inventario_barragens_mt.csv
  dados/tratados/pae_manchas_cobertura.csv
  dados/tratados/sigbm_barragens_mt.csv (opcional, via st_app.pae_checklist)

Saídas:
  dados/tratados/pae_checklist_lacunas.csv
  relatorios/pae_checklist_estadual.md

Uso:
  python scripts/48_pae_checklist_estadual.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))

import comum  # noqa: E402
from st_app.pae_checklist import montar_checklist_pae  # noqa: E402

INV = comum.DADOS_TRATADOS / "inventario_barragens_mt.csv"
SAIDA = comum.DADOS_TRATADOS / "pae_checklist_lacunas.csv"
REL = comum.RELATORIOS / "pae_checklist_estadual.md"


def main() -> int:
    if not INV.is_file():
        print(f"Inventário ausente: {INV}")
        return 1
    df = pd.read_csv(INV, sep=";", dtype=str).fillna("")
    rows = []
    for _, r in df.iterrows():
        chk = montar_checklist_pae(r)
        res = chk.get("resumo") or {}
        rows.append(
            {
                "id_snisb": chk.get("id_snisb"),
                "nome": chk.get("nome"),
                "municipio": chk.get("municipio"),
                "n_ok": res.get("ok", 0),
                "n_atencao": res.get("atencao", 0),
                "n_nao": res.get("nao", 0),
                "n_lacuna": res.get("lacuna", 0),
                "n_lacunas_criticas": chk.get("n_lacunas", 0),
                "pae_01": next(
                    (i["status"] for i in chk["itens"] if i["codigo"] == "PAE-01"),
                    "",
                ),
                "pae_04_zas": next(
                    (i["status"] for i in chk["itens"] if i["codigo"] == "PAE-04"),
                    "",
                ),
            }
        )
    out = pd.DataFrame(rows)
    out = out.sort_values(
        ["n_lacunas_criticas", "n_atencao", "nome"],
        ascending=[False, False, True],
    )
    comum.DADOS_TRATADOS.mkdir(parents=True, exist_ok=True)
    comum.RELATORIOS.mkdir(parents=True, exist_ok=True)
    out.to_csv(SAIDA, sep=";", index=False, encoding="utf-8-sig")

    n = len(out)
    top = out.head(25)
    md = [
        "# Checklist PAE — ranking estadual de lacunas",
        "",
        f"- Barragens avaliadas: **{n}**",
        f"- Com ≥1 lacuna/não: **{int((out['n_lacunas_criticas'] > 0).sum())}**",
        f"- PAE-01 = ok: **{int((out['pae_01'] == 'ok').sum())}**",
        f"- PAE-01 = lacuna: **{int((out['pae_01'] == 'lacuna').sum())}**",
        f"- Mancha ZAS (PAE-04) ok: **{int((out['pae_04_zas'] == 'ok').sum())}**",
        "",
        "## Top 25 por lacunas",
        "",
        "| SNISB | Nome | Município | Lacunas | Atenção | PAE-01 | ZAS |",
        "| --- | --- | --- | ---: | ---: | --- | --- |",
    ]
    for _, r in top.iterrows():
        md.append(
            f"| {r['id_snisb']} | {r['nome']} | {r['municipio']} | "
            f"{r['n_lacunas_criticas']} | {r['n_atencao']} | {r['pae_01']} | {r['pae_04_zas']} |"
        )
    md += [
        "",
        f"CSV: `{SAIDA.relative_to(RAIZ)}`",
        "",
        "_Checklist proxy — não substitui auditoria do PAE oficial._",
        "",
    ]
    REL.write_text("\n".join(md), encoding="utf-8")
    print(f"OK {SAIDA} ({n} linhas)")
    print(f"OK {REL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
