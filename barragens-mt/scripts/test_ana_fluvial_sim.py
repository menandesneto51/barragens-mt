"""Aceite do plano ANA rios na simulação (contexto fluvial + A6)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import pandas as pd  # noqa: E402


class TestAnaFluvialSim(unittest.TestCase):
    def test_auditoria_e_export(self) -> None:
        audit = ROOT / "dados/tratados/auditoria_ana_sisclima.json"
        est = ROOT / "dados/tratados/ana_estacoes_barragem.csv"
        self.assertTrue(audit.is_file(), "rode python executar.py 52")
        self.assertTrue(est.is_file(), "rode python executar.py 53")
        meta = json.loads(audit.read_text(encoding="utf-8"))
        self.assertGreaterEqual(int(meta.get("n_estacoes_mt") or 0), 1)
        df = pd.read_csv(est, sep=";")
        self.assertGreaterEqual(len(df), 1)
        # Se houver cota na fonte, o CSV deve expor
        if int(meta.get("n_estacoes_com_cota") or 0) >= 1:
            self.assertTrue(df["cota_cm"].notna().any() or (df["cota_cm"].astype(str) != "").any())

    def test_ui_helper(self) -> None:
        from st_app.ana_fluvial import carregar_estacoes_barragem, contexto_fluvial_barragem

        df = carregar_estacoes_barragem()
        if df.empty:
            self.skipTest("ana_estacoes_barragem.csv vazio — séries SisClima não habilitadas")
        bid = str(df.iloc[0]["id_snisb"])
        ctx = contexto_fluvial_barragem(bid)
        self.assertTrue(ctx.get("disponivel"))
        self.assertGreater(len(ctx.get("itens") or []), 0)

    def test_a6_cota_medida_quando_alerta(self) -> None:
        hidro = ROOT / "dados/tratados/hidro_barragens_mt.csv"
        est = ROOT / "dados/tratados/ana_estacoes_barragem.csv"
        if not hidro.is_file() or not est.is_file():
            self.skipTest("artefatos hidro/ANA ausentes")
        df_e = pd.read_csv(est, sep=";")
        medidos = df_e[df_e["a6_fonte"].astype(str) == "cota_medida"]
        if medidos.empty:
            self.skipTest("sem cota_alerta na fonte — A6 medido não aplicável")
        df_h = pd.read_csv(hidro, sep=";")
        self.assertIn("a6_fonte", df_h.columns)
        n = int((df_h["a6_fonte"].astype(str) == "cota_medida").sum())
        self.assertGreaterEqual(n, 1)
        # Razão preenchida nas barragens medidas
        sub = df_h[df_h["a6_fonte"].astype(str) == "cota_medida"]
        self.assertTrue(sub["razao_nivel_cota_alerta"].notna().any())

    def test_docs_fronteira(self) -> None:
        d02 = (ROOT / "docs/02-fontes-de-dados.md").read_text(encoding="utf-8")
        d03 = (ROOT / "docs/03-idap.md").read_text(encoding="utf-8")
        d12 = (ROOT / "docs/12-integracao-sisclima-titan.md").read_text(encoding="utf-8")
        self.assertIn("2.5.8b", d02)
        self.assertIn("não redefine a mancha", d02.lower().replace("**", ""))
        self.assertIn("cota_medida", d03)
        self.assertIn("ANA_FETCH_SERIES", d12)
        app = (ROOT / "streamlit_app.py").read_text(encoding="utf-8")
        self.assertIn("Contexto fluvial", app)
        self.assertIn("ana_fluvial", app)


if __name__ == "__main__":
    unittest.main()
