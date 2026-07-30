"""Baixa a base territorial de Mato Grosso no IBGE.

Serve de camada de contexto para o monitoramento: permite validar o municipio
declarado de cada barragem, agregar indicadores por municipio e desenhar mapas.
"""

from __future__ import annotations

import comum

URL_MUNICIPIOS = (
    f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{comum.UF_CODIGO_IBGE}/municipios"
)
URL_MALHA = (
    f"https://servicodados.ibge.gov.br/api/v3/malhas/estados/{comum.UF_CODIGO_IBGE}"
    "?formato=application/vnd.geo+json&intrarregiao=municipio&qualidade=maxima"
)
# Versao generalizada da mesma malha: 205 KB contra 11 MB, o que viabiliza embutir os
# limites municipais no HTML do painel sem tornar o arquivo pesado demais.
URL_MALHA_SIMPLES = (
    f"https://servicodados.ibge.gov.br/api/v3/malhas/estados/{comum.UF_CODIGO_IBGE}"
    "?formato=application/vnd.geo+json&intrarregiao=municipio&qualidade=minima"
)
# Contorno das UFs do pais: alimenta o mapa de localizacao (encarte) das figuras.
URL_MALHA_BRASIL = (
    "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
    "?formato=application/vnd.geo+json&intrarregiao=UF&qualidade=minima"
)


def main() -> None:
    comum.preparar_diretorios()
    print("Baixando base territorial de Mato Grosso (IBGE)")

    with comum.cliente(verificar_tls=False) as cli:
        municipios = comum.requisitar_json(cli, URL_MUNICIPIOS)
        malha = comum.requisitar_json(cli, URL_MALHA)
        malha_simples = comum.requisitar_json(cli, URL_MALHA_SIMPLES)
        malha_brasil = comum.requisitar_json(cli, URL_MALHA_BRASIL)

    def texto(dicionario: Any, *chaves: str) -> str | None:
        """Navega por um caminho de chaves tolerando niveis ausentes ou nulos."""
        atual = dicionario
        for chave in chaves:
            if not isinstance(atual, dict):
                return None
            atual = atual.get(chave)
        return atual if isinstance(atual, str) else None

    registros = [
        {
            "codigo_ibge": m["id"],
            "municipio": m["nome"],
            "microrregiao": texto(m, "microrregiao", "nome"),
            "mesorregiao": texto(m, "microrregiao", "mesorregiao", "nome"),
            "regiao_imediata": texto(m, "regiao-imediata", "nome"),
            "regiao_intermediaria": texto(m, "regiao-imediata", "regiao-intermediaria", "nome"),
        }
        for m in municipios
    ]
    registros.sort(key=lambda r: r["municipio"])

    comum.salvar_csv(
        comum.DADOS_TRATADOS / "ibge_municipios_mt.csv",
        registros,
        ["codigo_ibge", "municipio", "microrregiao", "mesorregiao", "regiao_imediata", "regiao_intermediaria"],
    )
    comum.salvar_json(comum.DADOS_TRATADOS / "ibge_malha_municipios_mt.geojson", malha)
    comum.salvar_json(
        comum.DADOS_TRATADOS / "ibge_malha_municipios_mt_simplificada.geojson", malha_simples
    )
    comum.salvar_json(comum.DADOS_TRATADOS / "ibge_malha_ufs_brasil.geojson", malha_brasil)
    print(
        f"\n{len(registros)} municipios, {len(malha.get('features', []))} poligonos municipais "
        f"e {len(malha_brasil.get('features', []))} UFs"
    )


if __name__ == "__main__":
    main()
