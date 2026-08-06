"""Importa contatos/e-mails para contatos_institucionais_piloto.csv.

Aceita:
  - modelo parcial (só linhas com e-mail) — modo `patch`
  - arquivo completo no schema do cadastro — modo `merge` ou `replace`

Quando o arquivo oficial da SES chegar, use:
  python scripts/36_contatos_importar_emails.py arquivo_completo.csv --modo replace
  python executar.py 19 16 18

Uso:
  python scripts/36_contatos_importar_emails.py
  python scripts/36_contatos_importar_emails.py caminho.csv --modo merge
  python scripts/36_contatos_importar_emails.py caminho.csv --modo replace
  python scripts/36_contatos_importar_emails.py --gerar-modelo
  python scripts/36_contatos_importar_emails.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path
from typing import Any

import comum

CONTATOS = comum.DADOS_TRATADOS / "contatos_institucionais_piloto.csv"
MODELO = comum.DADOS_TRATADOS / "contatos_emails_modelo.csv"

CAMPOS_CADASTRO = (
    "municipio",
    "codigo_ibge",
    "regiao_saude",
    "papel",
    "papel_rotulo",
    "nome",
    "cargo",
    "telefone",
    "celular",
    "email",
    "substituto",
    "telefone_substituto",
    "data_validacao",
    "fonte",
    "observacao",
)

CAMPOS_HUMANOS = (
    "nome",
    "cargo",
    "telefone",
    "celular",
    "email",
    "substituto",
    "telefone_substituto",
    "data_validacao",
    "fonte",
    "observacao",
    "regiao_saude",
    "papel_rotulo",
)


def ler(caminho: Path) -> list[dict[str, str]]:
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "") for k, v in r.items()} for r in csv.DictReader(f, delimiter=";")]


def gravar(caminho: Path, rows: list[dict[str, str]], campos: tuple[str, ...] | list[str]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(campos), delimiter=";")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in campos})


def _chave(row: dict[str, str]) -> tuple[str, str] | None:
    papel = (row.get("papel") or "").strip()
    if not papel:
        return None
    cod = (row.get("codigo_ibge") or "").strip().replace(".0", "")
    mun = (row.get("municipio") or "").strip()
    if cod:
        return (f"ibge:{cod}", papel)
    if mun:
        return (mun, papel)
    return None


def _parece_completo(rows: list[dict[str, str]]) -> bool:
    if not rows:
        return False
    cols = set(rows[0].keys())
    return {"papel", "municipio"}.issubset(cols) and (
        "cargo" in cols or "regiao_saude" in cols or "papel_rotulo" in cols
    )


def gerar_modelo() -> Path:
    """Gera modelo com todas as linhas do cadastro (e-mail vazio, pronto para SES)."""
    contatos = ler(CONTATOS)
    if not contatos:
        raise SystemExit(f"ausente: {CONTATOS.name}")
    out = []
    for c in contatos:
        out.append(
            {
                "municipio": c.get("municipio", ""),
                "codigo_ibge": c.get("codigo_ibge", ""),
                "papel": c.get("papel", ""),
                "email": c.get("email", ""),
                "nome": c.get("nome", ""),
                "telefone": c.get("telefone", "") or c.get("celular", ""),
                "observacao": "Preencher e-mail institucional validado pela SES-MT/SMS",
            }
        )
    campos = ("municipio", "codigo_ibge", "papel", "email", "nome", "telefone", "observacao")
    gravar(MODELO, out, campos)
    return MODELO


def aplicar(
    fonte: Path,
    *,
    modo: str = "auto",
    dry_run: bool = False,
) -> dict[str, Any]:
    contatos = ler(CONTATOS)
    modelo = ler(fonte)
    if not modelo:
        raise SystemExit(f"modelo vazio/ausente: {fonte}")

    if modo == "auto":
        modo = "merge" if _parece_completo(modelo) else "patch"

    hoje = date.today().isoformat()
    stats: dict[str, Any] = {
        "modo": modo,
        "linhas_fonte": len(modelo),
        "emails_aplicados": 0,
        "campos_atualizados": 0,
        "linhas_novas": 0,
        "linhas_ignoradas": 0,
        "dry_run": dry_run,
    }

    if modo == "replace":
        # Aceita schema completo; completa chaves faltantes do esqueleto atual.
        idx_atual = {_chave(c): c for c in contatos if _chave(c)}
        novos: list[dict[str, str]] = []
        for m in modelo:
            ch = _chave(m)
            if not ch:
                stats["linhas_ignoradas"] += 1
                continue
            base = {k: "" for k in CAMPOS_CADASTRO}
            base.update(idx_atual.get(ch) or {})
            for k in CAMPOS_CADASTRO:
                if k in m and str(m.get(k) or "").strip():
                    base[k] = str(m.get(k) or "").strip()
            if "@" in (base.get("email") or "") or any(
                (base.get(k) or "").strip() for k in ("nome", "telefone", "celular")
            ):
                if not (base.get("data_validacao") or "").strip():
                    base["data_validacao"] = hoje
                if not (base.get("fonte") or "").strip():
                    base["fonte"] = "validacao_import"
            novos.append(base)
            if "@" in (base.get("email") or ""):
                stats["emails_aplicados"] += 1
        # Mantém linhas do esqueleto não presentes no arquivo (não perde papéis).
        chaves_novas = {_chave(n) for n in novos}
        for c in contatos:
            ch = _chave(c)
            if ch and ch not in chaves_novas:
                novos.append(c)
                stats["linhas_ignoradas"] += 0  # preservada
        stats["linhas_novas"] = max(0, len(novos) - len(contatos))
        if not dry_run:
            gravar(CONTATOS, novos, CAMPOS_CADASTRO)
        stats["linhas_saida"] = len(novos)
        return stats

    # merge / patch sobre o cadastro atual
    if not contatos:
        raise SystemExit(f"ausente: {CONTATOS.name} — rode a etapa 19 antes.")

    idx: dict[tuple[str, str], dict[str, str]] = {}
    for c in contatos:
        ch = _chave(c)
        if ch:
            idx[ch] = c
        mun = (c.get("municipio") or "").strip()
        papel = (c.get("papel") or "").strip()
        if mun and papel:
            idx[(mun, papel)] = c

    for m in modelo:
        ch = _chave(m)
        if not ch:
            stats["linhas_ignoradas"] += 1
            continue
        alvo = idx.get(ch)
        if not alvo:
            # tenta municipio+papel se chave era ibge
            mun = (m.get("municipio") or "").strip()
            papel = (m.get("papel") or "").strip()
            alvo = idx.get((mun, papel)) if mun and papel else None
        if not alvo:
            if modo == "merge" and (m.get("papel") or "").strip():
                # upsert nova linha mínima
                nova = {k: "" for k in CAMPOS_CADASTRO}
                for k in CAMPOS_CADASTRO:
                    if k in m:
                        nova[k] = str(m.get(k) or "").strip()
                nova["fonte"] = nova.get("fonte") or "validacao_import"
                nova["data_validacao"] = nova.get("data_validacao") or hoje
                contatos.append(nova)
                idx[ch] = nova
                stats["linhas_novas"] += 1
                if "@" in (nova.get("email") or ""):
                    stats["emails_aplicados"] += 1
                continue
            stats["linhas_ignoradas"] += 1
            continue

        if modo == "patch" and "@" not in (m.get("email") or ""):
            stats["linhas_ignoradas"] += 1
            continue

        mudou = False
        for k in CAMPOS_HUMANOS:
            val = str(m.get(k) or "").strip()
            if not val:
                continue
            if k == "email" and "@" not in val:
                continue
            if alvo.get(k) != val:
                alvo[k] = val
                mudou = True
                stats["campos_atualizados"] += 1
            if k == "email" and "@" in val:
                stats["emails_aplicados"] += 1
        if mudou:
            alvo["data_validacao"] = hoje
            alvo["fonte"] = "validacao_import"

    if not dry_run:
        gravar(CONTATOS, contatos, CAMPOS_CADASTRO if contatos else list(contatos[0].keys()))
    stats["linhas_saida"] = len(contatos)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("arquivo", nargs="?", default=str(MODELO))
    parser.add_argument(
        "--modo",
        choices=("auto", "patch", "merge", "replace"),
        default="auto",
        help="auto detecta schema completo; replace regrava o cadastro",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--gerar-modelo",
        action="store_true",
        help="Regenera contatos_emails_modelo.csv com todas as linhas do cadastro",
    )
    args = parser.parse_args()
    if args.gerar_modelo:
        path = gerar_modelo()
        print(f"modelo gerado: {path.name} ({len(ler(path))} linhas)")
        return
    stats = aplicar(Path(args.arquivo), modo=args.modo, dry_run=args.dry_run)
    print(stats)
    if stats.get("emails_aplicados", 0) == 0 and stats["modo"] == "patch":
        print(
            "Nenhum e-mail no arquivo. Quando o cadastro completo da SES chegar, use:\n"
            f"  python scripts/36_contatos_importar_emails.py <arquivo.csv> --modo replace"
        )


if __name__ == "__main__":
    main()
