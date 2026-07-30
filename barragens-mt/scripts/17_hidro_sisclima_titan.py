"""Lê o banco operacional do SIS Clima Saúde / TITAN e produz hidro por barragem.

Não recoleta APIs: consome o SQLite já validado pelo CIEVS MT
(`sis_cloud_seed.db` ou `sis_integrado.db`).

Variável de ambiente opcional:
  VIGIBARRAGENS_SISCLIMA_DB = caminho absoluto do .db

Saídas:
  dados/tratados/hidro_municipios_mt.csv   — agregado municipal (A1–A7)
  dados/tratados/hidro_barragens_mt.csv    — mesmo agregado, por barragem (sede)
  relatorios/hidro_sisclima_titan.md

Aproximação espacial: máximo entre município-sede e municípios com seção Otto a
montante da barragem. A agregação areal na BHO estadual completa permanece como
próximo passo (docs/12-integracao-sisclima-titan.md §12.3).
"""

from __future__ import annotations

import csv
import json
import os
import sqlite3
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import comum
import otto

# Limiar alinhado a scripts/idap/pesos.py (A7).
LIMIAR_DIA_ADVERSO_MM = 20.0

CANDIDATOS_DB = [
    Path(os.environ["VIGIBARRAGENS_SISCLIMA_DB"])
    if os.environ.get("VIGIBARRAGENS_SISCLIMA_DB")
    else None,
    Path(
        r"C:\Users\Menandesneto\OneDrive\CIEVS MT"
        r"\SIS-Monitoramento-Clima-Saude-GITHUB-LIMPO\data\cloud\sis_cloud_seed.db"
    ),
    Path(
        r"C:\Users\Menandesneto\OneDrive\CIEVS MT"
        r"\SIS-Monitoramento-Clima-Saude-GITHUB-LIMPO\data\output\sis_integrado.db"
    ),
]


def resolver_db() -> Path:
    for caminho in CANDIDATOS_DB:
        if caminho is not None and caminho.exists() and caminho.stat().st_size > 0:
            return caminho
    raise SystemExit(
        "banco SIS Clima/TITAN não encontrado. Defina VIGIBARRAGENS_SISCLIMA_DB "
        "ou mantenha o repositório CIEVS MT no OneDrive."
    )


def ibge7(valor: Any) -> str:
    texto = str(valor or "").strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    digitos = "".join(c for c in texto if c.isdigit())
    return digitos[:7] if len(digitos) >= 7 else digitos


