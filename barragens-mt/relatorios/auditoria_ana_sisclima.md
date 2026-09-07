# Auditoria ANA / SisClima

- Gerado: `2026-09-07T13:53:03Z`
- DB: `/workspace/barragens-mt/dados/brutos/sisclima/sis_cloud_seed.db`
- SQLite com tabelas ANA: **True**
- Estações: `sqlite:sis_cloud_seed.db:ana_estacoes` (526 MT)
- Telemetria: `sqlite:sis_cloud_seed.db:ana_telemetria` (19462 registros)
- Com cota / vazão / cota_alerta (última leitura): **30** / **19** / **5**
- No corredor Manso–Cuiabá (≤25 km do eixo): **14**
- Séries fluviométricas utilizáveis: **True**

## Checklist SisClima

- `USE_ANA`: true no .env SisClima para popular ana_estacoes (ou etapa 59 SOAP)
- `ANA_FETCH_SERIES`: true para baixar cota/vazão (etapa 59 grava ana_telemetria)
- `ANA_HIDROWEB_TOKEN`: opcional HidroWeb v3; SOAP público cobre telemetria recente
- `fallback_local`: dados/brutos/ana_*.csv quando SQLite sem tabelas ANA
- `seed_local`: python executar.py 59 → dados/brutos/sisclima/sis_cloud_seed.db

## Fronteira

Cota/vazão ANA alimentam contexto fluvial e IDAP A6; não redimensionam a mancha Circular/Trajeto/HAND (não é dam break).

## Estações no corredor

| Código | Nome | Rio | Cota cm | Vazão m³/s | Dist eixo km |
| --- | --- | --- | ---: | ---: | ---: |
| 01455013 | UHE MANSO MET | — | — | — | 1.04 |
| 66210000 | UHE MANSO JUSANTE | RIO MANSO | 294.0 | 98.0 | 0.06 |
| 66240060 | UHE MANSO RESERVATÓRIO | RIO MANSO | — | — | 0.1 |
| 66240080 | UHE MANSO BARRAMENTO | RIO MANSO | 29549.0 | — | 0.03 |
| 66244400 | NOBRES | RIO CUIABÁ | — | — | 0.25 |
| 66258003 | COXIPÓ DO OURO | RIO COXIPO | — | — | 21.03 |
| 66259650 | RIO COXIPÓ - AABB | RIO COXIPO | — | — | 3.76 |
| 66260001 | CUIABÁ | RIO CUIABÁ | — | — | 0.21 |
| 66260006 | CUIABÁ-BEIRA RIO | RIO CUIABÁ | 98.0 | — | 0.23 |
| 66270000 | SANTO ANTÔNIO DO LEVERGER | RIO CUIABÁ | — | — | 0.38 |
| 66280000 | BARÃO DE MELGAÇO | RIO CUIABÁ | — | — | 0.02 |
| 66302500 | BARÃO DE MELGAÇO - BAIA | RIO CUIABÁ-MIRIM | — | — | 5.34 |
| 66340500 | POCONÉ - RIO CUIABÁ | RIO CUIABÁ | 72.0 | — | 0.1 |
| 66710000 | POUSADA TAIAMÃ  (Ex-Porto Jofre) | RIO CUIABÁ | — | — | 0.19 |
