"""Cruza populacoes vulneraveis e rede de saude com o eixo hidrografico Manso-Cuiaba.

O que este script faz e o que ele deliberadamente nao faz:

FAZ  medir a distancia de cada aldeia indigena, assentamento rural, territorio
     quilombola e estabelecimento de saude ate o eixo de drenagem que liga o
     Aproveitamento Multiplo de Manso a capital e segue rio Cuiaba abaixo, e
     classificar cada elemento em faixas de proximidade.

NAO  FAZ estimativa de populacao atingida. Nao existe mancha de inundacao publica para
     nenhuma barragem de Mato Grosso. Distancia ao talvegue nao e cota de inundacao:
     um ponto a 500 m do rio pode estar 40 m acima dele. A faixa de proximidade serve
     para priorizar onde a vigilancia precisa olhar primeiro, e nao para dizer quem
     sera atingido.

A distancia e geodesica aproximada, calculada em plano local com correcao de latitude,
o que e adequado para as escalas de poucos quilometros usadas aqui.
"""

from __future__ import annotations

import csv
import json
import math
import unicodedata
from typing import Any, Iterable

import comum

FAIXAS_KM = (2.0, 5.0, 10.0)
RAIO_TERRA_KM = 6371.0


def sem_acento(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normalizado if not unicodedata.combining(c)).upper().strip()


def ler_geojson(nome: str) -> dict[str, Any]:
    caminho = comum.DADOS_TRATADOS / nome
    if not caminho.exists():
        raise SystemExit(f"base ausente: {caminho.name}. Rode os coletores 10 a 12 antes.")
    return json.loads(caminho.read_text(encoding="utf-8"))


def ler_csv(nome: str) -> list[dict[str, Any]]:
    caminho = comum.DADOS_TRATADOS / nome
    if not caminho.exists():
        raise SystemExit(f"base ausente: {caminho.name}. Rode os coletores 10 a 12 antes.")
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


# ------------------------------------------------------------------------ geometria


def pontos_de(geometria: dict[str, Any]) -> list[tuple[float, float]]:
    """Achata qualquer geometria GeoJSON numa lista de vertices."""
    tipo = geometria.get("type")
    coordenadas = geometria.get("coordinates")
    if coordenadas is None:
        return []
    if tipo == "Point":
        return [(float(coordenadas[0]), float(coordenadas[1]))]

    pontos: list[tuple[float, float]] = []

    def descer(no: Any) -> None:
        if (
            isinstance(no, (list, tuple))
            and len(no) >= 2
            and all(isinstance(v, (int, float)) for v in no[:2])
        ):
            pontos.append((float(no[0]), float(no[1])))
            return
        if isinstance(no, (list, tuple)):
            for filho in no:
                descer(filho)

    descer(coordenadas)
    return pontos


def centroide(geometria: dict[str, Any]) -> tuple[float, float] | None:
    pontos = pontos_de(geometria)
    if not pontos:
        return None
    return (
        sum(p[0] for p in pontos) / len(pontos),
        sum(p[1] for p in pontos) / len(pontos),
    )


def _plano(lon: float, lat: float, lat_referencia: float) -> tuple[float, float]:
    """Projeta em plano local, em km, com a compressao do meridiano na latitude dada."""
    fator = math.cos(math.radians(lat_referencia))
    return (
        math.radians(lon) * RAIO_TERRA_KM * fator,
        math.radians(lat) * RAIO_TERRA_KM,
    )


def _distancia_ao_segmento(
    ponto: tuple[float, float],
    inicio: tuple[float, float],
    fim: tuple[float, float],
) -> float:
    lat_referencia = ponto[1]
    px, py = _plano(*ponto, lat_referencia)
    ax, ay = _plano(*inicio, lat_referencia)
    bx, by = _plano(*fim, lat_referencia)
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


