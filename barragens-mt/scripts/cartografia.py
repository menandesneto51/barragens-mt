"""Primitivos de prancha cartografica compartilhados pelos scripts de mapa.

Reune os elementos que o padrao de prancha do projeto exige em toda figura — moldura,
grade em graus, rosa dos ventos, escala grafica, encarte de localizacao e bloco de
credito — para que o mapa estadual e os mapas regionais nao mantenham copias
divergentes das mesmas funcoes.

Tudo aqui assume coordenadas geograficas em graus decimais (EPSG:4326 / SIRGAS 2000).
"""

from __future__ import annotations

import datetime as dt
import json
import math
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")

from matplotlib.patches import Polygon as PoligonoMPL
from matplotlib.patches import Rectangle

import comum

FIGURAS = comum.RAIZ / "figuras"

FONTE_BARRAGENS = (
    "SNISB — Sistema Nacional de Informações sobre\n"
    "Segurança de Barragens (ANA)\n"
    "SIGBM — Sistema Integrado de Gestão de\n"
    "Barragens de Mineração (ANM)\n"
    "Malha territorial: IBGE"
)

DATA_ELABORACAO = dt.date.today().strftime("%m/%Y")


def ler_geojson(nome: str) -> dict[str, Any]:
    return json.loads((comum.DADOS_TRATADOS / nome).read_text(encoding="utf-8"))


def numero(valor: Any) -> float | None:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def aneis(geometria: dict[str, Any]) -> Iterable[list[list[float]]]:
    """Percorre os aneis externos de um Polygon ou MultiPolygon GeoJSON."""
    tipo = geometria.get("type")
    coordenadas = geometria.get("coordinates", [])
    if tipo == "Polygon":
        yield from coordenadas
    elif tipo == "MultiPolygon":
        for parte in coordenadas:
            yield from parte


def linhas(geometria: dict[str, Any]) -> Iterable[list[list[float]]]:
    """Percorre as polilinhas de um LineString ou MultiLineString GeoJSON."""
    tipo = geometria.get("type")
    coordenadas = geometria.get("coordinates", [])
    if tipo == "LineString":
        yield coordenadas
    elif tipo == "MultiLineString":
        yield from coordenadas


def desenhar_malha(eixo, geojson: dict[str, Any], **estilo) -> None:
    for feicao in geojson.get("features", []):
        for anel in aneis(feicao.get("geometry") or {}):
            eixo.add_patch(PoligonoMPL(anel, closed=True, **estilo))


def grau_para_dms(valor: float, eixo_horizontal: bool, com_minutos: bool = True) -> str:
    hemisferio = ("W" if valor < 0 else "E") if eixo_horizontal else ("S" if valor < 0 else "N")
    absoluto = abs(valor)
    graus = int(absoluto)
    minutos = int(round((absoluto - graus) * 60))
    if minutos == 60:
        graus, minutos = graus + 1, 0
    if not com_minutos:
        return f"{graus}°{hemisferio}"
    return f"{graus}°{minutos:02d}'{hemisferio}"


def _passo_da_grade(extensao_graus: float) -> float:
    """Escolhe um intervalo de grade legivel para a extensao da prancha."""
    for candidato in (0.1, 0.25, 0.5, 1.0, 2.0, 5.0):
        if extensao_graus / candidato <= 8:
            return candidato
    return 10.0


def formatar_grade(
    eixo, limites: tuple[float, float, float, float], passo: float | None = None
) -> None:
    oeste, leste, sul, norte = limites
    intervalo = passo or _passo_da_grade(max(leste - oeste, norte - sul))

    def marcas(inicio: float, fim: float) -> list[float]:
        primeira = math.ceil(inicio / intervalo) * intervalo
        quantidade = int((fim - primeira) / intervalo) + 1
        return [round(primeira + i * intervalo, 6) for i in range(max(quantidade, 0))]

    eixo.set_xticks(marcas(oeste, leste))
    eixo.set_yticks(marcas(sul, norte))
    eixo.set_xticklabels(
        [grau_para_dms(t, True) for t in eixo.get_xticks()], fontsize=7
    )
    eixo.set_yticklabels(
        [grau_para_dms(t, False) for t in eixo.get_yticks()], fontsize=7
    )
    eixo.grid(True, color="#b0b0b0", linewidth=0.4, linestyle=":", alpha=0.8)
    eixo.tick_params(direction="in", length=3)


def rosa_dos_ventos(eixo, x: float, y: float, tamanho: float = 0.055) -> None:
    eixo.annotate(
        "N",
        xy=(x, y),
        xytext=(x, y - tamanho),
        xycoords="axes fraction",
        textcoords="axes fraction",
        arrowprops={"facecolor": "black", "width": 3.2, "headwidth": 10, "headlength": 9},
        ha="center",
        va="center",
        fontsize=10,
        fontweight="bold",
    )


def escala_grafica(eixo, limites: tuple[float, float, float, float], km: int = 200) -> None:
    """Barra de escala aproximada, valida na latitude central da prancha."""
    oeste, leste, sul, norte = limites
    latitude_central = (sul + norte) / 2
    graus_por_km = 1 / (111.32 * abs(math.cos(math.radians(latitude_central))))
    largura = km * graus_por_km

    # Canto inferior direito: o inferior esquerdo e ocupado pelo encarte de localizacao.
    x0 = leste - (leste - oeste) * 0.06 - largura
    y0 = sul + (norte - sul) * 0.055
    altura = (norte - sul) * 0.012

    eixo.add_patch(
        Rectangle(
            (x0 - largura * 0.08, y0 - altura * 2.6),
            largura * 1.16,
            altura * 6.4,
            facecolor="white",
            edgecolor="none",
            alpha=0.85,
            zorder=9,
        )
    )
    for indice in range(4):
        eixo.add_patch(
            Rectangle(
                (x0 + indice * largura / 4, y0),
                largura / 4,
                altura,
                facecolor="black" if indice % 2 == 0 else "white",
                edgecolor="black",
                linewidth=0.6,
                zorder=10,
            )
        )
    for indice in range(5):
        eixo.text(
            x0 + indice * largura / 4,
            y0 + altura * 1.4,
            f"{int(indice * km / 4)}",
            ha="center",
            va="bottom",
            fontsize=6.2,
            zorder=10,
        )
    eixo.text(
        x0 + largura / 2, y0 - altura * 0.7, "km", ha="center", va="top", fontsize=6.5, zorder=10
    )


