# 3. IDAP-Barragens — Índice Dinâmico de Alerta e Prontidão

> **Aviso metodológico que vale para todo este documento.** Os pesos, os limiares e as
> faixas apresentados são a versão `0.1.0-metodologica`. Eles foram construídos a partir de
> referências públicas — limiares de chuva usados por INMET e Cemaden, escala 0–10 de
> anomalias do formulário do SIGBM, critério de 30 minutos da Zona de Autossalvamento na
> Resolução ANM nº 95/2022, classificação CRI × DPA da Resolução CNRH nº 143/2012 — mas
> **nenhum valor aqui é oficial**. Toda faixa numérica proposta está marcada como
> **proposta a validar**. A calibração precisa de validação por painel de especialistas
> antes de sustentar decisão operacional (§3.11).

## 3.1 Definição e delimitação

O IDAP-Barragens é um índice de **0 a 100** que responde a uma única pergunta:

> Qual deve ser a postura do setor saúde em relação a esta barragem, nas próximas horas e
> dias, dado tudo o que se sabe agora?

Ele **não** é, e não deve ser apresentado como:

| Não é | Razão |
| --- | --- |
| Probabilidade de rompimento | Exigiria modelo de engenharia calibrado e instrumentação da estrutura |
| Índice de risco de ruptura | O mesmo, e o nome sugeriria autoridade técnica que a plataforma não tem |
| Substituto de Categoria de Risco (CRI) ou Dano Potencial Associado (DPA) | CRI e DPA são classificações regulatórias oficiais; o IDAP as **consome** como indicadores B1 e parte de C |
| Base para ordem de evacuação | Evacuação é ato de autoridade (`docs/01-visao-geral.md`, §1.2) |

É um índice **dinâmico**: recalculado em rotina, com valor que muda ao longo do dia
conforme chove, conforme o nível sobe e conforme o empreendedor declara.

## 3.2 Estrutura geral

| Dimensão | Nome | Pontos | O que responde | Volatilidade |
| --- | --- | ---: | --- | --- |
| **A** | Pressão hidroclimática | 30 | O que está acontecendo com a chuva e com o rio? | Alta — muda em horas |
| **B** | Condição da barragem | 30 | O que a estrutura e os órgãos declaram? | Média — muda em dias |
| **C** | Impacto sanitário potencial | 25 | Quem e o que seria atingido? | Baixa — muda em meses |
| **D** | Déficit de capacidade de resposta | 15 | O que falta para responder? | Baixa a média |
| | **Total** | **100** | | |

A lógica da divisão de pesos entre dimensões: **A + B = 60 pontos** representam o
*gatilho* (o que pode acontecer agora), e **C + D = 40 pontos** representam a
*consequência e o preparo* (o que aconteceria se acontecesse, e quão pronta está a rede).
Assim, uma barragem em situação hidrológica e estrutural tranquila nunca passa de 40 pontos
por exposição e déficit, o que a mantém abaixo da faixa Laranja — corretamente, porque não
há evento em curso. E uma barragem em situação crítica de gatilho, com pouca exposição,
chega a 60 pontos, entrando em Vermelho — também corretamente, porque a estrutura pode
romper e a plataforma não tem autoridade para dizer que não vai.

---

## 3.3 Dimensão A — Pressão hidroclimática (30 pontos)

### 3.3.1 Quadro de pontuação

| Código | Indicador | Pontos |
| --- | --- | ---: |
| A1 | Chuva acumulada em 24 h | 0–5 |
| A2 | Chuva acumulada em 72 h | 0–5 |
| A3 | Chuva prevista para 24–72 h | 0–5 |
| A4 | Percentil climatológico da chuva | 0–4 |
| A5 | Saturação antecedente do solo | 0–4 |
| A6 | Nível ou vazão do rio a jusante | 0–4 |
| A7 | Persistência da condição adversa | 0–3 |
| | **Total** | **30** |

### 3.3.2 A1 — Chuva acumulada em 24 h (0–5)

| Aspecto | Definição |
| --- | --- |
| Fonte | INMET (estações automáticas), Cemaden (pluviômetros) e NASA GPM-IMERG Early Run |
| Unidade | mm |
| Janela temporal | 24 h móveis, encerradas na última observação disponível |
| Agregação espacial | Média ponderada por área dos pixels/estações da bacia contribuinte da barragem |
| Recálculo | A cada 30 min (satélite) ou a cada hora (estações) |
| Dado ausente | Se nenhuma das três fontes tiver dado na janela, o indicador é lacuna: 0 ponto e redução da completude. **Não** se assume "não chuveu" |
| Implementação atual | Etapa 39 (`telemetria_hidro_a`) preenche A1–A4 no ponto da barragem (INMET próximo ou Open-Meteo); etapa 17 mantém SisClima municipal + alertas. Ver `docs/02-fontes-de-dados.md` §2.5.8 |

Faixas de pontuação (**proposta a validar**):

| Acumulado em 24 h | Pontos | Rótulo | Justificativa da fronteira |
| --- | ---: | --- | --- |
| < 10 mm | 0 | chuva fraca ou ausente | Abaixo do que altera balanço hídrico de reservatório |
| 10 a < 30 mm | 1 | chuva moderada | |
| 30 a < 50 mm | 2 | chuva forte | 30 mm/24 h é limiar comum de atenção operacional |
| 50 a < 80 mm | 3 | chuva muito forte | 50 mm/24 h é limiar frequente de alerta hidrológico |
| 80 a < 120 mm | 4 | chuva extrema | |
| >= 120 mm | 5 | chuva excepcional | Acima de 100 mm/24 h já caracteriza chuva extrema em avisos meteorológicos |

### 3.3.3 A2 — Chuva acumulada em 72 h (0–5)

| Aspecto | Definição |
| --- | --- |
| Fonte | Mesma de A1 |
| Unidade | mm |
| Janela temporal | 72 h móveis |
| Por que existe além de A1 | Barragem responde a volume acumulado, não só a intensidade. Três dias de 40 mm somam 120 mm e enchem um reservatório que um único dia de 60 mm não encheria |
| Recálculo | Igual a A1 |
| Dado ausente | Lacuna, como em A1. Se houver dado parcial (2 dos 3 dias), usar o acumulado parcial e registrar a cobertura da janela como observação |

Faixas (**proposta a validar**):

| Acumulado em 72 h | Pontos | Rótulo |
| --- | ---: | --- |
| < 25 mm | 0 | acumulado baixo |
| 25 a < 60 mm | 1 | acumulado moderado |
| 60 a < 100 mm | 2 | acumulado alto |
| 100 a < 150 mm | 3 | acumulado muito alto |
| 150 a < 250 mm | 4 | acumulado extremo |
| >= 250 mm | 5 | acumulado excepcional |

