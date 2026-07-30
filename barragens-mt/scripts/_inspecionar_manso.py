"""Inspecao pontual dos registros do Aproveitamento de Manso e do entorno de Cuiaba.

Nao faz parte do pipeline. Serve para conferir nos dados, campo a campo, o que o
cadastro realmente diz antes de escrever qualquer afirmacao no relatorio.
"""

from __future__ import annotations

import csv
import unicodedata
from pathlib import Path
from typing import Any

import comum


def sem_acento(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normalizado if not unicodedata.combining(c)).upper()


def ler(caminho: Path) -> list[dict[str, Any]]:
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def mostrar(registro: dict[str, Any], campos: list[str]) -> None:
    for campo in campos:
        valor = registro.get(campo)
        if valor not in (None, "", "None"):
            print(f"    {campo:34s} {valor}")


def main() -> None:
    inventario = ler(comum.DADOS_TRATADOS / "inventario_barragens_mt.csv")
    print(f"inventario: {len(inventario)} registros")
    print(f"colunas: {list(inventario[0].keys())}\n")

    print("=" * 78)
    print("1. REGISTROS COM 'MANSO' NO NOME")
    print("=" * 78)
    manso = [r for r in inventario if "MANSO" in sem_acento(r.get("nome", ""))]
    for registro in manso:
        print(f"\n  [{registro.get('id_snisb')}] {registro.get('nome')}")
        mostrar(
            registro,
            [
                "municipio",
                "codigo_ibge",
                "orgao_fiscalizador",
                "empreendedor",
                "categoria_risco",
                "dano_potencial_associado",
                "classe",
                "classe_cnrh",
                "prioridade_fiscalizacao",
                "altura_m",
                "altura_max_terreno_m",
                "altura_max_fundacao_m",
                "capacidade_hm3",
                "capacidade_m3",
                "curso_dagua",
                "dominio_curso_dagua",
                "regiao_hidrografica",
                "uso_principal",
                "uso_complementar",
                "tipo_material",
                "fase_de_vida",
                "possui_plano_de_seguranca",
                "possui_pae",
                "possui_revisao_periodica",
                "data_ultima_inspecao",
                "tipo_ultima_inspecao",
                "regulada_pelo_pnsb",
                "completude_cadastro",
                "nivel_de_perigo",
                "barragem_autuada",
                "latitude",
                "longitude",
                "comite_de_bacia_estadual",
                "unidade_de_gestao",
            ],
        )

    print("\n" + "=" * 78)
    print("2. TODAS AS BARRAGENS DE CHAPADA DOS GUIMARAES")
    print("=" * 78)
    chapada = [r for r in inventario if sem_acento(r.get("municipio", "")) == "CHAPADA DOS GUIMARAES"]
    print(f"  total: {len(chapada)}")
    for registro in sorted(chapada, key=lambda r: -(float(r.get("capacidade_hm3") or 0))):
        print(
            f"    {registro.get('nome','')[:44]:46s} "
            f"cap={registro.get('capacidade_hm3') or '-':>10s} hm3  "
            f"alt={registro.get('altura_m') or '-':>6s} m  "
            f"CRI={registro.get('categoria_risco') or '-':16s} "
            f"DPA={registro.get('dano_potencial_associado') or '-':16s} "
            f"rio={registro.get('curso_dagua') or '-'}"
        )

    print("\n" + "=" * 78)
    print("3. MAIORES RESERVATORIOS DO ESTADO (capacidade declarada)")
    print("=" * 78)
    def cap(registro: dict[str, Any]) -> float:
        try:
            return float(registro.get("capacidade_hm3") or 0)
        except ValueError:
            return 0.0

    for registro in sorted(inventario, key=cap, reverse=True)[:15]:
        print(
            f"    {cap(registro):12,.1f} hm3  {registro.get('municipio','')[:26]:28s} "
            f"{registro.get('nome','')[:44]:46s} DPA={registro.get('dano_potencial_associado') or '-'}"
        )

    print("\n" + "=" * 78)
    print("4. CURSOS D'AGUA DAS BARRAGENS DE CUIABA E VIZINHOS A MONTANTE")
    print("=" * 78)
    vizinhos = [
        "CUIABA",
        "CHAPADA DOS GUIMARAES",
        "NOSSA SENHORA DO LIVRAMENTO",
        "POCONE",
        "SANTO ANTONIO DE LEVERGER",
        "VARZEA GRANDE",
        "JANGADA",
        "ACORIZAL",
        "ROSARIO OESTE",
        "NOBRES",
        "PLANALTO DA SERRA",
        "CAMPO VERDE",
        "NOVA BRASILANDIA",
    ]
    for nome_municipio in vizinhos:
        grupo = [r for r in inventario if sem_acento(r.get("municipio", "")) == nome_municipio]
        if not grupo:
            print(f"  {nome_municipio}: sem registro no cadastro")
            continue
        rios: dict[str, int] = {}
        for registro in grupo:
            rio = (registro.get("curso_dagua") or "(nao informado)").strip()
            rios[rio] = rios.get(rio, 0) + 1
        alto_dpa = sum(1 for r in grupo if r.get("dano_potencial_associado") == "Alto")
        alto_cri = sum(1 for r in grupo if r.get("categoria_risco") == "Alto")
        total_cap = sum(cap(r) for r in grupo)
        print(
            f"\n  {nome_municipio}: {len(grupo)} barragens | DPA alto {alto_dpa} | "
            f"CRI alto {alto_cri} | capacidade somada {total_cap:,.1f} hm3"
        )
        for rio, quantidade in sorted(rios.items(), key=lambda x: -x[1])[:8]:
            print(f"      {quantidade:4d}  {rio}")


if __name__ == "__main__":
    main()
