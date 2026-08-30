"""Assinatura institucional — logos SES, CIEVS, Vigidesastres e Defesa Civil.

Arquivos SVG em `st_app/assets/logos/` (espelho em `painel/media/logos/`).
Podem ser substituídos pelos arquivos oficiais do GCOM/SECOM sem mudar o código.
"""

from __future__ import annotations

import base64
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets" / "logos"
PAINEL_LOGOS = Path(__file__).resolve().parents[1] / "painel" / "media" / "logos"

LOGOS = (
    ("ses_mt.svg", "SES-MT", "Secretaria de Estado de Saúde"),
    ("cievs_mt.svg", "CIEVS-MT", "Centro de Informações Estratégicas em Vigilância em Saúde"),
    ("vigidesastres.svg", "Vigidesastres", "Vigilância em Saúde ante Desastres"),
    ("defesa_civil_mt.svg", "Defesa Civil", "Defesa Civil do Estado de Mato Grosso"),
)


def diretorio_logos() -> Path:
    if ASSETS.is_dir() and any(ASSETS.glob("*.svg")):
        return ASSETS
    return PAINEL_LOGOS


def _svg_data_uri(path: Path) -> str:
    bruto = path.read_bytes()
    b64 = base64.b64encode(bruto).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def html_faixa_logos(*, altura_px: int = 44, classe: str = "faixa-logos") -> str:
    """HTML com as quatro marcas (data-URI — funciona no Streamlit Cloud)."""
    pasta = diretorio_logos()
    itens: list[str] = []
    for arquivo, rotulo, titulo in LOGOS:
        path = pasta / arquivo
        if not path.is_file():
            continue
        uri = _svg_data_uri(path)
        itens.append(
            f'<img class="logo-inst" src="{uri}" alt="{rotulo}" title="{titulo}" '
            f'height="{altura_px}" loading="lazy" />'
        )
    if not itens:
        return ""
    return (
        f'<div class="{classe}" role="group" '
        'aria-label="Instituições: SES-MT, CIEVS-MT, Vigidesastres e Defesa Civil">'
        + "".join(itens)
        + "</div>"
    )


def html_faixa_logos_painel(*, rel: str = "media/logos", altura_px: int = 40) -> str:
    """HTML para painéis offline (caminhos relativos a `painel/`)."""
    itens: list[str] = []
    for arquivo, rotulo, titulo in LOGOS:
        itens.append(
            f'<img class="logo-inst" src="{rel}/{arquivo}" alt="{rotulo}" '
            f'title="{titulo}" height="{altura_px}" />'
        )
    return (
        '<div class="faixa-logos" role="group" '
        'aria-label="Instituições: SES-MT, CIEVS-MT, Vigidesastres e Defesa Civil">'
        + "".join(itens)
        + "</div>"
    )
