"""Topologia de drenagem sobre a codificacao de Otto Pfafstetter.

Por que este modulo existe. A pergunta sanitaria correta nao e "quais barragens
ficam dentro do municipio de Cuiaba", e sim "quais barragens drenam para Cuiaba".
As duas respostas sao muito diferentes: filtrar por limite municipal esconde as
estruturas de maior dano potencial, que estao a montante, em outros municipios.
A codificacao de Otto Pfafstetter, adotada pela ANA na Base Hidrografica
Ottocodificada e presente no cadastro do SNISB no campo do trecho de curso
d'agua, permite decidir montante e jusante por topologia da rede.

Regra de leitura do codigo. Em cada nivel, a bacia e dividida em nove partes com
os digitos 1 a 9, numerados da foz para a nascente. Os digitos impares
(1, 3, 5, 7, 9) sao as interbacias da calha principal, e os pares (2, 4, 6, 8)
sao as quatro maiores bacias tributarias. A agua de uma parte de digito maior
escoa pela calha principal atravessando as interbacias de digito menor. Logo:

    A esta a montante de B quando, no primeiro digito em que os codigos diferem,
    o digito de A e maior que o de B E o digito de B e impar.

A exigencia de que o digito de B seja impar e o ponto delicado. Se B estiver numa
bacia tributaria (digito par), a agua de A nao passa por B: as duas ficam em
ramos distintos, ainda que na mesma bacia e ainda que A esteja "mais acima" no
mapa. Foi exatamente esse tipo de confusao que levou a incluir, num primeiro
recorte por latitude, barragens de Barra do Bugres e Tangara da Serra, que estao
na bacia do Paraguai mas nao drenam para Cuiaba.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Relacao(Enum):
    """Posicao relativa de dois trechos na rede de drenagem."""

    MONTANTE = "montante"
    JUSANTE = "jusante"
    MESMO_TRECHO = "mesmo trecho"
    CONTIDO = "contido"
    CONTEM = "contem"
    OUTRO_RAMO = "outro ramo"
    INDETERMINADO = "indeterminado"


def normalizar(codigo: str | int | None) -> str:
    """Devolve o codigo como cadeia de digitos, ou vazio se nao for utilizavel."""
    if codigo is None:
        return ""
    texto = str(codigo).strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    return texto if texto.isdigit() else ""


def relacao(codigo_a: str | int | None, codigo_b: str | int | None) -> Relacao:
    """Posicao de A em relacao a B.

    MONTANTE significa que a agua de A escoa passando por B — ou seja, um
    rompimento em A alcanca B. CONTIDO significa que A esta dentro da bacia
    representada por B num nivel mais grosseiro de codificacao, caso em que o
    codigo nao resolve a posicao relativa e e preciso outro critereo.
    """
    a, b = normalizar(codigo_a), normalizar(codigo_b)
    if not a or not b:
        return Relacao.INDETERMINADO
    if a == b:
        return Relacao.MESMO_TRECHO

    for digito_a, digito_b in zip(a, b):
        if digito_a == digito_b:
            continue
        menor = min(digito_a, digito_b)
        # A agua do lado de digito maior so passa pelo lado de digito menor se este
        # for interbacia de calha principal (impar).
        if int(menor) % 2 == 0:
            return Relacao.OUTRO_RAMO
        return Relacao.MONTANTE if digito_a > digito_b else Relacao.JUSANTE

    # Um codigo e prefixo do outro: mesma calha, resolucoes diferentes.
    return Relacao.CONTIDO if len(a) > len(b) else Relacao.CONTEM


def comprimento_prefixo_comum(
    codigo_a: str | int | None, codigo_b: str | int | None
) -> int:
    """Quantos dígitos iniciais coincidem antes da primeira divergência."""
    a, b = normalizar(codigo_a), normalizar(codigo_b)
    n = 0
    for digito_a, digito_b in zip(a, b):
        if digito_a != digito_b:
            break
        n += 1
    return n


def drena_para(
    codigo_a: str | int | None,
    codigo_b: str | int | None,
    *,
    min_prefixo: int = 0,
) -> bool:
    """Verdadeiro quando um rompimento em A propaga onda que alcanca B.

    `min_prefixo` exige prefixo Otto comum mínimo antes de aceitar MONTANTE.
    Sem isso, bacias irmãs sob o mesmo nível grosseiro (ex.: 896… vs 895…)
    podem ser classificadas como montante/jusante só porque o dígito divergente
    da seção é ímpar — falso positivo típico (Alto Taquari vs eixo Cuiabá).
    """
    r = relacao(codigo_a, codigo_b)
    if r == Relacao.MESMO_TRECHO:
        return True
    if r != Relacao.MONTANTE:
        return False
    if min_prefixo <= 0:
        return True
    return comprimento_prefixo_comum(codigo_a, codigo_b) >= min_prefixo


@dataclass(frozen=True)
class Trecho:
    """Trecho de drenagem da BHO, com o minimo necessario para medir distancias."""

    cotrecho: int
    cobacia: str
    rio: str
    area_montante_km2: float
    comprimento_km: float
    distancia_foz_km: float
    trecho_jusante: int


def indexar_trechos(feicoes: list[dict]) -> dict[int, Trecho]:
    """Constroi o indice de trechos a partir do GeoJSON da BHO da ANA."""
    indice: dict[int, Trecho] = {}
    for feicao in feicoes:
        p = feicao.get("properties") or {}
        try:
            cotrecho = int(p.get("COTRECHO"))
        except (TypeError, ValueError):
            continue
        indice[cotrecho] = Trecho(
            cotrecho=cotrecho,
            cobacia=normalizar(p.get("COBACIA")),
            rio=(p.get("NORIOCOMP") or p.get("NOORIGINAL") or "").strip(),
            area_montante_km2=float(p.get("NUAREAMONT") or 0),
            comprimento_km=float(p.get("NUCOMPTREC") or 0),
            distancia_foz_km=float(p.get("NUDISTBACT") or 0),
            trecho_jusante=int(p.get("NUTRJUS") or 0),
        )
    return indice


def caminho_jusante(
    indice: dict[int, Trecho],
    origem: int,
    destino: int,
    limite: int = 5000,
) -> list[Trecho] | None:
    """Percorre a rede de jusante da origem ate o destino.

    Devolve a sequencia de trechos, ou None se o destino nao for alcancado — o que
    indica que as duas posicoes estao em ramos distintos da rede.
    """
    atual = indice.get(origem)
    percurso: list[Trecho] = []
    visitados: set[int] = set()
    while atual is not None and len(percurso) < limite:
        percurso.append(atual)
        if atual.cotrecho == destino:
            return percurso
        if atual.cotrecho in visitados:
            return None
        visitados.add(atual.cotrecho)
        atual = indice.get(atual.trecho_jusante)
    return None


def distancia_talvegue_km(
    indice: dict[int, Trecho],
    origem: int,
    destino: int,
) -> float | None:
    """Distancia ao longo do rio entre dois trechos, somando os comprimentos.

    E distancia geografica pela calha, nao tempo de chegada de onda: a celeridade
    de uma onda de ruptura depende de vazao, geometria do vale e rugosidade, e so
    um estudo de dam break dimensiona isso.
    """
    percurso = caminho_jusante(indice, origem, destino)
    if percurso is None:
        return None
    # O comprimento do trecho de destino nao entra: a onda chega ao seu inicio.
    return sum(t.comprimento_km for t in percurso[:-1])
