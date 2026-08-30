# Auditoria ANA / SisClima

- Gerado: `2026-08-30T16:49:14Z`
- DB: `não encontrado`
- SQLite com tabelas ANA: **False**
- Estações: `csv:/workspace/barragens-mt/dados/tratados/ana_estacoes_mt_sample.csv` (5 MT)
- Telemetria: `csv:/workspace/barragens-mt/dados/tratados/ana_telemetria_sample.csv` (13 registros)
- Com cota / vazão / cota_alerta (última leitura): **3** / **3** / **2**
- No corredor Manso–Cuiabá (≤25 km do eixo): **1**
- Séries fluviométricas utilizáveis: **True**

## Checklist SisClima

- `USE_ANA`: true no .env SisClima para popular ana_estacoes
- `ANA_FETCH_SERIES`: true para baixar cota/vazão (default false só traz metadados)
- `ANA_HIDROWEB_TOKEN`: obrigatório para API HidroWeb v3
- `fallback_local`: dados/brutos/ana_*.csv quando SQLite sem tabelas ANA

## Fronteira

Cota/vazão ANA alimentam contexto fluvial e IDAP A6; não redimensionam a mancha Circular/Trajeto/HAND (não é dam break).

## Estações no corredor

| Código | Nome | Rio | Cota cm | Vazão m³/s | Dist eixo km |
| --- | --- | --- | ---: | ---: | ---: |
| 01455013 | UHE MANSO MET | Rio Manso | 360.0 | 110.5 | 1.04 |
