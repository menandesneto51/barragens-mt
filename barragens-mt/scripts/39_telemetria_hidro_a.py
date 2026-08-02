"""Telemetria pontual para dimensão A do IDAP (chuva no ponto da barragem).

Enriquece `hidro_barragens_mt.csv` com série no coordenada da barragem:
  - Open-Meteo forecast + past_days (proxy IMERG/modelo quando estação local falha)
  - INMET estações automáticas próximas (API pública), quando responder
  - Preserva alertas Cemaden/INMET/ANA já presentes no hidro municipal

Saídas:
  dados/tratados/telemetria_hidro_a.csv          — overlay por barragem
  dados/tratados/hidro_barragens_mt.csv          — mesclado (campos A1–A4 atualizados)
  relatorios/telemetria_hidro_a.md

Uso:
  python scripts/39_telemetria_hidro_a.py
  python executar.py 39
"""

from __future__ import annotations

import csv
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import comum

HIDRO = comum.DADOS_TRATADOS / "hidro_barragens_mt.csv"
INVENTARIO = comum.DADOS_TRATADOS / "inventario_barragens_mt.csv"
PILOTO = comum.DADOS_TRATADOS / "piloto_manso_cuiaba.csv"
SAIDA_OVERLAY = comum.DADOS_TRATADOS / "telemetria_hidro_a.csv"
REL = comum.RELATORIOS / "telemetria_hidro_a.md"

UA = "VIGIBARRAGENS-MT/1.0 (SES-MT; telemetria dimensao A)"
INMET_ESTACOES = "https://apitempo.inmet.gov.br/estacoes/T"
# Dados horários recentes (pode exigir CORS/rede institucional)
INMET_DADOS = "https://apitempo.inmet.gov.br/estacao/diaria/{inicio}/{fim}/{codigo}"


def _get_json(url: str, timeout: int = 45) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _num(v: Any) -> float | None:
    if v is None:
        return None
    s = str(v).strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
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


def ids_piloto() -> set[str]:
    return {
        (r.get("id_snisb") or "").strip()
        for r in ler_csv(PILOTO)
        if (r.get("id_snisb") or "").strip()
    }


def inventario_coords() -> dict[str, dict[str, Any]]:
    piloto = ids_piloto()
    out: dict[str, dict[str, Any]] = {}
    for r in ler_csv(INVENTARIO):
        bid = (r.get("id_snisb") or "").strip()
        if not bid:
            continue
        la, lo = _num(r.get("latitude")), _num(r.get("longitude"))
        if la is None or lo is None:
            continue
        out[bid] = {
            "id_snisb": bid,
            "nome": r.get("nome") or "",
            "municipio": r.get("municipio") or "",
            "latitude": la,
            "longitude": lo,
            "piloto": bid in piloto,
        }
    return out


def _parse_openmeteo_daily(item: dict[str, Any]) -> dict[str, Any] | None:
    daily = item.get("daily") or {}
    precip = [float(x or 0) for x in (daily.get("precipitation_sum") or [])]
    datas = list(daily.get("time") or [])
    if len(precip) < 3:
        return None
    obs = precip[:3]
    fut = precip[3:6] if len(precip) > 3 else []
    chuva_24 = obs[-1] if obs else 0.0
    chuva_72 = sum(obs)
    prev = sum(fut) if fut else None
    if chuva_24 >= 50:
        pct = 95.0
    elif chuva_24 >= 30:
        pct = 85.0
    elif chuva_24 >= 15:
        pct = 70.0
    elif chuva_24 >= 5:
        pct = 55.0
    else:
        pct = 30.0
    dias_int = 0
    for v in reversed(obs):
        if v >= 10:
            dias_int += 1
        else:
            break
    return {
        "chuva_24h_mm": round(chuva_24, 2),
        "chuva_72h_mm": round(chuva_72, 2),
        "chuva_prevista_24_72h_mm": round(prev, 2) if prev is not None else "",
        "percentil_climatologico": pct,
        "dias_consecutivos_chuva_intensa": dias_int,
        "data_referencia": datas[2] if len(datas) >= 3 else date.today().isoformat(),
        "fonte_precip": "openmeteo_ponto",
        "fonte_previsao": "openmeteo_ponto" if prev is not None else "",
        "datas_serie": "|".join(datas[:6]),
        "serie_mm": "|".join(f"{v:.1f}" for v in precip[:6]),
    }


