"""Aceite do plano KPIs / dados abertos / relevo HAND.

Garante que as seis entregas do plano permanecem presentes e utilizáveis.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402


class TestPlanKpisRelevo(unittest.TestCase):
    def test_docs_fontes_mde_mapbiomas_setores(self) -> None:
        docs = (ROOT / "docs" / "02-fontes-de-dados.md").read_text(encoding="utf-8")
        self.assertIn("### 2.5.4", docs)
        self.assertIn("HAND", docs)
        self.assertIn("Copernicus", docs)
        self.assertIn("NASADEM", docs)
        self.assertIn("Topodata", docs)
        self.assertIn("### 2.5.5", docs)
        self.assertIn("MapBiomas", docs)
        self.assertIn("### 2.5.6", docs)
        self.assertIn("setores censitários", docs.lower())

    def test_etl_hand_piloto(self) -> None:
        meta = json.loads(
            (ROOT / "dados/tratados/hand_piloto_manso_cuiaba_meta.json").read_text(
                encoding="utf-8"
            )
        )
        grade = pd.read_csv(
            ROOT / "dados/tratados/hand_piloto_manso_cuiaba_grade.csv", sep=";"
        )
        geo = json.loads(
            (ROOT / "dados/tratados/hand_piloto_manso_cuiaba.geojson").read_text(
                encoding="utf-8"
            )
        )
        self.assertGreaterEqual(int(meta.get("n_celulas") or 0), 600)
        self.assertGreaterEqual(len(grade), 600)
        self.assertGreaterEqual(len(geo.get("features") or []), 1)
        self.assertTrue((ROOT / "scripts/35_mde_hand_piloto.py").is_file())

    def test_ui_sim_relevo(self) -> None:
        app = (ROOT / "streamlit_app.py").read_text(encoding="utf-8")
        self.assertTrue(
            "Só relevo (HAND)" in app or "Relevo (HAND)" in app,
            "geometria HAND ausente na Simulação",
        )
        self.assertTrue((ROOT / "st_app/relevo_hand.py").is_file())
        from st_app.relevo_hand import resumo_hand

        info = resumo_hand(5.0)
        self.assertTrue(info.get("ok"))

    def test_setores_ibge(self) -> None:
        df = pd.read_csv(
            ROOT / "dados/tratados/setores_censitarios_eixo_cuiaba.csv", sep=";"
        )
        self.assertGreaterEqual(len(df), 2000)
        from st_app.setores_ibge import cruzar_setores_mancha

        kpi = cruzar_setores_mancha(
            lat0=-15.6,
            lon0=-56.1,
            raio_km=12.0,
            mostrar_circular=True,
            mostrar_trajeto=False,
            usar_hand=False,
        )
        self.assertTrue(kpi.get("disponivel"))
        self.assertGreater(int(kpi.get("n_setores_expostos") or 0), 0)

    def test_sisagua_real(self) -> None:
        df = pd.read_csv(ROOT / "dados/tratados/sisagua_captacoes_eixo.csv", sep=";")
        self.assertGreaterEqual(len(df), 200)
        from st_app.sisagua_captacoes import cruzar_captacoes_mancha

        kpi = cruzar_captacoes_mancha(
            lat0=-15.6,
            lon0=-56.1,
            raio_km=20.0,
            mostrar_circular=True,
            mostrar_trajeto=False,
            usar_hand=False,
        )
        self.assertTrue(kpi.get("disponivel"))
        self.assertFalse(kpi.get("esqueleto"))
        self.assertGreater(int(kpi.get("n_na_mancha") or 0), 0)

    def test_telemetria_a(self) -> None:
        tele = pd.read_csv(ROOT / "dados/tratados/telemetria_hidro_a.csv", sep=";")
        hidro = pd.read_csv(ROOT / "dados/tratados/hidro_barragens_mt.csv", sep=";")
        self.assertGreaterEqual(len(tele), 100)
        self.assertIn("aproximacao_espacial", hidro.columns)
        n = int((hidro["aproximacao_espacial"] == "ponto_barragem_telemetria").sum())
        self.assertGreaterEqual(n, 100)
        self.assertTrue((ROOT / "scripts/39_telemetria_hidro_a.py").is_file())


if __name__ == "__main__":
    unittest.main()