### 3.3.4 A3 — Chuva prevista para 24–72 h (0–5)

| Aspecto | Definição |
| --- | --- |
| Fonte | INMET, boletim de risco geo-hidrológico do Cemaden e GloFAS como contexto regional |
| Unidade | mm previstos na janela |
| Janela temporal | Próximas 24 a 72 h |
| Recálculo | A cada rodada de modelo, 2 a 4 vezes por dia |
| Dado ausente | Lacuna. Previsão indisponível é situação comum e não deve inflar nem desinflar o índice |
| Ressalva | Previsão tem incerteza crescente com o horizonte. A plataforma deve exibir, junto ao valor, a fonte e a hora da rodada |

Faixas (**proposta a validar** — mais tolerantes que A1 e A2 porque previsão erra):

| Chuva prevista | Pontos | Rótulo |
| --- | ---: | --- |
| < 20 mm | 0 | previsão sem relevância hidrológica |
| 20 a < 50 mm | 1 | previsão moderada |
| 50 a < 90 mm | 2 | previsão alta |
| 90 a < 140 mm | 3 | previsão muito alta |
| 140 a < 200 mm | 4 | previsão extrema |
| >= 200 mm | 5 | previsão excepcional |

### 3.3.5 A4 — Percentil climatológico da chuva (0–4)

| Aspecto | Definição |
| --- | --- |
| Fonte | Normais climatológicas do INMET e série histórica das estações da bacia; GPM-IMERG Final Run como alternativa onde não há estação |
| Unidade | Percentil de 0 a 100 |
| Janela temporal | Comparação do acumulado observado (24 h ou 72 h, o mais severo) com a distribuição histórica do **mesmo período do ano** |
| Por que existe | 60 mm em janeiro em Cuiabá é rotina; 60 mm em julho é evento raro. Sem normalização climatológica, o índice trata os dois igual e superalerta na estação chuvosa |
| Recálculo | Junto com A1 e A2 |
| Dado ausente | Lacuna. Exige série histórica de pelo menos 15 anos na região (**proposta a validar**); onde não houver, o indicador fica permanentemente em lacuna e isso deve constar do relatório de pendências |

Faixas (**proposta a validar**):

| Percentil do acumulado observado | Pontos | Rótulo |
| --- | ---: | --- |
| < p50 | 0 | abaixo da mediana climatológica |
| p50 a < p75 | 1 | acima da mediana |
| p75 a < p90 | 2 | acima do percentil 75 |
| p90 a < p98 | 3 | acima do percentil 90 |
| >= p98 | 4 | evento raro para a época |

### 3.3.6 A5 — Saturação antecedente do solo (0–4)

| Aspecto | Definição |
| --- | --- |
| Fonte | Índice de precipitação antecedente derivado de IMERG/Cemaden; produto de umidade de solo por satélite ou modelo, onde disponível |
| Unidade | Índice normalizado de 0 a 1 |
| Janela temporal | 30 dias antecedentes, com decaimento exponencial (peso maior para os dias recentes) |
| Por que existe | Solo saturado converte chuva em escoamento quase integralmente. A mesma chuva produz vazão muito diferente em solo seco e em solo saturado |
| Recálculo | Diário |
| Dado ausente | Lacuna |

Faixas (**proposta a validar**):

| Índice de saturação | Pontos | Rótulo |
| --- | ---: | --- |
| < 0,40 | 0 | solo seco |
| 0,40 a < 0,60 | 1 | solo parcialmente úmido |
| 0,60 a < 0,75 | 2 | solo úmido |
| 0,75 a < 0,90 | 3 | solo muito úmido |
| >= 0,90 | 4 | solo saturado |

### 3.3.7 A6 — Nível ou vazão do rio a jusante (0–4)

| Aspecto | Definição |
| --- | --- |
| Fonte | ANA — Rede Hidrometeorológica Nacional e telemetria; réguas da Defesa Civil |
| Unidade | Razão entre o nível observado e a **cota de alerta** da estação de referência a jusante |
| Janela temporal | Última leitura telemétrica |
| Por que existe | Um rio já em cota de alerta amplifica qualquer contribuição adicional da barragem, e reduz o tempo disponível para evacuação por via terrestre |
| Recálculo | A cada leitura, 15 min a 1 h |
| Dado ausente | Lacuna. Depende de haver estação a jusante com cota de alerta cadastrada — pendência mapeada em `docs/02-fontes-de-dados.md`, §2.11 |

Faixas (**proposta a validar**):

| Razão nível / cota de alerta | Pontos | Rótulo |
| --- | ---: | --- |
| < 0,70 | 0 | nível normal |
| 0,70 a < 0,90 | 1 | nível em elevação |
| 0,90 a < 1,00 | 2 | aproximando-se da cota de alerta |
| 1,00 a < 1,20 | 3 | acima da cota de alerta |
| >= 1,20 | 4 | acima da cota de inundação |

### 3.3.8 A7 — Persistência da condição adversa (0–3)

| Aspecto | Definição |
| --- | --- |
| Fonte | Mesma de A1 |
| Unidade | Dias consecutivos com chuva diária >= 20 mm (limiar **proposta a validar**) |
| Janela temporal | 10 dias antecedentes |
| Por que existe | Chuva persistente esgota a capacidade de amortecimento do reservatório e a resistência da operação: turnos de vigilância, drenagem, acesso para inspeção |
| Recálculo | Diário |
| Dado ausente | Lacuna |

Faixas (**proposta a validar**):

| Dias consecutivos adversos | Pontos | Rótulo |
| --- | ---: | --- |
| 0 ou 1 | 0 | sem persistência |
| 2 | 1 | dois dias consecutivos |
| 3 ou 4 | 2 | três a quatro dias consecutivos |
| >= 5 | 3 | cinco dias ou mais |

---

## 3.4 Dimensão B — Condição da barragem (30 pontos)

### 3.4.1 Quadro de pontuação

| Código | Indicador | Pontos |
| --- | --- | ---: |
| B1 | Categoria de Risco (CRI) oficial | 0–5 |
| B2 | Nível oficial de emergência | 0–10 |
| B3 | Ausência de estabilidade declarada | 0–5 |
| B4 | Anomalia estrutural ativa | 0–5 |
| B5 | Elevação anormal do reservatório | 0–3 |
| B6 | Falha ou ausência de telemetria | 0–2 |
| | **Total** | **30** |

B2 concentra 10 dos 30 pontos da dimensão — um terço — porque é o único indicador em que
**o responsável técnico pela estrutura afirma oficialmente que há um problema**. É a
informação de maior valor probatório disponível à plataforma.

