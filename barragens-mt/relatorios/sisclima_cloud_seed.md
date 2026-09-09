# SisClima cloud seed (operacional)

- Gerado: `2026-09-07T13:48:21Z`
- DB: `/workspace/barragens-mt/dados/brutos/sisclima/sis_cloud_seed.db`
- Municípios: **142**
- Solo (proxy Open-Meteo): **142**
- Alertas INMET (MT): **295**
- Alertas Cemaden (MT): **0**
- ANA estações (bbox): **526** / com série 7d: **32**
- Leituras ANA: **19462**

## Flags equivalentes

- `USE_ANA=true` → tabela `ana_estacoes` populada via SOAP
- `ANA_FETCH_SERIES=true` → tabela `ana_telemetria` com cota/vazão/chuva

## Fronteira

Solo aqui é **proxy Open-Meteo** (`openmeteo_soil_proxy`), não o índice TITAN institucional. Quando o `sis_cloud_seed.db` do CIEVS estiver no caminho preferido, a etapa 17 passa a consumi-lo sem remontar este seed.
