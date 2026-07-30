# IDAP estadual — Mato Grosso

Cálculo em lote das **1248** barragens do inventário consolidado, com pesos `0.1.0-metodologica`.

> proposta metodológica — pendente de validação por painel de especialistas em engenharia de barragens, hidrologia, meteorologia, epidemiologia, saúde ambiental, assistência, Defesa Civil e geoprocessamento

## Princípio

O sistema é **estadual**. O município de sede da barragem não limita o impacto: uma estrutura em Chapada dos Guimarães pode exigir preparação em Cuiabá. Ver `docs/11-principio-estadual-e-sequencia.md`.

## Completude desta rodada

Nesta versão entram apenas indicadores já presentes no cadastro:

- **B** — categoria de risco, nível de emergência / DCE (quando houver)
- **C8** — material do reservatório (água vs. rejeito)
- **D1** — existência de PAE no SNISB

A dimensão **A** (pressão hidroclimática) fica vazia de propósito: será preenchida pelos coletores do **SIS Clima Saúde** e do **TITAN**. As demais parcelas de C e D dependem de mancha de inundação e de cadastros operacionais ainda não integrados. Por isso a completude média é baixa e a **confiabilidade** tende a `insuficiente` ou `parcial` — isso é diagnóstico honesto, não falha do cálculo.

## Distribuição por faixa

| Faixa | Barragens |
| --- | ---: |
| Roxo | 0 |
| Vermelho | 0 |
| Laranja | 0 |
| Amarelo | 115 |
| Verde | 1133 |

## Impacto extraterritorial

- Barragens com ao menos um município afetado diferente da sede: **493**
- Vínculos sede → município afetado: **1624** (arquivo `impacto_extraterritorial_mt.csv`)

A seção de controle por município é provisória (código Otto mais específico entre as barragens daquele município; Cuiabá usa a seção `896573` validada). Códigos grosseiros demais para decidir (relação Otto `contem`) saem na coluna `municipios_posicao_indeterminada`, exceto o complexo de Manso, forçado ao vínculo com Cuiabá/Várzea Grande pela geometria do reservatório. A BHO estadual completa e a mancha de inundação oficial substituirão este proxy.

## Maiores IDAP desta rodada (top 25)

| IDAP | Nível | Completude | Sede | Nome | Municípios afetados (n) |
| ---: | --- | ---: | --- | --- | ---: |
| 34 | Amarelo | 0,640 | Nossa Senhora do Livramento | T G de Souza | 1 |
| 33 | Amarelo | 0,650 | Nossa Senhora do Livramento | Barragem de Rejeitos Bom Futuro | 3 |
| 33 | Amarelo | 0,650 | Nossa Senhora do Livramento | Santa Maria | 3 |
| 32 | Amarelo | 0,640 | Nossa Senhora do Livramento | Bacia de Rejeitos | 1 |
| 30 | Amarelo | 0,600 | Nossa Senhora do Livramento | Barragem de Rejeito Estrela | 3 |
| 30 | Amarelo | 0,600 | Nossa Senhora do Livramento | Barragem de Rejeito Estrela 02 | 3 |
| 30 | Amarelo | 0,600 | Nossa Senhora do Livramento | Barragem de Rejeito Estrela 03 | 3 |
| 29 | Amarelo | 0,650 | Nossa Senhora do Livramento | BR SANTA 01 | 3 |
| 26 | Amarelo | 0,510 | Pontes e Lacerda | Fortuna | 3 |
| 24 | Amarelo | 0,650 | Cuiabá | Barragem Serrinha | 2 |
| 24 | Amarelo | 0,650 | Nossa Senhora do Livramento | BR BOSCO | 3 |
| 24 | Amarelo | 0,650 | Nossa Senhora do Livramento | BR PIRÂMIDE | 3 |
| 24 | Amarelo | 0,650 | Nossa Senhora do Livramento | BR SANTA FELICIDADE | 3 |
| 23 | Amarelo | 0,640 | Nossa Senhora do Livramento | BR02 | 1 |
| 23 | Amarelo | 0,550 | Nossa Senhora do Livramento | Barragem do Serginho | 0 |
| 22 | Amarelo | 0,610 | Nossa Senhora do Livramento | BACIA DE REJEITO MINERGOLD | 1 |
| 22 | Amarelo | 0,650 | Nossa Senhora do Livramento | BR SANTA FELICIDADE 02 | 3 |
| 22 | Amarelo | 0,610 | Nossa Senhora do Livramento | BR ÁGUA DE COCO | 1 |
| 22 | Amarelo | 0,610 | Nossa Senhora do Livramento | BR03 | 1 |
| 22 | Amarelo | 0,610 | Nossa Senhora do Livramento | Barragem Fazenda Aguassu | 1 |
| 22 | Amarelo | 0,620 | Rosário Oeste | VALE DOURADO | 4 |
| 21 | Amarelo | 0,600 | Cuiabá | BARRAGEM JVR | 3 |
| 21 | Amarelo | 0,620 | Cuiabá | Barragem TB | 3 |
| 21 | Amarelo | 0,620 | Nossa Senhora do Livramento | BR SANTA FELICIDADE 04 | 3 |
| 21 | Amarelo | 0,620 | Nossa Senhora do Livramento | Barragem GMX | 3 |

## Pressão hidroclimática (dimensão A)

- Barragens com linha SisClima/TITAN: **1248** (`hidro_barragens_mt.csv`, etapa 17).
- Aproximação espacial atual: município-sede (não bacia contribuinte).
- A3 (previsão) e A4 (percentil) ainda vazios no contrato atual.

## Próximos passos

1. Expandir BHO além da bacia do Cuiabá e agregar chuva/solo na drenagem.
2. Montar o piloto operacional do eixo Manso–Cuiabá.
