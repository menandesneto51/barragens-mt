"""Previsão de chuva e contexto Copernicus (ECMWF / GloFAS) via Open-Meteo.

Não exige chave. ECMWF IFS alimenta o Copernicus C3S; GloFAS é o sistema global
de cheias do Copernicus EMS. Sentinel EMS Rapid Mapping continua dependente de
acionamento autorizado (Defesa Civil) — fora do escopo deste coletor.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


UA = "VIGIBARRAGENS-MT/1.0 (SES-MT; monitoramento-barragens)"


def _get_json(url: str, timeout: int = 60) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def previsao_chuva_lote(
    pontos: list[tuple[str, float, float]],
    *,
    dias: int = 3,
) -> dict[str, dict[str, Any]]:
    """Chuva prevista 24–72 h (ECMWF IFS) por código IBGE.

    `pontos`: lista (cod_ibge, lat, lon). Open-Meteo aceita até ~100 coords/request.
    """
    if not pontos:
        return {}
    saida: dict[str, dict[str, Any]] = {}
    for i in range(0, len(pontos), 40):
        lote = pontos[i : i + 40]
        lats = ",".join(f"{p[1]:.4f}" for p in lote)
        lons = ",".join(f"{p[2]:.4f}" for p in lote)
        for modelo in ("ecmwf_ifs025", ""):
            q = {
                "latitude": lats,
                "longitude": lons,
                "daily": "precipitation_sum",
                "forecast_days": str(dias),
                "timezone": "America/Cuiaba",
            }
            if modelo:
                q["models"] = modelo
            url = f"https://api.open-meteo.com/v1/forecast?{urllib.parse.urlencode(q)}"
            try:
                raw = _get_json(url)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                print(f"  aviso Open-Meteo ({modelo or 'default'}): {exc}")
                continue
            itens = raw if isinstance(raw, list) else [raw]
            ok = False
            for ponto, item in zip(lote, itens):
                if item.get("error"):
                    continue
                daily = item.get("daily") or {}
                precip = daily.get("precipitation_sum") or []
                datas = daily.get("time") or []
                if not precip:
                    continue
                vals = [float(x or 0) for x in precip[:dias]]
                saida[ponto[0]] = {
                    "chuva_prevista_24_72h_mm": round(sum(vals), 2),
                    "chuva_prevista_detalhe_mm": "|".join(f"{v:.1f}" for v in vals),
                    "datas_previsao": "|".join(datas[:dias]),
                    "fonte_previsao": f"openmeteo_{modelo or 'best_match'}",
                    "modelo": modelo or "best_match",
                }
                ok = True
            if ok:
                break
    return saida


def risco_cheias_glofas(
    pontos: list[tuple[str, float, float]],
) -> dict[str, dict[str, Any]]:
    """Descarga fluvial prevista (GloFAS / Copernicus EMS) — contexto regional.

    API pública Open-Meteo Flood. Nem todo ponto tem rio modelado; falhas são
    silenciosas por município.
    """
    if not pontos:
        return {}
    saida: dict[str, dict[str, Any]] = {}
    for cod, lat, lon in pontos[:80]:  # limitar volume de requests
        params = urllib.parse.urlencode(
            {
                "latitude": f"{lat:.4f}",
                "longitude": f"{lon:.4f}",
                "daily": "river_discharge",
                "forecast_days": "3",
                "timezone": "America/Cuiaba",
            }
        )
        url = f"https://flood-api.open-meteo.com/v1/flood?{params}"
        try:
            item = _get_json(url, timeout=30)
        except Exception:
            continue
        daily = item.get("daily") or {}
        vals = [float(x) for x in (daily.get("river_discharge") or []) if x is not None]
        if not vals:
            continue
        saida[cod] = {
            "vazao_prevista_max_m3s": round(max(vals), 2),
            "vazao_prevista_media_m3s": round(sum(vals) / len(vals), 2),
            "fonte_glofas": "openmeteo_glofas_copernicus_ems",
        }
    return saida
