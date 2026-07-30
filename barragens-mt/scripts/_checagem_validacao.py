"""Resumo numérico para validação visual dos painéis."""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TRAT = RAIZ / "dados" / "tratados"


def ler(nome: str) -> list[dict]:
    with (TRAT / nome).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def main() -> None:
    idap = ler("idap_estadual_mt.csv")
    pil = ler("piloto_manso_cuiaba.csv")
    print("=== CHECAGEM RÁPIDA PARA VALIDAÇÃO ===")
    print(f"IDAP estadual: {len(idap)}  {dict(Counter(r['nivel'] for r in idap))}")
    print(f"Piloto:        {len(pil)}  {dict(Counter(r['nivel'] for r in pil))}")
    print(f"Alertáveis piloto: {sum(1 for r in pil if r.get('alertavel') == 'sim')}")
    manso = [r for r in pil if (r.get("nome") or "").upper().startswith("UHE MANSO")]
    print(f"Complexo Manso: {len(manso)}")
    for r in sorted(manso, key=lambda x: -int(x["idap"])):
        print(
            f"  IDAP {r['idap']:>2} {r['nivel']:<7} A{r['pontos_a']} | {r['nome'][:55]}"
        )
    print("Top 5 piloto:")
    for r in sorted(pil, key=lambda x: -int(x["idap"]))[:5]:
        print(
            f"  IDAP {r['idap']:>2} {r['nivel']:<7} | {r['municipio_sede'][:22]:<22} | {r['nome'][:40]}"
        )
    am = [r for r in idap if r["nivel"] == "Amarelo"]
    print(f"Amarelo estadual: {len(am)}")
    for r in am:
        print(
            f"  {r['id_snisb']} {r['municipio_sede'][:20]:<20} "
            f"IDAP {r['idap']} A{r['pontos_a']}B{r['pontos_b']}C{r['pontos_c']}D{r['pontos_d']} | "
            f"{r['nome'][:35]}"
        )
    print()
    print("Painéis:")
    print(f"  {(RAIZ / 'painel' / 'index.html').as_uri()}")
    print(f"  {(RAIZ / 'painel' / 'piloto_manso_cuiaba.html').as_uri()}")
    print(f"  {(RAIZ / 'painel' / 'hidro.html').as_uri()}")
    print(f"  {(RAIZ / 'painel' / 'alertas.html').as_uri()}")


if __name__ == "__main__":
    main()