### 3.4.2 B1 — Categoria de Risco (CRI) oficial (0–5)

| Aspecto | Definição |
| --- | --- |
| Fonte | SNISB/ANA, campo `CATEGORIA_RISCO`; SIGBM/ANM, campo `Categoria de Risco - CRI` |
| Unidade | Categoria |
| Janela temporal | Último cadastro publicado |
| Recálculo | A cada carga do inventário (diária) |
| Dado ausente | **Campo vazio** (`None`) é lacuna: 0 ponto. **Categoria declarada de desconhecimento** (`Não Classificado`) rende 2 pontos de precaução. A distinção importa: 258 das 1.248 barragens de MT estão declaradas como `Não Classificado`, o que é um fato cadastral, não uma ausência de dado |

| Categoria | Pontos | Racional |
| --- | ---: | --- |
| Alto / Alta | 5 | |
| Médio / Média | 3 | |
| Baixo / Baixa | 1 | Piso de 1 ponto porque CRI baixa não é risco nulo |
| Não Classificado | 2 | Precaução: não se pode afirmar risco baixo em estrutura que o órgão nunca classificou |
| Não se Aplica | 1 | Estrutura fora do escopo de classificação; mantém o piso |

### 3.4.3 B2 — Nível oficial de emergência (0–10)

| Aspecto | Definição |
| --- | --- |
| Fonte | SIGBM/ANM, campo `Nível de Emergência`; SNISB, campo `NIVEL_PERIGO`; comunicação direta do empreendedor |
| Unidade | Categoria |
| Janela temporal | Declaração vigente |
| Recálculo | A cada carga (diária) **e imediatamente** ao receber comunicação oficial — este é o único indicador que justifica recálculo por evento, fora da rotina |
| Dado ausente | Lacuna. Atenção: para as 1.065 barragens de MT que não são de mineração, o campo `NIVEL_PERIGO` está vazio em 99% dos casos, o que significa que B2 é lacuna para quase todo o inventário. Esse é o maior gargalo de informação do índice |

| Categoria | Pontos | Observação |
| --- | ---: | --- |
| Sem emergência / Normal | 0 | |
| Atenção / Nível de Atenção | 3 | |
| Alerta / Nível de Alerta | 5 | |
| Emergência Nível 1 | 7 | |
| `Emergência` sem nível informado (SNISB) | 7 | Leitura conservadora: trata como nível 1 e abre pendência de confirmação com o fiscalizador |
| Emergência Nível 2 | 9 | Dispara a regra R01 |
| Emergência Nível 3 | 10 | Dispara a regra R01 |

### 3.4.4 B3 — Ausência de estabilidade declarada (0–5)

| Aspecto | Definição |
| --- | --- |
| Fonte | SIGBM/ANM — `Status DCE RISR`, `Status DCE RPSB`, `Status da DCO Atual` |
| Unidade | Categoria (a pior situação entre as três declarações) |
| Janela temporal | Campanha de declaração vigente |
| Recálculo | A cada carga (diária) |
| Dado ausente | O SIGBM usa a string `-` como sentinela de ausência. `-` é tratado como `Sem informação` e rende 3 pontos, porque em um regime de declaração obrigatória a ausência de declaração **é** um sinal. Campo verdadeiramente nulo é lacuna |

| Situação | Pontos |
| --- | ---: |
| Atestada e vigente (`Atestado`) | 0 |
| Não se aplica a esse tipo de barragem | 0 |
| Atestada mas vencida | 3 |
| Sem informação (`-`) | 3 |
| Atestada com ressalva | 5 |
| Não atestada / Não enviada | 5 |

### 3.4.5 B4 — Anomalia estrutural ativa (0–5)

| Aspecto | Definição |
| --- | --- |
| Fonte | SIGBM/ANM — `Percolação`, `Deformações e recalque`, `Deteriorização dos taludes / paramentos`, `Drenagem Interna`, `Confiabilidade das estruturas extravasora`. Também relatórios de inspeção quando disponíveis |
| Unidade | Pior nota entre as anomalias, na escala 0–10 do próprio formulário do SIGBM |
| Janela temporal | Última declaração de condição de estabilidade ou última inspeção |
| Por que "pior nota" e não média | Anomalia não se compensa: uma percolação com carreamento de material não fica menos grave porque os taludes estão bons |
| Recálculo | A cada carga (diária) e a cada inspeção registrada |
| Dado ausente | Lacuna. O valor `Não se aplica a esse tipo de barragem` (32 dos 183 registros de MT) deve ser convertido em nota 0 pelo ETL, com registro da conversão |

| Pior nota do SIGBM | Pontos | Rótulo |
| --- | ---: | --- |
| 0 | 0 | sem anomalia registrada |
| 1 a < 4 | 2 | anomalia com medidas corretivas em implantação |
| 4 a < 7 | 4 | anomalia sem medidas corretivas implantadas |
| >= 7 | 5 | anomalia com potencial de comprometer a segurança |

O limiar de nota **4** define "anomalia ativa" para efeito das regras determinísticas R03 e
R04 (**proposta a validar**).

### 3.4.6 B5 — Elevação anormal do reservatório (0–3)

| Aspecto | Definição |
| --- | --- |
| Fonte | Telemetria do empreendedor; SIGBM (`Volume atual do Reservatório` ÷ `Capacidade Total do Reservatório`) |
| Unidade | Razão volume atual / capacidade total, ou cota atual / cota máxima operacional |
| Janela temporal | Última leitura |
| Recálculo | A cada leitura telemétrica; diário quando só houver declaração |
| Dado ausente | Lacuna. Hoje disponível para 175 das 183 barragens de mineração e para praticamente nenhuma das demais |

| Razão | Pontos | Rótulo |
| --- | ---: | --- |
| < 0,80 | 0 | reservatório em faixa operacional |
| 0,80 a < 0,90 | 1 | reservatório alto |
| 0,90 a < 0,98 | 2 | reservatório muito alto |
| >= 0,98 | 3 | reservatório no limite ou vertendo |

### 3.4.7 B6 — Falha ou ausência de telemetria (0–2)

| Aspecto | Definição |
| --- | --- |
| Fonte | SIGBM/ANM, campo `Instrumentação`; monitoramento do próprio fluxo de telemetria pela plataforma |
| Unidade | Categoria |
| Janela temporal | Últimas 72 h de transmissão |
| Por que pontua pouco | Falta de telemetria não aumenta o risco físico da estrutura; aumenta a **cegueira** sobre ela. Por isso pesa 2 pontos no índice e, ao mesmo tempo, dispara a regra técnica R06, que é o canal adequado para tratar o problema |
| Recálculo | Horário |
| Dado ausente | Lacuna |

