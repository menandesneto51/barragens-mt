"""Testes do fallback de malha offline e payload Overpass-compatível."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from st_app.malha_offline import malha_offline_elements  # noqa: E402


class TestMalhaOffline(unittest.TestCase):
    def test_elements_nao_vazio(self) -> None:
        payload = malha_offline_elements()
        els = payload.get("elements") or []
        self.assertGreater(len(els), 10, payload.get("erro"))
        types = {e.get("type") for e in els}
        self.assertIn("node", types)
        self.assertIn("way", types)

    def test_filtro_raio_manso(self) -> None:
        payload = malha_offline_elements(lat=-14.94, lon=-55.79, raio_km=25.0)
        ways = [e for e in payload.get("elements") or [] if e.get("type") == "way"]
        self.assertGreater(len(ways), 0)
        meta = payload.get("_meta") or {}
        self.assertIn("offline", str(meta.get("fonte") or "").lower())


if __name__ == "__main__":
    unittest.main()
