# HAND piloto — eixo Manso–Cuiabá

- Dataset: **srtm30m** (`https://api.opentopodata.org/v1/srtm30m`)
- Células na grade: **697** (HAND válido: **697**)
- Eixo amostrado: até **80.0 km** a jusante (passo 2.0 km)
- Arquivos: `hand_piloto_manso_cuiaba_grade.csv`, `hand_piloto_manso_cuiaba.geojson`, `hand_piloto_manso_cuiaba_meta.json`

| Limiar HAND | Células |
| --- | ---: |
| ≤ 2 m | 91 |
| ≤ 5 m | 124 |
| ≤ 8 m | 147 |
| ≤ 10 m | 176 |
| ≤ 15 m | 252 |
| ≤ 20 m | 326 |
| ≤ 30 m | 456 |

> Proxy geomorfológico SRTM/HAND — não é mancha PAE nem dam break. Não estima tempo de chegada da onda.

UI: Simulação → geometria **Relevo (HAND)** (`st_app/relevo_hand.py`).