class Eixo:
    """Eixo de drenagem em segmentos, com filtro grosseiro por caixa envolvente.

    O filtro por longitude e latitude antes do calculo metrico existe porque o eixo tem
    milhares de segmentos e o cruzamento roda sobre milhares de pontos.
    """

    def __init__(self, colecao: dict[str, Any]) -> None:
        self.segmentos: list[tuple[tuple[float, float], tuple[float, float], str]] = []
        for feicao in colecao.get("features", []):
            rotulo = (feicao.get("properties") or {}).get("segmento", "")
            vertices = pontos_de(feicao.get("geometry") or {})
            for inicio, fim in zip(vertices, vertices[1:]):
                self.segmentos.append((inicio, fim, rotulo))
        if not self.segmentos:
            raise SystemExit("eixo hidrografico vazio")

    def distancia(self, ponto: tuple[float, float]) -> tuple[float, str]:
        lon, lat = ponto
        # 1 grau de latitude ~ 111 km; a janela de 0.35 grau cobre com folga a maior
        # faixa analisada, de 10 km, sem descartar candidato valido.
        janela = 0.35
        melhor = (float("inf"), "")
        while True:
            for inicio, fim, rotulo in self.segmentos:
                if (
                    max(inicio[1], fim[1]) < lat - janela
                    or min(inicio[1], fim[1]) > lat + janela
                    or max(inicio[0], fim[0]) < lon - janela
                    or min(inicio[0], fim[0]) > lon + janela
                ):
                    continue
                distancia = _distancia_ao_segmento(ponto, inicio, fim)
                if distancia < melhor[0]:
                    melhor = (distancia, rotulo)
            if melhor[0] < float("inf") or janela > 6:
                return melhor
            janela *= 3


def faixa(distancia_km: float) -> str:
    for limite in FAIXAS_KM:
        if distancia_km <= limite:
            return f"até {limite:.0f} km".replace(".0", "")
    return f"acima de {FAIXAS_KM[-1]:.0f} km"


# -------------------------------------------------------------------------- analise


def avaliar(
    rotulo: str,
    elementos: Iterable[dict[str, Any]],
    eixo: Eixo,
    nome_de: Any,
    municipio_de: Any,
    extra_de: Any = None,
) -> list[dict[str, Any]]:
    resultados: list[dict[str, Any]] = []
    sem_geometria = 0
    for elemento in elementos:
        geometria = elemento.get("geometry") or {}
        ponto = centroide(geometria)
        if ponto is None:
            sem_geometria += 1
            continue
        distancia, segmento = eixo.distancia(ponto)
        registro = {
            "categoria": rotulo,
            "nome": nome_de(elemento),
            "municipio": municipio_de(elemento),
            "longitude": round(ponto[0], 6),
            "latitude": round(ponto[1], 6),
            "distancia_eixo_km": round(distancia, 2),
            "faixa": faixa(distancia),
            "segmento_do_eixo": segmento,
        }
        if extra_de:
            registro.update(extra_de(elemento))
        resultados.append(registro)
    if sem_geometria:
        print(f"  {rotulo}: {sem_geometria} elementos sem geometria utilizavel")
    dentro = [r for r in resultados if r["distancia_eixo_km"] <= FAIXAS_KM[-1]]
    print(
        f"  {rotulo:<34} {len(resultados):>5} elementos"
        f" | {len(dentro):>4} a até {FAIXAS_KM[-1]:.0f} km do eixo"
    )
    return resultados


def inteiro(valor: Any) -> int:
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return 0


