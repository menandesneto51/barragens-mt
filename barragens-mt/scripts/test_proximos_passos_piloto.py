"""Aceite — A8 coletores, PAE gancho 58, contatos CIEVS."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class TestColetoresStatus(unittest.TestCase):
    def test_status_nao_zera_e_lista_lacunas(self) -> None:
        from st_app.coletores_status import faixa_html, status_coletores

        st = status_coletores()
        self.assertIn("lacunas", st)
        self.assertIn("n_lacunas", st)
        html = faixa_html(st)
        self.assertIn("Completude" if st["lacunas"] else "Coletores", html)
        # IDAP não é mencionado como zerado
        self.assertNotIn("IDAP=0", html)


class TestPaeManchas(unittest.TestCase):
    def test_ponto_em_poligono_e_carga_vazia(self) -> None:
        from st_app.pae_manchas import carregar_mancha, ponto_em_poligono, tem_mancha_pae

        ring = [[-15.0, -56.0], [-15.0, -55.0], [-14.0, -55.0], [-14.0, -56.0], [-15.0, -56.0]]
        self.assertTrue(ponto_em_poligono(-14.5, -55.5, ring))
        self.assertFalse(ponto_em_poligono(-20.0, -40.0, ring))
        self.assertFalse(tem_mancha_pae("99999999"))
        m = carregar_mancha("99999999")
        self.assertFalse(m["ok"])


class TestContatosCievS(unittest.TestCase):
    def test_filtro_so_cievs(self) -> None:
        import pandas as pd

        from st_app.contatos_cobranca import lista_cobranca_contatos, municipios_criticos_completos

        ct = pd.DataFrame(
            [
                {
                    "municipio": "Cuiabá",
                    "papel": "cievs",
                    "telefone": "",
                    "celular": "",
                    "email": "",
                    "data_validacao": "",
                    "nome": "A",
                    "regiao_saude": "Baixada",
                },
                {
                    "municipio": "Cuiabá",
                    "papel": "vigilancia_saude",
                    "telefone": "65999999999",
                    "celular": "",
                    "email": "",
                    "data_validacao": "",
                    "nome": "B",
                    "regiao_saude": "Baixada",
                },
            ]
        )
        cob = lista_cobranca_contatos(ct, so_cievs=True)
        self.assertEqual(len(cob), 1)
        self.assertEqual(cob.iloc[0]["papel"], "cievs")
        m = municipios_criticos_completos(ct, so_cievs=True)
        self.assertEqual(m["n_completos"], 0)


class TestEtapa58Vazia(unittest.TestCase):
    def test_58_sem_arquivos(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "e58", ROOT / "scripts" / "58_pae_manchas_carregar.py"
        )
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        rc = mod.main()
        self.assertEqual(rc, 0)
        st = json.loads((ROOT / "dados/tratados/pae_manchas_status.json").read_text(encoding="utf-8"))
        self.assertTrue(st.get("ok"))
        self.assertEqual(st.get("n_manchas_indexadas"), 0)


if __name__ == "__main__":
    unittest.main()