| Situação | Pontos | Correspondência no SIGBM |
| --- | ---: | --- |
| Conforme projeto e transmitindo | 0 | `Existe instrumentação de acordo com o projeto técnico` |
| Falha parcial, em instalação ou dados desatualizados | 1 | `Existe instrumentação em desacordo com o projeto, porém em processo de instalação`; `Barragem não instrumentada de acordo com o projeto` |
| Ausente ou sem transmissão | 2 | `Existe instrumentação em desacordo com o projeto sem processo de instalação`; `Barragem não instrumentada em desacordo com o projeto` |

---

## 3.5 Dimensão C — Impacto sanitário potencial (25 pontos)

### 3.5.1 Distribuição proposta dos 25 pontos e sua justificativa

| Código | Indicador | Pontos | Por que este peso |
| --- | --- | ---: | --- |
| C1 | População residente na ZAS | 5 | Maior peso da dimensão: é o número de vidas em jogo, a variável de que todas as outras são qualificadoras |
| C2 | População vulnerável na ZAS | 3 | Vulnerabilidade multiplica o dano por pessoa exposta e determina a logística (transporte de acamado, diálise, oxigênio), mas é modificador de C1, não substituto |
| C3 | Unidades de saúde ameaçadas | 4 | Peso alto porque perder o nó assistencial converte um evento localizado em crise regional: quem sobrevive à onda perde o atendimento |
| C4 | Captações de água ameaçadas | 3 | Converte evento agudo em crise sanitária prolongada, e atinge população muito maior que a da mancha — dias a semanas de desabastecimento em toda a sede municipal |
| C5 | Serviços essenciais não assistenciais ameaçados | 2 | Relevante (energia, ETA/ETE, escolas, pontes), mas o efeito sobre saúde é indireto e mediado |
| C6 | Tempo de chegada da onda | 4 | Peso alto porque define se **existe** possibilidade de resposta. Abaixo de 30 min, nenhuma evacuação assistida é viável e a única defesa é o autossalvamento — é o critério que a Resolução ANM nº 95/2022 usa para definir a própria ZAS |
| C7 | Possibilidade de isolamento rodoviário | 2 | Determina se a ajuda chega e se o paciente sai, mas há alternativas (aéreo, fluvial) que atenuam |
| C8 | Presença de contaminantes ou rejeitos | 2 | Muda a natureza do agravo e o painel laboratorial; peso menor porque o efeito é sobre o *tipo* de resposta, não sobre a magnitude imediata |
| | **Total** | **25** | |

O princípio da distribuição: **magnitude (C1) e viabilidade de resposta (C6) recebem os
maiores pesos, seguidos pela integridade da rede que responde (C3)**. Os demais qualificam.

### 3.5.2 C1 — População residente na ZAS (0–5)

| Aspecto | Definição |
| --- | --- |
| Fonte | Setores censitários do IBGE recortados pela mancha de inundação; `Número de pessoas possivelmente afetadas a jusante` do SIGBM como piso quando não há mancha |
| Unidade | Habitantes |
| Janela temporal | Estático; revisto a cada atualização de mancha ou de setor censitário |
| Recálculo | A cada atualização de mancha, ou anual |
| Dado ausente | Lacuna. Situação atual da maioria das barragens de MT, por falta de mancha modelada |

| População na ZAS | Pontos |
| --- | ---: |
| 0 | 0 |
| 1 a 49 | 1 |
| 50 a 199 | 2 |
| 200 a 999 | 3 |
| 1.000 a 4.999 | 4 |
| >= 5.000 | 5 |

Faixas em escala aproximadamente logarítmica (**proposta a validar**), porque o salto
relevante para a resposta é de ordem de grandeza, não linear.

### 3.5.3 C2 — População vulnerável na ZAS (0–3)

| Aspecto | Definição |
| --- | --- |
| Fonte | IBGE, e-SUS APS (cadastro individual e domiciliar), CNES (pacientes dependentes de tecnologia), CadÚnico |
| Unidade | Proporção de 0 a 1 |
| Definição de vulnerável | Menores de 5 anos, 60 anos ou mais, gestantes, pessoas com deficiência, acamados, dependentes de energia elétrica para equipamento de suporte, pacientes em diálise, pacientes dependentes de oxigênio, população indígena, quilombola, ribeirinha e de assentamentos |
| Janela temporal | Estático, revisto anualmente |
| Recálculo | Anual, ou a cada atualização de mancha |
| Dado ausente | Lacuna |

| Proporção vulnerável | Pontos |
| --- | ---: |
| < 10% | 0 |
| 10% a < 20% | 1 |
| 20% a < 35% | 2 |
| >= 35% | 3 |

### 3.5.4 C3 — Unidades de saúde ameaçadas (0–4)

| Aspecto | Definição |
| --- | --- |
| Fonte | CNES cruzado com a mancha de inundação **e com as vias de acesso** — unidade fora da mancha mas com acesso interrompido conta como ameaçada |
| Unidade | Categoria derivada da contagem e do tipo de estabelecimento |
| Janela temporal | Estático, revisto a cada atualização de mancha ou de carga do CNES |
| Recálculo | A cada atualização de mancha ou de CNES |
| Dado ausente | Lacuna quando não há mancha nem contagem |

| Situação | Pontos |
| --- | ---: |
| Nenhuma unidade ameaçada | 0 |
| Uma unidade sem internação | 1 |
| Duas a três unidades sem internação | 2 |
| Quatro ou mais unidades sem internação | 3 |
| Qualquer unidade com internação ou urgência | 3 |
| Hospital de referência regional, ou única unidade do município | 4 |

Regra de precedência: **criticidade acima de quantidade**. Perder o único hospital do
município é pior que perder quatro unidades básicas.

**Implementação atual (`16_idap_estadual.py`):** C3 usa o CNES **estadual**
(`cnes_estabelecimentos_mt.csv`), agregado por município afetado via Otto (proxy de
mancha). Ainda não cruza vias de acesso nem geometria de ZAS oficial.

### 3.5.5 C4 — Captações de água ameaçadas (0–3)

| Aspecto | Definição |
| --- | --- |
| Fonte | Sisagua/Vigiagua, cadastro da concessionária, SNISB (corpo hídrico barrado e trecho a jusante) |
| Unidade | Categoria |
| Janela temporal | Estático, revisto a cada atualização de mancha |
| Recálculo | A cada atualização de mancha ou de carga do Sisagua |
| Dado ausente | Lacuna |

| Situação | Pontos |
| --- | ---: |
| Nenhuma captação ameaçada | 0 |
| Captação de sistema isolado ou rural | 1 |
| Captação de sistema urbano de pequeno ou médio porte | 2 |
| Captação principal de sede municipal, ou única captação | 3 |

