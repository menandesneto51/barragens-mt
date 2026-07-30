"""Cadastro de contatos institucionais do piloto e flag de alertabilidade.

Gera o esqueleto exigido por docs/04-alertas.md §4.2 para os municípios do eixo
Manso–Cuiabá. Contatos começam sem validação (alertável = não) até validação
telefônica institucional.

Saídas:
  dados/tratados/contatos_institucionais_piloto.csv
  dados/tratados/alertabilidade_piloto.csv
  relatorios/contatos_alertabilidade.md
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

import comum

PAPEIS_OBRIGATORIOS = (
    "gestor_municipal_saude",
    "vigilancia_saude",
    "defesa_civil_municipal",
    "cievs",
    "samu",
    "hospital_referencia",
    "vigiagua",
    "concessionaria_agua",
)

ROTULOS = {
    "gestor_municipal_saude": "Gestor municipal de saúde",
    "vigilancia_saude": "Vigilância em Saúde municipal",
    "defesa_civil_municipal": "Defesa Civil municipal",
    "cievs": "CIEVS (regional/municipal)",
    "samu": "SAMU / regulação de urgência",
    "hospital_referencia": "Hospital de referência",
    "vigiagua": "Vigilância da qualidade da água",
    "concessionaria_agua": "Concessionária de água",
}


def ler_interesse() -> dict[str, Any]:
    caminho = comum.DADOS_TRATADOS / "cuiaba_municipios_de_interesse.json"
    if not caminho.exists():
        raise SystemExit(f"base ausente: {caminho.name}")
    return json.loads(caminho.read_text(encoding="utf-8"))


def ler_csv(caminho: Path) -> list[dict[str, Any]]:
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def telefone_hospital_por_municipio() -> dict[str, dict[str, str]]:
    """Melhor candidato a hospital de referência por município (CNES estadual ou eixo)."""
    estadual = comum.DADOS_TRATADOS / "cnes_estabelecimentos_mt.csv"
    eixo = comum.DADOS_TRATADOS / "cnes_estabelecimentos_regiao_cuiaba.csv"
    rows = ler_csv(estadual if estadual.exists() else eixo)
    fonte = "cnes_estadual" if estadual.exists() else "cnes_eixo"
    melhor: dict[str, dict[str, str]] = {}
    for r in rows:
        mun = (r.get("municipio") or "").strip()
        if not mun:
            continue
        hosp = (r.get("atendimento_hospitalar") or "").strip().lower() == "sim"
        tel = (r.get("numero_telefone_estabelecimento") or "").strip()
        nome = (r.get("nome_fantasia") or r.get("nome_razao_social") or "").strip()
        if not hosp:
            continue
        atual = melhor.get(mun)
        # Preferir quem tem telefone.
        if atual is None or (tel and not atual.get("telefone")):
            melhor[mun] = {
                "nome": nome,
                "telefone": tel,
                "cnes": r.get("codigo_cnes") or "",
                "fonte": fonte,
            }
    return melhor


def mesclar_existente(
    gerados: list[dict[str, Any]], existentes: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Preserva preenchimentos humanos já gravados no CSV."""
    chave = lambda r: ((r.get("codigo_ibge") or ""), (r.get("papel") or ""))
    por_chave = {chave(r): r for r in existentes}
    saida = []
    for novo in gerados:
        velho = por_chave.get(chave(novo))
        if not velho:
            saida.append(novo)
            continue
        # Campos editáveis pelo usuário prevalecem se não vazios.
        mesclado = dict(novo)
        for campo in (
            "nome",
            "cargo",
            "telefone",
            "celular",
            "email",
            "substituto",
            "telefone_substituto",
            "data_validacao",
            "observacao",
        ):
            if (velho.get(campo) or "").strip():
                mesclado[campo] = velho[campo]
        saida.append(mesclado)
    return saida


def gerar_contatos(interesse: dict[str, Any]) -> list[dict[str, Any]]:
    hospitais = telefone_hospital_por_municipio()
    linhas: list[dict[str, Any]] = []
    for mun in interesse.get("municipios") or []:
        nome = mun["nome"]
        ibge = mun["codigo_ibge"]
        hosp = hospitais.get(nome, {})
        for papel in PAPEIS_OBRIGATORIOS:
            nome_contato = ""
            telefone = ""
            fonte = "esqueleto"
            if papel == "hospital_referencia" and hosp:
                nome_contato = hosp.get("nome") or ""
                telefone = hosp.get("telefone") or ""
                fonte = hosp.get("fonte") or ("cnes_eixo" if nome_contato else "esqueleto")
            linhas.append(
                {
                    "municipio": nome,
                    "codigo_ibge": ibge,
                    "regiao_saude": "Baixada Cuiabana",
                    "papel": papel,
                    "papel_rotulo": ROTULOS[papel],
                    "nome": nome_contato,
                    "cargo": "",
                    "telefone": telefone,
                    "celular": "",
                    "email": "",
                    "substituto": "",
                    "telefone_substituto": "",
                    "data_validacao": "",
                    "fonte": fonte,
                    "observacao": (
                        "Preencher e validar por telefone (prazo 90 dias)."
                        if not nome_contato
                        else "Candidato CNES — validar contato institucional."
                    ),
                }
            )
    return linhas


def validado_90d(data_txt: str, hoje: date) -> bool:
    if not (data_txt or "").strip():
        return False
    try:
        data = date.fromisoformat(data_txt.strip()[:10])
    except ValueError:
        return False
    return (hoje - data).days <= 90