def num(valor: Any) -> float | None:
    if valor is None or valor == "":
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def tabelas(con: sqlite3.Connection) -> set[str]:
    return {
        r[0]
        for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def ler_met(con: sqlite3.Connection) -> list[dict[str, Any]]:
    nomes = tabelas(con)
    if "met_biometeo" not in nomes:
        return []
    cols = {r[1] for r in con.execute("PRAGMA table_info(met_biometeo)")}
    precip = "precipitacao_mm" if "precipitacao_mm" in cols else (
        "chuva_mm" if "chuva_mm" in cols else None
    )
    if precip is None:
        return []
    solo = "indice_saturacao_solo" if "indice_saturacao_solo" in cols else "NULL"
    sql = (
        f"SELECT data, cod_ibge, municipio, {precip} AS precip_mm, "
        f"{solo} AS indice_saturacao_solo, fonte "
        f"FROM met_biometeo WHERE {precip} IS NOT NULL"
    )
    linhas = []
    for data_txt, cod, mun, precip_mm, sat, fonte in con.execute(sql):
        dia = str(data_txt)[:10]
        linhas.append(
            {
                "data": dia,
                "cod_ibge": ibge7(cod),
                "municipio": mun if mun and str(mun) != "nan" else "",
                "precip_mm": num(precip_mm) or 0.0,
                "indice_saturacao_solo": num(sat),
                "fonte": fonte or "sisclima",
            }
        )
    return linhas


def ler_solo_snapshot(con: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    if "solo_saturacao_municipal" not in tabelas(con):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for cod, mun, data_txt, sat, classe, fonte in con.execute(
        "SELECT cod_ibge, municipio, data, indice_saturacao_solo, "
        "classe_saturacao_solo, fonte_solo FROM solo_saturacao_municipal"
    ):
        chave = ibge7(cod)
        if not chave:
            continue
        out[chave] = {
            "data": str(data_txt)[:10],
            "municipio": mun if mun and str(mun) != "nan" else "",
            "indice_saturacao_solo": num(sat),
            "classe_saturacao_solo": classe,
            "fonte_solo": fonte or "titan",
        }
    return out


def ler_hidro_ana(con: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    nomes = tabelas(con)
    fonte_tabela = (
        "hidro_risco_municipal"
        if "hidro_risco_municipal" in nomes
        else "ana_risco_municipal"
        if "ana_risco_municipal" in nomes
        else None
    )
    if fonte_tabela is None:
        return {}
    cols = {r[1] for r in con.execute(f"PRAGMA table_info({fonte_tabela})")}
    nivel_col = (
        "nivel_alerta_hidro"
        if "nivel_alerta_hidro" in cols
        else "nivel_chuva"
        if "nivel_chuva" in cols
        else None
    )
    campos = ["cod_ibge", "municipio", "data", "cota_cm", "vazao_m3s"]
    if nivel_col:
        campos.append(nivel_col)
    sql = f"SELECT {', '.join(campos)} FROM {fonte_tabela}"
    out: dict[str, dict[str, Any]] = {}
    for row in con.execute(sql):
        registro = dict(zip(campos, row))
        chave = ibge7(registro["cod_ibge"])
        if not chave:
            continue
        out[chave] = {
            "data": str(registro.get("data") or "")[:10],
            "municipio": registro.get("municipio") or "",
            "cota_cm": num(registro.get("cota_cm")),
            "vazao_m3s": num(registro.get("vazao_m3s")),
            "nivel_alerta_hidro": registro.get(nivel_col) if nivel_col else None,
            "fonte_hidro": fonte_tabela,
        }
    return out


def razao_nivel_proxy(nivel: str | None) -> float | None:
    """Traduz o estágio hidrológico do TITAN/SIS em razão à cota de alerta.

    Proxy operacional enquanto a cota de alerta nominal por estação não estiver
    no contrato de dados. Valores alinhados às faixas de A6.
    """
    if not nivel:
        return None
    chave = str(nivel).strip().lower()
    return {
        "verde": 0.55,
        "amarela": 0.80,
        "amarelo": 0.80,
        "laranja": 1.05,
        "vermelha": 1.30,
        "vermelho": 1.30,
        "roxa": 1.40,
        "roxo": 1.40,
    }.get(chave)


def dias_consecutivos_adversos(series: list[tuple[date, float]]) -> int:
    """Conta dias consecutivos com chuva >= limiar, a partir do dia mais recente."""
    if not series:
        return 0
    ordenada = sorted(series, key=lambda item: item[0], reverse=True)
    contagem = 0
    esperado = ordenada[0][0]
    for dia, precip in ordenada:
        if dia != esperado:
            break
        if precip >= LIMIAR_DIA_ADVERSO_MM:
            contagem += 1
            esperado = dia - timedelta(days=1)
        else:
            break
    return contagem


def ler_alertas_sisclima(con: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    """Consolida INMET, Cemaden, ANA e alerta integrado por município (IBGE7)."""
    nomes = tabelas(con)
    out: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "alerta_cemaden": "",
            "alerta_cemaden_nivel": "",
            "alerta_inmet": "",
            "alerta_inmet_nivel": "",
            "alerta_ana_nivel": "",
            "nivel_alerta_integrado": "",
            "score_alerta_integrado": "",
            "componente_dominante": "",
            "motivo_integrado": "",
        }
    )

    if "cemaden_alertas" in nomes:
        for row in con.execute(
            "SELECT cod_ibge, municipio, tipo_risco, evento, nivel_sis, nivel_alerta "
            "FROM cemaden_alertas"
        ):
            cod, mun, tipo, evento, nivel_sis, nivel = row
            chave = ibge7(cod)
            if not chave:
                continue
            slot = out[chave]
            slot["alerta_cemaden"] = f"{tipo or ''}:{evento or ''}".strip(":")
            slot["alerta_cemaden_nivel"] = (nivel_sis or nivel or "").lower()
            if mun and str(mun) != "nan":
                slot["municipio"] = mun

    if "inmet_alertas" in nomes:
        for row in con.execute(
            "SELECT cod_ibge, municipio, nivel_alerta, evento, descricao "
            "FROM inmet_alertas"
        ):
            cod, mun, nivel, evento, desc = row
            chave = ibge7(cod)
            if not chave:
                continue
            slot = out[chave]
            slot["alerta_inmet"] = f"{evento or ''}".strip()
            slot["alerta_inmet_nivel"] = (nivel or "").lower()
            slot["alerta_inmet_descricao"] = (desc or "")[:180]
            if mun and str(mun) != "nan":
                slot["municipio"] = mun

    if "alerta_integrado_sis_titan" in nomes:
        for row in con.execute(
            "SELECT cod_ibge, municipio, nivel_alerta_integrado, score_alerta_integrado, "
            "componente_dominante, motivo_integrado FROM alerta_integrado_sis_titan"
        ):
            cod, mun, nivel, score, comp, motivo = row
            chave = ibge7(cod)
            if not chave:
                continue
            slot = out[chave]
            slot["nivel_alerta_integrado"] = (nivel or "").lower()
            slot["score_alerta_integrado"] = score if score is not None else ""
            slot["componente_dominante"] = comp or ""
            slot["motivo_integrado"] = (motivo or "")[:220]
            if mun and str(mun) != "nan":
                slot["municipio"] = mun

    if "hidro_risco_municipal" in nomes or "ana_risco_municipal" in nomes:
        # nível ANA já lido em ler_hidro_ana — reforço aqui se faltar
        pass

    return dict(out)


def coords_municipais(met: list[dict[str, Any]], con: sqlite3.Connection) -> dict[str, tuple[float, float]]:
    """lat/lon por IBGE a partir de met_biometeo."""
    coords: dict[str, tuple[float, float]] = {}
    if "met_biometeo" not in tabelas(con):
        return coords
    cols = {r[1] for r in con.execute("PRAGMA table_info(met_biometeo)")}
    if "lat" not in cols or "lon" not in cols:
        return coords
    for cod, lat, lon in con.execute(
        "SELECT cod_ibge, lat, lon FROM met_biometeo "
        "WHERE lat IS NOT NULL AND lon IS NOT NULL"
    ):
        chave = ibge7(cod)
        if chave and chave not in coords:
            try:
                coords[chave] = (float(lat), float(lon))
            except (TypeError, ValueError):
                continue
    return coords


def _percentil(valor: float, amostra: list[float]) -> float | None:
    if not amostra:
        return None
    ordenada = sorted(amostra)
    abaixo = sum(1 for x in ordenada if x <= valor)
    return round(100.0 * abaixo / len(ordenada), 1)


def agregar_municipios(
    met: list[dict[str, Any]],
    solo: dict[str, dict[str, Any]],
    hidro: dict[str, dict[str, Any]],
    alertas: dict[str, dict[str, Any]] | None = None,
    previsoes: dict[str, dict[str, Any]] | None = None,
    glofas: dict[str, dict[str, Any]] | None = None,
    *,
    hoje: date | None = None,
) -> list[dict[str, Any]]:
    alertas = alertas or {}
    previsoes = previsoes or {}
    glofas = glofas or {}
    hoje = hoje or date.today()

    por_mun: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for linha in met:
        if linha["cod_ibge"]:
            por_mun[linha["cod_ibge"]].append(linha)

    # Amostra espacial do dia de referência (percentil estadual proxy de A4).
    chuva_dia_ref: dict[str, float] = {}
    for cod, linhas in por_mun.items():
        por_data_tmp: dict[date, float] = {}
        for linha in linhas:
            dia = date.fromisoformat(linha["data"])
            if dia <= hoje:
                por_data_tmp[dia] = por_data_tmp.get(dia, 0.0) + float(linha["precip_mm"])
        if por_data_tmp:
            ultima = max(por_data_tmp)
            chuva_dia_ref[cod] = por_data_tmp[ultima]
    amostra_espacial = list(chuva_dia_ref.values())

    saida: list[dict[str, Any]] = []
    for cod, linhas in sorted(por_mun.items()):
        por_data_obs: dict[date, float] = {}
        por_data_fut: dict[date, float] = {}
        nome = ""
        fonte = ""
        sat_serie: list[float] = []
        for linha in linhas:
            dia = date.fromisoformat(linha["data"])
            precip = float(linha["precip_mm"])
            if dia <= hoje:
                por_data_obs[dia] = por_data_obs.get(dia, 0.0) + precip
            else:
                por_data_fut[dia] = por_data_fut.get(dia, 0.0) + precip
            if linha["municipio"]:
                nome = linha["municipio"]
            fonte = linha["fonte"] or fonte
            if linha["indice_saturacao_solo"] is not None:
                sat_serie.append(linha["indice_saturacao_solo"])

        if not por_data_obs and not por_data_fut:
            continue

        if por_data_obs:
            ultima = max(por_data_obs)
            chuva_24h = por_data_obs.get(ultima, 0.0)
            chuva_72h = sum(
                por_data_obs.get(ultima - timedelta(days=d), 0.0) for d in range(3)
            )
            series = list(por_data_obs.items())
            dias_adv = dias_consecutivos_adversos(series)
            data_ref = ultima
        else:
            chuva_24h = 0.0
            chuva_72h = 0.0
            dias_adv = 0
            data_ref = min(por_data_fut) if por_data_fut else hoje

        # A3: preferir Open-Meteo ECMWF; senão soma dos dias futuros no seed SisClima.
        prev = previsoes.get(cod, {})
        chuva_prev = prev.get("chuva_prevista_24_72h_mm")
        fonte_prev = prev.get("fonte_previsao") or ""
        if chuva_prev is None and por_data_fut:
            proximos = sorted(por_data_fut)[:3]
            chuva_prev = sum(por_data_fut[d] for d in proximos)
            fonte_prev = "sisclima_met_futuro"

        # A4: percentil espacial estadual do acumulado 24 h (proxy até série longa).
        pct = _percentil(chuva_24h, amostra_espacial)

        snap = solo.get(cod, {})
        sat_idx = snap.get("indice_saturacao_solo")
        if sat_idx is None and sat_serie:
            sat_idx = sat_serie[-1]
        saturacao_01 = (sat_idx / 100.0) if sat_idx is not None else None

        hidro_m = hidro.get(cod, {})
        razao = razao_nivel_proxy(hidro_m.get("nivel_alerta_hidro"))
        al = alertas.get(cod, {})
        if not razao and al.get("alerta_ana_nivel"):
            razao = razao_nivel_proxy(al.get("alerta_ana_nivel"))

        # ANA nível a partir do hidro
        nivel_ana = (hidro_m.get("nivel_alerta_hidro") or "").lower()
        if nivel_ana and nivel_ana not in {"verde", ""}:
            al = {**al, "alerta_ana_nivel": nivel_ana}

        if not nome:
            nome = snap.get("municipio") or hidro_m.get("municipio") or al.get("municipio") or ""

        gf = glofas.get(cod, {})

        saida.append(
            {
                "codigo_ibge": cod,
                "municipio": nome,
                "data_referencia": data_ref.isoformat(),
                "chuva_24h_mm": round(chuva_24h, 2),
                "chuva_72h_mm": round(chuva_72h, 2),
                "chuva_prevista_24_72h_mm": (
                    round(float(chuva_prev), 2) if chuva_prev is not None else ""
                ),
                "percentil_climatologico": pct if pct is not None else "",
                "saturacao_antecedente": (
                    f"{saturacao_01:.4f}".replace(".", ",")
                    if saturacao_01 is not None
                    else ""
                ),
                "indice_saturacao_solo": (
                    f"{sat_idx:.1f}".replace(".", ",") if sat_idx is not None else ""
                ),
                "classe_saturacao_solo": snap.get("classe_saturacao_solo") or "",
                "razao_nivel_cota_alerta": (
                    f"{razao:.2f}".replace(".", ",") if razao is not None else ""
                ),
                "nivel_alerta_hidro": hidro_m.get("nivel_alerta_hidro") or "",
                "dias_consecutivos_chuva_intensa": dias_adv,
                "dias_com_serie_precip": len(por_data_obs),
                "fonte_precip": fonte or "sisclima",
                "fonte_previsao": fonte_prev,
                "fonte_solo": snap.get("fonte_solo") or "",
                "fonte_hidro": hidro_m.get("fonte_hidro") or "",
                "alerta_cemaden": al.get("alerta_cemaden") or "",
                "alerta_cemaden_nivel": al.get("alerta_cemaden_nivel") or "",
                "alerta_inmet": al.get("alerta_inmet") or "",
                "alerta_inmet_nivel": al.get("alerta_inmet_nivel") or "",
                "alerta_ana_nivel": al.get("alerta_ana_nivel") or nivel_ana,
                "nivel_alerta_integrado": al.get("nivel_alerta_integrado") or "",
                "score_alerta_integrado": al.get("score_alerta_integrado") or "",
                "componente_dominante": al.get("componente_dominante") or "",
                "motivo_integrado": al.get("motivo_integrado") or "",
                "vazao_prevista_glofas_m3s": gf.get("vazao_prevista_max_m3s") or "",
                "fonte_glofas": gf.get("fonte_glofas") or "",
                "aproximacao_espacial": "municipio_sede",
            }
        )
    return saida


def ler_inventario() -> list[dict[str, Any]]:
    caminho = comum.DADOS_TRATADOS / "inventario_barragens_mt.csv"
    if not caminho.exists():
        raise SystemExit(f"base ausente: {caminho.name}")
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def secoes_controle_por_municipio(
    inventario: list[dict[str, Any]],
) -> dict[str, tuple[str, str]]:
    """Município → (código Otto de seção, IBGE7)."""
    por_municipio: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for registro in inventario:
        mun = (registro.get("municipio") or "").strip()
        codigo = otto.normalizar(registro.get("codigo_trecho_curso_dagua"))
        ibge = ibge7(registro.get("codigo_ibge"))
        if mun and codigo:
            por_municipio[mun].append((codigo, ibge))

    secoes: dict[str, tuple[str, str]] = {}
    for mun, pares in por_municipio.items():
        codigo, ibge = sorted(pares, key=lambda p: (-len(p[0]), p[0]))[0]
        secoes[mun] = (codigo, ibge)

    recorte = comum.DADOS_TRATADOS / "cuiaba_municipios_de_interesse.json"
    if recorte.exists():
        dados = json.loads(recorte.read_text(encoding="utf-8"))
        cobacia = otto.normalizar(dados.get("secao_de_controle"))
        if cobacia and "Cuiabá" in secoes:
            _, ibge = secoes["Cuiabá"]
            secoes["Cuiabá"] = (cobacia, ibge)
        elif cobacia:
            secoes["Cuiabá"] = (cobacia, "5103403")
    secoes.setdefault("Cuiabá", ("896573", "5103403"))
    return secoes


def ibges_contribuinte(
    codigo_barragem: str,
    municipio_sede: str,
    ibge_sede: str,
    secoes: dict[str, tuple[str, str]],
) -> tuple[list[str], str]:
    """IBGEs da sede + municípios com seção a montante da barragem (docs/12 §12.3)."""
    ibges = {ibge_sede} if ibge_sede else set()
    nomes_montante: list[str] = []
    if codigo_barragem:
        for mun, (secao, ibge) in secoes.items():
            # Mesmo filtro de prefixo do IDAP estadual — evita 895×896 e afins.
            if otto.drena_para(secao, codigo_barragem, min_prefixo=3):
                if ibge:
                    ibges.add(ibge)
                if mun != municipio_sede:
                    nomes_montante.append(mun)
    if len(ibges) <= 1 and not nomes_montante:
        return sorted(ibges), "municipio_sede"
    return sorted(ibges), "sede_mais_montante_max"


def _float_campo(valor: Any) -> float | None:
    if valor is None or valor == "":
        return None
    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return None


def agregar_hidro_contribuintes(
    por_ibge: dict[str, dict[str, Any]],
    ibges: list[str],
    *,
    ibge_sede: str = "",
) -> dict[str, Any] | None:
    """Máximo das intensidades entre os municípios da área contribuinte.

    Soma municipal superestimaria a chuva na bacia; o máximo captura o pior
    município a montante (proxy até existir agregação areal na BHO).

    Alertas Cemaden/INMET/integrado vêm só do município-sede: a topologia Otto
    provisória espalharia alertas pontuais por bacias irmãs (falso positivo).
    """
    partes = [por_ibge[c] for c in ibges if c in por_ibge]
    if not partes:
        return None

    def max_campo(chave: str) -> float | None:
        vals = [_float_campo(p.get(chave)) for p in partes]
        vals = [v for v in vals if v is not None]
        return max(vals) if vals else None

    chuva_24 = max_campo("chuva_24h_mm")
    chuva_72 = max_campo("chuva_72h_mm")
    chuva_prev = max_campo("chuva_prevista_24_72h_mm")
    pct = max_campo("percentil_climatologico")
    sat = max_campo("saturacao_antecedente")
    razao = max_campo("razao_nivel_cota_alerta")
    dias = max_campo("dias_consecutivos_chuva_intensa")
    vazao_g = max_campo("vazao_prevista_glofas_m3s")
    datas = sorted({p.get("data_referencia") or "" for p in partes if p.get("data_referencia")})
    niveis = [p.get("nivel_alerta_hidro") or "" for p in partes if p.get("nivel_alerta_hidro")]
    ordem = {
        "verde": 0,
        "amarela": 1,
        "amarelo": 1,
        "laranja": 2,
        "vermelha": 3,
        "vermelho": 3,
        "roxa": 4,
        "roxo": 4,
        "moderado": 2,
    }
    nivel = max(niveis, key=lambda n: ordem.get(str(n).lower(), -1)) if niveis else ""

    sede = por_ibge.get(ibge_sede) or partes[0]

    def fmt(v: float | None, casas: int = 2) -> str:
        if v is None:
            return ""
        return f"{v:.{casas}f}".replace(".", ",")

    return {
        "data_referencia": datas[-1] if datas else "",
        "chuva_24h_mm": round(chuva_24, 2) if chuva_24 is not None else "",
        "chuva_72h_mm": round(chuva_72, 2) if chuva_72 is not None else "",
        "chuva_prevista_24_72h_mm": round(chuva_prev, 2) if chuva_prev is not None else "",
        "percentil_climatologico": round(pct, 1) if pct is not None else "",
        "saturacao_antecedente": fmt(sat, 4),
        "razao_nivel_cota_alerta": fmt(razao, 2),
        "dias_consecutivos_chuva_intensa": int(dias) if dias is not None else "",
        "nivel_alerta_hidro": nivel,
        "fonte_precip": partes[0].get("fonte_precip") or "sisclima",
        "fonte_previsao": sede.get("fonte_previsao")
        or next((p.get("fonte_previsao") for p in partes if p.get("fonte_previsao")), ""),
        "fonte_solo": next((p.get("fonte_solo") for p in partes if p.get("fonte_solo")), ""),
        "fonte_hidro": next((p.get("fonte_hidro") for p in partes if p.get("fonte_hidro")), ""),
        "alerta_cemaden": sede.get("alerta_cemaden") or "",
        "alerta_cemaden_nivel": sede.get("alerta_cemaden_nivel") or "",
        "alerta_inmet": sede.get("alerta_inmet") or "",
        "alerta_inmet_nivel": sede.get("alerta_inmet_nivel") or "",
        "alerta_ana_nivel": sede.get("alerta_ana_nivel") or "",
        "nivel_alerta_integrado": sede.get("nivel_alerta_integrado") or "",
        "score_alerta_integrado": sede.get("score_alerta_integrado") or "",
        "componente_dominante": sede.get("componente_dominante") or "",
        "motivo_integrado": sede.get("motivo_integrado") or "",
        "vazao_prevista_glofas_m3s": round(vazao_g, 2) if vazao_g is not None else "",
        "fonte_glofas": next((p.get("fonte_glofas") for p in partes if p.get("fonte_glofas")), ""),
        "n_municipios_contribuintes": len(partes),
        "municipios_contribuintes_ibge": "|".join(ibges),
    }


def expandir_barragens(
    municipios: list[dict[str, Any]], inventario: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    por_ibge = {r["codigo_ibge"]: r for r in municipios}
    secoes = secoes_controle_por_municipio(inventario)
    saida: list[dict[str, Any]] = []
    sem_hidro = 0
    com_montante = 0
    for registro in inventario:
        cod = ibge7(registro.get("codigo_ibge"))
        mun_sede = (registro.get("municipio") or "").strip()
        codigo_otto = otto.normalizar(registro.get("codigo_trecho_curso_dagua"))
        ibges, aproximacao = ibges_contribuinte(codigo_otto, mun_sede, cod, secoes)
        hidro = agregar_hidro_contribuintes(por_ibge, ibges, ibge_sede=cod)
        if hidro is None:
            sem_hidro += 1
            saida.append(
                {
                    "id_snisb": registro.get("id_snisb"),
                    "nome": registro.get("nome"),
                    "municipio_sede": mun_sede,
                    "codigo_ibge": cod,
                    "data_referencia": "",
                    "chuva_24h_mm": "",
                    "chuva_72h_mm": "",
                    "chuva_prevista_24_72h_mm": "",
                    "percentil_climatologico": "",
                    "saturacao_antecedente": "",
                    "razao_nivel_cota_alerta": "",
                    "dias_consecutivos_chuva_intensa": "",
                    "fonte_precip": "",
                    "fonte_previsao": "",
                    "alerta_cemaden": "",
                    "alerta_cemaden_nivel": "",
                    "alerta_inmet": "",
                    "alerta_inmet_nivel": "",
                    "alerta_ana_nivel": "",
                    "nivel_alerta_integrado": "",
                    "vazao_prevista_glofas_m3s": "",
                    "n_municipios_contribuintes": 0,
                    "municipios_contribuintes_ibge": "",
                    "aproximacao_espacial": "sem_dado_municipal",
                }
            )
            continue
        if aproximacao == "sede_mais_montante_max":
            com_montante += 1
        saida.append(
            {
                "id_snisb": registro.get("id_snisb"),
                "nome": registro.get("nome"),
                "municipio_sede": mun_sede,
                "codigo_ibge": cod,
                "data_referencia": hidro["data_referencia"],
                "chuva_24h_mm": hidro["chuva_24h_mm"],
                "chuva_72h_mm": hidro["chuva_72h_mm"],
                "chuva_prevista_24_72h_mm": hidro["chuva_prevista_24_72h_mm"],
                "percentil_climatologico": hidro["percentil_climatologico"],
                "saturacao_antecedente": hidro["saturacao_antecedente"],
                "razao_nivel_cota_alerta": hidro["razao_nivel_cota_alerta"],
                "dias_consecutivos_chuva_intensa": hidro[
                    "dias_consecutivos_chuva_intensa"
                ],
                "fonte_precip": hidro["fonte_precip"],
                "fonte_previsao": hidro.get("fonte_previsao") or "",
                "fonte_solo": hidro["fonte_solo"],
                "fonte_hidro": hidro["fonte_hidro"],
                "nivel_alerta_hidro": hidro["nivel_alerta_hidro"],
                "alerta_cemaden": hidro.get("alerta_cemaden") or "",
                "alerta_cemaden_nivel": hidro.get("alerta_cemaden_nivel") or "",
                "alerta_inmet": hidro.get("alerta_inmet") or "",
                "alerta_inmet_nivel": hidro.get("alerta_inmet_nivel") or "",
                "alerta_ana_nivel": hidro.get("alerta_ana_nivel") or "",
                "nivel_alerta_integrado": hidro.get("nivel_alerta_integrado") or "",
                "score_alerta_integrado": hidro.get("score_alerta_integrado") or "",
                "componente_dominante": hidro.get("componente_dominante") or "",
                "motivo_integrado": hidro.get("motivo_integrado") or "",
                "vazao_prevista_glofas_m3s": hidro.get("vazao_prevista_glofas_m3s") or "",
                "fonte_glofas": hidro.get("fonte_glofas") or "",
                "n_municipios_contribuintes": hidro["n_municipios_contribuintes"],
                "municipios_contribuintes_ibge": hidro["municipios_contribuintes_ibge"],
                "aproximacao_espacial": aproximacao,
            }
        )
    print(f"  barragens sem hidro municipal: {sem_hidro}")
    print(f"  barragens com agregação sede+montante: {com_montante}")
    return saida


def escrever_relatorio(
    db: Path,
    municipios: list[dict[str, Any]],
    barragens: list[dict[str, Any]],
) -> None:
    com_chuva = sum(1 for r in municipios if float(str(r["chuva_24h_mm"]).replace(",", ".") or 0) > 0)
    com_solo = sum(1 for r in municipios if r.get("saturacao_antecedente"))
    com_hidro = sum(1 for r in municipios if r.get("nivel_alerta_hidro"))
    partes = [
        "# Hidrometeorologia — SIS Clima Saúde / TITAN",
        "",
        f"Fonte: `{db}`",
        f"Extração: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Cobertura",
        "",
        f"- Municípios com série de precipitação: **{len(municipios)}**",
        f"- Destes, com chuva > 0 mm na data de referência: **{com_chuva}**",
        f"- Com saturação do solo (TITAN): **{com_solo}**",
        f"- Com estágio hidrológico ANA/TITAN: **{com_hidro}**",
        f"- Barragens no inventário com linha hidro: **{len(barragens)}**",
        "",
        "## Mapeamento → IDAP",
        "",
        "| Campo | Indicador |",
        "| --- | --- |",
        "| `chuva_24h_mm` | A1 |",
        "| `chuva_72h_mm` | A2 |",
        "| `chuva_prevista_24_72h_mm` | A3 (Open-Meteo ECMWF IFS / SisClima futuro) |",
        "| `percentil_climatologico` | A4 (percentil espacial estadual — proxy) |",
        "| `saturacao_antecedente` | A5 (índice TITAN 0–100 → 0–1) |",
        "| `razao_nivel_cota_alerta` | A6 (proxy do estágio hidro) |",
        "| `dias_consecutivos_chuva_intensa` | A7 |",
        "| alertas Cemaden/INMET/ANA + integrado | sinais → regras R10–R12 |",
        "| `vazao_prevista_glofas_m3s` | contexto Copernicus EMS (GloFAS) |",
        "",
        "## Copernicus",
        "",
        "- Previsão de chuva: **ECMWF IFS** via Open-Meteo (ecossistema Copernicus/C3S).",
        "- Cheias: **GloFAS** via Open-Meteo Flood API (amostra de municípios).",
        "- Sentinel EMS Rapid Mapping: acionamento autorizado (Defesa Civil) — não automatizado aqui.",
        "",
        "## Aproximação espacial",
        "",
        f"- Barragens com agregação **sede + municípios a montante** (máximo): "
        f"**{sum(1 for r in barragens if r.get('aproximacao_espacial') == 'sede_mais_montante_max')}**",
        f"- Apenas município-sede: "
        f"**{sum(1 for r in barragens if r.get('aproximacao_espacial') == 'municipio_sede')}**",
        "",
        "A métrica agregada é o **máximo** entre os municípios contribuintes (pior pressão), "
        "não a soma. A agregação areal sobre a BHO estadual completa substitui este proxy.",
        "",
    ]
    destino = comum.RELATORIOS / "hidro_sisclima_titan.md"
    destino.write_text("\n".join(partes), encoding="utf-8")
    print(f"  gravado {destino.relative_to(comum.RAIZ)}")


def main() -> None:
    comum.preparar_diretorios()
    db = resolver_db()
    print(f"Hidro SIS Clima / TITAN — lendo {db}")

    con = sqlite3.connect(db)
    try:
        met = ler_met(con)
        solo = ler_solo_snapshot(con)
        hidro = ler_hidro_ana(con)
        alertas = ler_alertas_sisclima(con)
        coords = coords_municipais(met, con)
    finally:
        con.close()

    print(f"  met_biometeo com precip: {len(met)} linhas")
    print(f"  solo_saturacao_municipal: {len(solo)} municípios")
    print(f"  hidro/ANA: {len(hidro)} municípios")
    print(f"  alertas SisClima (mun): {len(alertas)}")
    print(f"  coords municipais: {len(coords)}")

    if not met:
        raise SystemExit(
            "met_biometeo sem coluna de precipitação no banco escolhido. "
            "Use o sis_cloud_seed.db (tem precipitacao_mm)."
        )

    # Previsão ECMWF (Copernicus/C3S) + amostra GloFAS
    from previsao_copernicus import previsao_chuva_lote, risco_cheias_glofas

    pontos = [(cod, la, lo) for cod, (la, lo) in sorted(coords.items())]
    print(f"  buscando previsão ECMWF Open-Meteo para {len(pontos)} municípios…")
    previsoes = previsao_chuva_lote(pontos, dias=3)
    print(f"  previsão obtida: {len(previsoes)} municípios")
    # GloFAS: eixo Cuiabá + amostra com alerta hidro
    foco = {
        c
        for c, a in alertas.items()
        if (a.get("alerta_cemaden_nivel") or a.get("nivel_alerta_integrado") or "")
        not in ("", "verde")
    }
    foco |= {c for c in ("5103403", "5108402", "5103007", "5107925") if c in coords}
    pontos_g = [(c, *coords[c]) for c in sorted(foco) if c in coords][:40]
    print(f"  buscando GloFAS (Copernicus EMS) para {len(pontos_g)} pontos…")
    glofas = risco_cheias_glofas(pontos_g)
    print(f"  GloFAS: {len(glofas)} municípios com descarga")

    municipios = agregar_municipios(
        met, solo, hidro, alertas, previsoes, glofas, hoje=date.today()
    )
    inventario = ler_inventario()
    barragens = expandir_barragens(municipios, inventario)

    comum.salvar_csv(
        comum.DADOS_TRATADOS / "hidro_municipios_mt.csv",
        municipios,
        list(municipios[0].keys()) if municipios else [],
    )
    comum.salvar_csv(
        comum.DADOS_TRATADOS / "hidro_barragens_mt.csv",
        barragens,
        list(barragens[0].keys()) if barragens else [],
    )
    escrever_relatorio(db, municipios, barragens)
    com_a3 = sum(1 for r in municipios if r.get("chuva_prevista_24_72h_mm") not in ("", None))
    com_a4 = sum(1 for r in municipios if r.get("percentil_climatologico") not in ("", None))
    print(f"  municípios hidro: {len(municipios)} (A3={com_a3}, A4={com_a4})")
    print(f"  barragens hidro: {len(barragens)}")


if __name__ == "__main__":
    main()