Dispara também a regra determinística R08 quando o cruzamento geoespacial confirmar
interseção.

### 3.5.6 C5 — Serviços essenciais não assistenciais ameaçados (0–2)

| Aspecto | Definição |
| --- | --- |
| Fonte | Cadastro estadual de infraestrutura crítica, Defesa Civil, concessionárias, INEP (escolas) |
| Unidade | Contagem de ativos críticos na mancha |
| Ativos considerados | Subestação de energia, ETA, ETE, escola, abrigo previsto no plano, torre de telecomunicação, ponte estruturante, creche, sede de prefeitura ou de Defesa Civil |
| Janela temporal | Estático |
| Recálculo | A cada atualização de mancha |
| Dado ausente | Lacuna |

| Ativos críticos na mancha | Pontos |
| --- | ---: |
| 0 | 0 |
| 1 a 2 | 1 |
| >= 3 | 2 |

### 3.5.7 C6 — Tempo de chegada da onda (0–4)

| Aspecto | Definição |
| --- | --- |
| Fonte | Estudo de ruptura hipotética (dam break) do empreendedor, integrante do PAE/PAEBM; estimativa própria simplificada quando ausente, sinalizada como estimativa |
| Unidade | Minutos até a primeira ocupação humana a jusante |
| Janela temporal | Estático; revisto a cada revisão do estudo |
| Recálculo | A cada revisão do estudo de ruptura |
| Dado ausente | Lacuna. É a lacuna mais consequente da dimensão C, porque sem ela não se sabe se há tempo para agir |

| Tempo de chegada | Pontos | Rótulo |
| --- | ---: | --- |
| < 30 min | 4 | evacuação assistida inviável — só autossalvamento |
| 30 a < 60 min | 3 | |
| 60 a < 120 min | 2 | |
| 120 a < 360 min | 1 | |
| >= 360 min | 0 | seis horas ou mais |

A fronteira de 30 minutos não é arbitrária: é o critério da Resolução ANM nº 95/2022 para
definir a Zona de Autossalvamento — o trecho a jusante em que não há tempo suficiente para
intervenção da autoridade competente em caso de acidente.

### 3.5.8 C7 — Possibilidade de isolamento rodoviário (0–2)

| Aspecto | Definição |
| --- | --- |
| Fonte | Malha viária (DNIT, Sinfra-MT, OpenStreetMap) cruzada com a mancha |
| Unidade | Categoria |
| Janela temporal | Estático |
| Recálculo | A cada atualização de mancha |
| Dado ausente | Lacuna |

| Situação | Pontos |
| --- | ---: |
| Rotas alternativas pavimentadas disponíveis | 0 |
| Rota única com desvio precário ou travessia comprometida | 1 |
| Acesso único sem alternativa — localidade ou município isolável | 2 |

### 3.5.9 C8 — Presença de contaminantes ou rejeitos (0–2)

| Aspecto | Definição |
| --- | --- |
| Fonte | SIGBM/ANM — `Minério principal presente no reservatório`, `Produtos químicos utilizados`, `A Barragem armazena rejeitos/residuos que contenham Cianeto`, classe do resíduo pela NBR 10004 |
| Unidade | Categoria |
| Janela temporal | Último cadastro publicado |
| Recálculo | A cada carga (diária) |
| Dado ausente | Lacuna. Para barragens de água não minerárias, o ETL deve preencher `Água sem rejeito` quando o uso principal for de acumulação de água, registrando a inferência |

| Situação | Pontos |
| --- | ---: |
| Água sem rejeito | 0 |
| Rejeito inerte (Classe II B) ou sedimento | 1 |
| Rejeito não inerte (Classe II A) ou perigoso (Classe I), cianeto, mercúrio, arsênio, metais pesados | 2 |

---

## 3.6 Dimensão D — Déficit de capacidade de resposta (15 pontos)

Esta dimensão pontua **o que falta**, não o que existe. Pontuação alta significa
despreparo.

### 3.6.1 Distribuição proposta dos 15 pontos e sua justificativa

| Código | Indicador | Pontos | Por que este peso |
| --- | --- | ---: | --- |
| D1 | Ausência de plano de emergência | 3 | Maior peso, empatado com D3: sem plano, nenhuma das outras capacidades se organiza. Quem faz o quê, quando e com qual gatilho só existe no plano |
| D2 | Ausência de simulado | 2 | Plano nunca testado tende a falhar no primeiro uso, mas ainda é infinitamente melhor que nenhum plano — daí 2 e não 3 |
| D3 | Baixa cobertura de sirenes / sistema de alerta | 3 | Maior peso: é o único mecanismo que funciona nos casos de C6 abaixo de 30 min. Sem alerta sonoro na ZAS, a população não sabe que precisa correr |
| D4 | Insuficiência de abrigos | 2 | Determina se a evacuação tem destino; sem abrigo, a evacuação gera desabrigados e um segundo problema sanitário |
| D5 | Poucas ambulâncias | 1 | Relevante, mas parcialmente substituível por apoio regional e pela regulação estadual |
| D6 | Baixa capacidade hospitalar | 2 | Peso intermediário: gargalo real, mas mitigável por transferência inter-regional em algumas horas |
| D7 | Ausência de rotas alternativas | 1 | Já parcialmente capturado por C7; aqui entra o aspecto de **planejamento** da rota, não o de geografia |
| D8 | Contatos institucionais desatualizados | 1 | Peso baixo no índice porque o problema é corrigível em horas, mas dispara a regra R09 quando se materializa em falta de confirmação |
| | **Total** | **15** | |

O princípio: **os dois pontos de maior peso (D1 e D3) são os que determinam se a população
é avisada e se alguém sabe o que fazer**. Os demais dizem respeito à qualidade da resposta,
não à sua existência.

Justificativa empírica para o peso de D1 no contexto de Mato Grosso: das 63 barragens de
classe A do estado, 15 não registram PAE e 12 não registram Plano de Segurança no SNISB. O
déficit de plano não é hipótese, é a situação observada no subconjunto de maior exigência
legal.

### 3.6.2 D1 — Ausência de plano de emergência (0–3)

| Aspecto | Definição |
| --- | --- |
| Fonte | SNISB (`POSSUI_PAE`), SIGBM (`Necessita de PAEBM`, `As cópias físicas do PAEBM foram entregues para as Prefeituras e Defesas Civis`), Defesa Civil estadual (plano de contingência municipal) |
| Unidade | Categoria |
| Janela temporal | Situação vigente |
| Recálculo | A cada carga (diária) |
| Dado ausente | Lacuna. Nota: 87,7% dos registros de MT têm `POSSUI_PAE` vazio no SNISB — o que aqui é lacuna, não ausência de plano. É preciso distinguir "não informado" de "não possui", e o SNISB não permite essa distinção de forma confiável para a maior parte do inventário |

