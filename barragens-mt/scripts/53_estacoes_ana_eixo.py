"""Associa estações ANA (SisClima/CSV) a barragens e enriquece A6 quando houver cota+alerta.

Saídas:
  dados/tratados/ana_estacoes_barragem.csv   — N estações mais próximas por barragem
  dados/tratados/hidro_barragens_mt.csv      — mescla cota_cm/vazao_m3s/razao medida
  relatorios/estacoes_ana_eixo.md

Uso:
  python scripts/53_estacoes_ana_eixo.py
  python executar.py 53
"""

from __future__ import annotations

import csv
import json
import math
import sys
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
    ultima_leitura_por_estacao,
)

INVENTARIO = comum.DADOS_TRATADOS / "inventario_barragens_mt.csv"
PILOTO = comum.DADOS_TRATADOS / "piloto_manso_cuiaba.csv"
HIDRO = comum.DADOS_TRATADOS / "hidro_barragens_mt.csv"
EIXO = comum.DADOS_TRATADOS / "eixo_hidrografico_manso_cuiaba.geojson"
SAIDA = comum.DADOS_TRATADOS / "ana_estacoes_barragem.csv"
REL = comum.RELATORIOS / "estacoes_ana_eixo.md"

N_POR_BARRAGEM = 3
MAX_DIST_KM = 80.0
BUFFER_EIXO_KM = 25.0
# A6 medido só com estação próxima ou no corredor do eixo (evita “pegar” posto distante).
A6_MAX_DIST_KM = 30.0


def _num(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(str(v).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(min(1.0, a)))


def ler_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def gravar_csv(path: Path, rows: list[dict[str, Any]], campos: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";", extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in campos})


def pontos_eixo() -> list[tuple[float, float]]:
    if not EIXO.is_file():
        return []
    geo = json.loads(EIXO.read_text(encoding="utf-8"))
    pts: list[tuple[float, float]] = []
    for feat in geo.get("features") or []:
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates") or []
        if geom.get("type") == "LineString":
            for lon, lat in coords:
                pts.append((float(lat), float(lon)))
        elif geom.get("type") == "MultiLineString":
            for line in coords:
                for lon, lat in line:
                    pts.append((float(lat), float(lon)))
    return pts


def dist_eixo(lat: float, lon: float, pts: list[tuple[float, float]]) -> float | None:
    if not pts:
        return None
    return min(haversine_km(lat, lon, la, lo) for la, lo in pts)


def relacao_montante_jusante(lat_b: float, lat_e: float) -> str:
    """Heurística bacia Manso–Cuiabá (fluxo geral N→S): lat maior ≈ montante."""
    if lat_e > lat_b + 0.03:
        return "montante"
    if lat_e < lat_b - 0.03:
        return "jusante"
    return "local"


def ids_piloto() -> set[str]:
    return {
        (r.get("id_snisb") or "").strip()
        for r in ler_csv(PILOTO)
        if (r.get("id_snisb") or "").strip()
    }


def fmt(v: float | None, nd: int = 2) -> str:
    if v is None:
        return ""
    return f"{v:.{nd}f}".replace(".", ",")


def norm_id(valor: Any) -> str:
    texto = str(valor or "").strip()
    if texto.endswith(".0"):
        try:
            return str(int(float(texto)))
        except ValueError:
            return texto
    return texto


