"""Aceite — ciclo alerta: emissão → prazo → escalonamento → confirmação + payload DC."""

from __future__ import annotations

import datetime as dt
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class TestCicloAlerta(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        # Redireciona persistência para pasta temporária
        import st_app.ciclo_alerta as ca

        self.ca = ca
        self._patchers = [
            mock.patch.object(ca, "PASTA", self.tmp),
            mock.patch.object(ca, "ALERTAS", self.tmp / "alertas_ciclo.csv"),
            mock.patch.object(ca, "CONFIRMACOES", self.tmp / "confirmacoes.csv"),
            mock.patch.object(ca, "ESCALONAMENTOS", self.tmp / "escalonamentos_log.csv"),
            mock.patch.object(ca, "PAYLOADS", self.tmp / "payloads"),
        ]
        for p in self._patchers:
            p.start()
            self.addCleanup(p.stop)

    def test_emissao_escalonamento_confirmacao(self) -> None:
        t0 = dt.datetime(2026, 8, 30, 12, 0, 0, tzinfo=dt.timezone(dt.timedelta(hours=-4)))
        row = self.ca.emitir_alerta(
            id_snisb="34145",
            nome="UHE Manso",
            municipio_sede="Chapada dos Guimarães",
            nivel="Amarelo",
            idap=20,
            municipios_afetados="Cuiabá|Várzea Grande",
            lat=-14.86,
            lon=-55.78,
            agora=t0,
        )
        self.assertEqual(row["estado"], "AGUARDANDO_CONFIRMACAO")
        self.assertEqual(row["prazo_min"], "120")
        payload_path = self.tmp / "payloads" / f"{row['id_alerta']}.json"
        self.assertTrue(payload_path.is_file())
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["tipo"], "alerta_prontidao_saude")
        self.assertIn("não constitui ordem de evacuação", payload["ressalva"].lower())

        # Ainda no prazo — sem escalonamento
        ev0 = self.ca.processar_escalonamentos(agora=t0 + dt.timedelta(minutes=30))
        self.assertEqual(ev0, [])

        # Prazo esgotado — 1º escalonamento
        ev1 = self.ca.processar_escalonamentos(agora=t0 + dt.timedelta(minutes=121))
        self.assertEqual(len(ev1), 1)
        self.assertEqual(ev1[0]["estado_novo"], "ESCALONADO")

        # 2º prazo — máximo
        al = self.ca.carregar_alertas()
        limite2 = dt.datetime.fromisoformat(str(al.iloc[0]["prazo_limite"]))
        ev2 = self.ca.processar_escalonamentos(agora=limite2 + dt.timedelta(minutes=1))
        self.assertEqual(len(ev2), 1)
        self.assertEqual(ev2[0]["estado_novo"], "ESCALONADO_MAXIMO")

        # Confirmação em outro alerta fresco
        t1 = t0 + dt.timedelta(hours=5)
        row2 = self.ca.emitir_alerta(
            id_snisb="34146",
            nome="UHE Manso ME",
            municipio_sede="Chapada dos Guimarães",
            nivel="Laranja",
            agora=t1,
        )
        conf = self.ca.registrar_confirmacao(
            id_alerta=row2["id_alerta"],
            responsavel="Plantão CIEVS",
            canal="telefone",
            agora=t1 + dt.timedelta(minutes=5),
        )
        self.assertEqual(conf["responsavel"], "Plantão CIEVS")
        al2 = self.ca.carregar_alertas()
        est = al2.loc[al2["id_alerta"] == row2["id_alerta"], "estado"].iloc[0]
        self.assertEqual(est, "CONFIRMADO")


if __name__ == "__main__":
    unittest.main()
