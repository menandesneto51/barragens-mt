"""Gera as figuras cartograficas estaduais do inventario de barragens de Mato Grosso.

Reproduz o padrao de prancha usado no projeto (titulo, moldura, grade em graus,
legenda lateral, rosa dos ventos, escala grafica, encarte de localizacao e bloco de
fonte dos dados), com os 141 municipios de MT e as barragens do inventario consolidado.

Os primitivos de prancha vivem em `cartografia.py`, compartilhados com os mapas
regionais do script 14.

Saidas em figuras/.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon as PoligonoMPL

import cartografia
import comum

# Mesma semantica de cor das pranchas de referencia: quente = mais critico.
CORES_CRI = {
    "Alto": "#d7191c",
    "Médio": "#fdae61",
    "Baixo": "#ffd92f",
    "Não Classificado": "#808080",
    "Não se Aplica": "#c6c6c6",
}
ORDEM_CRI = ["Alto", "Médio", "Baixo", "Não Classificado", "Não se Aplica"]

CORES_ORGAO = {
    "MT - Secretaria de Estado do Meio Ambiente - SEMA": "#1b7837",
    "Agência Nacional de Mineração - ANM": "#762a83",
    "Agência Nacional de Energia Elétrica - ANEEL": "#2166ac",
    "Agência Nacional de Águas e Saneamento Básico - ANA": "#e08214",
}
ROTULO_ORGAO = {
    "MT - Secretaria de Estado do Meio Ambiente - SEMA": "SEMA-MT",
    "Agência Nacional de Mineração - ANM": "ANM",
    "Agência Nacional de Energia Elétrica - ANEEL": "ANEEL",
    "Agência Nacional de Águas e Saneamento Básico - ANA": "ANA",
}

ELABORACAO = (
    f"Sistema de Monitoramento de Barragens\nMato Grosso — {cartografia.DATA_ELABORACAO}"
)


def ler_inventario() -> list[dict[str, Any]]:
    caminho = comum.DADOS_TRATADOS / "inventario_barragens_mt.csv"
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def mapa_por_categoria(
    barragens: list[dict[str, Any]],
    coluna: str,
    cores: dict[str, str],
    ordem: list[str],
    titulo: str,
    rotulo_legenda: str,
    arquivo: str,
    rotulos: dict[str, str] | None = None,
) -> Path:
    municipios = cartografia.ler_geojson("ibge_malha_municipios_mt.geojson")
    limites = (-62.0, -49.9, -18.2, -7.2)
    oeste, leste, sul, norte = limites

    figura = plt.figure(figsize=(15.5, 10.5), dpi=170)
    figura.patch.set_facecolor("white")

    eixo = figura.add_axes([0.045, 0.045, 0.66, 0.87])
    cartografia.desenhar_malha(
        eixo, municipios, facecolor="#f6f6f1", edgecolor="#bdbdb4", linewidth=0.4
    )
    for anel in cartografia.contorno_estado():
        eixo.add_patch(
            PoligonoMPL(
                anel,
                closed=True,
                facecolor="none",
                edgecolor="#d95f0e",
                linewidth=1.6,
                zorder=4,
            )
        )

    contagens: dict[str, int] = {}
    # Desenha do menos para o mais critico para que os pontos de risco alto fiquem
    # visiveis por cima do adensamento de pontos de risco baixo.
    for chave in reversed(ordem):
        pontos = [
            (cartografia.numero(b.get("longitude")), cartografia.numero(b.get("latitude")))
            for b in barragens
            if (b.get(coluna) or "").strip() == chave
        ]
        pontos = [(x, y) for x, y in pontos if x is not None and y is not None]
        contagens[chave] = len(pontos)
        if not pontos:
            continue
        eixo.scatter(
            [p[0] for p in pontos],
            [p[1] for p in pontos],
            s=19,
            c=cores[chave],
            edgecolors="#333333",
            linewidths=0.3,
            alpha=0.92,
            zorder=5 + ordem.index(chave) * -1 + len(ordem),
        )

    eixo.set_xlim(oeste, leste)
    eixo.set_ylim(sul, norte)
    eixo.set_aspect("equal")
    cartografia.formatar_grade(eixo, limites, passo=2.0)
    cartografia.rosa_dos_ventos(eixo, 0.955, 0.955)
    cartografia.escala_grafica(eixo, limites, km=200)
    for borda in eixo.spines.values():
        borda.set_linewidth(1.1)

    figura.text(
        0.045 + 0.66 / 2,
        0.955,
        titulo,
        ha="center",
        va="center",
        fontsize=14.5,
        fontweight="bold",
    )

    painel = cartografia.PainelDeLegenda(figura, [0.725, 0.045, 0.245, 0.87])
    painel.separador(0.952)
    painel.eixo.text(
        0.06, 0.936, rotulo_legenda, ha="left", va="top", fontsize=8.2, fontweight="bold"
    )

    marcadores = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=cores[chave],
            markeredgecolor="#333333",
            markeredgewidth=0.4,
            markersize=8,
            label=f"{(rotulos or {}).get(chave, chave)}  ({contagens[chave]})",
        )
        for chave in ordem
        if contagens[chave]
    ]
    marcadores += [
        Line2D([0], [0], color="#d95f0e", linewidth=1.6, label="Limite estadual"),
        Line2D([0], [0], color="#bdbdb4", linewidth=0.9, label="Limite municipal"),
    ]
    painel.eixo.legend(
        handles=marcadores,
        loc="upper left",
        bbox_to_anchor=(0.04, 0.912),
        frameon=False,
        fontsize=8.2,
        handletextpad=0.7,
        labelspacing=0.85,
    )

    total = sum(contagens.values())
    painel.separador(0.660)
    painel.secao(0.640, "SÍNTESE")
    resumo = [
        f"Total de barragens cadastradas: {total}",
        f"Municípios com barragem: "
        f"{len({b.get('municipio') for b in barragens if b.get('municipio')})} de 141",
        f"Categoria de Risco alta: "
        f"{sum(1 for b in barragens if b.get('categoria_risco') == 'Alto')}",
        f"Dano Potencial Associado alto: "
        f"{sum(1 for b in barragens if b.get('dano_potencial_associado') == 'Alto')}",
        f"Com Plano de Segurança: "
        f"{sum(1 for b in barragens if b.get('possui_plano_de_seguranca') == 'Sim')}",
        f"Com Plano de Ação de Emergência: "
        f"{sum(1 for b in barragens if b.get('possui_pae') == 'Sim')}",
    ]
    painel.lista(0.608, "\n".join(resumo))
    painel.creditos(cartografia.FONTE_BARRAGENS, ELABORACAO)

    cartografia.encarte_localizacao(figura, [0.058, 0.062, 0.135, 0.185])

    destino = cartografia.salvar(figura, arquivo)
    plt.close(figura)
    return destino


def main() -> None:
    barragens = ler_inventario()
    print(f"Gerando mapas para {len(barragens)} barragens")

    mapa_por_categoria(
        barragens,
        coluna="categoria_risco",
        cores=CORES_CRI,
        ordem=ORDEM_CRI,
        titulo="BARRAGENS DE MATO GROSSO POR CATEGORIA DE RISCO (CRI)",
        rotulo_legenda="Categoria de Risco - CRI",
        arquivo="mapa_barragens_mt_cri.png",
    )
    mapa_por_categoria(
        barragens,
        coluna="orgao_fiscalizador",
        cores=CORES_ORGAO,
        ordem=list(CORES_ORGAO),
        titulo="BARRAGENS DE MATO GROSSO POR ÓRGÃO FISCALIZADOR",
        rotulo_legenda="Órgão fiscalizador",
        arquivo="mapa_barragens_mt_orgao.png",
        rotulos=ROTULO_ORGAO,
    )


if __name__ == "__main__":
    main()
