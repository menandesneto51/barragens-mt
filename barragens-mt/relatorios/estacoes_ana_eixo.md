# Estações ANA por barragem

- Fonte estações: `csv:/workspace/barragens-mt/dados/brutos/ana_estacoes_mt.csv`
- Fonte telemetria: `csv:/workspace/barragens-mt/dados/brutos/ana_telemetria.csv`
- Vínculos gerados: **245** (até 3 por barragem, ≤80 km)
- No piloto Manso–Cuiabá: **44** linhas
- Com cota na última leitura: **89**
- A6 com razão medida (cota/cota_alerta) mesclada no hidro: **16** barragens

## Fronteira

Telemetria de rio **não** altera a geometria da mancha (Circular / Trajeto / HAND).
Uso: contexto operacional na Simulação e indicador A6 do IDAP quando houver cota de alerta.

Arquivo: `ana_estacoes_barragem.csv`
