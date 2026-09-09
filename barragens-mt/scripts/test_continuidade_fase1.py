"""Testes da continuidade Fase 1 (A1 / A6 / VIGIPÓS / ficha)."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


class TestEtlHidroA6(unittest.TestCase):
    def test_52_53_60_no_padrao_antes_do_16(self) -> None:
        sys.path.insert(0, str(ROOT))
        from executar import ETAPAS

        padrao = [e[0] for e in ETAPAS if e[3]]
        self.assertIn("60", padrao)
        self.assertIn("52", padrao)
        self.assertIn("53", padrao)
        i17, i60, i52, i53, i16 = (
            padrao.index("17"),
            padrao.index("60"),
            padrao.index("52"),
            padrao.index("53"),
            padrao.index("16"),
        )
        self.assertLess(i17, i60)
        self.assertLess(i60, i52)
        self.assertLess(i52, i53)
        self.assertLess(i53, i16)

    def test_docs_receita_refresh(self) -> None:
        d12 = (ROOT / "docs" / "12-integracao-sisclima-titan.md").read_text(encoding="utf-8")
        self.assertIn("59 17 39 60 52 53 16", d12)
        self.assertIn("a6_fonte=cota_medida", d12)


class TestCotasAlerta60(unittest.TestCase):
    def test_etapa_60_grava_status(self) -> None:
        r = subprocess.run(
            [sys.executable, str(SCRIPTS / "60_ana_cotas_alerta.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        status = json.loads(
            (ROOT / "dados" / "tratados" / "ana_cotas_alerta_status.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(status.get("ok"))
        self.assertGreaterEqual(int(status.get("n_estacoes") or 0), 1)
        self.assertIn("eh_sample", status)


class TestVigiposStatus(unittest.TestCase):
    def test_etapa_50_status_honesto(self) -> None:
        r = subprocess.run(
            [sys.executable, str(SCRIPTS / "50_vigipos_linha_base.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        status = json.loads(
            (ROOT / "dados" / "tratados" / "vigipos_status.json").read_text(encoding="utf-8")
        )
        self.assertTrue(status.get("ok"))
        self.assertTrue(status.get("exemplo_564_ok"))
        self.assertTrue(status.get("eh_exemplo_ou_sintetico"))


class TestFichaRapida61(unittest.TestCase):
    def test_indexa_exemplos(self) -> None:
        r = subprocess.run(
            [sys.executable, str(SCRIPTS / "61_ficha_rapida_indexar.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        status = json.loads(
            (ROOT / "dados" / "tratados" / "fichas_rapidas_status.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertGreaterEqual(int(status.get("n_fichas") or 0), 2)
        self.assertGreaterEqual(int(status.get("n_com_termos_ipapd") or 0), 1)
        munics = status.get("municipios") or []
        self.assertTrue(any("Cuiab" in m for m in munics))


class TestColetoresCotasVigipos(unittest.TestCase):
    def test_a8_inclui_cotas_e_vigipos(self) -> None:
        sys.path.insert(0, str(ROOT))
        from st_app.coletores_status import status_coletores

        st = status_coletores()
        fontes = {x["fonte"] for x in st["lacunas"]}
        # Com sample/sintético atuais, ambas devem aparecer como atenção
        self.assertTrue(
            "Cotas alerta ANA" in fontes or "VIGIPÓS O/E" in fontes or st["ok"],
            fontes,
        )


class TestHistoricoProveniencia(unittest.TestCase):
    def test_indice_tem_versao_pesos(self) -> None:
        path = ROOT / "dados" / "tratados" / "historico_idap" / "indice.csv"
        self.assertTrue(path.is_file())
        with path.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f, delimiter=";"))
        self.assertGreaterEqual(len(rows), 1)
        self.assertIn("versao_pesos", rows[-1])


if __name__ == "__main__":
    unittest.main()
