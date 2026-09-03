"""Aceite — ciclo alerta: emissão → supervisão → prazo → escalonamento → confirmação + payload DC."""

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
        import st_app.ciclo_alerta as ca

        self.ca = ca
        self.fila = self.tmp / "piloto"
        self.fila.mkdir()
        self._patchers = [
            mock.patch.object(ca, "PASTA", self.tmp),
            mock.patch.object(ca, "ALERTAS", self.tmp / "alertas_ciclo.csv"),
            mock.patch.object(ca, "CONFIRMACOES", self.tmp / "confirmacoes.csv"),
            mock.patch.object(ca, "ESCALONAMENTOS", self.tmp / "escalonamentos_log.csv"),
            mock.patch.object(ca, "PAYLOADS", self.tmp / "payloads"),
            mock.patch.object(ca, "FILA_TXT", self.fila),
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
        self.assertTrue(row.get("arquivo_txt"))
        self.assertTrue((self.fila / row["arquivo_txt"]).is_file())
        payload_path = self.tmp / "payloads" / f"{row['id_alerta']}.json"
        self.assertTrue(payload_path.is_file())
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["tipo"], "alerta_prontidao_saude")
        self.assertIn("não constitui ordem de evacuação", payload["ressalva"].lower())

        ev0 = self.ca.processar_escalonamentos(agora=t0 + dt.timedelta(minutes=30))
        self.assertEqual(ev0, [])

        ev1 = self.ca.processar_escalonamentos(agora=t0 + dt.timedelta(minutes=121))
        self.assertEqual(len(ev1), 1)
        self.assertEqual(ev1[0]["estado_novo"], "ESCALONADO")

        al = self.ca.carregar_alertas()
        limite2 = dt.datetime.fromisoformat(str(al.iloc[0]["prazo_limite"]))
        ev2 = self.ca.processar_escalonamentos(agora=limite2 + dt.timedelta(minutes=1))
        self.assertEqual(len(ev2), 1)
        self.assertEqual(ev2[0]["estado_novo"], "ESCALONADO_MAXIMO")

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

    def test_roxo_exige_supervisao(self) -> None:
        t0 = dt.datetime(2026, 8, 30, 12, 0, 0, tzinfo=dt.timezone(dt.timedelta(hours=-4)))
        row = self.ca.emitir_alerta(
            id_snisb="99901",
            nome="Barragem crítica",
            municipio_sede="Cuiabá",
            nivel="Roxo",
            idap=85,
            agora=t0,
        )
        self.assertEqual(row["estado"], "AGUARDANDO_SUPERVISAO")
        ok, motivo = self.ca.pode_despachar(row)
        self.assertFalse(ok)
        self.assertIn("supervisão", motivo.lower())

        with self.assertRaises(ValueError):
            self.ca.registrar_confirmacao(
                id_alerta=row["id_alerta"],
                responsavel="Alguém",
                agora=t0,
            )

        auth = self.ca.autorizar_supervisao(
            id_alerta=row["id_alerta"],
            supervisor="Coordenador CIEVS",
            agora=t0 + dt.timedelta(minutes=2),
        )
        self.assertEqual(auth["estado"], "AGUARDANDO_CONFIRMACAO")
        self.assertEqual(auth["supervisor"], "Coordenador CIEVS")
        ok2, _ = self.ca.pode_despachar(auth)
        self.assertTrue(ok2)

        row2 = self.ca.emitir_alerta(
            id_snisb="99902",
            nome="Outra crítica",
            municipio_sede="Cuiabá",
            nivel="Vermelho",
            agora=t0,
        )
        ev = self.ca.processar_escalonamentos(agora=t0 + dt.timedelta(hours=5))
        ids_esc = {e["id_alerta"] for e in ev}
        self.assertNotIn(row2["id_alerta"], ids_esc)


class TestDespachoIdAlerta(unittest.TestCase):
    def test_log_tem_id_alerta_e_bloqueio(self) -> None:
        import importlib.util

        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        fila = tmp / "piloto"
        fila.mkdir()
        log = tmp / "despacho_alertas_log.csv"
        conf = tmp / "conf"
        conf.mkdir()

        import st_app.ciclo_alerta as ca

        with mock.patch.object(ca, "PASTA", conf), mock.patch.object(
            ca, "ALERTAS", conf / "alertas_ciclo.csv"
        ), mock.patch.object(ca, "CONFIRMACOES", conf / "confirmacoes.csv"), mock.patch.object(
            ca, "ESCALONAMENTOS", conf / "escalonamentos_log.csv"
        ), mock.patch.object(ca, "PAYLOADS", conf / "payloads"), mock.patch.object(
            ca, "FILA_TXT", fila
        ):
            t0 = dt.datetime(2026, 8, 30, 12, 0, 0, tzinfo=dt.timezone.utc)
            row = ca.emitir_alerta(
                id_snisb="5603",
                nome="Teste",
                municipio_sede="Cuiabá",
                nivel="Roxo",
                agora=t0,
            )
            sys.path.insert(0, str(ROOT / "scripts"))
            spec = importlib.util.spec_from_file_location(
                "desp29t", ROOT / "scripts" / "29_despacho_alertas.py"
            )
            assert spec and spec.loader
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            with mock.patch.object(mod, "FILA", fila), mock.patch.object(mod, "LOG", log):
                n = mod.despachar(
                    dry_run=True,
                    apenas_arquivo=row["arquivo_txt"],
                    id_alerta=row["id_alerta"],
                )
                self.assertEqual(n, 1)
                texto = log.read_text(encoding="utf-8-sig")
                self.assertIn("id_alerta", texto.splitlines()[0])
                self.assertIn(row["id_alerta"], texto)
                self.assertIn("bloqueado", texto)


if __name__ == "__main__":
    unittest.main()
