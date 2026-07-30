# 6. Arquitetura de referência

> Escolhas tecnológicas apresentadas aqui são recomendações fundamentadas, não decisões
> tomadas. Onde há alternativa razoável, ela está registrada. Itens marcados
> **a validar** dependem de decisão de infraestrutura da SES-MT.

## 6.1 Recomendação estratégica central

**Não tentar construir tudo dentro do Power BI.**

Esta é a recomendação de arquitetura mais importante deste documento, e ela precisa vir
antes de qualquer diagrama, porque é o erro mais comum e mais caro em projetos deste tipo.

O Power BI é excelente no que faz: distribuir indicadores para gestão, com governança de
acesso, em ferramenta que o gestor já conhece. Ele é ruim, ou incapaz, no seguinte:

| Necessidade da plataforma | Por que o Power BI não resolve |
| --- | --- |
| Cruzar mancha de inundação com setor censitário e com CNES | Não faz operação geoespacial de verdade (interseção, buffer, área ponderada). Os visuais de mapa apenas plotam pontos e polígonos prontos |
| Recalcular o IDAP a cada 30 minutos com regras determinísticas | Não é motor de regras nem agendador de processamento; DAX não é o lugar de uma máquina de estados |
| Enviar alerta por SMS, voz e WhatsApp, e registrar confirmação | Não é serviço de notificação nem armazena estado transacional |
| Armazenar séries temporais de chuva, nível e vazão a cada 15 min para 1.248 estruturas | O modelo tabular não é banco de séries temporais; o volume degrada a atualização |
| Detecção estatística de excesso (CUSUM, EWMA, binomial negativa) | Não é ambiente estatístico |
| Guardar registro imutável de cálculo para auditoria | Não é banco de dados transacional |
| Escrever dado (ficha rápida, confirmação de alerta) | É ferramenta de leitura, não de escrita |

Tentar forçar essas funções para dentro do Power BI produz um modelo lento, frágil,
impossível de auditar e que ninguém além do autor consegue manter. O caminho é o inverso: o
processamento acontece fora, e o Power BI consome o resultado já calculado.

### 6.1.1 Divisão de responsabilidades recomendada

| Camada | Tecnologia recomendada | Responsabilidade | Alternativa |
| --- | --- | --- | --- |
| Gestão, indicadores e relatórios executivos | **Power BI** | Painéis para secretário, superintendências, gestores municipais e regiões de saúde; relatórios periódicos; distribuição com governança de acesso | Metabase, Superset |
| Mapas, manchas e análise territorial | **PostGIS + WebGIS** (GeoServer + Leaflet/MapLibre, ou QGIS Server) | Toda operação geoespacial; mapa operacional; recorte de exposição | Esri ArcGIS Enterprise, se já houver licença |
| ETL, modelos, IA e geração de alertas | **Python** | Coletores das fontes, cálculo do IDAP, regras determinísticas, detecção estatística, geração de texto de alerta e de SITREP | — |
| Séries temporais de chuva, nível, vazão e sensores | **Banco de séries temporais** (TimescaleDB como extensão do próprio PostgreSQL, ou InfluxDB) | Ingestão de alta frequência, agregação por janela móvel, retenção por política | TimescaleDB é preferível por reaproveitar o PostgreSQL e permitir junção direta com as tabelas relacionais |
| Envio e confirmação de alertas | **Serviço específico** | Despacho multicanal, máquina de estados de entrega, escalonamento, registro de confirmação | Serviço próprio em Python + gateways de SMS/voz, ou plataforma de notificação contratada |
| Banco central | **PostgreSQL + PostGIS** | Fonte da verdade relacional e espacial | — |

