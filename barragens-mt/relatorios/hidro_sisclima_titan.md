# Hidrometeorologia — SIS Clima Saúde / TITAN

Fonte: `/workspace/sisclima-repo/data/output/sis_integrado.db`
Extração: 2026-09-07T11:26:07

## Cobertura

- Municípios com série de precipitação: **142**
- Destes, com chuva > 0 mm na data de referência: **135**
- Com saturação do solo (TITAN): **0**
- Com estágio hidrológico ANA/TITAN: **0**
- Barragens no inventário com linha hidro: **1280**

## Mapeamento → IDAP

| Campo | Indicador |
| --- | --- |
| `chuva_24h_mm` | A1 |
| `chuva_72h_mm` | A2 |
| `chuva_prevista_24_72h_mm` | A3 (Open-Meteo ECMWF IFS / SisClima futuro) |
| `percentil_climatologico` | A4 (percentil espacial estadual — proxy) |
| `saturacao_antecedente` | A5 (índice TITAN 0–100 → 0–1) |
| `razao_nivel_cota_alerta` | A6 (proxy do estágio hidro) |
| `dias_consecutivos_chuva_intensa` | A7 |
| alertas Cemaden/INMET/ANA + integrado | sinais → regras R10–R12 |
| `vazao_prevista_glofas_m3s` | contexto Copernicus EMS (GloFAS) |

## Copernicus

- Previsão de chuva: **ECMWF IFS** via Open-Meteo (ecossistema Copernicus/C3S).
- Cheias: **GloFAS** via Open-Meteo Flood API (amostra de municípios).
- Sentinel EMS Rapid Mapping: acionamento autorizado (Defesa Civil) — não automatizado aqui.

## Aproximação espacial

- Barragens com agregação **sede + municípios a montante** (máximo): **401**
- Apenas município-sede: **879**

A métrica agregada é o **máximo** entre os municípios contribuintes (pior pressão), não a soma. A agregação areal sobre a BHO estadual completa substitui este proxy.
