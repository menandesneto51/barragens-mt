"""Auditoria read-only da telemetria ANA disponível via SisClima / CSV fallback.

Saídas:
  dados/tratados/auditoria_ana_sisclima.json
  relatorios/auditoria_ana_sisclima.md

Uso:
  python scripts/52_auditoria_ana_sisclima.py
  python executar.py 52
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import comum

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from ana_sisclima_fontes import (  # noqa: E402
    carregar_cotas_alerta,
    carregar_estacoes,
    carregar_telemetria,
    cobertura_dias,
    resolver_db,
    ultima_leitura_por_estacao,
)

EIXO = comum.DADOS_TRATADOS / "eixo_hidrografico_manso_cuiaba.geojson"
SAIDA_JSON = comum.DADOS_TRATADOS / "auditoria_ana_sisclima.json"
SAIDA_MD = comum.RELATORIOS / "auditoria_ana_sisclima.md"
BUFFER_EIXO_KM = 25.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(min(1.0, a)))


def pontos_eixo() -> list[tuple[float, float]]:
    if not EIXO.is_file():
        return []
    geo = json.loads(EIXO.read_text(encoding="utf-8"))
    pts: list[tuple[float, float]] = []
    for feat in geo.get("features") or []:
        geom = feat.get("geometry") or {}
        tipo = geom.get("type")
        coords = geom.get("coordinates") or []
        if tipo == "LineString":
            for lon, lat in coords:
                pts.append((float(lat), float(lon)))
        elif tipo == "MultiLineString":
            for line in coords:
                for lon, lat in line:
                    pts.append((float(lat), float(lon)))
    return pts


def dist_eixo_km(lat: float, lon: float, pts: list[tuple[float, float]]) -> float | None:
    if not pts:
        return None
    return min(haversine_km(lat, lon, la, lo) for la, lo in pts)


def main() -> None:
    comum.preparar_diretorios()
    db = resolver_db()
    estacoes, fonte_est = carregar_estacoes()
    tele, fonte_tel = carregar_telemetria()
    alertas = carregar_cotas_alerta()
    ultimas = ultima_leitura_por_estacao(tele)
    cov7 = cobertura_dias(tele, 7)
    cov30 = cobertura_dias(tele, 30)
    eixo_pts = pontos_eixo()

    mt = [e for e in estacoes if str(e.get("uf") or "MT").upper() in ("MT", "")]
    com_cota = 0
    com_vazao = 0
    com_alerta = 0
    no_corredor = 0
    detalhe_est: list[dict[str, Any]] = []

    for e in mt:
        cod = e["codigo_estacao"]
        ult = ultimas.get(cod) or {}
        cota = ult.get("cota_cm")
        vazao = ult.get("vazao_m3s")
        alerta = alertas.get(cod)
        if alerta is None:
            alerta = ult.get("cota_alerta_cm")
        if cota is not None:
            com_cota += 1
        if vazao is not None:
            com_vazao += 1
        if alerta is not None:
            com_alerta += 1
        d_eixo = dist_eixo_km(float(e["lat"]), float(e["lon"]), eixo_pts)
        no_eixo = d_eixo is not None and d_eixo <= BUFFER_EIXO_KM
        if no_eixo:
            no_corredor += 1
        detalhe_est.append(
            {
                "codigo_estacao": cod,
                "nome": e.get("nome_estacao"),
                "rio": e.get("nome_rio"),
                "municipio": e.get("municipio"),
                "lat": e["lat"],
                "lon": e["lon"],
                "cota_cm": cota,
                "vazao_m3s": vazao,
                "cota_alerta_cm": alerta,
                "data_ultima": ult.get("data_hora") or ult.get("data"),
                "n_leituras_7d": cov7.get(cod, 0),
                "n_leituras_30d": cov30.get(cod, 0),
                "dist_eixo_km": round(d_eixo, 2) if d_eixo is not None else None,
                "no_corredor_manso_cuiaba": no_eixo,
            }
        )

    series_habilitadas = fonte_tel != "indisponivel" and any(
        (u.get("cota_cm") is not None or u.get("vazao_m3s") is not None)
        for u in ultimas.values()
    )

    relatorio = {
        "gerado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "db_sisclima": str(db) if db else None,
        "fonte_estacoes": fonte_est,
        "fonte_telemetria": fonte_tel,
        "n_estacoes_mt": len(mt),
        "n_registros_telemetria": len(tele),
        "n_estacoes_com_cota": com_cota,
        "n_estacoes_com_vazao": com_vazao,
        "n_estacoes_com_cota_alerta": com_alerta,
        "n_estacoes_corredor_eixo_km": BUFFER_EIXO_KM,
        "n_estacoes_no_corredor": no_corredor,
        "series_fluviometricas_disponiveis": series_habilitadas,
        "checklist_sisclima": {
            "USE_ANA": "true no .env SisClima para popular ana_estacoes",
            "ANA_FETCH_SERIES": "true para baixar cota/vazão (default false só traz metadados)",
            "ANA_HIDROWEB_TOKEN": "obrigatório para API HidroWeb v3",
            "fallback_local": "dados/brutos/ana_*.csv quando SQLite sem tabelas ANA",
        },
        "fronteira_produto": (
            "Cota/vazão ANA alimentam contexto fluvial e IDAP A6; "
            "não redimensionam a mancha Circular/Trajeto/HAND (não é dam break)."
        ),
        "estacoes": detalhe_est,
    }

    SAIDA_JSON.write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    linhas = [
        "# Auditoria ANA / SisClima",
        "",
        f"- Gerado: `{relatorio['gerado_em']}`",
        f"- DB: `{relatorio['db_sisclima'] or 'não encontrado'}`",
        f"- Estações: `{fonte_est}` ({len(mt)} MT)",
        f"- Telemetria: `{fonte_tel}` ({len(tele)} registros)",
        f"- Com cota / vazão / cota_alerta (última leitura): "
        f"**{com_cota}** / **{com_vazao}** / **{com_alerta}**",
        f"- No corredor Manso–Cuiabá (≤{BUFFER_EIXO_KM:.0f} km do eixo): **{no_corredor}**",
        f"- Séries fluviométricas utilizáveis: **{series_habilitadas}**",
        "",
        "## Checklist SisClima",
        "",
    ]
    for k, v in relatorio["checklist_sisclima"].items():
        linhas.append(f"- `{k}`: {v}")
    linhas.extend(
        [
            "",
            "## Fronteira",
            "",
            relatorio["fronteira_produto"],
            "",
            "## Estações no corredor",
            "",
            "| Código | Nome | Rio | Cota cm | Vazão m³/s | Dist eixo km |",
            "| --- | --- | --- | ---: | ---: | ---: |",
        ]
    )
    for e in detalhe_est:
        if not e.get("no_corredor_manso_cuiaba"):
            continue
        linhas.append(
            f"| {e['codigo_estacao']} | {e['nome']} | {e['rio'] or '—'} | "
            f"{e['cota_cm'] if e['cota_cm'] is not None else '—'} | "
            f"{e['vazao_m3s'] if e['vazao_m3s'] is not None else '—'} | "
            f"{e['dist_eixo_km'] if e['dist_eixo_km'] is not None else '—'} |"
        )
    SAIDA_MD.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"escrito {SAIDA_JSON.relative_to(comum.RAIZ)}")
    print(f"escrito {SAIDA_MD.relative_to(comum.RAIZ)}")
    print(
        f"estações MT={len(mt)} cota={com_cota} vazao={com_vazao} "
        f"corredor={no_corredor} series={series_habilitadas}"
    )


if __name__ == "__main__":
    main()
