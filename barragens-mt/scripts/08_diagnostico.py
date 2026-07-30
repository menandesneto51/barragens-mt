"""Gera o relatorio de diagnostico do inventario de barragens de Mato Grosso.

Escreve relatorios/diagnostico_barragens_mt.md com o retrato atual do cadastro: perfil
do inventario, classificacao de risco, lacunas de conformidade com a PNSB, situacao das
barragens de mineracao e problemas de qualidade do dado que precisam ser tratados na
origem pelos orgaos fiscalizadores.
"""

from __future__ import annotations

import csv
import datetime as dt
from collections import Counter
from typing import Any, Iterable

import comum

RELATORIOS = comum.RELATORIOS

ORDEM_RISCO = ["Alto", "Médio", "Baixo", "Não Classificado", "Não se Aplica"]
SIGLA_ORGAO = {
    "MT - Secretaria de Estado do Meio Ambiente - SEMA": "SEMA-MT",
    "Agência Nacional de Mineração - ANM": "ANM",
    "Agência Nacional de Energia Elétrica - ANEEL": "ANEEL",
    "Agência Nacional de Águas e Saneamento Básico - ANA": "ANA",
}


def ler(nome: str) -> list[dict[str, Any]]:
    caminho = comum.DADOS_TRATADOS / nome
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def numero(valor: Any) -> float | None:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def tabela(cabecalho: list[str], linhas: Iterable[list[Any]], alinhar_direita: set[int] | None = None) -> str:
    alinhar_direita = alinhar_direita or set()
    separador = [
        "---:" if indice in alinhar_direita else "---" for indice in range(len(cabecalho))
    ]
    corpo = "\n".join("| " + " | ".join(str(c) for c in linha) + " |" for linha in linhas)
    return (
        "| " + " | ".join(cabecalho) + " |\n"
        "| " + " | ".join(separador) + " |\n" + corpo
    )


def percentual(parte: int, total: int) -> str:
    return f"{100 * parte / total:.1f}%" if total else "—"