def contorno_estado() -> list[list[list[float]]]:
    """Aneis do poligono de Mato Grosso, usados para reforcar o limite estadual."""
    brasil = ler_geojson("ibge_malha_ufs_brasil.geojson")
    for feicao in brasil.get("features", []):
        codigo = str((feicao.get("properties") or {}).get("codarea", "")).strip()
        if codigo == str(comum.UF_CODIGO_IBGE):
            return list(aneis(feicao.get("geometry") or {}))
    return []


def encarte_localizacao(
    figura,
    retangulo: list[float],
    destaque: tuple[float, float, float, float] | None = None,
) -> None:
    """Encarte do Brasil com Mato Grosso realcado.

    Quando `destaque` e informado, desenha tambem o retangulo do recorte dentro do
    estado, o que e necessario nos mapas regionais para situar a area ampliada.
    """
    eixo = figura.add_axes(retangulo)
    brasil = ler_geojson("ibge_malha_ufs_brasil.geojson")
    for feicao in brasil.get("features", []):
        codigo = str((feicao.get("properties") or {}).get("codarea", ""))
        realcar = codigo.startswith(str(comum.UF_CODIGO_IBGE))
        for anel in aneis(feicao.get("geometry") or {}):
            eixo.add_patch(
                PoligonoMPL(
                    anel,
                    closed=True,
                    facecolor="#c0392b" if realcar else "#f2f2f2",
                    edgecolor="#7f7f7f",
                    linewidth=0.3,
                )
            )
    if destaque:
        oeste, leste, sul, norte = destaque
        eixo.add_patch(
            Rectangle(
                (oeste, sul),
                leste - oeste,
                norte - sul,
                facecolor="none",
                edgecolor="#111111",
                linewidth=1.1,
                zorder=6,
            )
        )
    eixo.set_xlim(-74.5, -33.5)
    eixo.set_ylim(-34.5, 6.5)
    eixo.set_aspect("equal")
    eixo.set_xticks([])
    eixo.set_yticks([])
    for borda in eixo.spines.values():
        borda.set_linewidth(0.8)
    eixo.set_title("LOCALIZAÇÃO", fontsize=7, fontweight="bold", pad=3)


class PainelDeLegenda:
    """Coluna lateral da prancha, com secoes separadas por linha horizontal.

    A escala do eixo e travada em 0..1 porque, sem isso, cada linha desenhada reescala
    o eixo e desloca todos os textos posicionados em coordenada de dados.
    """

    def __init__(self, figura, retangulo: list[float], titulo: str = "LEGENDA") -> None:
        self.eixo = figura.add_axes(retangulo)
        self.eixo.set_xticks([])
        self.eixo.set_yticks([])
        self.eixo.set_xlim(0, 1)
        self.eixo.set_ylim(0, 1)
        self.eixo.set_autoscale_on(False)
        for borda in self.eixo.spines.values():
            borda.set_linewidth(1.1)
        self.eixo.text(
            0.5, 0.982, titulo, ha="center", va="top", fontsize=10.5, fontweight="bold"
        )

    def separador(self, y: float) -> None:
        self.eixo.plot([0.04, 0.96], [y, y], color="black", linewidth=0.8, clip_on=False)

    def secao(self, y: float, titulo: str) -> None:
        self.eixo.text(
            0.5, y, titulo, ha="center", va="top", fontsize=8.4, fontweight="bold"
        )

    def texto(self, y: float, conteudo: str, **estilo) -> None:
        padrao = {
            "ha": "center",
            "va": "top",
            "fontsize": 7.2,
            "linespacing": 1.9,
        }
        padrao.update(estilo)
        self.eixo.text(0.5, y, conteudo, **padrao)

    def lista(self, y: float, conteudo: str, **estilo) -> None:
        padrao = {
            "ha": "left",
            "va": "top",
            "fontsize": 7.4,
            "linespacing": 2.1,
        }
        padrao.update(estilo)
        self.eixo.text(0.06, y, conteudo, **padrao)

    def creditos(self, fonte: str, elaboracao: str) -> None:
        """Bloco fixo do pe do painel: coordenadas, fonte e elaboracao."""
        self.separador(0.418)
        self.secao(0.398, "SISTEMA DE COORDENADAS")
        self.texto(0.368, "Datum: SIRGAS 2000 (EPSG: 4674)")
        self.separador(0.336)
        self.secao(0.316, "FONTE DOS DADOS")
        self.texto(0.286, fonte, fontsize=6.5)
        self.separador(0.170)
        self.secao(0.150, "ELABORAÇÃO")
        self.texto(0.118, elaboracao)


def salvar(figura, arquivo: str) -> Any:
    FIGURAS.mkdir(parents=True, exist_ok=True)
    destino = FIGURAS / arquivo
    figura.savefig(destino, facecolor="white")
    print(f"  gravado {destino.relative_to(comum.RAIZ)}")
    return destino