def main() -> None:
    comum.preparar_diretorios()
    estacoes, fonte_est = carregar_estacoes()
    tele, fonte_tel = carregar_telemetria()
    alertas = carregar_cotas_alerta()
    ultimas = ultima_leitura_por_estacao(tele)
    eixo_pts = pontos_eixo()
    piloto = ids_piloto()

    inv = []
    for r in ler_csv(INVENTARIO):
        bid = norm_id(r.get("id_snisb"))
        la, lo = _num(r.get("latitude")), _num(r.get("longitude"))
        if not bid or la is None or lo is None:
            continue
        inv.append(
            {
                "id_snisb": bid,
                "nome": r.get("nome") or "",
                "municipio": r.get("municipio") or "",
                "lat": la,
                "lon": lo,
                "piloto": bid in piloto,
            }
        )

    campos = [
        "id_snisb",
        "nome_barragem",
        "municipio_sede",
        "piloto_eixo",
        "rank",
        "codigo_estacao",
        "nome_estacao",
        "nome_rio",
        "municipio_estacao",
        "lat",
        "lon",
        "dist_barragem_km",
        "dist_eixo_km",
        "no_corredor_eixo",
        "relacao",
        "cota_cm",
        "vazao_m3s",
        "cota_alerta_cm",
        "razao_nivel_cota_alerta",
        "data_ultima",
        "fonte_estacao",
        "fonte_telemetria",
        "a6_fonte",
    ]

    saidas: list[dict[str, Any]] = []
    # Melhor estação com razão medida por barragem (para mesclar no hidro)
    a6_por_barragem: dict[str, dict[str, Any]] = {}

    for b in inv:
        candidatos: list[tuple[float, dict[str, Any]]] = []
        for e in estacoes:
            d = haversine_km(b["lat"], b["lon"], float(e["lat"]), float(e["lon"]))
            if d > MAX_DIST_KM:
                continue
            candidatos.append((d, e))
        candidatos.sort(key=lambda x: x[0])
        for rank, (dist, e) in enumerate(candidatos[:N_POR_BARRAGEM], start=1):
            cod = e["codigo_estacao"]
            ult = ultimas.get(cod) or {}
            cota = ult.get("cota_cm")
            vazao = ult.get("vazao_m3s")
            alerta = alertas.get(cod)
            if alerta is None:
                alerta = ult.get("cota_alerta_cm")
            razao = None
            a6_fonte = ""
            if cota is not None and alerta is not None and alerta > 0:
                razao = float(cota) / float(alerta)
                a6_fonte = (
                    "cota_medida" if dist <= A6_MAX_DIST_KM else "contexto_somente"
                )
            elif cota is not None:
                a6_fonte = "contexto_somente"
            d_eixo = dist_eixo(float(e["lat"]), float(e["lon"]), eixo_pts)
            no_corr = d_eixo is not None and d_eixo <= BUFFER_EIXO_KM
            row = {
                "id_snisb": b["id_snisb"],
                "nome_barragem": b["nome"],
                "municipio_sede": b["municipio"],
                "piloto_eixo": "1" if b["piloto"] else "0",
                "rank": rank,
                "codigo_estacao": cod,
                "nome_estacao": e.get("nome_estacao"),
                "nome_rio": e.get("nome_rio"),
                "municipio_estacao": e.get("municipio"),
                "lat": f"{e['lat']:.6f}".replace(".", ","),
                "lon": f"{e['lon']:.6f}".replace(".", ","),
                "dist_barragem_km": fmt(dist, 2),
                "dist_eixo_km": fmt(d_eixo, 2) if d_eixo is not None else "",
                "no_corredor_eixo": "1" if no_corr else "0",
                "relacao": relacao_montante_jusante(b["lat"], float(e["lat"])),
                "cota_cm": fmt(cota, 1) if cota is not None else "",
                "vazao_m3s": fmt(vazao, 2) if vazao is not None else "",
                "cota_alerta_cm": fmt(alerta, 1) if alerta is not None else "",
                "razao_nivel_cota_alerta": fmt(razao, 3) if razao is not None else "",
                "data_ultima": ult.get("data_hora") or ult.get("data") or "",
                "fonte_estacao": fonte_est,
                "fonte_telemetria": fonte_tel,
                "a6_fonte": a6_fonte,
            }
            saidas.append(row)
            # Corredor entra no contexto UI; A6 medido exige proximidade à barragem.
            elegivel_a6 = a6_fonte == "cota_medida" and dist <= A6_MAX_DIST_KM
            if elegivel_a6 and (
                b["id_snisb"] not in a6_por_barragem
                or dist < a6_por_barragem[b["id_snisb"]]["dist"]
            ):
                a6_por_barragem[b["id_snisb"]] = {
                    "dist": dist,
                    "cota_cm": cota,
                    "vazao_m3s": vazao,
                    "cota_alerta_cm": alerta,
                    "razao": razao,
                    "codigo_estacao": cod,
                    "data_ultima": row["data_ultima"],
                    "relacao": row["relacao"],
                }

    gravar_csv(SAIDA, saidas, campos)

    # Mescla no hidro: preenche cota/vazão; só sobrescreve razão A6 se medida.
    hidro = ler_csv(HIDRO)
    if hidro:
        campos_h = list(hidro[0].keys())
        for col in (
            "cota_cm",
            "vazao_m3s",
            "cota_alerta_cm",
            "codigo_estacao_ana_ref",
            "a6_fonte",
            "data_cota_ana",
        ):
            if col not in campos_h:
                campos_h.append(col)
        # Índice rank=1 para preenchimento de contexto
        rank1 = {
            s["id_snisb"]: s
            for s in saidas
            if int(s.get("rank") or 0) == 1
        }
        novos = []
        n_medido = 0
        for h in hidro:
            bid = norm_id(h.get("id_snisb"))
            a6 = a6_por_barragem.get(bid)
            h = dict(h)
            s = rank1.get(bid)
            if a6 is not None:
                h["cota_cm"] = fmt(a6["cota_cm"], 1)
                h["vazao_m3s"] = (
                    fmt(a6["vazao_m3s"], 2) if a6["vazao_m3s"] is not None else ""
                )
                h["cota_alerta_cm"] = fmt(a6["cota_alerta_cm"], 1)
                h["razao_nivel_cota_alerta"] = fmt(a6["razao"], 3)
                h["codigo_estacao_ana_ref"] = a6["codigo_estacao"]
                h["data_cota_ana"] = a6["data_ultima"]
                h["a6_fonte"] = "cota_medida"
                n_medido += 1
            else:
                if s:
                    h["cota_cm"] = s.get("cota_cm") or ""
                    h["vazao_m3s"] = s.get("vazao_m3s") or ""
                    h["cota_alerta_cm"] = s.get("cota_alerta_cm") or ""
                    h["codigo_estacao_ana_ref"] = s.get("codigo_estacao") or ""
                    h["data_cota_ana"] = s.get("data_ultima") or ""
                # Nunca preservar cota_medida sem elegibilidade espacial nesta corrida.
                if h.get("a6_fonte") == "cota_medida":
                    h["razao_nivel_cota_alerta"] = ""
                if s and s.get("cota_cm"):
                    h["a6_fonte"] = "contexto_somente"
                elif s:
                    h["a6_fonte"] = "sem_cota_alerta"
                else:
                    h["a6_fonte"] = ""
            novos.append(h)
        gravar_csv(HIDRO, novos, campos_h)
    else:
        n_medido = 0

    n_piloto = sum(1 for s in saidas if s.get("piloto_eixo") == "1")
    n_com_cota = sum(1 for s in saidas if s.get("cota_cm"))
    md = [
        "# Estações ANA por barragem",
        "",
        f"- Fonte estações: `{fonte_est}`",
        f"- Fonte telemetria: `{fonte_tel}`",
        f"- Vínculos gerados: **{len(saidas)}** (até {N_POR_BARRAGEM} por barragem, ≤{MAX_DIST_KM:.0f} km)",
        f"- No piloto Manso–Cuiabá: **{n_piloto}** linhas",
        f"- Com cota na última leitura: **{n_com_cota}**",
        f"- A6 com razão medida (cota/cota_alerta) mesclada no hidro: **{n_medido}** barragens",
        "",
        "## Fronteira",
        "",
        "Telemetria de rio **não** altera a geometria da mancha (Circular / Trajeto / HAND).",
        "Uso: contexto operacional na Simulação e indicador A6 do IDAP quando houver cota de alerta.",
        "",
        f"Arquivo: `{SAIDA.name}`",
    ]
    REL.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"escrito {SAIDA.relative_to(comum.RAIZ)} ({len(saidas)} linhas)")
    print(f"hidro A6 medido em {n_medido} barragens")
    print(f"escrito {REL.relative_to(comum.RAIZ)}")


if __name__ == "__main__":
    main()