## 6.2 Camadas

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. FONTES DE DADOS  (docs/02-fontes-de-dados.md)                        │
│  SNISB · SIGBM · IBGE · SEMA-MT · INMET · Cemaden · ANA · GPM-IMERG     │
│  Sentinel-1/2 · Landsat · CBERS · Copernicus EMS · GloFAS               │
│  CNES · SINAN · SIM · SIH · SIA · e-SUS APS · SISREG · SAMU · GAL       │
│  Sisagua · Renaveh · Defesa Civil · concessionárias · empreendedores    │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. CAMADA DE INGESTÃO                                                   │
│  APIs oficiais (preferência absoluta)                                   │
│  ETL agendado em Python, com controle de versão de extração             │
│  Robôs autorizados, apenas onde não há API e há autorização formal      │
│  Recepção de arquivo (CSV, GeoJSON, shapefile) de órgãos parceiros      │
│  Formulário de ficha rápida (entrada de dado pela plataforma)           │
│  → registro de proveniência: fonte, hora de coleta, hora do dado, hash  │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. BANCO CENTRAL                                                        │
│  PostgreSQL 16 + PostGIS 3   → relacional e espacial                    │
│  TimescaleDB                 → séries temporais de chuva/nível/vazão    │
│  Camada bruta (imutável) → camada tratada → camada analítica            │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. MOTORES ANALÍTICOS                                                   │
│  Motor de regras          → IDAP + regras R01..R09 (scripts/idap/)      │
│  Motor geoespacial        → mancha × setor × CNES × via × captação      │
│  Modelos epidemiológicos  → linha de base, canal endêmico, O/E          │
│  Detecção de anomalias    → CUSUM, EWMA, Poisson, binomial negativa     │
│  Simulação de impacto     → cenários de população e demanda             │
│  Assistente de IA         → texto, síntese, priorização (§6.5)          │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. SAÍDAS                                                               │
│  Power BI executivo · WebGIS operacional · Sala de Situação             │
│  Alertas aos gestores (multicanal, com confirmação)                     │
│  SITREP automático · relatórios pós-desastre · API interna              │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2.1 Camada de ingestão — regras

| Regra | Motivo |
| --- | --- |
| API oficial tem precedência sobre qualquer outro método | Interface publicada é contrato; raspagem não é |
| Robô só onde não há API **e** há autorização formal do órgão | Evita dependência frágil e problema jurídico |
| Toda extração grava a resposta bruta antes de qualquer transformação | Permite reprocessar sem nova coleta e auditar a transformação |
| Toda extração registra proveniência: fonte, URL, hora da coleta, hora de referência do dado, contagem de registros e hash do conteúdo | Sem isso não se sabe qual dado gerou qual alerta |
| Falha de coleta é dado: fica registrada e reflete na completude do IDAP | Silêncio de coletor não pode virar "sem risco" |
| Coletores frágeis (como o do modelo Power BI do SNISB) são monitorados e têm alerta de quebra próprio | `docs/02-fontes-de-dados.md`, §2.2.2 |

## 6.3 Esboço do modelo de dados relacional

Chaves primárias em **negrito**; chaves estrangeiras marcadas com `→`.

### 6.3.1 Cadastro e território

| Tabela | Campos principais |
| --- | --- |
| `barragem` | **id_barragem**, id_snisb, nome, nome_secundario, → id_municipio, → id_orgao_fiscalizador, → id_empreendedor, uso_principal, tipo_material, altura_m, capacidade_hm3, fase_de_vida, geom (Point, 4326), alertavel (booleano) |
| `orgao_fiscalizador` | **id_orgao**, sigla, nome, esfera, contato_ponto_focal |
| `empreendedor` | **id_empreendedor**, nome, cnpj_cpf, tipo, contato_responsavel_tecnico |
| `classificacao` | **id_classificacao**, → id_barragem, data_referencia, categoria_risco, dano_potencial, classe_cnrh, regulada_pnsb, possui_pae, possui_plano_seguranca, possui_revisao_periodica, nivel_emergencia, status_dce, fonte, versao_carga |
| `municipio` | **id_municipio** (código IBGE), nome, → id_regiao_saude, mesorregiao, regiao_intermediaria, populacao, geom (MultiPolygon, 4326) |
| `regiao_saude` | **id_regiao_saude**, nome, municipio_sede, populacao |
| `mancha_inundacao` | **id_mancha**, → id_barragem, tipo (ZAS, ZSS, cenário), origem (estudo do empreendedor, estimativa própria), data_do_estudo, tempo_chegada_min, geom (MultiPolygon, 4326) |
| `setor_censitario` | **id_setor**, → id_municipio, populacao, populacao_vulneravel, geom |
| `exposto` | **id_exposto**, → id_mancha, tipo (população, unidade de saúde, captação, escola, via, subestação, abrigo), → id_referencia_externa (CNES, Sisagua, INEP), quantidade, criticidade, geom |
| `contato_institucional` | **id_contato**, → id_municipio, instituicao, papel, nome, cargo, telefone, celular, email, substituto, data_ultima_validacao |
| `vinculo_barragem_ator` | **id_vinculo**, → id_barragem, → id_contato, tipo_de_vinculo (ZAS, ZSS, regional, fiscalizador, empreendedor) |

