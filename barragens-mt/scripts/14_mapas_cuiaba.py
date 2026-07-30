"""Gera as pranchas regionais de Cuiaba e entorno, do Manso ao Pantanal.

O recorte destas figuras nao e o municipio de Cuiaba. E a bacia contribuinte a capital,
e por isso a prancha precisa alcancar Chapada dos Guimaraes e o Lago do Manso a norte e
descer o rio Cuiaba a sul, mostrando o eixo por onde uma onda de ruptura se propagaria.
Mapear pelo limite municipal esconderia a estrutura de maior dano potencial da bacia.

Duas figuras:
  mapa_cuiaba_barragens_montante.png   barragens que drenam para a capital, eixo do rio
                                       e o reservatorio de Manso identificado
  mapa_cuiaba_populacoes_saude.png     aldeias, assentamentos, territorios quilombolas e
                                       rede hospitalar sobre o mesmo eixo

Saidas em figuras/.
"""

from __future__ import annotations

import csv
import json
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon as PoligonoMPL

import cartografia
import comum

CORES_CRI = {
    "Alto": "#d7191c",
    "Médio": "#fdae61",
    "Baixo": "#ffd92f",
    "Não Classificado": "#808080",
    "Não se Aplica": "#c6c6c6",
}
ORDEM_CRI = ["Alto", "Médio", "Baixo", "Não Classificado", "Não se Aplica"]

AZUL_AGUA = "#3182bd"
AZUL_EIXO = "#08519c"

FONTE_REGIONAL = (
    "Barragens: SNISB (ANA) e SIGBM (ANM)\n"
    "Hidrografia e massas d'água: BHO/ANA\n"
    "Terras indígenas e aldeias: FUNAI\n"
    "Assentamentos e quilombolas: INCRA\n"
    "Rede de saúde: CNES/Ministério da Saúde\n"
    "Malha territorial: IBGE"
)

ELABORACAO = (
    f"Sistema de Monitoramento de Barragens\nMato Grosso — {cartografia.DATA_ELABORACAO}"
)


def ler_csv(nome: str) -> list[dict[str, Any]]:
    caminho = comum.DADOS_TRATADOS / nome
    if not caminho.exists():
        raise SystemExit(f"base ausente: {caminho.name}")
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def recorte_de_interesse() -> dict[str, Any]:
    caminho = comum.DADOS_TRATADOS / "cuiaba_municipios_de_interesse.json"
    if not caminho.exists():
        raise SystemExit("rode antes: python scripts/12_analise_cuiaba.py")
    return json.loads(caminho.read_text(encoding="utf-8"))


def reservatorio_manso() -> list[dict[str, Any]]:
    """Espelho d'agua do Aproveitamento Multiplo de Manso na base de massas d'agua."""
    massas = cartografia.ler_geojson("ana_massas_dagua_mt.geojson")
    return [
        f
        for f in massas.get("features", [])
        if "MANSO" in ((f.get("properties") or {}).get("nmoriginal") or "").upper()
    ]


def centroide_de(geometria: dict[str, Any]) -> tuple[float, float] | None:
    pontos = [p for anel in cartografia.aneis(geometria) for p in anel]
    if not pontos:
        return None
    return (
        sum(p[0] for p in pontos) / len(pontos),
        sum(p[1] for p in pontos) / len(pontos),
    )


def limites_da_prancha(
    municipios_alvo: dict[str, dict[str, Any]], margem: float = 0.18
) -> tuple[float, float, float, float]:
    """Envelope dos municipios do recorte, com margem para o titulo e a legenda."""
    xs: list[float] = []
    ys: list[float] = []
    for feicao in municipios_alvo.values():
        for anel in cartografia.aneis(feicao.get("geometry") or {}):
            xs.extend(p[0] for p in anel)
            ys.extend(p[1] for p in anel)
    return (min(xs) - margem, max(xs) + margem, min(ys) - margem, max(ys) + margem)


def malha_por_codigo() -> dict[str, dict[str, Any]]:
    malha = cartografia.ler_geojson("ibge_malha_municipios_mt.geojson")
    return {
        str((f.get("properties") or {}).get("codarea", "")).strip(): f
        for f in malha.get("features", [])
    }


