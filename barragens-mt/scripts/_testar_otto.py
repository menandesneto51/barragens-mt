"""Confere a regra de Pfafstetter em casos conhecidos e classifica o cadastro."""

from __future__ import annotations

import csv
import json
import math
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import comum
import otto

# Trecho do rio Cuiaba na altura da capital, obtido por proximidade geografica
# entre a mancha urbana e a BHO 50K da ANA.
COBACIA_CUIABA = "896573"
COTRECHO_CUIABA = None  # resolvido em tempo de execucao
CUIABA_PONTO = (-56.0979, -15.6014)


def sem_acento(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normalizado if not unicodedata.combining(c)).upper()


def numero(valor: Any) -> float | None:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def distancia_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    raio = 6371.0
    lon1, lat1, lon2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    return 2 * raio * math.asin(
        math.sqrt(
            math.sin((lat2 - lat1) / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
        )
    )


def main() -> None:
    print("=" * 78)
    print("1. CONFERENCIA DA REGRA EM CASOS CONHECIDOS")
    print("=" * 78)
    casos = [
        ("89679", "896573", otto.Relacao.MONTANTE, "barragem do Manso -> capital"),
        ("89678", "8965754", otto.Relacao.MONTANTE, "diques do Manso -> rio Bandeira, em Cuiaba"),
        ("896573", "89679", otto.Relacao.JUSANTE, "capital -> barragem do Manso"),
        ("896573", "896573", otto.Relacao.MESMO_TRECHO, "mesmo trecho"),
        ("89657542", "8965754", otto.Relacao.CONTIDO, "Dois Corregos dentro do rio Bandeira"),
        # A interbacia 9 e a mais alta da calha: o rio Casca desagua no reservatorio
        # de Manso, e nao num ramo separado. O digito impar denuncia calha principal.
        ("896911", "896573", otto.Relacao.MONTANTE, "rio Casca -> reservatorio de Manso -> capital"),
        ("8965752", "896573", otto.Relacao.MONTANTE, "interbacia 5 esta acima da interbacia 3"),
        # Contraprova do vies corrigido: Pocone esta na bacia do Paraguai e ao norte
        # de boa parte da capital, mas drena pelo rio Bento Gomes, fora da calha.
        ("8966", "896573", otto.Relacao.OUTRO_RAMO, "bacia tributaria par nao alcanca a calha em 3"),
    ]
    for a, b, esperado, descricao in casos:
        obtido = otto.relacao(a, b)
        marca = "ok " if obtido == esperado else "ERRO"
        print(f"  {marca} {a:>9s} vs {b:>9s}  esperado={esperado.value:14s} obtido={obtido.value:14s} {descricao}")

    print("\n" + "=" * 78)
    print("2. TRECHOS DA BHO: RESOLVENDO O TRECHO DA CAPITAL")
    print("=" * 78)
    bho = json.loads((comum.DADOS_TRATADOS / "ana_bho_trechos_bacia_cuiaba.geojson").read_text(encoding="utf-8"))
    indice = otto.indexar_trechos(bho["features"])
    print(f"  {len(indice)} trechos indexados")

    alvo = [t for t in indice.values() if t.cobacia == COBACIA_CUIABA]
    for trecho in alvo:
        print(
            f"  trecho da capital: cotrecho={trecho.cotrecho} cobacia={trecho.cobacia} rio={trecho.rio} "
            f"area_montante={trecho.area_montante_km2:,.1f} km2 dist_foz={trecho.distancia_foz_km:,.1f} km"
        )
    trecho_capital = alvo[0]

    manso = [t for t in indice.values() if t.cobacia == "89679"]
    for trecho in manso:
        print(
            f"  trecho do Manso:   cotrecho={trecho.cotrecho} cobacia={trecho.cobacia} rio='{trecho.rio}' "
            f"area_montante={trecho.area_montante_km2:,.1f} km2 dist_foz={trecho.distancia_foz_km:,.1f} km"
        )
    trecho_manso = manso[0]

    print(f"\n  area de drenagem controlada pelo Manso: {trecho_manso.area_montante_km2:,.1f} km2")
    print(f"  area de drenagem a montante da capital: {trecho_capital.area_montante_km2:,.1f} km2")
    fracao = trecho_manso.area_montante_km2 / trecho_capital.area_montante_km2
    print(f"  fracao da bacia de Cuiaba controlada pelo Manso: {fracao:.1%}")

    print("\n  distancia pelo talvegue, Manso -> capital:")
    percurso = otto.caminho_jusante(indice, trecho_manso.cotrecho, trecho_capital.cotrecho)
    if percurso is None:
        print("    destino nao alcancado pelo grafo NUTRJUS no recorte")
        print(
            f"    alternativa por distancia a foz: "
            f"{trecho_manso.distancia_foz_km - trecho_capital.distancia_foz_km:,.1f} km"
        )
    else:
        soma = sum(t.comprimento_km for t in percurso[:-1])
        print(f"    {len(percurso)} trechos, {soma:,.1f} km")
        for trecho in percurso:
            print(
                f"      {trecho.cobacia:>10s} {trecho.rio[:26]:28s} "
                f"{trecho.comprimento_km:7.2f} km  area={trecho.area_montante_km2:12,.1f}"
            )

    print("\n" + "=" * 78)
    print("3. CLASSIFICACAO DE TODO O CADASTRO PELA POSICAO RELATIVA A CAPITAL")
    print("=" * 78)
    caminho = comum.DADOS_TRATADOS / "inventario_barragens_mt.csv"
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        inventario = list(csv.DictReader(arquivo, delimiter=";"))

    contagem: Counter[str] = Counter()
    montante: list[dict[str, Any]] = []
    for registro in inventario:
        rel = otto.relacao(registro.get("codigo_trecho_curso_dagua"), COBACIA_CUIABA)
        contagem[rel.value] += 1
        registro["_relacao"] = rel.value
        if rel in {otto.Relacao.MONTANTE, otto.Relacao.MESMO_TRECHO, otto.Relacao.CONTIDO}:
            montante.append(registro)

    for valor, quantidade in contagem.most_common():
        print(f"  {quantidade:5d}  {valor}")

    print(f"\n  barragens que drenam para a capital (montante/mesmo trecho/contido): {len(montante)}")
    por_municipio = Counter(r.get("municipio") or "(vazio)" for r in montante)
    print("\n  por municipio:")
    for valor, quantidade in por_municipio.most_common():
        print(f"    {quantidade:5d}  {valor}")

    print("\n  as de maior capacidade entre elas:")
    def cap(registro: dict[str, Any]) -> float:
        return numero(registro.get("capacidade_hm3")) or 0.0

    for registro in sorted(montante, key=cap, reverse=True)[:20]:
        print(
            f"    {cap(registro):10,.1f} hm3  {registro.get('municipio','')[:24]:26s} "
            f"{registro.get('nome','')[:38]:40s} otto={registro.get('codigo_trecho_curso_dagua'):>9s} "
            f"rel={registro['_relacao']:12s} DPA={registro.get('dano_potencial_associado') or '-'}"
        )

    print("\n  DPA Alto ou CRI Alto entre as que drenam para a capital:")
    criticas = [
        r
        for r in montante
        if r.get("dano_potencial_associado") == "Alto" or r.get("categoria_risco") == "Alto"
    ]
    print(f"    {len(criticas)} estruturas")
    for registro in sorted(criticas, key=cap, reverse=True):
        print(
            f"    {cap(registro):10,.1f} hm3  {registro.get('municipio','')[:22]:24s} "
            f"{registro.get('nome','')[:36]:38s} CRI={registro.get('categoria_risco') or '-':16s} "
            f"DPA={registro.get('dano_potencial_associado') or '-':6s} rio={registro.get('curso_dagua')}"
        )

    print("\n" + "=" * 78)
    print("4. CONTRAPROVA: O RECORTE POR LATITUDE INCLUIA RAMOS ERRADOS?")
    print("=" * 78)
    for nome_municipio in ["BARRA DO BUGRES", "TANGARA DA SERRA", "NOVA OLIMPIA", "DENISE", "NOSSA SENHORA DO LIVRAMENTO", "POCONE", "ROSARIO OESTE", "JANGADA", "CHAPADA DOS GUIMARAES", "NOBRES"]:
        grupo = [r for r in inventario if sem_acento(r.get("municipio", "")) == nome_municipio]
        if not grupo:
            continue
        relacoes = Counter(r["_relacao"] for r in grupo)
        print(f"  {nome_municipio:30s} {dict(relacoes)}")


if __name__ == "__main__":
    main()
