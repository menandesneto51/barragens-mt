"""Aceite — logos institucionais no cabeçalho."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from st_app.marca_institucional import (  # noqa: E402
    LOGOS,
    diretorio_logos,
    html_faixa_logos,
    html_faixa_logos_painel,
)


def main() -> int:
    pasta = diretorio_logos()
    for nome, _, _ in LOGOS:
        assert (pasta / nome).is_file(), f"faltando {nome}"
    html = html_faixa_logos()
    assert "SES-MT" in html and "CIEVS-MT" in html
    assert "Vigidesastres" in html and "Defesa Civil" in html
    assert "data:image/svg+xml;base64," in html
    html_p = html_faixa_logos_painel()
    assert "media/logos/ses_mt.svg" in html_p
    print("OK logos institucionais:", len(LOGOS), "arquivos em", pasta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
