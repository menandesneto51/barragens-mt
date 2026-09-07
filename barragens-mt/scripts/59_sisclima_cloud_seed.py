"""Monta `sis_cloud_seed.db` operacional para Solo / alertas / ANA.

O clone público do SisClima só traz `sis_integrado.db` sanitizado (calor/epi),
sem `precipitacao_mm`, `solo_saturacao_municipal`, `cemaden_alertas`,
`inmet_alertas` nem `ana_*`. O seed institucional CIEVS (OneDrive) com
`USE_ANA=true` + `ANA_FETCH_SERIES=true` continua preferido quando presente.

Esta etapa recria o contrato esperado pela etapa 17 a partir de fontes públicas:
  - precipitação + saturação proxy (Open-Meteo)
  - alertas INMET (`apiprevmet3`)
  - alertas Cemaden (`painelalertas.cemaden.gov.br/wsAlertas2`)
  - estações + séries ANA (SOAP telemetriaws1 — equivalente a USE_ANA + FETCH_SERIES)

Saídas:
  dados/brutos/sisclima/sis_cloud_seed.db
  dados/tratados/sisclima_cloud_seed_status.json
  relatorios/sisclima_cloud_seed.md
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import comum
from previsao_copernicus import precip_observada_lote

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

UA = "VIGIBARRAGENS-MT/1.0 (SES-MT; sis_cloud_seed)"
SAIDA_DB = comum.DADOS_BRUTOS / "sisclima" / "sis_cloud_seed.db"
SAIDA_STATUS = comum.DADOS_TRATADOS / "sisclima_cloud_seed_status.json"
SAIDA_MD = comum.RELATORIOS / "sisclima_cloud_seed.md"

BBOX_MT = comum.BBOX_MT  # (lon_min, lat_min, lon_max, lat_max)

# Estações prioritárias do eixo Manso–Cuiabá + inventário sample.
PRIORIDADE_ANA = [
    "66260006",  # CUIABÁ-BEIRA RIO
    "66210000",  # UHE MANSO JUSANTE
    "66162000",  # UHE MANSO MONTANTE
    "01455013",  # UHE MANSO MET
    "66240060",
    "66240080",
    "66171400",
    "66171500",
    "66174000",
    "66260001",
    "66340500",
]

INMET_SEVERIDADE = {
    "perigo potencial": "amarelo",
    "perigo": "laranja",
    "grande perigo": "vermelho",
    "observação": "verde",
    "observacao": "verde",
}

CEMADEN_NIVEL = {
    "moderado": "amarelo",
    "alto": "laranja",
    "muito alto": "vermelho",
    "baixo": "verde",
}


def _get_json(url: str, timeout: int = 45) -> Any:
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _ibge7(valor: Any) -> str:
    texto = str(valor or "").strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    digitos = "".join(c for c in texto if c.isdigit())
    return digitos[:7] if len(digitos) >= 7 else digitos


def _num(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(str(v).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None


def candidatos_sis_integrado() -> list[Path]:
    env = os.environ.get("VIGIBARRAGENS_SISCLIMA_DB")
    out: list[Path] = []
    if env:
        out.append(Path(env))
    out.extend(
        [
            comum.RAIZ.parent / "sisclima-repo" / "data" / "output" / "sis_integrado.db",
            comum.DADOS_BRUTOS / "sisclima" / "sis_integrado.db",
        ]
    )
    return out


def carregar_municipios_mt() -> list[dict[str, Any]]:
    """Coords municipais a partir do SisClima sanitizado (met/resumo)."""
    for db in candidatos_sis_integrado():
        if not db.is_file() or db.stat().st_size <= 0:
            continue
        con = sqlite3.connect(str(db))
        try:
            nomes = {
                r[0]
                for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            rows: list[dict[str, Any]] = []
            if "resumo_municipal_atual" in nomes:
                for cod, mun, lat, lon in con.execute(
                    "SELECT cod_ibge, municipio, lat, lon FROM resumo_municipal_atual "
                    "WHERE lat IS NOT NULL AND lon IS NOT NULL"
                ):
                    chave = _ibge7(cod)
                    if chave.startswith("51"):
                        rows.append(
                            {
                                "cod_ibge": chave,
                                "municipio": mun or "",
                                "lat": float(lat),
                                "lon": float(lon),
                            }
                        )
            elif "met_biometeo" in nomes:
                vistos: set[str] = set()
                for cod, mun, lat, lon in con.execute(
                    "SELECT cod_ibge, municipio, lat, lon FROM met_biometeo "
                    "WHERE lat IS NOT NULL AND lon IS NOT NULL"
                ):
                    chave = _ibge7(cod)
                    if not chave.startswith("51") or chave in vistos:
                        continue
                    vistos.add(chave)
                    rows.append(
                        {
                            "cod_ibge": chave,
                            "municipio": mun or "",
                            "lat": float(lat),
                            "lon": float(lon),
                        }
                    )
            if rows:
                return rows
        finally:
            con.close()
    raise SystemExit(
        "não achei municípios MT no sis_integrado.db — clone SisClima ou defina "
        "VIGIBARRAGENS_SISCLIMA_DB"
    )


def solo_openmeteo(
    pontos: list[tuple[str, float, float]],
) -> dict[str, dict[str, Any]]:
    """Saturação proxy 0–100 a partir de soil_moisture_0_to_7cm (m³/m³)."""
    saida: dict[str, dict[str, Any]] = {}
    hoje = date.today().isoformat()
    for i in range(0, len(pontos), 40):
        lote = pontos[i : i + 40]
        lats = ",".join(f"{p[1]:.4f}" for p in lote)
        lons = ",".join(f"{p[2]:.4f}" for p in lote)
        q = {
            "latitude": lats,
            "longitude": lons,
            "hourly": "soil_moisture_0_to_7cm",
            "past_days": "1",
            "forecast_days": "1",
            "timezone": "America/Cuiaba",
        }
        url = f"https://api.open-meteo.com/v1/forecast?{urllib.parse.urlencode(q)}"
        try:
            raw = _get_json(url)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"  aviso solo Open-Meteo: {exc}")
            continue
        itens = raw if isinstance(raw, list) else [raw]
        for ponto, item in zip(lote, itens):
            if item.get("error"):
                continue
            hourly = item.get("hourly") or {}
            vals = [v for v in (hourly.get("soil_moisture_0_to_7cm") or []) if v is not None]
            if not vals:
                continue
            umid = float(sum(vals) / len(vals))
            # capacidade de campo ~0.40 m³/m³ → índice 0–100
            idx = max(0.0, min(100.0, (umid / 0.40) * 100.0))
            if idx < 35:
                classe = "baixa"
            elif idx < 60:
                classe = "moderada"
            elif idx < 80:
                classe = "alta"
            else:
                classe = "muito_alta"
            saida[ponto[0]] = {
                "data": hoje,
                "indice_saturacao_solo": round(idx, 1),
                "classe_saturacao_solo": classe,
                "fonte_solo": "openmeteo_soil_proxy",
                "soil_moisture_m3m3": round(umid, 4),
            }
    return saida


def fetch_inmet_mt(municipios: dict[str, str]) -> list[dict[str, Any]]:
    """Alertas INMET ativos com geocode MT."""
    try:
        raw = _get_json("https://apiprevmet3.inmet.gov.br/avisos/ativos")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"  aviso INMET: {exc}")
        return []
    avisos = list(raw.get("hoje") or []) + list(raw.get("futuro") or [])
    out: list[dict[str, Any]] = []
    vistos: set[tuple[str, str]] = set()
    for aviso in avisos:
        geocodes = str(aviso.get("geocodes") or "")
        for cod in geocodes.split(","):
            chave = _ibge7(cod)
            if not chave.startswith("51"):
                continue
            evento = str(aviso.get("descricao") or "").strip()
            chave_unica = (chave, evento)
            if chave_unica in vistos:
                continue
            vistos.add(chave_unica)
            sev = str(aviso.get("severidade") or "").strip().lower()
            nivel = INMET_SEVERIDADE.get(sev, sev or "amarelo")
            riscos = aviso.get("riscos") or []
            desc = "; ".join(str(x) for x in riscos[:2]) if isinstance(riscos, list) else str(riscos)
            out.append(
                {
                    "cod_ibge": chave,
                    "municipio": municipios.get(chave) or "",
                    "nivel_alerta": nivel,
                    "evento": evento,
                    "descricao": (desc or evento)[:400],
                    "severidade_inmet": aviso.get("severidade") or "",
                    "inicio": aviso.get("inicio") or "",
                    "fim": aviso.get("fim") or "",
                    "fonte": "inmet_apiprevmet3",
                }
            )
    return out


def fetch_cemaden() -> list[dict[str, Any]]:
    try:
        raw = _get_json("https://painelalertas.cemaden.gov.br/wsAlertas2")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"  aviso Cemaden: {exc}")
        return []
    out: list[dict[str, Any]] = []
    for a in raw.get("alertas") or []:
        uf = str(a.get("uf") or "").upper()
        chave = _ibge7(a.get("codibge"))
        if uf != "MT" and not chave.startswith("51"):
            continue
        nivel_raw = str(a.get("nivel") or "").strip()
        nivel_sis = CEMADEN_NIVEL.get(nivel_raw.lower(), nivel_raw.lower())
        evento = str(a.get("evento") or "")
        tipo = evento.split(" - ")[0].strip() if " - " in evento else "risco"
        out.append(
            {
                "cod_ibge": chave,
                "municipio": str(a.get("municipio") or ""),
                "tipo_risco": tipo,
                "evento": evento,
                "nivel_sis": nivel_sis,
                "nivel_alerta": nivel_sis,
                "fonte": "cemaden_wsAlertas2",
                "datahoracriacao": a.get("datahoracriacao") or "",
            }
        )
    return out


def _soap(action: str, body_inner: str, timeout: int = 90) -> str:
    envelope = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
        'xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        f"<soap:Body>{body_inner}</soap:Body></soap:Envelope>"
    )
    req = urllib.request.Request(
        "http://telemetriaws1.ana.gov.br/ServiceANA.asmx",
        data=envelope.encode("utf-8"),
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f"http://MRCS/{action}",
            "User-Agent": UA,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def _parse_tables(xml_txt: str) -> list[dict[str, str]]:
    rows = re.findall(r"<Table[^>]*>(.*?)</Table>", xml_txt, re.S)
    out: list[dict[str, str]] = []
    for row in rows:
        out.append(dict(re.findall(r"<(\w+)>([^<]*)</\1>", row)))
    return out


def fetch_ana_estacoes_mt() -> list[dict[str, Any]]:
    inner = (
        '<ListaEstacoesTelemetricas xmlns="http://MRCS/">'
        "<statusEstacoes></statusEstacoes><origem></origem>"
        "</ListaEstacoesTelemetricas>"
    )
    try:
        txt = _soap("ListaEstacoesTelemetricas", inner, timeout=120)
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"  aviso ANA inventário: {exc}")
        return []
    lon_min, lat_min, lon_max, lat_max = BBOX_MT
    out: list[dict[str, Any]] = []
    for f in _parse_tables(txt):
        lat = _num(f.get("Latitude"))
        lon = _num(f.get("Longitude"))
        if lat is None or lon is None:
            continue
        if not (lat_min <= lat <= lat_max and lon_min <= lon <= lon_max):
            continue
        out.append(
            {
                "codigo_estacao": str(f.get("CodEstacao") or "").strip(),
                "nome_estacao": str(f.get("NomeEstacao") or ""),
                "municipio": "",
                "uf": "MT",
                "cod_ibge": "",
                "lat": lat,
                "lon": lon,
                "nome_rio": str(f.get("NomeRio") or ""),
                "origem": str(f.get("Origem") or ""),
                "status": str(f.get("StatusEstacao") or ""),
                "fonte": "ana_soap_lista",
            }
        )
    return out


def fetch_ana_telemetria(
    codigos: list[str],
    *,
    dias: int = 7,
) -> list[dict[str, Any]]:
    d1 = (date.today() - timedelta(days=dias)).strftime("%d/%m/%Y")
    d2 = date.today().strftime("%d/%m/%Y")
    out: list[dict[str, Any]] = []
    for cod in codigos:
        if not cod:
            continue
        inner = (
            f'<DadosHidrometeorologicos xmlns="http://MRCS/">'
            f"<codEstacao>{cod}</codEstacao>"
            f"<dataInicio>{d1}</dataInicio><dataFim>{d2}</dataFim>"
            f"</DadosHidrometeorologicos>"
        )
        try:
            txt = _soap("DadosHidrometeorologicos", inner, timeout=60)
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"  aviso ANA série {cod}: {exc}")
            continue
        if "Sem dados" in txt:
            continue
        # rows named DadosHidrometereologicos (typo in ANA schema)
        blocos = re.findall(
            r"<DadosHidrometereologicos[^>]*>(.*?)</DadosHidrometereologicos>",
            txt,
            re.S,
        )
        for bloco in blocos:
            campos = dict(re.findall(r"<(\w+)>([^<]*)</\1>", bloco))
            data_hora = str(campos.get("DataHora") or "").strip()
            out.append(
                {
                    "data": data_hora[:10],
                    "data_hora": data_hora,
                    "codigo_estacao": str(campos.get("CodEstacao") or cod).strip(),
                    "municipio": "",
                    "cod_ibge": "",
                    "chuva_mm": _num(campos.get("Chuva")),
                    "cota_cm": _num(campos.get("Nivel")),
                    "vazao_m3s": _num(campos.get("Vazao")),
                    "cota_alerta_cm": None,
                    "fonte": "ana_soap_series",
                }
            )
    return out


def montar_hidro_risco(
    estacoes: list[dict[str, Any]],
    tele: list[dict[str, Any]],
    municipios: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Snapshot municipal a partir da última leitura ANA (proxy estágio)."""
    ultima: dict[str, dict[str, Any]] = {}
    for row in tele:
        cod = row["codigo_estacao"]
        ant = ultima.get(cod)
        if ant is None or str(row.get("data_hora") or "") >= str(ant.get("data_hora") or ""):
            ultima[cod] = row

    def nearest_ibge(lat: float, lon: float) -> tuple[str, str]:
        best = ("", "")
        best_d = 1e18
        for m in municipios:
            dlat = float(m["lat"]) - lat
            dlon = float(m["lon"]) - lon
            d = dlat * dlat + dlon * dlon
            if d < best_d:
                best_d = d
                best = (m["cod_ibge"], m["municipio"])
        return best

    out: list[dict[str, Any]] = []
    vistos_ibge: set[str] = set()
    for est in estacoes:
        cod = est["codigo_estacao"]
        ult = ultima.get(cod)
        if not ult:
            continue
        cota = ult.get("cota_cm")
        vazao = ult.get("vazao_m3s")
        alerta = ult.get("cota_alerta_cm")
        nivel = ""
        if cota is not None and alerta is not None and alerta > 0:
            razao = cota / alerta
            if razao >= 1.2:
                nivel = "vermelho"
            elif razao >= 1.0:
                nivel = "laranja"
            elif razao >= 0.8:
                nivel = "amarelo"
            else:
                nivel = "verde"
        elif cota is not None:
            nivel = "verde"
        ibge, mun = nearest_ibge(float(est["lat"]), float(est["lon"]))
        if not ibge or ibge in vistos_ibge:
            continue
        vistos_ibge.add(ibge)
        out.append(
            {
                "cod_ibge": ibge,
                "municipio": mun,
                "data": ult.get("data") or date.today().isoformat(),
                "cota_cm": cota,
                "vazao_m3s": vazao,
                "nivel_alerta_hidro": nivel,
                "codigo_estacao": cod,
                "fonte": "ana_soap_series",
            }
        )
    return out