def main() -> None:
    comum.preparar_diretorios()
    print("Exposicao de populacoes vulneraveis e da rede de saude ao eixo Manso-Cuiaba")

    eixo = Eixo(ler_geojson("eixo_hidrografico_manso_cuiaba.geojson"))
    print(f"  eixo com {len(eixo.segmentos)} segmentos")

    recorte = json.loads(
        (comum.DADOS_TRATADOS / "cuiaba_municipios_de_interesse.json").read_text(
            encoding="utf-8"
        )
    )
    municipios_do_recorte = {sem_acento(m["nome"]) for m in recorte["municipios"]}

    linhas: list[dict[str, Any]] = []

    terras = ler_geojson("funai_terras_indigenas_mt.geojson")
    # A aldeia guarda apenas o codigo da terra indigena a que pertence. O nome vem da camada
    # de terras, senao o relatorio publicaria o codigo interno da FUNAI como se fosse nome.
    nome_da_terra = {
        (f["properties"] or {}).get("terrai_codigo"): (f["properties"] or {}).get("terrai_nome")
        for f in terras["features"]
    }

    def terra_da_aldeia(feicao: dict[str, Any]) -> dict[str, Any]:
        codigo = (feicao["properties"] or {}).get("cod_ti")
        nome = nome_da_terra.get(codigo)
        return {"detalhe": f"TI {nome}" if nome else "terra indígena não identificada"}

    aldeias = ler_geojson("funai_aldeias_mt.geojson")
    linhas += avaliar(
        "aldeia indígena",
        aldeias["features"],
        eixo,
        lambda f: (f["properties"] or {}).get("nome_aldeia"),
        lambda f: (f["properties"] or {}).get("nommunic"),
        terra_da_aldeia,
    )


    linhas += avaliar(
        "terra indígena",
        terras["features"],
        eixo,
        lambda f: (f["properties"] or {}).get("terrai_nome"),
        lambda f: (f["properties"] or {}).get("municipio_nome"),
        lambda f: {
            "detalhe": (
                f"etnia {(f['properties'] or {}).get('etnia_nome')}; "
                f"fase {(f['properties'] or {}).get('fase_ti')}"
            )
        },
    )

    assentamentos = ler_geojson("incra_assentamentos_mt.geojson")
    linhas += avaliar(
        "assentamento rural",
        assentamentos["features"],
        eixo,
        lambda f: (f["properties"] or {}).get("nome_projeto"),
        lambda f: (f["properties"] or {}).get("municipio"),
        lambda f: {
            "familias": inteiro((f["properties"] or {}).get("num_familias")),
            "detalhe": f"{(f['properties'] or {}).get('num_familias')} famílias",
        },
    )

    quilombolas = ler_geojson("incra_quilombolas_mt.geojson")
    linhas += avaliar(
        "território quilombola",
        quilombolas["features"],
        eixo,
        lambda f: (f["properties"] or {}).get("nome_area")
        or (f["properties"] or {}).get("nome")
        or (f["properties"] or {}).get("comunidade"),
        lambda f: (f["properties"] or {}).get("municipio"),
    )

    saude = ler_geojson("cnes_estabelecimentos_regiao_cuiaba.geojson")
    linhas += avaliar(
        "estabelecimento de saúde",
        saude["features"],
        eixo,
        lambda f: (f["properties"] or {}).get("nome_fantasia"),
        lambda f: (f["properties"] or {}).get("municipio"),
        lambda f: {
            "hospitalar": (f["properties"] or {}).get("atendimento_hospitalar"),
            "detalhe": (
                "atendimento hospitalar"
                if (f["properties"] or {}).get("atendimento_hospitalar") == "Sim"
                else "sem atendimento hospitalar"
            ),
        },
    )

    barragens = ler_csv("barragens_montante_cuiaba.csv")

    colunas = [
        "categoria",
        "nome",
        "municipio",
        "distancia_eixo_km",
        "faixa",
        "segmento_do_eixo",
        "familias",
        "hospitalar",
        "detalhe",
        "longitude",
        "latitude",
    ]
    comum.salvar_csv(
        comum.DADOS_TRATADOS / "exposicao_populacoes_eixo_cuiaba.csv",
        sorted(linhas, key=lambda r: (r["categoria"], r["distancia_eixo_km"])),
        colunas,
    )

    escrever_relatorio(linhas, barragens, municipios_do_recorte, recorte)