def openmeteo_lote(
    pontos: list[tuple[str, float, float]],
) -> dict[str, dict[str, Any]]:
    """Chuva observada recente + prevista via Open-Meteo (modelo / proxy IMERG)."""
    saida: dict[str, dict[str, Any]] = {}
    for i in range(0, len(pontos), 40):
        lote = pontos[i : i + 40]
        lats = ",".join(f"{p[1]:.4f}" for p in lote)
        lons = ",".join(f"{p[2]:.4f}" for p in lote)
        q = urllib.parse.urlencode(
            {
                "latitude": lats,
                "longitude": lons,
                "daily": "precipitation_sum",
                "past_days": "3",
                "forecast_days": "3",
                "timezone": "America/Cuiaba",
            }
        )
        url = f"https://api.open-meteo.com/v1/forecast?{q}"
        try:
            raw = _get_json(url)
        except Exception as exc:  # noqa: BLE001
            print(f"    Open-Meteo lote falhou: {exc}")
            time.sleep(2)
            continue
        itens = raw if isinstance(raw, list) else [raw]
        for ponto, item in zip(lote, itens):
            if not isinstance(item, dict) or item.get("error"):
                continue
            parsed = _parse_openmeteo_daily(item)
            if parsed:
                saida[ponto[0]] = parsed
        time.sleep(0.4)
    return saida


def carregar_estacoes_inmet() -> list[dict[str, Any]]:
    try:
        raw = _get_json(INMET_ESTACOES, timeout=60)
    except Exception as exc:  # noqa: BLE001
        print(f"  INMET estações indisponível: {exc}")
        return []
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for e in raw:
        uf = (e.get("SG_ESTADO") or e.get("UF") or "").upper()
        if uf and uf != "MT":
            continue
        la = _num(e.get("VL_LATITUDE") or e.get("latitude"))
        lo = _num(e.get("VL_LONGITUDE") or e.get("longitude"))
        cod = (e.get("CD_ESTACAO") or e.get("codigo") or "").strip()
        if la is None or lo is None or not cod:
            continue
        out.append(
            {
                "codigo": cod,
                "nome": e.get("DC_NOME") or e.get("nome") or cod,
                "lat": la,
                "lon": lo,
            }
        )
    print(f"  INMET estações MT: {len(out)}")
    return out


def chuva_inmet_estacao(codigo: str) -> dict[str, Any] | None:
    fim = date.today()
    inicio = fim - timedelta(days=4)
    url = INMET_DADOS.format(
        inicio=inicio.isoformat(), fim=fim.isoformat(), codigo=codigo
    )
    try:
        raw = _get_json(url, timeout=40)
    except Exception:
        return None
    if not isinstance(raw, list) or not raw:
        return None
    por_dia: dict[str, float] = {}
    for row in raw:
        dia = (row.get("DT_MEDICAO") or row.get("data") or "")[:10]
        prec = _num(row.get("CHUVA") or row.get("PRECIPITACAO") or row.get("precipitacao"))
        if not dia or prec is None:
            continue
        por_dia[dia] = por_dia.get(dia, 0.0) + prec
    if not por_dia:
        return None
    dias = sorted(por_dia)
    ultima = dias[-1]
    chuva_24 = por_dia[ultima]
    ult3 = dias[-3:]
    chuva_72 = sum(por_dia[d] for d in ult3)
    dias_int = 0
    for d in reversed(dias):
        if por_dia[d] >= 10:
            dias_int += 1
        else:
            break
    return {
        "chuva_24h_mm": round(chuva_24, 2),
        "chuva_72h_mm": round(chuva_72, 2),
        "data_referencia": ultima,
        "dias_consecutivos_chuva_intensa": dias_int,
        "fonte_precip": f"inmet_{codigo}",
        "estacao_inmet": codigo,
    }