def base_da_prancha(
    titulo: str, recorte: dict[str, Any]
) -> tuple[Any, Any, tuple[float, float, float, float], dict[str, dict[str, Any]]]:
    """Monta moldura, malha municipal, eixo hidrografico e reservatorio de Manso."""
    malha = malha_por_codigo()
    alvo = {
        m["nome"]: malha[m["codigo_ibge"]]
        for m in recorte["municipios"]
        if m.get("codigo_ibge") in malha
    }
    limites = limites_da_prancha(alvo)
    oeste, leste, sul, norte = limites

    figura = plt.figure(figsize=(15.5, 10.5), dpi=170)
    figura.patch.set_facecolor("white")
    eixo = figura.add_axes([0.045, 0.045, 0.66, 0.87])

    # Municipios do estado como fundo, para o recorte nao parecer uma ilha.
    for feicao in malha.values():
        for anel in cartografia.aneis(feicao.get("geometry") or {}):
            eixo.add_patch(
                PoligonoMPL(
                    anel, closed=True, facecolor="#f2f2ee", edgecolor="#cfcfc6", linewidth=0.4
                )
            )
    # Municipios do recorte realcados.
    for feicao in alvo.values():
        for anel in cartografia.aneis(feicao.get("geometry") or {}):
            eixo.add_patch(
                PoligonoMPL(
                    anel,
                    closed=True,
                    facecolor="#fbf7ea",
                    edgecolor="#8c8c80",
                    linewidth=0.9,
                    zorder=2,
                )
            )

    for feicao in reservatorio_manso():
        for anel in cartografia.aneis(feicao.get("geometry") or {}):
            eixo.add_patch(
                PoligonoMPL(
                    anel,
                    closed=True,
                    facecolor=AZUL_AGUA,
                    edgecolor=AZUL_EIXO,
                    linewidth=0.7,
                    alpha=0.85,
                    zorder=3,
                )
            )

    eixo_hidrografico = cartografia.ler_geojson("eixo_hidrografico_manso_cuiaba.geojson")
    for feicao in eixo_hidrografico.get("features", []):
        segmento = (feicao.get("properties") or {}).get("segmento")
        for linha in cartografia.linhas(feicao.get("geometry") or {}):
            eixo.plot(
                [p[0] for p in linha],
                [p[1] for p in linha],
                color=AZUL_EIXO,
                linewidth=1.9 if segmento == "manso_capital" else 1.3,
                linestyle="-" if segmento == "manso_capital" else (0, (5, 2)),
                solid_capstyle="round",
                zorder=4,
            )

    for nome, feicao in alvo.items():
        ponto = centroide_de(feicao.get("geometry") or {})
        if ponto is None:
            continue
        eixo.text(
            ponto[0],
            ponto[1],
            nome.upper(),
            ha="center",
            va="center",
            fontsize=6.1,
            color="#3a3a32",
            zorder=12,
            path_effects=None,
        )

    eixo.set_xlim(oeste, leste)
    eixo.set_ylim(sul, norte)
    eixo.set_aspect("equal")
    cartografia.formatar_grade(eixo, limites)
    cartografia.rosa_dos_ventos(eixo, 0.955, 0.955)
    cartografia.escala_grafica(eixo, limites, km=50)
    for borda in eixo.spines.values():
        borda.set_linewidth(1.1)

    figura.text(
        0.045 + 0.66 / 2, 0.955, titulo, ha="center", va="center", fontsize=13.5, fontweight="bold"
    )
    cartografia.encarte_localizacao(figura, [0.058, 0.062, 0.135, 0.185], destaque=limites)
    return figura, eixo, limites, alvo