| Situação | Pontos |
| --- | ---: |
| Plano vigente, testado e articulado com os municípios | 0 |
| Plano vigente sem articulação municipal formalizada | 1 |
| Plano em elaboração ou vencido | 2 |
| Plano inexistente, sendo exigível | 3 |

### 3.6.3 D2 — Ausência de simulado (0–2)

| Aspecto | Definição |
| --- | --- |
| Fonte | Registros da Defesa Civil estadual e municipal; relatórios do empreendedor |
| Unidade | Meses desde o último simulado |
| Janela temporal | Situação vigente |
| Recálculo | Mensal |
| Dado ausente | Lacuna |

| Meses desde o último simulado | Pontos |
| --- | ---: |
| < 12 | 0 |
| 12 a < 36 | 1 |
| >= 36, ou nunca realizado | 2 |

### 3.6.4 D3 — Baixa cobertura de sirenes (0–3)

| Aspecto | Definição |
| --- | --- |
| Fonte | Cadastro de sirenes do empreendedor e da Defesa Civil; registro dos testes periódicos |
| Unidade | Proporção da população da ZAS coberta por sistema de alerta sonoro testado |
| Janela temporal | Situação vigente |
| Recálculo | Mensal |
| Dado ausente | Lacuna |

| Cobertura da ZAS | Pontos |
| --- | ---: |
| >= 90% | 0 |
| 60% a < 90% | 1 |
| 30% a < 60% | 2 |
| < 30% | 3 |

### 3.6.5 D4 — Insuficiência de abrigos (0–2)

| Aspecto | Definição |
| --- | --- |
| Fonte | Cadastro de abrigos da Defesa Civil e da Assistência Social |
| Unidade | Razão vagas cadastradas / população a evacuar |
| Janela temporal | Situação vigente |
| Recálculo | Mensal em rotina; diário durante evento |
| Dado ausente | Lacuna |

| Razão vagas / demanda | Pontos |
| --- | ---: |
| >= 1,00 | 0 |
| 0,50 a < 1,00 | 1 |
| < 0,50 | 2 |

### 3.6.6 D5 — Poucas ambulâncias (0–1)

| Aspecto | Definição |
| --- | --- |
| Fonte | CNES (veículos), SAMU, regulação estadual |
| Unidade | Ambulâncias operacionais por 10 mil habitantes da área de resposta |
| Janela temporal | Situação vigente |
| Recálculo | Diário |
| Dado ausente | Lacuna |

| Ambulâncias por 10 mil habitantes | Pontos |
| --- | ---: |
| >= 1,00 | 0 |
| < 1,00 | 1 |

O limiar de 1 por 10 mil habitantes é **proposta a validar** com a coordenação estadual de
urgência e emergência.

### 3.6.7 D6 — Baixa capacidade hospitalar (0–2)

| Aspecto | Definição |
| --- | --- |
| Fonte | CNES (leitos cadastrados) e SISREG / central estadual (leitos efetivamente vagos) |
| Unidade | Razão leitos disponíveis / demanda estimada de internação |
| Demanda estimada | 2% da população exposta (**proposta a validar** — parâmetro de planejamento, a calibrar com literatura de desastres e com a experiência do estado) |
| Janela temporal | Situação vigente |
| Recálculo | Diário em rotina; horário durante evento |
| Dado ausente | Lacuna |

| Razão leitos / demanda | Pontos |
| --- | ---: |
| >= 1,00 | 0 |
| 0,50 a < 1,00 | 1 |
| < 0,50 | 2 |

**Implementação atual:** quando IndicaSUS/SISREG não têm carga, D6 usa proxy tipológico
`hospitais_CNES × 40 leitos` / (2% da pop. dos municípios afetados), rotulado
`cnes_tipologico_proxy` — a calibrar com a SES.

### 3.6.8 D7 — Ausência de rotas alternativas (0–1)

| Aspecto | Definição |
| --- | --- |
| Fonte | Plano de evacuação municipal; malha viária cruzada com a mancha |
| Unidade | Booleano |
| Janela temporal | Situação vigente |
| Recálculo | A cada atualização de mancha ou de plano |
| Dado ausente | Lacuna |

| Situação | Pontos |
| --- | ---: |
| Existe rota alternativa mapeada e transitável | 0 |
| Não existe rota alternativa | 1 |

### 3.6.9 D8 — Contatos institucionais desatualizados (0–1)

| Aspecto | Definição |
| --- | --- |
| Fonte | Cadastro de contatos institucionais da própria plataforma |
| Unidade | Booleano |
| Janela temporal | Últimos 90 dias |
| Recálculo | Diário |
| Dado ausente | Lacuna |

| Situação | Pontos |
| --- | ---: |
| Contatos validados nos últimos 90 dias | 0 |
| Contatos sem validação há mais de 90 dias | 1 |

---

## 3.7 Classificação em faixas

| IDAP | Faixa | Significado | Postura esperada do setor saúde |
| ---: | --- | --- | --- |
| 0 a 19 | **Verde** | normalidade | Rotina de monitoramento e atualização cadastral |
| 20 a 39 | **Amarelo** | atenção | Acompanhamento reforçado; verificação de plano e contatos |
| 40 a 59 | **Laranja** | mobilização | Acionamento da Vigilância e da Defesa Civil municipais; conferência de leitos, abrigos, estoques e rotas |
| 60 a 79 | **Vermelho** | emergência potencial | Sala de Situação em prontidão; pré-posicionamento de recursos; comunicação de risco articulada |
| 80 a 100 | **Roxo** | resposta crítica | COE ativado; VIGIPÓS-BARRAGENS acionado; resposta em execução |

As fronteiras são exatas e inclusivas: 19 é Verde e 20 é Amarelo; 39 é Amarelo e 40 é
Laranja; 59 é Laranja e 60 é Vermelho; 79 é Vermelho e 80 é Roxo. Como o índice é soma de
pontos inteiros, não há ambiguidade de arredondamento. A implementação de referência testa
cada uma dessas dez fronteiras (`scripts/idap/testes.py`, classe `TestFronteirasDasFaixas`).

---

## 3.8 Tratamento de dado ausente e completude do cálculo

O problema é real e grande: para a maior parte das 1.248 barragens de MT, a maioria dos
indicadores de B, C e D está indisponível hoje. Se o índice tratar ausência como zero e
apresentar o resultado como um número limpo, produzirá **falso verde** — a situação mais
perigosa possível em um sistema de alerta.

### 3.8.1 As três situações, e por que a distinção importa