def estacao_mais_proxima(
    lat: float, lon: float, estacoes: list[dict[str, Any]], raio_km: float = 80.0
) -> dict[str, Any] | None:
    melhor = None
    dmin = raio_km
    for e in estacoes:
        d = haversine_km(lat, lon, e["lat"], e["lon"])
        if d <= dmin:
            dmin = d
            melhor = {**e, "dist_km": round(d, 1)}
    return melhor


def main() -> None:
    comum.preparar_diretorios()
    hidro = ler_csv(HIDRO)
    if not hidro:
        raise SystemExit("hidro_barragens_mt.csv ausente — rode etapa 17 antes")
    coords = inventario_coords()
    print(f"Inventário com coordenada: {len(coords)}; hidro: {len(hidro)}", flush=True)

    # Prioriza piloto + amostra estadual (limite de API)
    ids_p = [b for b, c in coords.items() if c.get("piloto")]
    # Amostra estadual: uma barragem por município fora do piloto (até 40)
    vistos_mun: set[str] = set()
    ids_resto: list[str] = []
    for b, c in coords.items():
        if c.get("piloto"):
            continue
        mun = (c.get("municipio") or "").casefold()
        if mun in vistos_mun:
            continue
        vistos_mun.add(mun)
        ids_resto.append(b)
        if len(ids_resto) >= 40:
            break
    alvos = ids_p + ids_resto
    print(f"Telemetria pontual para {len(alvos)} barragens (piloto={len(ids_p)})", flush=True)

    estacoes = carregar_estacoes_inmet()
    print("  Open-Meteo em lote…", flush=True)
    om_por_id = openmeteo_lote(
        [(b, coords[b]["latitude"], coords[b]["longitude"]) for b in alvos]
    )
    print(f"  Open-Meteo ok: {len(om_por_id)}", flush=True)

    # Cache de séries INMET por código de estação
    cache_inmet: dict[str, dict[str, Any] | None] = {}
    overlay: dict[str, dict[str, Any]] = {}
    n_inmet = 0
    n_om = len(om_por_id)

    for i, bid in enumerate(alvos):
        c = coords[bid]
        la, lo = c["latitude"], c["longitude"]
        row: dict[str, Any] = {
            "id_snisb": bid,
            "nome": c["nome"],
            "municipio": c["municipio"],
            "latitude": f"{la:.6f}",
            "longitude": f"{lo:.6f}",
            "fonte_precip": "",
            "fonte_previsao": "",
            "chuva_24h_mm": "",
            "chuva_72h_mm": "",
            "chuva_prevista_24_72h_mm": "",
            "percentil_climatologico": "",
            "dias_consecutivos_chuva_intensa": "",
            "data_referencia": "",
            "estacao_inmet": "",
            "dist_estacao_km": "",
            "serie_mm": "",
            "datas_serie": "",
        }
        usado = None
        est = estacao_mais_proxima(la, lo, estacoes) if estacoes else None
        if est:
            cod = est["codigo"]
            if cod not in cache_inmet:
                cache_inmet[cod] = chuva_inmet_estacao(cod)
                time.sleep(0.2)
            dados = cache_inmet[cod]
            if dados:
                usado = dados
                row["estacao_inmet"] = cod
                row["dist_estacao_km"] = est["dist_km"]
                n_inmet += 1
        om = om_por_id.get(bid)
        if om:
            if usado is None:
                usado = om
            else:
                row["chuva_prevista_24_72h_mm"] = om.get("chuva_prevista_24_72h_mm") or ""
                row["fonte_previsao"] = om.get("fonte_previsao") or ""
                row["percentil_climatologico"] = om.get("percentil_climatologico") or ""
                row["serie_mm"] = om.get("serie_mm") or ""
                row["datas_serie"] = om.get("datas_serie") or ""
        if usado:
            for k in (
                "chuva_24h_mm",
                "chuva_72h_mm",
                "data_referencia",
                "dias_consecutivos_chuva_intensa",
                "fonte_precip",
            ):
                if usado.get(k) not in (None, ""):
                    row[k] = usado[k]
            if not row.get("chuva_prevista_24_72h_mm") and om:
                row["chuva_prevista_24_72h_mm"] = om.get("chuva_prevista_24_72h_mm") or ""
                row["fonte_previsao"] = om.get("fonte_previsao") or ""
            if not row.get("percentil_climatologico") and om:
                row["percentil_climatologico"] = om.get("percentil_climatologico") or ""
            if om and not row.get("serie_mm"):
                row["serie_mm"] = om.get("serie_mm") or ""
                row["datas_serie"] = om.get("datas_serie") or ""
        overlay[bid] = row
        if (i + 1) % 25 == 0:
            print(f"  … {i+1}/{len(alvos)}", flush=True)

    # Grava overlay
    cols_ov = [
        "id_snisb",
        "nome",
        "municipio",
        "latitude",
        "longitude",
        "chuva_24h_mm",
        "chuva_72h_mm",
        "chuva_prevista_24_72h_mm",
        "percentil_climatologico",
        "dias_consecutivos_chuva_intensa",
        "data_referencia",
        "fonte_precip",
        "fonte_previsao",
        "estacao_inmet",
        "dist_estacao_km",
        "serie_mm",
        "datas_serie",
    ]
    comum.salvar_csv(SAIDA_OVERLAY, [overlay[b] for b in alvos if b in overlay], cols_ov)

    # Mescla no hidro: atualiza A1–A4 quando overlay tem fonte_precip
    n_merge = 0
    if hidro:
        campos = list(hidro[0].keys())
        for extra in (
            "fonte_telemetria_a",
            "estacao_inmet",
            "dist_estacao_km",
        ):
            if extra not in campos:
                campos.append(extra)
        novo: list[dict[str, Any]] = []
        for h in hidro:
            bid = (h.get("id_snisb") or "").strip()
            o = overlay.get(bid)
            row = {k: h.get(k, "") for k in campos}
            if o and o.get("fonte_precip"):
                row["chuva_24h_mm"] = o["chuva_24h_mm"]
                row["chuva_72h_mm"] = o["chuva_72h_mm"]
                if o.get("chuva_prevista_24_72h_mm") not in ("", None):
                    row["chuva_prevista_24_72h_mm"] = o["chuva_prevista_24_72h_mm"]
                if o.get("percentil_climatologico") not in ("", None):
                    row["percentil_climatologico"] = o["percentil_climatologico"]
                if o.get("dias_consecutivos_chuva_intensa") not in ("", None):
                    row["dias_consecutivos_chuva_intensa"] = o[
                        "dias_consecutivos_chuva_intensa"
                    ]
                if o.get("data_referencia"):
                    row["data_referencia"] = o["data_referencia"]
                row["fonte_precip"] = o["fonte_precip"]
                if o.get("fonte_previsao"):
                    row["fonte_previsao"] = o["fonte_previsao"]
                row["fonte_telemetria_a"] = o["fonte_precip"]
                row["estacao_inmet"] = o.get("estacao_inmet") or ""
                row["dist_estacao_km"] = o.get("dist_estacao_km") or ""
                # Aproximação espacial passa a ser pontual
                row["aproximacao_espacial"] = "ponto_barragem_telemetria"
                n_merge += 1
            else:
                row.setdefault("fonte_telemetria_a", "")
                row.setdefault("estacao_inmet", "")
                row.setdefault("dist_estacao_km", "")
            novo.append(row)
        comum.salvar_csv(HIDRO, novo, campos)

    REL.write_text(
        "\n".join(
            [
                "# Telemetria pontual — dimensão A (IDAP)",
                "",
                f"- Extração: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
                f"- Overlay: `{SAIDA_OVERLAY.relative_to(comum.RAIZ)}` ({len(overlay)} barragens)",
                f"- Mesclados em hidro: **{n_merge}**",
                f"- Com série INMET próxima: **{n_inmet}**",
                f"- Com Open-Meteo no ponto: **{n_om}**",
                "",
                "Prioridade: estação INMET ≤80 km → senão Open-Meteo no ponto da barragem.",
                "Alertas Cemaden/INMET/ANA do SisClima municipal são preservados.",
                "Reexecute etapa 16 (IDAP) após esta para recalcular A1–A7 com os novos valores.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"  gravado {REL.relative_to(comum.RAIZ)}")
    print(f"  merge={n_merge} inmet={n_inmet} openmeteo={n_om}")


if __name__ == "__main__":
    main()