def mapa_barragens(recorte: dict[str, Any]) -> None:
    barragens = ler_csv("barragens_montante_cuiaba.csv")
    figura, eixo, limites, _ = base_da_prancha(
        "BARRAGENS A MONTANTE DE CUIABÁ E EIXO DE DRENAGEM DO RIO CUIABÁ", recorte
    )

    contagens: dict[str, int] = {}
    for chave in reversed(ORDEM_CRI):
        pontos = [
            (cartografia.numero(b.get("longitude")), cartografia.numero(b.get("latitude")))
            for b in barragens
            if (b.get("categoria_risco") or "").strip() == chave
        ]
        pontos = [p for p in pontos if p[0] is not None and p[1] is not None]
        contagens[chave] = len(pontos)
        if not pontos:
            continue
        eixo.scatter(
            [p[0] for p in pontos],
            [p[1] for p in pontos],
            s=42,
            c=CORES_CRI[chave],
            edgecolors="#333333",
            linewidths=0.4,
            zorder=6 + len(ORDEM_CRI) - ORDEM_CRI.index(chave),
        )

    manso = [b for b in barragens if "UHE MANSO" in (b.get("nome") or "").upper()]
    if manso:
        eixo.scatter(
            [cartografia.numero(b.get("longitude")) for b in manso],
            [cartografia.numero(b.get("latitude")) for b in manso],
            s=150,
            marker="*",
            c="#111111",
            edgecolors="white",
            linewidths=0.6,
            zorder=20,
            label="Complexo de Manso",
        )
        ponto = (
            cartografia.numero(manso[0].get("longitude")),
            cartografia.numero(manso[0].get("latitude")),
        )
        eixo.annotate(
            "Aproveitamento Múltiplo\nde Manso — 7.337 hm³",
            xy=ponto,
            xytext=(ponto[0] - 0.62, ponto[1] + 0.34),
            fontsize=7.4,
            fontweight="bold",
            ha="center",
            arrowprops={"arrowstyle": "->", "linewidth": 0.9, "color": "#111111"},
            zorder=21,
        )

    painel = cartografia.PainelDeLegenda(figura, [0.725, 0.045, 0.245, 0.87])
    painel.separador(0.952)
    painel.eixo.text(
        0.06,
        0.936,
        "Categoria de Risco - CRI",
        ha="left",
        va="top",
        fontsize=8.2,
        fontweight="bold",
    )
    marcadores = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=CORES_CRI[chave],
            markeredgecolor="#333333",
            markersize=8,
            label=f"{chave}  ({contagens[chave]})",
        )
        for chave in ORDEM_CRI
        if contagens[chave]
    ]
    marcadores += [
        Line2D(
            [0],
            [0],
            marker="*",
            color="none",
            markerfacecolor="#111111",
            markeredgecolor="white",
            markersize=13,
            label=f"Complexo de Manso  ({len(manso)})",
        ),
        Line2D([0], [0], color=AZUL_EIXO, linewidth=1.9, label="Eixo Manso — capital"),
        Line2D(
            [0],
            [0],
            color=AZUL_EIXO,
            linewidth=1.3,
            linestyle=(0, (5, 2)),
            label="Rio Cuiabá a jusante",
        ),
        Line2D([0], [0], color=AZUL_AGUA, linewidth=6, label="Reservatório"),
        Line2D([0], [0], color="#8c8c80", linewidth=1.1, label="Municípios do recorte"),
    ]
    painel.eixo.legend(
        handles=marcadores,
        loc="upper left",
        bbox_to_anchor=(0.04, 0.912),
        frameon=False,
        fontsize=8.0,
        handletextpad=0.7,
        labelspacing=0.8,
    )

    painel.separador(0.640)
    painel.secao(0.620, "SÍNTESE")
    dpa_alto = sum(1 for b in barragens if b.get("dano_potencial_associado") == "Alto")
    sem_pae = sum(1 for b in barragens if b.get("possui_pae") != "Sim")
    resumo = [
        f"Barragens que drenam para a capital: {len(barragens)}",
        f"Municípios envolvidos: {len({b.get('municipio') for b in barragens})}",
        f"Dano Potencial Associado alto: {dpa_alto}",
        f"Categoria de Risco alta: {contagens.get('Alto', 0)}",
        f"Sem Plano de Ação de Emergência: {sem_pae}",
        "Seção de controle: trecho 896573",
        "Drenagem a montante: 23.615 km²",
    ]
    painel.lista(0.590, "\n".join(resumo), fontsize=6.9, linespacing=1.75)
    painel.creditos(FONTE_REGIONAL, ELABORACAO)

    cartografia.salvar(figura, "mapa_cuiaba_barragens_montante.png")
    plt.close(figura)