Nota de modelagem: `classificacao` é separada de `barragem` e tem `data_referencia` porque a
classificação **muda no tempo** e o histórico é essencial — detectar que uma barragem passou
de CRI média para alta é um evento de gestão, e hoje esse histórico é justamente o que não
existe.

### 6.3.2 Séries temporais

| Tabela (hipertabela TimescaleDB) | Campos principais |
| --- | --- |
| `serie_chuva` | **(id_barragem, instante, fonte)**, chuva_mm, janela (30min, 1h, 24h, 72h), origem_espacial (estação, pixel, média da bacia), qualidade |
| `serie_nivel_vazao` | **(id_estacao, instante)**, → id_barragem_referencia, nivel_cm, vazao_m3s, cota_alerta_cm, cota_inundacao_cm, fonte, qualidade |
| `serie_sensor_barragem` | **(id_barragem, id_sensor, instante)**, tipo_sensor (piezômetro, inclinômetro, medidor de vazão, régua de nível), valor, unidade, situacao_transmissao |

Política de retenção proposta (**a validar**): dado bruto de 30 min por 2 anos; agregação
horária por 10 anos; agregação diária permanente.

### 6.3.3 Cálculo, alerta e evento

| Tabela | Campos principais |
| --- | --- |
| `calculo_idap` | **id_calculo**, → id_barragem, instante, versao_pesos, idap, completude, idap_projetado, confiabilidade, nivel_indice, nivel_final, estado_de_entrada (JSONB), pontos_por_indicador (JSONB), lacunas (array), regras_disparadas (array) |
| `alerta` | **id_alerta**, → id_calculo, → id_barragem, nivel, instante_emissao, corpo_do_alerta (texto), estado_atual, responsavel_supervisao, prazo_confirmacao_min |
| `confirmacao_entrega` | **id_confirmacao**, → id_alerta, → id_contato, canal, hora_envio, hora_entrega_tecnica, hora_confirmacao, quem_confirmou, estado, numero_escalonamentos |
| `evento` | **id_evento**, → id_barragem, tipo (rompimento, inundação, vazamento, evacuação, interrupção), instante_inicio, instante_encerramento, gatilho, municipios_afetados (array), status |
| `ficha_rapida` | **id_ficha**, → id_evento, → id_municipio, localidade, geom (Point), instante_referencia, instante_preenchimento, informante, versao, blocos (JSONB com Evento, Saúde, Serviços, Água) |
| `amostra_agua` | **id_amostra**, → id_evento, → id_municipio, → id_sistema_sisagua, ponto_de_coleta, geom, instante_coleta, instante_resultado, coliformes_totais, ecoli, turbidez_ut, cloro_residual_mgl, contaminantes_quimicos (JSONB), dentro_do_padrao |
| `sinal_epidemiologico` | **id_sinal**, → id_evento, agravo_ou_sindrome, janela, observado, esperado, limite_superior, razao_oe, excesso, metodo, parametros (JSONB), classificacao, instante_deteccao |
| `indicador_assistencial` | **id_medida**, → id_evento, → id_estabelecimento_cnes, instante, ipapd, termos (JSONB com O, A, P, E, C, S) |

Nota sobre `estado_de_entrada` e `pontos_por_indicador` em JSONB: guardar a entrada completa
de cada cálculo parece redundante, mas é o que permite reproduzir o resultado anos depois,
mesmo que a fonte original tenha mudado. É o requisito de auditoria da
§3.11.3 de `docs/03-idap.md`.

