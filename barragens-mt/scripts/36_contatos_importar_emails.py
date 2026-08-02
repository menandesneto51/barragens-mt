"""Importa e-mails/nomes do modelo para contatos_institucionais_piloto.csv.

Não inventa destinatários: só aplica linhas do CSV modelo (ou arquivo passado)
quando o campo `email` contém `@`. Marca fonte=validacao_import e data_validacao.

Uso:
  python scripts/36_contatos_importar_emails.py
  python scripts/36_contatos_importar_emails.py caminho/meu_preenchido.csv
  python scripts/36_contatos_importar_emails.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path

import comum

CONTATOS = comum.DADOS_TRATADOS / "contatos_institucionais_piloto.csv"
MODELO = comum.DADOS_TRATADOS / "contatos_emails_modelo.csv"


def ler(caminho: Path) -> list[dict[str, str]]:
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def gravar(caminho: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    campos = list(rows[0].keys())
    with caminho.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";")
        w.writeheader()
        w.writerows(rows)


def aplicar(fonte: Path, *, dry_run: bool = False) -> dict[str, int]:
    contatos = ler(CONTATOS)
    modelo = ler(fonte)
    if not contatos:
        raise SystemExit(f"ausente: {CONTATOS.name}")
    if not modelo:
        raise SystemExit(f"modelo vazio/ausente: {fonte}")

    hoje = date.today().isoformat()
    n_email = 0
    n_nome = 0
    n_tel = 0
    n_skip = 0

    idx: dict[tuple[str, str], dict[str, str]] = {}
    for c in contatos:
        chave = ((c.get("municipio") or "").strip(), (c.get("papel") or "").strip())
        idx[chave] = c
        cod = (c.get("codigo_ibge") or "").strip()
        if cod:
            idx[(f"ibge:{cod}", (c.get("papel") or "").strip())] = c

    for m in modelo:
        email = (m.get("email") or "").strip()
        papel = (m.get("papel") or "").strip()
        mun = (m.get("municipio") or "").strip()
        cod = (m.get("codigo_ibge") or "").strip()
        if "@" not in email or not papel:
            n_skip += 1
            continue
        alvo = idx.get((mun, papel)) or idx.get((f"ibge:{cod}", papel))
        if not alvo:
            n_skip += 1
            continue
        alvo["email"] = email
        n_email += 1
        nome = (m.get("nome") or "").strip()
        if nome:
            alvo["nome"] = nome
            n_nome += 1
        tel = (m.get("telefone") or "").strip()
        if tel:
            alvo["telefone"] = tel
            n_tel += 1
        alvo["data_validacao"] = hoje
        alvo["fonte"] = "validacao_import"
        obs = (m.get("observacao") or "").strip()
        if obs:
            alvo["observacao"] = obs

    if not dry_run and n_email:
        gravar(CONTATOS, contatos)
    return {
        "emails_aplicados": n_email,
        "nomes": n_nome,
        "telefones": n_tel,
        "linhas_ignoradas": n_skip,
        "dry_run": int(dry_run),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "arquivo",
        nargs="?",
        default=str(MODELO),
        help="CSV modelo preenchido (default: contatos_emails_modelo.csv)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    stats = aplicar(Path(args.arquivo), dry_run=args.dry_run)
    print(stats)
    if stats["emails_aplicados"] == 0:
        print(
            "Nenhum e-mail aplicado. Preencha a coluna `email` no modelo "
            f"({Path(args.arquivo).name}) com endereços institucionais validados pela SES-MT."
        )


if __name__ == "__main__":
    main()