| Situação | Exemplo | Pontuação | Efeito na completude |
| --- | --- | --- | --- |
| **Valor medido** | `categoria_risco = "Alto"` | Conforme a tabela: 5 | Conta como apurado |
| **Categoria declarada de desconhecimento** | `categoria_risco = "Não Classificado"`; `Status DCE = "-"` | Pontuação de precaução definida na tabela: 2 e 3 respectivamente | Conta como apurado — é um fato cadastral |
| **Lacuna** | `categoria_risco = null`; nenhuma estação com chuva na janela | 0 ponto | Reduz a completude |

### 3.8.2 As três métricas que acompanham o índice

| Métrica | Fórmula | Para que serve |
| --- | --- | --- |
| **IDAP** | Soma bruta dos pontos apurados | É o valor oficial, auditável, que classifica a faixa. Nunca extrapola |
| **Completude** | Soma dos tetos dos indicadores apurados ÷ 100 | Diz qual fração do índice foi efetivamente avaliada |
| **IDAP projetado** | IDAP ÷ (soma dos tetos apurados) × 100 | Contexto: onde o índice cairia se os ausentes se comportassem como a média dos apurados. **Não classifica faixa**, porque classificar por valor projetado equivale a inventar dado |

Faixas de confiabilidade declarada:

| Completude | Confiabilidade | Consequência |
| --- | --- | --- |
| >= 80% | suficiente | Nenhuma |
| 40% a < 80% | parcial | O alerta estampa a advertência de subestimação |
| < 40% | insuficiente | O alerta estampa a advertência **e** a regra R06 dispara alerta técnico |

### 3.8.3 A regra que impede o falso verde

A regra determinística **R06** dispara sempre que a completude da dimensão B (condição da
barragem) fica abaixo de 40%. Ela não eleva a faixa — elevar por ignorância produziria
alarme constante e destruiria a credibilidade do sistema. Ela emite um **alerta técnico**
ao empreendedor e ao órgão fiscalizador, e registra no alerta que o índice está
subestimado.

Consequência prática hoje: com o inventário atual, R06 disparará para a grande maioria das
1.248 barragens de MT. Isso não é defeito do índice — é o retrato correto do estado do
cadastro, e é a razão pela qual a Fase 1 do roteiro de implantação
(`docs/08-roadmap.md`) começa por preencher a dimensão B em um recorte piloto.

---

## 3.9 Regras determinísticas de sobreposição

Estas regras agem **depois** do índice e **não dependem dele**. Existem porque há fatos que
obrigam a resposta independentemente da pontuação: uma emergência de nível 3 declarada pelo
empreendedor exige alerta vermelho mesmo com bacia seca e pouca população a jusante. Sem
esta camada, um índice ponderado diluiria justamente o sinal mais grave.

| Código | Regra (condição) | Nível mínimo forçado | Ação automática |
| --- | --- | --- | --- |
| **R01** | Emergência oficial de nível 2 ou 3 declarada | **Vermelho** | Notificar imediatamente Defesa Civil estadual e municipal, CIEVS, SAMU e gestores da ZAS; colocar a Sala de Situação em prontidão |
| **R02** | Rompimento confirmado | **Roxo** | Ativar imediatamente a resposta: COE em funcionamento, acionamento do VIGIPÓS-BARRAGENS, abertura de evento e SITREP inicial em até 1 h |
| **R03** | Perda súbita de nível do reservatório **associada a** anomalia estrutural ativa (nota >= 4) | **Roxo** | Emitir alerta crítico para validação em campo em até 30 min pelo empreendedor e pelo órgão fiscalizador — suspeita de brecha em formação |
| **R04** | Chuva extrema (>= 100 mm/24 h ou >= 200 mm/72 h) **e** anomalia estrutural ativa | **Vermelho** | Alerta vermelho aos municípios da ZAS; exigir inspeção extraordinária e informe de condição em até 6 h |
| **R05** | Evacuação determinada pela autoridade competente | **Roxo** | Ativar a Sala de Situação, acionar abrigos e transporte sanitário, iniciar registro de desalojados e desabrigados |
| **R06** | Falha simultânea de 2 ou mais sensores críticos, **ou** completude da dimensão B abaixo de 40% | *não altera a faixa* | Emitir alerta técnico ao empreendedor e ao órgão fiscalizador; registrar que o IDAP está subestimado e não pode ser lido como normalidade |
| **R07** | Mancha de inundação atingindo unidade de saúde estratégica | **Laranja** | Alerta assistencial: acionar regulação estadual para remanejamento de leitos e pacientes; avaliar transferência de rede de frio e de pacientes críticos |
| **R08** | Mancha de inundação atingindo captação de água para consumo humano | **Laranja** | Alerta Vigiagua: suspender captação, iniciar coleta de amostras, acionar abastecimento alternativo e comunicação de risco |
| **R09** | Município da ZAS sem confirmação de recebimento no prazo do nível | *não altera a faixa* | Escalonar o alerta: acionar contato substituto, gestor regional de saúde e Defesa Civil estadual; registrar a falha de comunicação no evento |

Propriedades garantidas pela implementação e cobertas por teste:

1. Uma regra **nunca rebaixa** o nível: ela só eleva, ou mantém.
2. Quando mais de uma regra dispara, prevalece o nível mais alto entre elas e o do índice.
3. Todas as ações automáticas das regras disparadas são executadas, mesmo as das regras que
   não elevaram o nível.
4. Os limiares numéricos das regras (100 mm/24 h, 200 mm/72 h, nota 4 de anomalia, 2
   sensores, 40% de completude) são **propostas a validar** e vivem no mesmo módulo
   versionado dos pesos.

---

## 3.10 Frequência de recálculo consolidada

| Cadência | Indicadores | Por quê |
| --- | --- | --- |
| 15 min a 1 h | A6, B5 (quando houver telemetria) | Acompanham leitura de sensor |
| 30 min a 1 h | A1, A2, A4, A7 | Acompanham a publicação de chuva observada |
| Horária | B6 | Monitora o próprio fluxo de telemetria |
| 2 a 4 vezes ao dia | A3 | Acompanha rodada de modelo |
| Diária | A5, B1, B2, B3, B4, C8, D5, D6, D8 | Acompanham a carga do inventário e a operação |
| Mensal | D2, D3, D4 | Mudam por ato de gestão |
| A cada atualização de mancha | C1 a C7, D7 | Estáticos por natureza |
| **Por evento, fora da rotina** | B2 | Comunicação oficial de mudança de nível de emergência recalcula o índice na hora |

A cadência mínima do índice completo proposta é **horária** em situação normal e a cada
**15 minutos** para barragens em faixa Laranja ou superior (**proposta a validar** conforme
capacidade de infraestrutura).

---

## 3.11 Validação, versionamento dos pesos e auditoria

