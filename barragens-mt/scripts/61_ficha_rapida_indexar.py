"""Indexa fichas rápidas exportadas para o dossiê / IPAPD (A5).

Lê `dados/tratados/fichas_rapidas/*.json` (export de `painel/ficha_rapida.html`
ou exemplos) e grava:

  dados/tratados/fichas_rapidas_indice.csv
  dados/tratados/fichas_rapidas_status.json
  relatorios/fichas_rapidas.md

Uso:
  python scripts/61_ficha_rapida_indexar.py
  python executar.py 61
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))

import comum  # noqa: E402
from st_app.ficha_rapida import DIR_FICHAS, listar_fichas, termos_ipapd_da_ficha  # noqa: E402

INDICE = comum.DADOS_TRATADOS / "fichas_rapidas_indice.csv"
STATUS = comum.DADOS_TRATADOS / "fichas_rapidas_status.json"
REL = comum.RELATORIOS / "fichas_rapidas.md"

CAMPOS = [
    "arquivo",
    "municipio",
    "barragem",
    "id_snisb",
    "tipo",
    "status",
    "fonte",
    "tem_termos_ipapd",
    "mtime",
]


def _mtime_iso(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    except OSError:
        return ""


def main() -> None:
    comum.preparar_diretorios()
    DIR_FICHAS.mkdir(parents=True, exist_ok=True)
    linhas: list[dict[str, Any]] = []
    com_ipapd = 0
    for path in listar_fichas():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        data["_arquivo"] = path.name
        termos = termos_ipapd_da_ficha(data)
        tem = bool(
            set(termos.keys())
            - {"fonte_ficha"}
        )
        if tem:
            com_ipapd += 1
        linhas.append(
            {
                "arquivo": path.name,
                "municipio": str(data.get("municipio") or ""),
                "barragem": str(data.get("barragem") or ""),
                "id_snisb": str(data.get("id_snisb") or ""),
                "tipo": str(data.get("tipo") or ""),
                "status": str(data.get("status") or ""),
                "fonte": str(data.get("fonte") or ""),
                "tem_termos_ipapd": "sim" if tem else "nao",
                "mtime": _mtime_iso(path),
            }
        )

    comum.salvar_csv(INDICE, linhas, CAMPOS)
    munics = sorted({r["municipio"] for r in linhas if r["municipio"]})
    status = {
        "ok": True,
        "n_fichas": len(linhas),
        "n_com_termos_ipapd": com_ipapd,
        "municipios": munics,
        "pasta": str(DIR_FICHAS.relative_to(comum.RAIZ)),
        "gerado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "nota": (
            "Exporte JSON em painel/ficha_rapida.html para "
            "dados/tratados/fichas_rapidas/ — exemplos Manso/Cuiabá já inclusos."
        ),
    }
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    REL.write_text(
        "\n".join(
            [
                "# Fichas rápidas — índice",
                "",
                f"- Fichas: **{len(linhas)}**",
                f"- Com termos IPAPD A/P/C: **{com_ipapd}**",
                f"- Municípios: {', '.join(munics) or '—'}",
                "",
                status["nota"],
                "",
                "| Arquivo | Município | Barragem | IPAPD |",
                "| --- | --- | --- | --- |",
                *[
                    f"| `{r['arquivo']}` | {r['municipio']} | {r['barragem']} | "
                    f"{r['tem_termos_ipapd']} |"
                    for r in linhas
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"  fichas rápidas: {len(linhas)} indexadas ({com_ipapd} com IPAPD)")


if __name__ == "__main__":
    main()
