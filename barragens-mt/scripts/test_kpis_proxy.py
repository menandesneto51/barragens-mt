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

from st_app.cenario_export import montar_csv_cenario  # noqa: E402
from st_app.demanda_cenario import estimar_demanda  # noqa: E402
from st_app.ficha_rapida import (  # noqa: E402
    termos_ipapd_da_ficha,
    termos_irs_da_ficha,
)
from st_app.ipapd import calcular_ipapd_proxy  # noqa: E402
from st_app.irs import calcular_irs_proxy  # noqa: E402
from st_app.pae_checklist import montar_checklist_pae  # noqa: E402
from st_app.sitrep import montar_sitrep_cenario_md  # noqa: E402
from st_app.vigipos import exemplo_leptospirose_564  # noqa: E402


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


class TestPaeChecklist(unittest.TestCase):
    def test_monta_itens(self) -> None:
        chk = montar_checklist_pae(
            {
                "id_snisb": "31990",
                "nome": "1A",
                "municipio_sede": "Alta Floresta",
                "possui_pae": "",
                "possui_plano_de_seguranca": "Não",
                "possui_revisao_periodica": "",
            }
        )
        self.assertTrue(chk["ok"])
        self.assertGreaterEqual(chk["n_itens"], 5)
        codigos = {i["codigo"] for i in chk["itens"]}
        self.assertIn("PAE-01", codigos)
        self.assertIn("PAE-04", codigos)


class TestCenarioCsv(unittest.TestCase):
    def test_csv(self) -> None:
        csv_txt = montar_csv_cenario(
            {"barragem": "X", "municipio": "Y", "pop_exposta": 10, "pae_lacunas": 2}
        )
        self.assertIn("Barragem", csv_txt)
        self.assertIn("X", csv_txt)
        self.assertIn(";", csv_txt)


class TestIrs(unittest.TestCase):
    def test_sem_dados(self) -> None:
        r = calcular_irs_proxy()
        self.assertFalse(r["ok"])

    def test_ficha_exemplo(self) -> None:
        ft = termos_irs_da_ficha(
            {
                "us_abertas": 3,
                "us_fechadas": 1,
                "us_danificadas": 0,
                "prof_disp": 20,
                "prof_escala": 40,
                "abrigados_atual": 100,
                "abrigados_pico": 400,
                "fracao_agua_ok": 0.8,
                "_arquivo": "t.json",
            }
        )
        r = calcular_irs_proxy(ficha_irs=ft, n_vias=0, n_pontes=0)
        self.assertTrue(r["ok"])
        self.assertIsNotNone(r["irs"])
        self.assertGreaterEqual(r["irs"], 0.0)
        self.assertLessEqual(r["irs"], 1.0)
        self.assertIsNotNone(r["termos"]["aps"])
        self.assertIsNotNone(r["termos"]["equipes"])
        self.assertIsNotNone(r["termos"]["abrigos"])


class TestVigipos(unittest.TestCase):
    def test_exemplo_564(self) -> None:
        s = exemplo_leptospirose_564()
        self.assertEqual(s.observado, 12)
        self.assertAlmostEqual(s.esperado, 1.8)
        self.assertEqual(s.limite_superior, 4)
        self.assertAlmostEqual(s.razao_oe, 6.7, places=1)
        self.assertEqual(s.excesso, 8)
        self.assertIn("crítico", s.classificacao)


if __name__ == "__main__":
    unittest.main()
