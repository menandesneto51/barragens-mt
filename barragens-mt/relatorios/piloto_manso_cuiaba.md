# Piloto operacional — eixo Manso–Cuiabá

Ciclo: **dado (SisClima/TITAN) → IDAP → alerta → ficha (esqueleto)**.
Emissão: 03/08/2026 07:53 (horário de Cuiabá).
Seção de controle: `896573`.
Região de saúde do piloto: **Baixada Cuiabana**.

## Recorte

- Barragens no piloto: **105** (afetam Cuiabá e/ou Várzea Grande, ou fazem parte do complexo UHE Manso).
- Textos do complexo Manso: **10**.

| Nível | Barragens |
| --- | ---: |
| Roxo | 0 |
| Vermelho | 0 |
| Laranja | 0 |
| Amarelo | 49 |
| Verde | 56 |

## Complexo UHE Manso

| IDAP | Nível | A | Nome | Municípios afetados |
| ---: | --- | ---: | --- | --- |
| 15 | Amarelo | 3 | UHE Manso - Barragem de Terra do Leito do Rio | Chapada dos Guimarães | Cuiabá | Várzea Grande |
| 15 | Amarelo | 3 | UHE Manso - Dique 2 | Cuiabá | Jangada | Nossa Senhora do Livramento | Rosário Oeste | Santo Antônio de Leverger | Várzea Grande |
| 15 | Amarelo | 3 | UHE Manso - Dique 3 | Cuiabá | Jangada | Nossa Senhora do Livramento | Rosário Oeste | Santo Antônio de Leverger | Várzea Grande |
| 15 | Amarelo | 3 | UHE Manso - Dique 4 | Cuiabá | Jangada | Nossa Senhora do Livramento | Rosário Oeste | Santo Antônio de Leverger | Várzea Grande |
| 15 | Amarelo | 3 | UHE Manso - Dique 5 | Cuiabá | Jangada | Nossa Senhora do Livramento | Rosário Oeste | Santo Antônio de Leverger | Várzea Grande |
| 15 | Amarelo | 3 | UHE Manso - Dique 6 | Cuiabá | Jangada | Nossa Senhora do Livramento | Rosário Oeste | Santo Antônio de Leverger | Várzea Grande |
| 15 | Amarelo | 3 | UHE Manso - Dique 7 | Cuiabá | Jangada | Nossa Senhora do Livramento | Rosário Oeste | Santo Antônio de Leverger | Várzea Grande |
| 14 | Amarelo | 3 | UHE Manso - Barragem da Margem Direita | Chapada dos Guimarães | Cuiabá | Várzea Grande |
| 14 | Amarelo | 3 | UHE Manso - Barragem da Margem Esquerda | Chapada dos Guimarães | Cuiabá | Várzea Grande |
| 13 | Verde | 0 | UHE Manso - Dique 1 | Juara | Nobres | Novo Horizonte do Norte | Porto dos Gaúchos | São José do Rio Claro |

## Maiores IDAP do piloto (top 20)

| IDAP | Nível | Completude | Sede | Nome | Arquivo alerta |
| ---: | --- | ---: | --- | --- | --- |
| 28 | Amarelo | 0,680 | Nossa Senhora do Livramento | Barragem de Rejeitos Bom Futuro | `alertas/piloto/amarelo_5603.txt` |
| 27 | Amarelo | 0,680 | Nossa Senhora do Livramento | Santa Maria | `alertas/piloto/amarelo_5563.txt` |
| 24 | Amarelo | 0,680 | Nossa Senhora do Livramento | BR SANTA 01 | `alertas/piloto/amarelo_5573.txt` |
| 24 | Amarelo | 0,630 | Nossa Senhora do Livramento | Barragem de Rejeito Estrela | `alertas/piloto/amarelo_5560.txt` |
| 24 | Amarelo | 0,630 | Nossa Senhora do Livramento | Barragem de Rejeito Estrela 02 | `alertas/piloto/amarelo_5562.txt` |
| 24 | Amarelo | 0,630 | Nossa Senhora do Livramento | Barragem de Rejeito Estrela 03 | `alertas/piloto/amarelo_5559.txt` |
| 19 | Verde | 0,680 | Nossa Senhora do Livramento | BR BOSCO | `alertas/piloto/verde_586.txt` |
| 18 | Verde | 0,680 | Nossa Senhora do Livramento | BR PIRÂMIDE | `alertas/piloto/verde_21940.txt` |
| 18 | Verde | 0,680 | Nossa Senhora do Livramento | BR SANTA FELICIDADE | `alertas/piloto/verde_588.txt` |
| 18 | Amarelo | 0,680 | Cuiabá | Barragem Serrinha | `alertas/piloto/amarelo_26138.txt` |
| 17 | Verde | 0,650 | Rosário Oeste | VALE DOURADO | `alertas/piloto/verde_8006.txt` |
| 16 | Verde | 0,680 | Nossa Senhora do Livramento | BR SANTA FELICIDADE 02 | `alertas/piloto/verde_22009.txt` |
| 16 | Amarelo | 0,650 | Cuiabá | Barragem TB | `alertas/piloto/amarelo_26146.txt` |
| 15 | Amarelo | 0,630 | Cuiabá | BARRAGEM JVR | `alertas/piloto/amarelo_26131.txt` |
| 15 | Verde | 0,650 | Nossa Senhora do Livramento | Barragem GMX | `alertas/piloto/verde_34856.txt` |
| 15 | Verde | 0,500 | Nossa Senhora do Livramento | Barragem_Valdenir2 | `alertas/piloto/verde_27624.txt` |
| 15 | Verde | 0,650 | Nossa Senhora do Livramento | MULTI 1 | `alertas/piloto/verde_26171.txt` |
| 15 | Amarelo | 0,530 | Chapada dos Guimarães | UHE Manso - Barragem de Terra do Leito do Rio | `alertas/piloto/amarelo_4436.txt` |
| 15 | Amarelo | 0,530 | Chapada dos Guimarães | UHE Manso - Dique 2 | `alertas/piloto/amarelo_20601.txt` |
| 15 | Amarelo | 0,530 | Chapada dos Guimarães | UHE Manso - Dique 3 | `alertas/piloto/amarelo_20602.txt` |

## Ficha rápida (esqueleto operacional)

Campos mínimos a preencher no simulado (docs/05 §5.4) — ainda sem formulário web:

1. Identificação do evento / barragem / municípios atingidos
2. Horário de início da resposta e responsável municipal
3. Unidades de saúde afetadas ou isoladas (CNES)
4. Óbitos, feridos, desalojados, desaparecidos (contagens)
5. Interrupção de água / energia / acesso
6. Necessidades imediatas (transporte, abrigo, água potável, insumos)

Formulário de simulado: [`painel/ficha_rapida.html`](../painel/ficha_rapida.html).
Os textos em `alertas/piloto/` já trazem as ações recomendadas por nível e a
ressalva obrigatória de não-evacuação.

## Limitações deste ciclo

- C1/C2/C4–C7 ainda sem mancha oficial; C3 usa CNES municipal do eixo (proxy).
- Hidro: máximo entre sede + municípios a montante (Otto); não é agregação areal BHO.
- Contatos: esqueleto em `contatos_institucionais_piloto.csv` — quase todas não alertáveis até validação telefônica.
- Proxy Otto ainda inclui falsos positivos em alguns códigos grosseiros.
