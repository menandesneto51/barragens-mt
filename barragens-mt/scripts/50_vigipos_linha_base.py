"""Monta linha de base VIGIPÓS e avalia O/E (canal endêmico).

Fontes (em ordem):
  1. dados/tratados/sinan_notificacoes_mt.csv (se houver linhas)
  2. dados/config/exemplos/sinan_notificacoes.exemplo.csv
  3. Série sintética documentada para leptospirose (§5.6.4)

Saídas:
  dados/tratados/vigipos_linha_base.csv
  dados/tratados/vigipos_sinais.csv
  dados/tratados/vigipos_status.json
  relatorios/vigipos_oe.md

Uso:
  python scripts/50_vigipos_linha_base.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))

import comum  # noqa: E402
from st_app.vigipos import (  # noqa: E402
    avaliar_oe,
    avaliar_oe_por_serie,
    exemplo_leptospirose_564,
)

SINAN = comum.DADOS_TRATADOS / "sinan_notificacoes_mt.csv"
EXEMPLO = comum.RAIZ / "dados" / "config" / "exemplos" / "sinan_notificacoes.exemplo.csv"
LINHA = comum.DADOS_TRATADOS / "vigipos_linha_base.csv"
SINAIS = comum.DADOS_TRATADOS / "vigipos_sinais.csv"
STATUS = comum.DADOS_TRATADOS / "vigipos_status.json"
REL = comum.RELATORIOS / "vigipos_oe.md"

# Série histórica sintética (mesma SE em anos anteriores) → média 1,8
# Usada quando não há dump SINAN — explicitamente marcada como exemplo.
SERIE_LEPTO_EXEMPLO = [1, 2, 1, 3, 2, 2, 1, 2, 1, 3]


def _ler_sinan() -> pd.DataFrame:
    for path, fonte in ((SINAN, "sinan_tratado"), (EXEMPLO, "exemplo_config")):
        if not path.is_file():
            continue
        df = pd.read_csv(path, sep=";")
        if df.empty or len(df) == 0:
            continue
        if "n_notificacoes" not in df.columns:
            continue
        df = df.copy()
        df["fonte"] = fonte
        return df
    return pd.DataFrame()


def main() -> int:
    comum.DADOS_TRATADOS.mkdir(parents=True, exist_ok=True)
    comum.RELATORIOS.mkdir(parents=True, exist_ok=True)

    sinan = _ler_sinan()
    linhas = []
    sinais_rows = []

    # Sempre inclui o exemplo normativo §5.6.4 (aceitação C3)
    ex = exemplo_leptospirose_564()
    sinais_rows.append(ex.as_dict())
    linhas.append(
        {
            "municipio": "exemplo_documental",
            "agravo": "leptospirose",
            "ano": "",
            "semana_epidemiologica": "",
            "casos": "",
            "esperado_ref": 1.8,
            "limite_superior_ref": 4,
            "fonte": "docs/05 §5.6.4",
            "observacao": "Referência normativa do roadmap (C3) — não é série municipal",
        }
    )

    if sinan.empty:
        # linha de base sintética para Cuiabá (demo)
        for i, c in enumerate(SERIE_LEPTO_EXEMPLO):
            linhas.append(
                {
                    "municipio": "Cuiabá",
                    "agravo": "leptospirose",
                    "ano": str(2016 + (i % 5)),
                    "semana_epidemiologica": "30",
                    "casos": c,
                    "esperado_ref": "",
                    "limite_superior_ref": "",
                    "fonte": "serie_sintetica_demo",
                    "observacao": "Substituir por SINAN oficial antes de uso operacional",
                }
            )
        sinal_cba = avaliar_oe_por_serie(
            observado=12,
            serie_historica=SERIE_LEPTO_EXEMPLO,
            agravo="leptospirose",
            municipio="Cuiabá",
            janela="SE-30 / 7 dias (demo)",
            k_dp=1.96,
        )
        # Força alinhamento ao exemplo documental quando a série demo foi calibrada
        # para média ~1,8 — se o limite calculado divergir, mantém o calculado.
        sinais_rows.append(sinal_cba.as_dict())
        fonte_dados = "serie_sintetica_demo + exemplo §5.6.4"
    else:
        for _, r in sinan.iterrows():
            linhas.append(
                {
                    "municipio": r.get("municipio"),
                    "agravo": r.get("agravo"),
                    "ano": "",
                    "semana_epidemiologica": r.get("semana_epidemiologica"),
                    "casos": r.get("n_notificacoes"),
                    "esperado_ref": "",
                    "limite_superior_ref": "",
                    "fonte": r.get("fonte") or "sinan",
                    "observacao": "Carga SINAN / exemplo",
                }
            )
        # O/E por município×agravo na última SE vs demais (se houver histórico)
        for (mun, agr), g in sinan.groupby(["municipio", "agravo"]):
            vals = [float(x) for x in g["n_notificacoes"].tolist()]
            if len(vals) < 2:
                # sem histórico: só registra observado
                sinal = avaliar_oe(
                    observado=vals[-1],
                    esperado=vals[-1],
                    limite_superior=vals[-1],
                    agravo=str(agr),
                    municipio=str(mun),
                    janela=str(g["semana_epidemiologica"].iloc[-1]),
                    metodo="sem_historico",
                    parametros={"n": len(vals)},
                )
            else:
                hist, obs = vals[:-1], vals[-1]
                sinal = avaliar_oe_por_serie(
                    observado=obs,
                    serie_historica=hist,
                    agravo=str(agr),
                    municipio=str(mun),
                    janela=str(g["semana_epidemiologica"].iloc[-1]),
                )
            sinais_rows.append(sinal.as_dict())
        fonte_dados = "sinan_disponivel + exemplo §5.6.4"

    pd.DataFrame(linhas).to_csv(LINHA, sep=";", index=False, encoding="utf-8-sig")

    # Flatten parametros for CSV
    flat = []
    for s in sinais_rows:
        row = {k: v for k, v in s.items() if k != "parametros"}
        row["parametros_json"] = json.dumps(s.get("parametros") or {}, ensure_ascii=False)
        flat.append(row)
    pd.DataFrame(flat).to_csv(SINAIS, sep=";", index=False, encoding="utf-8-sig")

    status = {
        "ok": True,
        "fonte": fonte_dados,
        "n_linha_base": len(linhas),
        "n_sinais": len(sinais_rows),
        "exemplo_564_ok": (
            abs(ex.observado - 12) < 1e-9
            and abs(ex.esperado - 1.8) < 1e-9
            and abs(ex.limite_superior - 4) < 1e-9
            and abs(ex.razao_oe - 6.7) < 0.05
            and "crítico" in ex.classificacao
        ),
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "nota": (
            "Sinal epidemiológico é ato de vigilância — método e parâmetros ficam "
            "registrados. Substituir série sintética por SINAN oficial (etapa 44/DW)."
        ),
    }
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# VIGIPÓS — O/E e canal endêmico",
        "",
        f"- Fonte: **{fonte_dados}**",
        f"- Linhas de base: **{len(linhas)}**",
        f"- Sinais avaliados: **{len(sinais_rows)}**",
        f"- Exemplo §5.6.4 reproduzido: **{'sim' if status['exemplo_564_ok'] else 'não'}**",
        "",
        "## Sinais",
        "",
        "| Município | Agravo | Obs | Esp | Lim | O/E | Classe |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for s in sinais_rows:
        md.append(
            f"| {s['municipio']} | {s['agravo']} | {s['observado']} | {s['esperado']} | "
            f"{s['limite_superior']} | {s['razao_oe']} | {s['classificacao']} |"
        )
    md += [
        "",
        f"CSV base: `{LINHA.relative_to(comum.RAIZ)}`",
        f"CSV sinais: `{SINAIS.relative_to(comum.RAIZ)}`",
        "",
    ]
    REL.write_text("\n".join(md), encoding="utf-8")
    print(f"OK {LINHA}")
    print(f"OK {SINAIS}")
    print(f"OK {STATUS} exemplo_564={status['exemplo_564_ok']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
