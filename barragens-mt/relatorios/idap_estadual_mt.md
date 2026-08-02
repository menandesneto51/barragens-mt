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
| Amarelo | 129 |
| Verde | 1119 |

## Impacto extraterritorial

- Barragens com ao menos um município afetado diferente da sede: **493**
- Vínculos sede → município afetado: **1624** (arquivo `impacto_extraterritorial_mt.csv`)

A seção de controle por município é provisória (código Otto mais específico entre as barragens daquele município; Cuiabá usa a seção `896573` validada). Códigos grosseiros demais para decidir (relação Otto `contem`) saem na coluna `municipios_posicao_indeterminada`, exceto o complexo de Manso, forçado ao vínculo com Cuiabá/Várzea Grande pela geometria do reservatório. A BHO estadual completa e a mancha de inundação oficial substituirão este proxy.

## Maiores IDAP desta rodada (top 25)

| IDAP | Nível | Completude | Sede | Nome | Municípios afetados (n) |
| ---: | --- | ---: | --- | --- | ---: |
| 39 | Amarelo | 0,710 | Nossa Senhora do Livramento | T G de Souza | 1 |
| 35 | Amarelo | 0,710 | Nossa Senhora do Livramento | Bacia de Rejeitos | 1 |
| 35 | Amarelo | 0,720 | Nossa Senhora do Livramento | Barragem de Rejeitos Bom Futuro | 3 |
| 33 | Amarelo | 0,720 | Nossa Senhora do Livramento | Santa Maria | 3 |
| 31 | Amarelo | 0,720 | Nossa Senhora do Livramento | BR SANTA 01 | 3 |
| 30 | Amarelo | 0,670 | Nossa Senhora do Livramento | Barragem de Rejeito Estrela | 3 |
| 30 | Amarelo | 0,670 | Nossa Senhora do Livramento | Barragem de Rejeito Estrela 02 | 3 |
| 30 | Amarelo | 0,670 | Nossa Senhora do Livramento | Barragem de Rejeito Estrela 03 | 3 |
| 27 | Amarelo | 0,680 | Nossa Senhora do Livramento | BACIA DE REJEITO MINERGOLD | 1 |
| 27 | Amarelo | 0,680 | Nossa Senhora do Livramento | BR ÁGUA DE COCO | 1 |
| 27 | Amarelo | 0,680 | Nossa Senhora do Livramento | BR03 | 1 |
| 26 | Amarelo | 0,720 | Cuiabá | Barragem Serrinha | 2 |
| 26 | Amarelo | 0,720 | Nossa Senhora do Livramento | BR BOSCO | 3 |
| 26 | Amarelo | 0,720 | Nossa Senhora do Livramento | BR PIRÂMIDE | 3 |
| 26 | Amarelo | 0,720 | Nossa Senhora do Livramento | BR SANTA FELICIDADE | 3 |
| 26 | Amarelo | 0,710 | Nossa Senhora do Livramento | BR02 | 1 |
| 26 | Amarelo | 0,680 | Nossa Senhora do Livramento | Barragem Fazenda Aguassu | 1 |
| 26 | Amarelo | 0,580 | Poconé | BACIA DE REJEITOS SÃO BENTO | 0 |
| 26 | Amarelo | 0,670 | Poconé | BR ISMAEL | 1 |
| 26 | Amarelo | 0,580 | Poconé | Barragem de Rejeitos SB 02 | 0 |
| 26 | Amarelo | 0,670 | Poconé | Davi | 1 |
| 26 | Amarelo | 0,510 | Pontes e Lacerda | Fortuna | 3 |
| 25 | Amarelo | 0,620 | Nossa Senhora do Livramento | Barragem do Serginho | 0 |
| 25 | Amarelo | 0,680 | Nossa Senhora do Livramento | Mineração Livramento | 1 |
| 25 | Amarelo | 0,640 | Poconé | Barragem Barba 02 | 1 |

## Pressão hidroclimática (dimensão A)

- Barragens com linha SisClima/TITAN: **1248** (`hidro_barragens_mt.csv`, etapa 17).
- Onde a etapa 39 rodou: chuva A1–A4 no **ponto da barragem** (INMET ≤80 km ou Open-Meteo pontual); demais usam município-sede/montante.
- Alertas Cemaden/INMET/ANA do contrato municipal são preservados na mescla.

## Próximos passos

1. Expandir BHO além da bacia do Cuiabá e agregar chuva/solo na drenagem.
2. Preferir série INMET/ANA HidroWeb quando a API diária estiver estável.