## 6.4 Motores analíticos

| Motor | O que faz | Onde vive | Cadência |
| --- | --- | --- | --- |
| **Motor de regras** | Calcula o IDAP, aplica R01–R09, decide nível final e ações automáticas | `scripts/idap/` (implementação de referência já executável) | Horária em rotina; 15 min para barragens em Laranja ou acima |
| **Motor geoespacial** | Interseção de mancha com setor censitário, CNES, captações, malha viária e ativos críticos; cálculo de população exposta por área ponderada | PostGIS, com funções encapsuladas em views materializadas | A cada atualização de mancha ou de cadastro |
| **Modelos epidemiológicos** | Linha de base, canal endêmico, esperado por semana epidemiológica, razão O/E | Python (biblioteca padrão + estatística), lendo do PostgreSQL | Diária em rotina; a cada carga durante evento |
| **Detecção de anomalias** | CUSUM, EWMA, Poisson, binomial negativa, bayesiano, controle sintético | Python | Diária em rotina; a cada ficha durante evento |
| **Simulação de impacto** | Cenários de população atingida, demanda de leitos, demanda de água, rotas alternativas | Python + PostGIS | Sob demanda e em pré-impacto |
| **Assistente de IA** | Texto, síntese, priorização, explicação de sinal | Serviço de modelo de linguagem, com contexto restrito aos dados agregados | Sob demanda |

## 6.5 Uso e limites da inteligência artificial

### 6.5.1 Usos apropriados

| Uso | Descrição | Por que é apropriado |
| --- | --- | --- |
| Análise de cenário | Descrever, em texto, o que decorre de um conjunto de indicadores | Síntese textual sobre dado já calculado |
| Priorização de municípios | Ordenar municípios por combinação de exposição, déficit e sinal, com justificativa | Apoio à decisão, com o critério explicitado e revisável |
| Detecção de anomalias | **Explicar** um sinal produzido pelo algoritmo estatístico, cruzando com contexto territorial e temporal | O número vem do algoritmo; a IA interpreta |
| Produção de SITREP | Redigir o relatório de situação a partir dos indicadores do período | Redação estruturada, economia de horas em plena crise |
| Produção de boletim, informe e resumo executivo | Adaptar o mesmo conteúdo a públicos diferentes | |
| Nota de comunicação de risco | Redigir linguagem acessível para a população, a partir do conteúdo técnico | Sujeita a revisão humana obrigatória antes da publicação |
| Lista de pendências | Extrair, das fichas e dos registros, o que ficou em aberto e para quem | |
| Relatório diário do COE | Consolidar as fontes do dia em documento único | |
| Assistente operacional | Responder perguntas sobre os dados da plataforma em linguagem natural | Reduz a barreira de uso do painel |

### 6.5.2 Limites obrigatórios

| A IA NÃO deve | Por quê |
| --- | --- |
| Determinar evacuação | Ato de autoridade com consequência legal e material imediata |
| Declarar estabilidade de barragem | Requer laudo de responsável técnico habilitado |
| Substituir laudo de engenharia | O mesmo |
| Confirmar causalidade epidemiológica automaticamente | Sinal estatístico não é nexo causal; a confirmação exige investigação de campo |
| Divulgar dados individuais | Dado de saúde é sensível pela LGPD; a IA opera sobre agregados |
| Enviar alerta crítico sem regra validada e supervisão humana | Alerta em Vermelho ou Roxo passa pelo estado `AGUARDANDO_SUPERVISAO` (`docs/04-alertas.md`, §4.6.1) |
| Produzir o número que dispara o alerta | Todo gatilho vem de regra determinística ou de algoritmo estatístico reproduzível |

Controles técnicos que implementam esses limites (**propostas a validar**):

1. O serviço de IA recebe apenas dados **agregados**; não tem acesso às tabelas com
   identificação individual.
2. Todo texto gerado é marcado como gerado por IA, com data, modelo e versão do prompt.
3. Todo texto destinado a público externo passa por revisão humana registrada.
4. Nenhum caminho de código permite que uma saída de modelo de linguagem altere o nível de
   um alerta ou dispare um envio.