def numero_br(valor: float, casas: int = 0) -> str:
    """Formata no padrao pt-BR: ponto para milhar, virgula para decimal."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def main() -> None:
    barragens = ler("inventario_barragens_mt.csv")
    mineracao = ler("sigbm_barragens_mt.csv")
    total = len(barragens)

    linhas: list[str] = []
    ad = linhas.append

    ad("# Diagnóstico do inventário de barragens — Mato Grosso")
    ad("")
    ad(f"Extração dos dados: **{dt.date.today().strftime('%d/%m/%Y')}**")
    ad("")
    ad(
        "Consolidação do SNISB (ANA), do SIGBM (ANM) e da base territorial do IBGE. "
        "Cobre todas as barragens cadastradas no estado, independentemente do órgão "
        "fiscalizador e de estarem ou não sujeitas à Lei Federal 12.334/2010."
    )
    ad("")

    # ------------------------------------------------------------------ panorama
    ad("## 1. Panorama")
    ad("")
    municipios_com_barragem = len({b["municipio"] for b in barragens if b.get("municipio")})
    criticos = {
        "Barragens cadastradas": total,
        "Categoria de Risco alta": sum(1 for b in barragens if b["categoria_risco"] == "Alto"),
        "Dano Potencial Associado alto": sum(
            1 for b in barragens if b["dano_potencial_associado"] == "Alto"
        ),
        "Classe A (maior exigência legal)": sum(1 for b in barragens if b.get("classe_cnrh") == "A"),
        "Reguladas pela PNSB": sum(1 for b in barragens if b["regulada_pelo_pnsb"] == "Sim"),
        "Com Plano de Segurança": sum(
            1 for b in barragens if b["possui_plano_de_seguranca"] == "Sim"
        ),
        "Com Plano de Ação de Emergência": sum(1 for b in barragens if b["possui_pae"] == "Sim"),
    }
    ad(
        tabela(
            ["Indicador", "Quantidade", "% do total"],
            [[rotulo, valor, percentual(valor, total)] for rotulo, valor in criticos.items()],
            {1, 2},
        )
    )
    ad("")

    volumes = [numero(b["capacidade_hm3"]) for b in barragens]
    volumes = [v for v in volumes if v is not None]
    alturas = [numero(b["altura_m"]) for b in barragens]
    alturas = [a for a in alturas if a is not None]
    ad(
        f"As barragens estão distribuídas em **{municipios_com_barragem} dos 141 municípios** "
        f"({percentual(municipios_com_barragem, 141)} do estado). O volume acumulado declarado "
        f"soma **{numero_br(sum(volumes))} hm³** ({len(volumes)} barragens com o campo "
        f"preenchido). A altura mediana é de **{numero_br(sorted(alturas)[len(alturas) // 2], 1)} m** "
        f"e a maior barragem tem **{numero_br(max(alturas))} m**."
    )
    ad("")

    # ------------------------------------------------- responsabilidade e finalidade
    ad("## 2. Quem fiscaliza e para que servem")
    ad("")
    por_orgao = Counter(b["orgao_fiscalizador"] for b in barragens)
    ad(
        tabela(
            ["Órgão fiscalizador", "Barragens", "% do total", "CRI alta", "DPA alto"],
            [
                [
                    SIGLA_ORGAO.get(orgao, orgao),
                    quantidade,
                    percentual(quantidade, total),
                    sum(
                        1
                        for b in barragens
                        if b["orgao_fiscalizador"] == orgao and b["categoria_risco"] == "Alto"
                    ),
                    sum(
                        1
                        for b in barragens
                        if b["orgao_fiscalizador"] == orgao
                        and b["dano_potencial_associado"] == "Alto"
                    ),
                ]
                for orgao, quantidade in por_orgao.most_common()
            ],
            {1, 2, 3, 4},
        )
    )
    ad("")
    por_uso = Counter(b["uso_principal"] or "Não informado" for b in barragens)
    ad(
        tabela(
            ["Uso principal", "Barragens", "% do total"],
            [
                [uso, quantidade, percentual(quantidade, total)]
                for uso, quantidade in por_uso.most_common(10)
            ],
            {1, 2},
        )
    )
    ad("")

    # ---------------------------------------------------------------- classificação
    ad("## 3. Classificação de risco")
    ad("")
    cri = Counter(b["categoria_risco"] or "Não informado" for b in barragens)
    dpa = Counter(b["dano_potencial_associado"] or "Não informado" for b in barragens)
    ad(
        tabela(
            ["Nível", "Categoria de Risco (CRI)", "Dano Potencial Associado (DPA)"],
            [[nivel, cri.get(nivel, 0), dpa.get(nivel, 0)] for nivel in ORDEM_RISCO],
            {1, 2},
        )
    )
    ad("")
    ad(
        "A **Categoria de Risco** mede a condição da estrutura e do seu gerenciamento; "
        "o **Dano Potencial Associado** mede a consequência de um rompimento. O cruzamento "
        "define a classe da barragem pela Resolução CNRH nº 143/2012, e é a classe que "
        "determina quais instrumentos de segurança são exigidos."
    )
    ad("")
    classes = Counter(b.get("classe_cnrh") or "Sem classificação" for b in barragens)
    ad(
        tabela(
            ["Classe CNRH", "Barragens", "% do total"],
            [
                [classe, classes[classe], percentual(classes[classe], total)]
                for classe in ["A", "B", "C", "D", "E", "Sem classificação"]
                if classes.get(classe)
            ],
            {1, 2},
        )
    )
    ad("")

    # ------------------------------------------------------------------ prioridade
    fila = sorted(
        (b for b in barragens if numero(b.get("prioridade_fiscalizacao"))),
        key=lambda b: (
            -(numero(b["prioridade_fiscalizacao"]) or 0),
            -(numero(b["capacidade_hm3"]) or 0),
        ),
    )
    ad("### Fila de priorização — classe A")
    ad("")
    classe_a = [b for b in fila if b.get("classe_cnrh") == "A"]
    if classe_a:
        ad(
            tabela(
                [
                    "Barragem",
                    "Município",
                    "Fiscalizador",
                    "CRI",
                    "DPA",
                    "Altura (m)",
                    "Capac. (hm³)",
                    "Plano seg.",
                    "PAE",
                ],
                [
                    [
                        b["nome"] or "—",
                        b["municipio"] or "—",
                        SIGLA_ORGAO.get(b["orgao_fiscalizador"], "—"),
                        b["categoria_risco"],
                        b["dano_potencial_associado"],
                        numero_br(numero(b["altura_m"]), 1) if numero(b["altura_m"]) else "—",
                        numero_br(numero(b["capacidade_hm3"]), 3)
                        if numero(b["capacidade_hm3"])
                        else "—",
                        b["possui_plano_de_seguranca"] or "—",
                        b["possui_pae"] or "—",
                    ]
                    for b in classe_a[:20]
                ],
                {5, 6},
            )
        )
        ad("")
        sem_plano = sum(1 for b in classe_a if b["possui_plano_de_seguranca"] != "Sim")
        sem_pae = sum(1 for b in classe_a if b["possui_pae"] != "Sim")
        ad(
            f"Das {len(classe_a)} barragens de classe A, **{sem_plano} não registram Plano de "
            f"Segurança** e **{sem_pae} não registram PAE** no SNISB — são as pendências de "
            "maior consequência do inventário."
        )
        ad("")

    # ---------------------------------------------------------------- conformidade
    ad("## 4. Conformidade com os instrumentos da PNSB")
    ad("")
    reguladas = [b for b in barragens if b["regulada_pelo_pnsb"] == "Sim"]
    instrumentos = [
        ("Plano de Segurança da Barragem", "possui_plano_de_seguranca"),
        ("Plano de Ação de Emergência (PAE)", "possui_pae"),
        ("Revisão periódica de segurança", "possui_revisao_periodica"),
    ]
    ad(
        tabela(
            ["Instrumento", "Todas as barragens", "% ", "Reguladas pela PNSB", "% "],
            [
                [
                    rotulo,
                    sum(1 for b in barragens if b[campo] == "Sim"),
                    percentual(sum(1 for b in barragens if b[campo] == "Sim"), total),
                    sum(1 for b in reguladas if b[campo] == "Sim"),
                    percentual(sum(1 for b in reguladas if b[campo] == "Sim"), len(reguladas)),
                ]
                for rotulo, campo in instrumentos
            ],
            {1, 2, 3, 4},
        )
    )
    ad("")
    com_inspecao = sum(1 for b in barragens if b["data_ultima_inspecao"])
    ad(
        f"Apenas **{com_inspecao} barragens ({percentual(com_inspecao, total)})** têm data de "
        f"inspeção registrada, e **{sum(1 for b in barragens if b.get('data_ultima_fiscalizacao'))}** "
        "registram fiscalização pelo órgão competente. O acompanhamento temporal é, hoje, "
        "a maior lacuna do cadastro."
    )
    ad("")

    # ------------------------------------------------------------------- mineração
    ad("## 5. Barragens de mineração (SIGBM/ANM)")
    ad("")
    emergencia = Counter(
        (m.get("Nível de Emergência") or "Não informado").strip() for m in mineracao
    )
    em_emergencia = [
        m for m in mineracao
        if (m.get("Nível de Emergência") or "").strip() not in ("", "Sem emergência", "-")
    ]
    ad(
        f"O SIGBM registra **{len(mineracao)} barragens de mineração** em Mato Grosso. "
        f"**{len(em_emergencia)} estão com nível de emergência declarado.**"
    )
    ad("")
    ad(
        tabela(
            ["Nível de emergência", "Barragens"],
            [[nivel, quantidade] for nivel, quantidade in emergencia.most_common()],
            {1},
        )
    )
    ad("")
    if em_emergencia:
        ad(
            tabela(
                ["Barragem", "Município", "Empreendedor", "Nível", "Alteamento", "Situação"],
                [
                    [
                        (m.get("Nome") or "—")[:40],
                        m.get("Município") or "—",
                        (m.get("Empreendedor") or "—")[:34],
                        (m.get("Nível de Emergência") or "—").strip(),
                        m.get("Método construtivo da barragem") or "—",
                        m.get("Situação Operacional") or "—",
                    ]
                    for m in em_emergencia
                ],
            )
        )
        ad("")
    montante = [
        m for m in mineracao
        if "montante" in (m.get("Método construtivo da barragem") or "").lower()
    ]
    populacao = [
        m for m in mineracao
        if (m.get("Existência de população a jusante") or "").startswith("Existente")
    ]
    ad(
        f"Alteamento a montante — método proibido pela Resolução ANM nº 95/2022: "
        f"**{len(montante)} barragens**. Com população permanente a jusante: "
        f"**{len(populacao)} barragens**."
    )
    ad("")

    # ------------------------------------------------------------- concentração
    ad("## 6. Concentração territorial")
    ad("")
    por_municipio = Counter(b["municipio"] for b in barragens if b.get("municipio"))
    ad(
        tabela(
            ["Município", "Barragens", "CRI alta", "DPA alto"],
            [
                [
                    municipio,
                    quantidade,
                    sum(
                        1
                        for b in barragens
                        if b["municipio"] == municipio and b["categoria_risco"] == "Alto"
                    ),
                    sum(
                        1
                        for b in barragens
                        if b["municipio"] == municipio
                        and b["dano_potencial_associado"] == "Alto"
                    ),
                ]
                for municipio, quantidade in por_municipio.most_common(15)
            ],
            {1, 2, 3},
        )
    )
    ad("")

    # ------------------------------------------------------------------ qualidade
    ad("## 7. Qualidade do dado")
    ad("")
    campos_criticos = [
        ("Altura máxima", "altura_m"),
        ("Capacidade do reservatório", "capacidade_hm3"),
        ("Comprimento do coroamento", "comprimento_coroamento_m"),
        ("Tipo de material", "tipo_material"),
        ("Fase de vida", "fase_de_vida"),
        ("Empreendedor", "empreendedor"),
        ("Corpo hídrico", "corpo_hidrico"),
        ("Data da última inspeção", "data_ultima_inspecao"),
    ]
    ad(
        tabela(
            ["Campo", "Preenchido", "% do total", "Em branco"],
            [
                [
                    rotulo,
                    sum(1 for b in barragens if b.get(campo)),
                    percentual(sum(1 for b in barragens if b.get(campo)), total),
                    total - sum(1 for b in barragens if b.get(campo)),
                ]
                for rotulo, campo in campos_criticos
            ],
            {1, 2, 3},
        )
    )
    ad("")
    completude = Counter(b["completude_cadastro"] or "Não informado" for b in barragens)
    ad("Índice de completude atribuído pelo próprio SNISB:")
    ad("")
    ad(
        tabela(
            ["Completude", "Barragens", "% do total"],
            [
                [nivel, quantidade, percentual(quantidade, total)]
                for nivel, quantidade in completude.most_common()
            ],
            {1, 2},
        )
    )
    ad("")
    ad("### Inconsistências que precisam de correção na origem")
    ad("")
    negativas = [b for b in barragens if b.get("alerta_altura_negativa") == "sim"]
    ad(
        f"- **Altura negativa**: {len(negativas)} registro(s) com altura declarada abaixo de "
        "zero, o que é fisicamente impossível e indica erro de digitação no cadastro."
    )
    ad(
        "- **Nome de município com grafia divergente**: os órgãos alimentam o SNISB com caixa "
        "e acentuação inconsistentes (por exemplo, `SORRISO` e `Sorriso` como registros "
        "distintos), o que fragmenta qualquer contagem por município feita direto na fonte. "
        "O pipeline normaliza contra a base do IBGE e anexa o código municipal."
    )
    ad(
        f"- **Ausência de classificação**: {classes.get('Sem classificação', 0)} barragens não "
        "têm CRI e DPA definidos simultaneamente, e por isso ficam fora de qualquer fila de "
        "priorização baseada em risco."
    )
    ad(
        "- **Unidade da capacidade**: o campo `BAR_NU_CAP_TOTAL_RESERV` é publicado em hm³ "
        "(milhões de m³) apesar do nome sugerir m³. O pipeline expõe as duas colunas "
        "(`capacidade_hm3` e `capacidade_m3`) para evitar erro de escala."
    )
    ad("")

    # -------------------------------------------------------------------- fontes
    ad("## 8. Fontes e periodicidade")
    ad("")
    ad(
        tabela(
            ["Fonte", "Conteúdo", "Acesso", "Atualização"],
            [
                [
                    "SNISB / SNIRH (ANA)",
                    "Cadastro consolidado, todos os fiscalizadores",
                    "Serviço ArcGIS REST",
                    "Contínua",
                ],
                [
                    "Painel público do SNISB (ANA)",
                    "Mesmo cadastro com 73 atributos",
                    "API pública do Power BI",
                    "Contínua",
                ],
                [
                    "SIGBM (ANM)",
                    "Barragens de mineração, detalhe de engenharia",
                    "CSV em dados abertos",
                    "Diária",
                ],
                ["IBGE", "Malha municipal e códigos oficiais", "API de localidades e malhas", "Anual"],
            ],
        )
    )
    ad("")
    ad(
        "A SEMA-MT é o órgão fiscalizador da maior parte do inventário e alimenta o SNISB "
        "diretamente, conforme as Instruções Normativas nº 02/2020 e nº 04/2021. Não há, hoje, "
        "uma API estadual independente: o SNISB é o ponto de coleta."
    )
    ad("")

    RELATORIOS.mkdir(parents=True, exist_ok=True)
    destino = RELATORIOS / "diagnostico_barragens_mt.md"
    destino.write_text("\n".join(linhas), encoding="utf-8")
    print(f"  gravado {destino.relative_to(comum.RAIZ)} ({destino.stat().st_size / 1024:.0f} KB)")
    print(f"  {total} barragens | {len(classe_a)} classe A | {len(em_emergencia)} em emergência")


if __name__ == "__main__":
    main()
