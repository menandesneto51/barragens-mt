"""Sondagem dos campos de bacia do inventario.

Objetivo: descobrir qual campo permite recortar as barragens por posicao na bacia
do rio Cuiaba, em vez de por limite municipal.
"""

from __future__ import annotations

import csv
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

import comum

CUIABA_LAT = -15.601
CUIABA_LON = -56.098


def sem_acento(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normalizado if not unicodedata.combining(c)).upper()


def ler(caminho: Path) -> list[dict[str, Any]]:
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def numero(valor: Any) -> float | None:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def main() -> None:
    inventario = ler(comum.DADOS_TRATADOS / "inventario_barragens_mt.csv")

    print("=" * 78)
    print("REGIAO HIDROGRAFICA")
    print("=" * 78)
    for valor, quantidade in Counter(r.get("regiao_hidrografica") or "(vazio)" for r in inventario).most_common():
        print(f"  {quantidade:5d}  {valor}")

    print("\n" + "=" * 78)
    print("COMITE DE BACIA ESTADUAL")
    print("=" * 78)
    for valor, quantidade in Counter(r.get("comite_de_bacia_estadual") or "(vazio)" for r in inventario).most_common():
        print(f"  {quantidade:5d}  {valor}")

    print("\n" + "=" * 78)
    print("UNIDADE DE GESTAO")
    print("=" * 78)
    for valor, quantidade in Counter(r.get("unidade_de_gestao") or "(vazio)" for r in inventario).most_common(30):
        print(f"  {quantidade:5d}  {valor}")

    print("\n" + "=" * 78)
    print("BACIA DNAEE")
    print("=" * 78)
    for valor, quantidade in Counter(r.get("bacia_dnaee") or "(vazio)" for r in inventario).most_common(20):
        print(f"  {quantidade:5d}  {valor}")

    print("\n" + "=" * 78)
    print("COMITE DE BACIA FEDERAL")
    print("=" * 78)
    for valor, quantidade in Counter(r.get("comite_de_bacia_federal") or "(vazio)" for r in inventario).most_common(20):
        print(f"  {quantidade:5d}  {valor}")

    print("\n" + "=" * 78)
    print("CURSOS D'AGUA DA REDE DO CUIABA (busca textual)")
    print("=" * 78)
    chaves = ["CUIABA", "MANSO", "COXIPO", "ARICA", "JANGADA", "MUTUM", "CASCA", "PARI", "ACORIZAL", "MARZAGAO"]
    for chave in chaves:
        grupo = [r for r in inventario if chave in sem_acento(r.get("curso_dagua", ""))]
        if not grupo:
            continue
        print(f"\n  '{chave}': {len(grupo)} barragens")
        for valor, quantidade in Counter(
            f"{r.get('curso_dagua')} | {r.get('municipio')}" for r in grupo
        ).most_common(12):
            print(f"      {quantidade:4d}  {valor}")

    print("\n" + "=" * 78)
    print("BARRAGENS AO NORTE DE CUIABA (montante potencial) NA BACIA DO PARAGUAI")
    print("=" * 78)
    print("Criterio: latitude > Cuiaba (rio corre para sul) e regiao hidrografica Paraguai")
    montante = []
    for registro in inventario:
        latitude = numero(registro.get("latitude"))
        longitude = numero(registro.get("longitude"))
        if latitude is None or longitude is None:
            continue
        if "PARAGUAI" not in sem_acento(registro.get("regiao_hidrografica", "")):
            continue
        if latitude <= CUIABA_LAT:
            continue
        if not (-57.5 <= longitude <= -54.5):
            continue
        montante.append(registro)

    print(f"\n  total: {len(montante)} barragens")
    por_municipio = Counter(r.get("municipio") or "(vazio)" for r in montante)
    for valor, quantidade in por_municipio.most_common():
        capacidade = sum(numero(r.get("capacidade_hm3")) or 0 for r in montante if r.get("municipio") == valor)
        dpa_alto = sum(
            1 for r in montante if r.get("municipio") == valor and r.get("dano_potencial_associado") == "Alto"
        )
        print(f"  {quantidade:5d}  {valor:32s} DPA alto={dpa_alto:3d}  cap.somada={capacidade:12,.1f} hm3")

    print("\n  -- as de DPA Alto ou CRI Alto entre elas --")
    for registro in montante:
        if registro.get("dano_potencial_associado") == "Alto" or registro.get("categoria_risco") == "Alto":
            print(
                f"    {registro.get('nome','')[:42]:44s} {registro.get('municipio','')[:24]:26s} "
                f"CRI={registro.get('categoria_risco') or '-':8s} DPA={registro.get('dano_potencial_associado') or '-':8s} "
                f"cap={numero(registro.get('capacidade_hm3')) or 0:10,.1f} hm3  rio={registro.get('curso_dagua')}"
            )


if __name__ == "__main__":
    main()
