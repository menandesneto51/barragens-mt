"""Verifica se o codigo de trecho de curso d'agua (otto ANA) esta preenchido.

Se estiver, permite determinar montante/jusante por topologia de bacia em vez de
limite municipal, que foi justamente o vies apontado.
"""

from __future__ import annotations

import csv
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

import comum


def sem_acento(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normalizado if not unicodedata.combining(c)).upper()


def ler(caminho: Path) -> list[dict[str, Any]]:
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def main() -> None:
    inventario = ler(comum.DADOS_TRATADOS / "inventario_barragens_mt.csv")

    preenchidos = [r for r in inventario if (r.get("codigo_trecho_curso_dagua") or "").strip()]
    print(f"codigo_trecho_curso_dagua preenchido: {len(preenchidos)}/{len(inventario)}")

    if preenchidos:
        print("\namostra de codigos:")
        for registro in preenchidos[:20]:
            print(
                f"  {registro.get('codigo_trecho_curso_dagua'):>18s}  "
                f"{registro.get('municipio','')[:22]:24s} {registro.get('curso_dagua','')[:28]:30s} "
                f"{registro.get('nome','')[:34]}"
            )
        tamanhos = Counter(len((r.get("codigo_trecho_curso_dagua") or "").strip()) for r in preenchidos)
        print(f"\n  tamanhos de codigo: {dict(tamanhos)}")

    print("\n" + "=" * 78)
    print("CODIGOS DAS ESTRUTURAS DO MANSO E DAS BARRAGENS DE CUIABA")
    print("=" * 78)
    for rotulo, filtro in [
        ("MANSO", lambda r: "MANSO" in sem_acento(r.get("nome", ""))),
        ("CUIABA (municipio)", lambda r: sem_acento(r.get("municipio", "")) == "CUIABA"),
    ]:
        grupo = [r for r in inventario if filtro(r)]
        print(f"\n  {rotulo}: {len(grupo)} registros")
        for registro in grupo[:12]:
            print(
                f"    otto={registro.get('codigo_trecho_curso_dagua') or '(vazio)':>18s}  "
                f"rio={registro.get('curso_dagua','')[:26]:28s} "
                f"ug={registro.get('unidade_de_gestao') or '(vazio)':38s} "
                f"{registro.get('nome','')[:30]}"
            )

    print("\n" + "=" * 78)
    print("UNIDADE DE GESTAO / COMITE POR MUNICIPIO DO EIXO DO CUIABA")
    print("=" * 78)
    eixo = [
        "CHAPADA DOS GUIMARAES",
        "NOBRES",
        "ROSARIO OESTE",
        "JANGADA",
        "ACORIZAL",
        "CUIABA",
        "VARZEA GRANDE",
        "SANTO ANTONIO DE LEVERGER",
        "NOSSA SENHORA DO LIVRAMENTO",
        "POCONE",
        "BARAO DE MELGACO",
        "CAMPO VERDE",
    ]
    for nome_municipio in eixo:
        grupo = [r for r in inventario if sem_acento(r.get("municipio", "")) == nome_municipio]
        if not grupo:
            print(f"\n  {nome_municipio}: ausente do cadastro")
            continue
        print(f"\n  {nome_municipio}: {len(grupo)}")
        for valor, quantidade in Counter(
            (r.get("unidade_de_gestao") or "(vazio)") for r in grupo
        ).most_common():
            print(f"      {quantidade:4d}  ug={valor}")
        for valor, quantidade in Counter(
            (r.get("regiao_hidrografica") or "(vazio)") for r in grupo
        ).most_common():
            print(f"      {quantidade:4d}  rh={valor}")


if __name__ == "__main__":
    main()
