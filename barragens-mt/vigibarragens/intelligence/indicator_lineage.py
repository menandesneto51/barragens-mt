"""Lineage observacional por indicador IDAP.

Não altera pontuação. Explica qual produto/campo sustentou o valor observado na rodada
corrente e explicita quando a evidência é proxy, derivada ou ausente.
"""
from __future__ import annotations
from typing import Any


def indicator_lineage(
    code: str,
    *,
    hydro: dict[str, Any] | None = None,
    inventory: dict[str, Any] | None = None,
    alertability: dict[str, Any] | None = None,
) -> dict[str, str]:
    hydro = hydro or {}
    inventory = inventory or {}
    alertability = alertability or {}

    hydro_fields = {
        "A1": "chuva_24h_mm",
        "A2": "chuva_72h_mm",
        "A3": "chuva_prevista_24_72h_mm",
        "A4": "percentil_climatologico",
        "A5": "saturacao_antecedente",
        "A6": "razao_nivel_cota_alerta",
        "A7": "dias_consecutivos_chuva_intensa",
    }
    if code in hydro_fields:
        field = hydro_fields[code]
        proxy = code in {"A4", "A6"} or hydro.get("aproximacao_espacial") in {
            "municipio_sede", "sede_mais_montante_max"
        }
        return {
            "produto_observacional": "hidro_barragens_mt.csv",
            "campo_observacional": field,
            "referencia_temporal": str(hydro.get("data_referencia") or ""),
            "tipo_evidencia": "proxy" if proxy else "derivada",
            "metodo_proxy": str(hydro.get("aproximacao_espacial") or "") if proxy else "",
            "fonte_observacional": "|".join(sorted({
                str(hydro.get(k) or "").strip()
                for k in ("fonte_precip", "fonte_previsao", "fonte_solo", "fonte_hidro", "fonte_glofas")
                if str(hydro.get(k) or "").strip()
            })),
        }

    inventory_map = {
        "B1": "categoria_risco",
        "B2": "sigbm_nivel_emergencia|nivel_de_perigo",
        "B3": "sigbm_status_dce",
        "D1": "possui_pae",
    }
    if code in inventory_map:
        return {
            "produto_observacional": "inventario_barragens_mt.csv",
            "campo_observacional": inventory_map[code],
            "referencia_temporal": "",
            "tipo_evidencia": "oficial_cadastral",
            "metodo_proxy": "",
            "fonte_observacional": "SNISB/ANA|SIGBM/ANM",
        }

    if code == "C1":
        return {
            "produto_observacional": "ibge_populacao_municipios_mt.csv",
            "campo_observacional": "populacao",
            "referencia_temporal": "",
            "tipo_evidencia": "proxy",
            "metodo_proxy": "soma_populacao_municipios_potencialmente_afetados_otto",
            "fonte_observacional": "IBGE|topologia Otto provisoria",
        }
    if code == "C3":
        return {
            "produto_observacional": "cnes_estabelecimentos_mt.geojson",
            "campo_observacional": "estabelecimentos_por_municipio_afetado",
            "referencia_temporal": "",
            "tipo_evidencia": "proxy",
            "metodo_proxy": "CNES nos municipios potencialmente afetados por Otto; sem mancha validada",
            "fonte_observacional": "CNES|topologia Otto provisoria",
        }
    if code == "C8":
        return {
            "produto_observacional": "inventario_barragens_mt.csv",
            "campo_observacional": "uso_principal|orgao_fiscalizador",
            "referencia_temporal": "",
            "tipo_evidencia": "derivada",
            "metodo_proxy": "classificacao operacional do material a partir do cadastro",
            "fonte_observacional": "SNISB/ANA|SIGBM/ANM",
        }
    if code == "D8":
        return {
            "produto_observacional": "alertabilidade_piloto.csv",
            "campo_observacional": "contatos_validados_90d",
            "referencia_temporal": "",
            "tipo_evidencia": "operacional_derivada",
            "metodo_proxy": "",
            "fonte_observacional": "cadastro institucional de contatos",
        }

    return {
        "produto_observacional": "",
        "campo_observacional": "",
        "referencia_temporal": "",
        "tipo_evidencia": "ausente",
        "metodo_proxy": "",
        "fonte_observacional": "",
    }
