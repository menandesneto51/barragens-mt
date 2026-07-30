# 11. Princípio estadual, impacto extraterritorial e sequência de implantação

> Decisão de produto alinhada em 29/07/2026. Complementa `docs/01-visao-geral.md` e
> reordena a Fase 1 de `docs/08-roadmap.md`.

## 11.1 Escopo territorial

O VIGIBARRAGENS–MT / Saúde 360 é um **sistema estadual**. O inventário, o IDAP, os alertas
e a vigilância pós-desastre cobrem Mato Grosso como um todo — não um município-piloto
como unidade de desenho.

O piloto municipal (Cuiabá e eixo Manso) é um **recorte de validação operacional**, não o
limite do sistema. Ele só é montado depois que a base estadual e os coletores
hidrometeorológicos estiverem ligados.

## 11.2 Impacto extraterritorial

A pergunta sanitária correta não é “quais barragens estão no município X”, e sim
**“quais barragens podem atingir o município X”**.

| Situação | Exemplo | Tratamento no sistema |
| --- | --- | --- |
| Barragem em outro município do MT, a montante na mesma bacia | UHE Manso (Chapada dos Guimarães) → Cuiabá e Várzea Grande | Incluída no recorte a jusante por topologia de drenagem (Otto Pfafstetter / BHO) |
| Barragem no município, mas que não drena para a sede urbana | Parte das barragens de Cuiabá a jusante da seção de controle | Fora do recorte de exposição da mancha urbana central; permanece no inventário estadual |
| Barragem em outro estado cuja calha entra em MT | A validar caso a caso nas bacias de fronteira | Escopo futuro: expandir o inventário além do filtro UF=MT quando a topologia indicar impacto em território mato-grossense |
| Proximidade geográfica sem vínculo hidrológico | Barragens de Poconé vs. Cuiabá | Excluídas do vínculo de impacto; drenam por ramo distinto |

**Regra de ouro:** limite municipal nunca é critério de exclusão de ameaça. É apenas o
lugar onde a estrutura está cadastrada.

## 11.3 Sequência de trabalho (ordem fixa)

| Ordem | Frente | Objetivo | Dependência |
| --- | --- | --- | --- |
| 1 | **Base estadual + IDAP** | Calcular IDAP para as ~1.248 barragens de MT; mapear municípios potencialmente afetados a jusante; declarar lacunas (chuva, mancha) | Inventário SNISB/SIGBM já coletado |
| 2 | **Coletores hidrometeorológicos** | Alimentar a dimensão A do IDAP com dados já validados do **SIS Clima Saúde** e do **TITAN** (chuva, solo, alertas INMET/Cemaden/ANA) | Sistemas CIEVS MT em operação |
| 3 | **Piloto operacional** | Percorrer o ciclo completo (dado → índice → alerta → ficha) no eixo Manso–Cuiabá, com hidro real — `scripts/18_piloto_manso_cuiaba.py` | Itens 1 e 2 |

Não inverter essa ordem: um piloto sem base estadual recria o erro de recortar por
município; um piloto sem hidro classifica alerta com completude estruturalmente baixa.

## 11.4 Fontes hidrometeorológicas já validadas

> Consumidas por `scripts/17_hidro_sisclima_titan.py` → `hidro_barragens_mt.csv` → dimensão A do IDAP. Detalhe em `docs/12-integracao-sisclima-titan.md`.

Repositórios de referência no ambiente CIEVS MT (não duplicar coleta):

| Sistema | Caminho de referência | O que o VIGIBARRAGENS consome |
| --- | --- | --- |
| **SIS Clima Saúde** | `CIEVS MT/SIS-Monitoramento-Clima-Saude-GITHUB-LIMPO` | Precipitação municipal, Open-Meteo, pipeline em tempo quase real |
| **TITAN** | integração documentada em `docs/INTEGRACAO_TITAN_SOLO_ALERTAS.md` do SIS | Saturação do solo, alertas INMET/Cemaden, risco hidrológico ANA (`ana_risco_municipal`, `hidro_risco_municipal`) |

Mapeamento preliminar → indicadores do IDAP:

| Indicador IDAP | Origem preferencial |
| --- | --- |
| A1 / A2 — chuva 24 h / 72 h | SIS Clima (Open-Meteo / estações) + Cemaden via TITAN |
| A3 — chuva prevista | SIS Clima / INMET |
| A5 — saturação antecedente | TITAN `indice_saturacao_solo` |
| A6 — razão nível / cota de alerta | ANA telemetria via TITAN/SIS (`ana_risco_municipal`) |
| Regras R0x de chuva extrema | Alertas INMET + Cemaden consolidados no TITAN |

## 11.5 O que o Produto 04 representa neste desenho

O relatório ABNT de Cuiabá é um **produto analítico** do Vigidesastres, não o perímetro do
sistema. Ele usa o eixo Manso–Cuiabá como caso crítico de impacto extraterritorial. A
plataforma operacional, porém, nasce estadual.
