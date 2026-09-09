"""Priorização estadual de barragens (roadmap 2.1).

Score determinístico 0–100 a partir de DPA, rejeito, IDAP/nível, exposição
extraterritorial, lacunas PAE e alertabilidade.

Saídas:
  dados/tratados/barragens_prioritarias_mt.csv
  relatorios/barragens_prioritarias_mt.md

Uso:
  python scripts/54_priorizacao_barragens.py
  python executar.py 54
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import comum

IDAP = comum.DADOS_TRATADOS / "idap_estadual_mt.csv"
PAE = comum.DADOS_TRATADOS / "pae_checklist_lacunas.csv"
SAIDA = comum.DADOS_TRATADOS / "barragens_prioritarias_mt.csv"
REL = comum.RELATORIOS / "barragens_prioritarias_mt.md"

# Pesos explícitos (soma 100)
PESOS = {
    "dpa_alto": 20,
    "rejeito": 15,
    "nivel_idap": 25,
    "extraterritorial": 15,
    "pae_lacunas": 15,
    "nao_alertavel": 10,
}

NIVEL_PTS = {
    "Roxo": 25,
    "Vermelho": 22,
    "Laranja": 16,
    "Amarelo": 10,
    "Verde": 2,
}


def _num(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(str(v).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None


def _ler(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def score_linha(r: dict[str, str], pae_lac: dict[str, float]) -> dict[str, Any]:
    dpa = str(r.get("dano_potencial_associado") or "").strip().casefold()
    pts_dpa = PESOS["dpa_alto"] if dpa in {"alto", "high"} or "alto" in dpa else 0

    uso = str(r.get("uso_principal") or "").casefold()
    rejeito = "rejeito" in uso or "miner" in uso
    # SIGBM / mineração costuma ter pop jusante preenchida
    if str(r.get("sigbm_populacao_jusante") or "").strip():
        rejeito = True
    pts_rej = PESOS["rejeito"] if rejeito else 0

    nivel = str(r.get("nivel") or "Verde").strip()
    pts_nv = NIVEL_PTS.get(nivel, 2)
    # Cap no peso
    pts_nv = min(pts_nv, PESOS["nivel_idap"])

    n_extra = _num(r.get("n_municipios_extraterritoriais")) or 0
    pts_ex = 0
    if n_extra >= 3:
        pts_ex = PESOS["extraterritorial"]
    elif n_extra >= 1:
        pts_ex = int(PESOS["extraterritorial"] * 0.6)

    bid = str(r.get("id_snisb") or "").strip()
    n_lac = pae_lac.get(bid, 0)
    if n_lac >= 4:
        pts_pae = PESOS["pae_lacunas"]
    elif n_lac >= 1:
        pts_pae = int(PESOS["pae_lacunas"] * 0.5)
    else:
        pts_pae = 0

    alertavel = str(r.get("alertavel") or "").strip().casefold()
    pts_al = PESOS["nao_alertavel"] if alertavel in {"não", "nao", "0", "false", ""} else 0

    total = pts_dpa + pts_rej + pts_nv + pts_ex + pts_pae + pts_al
    return {
        "id_snisb": bid,
        "nome": r.get("nome") or "",
        "municipio_sede": r.get("municipio_sede") or "",
        "nivel": nivel,
        "idap": r.get("idap") or "",
        "dano_potencial_associado": r.get("dano_potencial_associado") or "",
        "uso_principal": r.get("uso_principal") or "",
        "n_municipios_extraterritoriais": r.get("n_municipios_extraterritoriais") or "",
        "n_lacunas_pae": f"{n_lac:.0f}" if n_lac else "0",
        "alertavel": r.get("alertavel") or "",
        "pts_dpa": pts_dpa,
        "pts_rejeito": pts_rej,
        "pts_nivel": pts_nv,
        "pts_extraterritorial": pts_ex,
        "pts_pae": pts_pae,
        "pts_nao_alertavel": pts_al,
        "score_prioridade": total,
        "faixa": (
            "crítica"
            if total >= 70
            else "alta"
            if total >= 45
            else "média"
            if total >= 25
            else "baixa"
        ),
    }


def main() -> None:
    comum.preparar_diretorios()
    rows = _ler(IDAP)
    if not rows:
        print("sem idap_estadual_mt.csv — rode python executar.py 16")
        return

    pae_map: dict[str, float] = {}
    for p in _ler(PAE):
        bid = str(p.get("id_snisb") or "").strip()
        if not bid:
            continue
        n = _num(p.get("n_lacunas_criticas"))
        if n is None:
            n = _num(p.get("n_lacuna")) or 0
        pae_map[bid] = float(n)

    scored = [score_linha(r, pae_map) for r in rows]
    scored.sort(key=lambda x: (-int(x["score_prioridade"]), str(x["nome"])))
    for i, s in enumerate(scored, start=1):
        s["rank"] = i

    campos = [
        "rank",
        "score_prioridade",
        "faixa",
        "id_snisb",
        "nome",
        "municipio_sede",
        "nivel",
        "idap",
        "dano_potencial_associado",
        "uso_principal",
        "n_municipios_extraterritoriais",
        "n_lacunas_pae",
        "alertavel",
        "pts_dpa",
        "pts_rejeito",
        "pts_nivel",
        "pts_extraterritorial",
        "pts_pae",
        "pts_nao_alertavel",
    ]
    with SAIDA.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";", extrasaction="ignore")
        w.writeheader()
        for s in scored:
            w.writerow(s)

    n_crit = sum(1 for s in scored if s["faixa"] == "crítica")
    n_alta = sum(1 for s in scored if s["faixa"] == "alta")
    md = [
        "# Priorização estadual de barragens",
        "",
        f"- Total ranqueado: **{len(scored)}**",
        f"- Faixa crítica (score ≥70): **{n_crit}**",
        f"- Faixa alta (45–69): **{n_alta}**",
        "",
        "## Pesos",
        "",
    ]
    for k, v in PESOS.items():
        md.append(f"- `{k}`: {v}")
    md.extend(["", "## Top 15", "", "| Rank | Score | Barragem | Município | Nível |", "| ---: | ---: | --- | --- | --- |"])
    for s in scored[:15]:
        md.append(
            f"| {s['rank']} | {s['score_prioridade']} | {s['nome']} | "
            f"{s['municipio_sede']} | {s['nivel']} |"
        )
    md.append("")
    md.append(f"Arquivo: `{SAIDA.name}`")
    REL.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"escrito {SAIDA.relative_to(comum.RAIZ)} ({len(scored)} linhas)")
    print(f"crítica={n_crit} alta={n_alta}")
    print(f"escrito {REL.relative_to(comum.RAIZ)}")


if __name__ == "__main__":
    main()
