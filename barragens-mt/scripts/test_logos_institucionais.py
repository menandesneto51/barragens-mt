"""Aceite — logos institucionais no cabeçalho."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from st_app.marca_institucional import (  # noqa: E402
    LOGOS,
    LOGOS_META,
    diretorio_logos,
    html_faixa_logos,
    html_faixa_logos_painel,
    resolver_arquivo_logo,
)


def main() -> int:
    pasta = diretorio_logos()
    for stem, _, _ in LOGOS_META:
        path = resolver_arquivo_logo(pasta, stem)
        assert path is not None and path.is_file(), f"faltando {stem}.*"
    # Retrocompat: stubs .svg listados em LOGOS
    for nome, _, _ in LOGOS:
        assert (pasta / nome).is_file() or resolver_arquivo_logo(pasta, Path(nome).stem), nome
    html = html_faixa_logos()
    assert "SES-MT" in html and "CIEVS-MT" in html
    assert "Vigidesastres" in html and "Defesa Civil" in html
    assert "data:image/" in html and "base64," in html
    html_p = html_faixa_logos_painel()
    assert "media/logos/ses_mt" in html_p
    assert "media/logos/cievs_mt" in html_p
    assert "media/logos/vigidesastres" in html_p
    assert "media/logos/defesa_civil_mt" in html_p
    print("OK logos institucionais:", len(LOGOS_META), "arquivos em", pasta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
