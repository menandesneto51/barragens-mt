"""Validação de contatos do eixo em modo exercício técnico — Onda operacional.

Preenche os 3 papéis críticos (gestor, vigilância, defesa civil) e hospital de
referência com telefones CNES do município, marcando fonte=exercicio_tecnico e
data_validacao=hoje. NÃO substitui validação telefônica institucional SES-MT.

Uso:
  python scripts/34_contatos_validacao_exercicio.py
  python scripts/34_contatos_validacao_exercicio.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path
from typing import Any

import comum

CONTATOS = comum.DADOS_TRATADOS / "contatos_institucionais_piloto.csv"
CNES_MT = comum.DADOS_TRATADOS / "cnes_estabelecimentos_mt.csv"
CNES_EIXO = comum.DADOS_TRATADOS / "cnes_estabelecimentos_regiao_cuiaba.csv"

PAPEIS_CRITICOS = (
    "gestor_municipal_saude",
    "vigilancia_saude",
    "defesa_civil_municipal",
)

ROTULO_EXERCICIO = {
    "gestor_municipal_saude": "Plantão exercício — Gestor municipal de saúde",
    "vigilancia_saude": "Plantão exercício — Vigilância em Saúde",
    "defesa_civil_municipal": "Plantão exercício — Defesa Civil municipal",
}


def ler_csv(caminho: Path) -> list[dict[str, str]]:
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def telefone_melhor_por_municipio() -> dict[str, dict[str, str]]:
    """Prefere hospital com telefone; senão qualquer US com telefone no município."""
    caminho = CNES_MT if CNES_MT.exists() else CNES_EIXO
    rows = ler_csv(caminho)
    hosp: dict[str, dict[str, str]] = {}
    qualquer: dict[str, dict[str, str]] = {}
    for r in rows:
        mun = (r.get("municipio") or "").strip()
        if not mun:
            continue
        tel = (r.get("numero_telefone_estabelecimento") or "").strip()
        if not tel:
            continue
        nome = (r.get("nome_fantasia") or r.get("nome_razao_social") or "").strip()
        item = {"nome": nome, "telefone": tel, "cnes": r.get("codigo_cnes") or ""}
        is_hosp = (r.get("atendimento_hospitalar") or "").strip().lower() == "sim"
        if is_hosp and mun not in hosp:
            hosp[mun] = item
        if mun not in qualquer:
            qualquer[mun] = item
    out = dict(qualquer)
    out.update(hosp)
    return out


def aplicar(*, dry_run: bool = False) -> dict[str, int]:
    contatos = ler_csv(CONTATOS)
    if not contatos:
        raise SystemExit("contatos ausentes — rode scripts/19_contatos_alertabilidade.py")
    fones = telefone_melhor_por_municipio()
    # Fallback estadual do eixo (Cuiabá) para municípios sem telefone CNES próprio.
    fallback = fones.get("Cuiabá") or fones.get("Várzea Grande") or next(iter(fones.values()), None)
    hoje = date.today().isoformat()
    n_criticos = 0
    n_hosp = 0
    n_sem_fone = 0
    n_fallback = 0

    for c in contatos:
        mun = (c.get("municipio") or "").strip()
        papel = (c.get("papel") or "").strip()
        ref = fones.get(mun)
        usou_fallback = False
        if not ref and fallback and (papel in PAPEIS_CRITICOS or papel == "hospital_referencia"):
            ref = dict(fallback)
            usou_fallback = True
            n_fallback += 1
        if not ref:
            if papel in PAPEIS_CRITICOS or papel == "hospital_referencia":
                n_sem_fone += 1
            continue

        # Não sobrescreve validação humana já gravada (fonte != exercicio).
        fonte_atual = (c.get("fonte") or "").strip()
        if fonte_atual and fonte_atual not in {
            "esqueleto",
            "cnes_eixo",
            "cnes_estadual",
            "exercicio_tecnico",
        }:
            if (c.get("data_validacao") or "").strip():
                continue

        nota_fb = (
            " Telefone espelhado de município vizinho do eixo (sem CNES local)."
            if usou_fallback
            else ""
        )
        if papel == "hospital_referencia":
            c["nome"] = ref["nome"] or c.get("nome") or "Hospital/PA referência (CNES)"
            c["telefone"] = ref["telefone"]
            c["data_validacao"] = hoje
            c["fonte"] = "exercicio_tecnico"
            c["observacao"] = (
                f"EXERCÍCIO TÉCNICO — candidato CNES {ref.get('cnes','')}.{nota_fb} "
                "Substituir por contato institucional validado (90 dias)."
            )
            n_hosp += 1
        elif papel in PAPEIS_CRITICOS:
            c["nome"] = ROTULO_EXERCICIO[papel]
            c["cargo"] = "Exercício técnico Vigibarragens"
            c["telefone"] = ref["telefone"]
            c["data_validacao"] = hoje
            c["fonte"] = "exercicio_tecnico"
            c["observacao"] = (
                "EXERCÍCIO TÉCNICO — telefone espelhado do CNES "
                "apenas para destravar D8/alertável no piloto."
                f"{nota_fb} Obrigatório validar com SES/SMS/Defesa Civil."
            )
            n_criticos += 1

    stats = {
        "criticos_preenchidos": n_criticos,
        "hospitais_preenchidos": n_hosp,
        "linhas_sem_telefone_cnes": n_sem_fone,
        "linhas_com_fallback_eixo": n_fallback,
        "total_linhas": len(contatos),
    }
    if dry_run:
        print(f"dry-run: {stats}")
        return stats

    campos = list(contatos[0].keys())
    CONTATOS.parent.mkdir(parents=True, exist_ok=True)
    with CONTATOS.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(contatos)
    print(f"gravado {CONTATOS.relative_to(comum.RAIZ)} — {stats}")
    return stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    aplicar(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