### 3.11.1 Por que a calibração precisa de painel de especialistas

Os pesos desta versão são **metodológicos**: expressam uma hierarquia de importância
defensável, não uma calibração empírica. Nenhum deles foi ajustado contra histórico de
eventos, porque não existe série de eventos de barragem em MT suficiente para isso.

Composição mínima proposta para o painel de validação:

| Especialidade | O que deve validar |
| --- | --- |
| Engenharia de barragens | B1 a B6, limiar de anomalia ativa, definição de perda súbita de nível |
| Hidrologia | A2, A5, A6, definição de bacia contribuinte e de cota de alerta |
| Meteorologia | A1, A3, A4, A7, escolha de produto de chuva e limiares |
| Epidemiologia | Uso do índice como gatilho de vigilância; ligação com `docs/05-vigipos-barragens.md` |
| Saúde ambiental (Vigidesastres e Vigiagua) | C4, C8, painel laboratorial associado |
| Assistência (APS, urgência, hospitalar) | C3, D5, D6, parâmetro de demanda estimada de internação |
| Defesa Civil | C6, C7, D1 a D4, D7, prazos de confirmação de alerta |
| Geoprocessamento | Recorte de mancha, setor censitário, malha viária, cruzamento com CNES |

### 3.11.2 Como versionar os pesos

Toda a calibração vive em um único módulo, `scripts/idap/pesos.py`, com três metadados
obrigatórios:

| Metadado | Valor atual | Regra |
| --- | --- | --- |
| `VERSAO_PESOS` | `0.1.0-metodologica` | Versionamento semântico: **maior** para mudança de estrutura (indicador criado ou removido, teto alterado), **menor** para mudança de peso dentro da estrutura, **correção** para ajuste de limiar sem mudança de peso |
| `DATA_VERSAO_PESOS` | `2026-07-29` | Data de publicação da versão |
| `STATUS_VERSAO_PESOS` | proposta metodológica | `proposta metodológica`, `em validação`, `validada`, `depreciada` |

Regras de governança da calibração (**proposta a validar**):

1. Nenhuma alteração de peso entra em produção sem nova `VERSAO_PESOS` publicada.
2. O módulo executa uma função de autovalidação na importação, que falha se a soma dos
   tetos dos indicadores divergir de 30/30/25/15 ou se as faixas de alerta não forem
   contíguas. Calibração inconsistente não chega a rodar.
3. Toda versão publicada é acompanhada de um **recálculo retroativo** sobre o inventário
   completo, com o quadro comparativo de quantas barragens mudam de faixa. Uma
   recalibração que move 800 das 1.248 barragens de faixa precisa de justificativa
   explícita.
4. Uma versão nunca é editada depois de publicada. Correção gera nova versão.

### 3.11.3 O que registrar em cada recálculo, para auditoria

Cada execução do índice para cada barragem grava um registro imutável:

| Campo | Conteúdo | Por que é necessário |
| --- | --- | --- |
| `id_barragem`, `instante` | Chave do cálculo | Identifica o que foi calculado e quando |
| `versao_pesos` | Versão da calibração usada | Sem isso, não se reproduz o resultado |
| `estado_de_entrada` | Todos os valores de entrada, indicador por indicador, com a fonte e a hora de cada um | É o que permite reproduzir o cálculo anos depois |
| `pontos_por_indicador` | Pontuação apurada de cada indicador, com o rótulo da faixa | Justifica cada ponto do índice |
| `lacunas` | Códigos dos indicadores em lacuna | Explica a completude |
| `idap`, `completude`, `idap_projetado`, `confiabilidade` | Resultado | |
| `nivel_indice`, `nivel_final`, `regras_disparadas` | Classificação antes e depois das regras | Mostra se a elevação foi por pontuação ou por regra |
| `alerta_emitido` | Identificador do alerta gerado, se houver | Liga o cálculo à comunicação |
| `responsavel_pela_supervisao` | Quem validou, para alertas críticos | Alerta crítico não sai sem supervisão humana |

O cálculo é uma **função pura**: mesmo estado de entrada e mesma versão de pesos produzem
sempre o mesmo resultado, inclusive as justificativas por indicador. É essa propriedade que
torna a auditoria possível, e ela é verificada por teste
(`scripts/idap/testes.py`, classe `TestReprodutibilidade`).

---

## 3.12 Implementação de referência

| Arquivo | Papel |
| --- | --- |
| `scripts/idap/modelo.py` | Dataclasses do estado de entrada, com campo opcional para representar lacuna |
| `scripts/idap/pesos.py` | Pesos, faixas e limiares versionados, com autovalidação |
| `scripts/idap/calculo.py` | Funções puras de pontuação, soma, classificação e justificativa |
| `scripts/idap/regras.py` | Regras R01 a R09, aplicadas depois do índice |
| `scripts/idap/relatorio.py` | Geração do texto do alerta no formato de `docs/04-alertas.md` |
| `scripts/idap/exemplo.py` | Quatro barragens fictícias em situações diferentes — `python scripts/idap/exemplo.py` |
| `scripts/idap/testes.py` | 45 testes de `unittest` — `python -m unittest scripts.idap.testes` |

Dependências: apenas a biblioteca padrão do Python 3.12.

## 3.13 Exemplo trabalhado — o caso que justifica as regras

Cenário 3 do exemplo executável: Barragem de Rejeitos São Bento II, em Poconé.

| Dimensão | Pontos | Situação |
| --- | ---: | --- |
| A — Pressão hidroclimática | 5/30 | Chuva moderada, sem persistência, rio em nível normal |
| B — Condição da barragem | 17/30 | CRI média (3), **emergência nível 2 declarada (9)**, estabilidade vencida (3), anomalia com correção em andamento (2) |
| C — Impacto sanitário potencial | 8/25 | 150 pessoas na ZAS, uma unidade básica ameaçada, onda em 90 min, rejeito perigoso |
| D — Déficit de capacidade | 0/15 | Plano vigente e testado, simulado recente, sirenes cobrindo 92%, leitos e ambulâncias suficientes |
| **IDAP** | **30/100** | Faixa do índice: **Amarelo** (atenção) |

O índice sozinho diria "atenção". Mas a regra **R01** dispara, porque há emergência oficial
de nível 2 declarada, e o nível final vai para **Vermelho** (emergência potencial), com a
ação automática de notificação imediata e prontidão da Sala de Situação.

É exatamente o comportamento desejado: uma barragem bem preparada, sob tempo bom, com
população pequena a jusante, **ainda assim** exige resposta de emergência quando o
responsável técnico declara nível 2. Nenhuma ponderação deveria ser capaz de diluir isso, e
nesta especificação nenhuma é.