def avaliar_alertabilidade(
    contatos: list[dict[str, Any]],
    piloto: list[dict[str, Any]],
    hoje: date,
) -> list[dict[str, Any]]:
    por_mun: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in contatos:
        por_mun[c["municipio"]].append(c)

    saida: list[dict[str, Any]] = []
    for b in piloto:
        afetados = [
            p.strip()
            for p in (b.get("municipios_potencialmente_afetados") or "").split("|")
            if p.strip()
        ]
        if not afetados:
            afetados = [b.get("municipio_sede") or ""]
        munis_ok = 0
        munis_falta: list[str] = []
        for mun in afetados:
            lista = por_mun.get(mun, [])
            if not lista:
                munis_falta.append(f"{mun}:sem_cadastro")
                continue
            papeis = {c["papel"] for c in lista}
            faltam = [p for p in PAPEIS_OBRIGATORIOS if p not in papeis]
            validados = [
                c
                for c in lista
                if c["papel"] in {"gestor_municipal_saude", "vigilancia_saude", "defesa_civil_municipal"}
                and validado_90d(c.get("data_validacao") or "", hoje)
                and (c.get("telefone") or c.get("celular") or c.get("email"))
            ]
            if faltam or len(validados) < 3:
                detalhe = []
                if faltam:
                    detalhe.append("papeis=" + ",".join(faltam))
                if len(validados) < 3:
                    detalhe.append("criticos_nao_validados")
                munis_falta.append(f"{mun}:{'|'.join(detalhe)}")
            else:
                munis_ok += 1

        alertavel = munis_ok == len(afetados) and len(afetados) > 0
        contatos_ok = alertavel  # D8 True só quando o vínculo completo está validado
        saida.append(
            {
                "id_snisb": b.get("id_snisb"),
                "nome": b.get("nome"),
                "municipio_sede": b.get("municipio_sede"),
                "n_municipios_afetados": len(afetados),
                "municipios_com_vinculo_ok": munis_ok,
                "alertavel": "sim" if alertavel else "não",
                "contatos_validados_90d": "sim" if contatos_ok else "não",
                "pendencias": " | ".join(munis_falta),
            }
        )
    return saida


def escrever_relatorio(
    contatos: list[dict[str, Any]],
    alertab: list[dict[str, Any]],
) -> None:
    preenchidos = sum(1 for c in contatos if (c.get("nome") or "").strip())
    com_tel = sum(1 for c in contatos if (c.get("telefone") or c.get("celular") or "").strip())
    validados = sum(1 for c in contatos if (c.get("data_validacao") or "").strip())
    alertaveis = sum(1 for a in alertab if a.get("alertavel") == "sim")
    partes = [
        "# Contatos institucionais e alertabilidade — piloto Manso–Cuiabá",
        "",
        f"Gerado em {datetime.now().isoformat(timespec='seconds')}.",
        "",
        "## Cadastro",
        "",
        f"- Linhas de contato: **{len(contatos)}** "
        f"({len(PAPEIS_OBRIGATORIOS)} papéis × municípios do eixo)",
        f"- Com nome preenchido: **{preenchidos}**",
        f"- Com telefone/celular: **{com_tel}**",
        f"- Com data de validação: **{validados}**",
        "",
        "## Alertabilidade das barragens do piloto",
        "",
        f"- Barragens avaliadas: **{len(alertab)}**",
        f"- Alertáveis (vínculo completo validado): **{alertaveis}**",
        "",
        "Enquanto `alertavel=não`, o alerta textual continua sendo gerado para treino/"
        "simulado, mas a barragem fica marcada como **não alertável** na operação "
        "(docs/04 §4.1–4.2).",
        "",
        "## Como validar",
        "",
        "1. Editar `dados/tratados/contatos_institucionais_piloto.csv`.",
        "2. Preencher nome, telefone/e-mail e `data_validacao` (AAAA-MM-DD).",
        "3. Rodar de novo `python scripts/19_contatos_alertabilidade.py` "
        "(preserva preenchimentos).",
        "4. Recalcular IDAP/piloto (`16` → `18`) para propagar D8 e a flag.",
        "",
    ]
    destino = comum.RELATORIOS / "contatos_alertabilidade.md"
    destino.write_text("\n".join(partes), encoding="utf-8")
    print(f"  gravado {destino.relative_to(comum.RAIZ)}")


def main() -> None:
    comum.preparar_diretorios()
    interesse = ler_interesse()
    caminho_contatos = comum.DADOS_TRATADOS / "contatos_institucionais_piloto.csv"
    existentes = ler_csv(caminho_contatos)
    gerados = gerar_contatos(interesse)
    contatos = mesclar_existente(gerados, existentes)

    piloto = ler_csv(comum.DADOS_TRATADOS / "piloto_manso_cuiaba.csv")
    if not piloto:
        # Fallback: monta a partir do IDAP estadual se o piloto ainda não rodou.
        idap = ler_csv(comum.DADOS_TRATADOS / "idap_estadual_mt.csv")
        piloto = [
            r
            for r in idap
            if "Cuiabá" in (r.get("municipios_potencialmente_afetados") or "")
            or "Várzea Grande" in (r.get("municipios_potencialmente_afetados") or "")
            or (r.get("nome") or "").upper().startswith("UHE MANSO")
        ]

    hoje = date.today()
    alertab = avaliar_alertabilidade(contatos, piloto, hoje)

    comum.salvar_csv(
        caminho_contatos,
        contatos,
        list(contatos[0].keys()) if contatos else [],
    )
    comum.salvar_csv(
        comum.DADOS_TRATADOS / "alertabilidade_piloto.csv",
        alertab,
        list(alertab[0].keys()) if alertab else [],
    )
    escrever_relatorio(contatos, alertab)
    print(f"  contatos: {len(contatos)} (existentes preservados: {len(existentes)})")
    print(f"  alertáveis: {sum(1 for a in alertab if a['alertavel'] == 'sim')}/{len(alertab)}")


if __name__ == "__main__":
    main()