def carregar_cotas_alerta_local() -> dict[str, float]:
    from ana_sisclima_fontes import carregar_cotas_alerta

    return carregar_cotas_alerta()


def gravar_seed(
    municipios: list[dict[str, Any]],
    precip: dict[str, list[dict[str, Any]]],
    solo: dict[str, dict[str, Any]],
    inmet: list[dict[str, Any]],
    cemaden: list[dict[str, Any]],
    ana_est: list[dict[str, Any]],
    ana_tel: list[dict[str, Any]],
    hidro: list[dict[str, Any]],
) -> None:
    SAIDA_DB.parent.mkdir(parents=True, exist_ok=True)
    if SAIDA_DB.exists():
        SAIDA_DB.unlink()
    con = sqlite3.connect(str(SAIDA_DB))
    try:
        con.executescript(
            """
            CREATE TABLE met_biometeo (
              data TEXT, municipio TEXT, cod_ibge TEXT, lat REAL, lon REAL,
              precipitacao_mm REAL, fonte TEXT
            );
            CREATE TABLE solo_saturacao_municipal (
              cod_ibge TEXT, municipio TEXT, data TEXT,
              indice_saturacao_solo REAL, classe_saturacao_solo TEXT, fonte_solo TEXT
            );
            CREATE TABLE inmet_alertas (
              cod_ibge TEXT, municipio TEXT, nivel_alerta TEXT, evento TEXT,
              descricao TEXT, severidade_inmet TEXT, inicio TEXT, fim TEXT, fonte TEXT
            );
            CREATE TABLE cemaden_alertas (
              cod_ibge TEXT, municipio TEXT, tipo_risco TEXT, evento TEXT,
              nivel_sis TEXT, nivel_alerta TEXT, fonte TEXT, datahoracriacao TEXT
            );
            CREATE TABLE ana_estacoes (
              codigo_estacao TEXT, nome_estacao TEXT, municipio TEXT, uf TEXT,
              cod_ibge TEXT, lat REAL, lon REAL, nome_rio TEXT, origem TEXT,
              status TEXT, fonte TEXT
            );
            CREATE TABLE ana_telemetria (
              data TEXT, data_hora TEXT, codigo_estacao TEXT, municipio TEXT,
              cod_ibge TEXT, chuva_mm REAL, cota_cm REAL, vazao_m3s REAL,
              cota_alerta_cm REAL, fonte TEXT
            );
            CREATE TABLE hidro_risco_municipal (
              cod_ibge TEXT, municipio TEXT, data TEXT, cota_cm REAL, vazao_m3s REAL,
              nivel_alerta_hidro TEXT, codigo_estacao TEXT, fonte TEXT
            );
            CREATE TABLE ana_risco_municipal (
              cod_ibge TEXT, municipio TEXT, data TEXT, cota_cm REAL, vazao_m3s REAL,
              nivel_alerta_hidro TEXT, codigo_estacao TEXT, fonte TEXT
            );
            """
        )
        mun_nome = {m["cod_ibge"]: m["municipio"] for m in municipios}
        met_rows = []
        for m in municipios:
            cod = m["cod_ibge"]
            for linha in precip.get(cod) or []:
                met_rows.append(
                    (
                        linha["data"],
                        m["municipio"],
                        cod,
                        m["lat"],
                        m["lon"],
                        linha["precip_mm"],
                        linha.get("fonte") or "openmeteo_sisclima_fallback",
                    )
                )
        con.executemany(
            "INSERT INTO met_biometeo VALUES (?,?,?,?,?,?,?)", met_rows
        )
        solo_rows = []
        for cod, s in solo.items():
            solo_rows.append(
                (
                    cod,
                    mun_nome.get(cod, ""),
                    s["data"],
                    s["indice_saturacao_solo"],
                    s["classe_saturacao_solo"],
                    s["fonte_solo"],
                )
            )
        con.executemany(
            "INSERT INTO solo_saturacao_municipal VALUES (?,?,?,?,?,?)", solo_rows
        )
        con.executemany(
            "INSERT INTO inmet_alertas VALUES (?,?,?,?,?,?,?,?,?)",
            [
                (
                    r["cod_ibge"],
                    r["municipio"],
                    r["nivel_alerta"],
                    r["evento"],
                    r["descricao"],
                    r.get("severidade_inmet") or "",
                    r.get("inicio") or "",
                    r.get("fim") or "",
                    r.get("fonte") or "",
                )
                for r in inmet
            ],
        )
        con.executemany(
            "INSERT INTO cemaden_alertas VALUES (?,?,?,?,?,?,?,?)",
            [
                (
                    r["cod_ibge"],
                    r["municipio"],
                    r["tipo_risco"],
                    r["evento"],
                    r["nivel_sis"],
                    r["nivel_alerta"],
                    r.get("fonte") or "",
                    r.get("datahoracriacao") or "",
                )
                for r in cemaden
            ],
        )
        con.executemany(
            "INSERT INTO ana_estacoes VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    e["codigo_estacao"],
                    e["nome_estacao"],
                    e.get("municipio") or "",
                    e.get("uf") or "MT",
                    e.get("cod_ibge") or "",
                    e["lat"],
                    e["lon"],
                    e.get("nome_rio") or "",
                    e.get("origem") or "",
                    e.get("status") or "",
                    e.get("fonte") or "",
                )
                for e in ana_est
            ],
        )
        con.executemany(
            "INSERT INTO ana_telemetria VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    t.get("data") or "",
                    t.get("data_hora") or "",
                    t["codigo_estacao"],
                    t.get("municipio") or "",
                    t.get("cod_ibge") or "",
                    t.get("chuva_mm"),
                    t.get("cota_cm"),
                    t.get("vazao_m3s"),
                    t.get("cota_alerta_cm"),
                    t.get("fonte") or "",
                )
                for t in ana_tel
            ],
        )
        for tabela in ("hidro_risco_municipal", "ana_risco_municipal"):
            con.executemany(
                f"INSERT INTO {tabela} VALUES (?,?,?,?,?,?,?,?)",
                [
                    (
                        h.get("cod_ibge") or "",
                        h.get("municipio") or "",
                        h.get("data") or "",
                        h.get("cota_cm"),
                        h.get("vazao_m3s"),
                        h.get("nivel_alerta_hidro") or "",
                        h.get("codigo_estacao") or "",
                        h.get("fonte") or "",
                    )
                    for h in hidro
                ],
            )
        con.commit()
    finally:
        con.close()


