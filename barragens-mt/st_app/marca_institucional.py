"""Assinatura institucional — logos SES, CIEVS, Vigidesastres e Defesa Civil.

Arquivos em `st_app/assets/logos/` (espelho em `painel/media/logos/`).
Ordem de preferência por instituição: `.png` → `.jpg`/`.jpeg` → `.svg`.
Substitua pelos arquivos oficiais do GCOM/SECOM mantendo o stem do nome.
"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets" / "logos"
PAINEL_LOGOS = Path(__file__).resolve().parents[1] / "painel" / "media" / "logos"

# stem → (rótulo curto, título acessível)
LOGOS_META = (
    ("ses_mt", "SES-MT", "Secretaria de Estado de Saúde"),
    ("cievs_mt", "CIEVS-MT", "Centro de Informações Estratégicas em Vigilância em Saúde"),
    ("vigidesastres", "Vigidesastres", "Vigilância em Saúde ante Desastres"),
    ("defesa_civil_mt", "Defesa Civil", "Defesa Civil do Estado de Mato Grosso"),
)

# Retrocompatível com testes/código que esperam tuplas com extensão .svg
LOGOS = tuple((f"{stem}.svg", rotulo, titulo) for stem, rotulo, titulo in LOGOS_META)

_EXT_PREFERIDA = (".png", ".jpg", ".jpeg", ".svg", ".webp")


def diretorio_logos() -> Path:
    if ASSETS.is_dir() and any(ASSETS.iterdir()):
        return ASSETS
    return PAINEL_LOGOS


def resolver_arquivo_logo(pasta: Path, stem: str) -> Path | None:
    """Retorna o melhor arquivo disponível para o stem (PNG oficial > SVG)."""
    for ext in _EXT_PREFERIDA:
        path = pasta / f"{stem}{ext}"
        if path.is_file():
            return path
    return None


def _data_uri(path: Path) -> str:
    bruto = path.read_bytes()
    mime, _ = mimetypes.guess_type(path.name)
    if path.suffix.lower() == ".svg":
        mime = "image/svg+xml"
    if not mime:
        mime = "application/octet-stream"
    b64 = base64.b64encode(bruto).decode("ascii")
    return f"data:{mime};base64,{b64}"


def html_faixa_logos(*, altura_px: int = 44, classe: str = "faixa-logos") -> str:
    """HTML com as quatro marcas (data-URI — funciona no Streamlit Cloud)."""
    pasta = diretorio_logos()
    itens: list[str] = []
    for stem, rotulo, titulo in LOGOS_META:
        path = resolver_arquivo_logo(pasta, stem)
        if path is None:
            continue
        uri = _data_uri(path)
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
    pasta = PAINEL_LOGOS if PAINEL_LOGOS.is_dir() else diretorio_logos()
    itens: list[str] = []
    for stem, rotulo, titulo in LOGOS_META:
        path = resolver_arquivo_logo(pasta, stem)
        nome = path.name if path is not None else f"{stem}.svg"
        itens.append(
            f'<img class="logo-inst" src="{rel}/{nome}" alt="{rotulo}" '
            f'title="{titulo}" height="{altura_px}" />'
        )
    return (
        '<div class="faixa-logos" role="group" '
        'aria-label="Instituições: SES-MT, CIEVS-MT, Vigidesastres e Defesa Civil">'
        + "".join(itens)
        + "</div>"
    )
