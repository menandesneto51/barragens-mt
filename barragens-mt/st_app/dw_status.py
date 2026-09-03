"""Status dos extratos DW / IndicaSUS / CNES LT para o painel."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TRATADOS = Path(__file__).resolve().parents[1] / "dados" / "tratados"
CATALOGO = Path(__file__).resolve().parents[1] / "dados" / "config" / "dw_catalogo.json"


def _ler_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def listar_status_dw() -> list[dict[str, Any]]:
    cat = _ler_json(CATALOGO)
    extratos = cat.get("extratos") or {}
    itens: list[dict[str, Any]] = []
    for nome, cfg in extratos.items():
        st_path = TRATADOS / f"{nome}_status.json"
        # IndicaSUS usa nome legado
        if nome == "indicasus_leitos":
            st_path = TRATADOS / "indicasus_leitos_status.json"
        st = _ler_json(st_path)
        saida = cfg.get("saida") or f"{nome}_mt.csv"
        arquivo = TRATADOS / saida
        n_arquivo = 0
        if arquivo.is_file():
            try:
                n_arquivo = max(0, len(arquivo.read_text(encoding="utf-8-sig").splitlines()) - 1)
            except OSError:
                n_arquivo = 0
        ok = bool(st.get("ok")) or n_arquivo > 0
        itens.append(
            {
                "extrato": nome,
                "titulo": cfg.get("titulo") or nome,
                "prioridade": cfg.get("prioridade") or "",
                "pipeline": str(cfg.get("pipeline") or ""),
                "ok": ok,
                "n_linhas": int(st.get("n_linhas") or st.get("n_estabelecimentos") or n_arquivo or 0),
                "fonte": st.get("fonte") or st.get("motivo") or ("arquivo local" if n_arquivo else "sem fonte"),
                "saida": saida,
            }
        )
    return itens