def selecionar_codigos_ana(estacoes: list[dict[str, Any]]) -> list[str]:
    por_cod = {e["codigo_estacao"]: e for e in estacoes if e.get("codigo_estacao")}
    escolhidos: list[str] = []
    for cod in PRIORIDADE_ANA:
        if cod in por_cod and cod not in escolhidos:
            escolhidos.append(cod)
    # reforço: RHN ativos no bbox (até 40)
    rhn = [
        e
        for e in estacoes
        if "RHN" in str(e.get("origem") or "").upper()
        and "Ativo" in str(e.get("status") or "")
    ]
    rhn.sort(key=lambda e: e["codigo_estacao"])
    for e in rhn:
        cod = e["codigo_estacao"]
        if cod not in escolhidos:
            escolhidos.append(cod)
        if len(escolhidos) >= 45:
            break
    return escolhidos


def main() -> None:
    comum.preparar_diretorios()
    print("SisClima cloud seed — montando contrato Solo/alertas/ANA")
    municipios = carregar_municipios_mt()
    mun_nome = {m["cod_ibge"]: m["municipio"] for m in municipios}
    pontos = [(m["cod_ibge"], m["lat"], m["lon"]) for m in municipios]
    print(f"  municípios MT: {len(municipios)}")

    print("  precipitação Open-Meteo…")
    precip = precip_observada_lote(pontos, past_days=3)
    print(f"  séries precip: {len(precip)}")

    print("  solo Open-Meteo (proxy TITAN)…")
    solo = solo_openmeteo(pontos)
    print(f"  solo municipal: {len(solo)}")

    print("  alertas INMET…")
    inmet = fetch_inmet_mt(mun_nome)
    print(f"  inmet_alertas MT: {len(inmet)}")

    print("  alertas Cemaden…")
    cemaden = fetch_cemaden()
    print(f"  cemaden_alertas MT: {len(cemaden)}")

    print("  ANA inventário telemetria (SOAP)…")
    ana_est = fetch_ana_estacoes_mt()
    print(f"  ana_estacoes no bbox MT: {len(ana_est)}")
    codigos = selecionar_codigos_ana(ana_est)
    print(f"  buscando séries para {len(codigos)} estações…")
    ana_tel = fetch_ana_telemetria(codigos, dias=7)
    cotas_alerta = carregar_cotas_alerta_local()
    if cotas_alerta:
        for row in ana_tel:
            alerta = cotas_alerta.get(row["codigo_estacao"])
            if alerta is not None:
                row["cota_alerta_cm"] = alerta
        print(f"  cotas de alerta aplicadas: {len(cotas_alerta)} estações (CSV sample/oficial)")
    n_est_com_serie = len({t["codigo_estacao"] for t in ana_tel})
    print(f"  ana_telemetria: {len(ana_tel)} leituras / {n_est_com_serie} estações")

    hidro = montar_hidro_risco(ana_est, ana_tel, municipios)
    gravar_seed(municipios, precip, solo, inmet, cemaden, ana_est, ana_tel, hidro)
    print(f"  gravado {SAIDA_DB}")

    status = {
        "gerado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "db": str(SAIDA_DB),
        "n_municipios": len(municipios),
        "n_met_biometeo_com_precip": sum(len(v) for v in precip.values()),
        "n_solo_saturacao": len(solo),
        "fonte_solo": "openmeteo_soil_proxy (não é TITAN institucional)",
        "n_inmet_alertas": len(inmet),
        "n_cemaden_alertas": len(cemaden),
        "n_ana_estacoes": len(ana_est),
        "n_ana_telemetria": len(ana_tel),
        "n_ana_estacoes_com_serie": n_est_com_serie,
        "equivalente_sisclima": {
            "USE_ANA": True,
            "ANA_FETCH_SERIES": True,
            "nota": (
                "Seed local via SOAP público ANA + INMET/Cemaden/Open-Meteo. "
                "Substitua por sis_cloud_seed.db do CIEVS (TITAN) quando disponível."
            ),
        },
        "tabelas": [
            "met_biometeo",
            "solo_saturacao_municipal",
            "inmet_alertas",
            "cemaden_alertas",
            "ana_estacoes",
            "ana_telemetria",
            "hidro_risco_municipal",
            "ana_risco_municipal",
        ],
    }
    SAIDA_STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    linhas = [
        "# SisClima cloud seed (operacional)",
        "",
        f"- Gerado: `{status['gerado_em']}`",
        f"- DB: `{SAIDA_DB}`",
        f"- Municípios: **{len(municipios)}**",
        f"- Solo (proxy Open-Meteo): **{len(solo)}**",
        f"- Alertas INMET (MT): **{len(inmet)}**",
        f"- Alertas Cemaden (MT): **{len(cemaden)}**",
        f"- ANA estações (bbox): **{len(ana_est)}** / com série 7d: **{n_est_com_serie}**",
        f"- Leituras ANA: **{len(ana_tel)}**",
        "",
        "## Flags equivalentes",
        "",
        "- `USE_ANA=true` → tabela `ana_estacoes` populada via SOAP",
        "- `ANA_FETCH_SERIES=true` → tabela `ana_telemetria` com cota/vazão/chuva",
        "",
        "## Fronteira",
        "",
        "Solo aqui é **proxy Open-Meteo** (`openmeteo_soil_proxy`), não o índice TITAN "
        "institucional. Quando o `sis_cloud_seed.db` do CIEVS estiver no caminho "
        "preferido, a etapa 17 passa a consumi-lo sem remontar este seed.",
        "",
    ]
    SAIDA_MD.write_text("\n".join(linhas), encoding="utf-8")
    print(f"  status → {SAIDA_STATUS.relative_to(comum.RAIZ)}")
    print(f"  relatório → {SAIDA_MD.relative_to(comum.RAIZ)}")


if __name__ == "__main__":
    main()