## 6.6 Proteção de dados (LGPD)

A plataforma trata dado pessoal sensível — dado de saúde, na definição do art. 5º, II da Lei
nº 13.709/2018. As medidas abaixo são requisitos, não recomendações.

### 6.6.1 Base legal e finalidade

| Aspecto | Definição |
| --- | --- |
| Base legal | Tutela da saúde, em procedimento realizado por autoridade sanitária (art. 11, II, "f"), e execução de política pública (art. 7º, III) — **a validar** com a assessoria jurídica e o encarregado de dados da SES-MT |
| Finalidade declarada | Vigilância em saúde de população exposta a risco de desastre com barragens, em suas fases pré, durante e pós-evento |
| Vedação expressa | Uso do dado para finalidade diversa da declarada, inclusive comercial ou de comunicação de terceiros |

### 6.6.2 Medidas por camada

| Camada | Medida |
| --- | --- |
| Coleta | Coletar o **mínimo necessário**. A ficha rápida coleta contagens agregadas por localidade, não identificação individual, exceto quando o cuidado exigir (paciente em diálise, dependente de oxigênio) — e nesses casos o dado fica em tabela segregada |
| Armazenamento | Segregação física entre a base de indicadores agregados e a base com identificação; criptografia em repouso; PostgreSQL com Row Level Security por perfil |
| Trânsito | TLS obrigatório em toda comunicação; nenhum dado identificável em SMS ou WhatsApp |
| Acesso | Perfil mínimo necessário, com registro de todo acesso a dado identificável (quem, quando, qual registro) |
| Retenção | Prazo definido por tipo de dado, com descarte ou anonimização ao término (**a validar** com o encarregado) |
| Compartilhamento | Somente agregado, exceto quando houver base legal e instrumento formal; nunca por canal não institucional |
| Anonimização | Todo painel, relatório e boletim publicado usa dado agregado, com supressão de célula pequena (proposta: suprimir contagens de 1 a 4 casos por localidade, para evitar reidentificação) |
| IA | O serviço de modelo de linguagem recebe apenas agregados (§6.5.2) |
| Incidente | Plano de resposta a incidente de segurança, com comunicação à ANPD e aos titulares nos prazos legais |

### 6.6.3 Tensão a resolver explicitamente

Existe um conflito real entre a proteção do dado e a operação do cuidado: identificar
nominalmente o paciente em diálise que mora na ZAS é o que permite buscá-lo antes da onda, e
é exatamente o dado mais sensível da plataforma.

Encaminhamento proposto (**a validar** com o encarregado de dados e com a assessoria
jurídica): manter a lista nominal em módulo segregado, acessível apenas ao responsável pelo
cuidado no município e à regulação estadual, com registro de todo acesso, e liberá-la para
uso operacional apenas quando a barragem estiver em faixa Laranja ou superior — nunca em
rotina, e nunca no painel de gestão.

## 6.7 Ambiente e operação

| Aspecto | Recomendação | Observação |
| --- | --- | --- |
| Hospedagem | Infraestrutura estadual, ou nuvem com dados em território nacional | **a validar** com a área de TI da SES-MT |
| Orquestração de ETL | Agendador com registro de execução e alerta de falha | Airflow, Prefect ou cron com logging estruturado, conforme a capacidade da equipe |
| Versionamento | Git para código, migrações versionadas para o banco, versão explícita para os pesos do IDAP | Já praticado neste repositório |
| Observabilidade | Métrica de frescor por fonte (idade do dado mais recente), taxa de falha de coletor, latência do cálculo | O painel deve mostrar quando uma fonte está atrasada |
| Ambiente de homologação | Réplica com dado sintético para testar recalibração antes de publicar | Requisito para a governança de pesos da §3.11.2 |
| Plano de continuidade | O que fazer quando a plataforma cair durante um evento | Procedimento manual documentado, com lista de contatos impressa |

O último item merece ênfase: um sistema de alerta que só funciona quando está no ar não é
confiável. O procedimento manual de contingência — quem liga para quem, com qual lista — é
parte do produto, não um anexo.
