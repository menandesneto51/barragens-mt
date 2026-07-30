"""Coleta a rede de estabelecimentos de saude do CNES nos municipios de interesse.

O recorte territorial nao e escolhido aqui: vem de `cuiaba_municipios_de_interesse.json`,
publicado pelo script 12 a partir da topologia de drenagem. Assim a capacidade de resposta
e medida exatamente nos municipios que a analise de exposicao identificou.

Duas armadilhas do endpoint, descobertas por sondagem e tratadas no codigo:
  - `codigo_municipio` exige o codigo do IBGE de 6 digitos, sem o verificador. O codigo
    de 7 digitos devolve lista vazia com HTTP 200, sem qualquer erro;
  - o parametro `limit` e ignorado acima de 20, entao a paginacao por `offset` e
    obrigatoria mesmo quando se pede tudo de uma vez.

O endpoint nao expoe numero de leitos. O que se extrai daqui e a existencia e a
localizacao dos servicos — atendimento hospitalar, centro cirurgico, centro obstetrico
e centro neonatal —, que e o suficiente para dizer onde ha retaguarda e onde nao ha.
"""

from __future__ import annotations

import json
from typing import Any, Iterator

import comum

URL = "https://apidadosabertos.saude.gov.br/cnes/estabelecimentos"
NAVEGADOR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
POR_PAGINA = 20
TETO_DE_PAGINAS = 400

COLUNAS = [
    "codigo_cnes",
    "nome_fantasia",
    "nome_razao_social",
    "codigo_municipio",
    "municipio",
    "no_eixo_montante",
    "no_eixo_jusante",
    "bairro_estabelecimento",
    "endereco_estabelecimento",
    "descricao_esfera_administrativa",
    "descricao_nivel_hierarquia",
    "descricao_turno_atendimento",
    "codigo_tipo_unidade",
    "tipo_gestao",
    "atendimento_hospitalar",
    "atendimento_ambulatorial",
    "ambulatorial_sus",
    "centro_cirurgico",
    "centro_obstetrico",
    "centro_neonatal",
    "servico_apoio",
    "latitude",
    "longitude",
    "numero_telefone_estabelecimento",
    "data_atualizacao",
]

SERVICOS = {
    "atendimento_hospitalar": "estabelecimento_possui_atendimento_hospitalar",
    "atendimento_ambulatorial": "estabelecimento_possui_atendimento_ambulatorial",
    "ambulatorial_sus": "estabelecimento_faz_atendimento_ambulatorial_sus",
    "centro_cirurgico": "estabelecimento_possui_centro_cirurgico",
    "centro_obstetrico": "estabelecimento_possui_centro_obstetrico",
    "centro_neonatal": "estabelecimento_possui_centro_neonatal",
    "servico_apoio": "estabelecimento_possui_servico_apoio",
}


def ler_recorte() -> dict[str, Any]:
    caminho = comum.DADOS_TRATADOS / "cuiaba_municipios_de_interesse.json"
    if not caminho.exists():
        raise SystemExit(
            "recorte territorial ausente: execute antes 'python scripts/12_analise_cuiaba.py'"
        )
    return json.loads(caminho.read_text(encoding="utf-8"))


def paginar(cli, codigo_cnes: str) -> Iterator[dict[str, Any]]:
    vistos: set[Any] = set()
    for pagina in range(TETO_DE_PAGINAS):
        dados = comum.requisitar_json(
            cli,
            URL,
            {
                "codigo_municipio": codigo_cnes,
                "limit": POR_PAGINA,
                "offset": pagina * POR_PAGINA,
            },
        )
        lote = dados.get("estabelecimentos") or []
        if not lote:
            return
        novos = 0
        for item in lote:
            chave = item.get("codigo_cnes")
            if chave in vistos:
                continue
            vistos.add(chave)
            novos += 1
            yield item
        # Sem avanco real, `offset` deixou de paginar e insistir vira laco infinito.
        if novos == 0 or len(lote) < POR_PAGINA:
            return
    print(f"    atencao: teto de {TETO_DE_PAGINAS} paginas atingido em {codigo_cnes}")