def mapa_populacoes(recorte: dict[str, Any]) -> None:
    figura, eixo, limites, _ = base_da_prancha(
        "POPULAÇÕES VULNERÁVEIS E REDE DE SAÚDE NO EIXO MANSO — CUIABÁ", recorte
    )
    oeste, leste, sul, norte = limites

    def dentro(lon: Any, lat: Any) -> bool:
        x, y = cartografia.numero(lon), cartografia.numero(lat)
        return x is not None and y is not None and oeste <= x <= leste and sul <= y <= norte

    terras = cartografia.ler_geojson("funai_terras_indigenas_mt.geojson")
    total_terras = 0
    for feicao in terras.get("features", []):
        aneis_feicao = list(cartografia.aneis(feicao.get("geometry") or {}))
        if not any(dentro(p[0], p[1]) for anel in aneis_feicao for p in anel):
            continue
        total_terras += 1
        for anel in aneis_feicao:
            eixo.add_patch(
                PoligonoMPL(
                    anel,
                    closed=True,
                    facecolor="#f4a582",
                    edgecolor="#b2182b",
                    linewidth=0.8,
                    alpha=0.55,
                    zorder=5,
                )
            )

    assentamentos = cartografia.ler_geojson("incra_assentamentos_mt.geojson")
    total_assentamentos = 0
    for feicao in assentamentos.get("features", []):
        aneis_feicao = list(cartografia.aneis(feicao.get("geometry") or {}))
        if not any(dentro(p[0], p[1]) for anel in aneis_feicao for p in anel):
            continue
        total_assentamentos += 1
        for anel in aneis_feicao:
            eixo.add_patch(
                PoligonoMPL(
                    anel,
                    closed=True,
                    facecolor="#a6d96a",
                    edgecolor="#4d7f1f",
                    linewidth=0.6,
                    alpha=0.6,
                    zorder=5,
                )
            )

    exposicao = ler_csv("exposicao_populacoes_eixo_cuiaba.csv")
    aldeias = [
        l for l in exposicao if l["categoria"] == "aldeia indígena" and dentro(l["longitude"], l["latitude"])
    ]
    if aldeias:
        eixo.scatter(
            [cartografia.numero(l["longitude"]) for l in aldeias],
            [cartografia.numero(l["latitude"]) for l in aldeias],
            s=70,
            marker="^",
            c="#b2182b",
            edgecolors="white",
            linewidths=0.5,
            zorder=14,
        )

    saude = [l for l in exposicao if l["categoria"] == "estabelecimento de saúde"]
    hospitalares = [
        l for l in saude if l.get("hospitalar") == "Sim" and dentro(l["longitude"], l["latitude"])
    ]
    demais = [
        l for l in saude if l.get("hospitalar") != "Sim" and dentro(l["longitude"], l["latitude"])
    ]
    if demais:
        eixo.scatter(
            [cartografia.numero(l["longitude"]) for l in demais],
            [cartografia.numero(l["latitude"]) for l in demais],
            s=5,
            c="#6baed6",
            edgecolors="none",
            alpha=0.5,
            zorder=8,
        )
    if hospitalares:
        eixo.scatter(
            [cartografia.numero(l["longitude"]) for l in hospitalares],
            [cartografia.numero(l["latitude"]) for l in hospitalares],
            s=62,
            marker="P",
            c="#08306b",
            edgecolors="white",
            linewidths=0.5,
            zorder=15,
        )

    painel = cartografia.PainelDeLegenda(figura, [0.725, 0.045, 0.245, 0.87])
    painel.separador(0.952)
    painel.eixo.text(
        0.06, 0.936, "Territórios e serviços", ha="left", va="top", fontsize=8.2, fontweight="bold"
    )
    marcadores = [
        Line2D(
            [0],
            [0],
            marker="P",
            color="none",
            markerfacecolor="#08306b",
            markeredgecolor="white",
            markersize=10,
            label=f"Atendimento hospitalar  ({len(hospitalares)})",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor="#6baed6",
            markeredgecolor="none",
            markersize=5,
            label=f"Demais estabelecimentos  ({len(demais)})",
        ),
        Line2D(
            [0],
            [0],
            marker="^",
            color="none",
            markerfacecolor="#b2182b",
            markeredgecolor="white",
            markersize=9,
            label=f"Aldeia indígena  ({len(aldeias)})",
        ),
        Line2D([0], [0], color="#f4a582", linewidth=6, label=f"Terra indígena  ({total_terras})"),
        Line2D(
            [0],
            [0],
            color="#a6d96a",
            linewidth=6,
            label=f"Assentamento rural  ({total_assentamentos})",
        ),
        Line2D([0], [0], color=AZUL_EIXO, linewidth=1.9, label="Eixo Manso — capital"),
        Line2D(
            [0],
            [0],
            color=AZUL_EIXO,
            linewidth=1.3,
            linestyle=(0, (5, 2)),
            label="Rio Cuiabá a jusante",
        ),
        Line2D([0], [0], color=AZUL_AGUA, linewidth=6, label="Reservatório"),
    ]
    painel.eixo.legend(
        handles=marcadores,
        loc="upper left",
        bbox_to_anchor=(0.04, 0.912),
        frameon=False,
        fontsize=8.0,
        handletextpad=0.7,
        labelspacing=0.8,
    )

    palmares = ler_csv("palmares_quilombolas_mt.csv")
    nomes_recorte = {m["nome"].upper() for m in recorte["municipios"]}
    certificadas = [
        r for r in palmares if (r.get("MUNICÍPIO") or "").strip().upper() in nomes_recorte
    ]

    painel.separador(0.640)
    painel.secao(0.620, "SÍNTESE")
    resumo = [
        f"Estabelecimentos de saúde: {len(saude)}",
        f"Com atendimento hospitalar: {len(hospitalares)}",
        "Sem hospital próprio: Acorizal,",
        "   Chapada dos Guimarães e Jangada",
        f"Comunidades quilombolas certificadas: {len(certificadas)}",
        f"Assentamentos na prancha: {total_assentamentos}",
        "Sem mancha de inundação disponível:",
        "   proximidade não é exposição",
    ]
    painel.lista(0.590, "\n".join(resumo), fontsize=6.9, linespacing=1.6)
    painel.creditos(FONTE_REGIONAL, ELABORACAO)

    cartografia.salvar(figura, "mapa_cuiaba_populacoes_saude.png")
    plt.close(figura)


def main() -> None:
    recorte = recorte_de_interesse()
    print(f"Gerando pranchas regionais para {len(recorte['municipios'])} municipios")
    mapa_barragens(recorte)
    mapa_populacoes(recorte)


if __name__ == "__main__":
    main()
