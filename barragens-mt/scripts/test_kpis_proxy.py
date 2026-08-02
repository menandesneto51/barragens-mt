"""Testes dos proxies IPAPD / demanda / PAE / ficha.

  python -m unittest scripts.test_kpis_proxy
  python scripts/test_kpis_proxy.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))

from st_app.demanda_cenario import estimar_demanda  # noqa: E402
from st_app.ficha_rapida import termos_ipapd_da_ficha  # noqa: E402
from st_app.ipapd import calcular_ipapd_proxy  # noqa: E402
from st_app.sitrep import montar_sitrep_cenario_md  # noqa: E402


class TestDemanda(unittest.TestCase):
    def test_vazia(self) -> None:
        d = estimar_demanda(0)
        self.assertFalse(d["ok"])

    def test_valores(self) -> None:
        d = estimar_demanda(10_000, leitos_disponiveis=100)
        self.assertTrue(d["ok"])
        self.assertEqual(d["demanda_internacao"], 200)
        self.assertEqual(d["demanda_atendimentos_72h"], 800)
        self.assertEqual(d["demanda_agua_L_dia"], 150_000)
        self.assertEqual(d["ambulancias_ref"], 1)
        self.assertEqual(d["razao_leitos_demanda"], 0.5)


class TestIpapd(unittest.TestCase):
    def test_sem_termos(self) -> None:
        r = calcular_ipapd_proxy()
        self.assertFalse(r["ok"])

    def test_com_ocupacao_e_isolamento(self) -> None:
        r = calcular_ipapd_proxy(
            taxa_ocupacao_pct=100,
            n_us_atingidas=4,
            n_us_isoladas=4,
            n_servicos_essenciais_mancha=10,
            n_servicos_essenciais_eixo=50,
        )
        self.assertTrue(r["ok"])
        self.assertEqual(r["termos"]["O"], 1.0)
        self.assertEqual(r["termos"]["E"], 0.5)
        self.assertIsNone(r["termos"]["A"])
        self.assertGreaterEqual(r["completude"], 0.4)

    def test_ficha_preenche_apc(self) -> None:
        ft = termos_ipapd_da_ficha(
            {
                "prof_disp": 5,
                "prof_escala": 10,
                "aut_energia": 24,
                "aut_agua": 48,
                "aut_o2": 12,
                "pop_atingida": 1000,
                "diarreia": 30,
                "febre": 20,
                "us_abertas": 2,
                "us_fechadas": 1,
                "us_danificadas": 1,
                "_arquivo": "t.json",
            }
        )
        r = calcular_ipapd_proxy(ficha_termos=ft, n_us_atingidas=1, n_us_isoladas=0)
        self.assertTrue(r["ok"])
        self.assertIsNotNone(r["termos"]["P"])
        self.assertIsNotNone(r["termos"]["C"])
        self.assertIsNotNone(r["termos"]["A"])
        self.assertIsNotNone(r["termos"]["S"])


class TestSitrepCenario(unittest.TestCase):
    def test_md(self) -> None:
        md = montar_sitrep_cenario_md(
            {"barragem": "Teste", "municipio": "Cuiabá", "pop_exposta": 100}
        )
        self.assertIn("SITREP de cenário", md)
        self.assertIn("Teste", md)


class TestPaeNorm(unittest.TestCase):
    def test_norm(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "pae47", RAIZ / "scripts" / "47_pae_cobertura_snisb.py"
        )
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(mod._norm_pae("Sim"), "sim")
        self.assertEqual(mod._norm_pae("Não"), "nao")
        self.assertEqual(mod._norm_pae(""), "desconhecido")


if __name__ == "__main__":
    unittest.main()