def normalizar(item: dict[str, Any], municipio: dict[str, Any]) -> dict[str, Any]:
    def sim_nao(chave: str) -> str | None:
        valor = item.get(chave)
        if valor in (None, ""):
            return None
        if isinstance(valor, bool):
            return "Sim" if valor else "Não"
        texto = str(valor).strip().upper()
        return {"1": "Sim", "0": "Não", "S": "Sim", "N": "Não"}.get(texto, str(valor))

    registro: dict[str, Any] = {
        "codigo_cnes": item.get("codigo_cnes"),
        "nome_fantasia": item.get("nome_fantasia"),
        "nome_razao_social": item.get("nome_razao_social"),
        "codigo_municipio": item.get("codigo_municipio"),
        "municipio": municipio["nome"],
        "no_eixo_montante": "Sim" if municipio["no_eixo_montante"] else "Não",
        "no_eixo_jusante": "Sim" if municipio["no_eixo_jusante"] else "Não",
        "bairro_estabelecimento": item.get("bairro_estabelecimento"),
        "endereco_estabelecimento": item.get("endereco_estabelecimento"),
        "descricao_esfera_administrativa": item.get("descricao_esfera_administrativa"),
        "descricao_nivel_hierarquia": item.get("descricao_nivel_hierarquia"),
        "descricao_turno_atendimento": item.get("descricao_turno_atendimento"),
        "codigo_tipo_unidade": item.get("codigo_tipo_unidade"),
        "tipo_gestao": item.get("tipo_gestao"),
        "latitude": item.get("latitude_estabelecimento_decimo_grau"),
        "longitude": item.get("longitude_estabelecimento_decimo_grau"),
        "numero_telefone_estabelecimento": item.get("numero_telefone_estabelecimento"),
        "data_atualizacao": item.get("data_atualizacao"),
    }
    for destino, origem in SERVICOS.items():
        registro[destino] = sim_nao(origem)
    return registro


def main() -> None:
    comum.preparar_diretorios()
    recorte = ler_recorte()
    print("Coletando rede de saude do CNES nos municipios de interesse")
    print(f"  secao de controle da analise: {recorte['secao_de_controle']}")

    registros: list[dict[str, Any]] = []
    divergentes = 0
    with comum.cliente(verificar_tls=False) as cli:
        cli.headers.update(NAVEGADOR)
        for municipio in recorte["municipios"]:
            codigo = municipio.get("codigo_cnes")
            if not codigo:
                print(f"  {municipio['nome']}: sem codigo, ignorado")
                continue
            do_municipio = [
                normalizar(item, municipio) for item in paginar(cli, codigo)
            ]
            fora = [r for r in do_municipio if str(r["codigo_municipio"]) != codigo]
            divergentes += len(fora)
            registros.extend(do_municipio)
            hospitalares = sum(
                1 for r in do_municipio if r["atendimento_hospitalar"] == "Sim"
            )
            print(
                f"  {municipio['nome']:<28} {len(do_municipio):>5} estabelecimentos"
                f" | {hospitalares:>3} com atendimento hospitalar"
            )

    if divergentes:
        print(f"  atencao: {divergentes} registros com municipio divergente do filtro")

    comum.salvar_csv(
        comum.DADOS_TRATADOS / "cnes_estabelecimentos_regiao_cuiaba.csv",
        registros,
        COLUNAS,
    )
    georreferenciados = [
        r for r in registros if comum.dentro_do_bbox(r.get("longitude"), r.get("latitude"))
    ]
    comum.salvar_geojson(
        comum.DADOS_TRATADOS / "cnes_estabelecimentos_regiao_cuiaba.geojson",
        georreferenciados,
        "longitude",
        "latitude",
    )

    print("\nResumo da capacidade instalada")
    print(f"  estabelecimentos no recorte: {len(registros)}")
    print(f"  com coordenada valida em MT: {len(georreferenciados)}")
    for rotulo in ("atendimento_hospitalar", "centro_cirurgico", "centro_obstetrico", "centro_neonatal"):
        total = sum(1 for r in registros if r[rotulo] == "Sim")
        print(f"  {rotulo}: {total}")

    hospitalar_por_municipio = {}
    for registro in registros:
        if registro["atendimento_hospitalar"] == "Sim":
            chave = registro["municipio"]
            hospitalar_por_municipio[chave] = hospitalar_por_municipio.get(chave, 0) + 1
    sem_retaguarda = [
        m["nome"]
        for m in recorte["municipios"]
        if hospitalar_por_municipio.get(m["nome"], 0) == 0
    ]
    if sem_retaguarda:
        print(f"  municipios sem atendimento hospitalar proprio: {sem_retaguarda}")


if __name__ == "__main__":
    main()
