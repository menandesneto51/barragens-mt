# Estações ANA por barragem

- Fonte estações: `sqlite:sis_cloud_seed.db:ana_estacoes`
- Fonte telemetria: `sqlite:sis_cloud_seed.db:ana_telemetria`
- Vínculos gerados: **3382** (até 3 por barragem, ≤80 km)
- No piloto Manso–Cuiabá: **336** linhas
- Com cota na última leitura: **389**
- A6 com razão medida (cota/cota_alerta) mesclada no hidro: **69** barragens

## Fronteira

Telemetria de rio **não** altera a geometria da mancha (Circular / Trajeto / HAND).
Uso: contexto operacional na Simulação e indicador A6 do IDAP quando houver cota de alerta.

Arquivo: `ana_estacoes_barragem.csv`