def escrever_relatorio(
    linhas: list[dict[str, Any]],
    barragens: list[dict[str, Any]],
    municipios_do_recorte: set[str],
    recorte: dict[str, Any],
) -> None:
    partes: list[str] = []
    a = partes.append

    def por_categoria(categoria: str) -> list[dict[str, Any]]:
        return [l for l in linhas if l["categoria"] == categoria]

    def na_faixa(categoria: str, limite: float) -> list[dict[str, Any]]:
        return [l for l in por_categoria(categoria) if l["distancia_eixo_km"] <= limite]

    a("# Populações vulneráveis e rede de saúde no eixo Manso–Cuiabá")
    a("")
    a(
        "Cruzamento das bases de territórios e populações vulneráveis e da rede de "
        "estabelecimentos de saúde com o eixo de drenagem que liga o Aproveitamento "
        "Múltiplo de Manso à capital e segue pelo rio Cuiabá a jusante. As distâncias "
        "são medidas do elemento até o talvegue."
    )
    a("")
    a(
        "**Limite que acompanha todo este documento.** Distância ao eixo não é cota de "
        "inundação. Um ponto a 500 m do rio pode estar dezenas de metros acima dele, e "
        "um ponto a 8 km pode estar em planície alagável. Não existe mancha de inundação "
        "pública para nenhuma barragem de Mato Grosso, e por isso nenhum número aqui deve "
        "ser lido como população atingida. As faixas servem para ordenar onde a "
        "vigilância olha primeiro, e exigem estudo de ruptura hipotética para virar "
        "estimativa de exposição."
    )
    a("")

    a("## 1. Síntese por categoria")
    a("")
    a("| Categoria | Total na base | Até 2 km | Até 5 km | Até 10 km |")
    a("| --- | --- | --- | --- | --- |")
    for categoria in (
        "aldeia indígena",
        "terra indígena",
        "assentamento rural",
        "território quilombola",
        "estabelecimento de saúde",
    ):
        a(
            f"| {categoria.capitalize()} | {len(por_categoria(categoria))} | "
            f"{len(na_faixa(categoria, 2))} | {len(na_faixa(categoria, 5))} | "
            f"{len(na_faixa(categoria, 10))} |"
        )
    a("")

    familias_10 = sum(l.get("familias") or 0 for l in na_faixa("assentamento rural", 10))
    familias_5 = sum(l.get("familias") or 0 for l in na_faixa("assentamento rural", 5))
    a(
        f"Nos assentamentos rurais a até 10 km do eixo o INCRA registra {familias_10} "
        f"famílias assentadas, das quais {familias_5} em assentamentos a até 5 km. O "
        "número de famílias é o cadastrado na criação do projeto de assentamento, e não "
        "uma contagem populacional atual."
    )
    a("")

    a("## 2. Rede de saúde na faixa de proximidade")
    a("")
    saude = por_categoria("estabelecimento de saúde")
    hospitalares = [l for l in saude if l.get("hospitalar") == "Sim"]
    hospitalares_5 = [l for l in hospitalares if l["distancia_eixo_km"] <= 5]
    total_cnes = len(ler_csv("cnes_estabelecimentos_regiao_cuiaba.csv"))
    a(
        f"O CNES registra {total_cnes} estabelecimentos nos municípios do recorte. "
        f"Destes, {len(saude)} têm coordenada válida e entram na medida de distância; os "
        f"{total_cnes - len(saude)} sem coordenada ficam fora do cruzamento, e essa é uma "
        "lacuna do cadastro, não uma ausência de serviço. Entre os georreferenciados, "
        f"{len(hospitalares)} têm atendimento hospitalar, e {len(hospitalares_5)} deles "
        "estão a até 5 km do eixo. A retaguarda hospitalar da região está, portanto, "
        "majoritariamente instalada na própria planície do rio Cuiabá: a rede que "
        "precisaria responder ao evento é, em boa parte, exposta a ele."
    )
    a("")
    a("| Município | Estabelecimentos | Com atendimento hospitalar | Hospitalares até 5 km do eixo |")
    a("| --- | --- | --- | --- |")
    for municipio in sorted({l["municipio"] for l in saude if l["municipio"]}):
        do_municipio = [l for l in saude if l["municipio"] == municipio]
        hosp = [l for l in do_municipio if l.get("hospitalar") == "Sim"]
        hosp_proximos = [l for l in hosp if l["distancia_eixo_km"] <= 5]
        a(
            f"| {municipio} | {len(do_municipio)} | {len(hosp)} | {len(hosp_proximos)} |"
        )
    a("")

    sem_hospital = sorted(
        {
            l["municipio"]
            for l in saude
            if l["municipio"]
            and not any(
                o.get("hospitalar") == "Sim"
                for o in saude
                if o["municipio"] == l["municipio"]
            )
        }
    )
    if sem_hospital:
        listado = (
            ", ".join(sem_hospital[:-1]) + f" e {sem_hospital[-1]}"
            if len(sem_hospital) > 1
            else sem_hospital[0]
        )
        a(
            "**Achado de capacidade de resposta.** Não há estabelecimento com atendimento "
            f"hospitalar em {listado}. Chapada dos Guimarães, sede do "
            "Aproveitamento Múltiplo de Manso, está entre eles. O município que abriga a "
            "maior estrutura de dano potencial da bacia depende de retaguarda hospitalar "
            "externa, e a retaguarda disponível é a da capital — que é, no cenário de "
            "ruptura, o território atingido a jusante. A dependência é circular e precisa "
            "estar resolvida no plano de resposta antes do evento, com pactuação de "
            "referência para fora do eixo do rio Cuiabá."
        )
        a("")

    a("## 3. Territórios de povos e comunidades tradicionais")
    a("")
    aldeias_10 = na_faixa("aldeia indígena", 10)
    if aldeias_10:
        a(
            f"Há {len(aldeias_10)} aldeias indígenas a até 10 km do eixo analisado. "
            "Listagem no anexo. A presença de aldeia na faixa impõe ao plano de resposta "
            "requisitos que não são os da área urbana: comunicação em língua indígena, "
            "articulação com a Secretaria Especial de Saúde Indígena e com o Distrito "
            "Sanitário Especial Indígena de referência, e abrigo que não separe famílias."
        )
    else:
        a(
            "Nenhuma aldeia indígena cadastrada pela FUNAI está a até 10 km do eixo "
            "analisado. O resultado é do cadastro nacional de aldeias e não exclui a "
            "presença de população indígena urbana na região metropolitana, que o "
            "cadastro de aldeias não capta."
        )
    a("")

    quilombolas_10 = na_faixa("território quilombola", 10)
    a(
        f"Territórios quilombolas titulados ou em processo junto ao INCRA a até 10 km do "
        f"eixo: {len(quilombolas_10)}. A base do INCRA registra apenas 4 territórios em "
        "todo o estado, número que reflete o estágio do processo de titulação e não a "
        "presença de comunidades: a Fundação Cultural Palmares certifica 73 comunidades "
        "quilombolas em Mato Grosso. Para fins de vigilância, a base de certificação é a "
        "que informa presença, e a do INCRA informa apenas onde há território delimitado."
    )
    a("")

    palmares = ler_csv("palmares_quilombolas_mt.csv")
    no_recorte = [
        registro
        for registro in palmares
        if sem_acento(registro.get("MUNICÍPIO") or "") in municipios_do_recorte
    ]
    if no_recorte:
        a(
            f"Comunidades quilombolas certificadas pela Palmares nos {len(recorte['municipios'])} "
            f"municípios do recorte: {len(no_recorte)}."
        )
        a("")
        a("| Município | Comunidade |")
        a("| --- | --- |")
        for registro in sorted(
            no_recorte, key=lambda r: (r.get("MUNICÍPIO") or "", r.get("COMUNIDADE") or "")
        ):
            a(f"| {registro.get('MUNICÍPIO')} | {registro.get('COMUNIDADE')} |")
        a("")

    a("## 4. Ribeirinhos")
    a("")
    a(
        "Não há base oficial de delimitação de população ribeirinha comparável às da "
        "FUNAI e do INCRA. O recorte não pode ser produzido por consulta a cadastro, e "
        "qualquer número apresentado como população ribeirinha exposta seria estimativa "
        "sem fonte. O que este trabalho oferece no lugar é o eixo hidrográfico "
        "delimitado e a faixa de proximidade, sobre os quais a vigilância municipal pode "
        "aplicar o cadastro da Atenção Primária, que identifica domicílio por "
        "microárea e é a única base com resolução suficiente para esse recorte."
    )
    a("")

    a("## 5. Anexo — elementos a até 5 km do eixo")
    a("")
    a("| Categoria | Nome | Município | Distância (km) | Observação |")
    a("| --- | --- | --- | --- | --- |")
    proximos = [
        l
        for l in linhas
        if l["distancia_eixo_km"] <= 5 and l["categoria"] != "estabelecimento de saúde"
    ]
    for linha in sorted(proximos, key=lambda r: r["distancia_eixo_km"]):
        distancia = f"{linha['distancia_eixo_km']:.2f}".replace(".", ",")
        a(
            f"| {linha['categoria']} | {linha['nome']} | {linha['municipio']} | "
            f"{distancia} | {linha.get('detalhe') or ''} |"
        )
    a("")
    a(
        f"Barragens que drenam para a seção de controle da capital: {len(barragens)}. "
        "A relação completa está em `dados/tratados/barragens_montante_cuiaba.csv` e a "
        "análise por hierarquia de ameaça em `relatorios/analise_cuiaba.md`."
    )
    a("")

    caminho = comum.RELATORIOS / "exposicao_populacoes_vulneraveis.md"
    caminho.write_text("\n".join(partes), encoding="utf-8")
    print(f"  gravado {caminho.relative_to(comum.RAIZ)} ({len(partes)} linhas)")


if __name__ == "__main__":
    main()
