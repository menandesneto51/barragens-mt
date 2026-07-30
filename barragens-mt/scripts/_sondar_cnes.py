"""Sondagem: confirma o comportamento de paginacao do endpoint de estabelecimentos.

Nao faz parte do pipeline. Ja se sabe que o filtro exige o codigo municipal de 6
digitos; falta saber o teto de `limit` e se `offset` avanca de fato.
"""

from __future__ import annotations

import warnings

import httpx

warnings.filterwarnings("ignore")

NAVEGADOR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
URL = "https://apidadosabertos.saude.gov.br/cnes/estabelecimentos"
CUIABA = "510340"


def buscar(cli: httpx.Client, **parametros) -> list[dict]:
    resposta = cli.get(URL, params={"codigo_municipio": CUIABA, **parametros})
    resposta.raise_for_status()
    return resposta.json().get("estabelecimentos", [])


def main() -> None:
    with httpx.Client(timeout=180, verify=False, follow_redirects=True, headers=NAVEGADOR) as cli:
        print("Teto de 'limit'")
        for limite in (20, 100, 1000, 5000):
            try:
                itens = buscar(cli, limit=limite)
                print(f"  limit={limite}: {len(itens)} itens")
            except Exception as exc:  # noqa: BLE001
                print(f"  limit={limite}: ERRO {type(exc).__name__} {str(exc)[:140]}")

        print("\nAvanco de 'offset' (limit=20)")
        primeira = buscar(cli, limit=20, offset=0)
        segunda = buscar(cli, limit=20, offset=20)
        cnes_primeira = {i["codigo_cnes"] for i in primeira}
        cnes_segunda = {i["codigo_cnes"] for i in segunda}
        print(f"  pagina 1: {len(primeira)} itens | pagina 2: {len(segunda)} itens")
        print(f"  sobreposicao entre paginas: {len(cnes_primeira & cnes_segunda)}")

        print("\nCoerencia do filtro")
        amostra = buscar(cli, limit=100)
        codigos = {str(i.get("codigo_municipio")) for i in amostra}
        print(f"  codigos de municipio devolvidos: {sorted(codigos)}")


if __name__ == "__main__":
    main()
