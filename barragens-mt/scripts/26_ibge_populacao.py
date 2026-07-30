"""População municipal IBGE (Censo / estimativas) para MT.

Saída: dados/tratados/ibge_populacao_municipios_mt.csv
"""

from __future__ import annotations

from typing import Any

import comum

# Censo 2022 — população residente (variável 93) por município de MT (N3[51]).
URL_CENSO_2022 = (
    "https://servicodados.ibge.gov.br/api/v3/agregados/4714/periodos/2022/"
    f"variaveis/93?localidades=N6[N3[{comum.UF_CODIGO_IBGE}]]"
)
# Estimativas anuais (fallback) — variável 9324.
URL_ESTIMATIVA = (
    "https://servicodados.ibge.gov.br/api/v3/agregados/6579/periodos/-6/"
    f"variaveis/9324?localidades=N6[N3[{comum.UF_CODIGO_IBGE}]]"
)


def _extrair(payload: list[dict[str, Any]], fonte: str) -> list[dict[str, Any]]:
    saida: list[dict[str, Any]] = []
    for bloco in payload:
        resultados = bloco.get("resultados") or []
        for res in resultados:
            series = res.get("series") or []
            for serie in series:
                loc = serie.get("localidade") or {}
                cod = str(loc.get("id") or "")
                nome = (loc.get("nome") or "").split(" - ")[0].strip()
                valores = serie.get("serie") or {}
                # último período disponível
                periodos = sorted(valores.keys())
                if not periodos:
                    continue
                periodo = periodos[-1]
                bruto = valores.get(periodo)
                try:
                    pop = int(float(str(bruto).replace(",", ".")))
                except (TypeError, ValueError):
                    continue
                if pop <= 0:
                    continue
                saida.append(
                    {
                        "codigo_ibge": cod,
                        "municipio": nome,
                        "populacao": pop,
                        "ano_referencia": periodo,
                        "fonte": fonte,
                        "area_km2": "",
                        "densidade_hab_km2": "",
                    }
                )
    return saida


def enriquecer_area(registros: list[dict[str, Any]]) -> None:
    """Completa nome a partir do cadastro territorial, se necessário."""
    import csv

    territorios = comum.DADOS_TRATADOS / "ibge_municipios_mt.csv"
    nome_por_cod: dict[str, str] = {}
    if territorios.exists():
        with territorios.open(encoding="utf-8-sig", newline="") as arquivo:
            for r in csv.DictReader(arquivo, delimiter=";"):
                nome_por_cod[str(r.get("codigo_ibge") or "")] = r.get("municipio") or ""
    for r in registros:
        cod = r["codigo_ibge"]
        if not r.get("municipio") and cod in nome_por_cod:
            r["municipio"] = nome_por_cod[cod]


def main() -> None:
    comum.preparar_diretorios()
    print("População municipal IBGE — Mato Grosso")
    registros: list[dict[str, Any]] = []
    with comum.cliente(verificar_tls=False) as cli:
        try:
            payload = comum.requisitar_json(cli, URL_CENSO_2022)
            registros = _extrair(payload if isinstance(payload, list) else [payload], "censo_2022")
            print(f"  Censo 2022: {len(registros)} municípios")
        except Exception as exc:
            print(f"  Censo 2022 falhou ({exc}); tentando estimativas…")
        if len(registros) < 50:
            payload = comum.requisitar_json(cli, URL_ESTIMATIVA)
            registros = _extrair(
                payload if isinstance(payload, list) else [payload], "estimativa_ibge"
            )
            print(f"  Estimativas: {len(registros)} municípios")

    if not registros:
        raise SystemExit("não foi possível obter população municipal do IBGE")

    enriquecer_area(registros)
    registros.sort(key=lambda r: r["municipio"])
    comum.salvar_csv(
        comum.DADOS_TRATADOS / "ibge_populacao_municipios_mt.csv",
        registros,
        [
            "codigo_ibge",
            "municipio",
            "populacao",
            "ano_referencia",
            "fonte",
            "area_km2",
            "densidade_hab_km2",
        ],
    )
    print(f"  gravado dados/tratados/ibge_populacao_municipios_mt.csv ({len(registros)})")


if __name__ == "__main__":
    main()
