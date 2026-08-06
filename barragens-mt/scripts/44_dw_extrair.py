"""Extrator genérico de bancos do DW (catálogo `dw_catalogo.json`).

Uso:
  python scripts/44_dw_extrair.py                  # todos com pipeline=44
  python scripts/44_dw_extrair.py sih_internacoes
  python scripts/44_dw_extrair.py sih sia sinan
  python executar.py 44

Não processa `indicasus_leitos` (etapa 43) nem `cnes_leitos_cadastrados` (45).
Sem fonte: grava CSV vazio + status JSON (não falha o pipeline).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import comum
import dw_saude

STATUS_DIR = comum.DADOS_TRATADOS
REL = comum.RELATORIOS / "dw_extratos.md"

# Extratos com ETL dedicado — não reprocessar aqui.
DEDICADOS = {"indicasus_leitos", "cnes_leitos_cadastrados"}


def _campos_canonicos(cfg: dict[str, Any]) -> list[str]:
    aliases = cfg.get("aliases") or {}
    base = list(aliases.keys())
    extras = ["fonte", "banco_dw"]
    return base + [e for e in extras if e not in base]


def processar(nome: str) -> dict[str, Any]:
    cfg = dw_saude.extrato(nome)
    saida_nome = cfg.get("saida") or f"{nome}_mt.csv"
    saida = comum.DADOS_TRATADOS / saida_nome
    status_path = STATUS_DIR / f"{nome}_status.json"
    campos = _campos_canonicos(cfg)

    rows_raw, fonte = dw_saude.extrair(nome)
    if not rows_raw:
        comum.salvar_csv(saida, [], campos)
        payload = {
            "ok": False,
            "extrato": nome,
            "motivo": fonte,
            "n_linhas": 0,
            "saida": str(saida.relative_to(comum.RAIZ)),
            "orientacao": (
                f"Coloque dump em dados/brutos/{cfg.get('csv_dump')} ou defina "
                "VIGIBARRAGENS_DW_URL / VIGIBARRAGENS_DW_SQLITE. "
                "Ver docs/15-integracao-indicasus-dw.md."
            ),
            "gerado_em": datetime.now(timezone.utc).isoformat(),
        }
        status_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return payload

    rows: list[dict[str, Any]] = []
    for r in rows_raw:
        linha = {c: r.get(c, "") for c in campos if c not in ("fonte", "banco_dw")}
        linha["fonte"] = cfg.get("titulo") or nome
        linha["banco_dw"] = fonte
        rows.append(linha)

    comum.salvar_csv(saida, rows, campos)
    payload = {
        "ok": True,
        "extrato": nome,
        "fonte": fonte,
        "n_linhas": len(rows),
        "saida": str(saida.relative_to(comum.RAIZ)),
        "gerado_em": datetime.now(timezone.utc).isoformat(),
    }
    status_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload


def selecionar(argv: list[str]) -> list[str]:
    cat = dw_saude.carregar_catalogo()
    todos = cat.get("extratos") or {}
    if not argv:
        return sorted(
            n
            for n, cfg in todos.items()
            if str(cfg.get("pipeline") or "") == "44" and n not in DEDICADOS
        )
    # aceita nome completo ou prefixo (sih → sih_internacoes)
    out: list[str] = []
    for arg in argv:
        if arg in todos:
            out.append(arg)
            continue
        hits = [n for n in todos if n.startswith(arg) or arg in n]
        if not hits:
            raise SystemExit(f"extrato desconhecido: {arg}. Opções: {sorted(todos)}")
        out.extend(hits)
    return sorted(set(out) - DEDICADOS)


def main() -> None:
    comum.preparar_diretorios()
    nomes = selecionar(sys.argv[1:])
    if not nomes:
        raise SystemExit("nenhum extrato pipeline=44 no catálogo")
    print(f"DW extrator — {len(nomes)} extrato(s): {', '.join(nomes)}", flush=True)
    resultados: list[dict[str, Any]] = []
    for nome in nomes:
        print(f"  [{nome}] …", flush=True)
        res = processar(nome)
        resultados.append(res)
        flag = "ok" if res.get("ok") else "aguardando"
        print(f"    {flag} — {res.get('n_linhas', 0)} linhas — {res.get('motivo') or res.get('fonte')}")

    linhas_md = [
        "# Extratos DW (etapa 44)",
        "",
        f"- Gerado: {datetime.now(timezone.utc).isoformat()}",
        "",
        "| Extrato | Status | Linhas | Fonte / motivo |",
        "| --- | --- | ---: | --- |",
    ]
    for r in resultados:
        st = "ok" if r.get("ok") else "aguardando"
        linhas_md.append(
            f"| `{r.get('extrato')}` | {st} | {r.get('n_linhas', 0)} | "
            f"{r.get('fonte') or r.get('motivo') or ''} |"
        )
    linhas_md += [
        "",
        "Catálogo: `dados/config/dw_catalogo.json`.",
        "IndicaSUS: etapa `43`. CNES LT cadastrado: etapa `45`.",
        "",
    ]
    REL.write_text("\n".join(linhas_md), encoding="utf-8")
    print(f"  gravado {REL.relative_to(comum.RAIZ)}")


if __name__ == "__main__":
    main()
