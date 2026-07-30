---
origem: "c:\Users\Menandesneto\OneDrive\Vigidesastres Cuaibá\Vigidesastres 2026\Produto 04\VIGIBARRAGENS_MT_Especificacao_Funcional_Tecnica_v1_0.docx"
arquivo: VIGIBARRAGENS_MT_Especificacao_Funcional_Tecnica_v1_0.docx
tamanho_kb: 80.9
modificado_em_disco: 2026-07-29 16:19
titulo_documento: VIGIBARRAGENS–MT Saúde – Especificação Funcional e Técnica
autor: Documento técnico elaborado para SES-MT / Vigidesastres
ultima_modificacao_registrada: 2013-12-23 23:15:00+00:00
revisao: 1
metodo_extracao: python-docx 1.2.0 (insumos/extrair_docx.py)
transcrito_em: 2026-07-29 16:41
---

> Transcricao automatica e literal do documento oficial. O conteudo nao foi
> reescrito, resumido nem reordenado. Trechos nao transcritiveis estao marcados
> como **[LACUNA: ...]** no ponto correspondente.
**VIGIBARRAGENS–MT SAÚDE**

Documento de Concepção e Especificação Funcional e Técnica

Plataforma estadual de monitoramento de barragens, alerta precoce, análise de impacto sanitário e vigilância pós-desastre

**Tabela 1 do documento original**

| **Versão** | 1.0 – especificação para desenvolvimento |
|---|---|
| **Data** | 29 de julho de 2026 |
| **Escopo inicial** | Piloto Cuiabá/MT com expansão para o Estado de Mato Grosso |
| **Área proponente** | Vigidesastres / CIEVS / Vigilância em Saúde |
| **Princípio operacional** | Uso de dados disponíveis e automatizados, sem geração de demanda adicional à assistência durante o desastre |


*Documento-base para elaboração dos códigos, banco de dados, APIs, painéis e rotinas de alerta.*

## Controle do documento


**Tabela 2 do documento original**

| **Item** | **Definição** |
|---|---|
| Título | VIGIBARRAGENS–MT Saúde – Documento de Concepção e Especificação Funcional e Técnica |
| Finalidade | Orientar a implementação do banco de dados, conectores, rotinas analíticas, painel, motor de alertas e módulo de apoio por inteligência artificial. |
| Público-alvo | Gestores da SES-MT, Vigidesastres, CIEVS, Defesa Civil, SEMA, equipes de ciência de dados, desenvolvimento, epidemiologia e geoprocessamento. |
| Status | Versão inicial para validação técnica e priorização do MVP. |
| Premissa de segurança | A plataforma não substitui laudo de estabilidade, classificação oficial, ordem de evacuação ou decisão de autoridade competente. |


## Sumário executivo


O VIGIBARRAGENS–MT Saúde é proposto como uma plataforma estadual de inteligência sanitária territorial para monitorar barragens, integrar dados estruturais e hidroclimáticos, identificar populações e serviços expostos, apoiar alertas antecipados e acompanhar os efeitos de um possível desastre sobre a saúde. A solução deve combinar banco geoespacial, séries temporais, rotinas de integração, regras auditáveis, análise epidemiológica e uma camada de inteligência artificial supervisionada.

**Tabela 3 do documento original**

| **PRINCÍPIO CENTRAL:** nenhum indicador crítico do módulo operacional poderá depender de coleta extraordinária realizada pela assistência durante a fase aguda do desastre. Os dados devem ser obtidos de sistemas já existentes, de integrações automatizadas ou de cadastros atualizados em situação de normalidade. |
|---|


O Power BI deverá ser utilizado como camada de visualização gerencial, e não como repositório primário nem como motor de simulação. O núcleo da solução deverá operar em banco PostgreSQL/PostGIS, com serviços Python para ingestão, geoprocessamento, indicadores, detecção de sinais, alertas e geração de produtos. A expansão estadual deverá ser progressiva, iniciando pelas barragens e territórios com dados suficientes e maior dano potencial.

### Decisões de desenho já estabelecidas


**Dados disponíveis:** somente indicadores sustentados por fontes acessíveis e com periodicidade compatível serão ativados no painel operacional.

**Demanda assistencial zero:** não serão criados formulários, planilhas paralelas ou rotinas de alimentação destinadas a profissionais assistenciais durante o evento.

**Classificação oficial preservada:** CRI, DPA, nível de emergência e declarações oficiais serão exibidos com fonte, norma e data, sem reclassificação silenciosa.

**Sem “probabilidade de rompimento” genérica:** o sistema calculará prioridade operacional e prontidão sanitária; não emitirá probabilidade estrutural sem modelo de engenharia validado.

**Alertas supervisionados:** regras automáticas poderão identificar condições críticas, mas ordens de evacuação e decisões de engenharia permanecerão sob autoridade competente.

**Transparência:** todo indicador deverá exibir fonte, horário de atualização, regra de cálculo e nível de confiança.

### Estrutura do documento


**1.** Escopo, objetivos, usuários e princípios.

**2.** Arquitetura funcional e tecnológica.

**3.** Inventário de fontes e critérios de disponibilidade.

**4.** Modelo lógico de dados e contratos de integração.

**5.** Catálogo de indicadores e regras de cálculo.

**6.** Motor de alertas, vigilância pós-desastre e inteligência artificial.

**7.** Plano de implantação, testes, segurança e critérios de aceite.

## 1. Contexto e justificativa


O Produto 4 do Vigidesastres Cuiabá prevê a análise da capacidade de preparação e resposta do setor saúde frente a desastres associados ao rompimento de barragens, com mapeamento de áreas e populações vulneráveis, potenciais impactos à saúde, fluxos de resposta e recomendações. A proposta estadual aproveita essa base metodológica para estruturar uma solução permanente, escalável e interoperável.

A plataforma deve responder a cinco perguntas operacionais: qual estrutura exige atenção; qual território pode ser atingido; quais pessoas e serviços estão expostos; quais consequências sanitárias são plausíveis; e quais gestores precisam receber informação antecipada. Após o evento, deve responder onde há aumento de atendimentos, internações, agravos, óbitos, interrupção de água ou perda de acesso, utilizando registros já produzidos na rotina dos sistemas de saúde.

### 1.1 Objetivo geral


Desenvolver uma plataforma estadual para integrar, processar e visualizar dados relacionados às barragens de Mato Grosso, produzir indicadores de risco e prontidão sanitária, emitir alertas territorializados e monitorar impactos pós-desastre sem gerar novas demandas à área assistencial.

### 1.2 Objetivos específicos


Consolidar um cadastro estadual único de barragens e suas classificações oficiais.

Integrar chuva, nível, vazão, previsões e observações satelitais em tempo quase real.

Cruzar manchas de inundação com população, vulnerabilidades, rede de saúde, água e infraestrutura.

Identificar municípios, regiões de saúde, gestores e serviços que devem receber alertas.

Calcular indicadores reproduzíveis de exposição, impacto potencial, prontidão e qualidade dos dados.

Detectar sinais epidemiológicos e assistenciais posteriores ao desastre a partir de bases rotineiras.

Gerar mapas, painéis, SITREP, boletins e relatórios com rastreabilidade das fontes.

Disponibilizar assistência por IA para síntese, consulta e simulação supervisionada.

### 1.3 Fora de escopo


Emitir laudo de estabilidade ou substituir inspeções de engenharia.

Calcular probabilidade de rompimento sem dados instrumentais e modelo técnico específico.

Determinar evacuação ou acionar sirenes sem ordem da autoridade responsável.

Criar prontuário, sistema assistencial ou nova ficha obrigatória durante a fase aguda.

Exibir dados pessoais ou clínicos individualizados em painel público.

Raspar o painel público do Power BI como fonte primária; deverão ser identificadas as bases subjacentes e os respectivos responsáveis.

## 2. Usuários, governança e responsabilidades


**Tabela 4 do documento original**

| **Perfil** | **Responsabilidades no sistema** | **Permissão sugerida** |
|---|---|---|
| Administrador técnico | Configuração, conectores, usuários, auditoria, parâmetros e disponibilidade. | Administração total; sem alteração de classificações oficiais. |
| CIEVS/Vigidesastres | Monitoramento, validação de alertas, Sala de Situação, SITREP e comunicação de risco. | Leitura ampla; validação e publicação de produtos. |
| Defesa Civil | Informações territoriais, eventos, evacuação, rotas e resposta intersetorial. | Leitura operacional e registro de decisões autorizadas. |
| SEMA/órgão fiscalizador | Classificação, inspeção, anomalias e documentação da barragem. | Responsabilidade sobre dados técnicos sob sua competência. |
| Gestor municipal/regional | Recebimento de alertas, confirmação e execução do plano local. | Visão territorial e confirmação simplificada. |
| Regulação/SAMU/rede hospitalar | Uso de produtos para organização da resposta; sem alimentação paralela obrigatória. | Consulta a mapas, capacidade e rotas. |
| Ciência de dados/geoprocessamento | ETL, indicadores, modelos, qualidade e manutenção. | Acesso técnico controlado e auditado. |
| Público | Informação não sensível, educativa e de transparência. | Painel público resumido, sem dados restritos. |


### 2.1 Governança mínima


**Comitê gestor:** Vigidesastres/CIEVS, Defesa Civil, SEMA, áreas assistenciais estratégicas, TI e ciência de dados.

**Comitê técnico:** engenharia de barragens, hidrologia, meteorologia, epidemiologia, saúde ambiental, geoprocessamento e logística.

**Proprietário de cada dado:** definido no catálogo de fontes, com responsável, periodicidade, finalidade, base legal e contato.

**Gestão de mudanças:** novos indicadores e alterações de pesos, limiares ou regras somente após versionamento e validação.

**Auditoria:** registro de origem, processamento, versão do código, horário, resultado e usuário que aprovou cada alerta ou produto.

## 3. Arquitetura funcional


**Tabela 5 do documento original**

| **Módulo** | **Função principal** | **Saídas** |
|---|---|---|
| M01 – Cadastro Barragem 360° | Consolidar identificação, localização, finalidade, fiscalizador, classificação, documentos e relacionamentos territoriais. | Ficha individual, histórico, pendências e metadados. |
| M02 – Monitoramento hidroclimático | Integrar chuva, previsão, nível, vazão, telemetria e observações por bacia. | Séries temporais, acumulados, tendências e sinais. |
| M03 – Análise geoespacial | Cruzar manchas, ZAS/ZSS, setores censitários, saúde, água, vias e infraestrutura. | População exposta, serviços ameaçados e mapas. |
| M04 – Prontidão e capacidade | Organizar informações previamente cadastradas sobre planos, rotas, alertas, abrigos e rede de saúde. | Índice de prontidão e lacunas de preparação. |
| M05 – Motor de alertas | Aplicar regras, deduplicar eventos, localizar destinatários e registrar confirmação. | Alertas informativos, de preparação, ação ou críticos. |
| M06 – Vigilância pós-desastre | Detectar aumentos de agravos, atendimentos, internações, óbitos e alterações ambientais. | Sinais epidemiológicos e assistenciais. |
| M07 – Sala de Situação | Reunir linha do tempo, decisões, mapas e produtos automáticos. | SITREP, boletim, resumo executivo e pendências. |
| M08 – Assistente de IA | Consultar dados, explicar sinais, estruturar cenários e redigir produtos para revisão. | Respostas citadas, cenários e minutas supervisionadas. |
| M09 – Qualidade e auditoria | Avaliar completude, atualidade, consistência, disponibilidade e linhagem. | Selos de confiança, logs e alertas técnicos. |


### 3.1 Fluxo operacional


**Tabela 6 do documento original**

| FONTES → CONECTORES/ETL → BANCO BRONZE → PADRONIZAÇÃO SILVER → CAMADAS GOLD/INDICADORES → MOTOR DE REGRAS → API/PAINEL/ALERTAS → VALIDAÇÃO HUMANA → PRODUTOS E REGISTRO DE AUDITORIA |
|---|


As camadas Bronze, Silver e Gold devem preservar os dados originais, padronizar chaves e produzir tabelas analíticas. Nenhuma transformação deverá sobrescrever a classificação nativa. Dados estimados devem permanecer separados dos dados observados e identificados por método, versão e incerteza.

### 3.2 Arquitetura tecnológica recomendada


**Tabela 7 do documento original**

| **Camada** | **Tecnologia sugerida** | **Observação** |
|---|---|---|
| Banco relacional/geoespacial | PostgreSQL 16+ e PostGIS 3+ | Repositório primário, geometrias, indicadores e metadados. |
| Séries temporais | PostgreSQL particionado ou TimescaleDB | Chuva, nível, vazão, sensores e execução dos modelos. |
| ETL e análise | Python 3.12; Polars/Pandas; GeoPandas; Rasterio; Xarray; SQLAlchemy; Pydantic | Conectores modulares e validação de esquemas. |
| API | FastAPI + OpenAPI | Consumo pelo painel, WebGIS, alertas e integrações. |
| Orquestração MVP | PowerShell + Agendador de Tarefas do Windows | Compatível com o ambiente operacional atual da SES-MT. |
| Orquestração escalável | Prefect, Airflow ou Celery | Adotar após validação do MVP e infraestrutura. |
| Visualização executiva | Power BI | Indicadores, filtros, relatórios e visão gerencial. |
| Visualização operacional | WebGIS com MapLibre/Leaflet ou aplicação Python | Mapas, manchas, rotas, séries e simulações. |
| Alertas | Serviço próprio com e-mail, Teams, SMS e canal institucional autorizado | Confirmação por gestor; sem envio indiscriminado à assistência. |
| IA | Modelo de linguagem com RAG e chamadas estruturadas | Acesso somente às views autorizadas; saída em JSON e revisão humana. |


### 3.3 Estrutura inicial de diretórios


C:\SES_MT_INTELIGENCIA_SAUDE\05_vigibarragens_mt\
├── app\
│   ├── api\
│   ├── core\
│   ├── connectors\
│   ├── etl\
│   ├── geo\
│   ├── indicators\
│   ├── alerts\
│   ├── surveillance\
│   ├── ai\
│   └── reporting\
├── config\
├── data\bronze\
├── data\silver\
├── data\gold\
├── database\migrations\
├── docs\
├── logs\
├── outputs\
├── scripts_powershell\
└── tests\

## 4. Inventário de fontes de dados e disponibilidade


A inclusão de uma fonte no sistema requer confirmação de acesso, periodicidade, granularidade, termos de uso, responsável e mecanismo de contingência. O painel público do Power BI deve ser tratado apenas como referência visual até que suas bases subjacentes sejam identificadas; raspagem de elementos do relatório não é recomendada.

**Tabela 8 do documento original**

| **Código** | **Fonte** | **Conteúdo** | **Acesso** | **Granularidade** | **Latência** | **Disponibilidade** | **Regra de uso** |
|---|---|---|---|---|---|---|---|
| BARR-01 | SNISB/ANA | Cadastro nacional de barragens, fiscalizador, finalidade, CRI/DPA e situação cadastral. | Portal e dados abertos; conector por download/API a validar. | Nacional / barragem | Conforme publicação | B – automação viável | Chave principal para cadastro; preservar data e norma da classificação. |
| BARR-02 | SIGBM/ANM | Barragens de mineração, DCE, PAEBM e situação de emergência. | Dados abertos gerados diariamente e módulo público. | Barragem | Diária | A – prioritária | Utilizar endereço de dados abertos vigente; não inferir estabilidade. |
| BARR-03 | SEMA-MT / base estadual | Barragens fiscalizadas pelo Estado, inspeções, documentos, anomalias e coordenadas. | Acesso institucional/banco/arquivo. | Barragem | Definida pelo órgão | C – requer acordo | Fonte prioritária para detalhamento estadual. |
| BARR-04 | Empreendedores | Telemetria, níveis, vazões, instrumentos, PAE/PAEBM e manchas oficiais. | API, arquivo ou acordo de cooperação. | Sensor/barragem | Minutos a diária | D – dependente | Somente dados formalmente autorizados e com SLA. |
| HID-01 | ANA HidroWeb/Hidro-Telemetria | Chuva, nível, vazão, qualidade da água e sedimentos. | API HidroWebservice com autenticação; extração telemétrica. | Estação | Quase real a histórica | A – prioritária | Normalizar UTC, códigos de estação e flags de qualidade. |
| MET-01 | INMET | Chuva, temperatura, umidade, vento e avisos. | Portal/arquivos; automação a confirmar conforme serviço. | Estação | Horária; histórico | B | Dados automáticos são brutos e exigem controle de qualidade. |
| MET-02 | Cemaden PED/Mapa Interativo | Pluviômetros, estações hidrológicas, alertas e rede observacional. | API PED/Swagger e downloads; acesso a validar. | Estação/município | 10 min a quase real | A/B | Dados em UTC e potencialmente brutos. |
| SAT-01 | NASA GPM IMERG Early | Precipitação por satélite. | Earthdata/PPS; autenticação gratuita. | Grade 0,1° | 30 min; latência ~4 h | A | Cobertura complementar; não substituir pluviômetros. |
| SAT-02 | Copernicus Sentinel-1 | Radar para delimitação de inundação e mudança de superfície. | Copernicus Data Space APIs. | Cena/pixel | Conforme órbita | B | Não é sensor contínuo; processamento depende de cena disponível. |
| SAT-03 | Sentinel-2/Landsat/CBERS | Imagem óptica para danos, cobertura do solo e reservatório. | APIs/catálogos públicos. | Cena/pixel | Dias | B | Limitado por nuvens; uso complementar. |
| POP-01 | IBGE Censo 2022 | População, domicílios e características por setor censitário. | Downloads oficiais. | Setor censitário | Censitário | A | Base para estimar exposição; registrar método de alocação espacial. |
| GEO-01 | Manchas PAE/PAEBM | ZAS/ZSS, profundidade, velocidade e tempo de chegada. | Arquivo oficial do responsável/fiscalizador. | Polígono/raster | Conforme revisão | C/D | Dados essenciais; sem mancha oficial, limitar análises e marcar incerteza. |
| SAU-01 | CNES | Estabelecimentos, serviços, leitos, equipes, equipamentos e profissionais. | Download por competência e webservice. | Estabelecimento | Mensal | A | Representa capacidade cadastrada, não disponibilidade operacional em tempo real. |
| SAU-02 | SIM | Óbitos e causas. | DATASUS público e base estadual. | Município/registro | Atraso variável | B/C | Uso para linha de base e avaliação posterior; não é fonte primária das primeiras horas. |
| SAU-03 | SINAN | Agravos de notificação, incluindo leptospirose, intoxicação e acidentes. | DATASUS anonimizado e base estadual. | Município/caso institucional | Diária a anual | B/C | Oportunidade varia por agravo; não criar notificação adicional. |
| SAU-04 | SIH/SUS | Internações, diagnósticos e produção hospitalar. | Transferência de arquivos/DW. | AIH/estabelecimento | Mensal; interno pode ser mais oportuno | B/C | Adequado para impacto posterior e pressão assistencial consolidada. |
| SAU-05 | SIA/SUS | Produção ambulatorial. | Transferência de arquivos/DW. | Procedimento/estabelecimento | Mensal | B/C | Uso analítico, não tempo real. |
| SAU-06 | SISREG / regulação estadual | Solicitações, autorizações, transferências e filas. | Banco institucional/DW. | Solicitação/unidade | Minutos a diária | C – alto valor | Fonte potencial para detecção rápida sem demanda adicional. |
| SAU-07 | SAMU / urgência | Ocorrências, despachos, destino e tempos. | Integração institucional. | Ocorrência | Minutos a horas | C/D | Prioritária se já houver banco estruturado e acesso autorizado. |
| SAU-08 | GAL/LACEN | Exames, resultados, positividade e tempo de liberação. | Banco/integração institucional. | Exame/caso | Horas a dias | C | Útil para sinais pós-evento e qualidade da água/agravos. |
| AMB-01 | Sisagua/Vigiagua | Sistemas de abastecimento e qualidade da água. | Acesso institucional/exportações. | Sistema/amostra | Variável | C | Usar dados existentes; evitar formulários extraordinários. |
| INF-01 | DER-MT/DNIT/Defesa Civil | Rodovias, pontes, bloqueios, rotas e ocorrências. | Serviços geoespaciais, API ou arquivos. | Trecho/evento | Horas a diária | C/D | Necessário para isolamento e rotas alternativas. |
| DES-01 | S2ID/Atlas Digital | Ocorrências e histórico de desastres. | Portal e dados oficiais. | Município/evento | Conforme registro | B | Contexto histórico e calibração de cenários. |
| PBI-01 | Painel Power BI informado | Visualização existente sobre barragens. | Relatório público; bases internas não identificadas. | Não aplicável | Não aplicável | E – não usar como fonte | Mapear proprietário, modelo e fontes originais antes de integrar. |


### 4.1 Classificação de disponibilidade


**Tabela 9 do documento original**

| **Classe** | **Definição** | **Uso no MVP** |
|---|---|---|
| A | Fonte confirmada, estruturada e com acesso público ou institucional já disponível. | Pode compor o núcleo operacional. |
| B | Fonte disponível por download/portal, com automação tecnicamente viável e necessidade de validar estabilidade do acesso. | Implementar conector com cache e tolerância a falhas. |
| C | Fonte existente, porém dependente de credencial, banco estadual ou autorização institucional. | Planejar conector; não bloquear o MVP. |
| D | Fonte dependente de acordo, telemetria de terceiro ou acesso ainda não confirmado. | Manter como opcional/fase posterior. |
| E | Fonte inadequada como dado primário ou não acessível de forma confiável. | Não usar em cálculos críticos. |


### 4.2 Requisitos mínimos do catálogo de dados


**Tabela 10 do documento original**

| **Campo** | **Descrição** | **Campo** | **Descrição** |
|---|---|---|---|
| source_id | Identificador imutável da fonte. | nome | Nome oficial. |
| proprietario | Órgão responsável. | url_documentacao | Endereço oficial da documentação. |
| metodo_acesso | API, banco, arquivo, SFTP, serviço geoespacial ou carga pré-evento. | credencial | Tipo e local seguro de armazenamento. |
| frequencia | Periodicidade de extração. | latencia_esperada | Tempo entre ocorrência e disponibilidade. |
| timezone | UTC ou America/Cuiaba; armazenar UTC e exibir horário local. | granularidade | Barragem, estação, município, setor, estabelecimento, evento ou caso. |
| licenca_base_legal | Licença, acordo e finalidade. | responsavel_tecnico | Área responsável e contato institucional. |
| plano_contingencia | Fonte alternativa ou comportamento em indisponibilidade. | sla | Disponibilidade e prazo esperado. |
| campos_sensiveis | Classificação LGPD e restrições. | status | Ativa, degradada, suspensa ou em homologação. |


## 5. Modelo lógico de dados


O modelo deve combinar esquema dimensional, tabelas de séries temporais e objetos geoespaciais. Chaves naturais das fontes não devem ser usadas isoladamente: o sistema criará identificadores internos e tabelas de correspondência para tratar divergências entre SNISB, SIGBM, SEMA e empreendedores.

### 5.1 Entidades principais


**Tabela 11 do documento original**

| **Tabela** | **Finalidade** | **Campos mínimos** |
|---|---|---|
| dim_barragem | Cadastro mestre da barragem. | barragem_id, nomes, coordenadas, finalidade, curso d’água, município, bacia, empreendedor, fiscalizador. |
| xref_barragem_fonte | Correspondência entre identificadores. | barragem_id, source_id, source_record_id, confiança, data de validação. |
| fact_classificacao_barragem | Histórico de CRI, DPA, emergência e estabilidade. | tipo, valor original, norma, fonte, data de vigência, documento. |
| fact_inspecao_anomalia | Inspeções e anomalias. | data, tipo, gravidade, situação, prazo, fonte, documento. |
| dim_estacao | Estações meteorológicas/hidrológicas e sensores. | estacao_id, rede, tipo, coordenadas, bacia, status. |
| fact_observacao | Série temporal observada. | estacao_id, instante_utc, variável, valor, unidade, flag_qualidade, source_id. |
| fact_previsao | Previsões meteorológicas/hidrológicas. | modelo, rodada, validade, variável, valor, geometria, versão. |
| geo_mancha_cenario | Manchas oficiais e cenários. | cenario_id, barragem_id, geometria/raster, tipo, tempo_chegada, profundidade, velocidade, fonte. |
| dim_area_populacional | Setores e áreas estatísticas. | area_id, código IBGE, geometria, ano, população e grupos. |
| dim_estabelecimento_saude | Rede de saúde. | CNES, tipo, coordenadas, serviços, município, região de saúde. |
| dim_ponto_agua | Captação, ETA, poço e reservatório. | tipo, operador, população abastecida, coordenadas. |
| dim_infraestrutura | Pontes, vias, escolas, abrigos e estruturas críticas. | tipo, capacidade, responsável, geometria. |
| fact_exposicao | Interseções pré-calculadas por cenário. | cenario_id, objeto_id, tipo_objeto, métrica, valor, método. |
| fact_indicador | Resultados dos indicadores. | indicator_code, entidade, instante, valor, unidade, nível, confiança, versão. |
| fact_alerta | Ciclo do alerta. | alerta_id, regra, severidade, barragem, áreas, gerado, validado, publicado, status. |
| fact_entrega_alerta | Destinatários e confirmação. | alerta_id, contato, canal, enviado, entregue, confirmado, resposta. |
| fact_evento_desastre | Evento confirmado ou exercício. | evento_id, tipo, início, fim, autoridade, situação, geometria. |
| fact_sinal_saude | Sinais pós-desastre. | evento_id, síndrome/agravo, área, janela, observado, esperado, razão, método, nível. |
| fact_pipeline_run | Execução técnica. | pipeline, início, fim, status, linhas, hash, versão, erro. |
| fact_data_quality | Qualidade por fonte/tabela. | completude, atualidade, consistência, duplicidade, cobertura, nota. |


### 5.2 Regras de modelagem


Armazenar datas e horas em UTC; converter para America/Cuiaba na apresentação.

Usar SIRGAS 2000 (EPSG:4674) para intercâmbio e projeção métrica adequada para cálculos de área/distância.

Preservar arquivos e registros brutos com hash SHA-256, data de obtenção e versão.

Nunca sobrescrever histórico; aplicar vigência temporal e versionamento das classificações.

Separar valor observado, previsto, estimado e imputado.

Manter coluna de fonte e método em toda tabela Gold.

Não carregar identificadores pessoais para o painel; agregações mínimas devem respeitar LGPD e regras institucionais.

Usar constraints, chaves estrangeiras, índices espaciais GiST e particionamento temporal nas observações.

### 5.3 Contrato padrão de registro de indicador


**Tabela 12 do documento original**

| **Campo** | **Tipo** | **Obrigatório** | **Exemplo** |
|---|---|---|---|
| indicator_code | string | Sim | HID_CHUVA_72H |
| entity_type | string | Sim | barragem |
| entity_id | uuid/string | Sim | ... |
| reference_time_utc | timestamp | Sim | 2026-07-29T18:00:00Z |
| value | numeric | Não | 118.4 |
| unit | string | Sim | mm |
| status | enum | Sim | VALID |
| confidence_class | enum A-E | Sim | A |
| source_ids | array | Sim | [MET-02, SAT-01] |
| method_version | string | Sim | rainfall_accum_v1.2 |
| calculated_at_utc | timestamp | Sim | ... |
| quality_flags | json | Não | {"missing_pct": 0.02} |
| explanation | string | Não | Acumulado ponderado na bacia. |


## 6. Catálogo de indicadores


Os indicadores estão classificados por prioridade: P1 (MVP), P2 (expansão) e P3 (avançado). Os limiares devem ser configuráveis por YAML/banco e aprovados pelo comitê técnico; não devem ser codificados diretamente nas funções. A coluna “ação” define por que o indicador existe.

**Tabela 13 do documento original**

| **Código** | **Indicador** | **Definição** | **Fórmula/lógica** | **Fonte** | **Granularidade** | **Latência** | **Prior.** | **Ação** | **Limitações** |
|---|---|---|---|---|---|---|---|---|---|
| CAD-01 | Cobertura cadastral | Percentual de barragens estaduais presentes no cadastro mestre. | n cadastradas / n inventariadas × 100 | SNISB, ANM, SEMA | Estado/município | Mensal | P1 | Identificar lacunas de integração. | Denominador depende do inventário oficial consolidado. |
| CAD-02 | Cobertura de classificação | Barragens com CRI e DPA vigentes. | n com CRI e DPA / n cadastradas × 100 | SNISB/SEMA/ANM | Estado | Mensal | P1 | Priorizar atualização cadastral. | Não classificar ausentes como baixo risco. |
| CAD-03 | Cobertura de mancha oficial | Barragens elegíveis com mancha georreferenciada válida. | n com mancha / n elegíveis × 100 | PAE/PAEBM | Estado | Mensal | P1 | Limitar ou habilitar análise de impacto. | Necessita definição de elegibilidade. |
| CAD-04 | Atualidade documental | Documentos dentro da validade. | n documentos válidos / n exigidos × 100 | Órgão fiscalizador | Barragem | Diária/mensal | P1 | Gerar pendência de preparação. | Não substituir avaliação regulatória. |
| CAD-05 | Completude crítica | Campos essenciais preenchidos. | campos válidos / campos obrigatórios × 100 | Todas | Barragem/fonte | Por carga | P1 | Bloquear cálculo quando insuficiente. | Campos ponderados por criticidade. |
| CAD-06 | Conflito entre fontes | Quantidade de atributos divergentes. | contagem por regra de reconciliação | SNISB/ANM/SEMA | Barragem | Por carga | P1 | Encaminhar validação do cadastro. | Preservar valores e não escolher automaticamente em conflitos críticos. |
| CAD-07 | Horas desde atualização | Idade do dado mais recente. | agora_utc – max(instante_dado) | Todas | Fonte/entidade | Contínua | P1 | Sinalizar dado desatualizado. | Comparar com SLA específico da fonte. |
| CAD-08 | Disponibilidade do pipeline | Execuções bem-sucedidas no período. | runs_ok / runs_total × 100 | Logs | Pipeline | Diária | P1 | Alerta técnico e contingência. | Separar falha da fonte e falha interna. |
| HID-01 | Chuva acumulada 1 h | Soma da precipitação na última hora. | Σ chuva válida | INMET/Cemaden/ANA | Estação/bacia | 10–60 min | P1 | Detectar intensidade recente. | Controlar duplicidade e relógio UTC. |
| HID-02 | Chuva acumulada 6 h | Soma da precipitação nas últimas 6 h. | Σ chuva válida | INMET/Cemaden/ANA/IMERG | Bacia | 10–60 min | P1 | Acompanhar evento em formação. | Ponderação por área e cobertura. |
| HID-03 | Chuva acumulada 24 h | Soma da precipitação em 24 h. | Σ chuva válida | INMET/Cemaden/ANA/IMERG | Bacia | 10–60 min | P1 | Regra de atenção hidroclimática. | Limiares por bacia e sazonalidade. |
| HID-04 | Chuva acumulada 72 h | Soma da precipitação em 72 h. | Σ chuva válida | INMET/Cemaden/ANA/IMERG | Bacia | 10–60 min | P1 | Avaliar antecedência e saturação. | Não usar limiar único estadual. |
| HID-05 | Percentil climatológico | Posição da chuva atual na distribuição histórica. | ECDF do acumulado por mês/SE | Histórico INMET/ANA/IMERG | Bacia | Horária | P2 | Identificar condição excepcional. | Exige série histórica consistente. |
| HID-06 | Cobertura espacial da chuva | Parcela da bacia acima do limiar. | área pixels > limiar / área bacia | IMERG/radar | Bacia | ~4 h/variável | P2 | Diferenciar chuva localizada e generalizada. | Resolução IMERG aproximada de 0,1°. |
| HID-07 | Previsão de chuva 24/48/72 h | Acumulado previsto na bacia. | Σ previsão por janela | Modelo oficial disponível | Bacia | Por rodada | P2 | Antecipar preparação. | Manter rodada, modelo e incerteza. |
| HID-08 | Nível observado | Nível mais recente do reservatório/curso d’água. | última leitura válida | Telemetria/ANA/Cemaden | Sensor | Minutos | P1 | Monitorar tendência e limites operacionais. | Depende de datum e curva validados. |
| HID-09 | Taxa de elevação do nível | Variação do nível por tempo. | Δnível / Δtempo | Telemetria/ANA | Sensor | Minutos | P1 | Detectar aceleração anormal. | Filtrar ruído e leituras espúrias. |
| HID-10 | Vazão observada | Vazão mais recente. | última leitura válida | ANA/telemetria | Estação | Minutos/horas | P2 | Contextualizar cheia a jusante. | Nem toda estação possui curva válida em tempo real. |
| HID-11 | Disponibilidade da telemetria | Proporção de leituras recebidas. | n recebidas / n esperadas × 100 | Sensores | Sensor | Horária | P1 | Detectar cegueira operacional. | Falha de sensor não equivale a emergência estrutural. |
| HID-12 | Concordância estação-satélite | Diferença entre chuva terrestre e IMERG. | erro relativo/MAE por janela | Estações + IMERG | Bacia | Horária | P2 | Aumentar confiança e detectar falhas. | Comparar escalas espaciais distintas. |
| EST-01 | CRI oficial vigente | Categoria de risco informada pelo fiscalizador. | valor original | SNISB/ANM/SEMA | Barragem | Conforme atualização | P1 | Compor contexto de prioridade. | Não recalcular sem competência legal. |
| EST-02 | DPA oficial vigente | Dano potencial associado informado. | valor original | SNISB/ANM/SEMA | Barragem | Conforme atualização | P1 | Compor impacto potencial. | Preservar escala e norma de origem. |
| EST-03 | Nível oficial de emergência | Situação oficialmente declarada. | valor original | Fiscalizador/empreendedor | Barragem | Imediata | P1 | Acionar regras determinísticas. | Tem precedência sobre escore interno. |
| EST-04 | Condição de estabilidade | Situação da declaração oficial. | válida/não apresentada/não atestada | ANM/fiscalizador | Barragem | Conforme ciclo | P1 | Aplicar piso de severidade. | Não interpretar ausência de dado como não estabilidade. |
| EST-05 | Anomalias críticas ativas | Contagem e duração de anomalias críticas. | n e dias em aberto | Fiscalizador/empreendedor | Barragem | Diária | P2 | Priorizar acompanhamento. | Taxonomia precisa ser harmonizada. |
| EST-06 | Borda livre disponível | Distância entre nível e cota limite. | cota limite – nível | Telemetria/empreendedor | Barragem | Minutos | P3 | Regra avançada de monitoramento. | Somente com dados técnicos validados. |
| EXP-01 | População potencialmente atingida | População estimada na mancha oficial. | alocação espacial setor × fração de área/população | IBGE + mancha | Cenário | Por revisão | P1 | Dimensionar impacto. | Estimativa; expor método e incerteza. |
| EXP-02 | População na ZAS | População estimada na zona de autossalvamento. | interseção espacial | IBGE + ZAS | Barragem | Por revisão | P1 | Priorizar alerta e preparação. | Depende da ZAS oficial. |
| EXP-03 | População por tempo de chegada | Pessoas em faixas de chegada da onda. | interseção com isócronas | Mancha + IBGE | Cenário/faixa | Por revisão | P2 | Planejar resposta temporal. | Somente quando o estudo fornecer tempos. |
| EXP-04 | Índice de vulnerabilidade populacional | Proporção de crianças, idosos, deficiência e vulnerabilidade social. | combinação padronizada configurável | IBGE/cadastros agregados | Área | Anual/censitário | P2 | Priorizar territórios. | Evitar dados individuais; validar pesos. |
| EXP-05 | Domicílios potencialmente atingidos | Domicílios na mancha. | interseção espacial | IBGE + mancha | Cenário | Por revisão | P1 | Estimar desalojamento potencial. | Não equivale a dano confirmado. |
| EXP-06 | Unidades de saúde na mancha | Estabelecimentos intersectados. | ST_Intersects | CNES + mancha | Cenário | Mensal/revisão | P1 | Identificar perda direta de capacidade. | Revisar coordenadas CNES. |
| EXP-07 | Unidades potencialmente isoladas | Unidades cuja rota principal cruza área de impacto. | análise de rede com bloqueios | CNES + vias + mancha | Cenário | Por revisão | P2 | Planejar rotas alternativas. | Depende de rede viária e regras de bloqueio. |
| EXP-08 | Captações de água ameaçadas | Pontos de captação dentro/à jusante. | interseção/buffer hidrológico | Sisagua/operadores + mancha | Cenário | Por revisão | P1 | Acionar Vigiagua e contingência. | Exige localização confiável e sentido de fluxo. |
| EXP-09 | Infraestrutura crítica atingida | Pontes, escolas, abrigos e energia na área. | ST_Intersects | Bases territoriais | Cenário | Por revisão | P2 | Apoiar logística. | Cobertura das bases varia. |
| EXP-10 | Margem de evacuação estimada | Diferença entre chegada da onda e tempo de deslocamento. | tempo_chegada – tempo_rota | Estudo + rede viária | Área | Por cenário | P3 | Identificar áreas com margem insuficiente. | Não substituir plano de evacuação oficial. |
| SAU-01 | Leitos cadastrados expostos | Leitos CNES em unidades na mancha/isoladas. | Σ leitos cadastrados | CNES + exposição | Cenário | Mensal | P1 | Estimar capacidade potencialmente perdida. | Não representa leito disponível. |
| SAU-02 | Serviços estratégicos expostos | UTI, diálise, obstetrícia, trauma e outros. | contagem por serviço | CNES | Cenário | Mensal | P1 | Identificar dependências críticas. | Validar cadastro e atividade real em normalidade. |
| SAU-03 | Tempo de acesso a referência | Tempo estimado até serviço de referência. | menor caminho na rede | CNES + vias | Origem/serviço | Por atualização viária | P2 | Planejar referência e transporte. | Condições reais podem divergir. |
| SAU-04 | Aumento de solicitações de regulação | Variação frente à linha de base. | observado / esperado | SISREG | Município/unidade | Horas/dias | P1 se disponível | Detectar pressão assistencial. | Requer acesso institucional oportuno. |
| SAU-05 | Aumento de atendimentos de urgência | Variação por síndrome/causa. | observado / esperado | Urgência/DW | Município/unidade | Horas/dias | P2 | Detectar impacto agudo. | Somente se registro já existir e for acessível. |
| SAU-06 | Internações relacionadas | Internações por causas selecionadas. | contagem/taxa | SIH/DW | Município | Dias/mês | P1 pós | Avaliar impacto consolidado. | Latência impede uso nas primeiras horas. |
| SAU-07 | Ocupação operacional | Ocupação real quando integração automática existir. | ocupados / operacionais × 100 | Sistema hospitalar/DW | Unidade | Horas | P2 | Apoiar gestão de capacidade. | Não solicitar planilha manual. |
| SAU-08 | Unidades sem atualização operacional | Unidades com feed interrompido. | idade do último registro | Sistemas internos | Unidade | Horas | P2 | Sinalizar indisponibilidade de informação. | Não inferir fechamento automático. |
| SAU-09 | Positividade laboratorial | Exames positivos entre realizados. | positivos / realizados × 100 | GAL/LACEN | Agravo/território | Dias | P2 pós | Qualificar sinais epidemiológicos. | Interpretar conforme indicação e volume de testes. |
| SAU-10 | Excesso de mortalidade | Óbitos acima do esperado. | observado – esperado; intervalo de confiança | SIM estadual | Município/período | Semanas/meses | P2 pós | Avaliar impacto tardio. | Não atribuir causalidade automaticamente. |
| PRE-01 | Plano específico disponível | Existência e vigência do plano. | 0/1 + validade | Cadastro pré-evento | Município/barragem | Trimestral | P1 | Identificar lacuna de preparação. | Atualizado em normalidade. |
| PRE-02 | Contatos validados | Pontos focais com validação recente. | n válidos / n exigidos × 100 | Cadastro | Território | Mensal | P1 | Garantir entrega de alertas. | Não atualizar durante crise, salvo gestão central. |
| PRE-03 | Cobertura de alerta/sirene | População coberta pelos mecanismos previstos. | pop coberta / pop ZAS × 100 | PAE/Defesa Civil | Barragem | Semestral | P2 | Planejar comunicação. | Cobertura teórica precisa de teste. |
| PRE-04 | Tempo desde último simulado | Dias desde exercício. | data atual – último simulado | Defesa Civil/município | Território | Mensal | P2 | Priorizar capacitação. | Não medir qualidade sozinho. |
| PRE-05 | Rotas alternativas válidas | Proporção de áreas com rota fora da mancha. | áreas com rota / áreas críticas × 100 | Plano + rede viária | Cenário | Semestral | P2 | Identificar isolamento potencial. | Requer validação local prévia. |
| PRE-06 | Capacidade de abrigamento pré-cadastrada | Relação entre vagas e população potencial. | vagas válidas / pop a evacuar | Defesa Civil/município | Território | Trimestral | P2 | Dimensionar lacunas. | Capacidade deve ser validada antes do evento. |
| PRE-07 | Prontidão de dados | Percentual de indicadores P1 calculáveis. | P1 válidos / P1 previstos × 100 | Metadados | Barragem | Diária | P1 | Decidir se o escore integrado pode ser emitido. | Abaixo do limiar, classificar como indeterminado. |
| ALT-01 | Alertas ativos | Número por severidade e território. | contagem status=ativo | Motor de alertas | Estado/município | Contínua | P1 | Visão operacional. | Evitar duplicidade por regra/evento. |
| ALT-02 | Tempo de detecção | Tempo entre dado crítico e criação do alerta. | created_at – source_event_at | Logs | Alerta | Contínua | P1 | Avaliar oportunidade. | Relógios sincronizados. |
| ALT-03 | Tempo de validação | Tempo até validação humana, quando exigida. | validated_at – created_at | Logs | Alerta | Contínua | P1 | Avaliar fluxo do CIEVS. | Separar alertas automáticos informativos. |
| ALT-04 | Taxa de entrega | Mensagens entregues. | entregues / enviadas × 100 | Gateway | Alerta/canal | Contínua | P1 | Escalonar falhas. | Entrega técnica não é confirmação humana. |
| ALT-05 | Taxa de confirmação | Destinatários responsáveis que confirmaram. | confirmados / obrigatórios × 100 | Sistema de alertas | Alerta | Contínua | P1 | Escalonar ausência de resposta. | Confirmação simplificada pelo gestor. |
| ALT-06 | Falsos positivos operacionais | Alertas encerrados sem condição relevante após validação. | n FP / n alertas × 100 | Auditoria | Regra | Mensal | P2 | Calibrar regras. | Definição precisa de FP pelo comitê. |
| POS-01 | Casos observados por síndrome | Contagem de registros rotineiros classificados. | n por janela/território | SINAN/urgência/SISREG | Município/unidade | Horas a dias | P1 pós | Monitorar sinais sem nova ficha. | Depende da oportunidade da fonte. |
| POS-02 | Casos esperados | Linha de base sazonal. | mediana/modelo histórico | Bases históricas | Território/SE | Pré-calculada | P1 pós | Referência para detecção. | Recalibrar anualmente e após mudanças de sistema. |
| POS-03 | Razão observado/esperado | Intensidade relativa do sinal. | observado / esperado | Derivado | Território | Por carga | P1 pós | Gerar sinal estatístico. | Tratar esperado zero com regra específica. |
| POS-04 | Excesso absoluto | Diferença em relação ao esperado. | observado – esperado | Derivado | Território | Por carga | P1 pós | Dimensionar magnitude. | Exibir intervalo de incerteza. |
| POS-05 | Sinal CUSUM/EWMA | Detecção de mudança persistente. | algoritmo versionado | Bases de saúde | Território/síndrome | Diária | P2 pós | Detectar aumentos precoces. | Requer parametrização e validação retrospectiva. |
| POS-06 | Internações por causas externas | Volume e taxa após evento. | n/pop exposta × fator | SIH/DW | Município | Dias/mês | P1 pós | Avaliar trauma e impacto. | Latência variável. |
| POS-07 | Óbitos relacionados ao evento | Óbitos confirmados ou sob investigação. | contagem e taxa | SIM/Defesa Civil | Evento/território | Dias/meses | P1 pós | Acompanhar desfecho. | Separar preliminar, confirmado e atribuição causal. |
| POS-08 | Alterações na água | Amostras fora do padrão e sistemas interrompidos. | n fora padrão / n analisadas | Sisagua/GAL | Sistema/território | Dias | P1 pós | Acionar vigilância ambiental. | Volume de amostras influencia positividade. |
| POS-09 | Tempo de restabelecimento | Tempo até retorno de serviço crítico. | restored_at – disrupted_at | Bases operacionais | Serviço | Horas/dias | P2 pós | Monitorar recuperação. | Somente quando eventos são registrados rotineiramente. |
| POS-10 | Índice de recuperação sanitária | Síntese de serviços restabelecidos. | composição configurável | Múltiplas | Território | Diária | P3 | Acompanhar recuperação. | Pesos devem ser validados; não ocultar componentes. |


### 6.1 Regras obrigatórias de publicação do indicador


**Tabela 14 do documento original**

| **Regra** | **Implementação** |
|---|---|
| R-IND-01 | Não calcular quando dados mínimos não atingirem o limiar de suficiência; retornar status INSUFFICIENT_DATA. |
| R-IND-02 | Exibir valor, unidade, período, fonte, data/hora, versão do método e classe de confiança. |
| R-IND-03 | Diferenciar zero verdadeiro, nulo, não disponível, desatualizado, estimado e em processamento. |
| R-IND-04 | Não misturar classificações oficiais de escalas diferentes; manter valor original e tabela de equivalência apenas para visualização. |
| R-IND-05 | Indicadores estimados não podem substituir ordens ou níveis oficiais. |
| R-IND-06 | Todo limiar deve ser parametrizado, versionado e auditável. |
| R-IND-07 | Resultados agregados devem respeitar regras de privacidade e supressão de pequenas contagens. |


## 7. Estratificação de prioridade e motor de alertas


A plataforma deve distinguir a classificação regulatória da barragem da prioridade sanitária. O escore interno será um instrumento de triagem operacional e só poderá ser calculado quando houver suficiência de dados. A expressão “probabilidade de rompimento” não deverá ser empregada no painel, salvo quando fornecida por estudo de engenharia formalmente validado.

### 7.1 Índice de Prioridade Sanitária Integrada – IPS-B


**Tabela 15 do documento original**

| **Dimensão** | **Componentes** | **Peso inicial** |
|---|---|---|
| Pressão hidroclimática | Chuva 24/72 h, percentil, previsão, nível, taxa de elevação e cheia a jusante. | 30% |
| Condição oficial/estrutural | CRI, emergência oficial, estabilidade e anomalias formalmente registradas. | 30% |
| Impacto sanitário potencial | População, ZAS, vulnerabilidade, saúde, água, acessos e infraestrutura. | 25% |
| Déficit de prontidão | Plano, contatos, alertas, rotas, abrigos e prontidão dos dados. | 15% |


Fórmula inicial para homologação: IPS-B = 0,30 × H + 0,30 × E + 0,25 × I + 0,15 × D. Cada componente varia de 0 a 100. Pesos e pontos de corte deverão ser validados por painel de especialistas, análise multicritério, casos históricos e análise de sensibilidade.

### 7.2 Pré-condição de suficiência


**Tabela 16 do documento original**

| Se menos de 70% dos componentes P1 aplicáveis estiverem válidos, o sistema não emitirá escore numérico. O resultado será “PRIORIDADE INDETERMINADA – DADOS INSUFICIENTES”, acompanhado das lacunas. |
|---|


### 7.3 Faixas operacionais propostas


**Tabela 17 do documento original**

| **Faixa** | **Nível** | **Uso** |
|---|---|---|
| 0–19 | Verde – normalidade | Rotina de atualização, preparação e qualidade. |
| 20–39 | Amarelo – atenção | Acompanhamento reforçado e verificação de fontes. |
| 40–59 | Laranja – mobilização | Aviso a pontos focais e checagem dos planos. |
| 60–79 | Vermelho – emergência potencial | Sala de Situação e prontidão ampliada, conforme autoridade. |
| 80–100 | Roxo – resposta crítica | Resposta interinstitucional conforme evento e decisões oficiais. |


### 7.4 Regras determinísticas com precedência


**Tabela 18 do documento original**

| **Condição** | **Regra do sistema** |
|---|---|
| Nível oficial de emergência 2 ou 3 | Aplicar severidade mínima definida e notificar os responsáveis, sem reduzir o nível oficial. |
| Rompimento confirmado | Ativar módulo de evento, área de impacto, vigilância pós-desastre e Sala de Situação. |
| Ordem oficial de evacuação | Exibir ordem e fonte; suspender qualquer texto ambíguo da IA. |
| Não atestada estabilidade / declaração oficial equivalente | Aplicar piso de prioridade aprovado pelo comitê. |
| Chuva extrema + anomalia crítica ativa | Gerar alerta para validação imediata, ainda que o escore esteja incompleto. |
| Falha simultânea de telemetria crítica | Gerar alerta técnico de perda de observabilidade, não alerta de rompimento. |
| Unidade estratégica ou captação na mancha | Acionar alerta específico para gestão assistencial ou Vigiagua. |
| Fonte crítica desatualizada | Marcar painel como degradado e usar fonte de contingência, se existente. |


### 7.5 Estados do ciclo de alerta


**Tabela 19 do documento original**

| DETECTADO → GERADO → AGUARDANDO VALIDAÇÃO → VALIDADO → PUBLICADO → ENTREGUE → CONFIRMADO → EM ACOMPANHAMENTO → ENCERRADO/CANCELADO |
|---|


Alertas informativos de baixo risco podem ser automáticos.

Alertas de ação e críticos devem exigir validação do CIEVS/Vigidesastres ou regra institucional equivalente.

A confirmação será solicitada ao gestor/ponto focal, com resposta simples: recebido, em avaliação, plano ativado ou necessita apoio.

O sistema não solicitará relatório detalhado a profissionais assistenciais.

Deduplicação por barragem, regra, janela temporal e território evitará múltiplas mensagens para o mesmo sinal.

Ausência de confirmação dentro do prazo configurado deverá escalar para contato alternativo.

### 7.6 Estrutura do alerta


**Tabela 20 do documento original**

| **Campo** | **Conteúdo** |
|---|---|
| Identificação | Código, data/hora local, barragem, município da estrutura e severidade. |
| Motivos | Indicadores/regras acionados, valores, fontes e horários. |
| Territórios | Municípios, regiões de saúde e áreas potencialmente afetadas. |
| Impacto estimado | População, unidades, serviços e captações, sempre com classe de confiança. |
| Ações | Somente ações previstas no plano e adequadas ao perfil do destinatário. |
| Limite | Indicar explicitamente quando não constitui ordem de evacuação. |
| Confirmação | Botão/resposta simples pelo gestor responsável. |
| Auditoria | Versão da regra, hash do conteúdo e usuário validador. |


## 8. Vigilância pós-desastre sem nova demanda assistencial


O módulo pós-desastre deve ser ativado por evento confirmado ou exercício e utilizar exclusivamente dados já produzidos na rotina dos sistemas. A assistência não será responsável por preencher fichas paralelas para alimentar o painel. Onde não houver integração automática, o indicador deverá permanecer indisponível ou ser mantido apenas como cadastro de preparação.

### 8.1 Hierarquia temporal das fontes


**Tabela 21 do documento original**

| **Janela** | **Fontes prioritárias** | **Finalidade** |
|---|---|---|
| Minutos a horas | Alertas oficiais, telemetria, chuva, nível, satélite disponível, SAMU, regulação e sistemas hospitalares já integrados. | Reconhecer evento, pressão inicial, acessos e capacidade. |
| Horas a dias | Urgência, SISREG, GAL, SINAN oportuno, Sisagua e movimentação hospitalar. | Detectar sinais sindrômicos, transferências e alterações da água. |
| Dias a semanas | SINAN consolidado, SIH, SIA, SIM e investigação de óbitos. | Avaliar impacto, excesso de morbimortalidade e recuperação. |


### 8.2 Síndromes e desfechos monitoráveis


Trauma, afogamento e causas externas.

Síndrome diarreica e doenças transmitidas por água/alimentos.

Síndrome febril e leptospirose.

Síndrome respiratória.

Síndrome dermatológica.

Intoxicações exógenas e exposição a contaminantes.

Acidentes com animais peçonhentos.

Interrupção de tratamentos crônicos e necessidade de transferência.

Sofrimento mental, quando identificável em registros rotineiros.

Óbitos e excesso de mortalidade.

### 8.3 Métodos estatísticos


**Tabela 22 do documento original**

| **Método** | **Aplicação** | **Saída mínima** |
|---|---|---|
| Canal endêmico/quantis históricos | Agravos com sazonalidade e número suficiente. | Observado, mediana, limite superior e sinal. |
| Razão observado/esperado | Comparação simples em janelas curtas. | O/E, excesso absoluto e confiança. |
| Poisson/binomial negativa | Contagens ajustadas por população, tendência e sazonalidade. | Esperado, intervalo e probabilidade do sinal. |
| CUSUM/EWMA | Mudança pequena e persistente. | Escore e data de detecção. |
| Série temporal interrompida | Avaliação posterior do efeito do evento. | Mudança de nível e tendência. |
| Controle sintético/municípios comparadores | Análise avançada quando houver grupo comparável. | Contrafactual e diferença estimada. |


Todo sinal deverá ser descrito como associação temporal ou anomalia estatística, e não como causalidade confirmada. A confirmação epidemiológica depende de investigação e contexto.

### 8.4 Regra de demanda zero


**Tabela 23 do documento original**

| **Situação** | **Decisão de desenho** |
|---|---|
| Leitos operacionais não disponíveis automaticamente | Mostrar capacidade cadastrada no CNES e marcar disponibilidade real como não disponível. |
| Estoque por unidade exige planilha manual | Não incluir no painel operacional; manter apenas inventário pré-evento, se existente. |
| Contagem de sintomas em abrigo depende de nova ficha | Não ativar até existir sistema rotineiro ou integração autorizada. |
| Equipe assistencial precisa elaborar relatório narrativo | Substituir por geração automática de SITREP com revisão da coordenação. |
| Dado crítico ausente | Exibir lacuna e classe E; não transferir a produção à assistência. |


## 9. Inteligência artificial e simulação


A IA será uma camada de apoio, não o motor físico de ruptura. Manchas de inundação, tempos de chegada, profundidade e velocidade devem provir de estudos oficiais ou modelos hidráulicos validados. A IA poderá combinar cenários, consultar dados, explicar indicadores, priorizar pendências e produzir minutas de documentos.

### 9.1 Casos de uso permitidos


Consulta em linguagem natural sobre barragens, chuva, população e serviços expostos.

Síntese de indicadores com citação da fonte e horário de atualização.

Geração de cenários parametrizados a partir de manchas oficiais e condições hidroclimáticas.

Estimativa de faixas de demanda, sempre com premissas e incerteza.

Identificação de conflitos, dados faltantes e valores anômalos.

Geração de SITREP, boletim, informe ao gestor e lista de pendências para revisão humana.

Explicação de sinais epidemiológicos produzidos por algoritmos reproduzíveis.

Recuperação de ações previstas nos planos de contingência por meio de RAG.

### 9.2 Funções proibidas ou condicionadas


Declarar estabilidade ou risco estrutural por conta própria.

Determinar evacuação ou disparar sirene sem regra e autoridade formal.

Inventar dados ausentes ou omitir incerteza.

Atribuir causalidade epidemiológica automaticamente.

Acessar ou expor dados pessoais não necessários.

Enviar alerta crítico sem mecanismo de validação definido.

Gerar mancha de ruptura apenas por texto ou modelo generativo.

### 9.3 Contrato de saída da IA


**Tabela 24 do documento original**

| **Campo JSON** | **Regra** |
|---|---|
| answer | Texto objetivo, sem afirmar além dos dados. |
| data_timestamp | Horário do dado mais recente utilizado. |
| sources | Lista de source_id e registros. |
| assumptions | Premissas explícitas. |
| uncertainty | Limitações e classe de confiança. |
| recommended_actions | Ações existentes no plano, associadas ao perfil do usuário. |
| requires_human_approval | true para alertas, comunicação externa e decisões críticas. |
| prohibited_inference | Campo para registrar inferências que não foram realizadas por falta de dados. |


## 10. Especificações para desenvolvimento dos códigos


### 10.1 Serviços mínimos da API


**Tabela 25 do documento original**

| **Endpoint** | **Finalidade** |
|---|---|
| GET /v1/barragens | Lista com filtros por município, fiscalizador, CRI, DPA, emergência e disponibilidade de dados. |
| GET /v1/barragens/{id} | Ficha 360°, fontes, classificações, documentos e indicadores. |
| GET /v1/barragens/{id}/series | Séries de chuva, nível, vazão e telemetria. |
| GET /v1/barragens/{id}/exposure | População, saúde, água e infraestrutura por cenário. |
| GET /v1/indicators | Consulta padronizada de indicadores por código, entidade e período. |
| GET /v1/alerts | Alertas ativos e históricos conforme permissão. |
| POST /v1/alerts/{id}/validate | Validação por usuário autorizado. |
| POST /v1/alerts/{id}/ack | Confirmação simplificada do gestor. |
| GET /v1/events/{id}/surveillance | Sinais de saúde pós-desastre. |
| GET /v1/data-quality | Qualidade, disponibilidade e idade das fontes. |
| POST /v1/scenarios/run | Execução de cenário parametrizado, com trilha de auditoria. |
| POST /v1/ai/query | Consulta assistida com resposta estruturada e fontes. |


### 10.2 Padrões dos conectores


**Tabela 26 do documento original**

| **Método** | **Obrigação** |
|---|---|
| discover() | Listar recursos/estações/arquivos disponíveis e metadados. |
| extract(start,end) | Baixar somente a janela necessária, com retentativa e timeout. |
| validate_raw() | Validar esquema, tipos, coordenadas, datas, unidades e duplicidades. |
| load_bronze() | Persistir conteúdo bruto e hash sem alteração. |
| transform_silver() | Padronizar nomes, chaves, UTC, unidades e flags. |
| publish_gold() | Atualizar tabelas analíticas de forma idempotente. |
| healthcheck() | Informar disponibilidade, latência e última carga válida. |
| audit() | Registrar versão, duração, linhas, erros e checksum. |


### 10.3 Idempotência e tolerância a falhas


Cada carga deve possuir chave composta da fonte, identificador do registro e instante de referência.

Reprocessar uma janela não pode duplicar registros ou alterar histórico sem versionamento.

Aplicar retry exponencial, timeout, circuit breaker e cache da última carga válida.

Falha de uma fonte não deve interromper fontes independentes.

O sistema deve degradar de forma explícita, reduzindo a confiança e preservando o último dado válido com sua idade.

Segredos devem ficar em cofre/variáveis de ambiente, nunca em scripts ou repositório.

### 10.4 Configuração externa dos limiares


timezone: America/Cuiaba
indicators:
  HID-04:
    windows_hours: [24, 72]
    thresholds_by_basin:
      default: {attention: null, mobilization: null, critical: null}
alerts:
  acknowledgement_minutes:
    orange: 60
    red: 30
    purple: 15
  deduplication_window_minutes: 120
quality:
  minimum_score_for_integrated_index: 0.70
  stale_multiplier_by_source: 2.0
privacy:
  suppress_counts_below: 5

### 10.5 Pseudocódigo do cálculo de indicador


def calcular_indicador(contexto, especificacao):
    dados = carregar_dependencias(especificacao.sources, contexto)
    qualidade = avaliar_qualidade(dados, especificacao.quality_rules)

    if qualidade.suficiencia < especificacao.minimum_sufficiency:
        return IndicatorResult(status="INSUFFICIENT_DATA",
                               confidence="E",
                               quality_flags=qualidade.flags)

    valor = especificacao.algorithm(dados, contexto)
    nivel = aplicar_limites_configurados(valor, contexto)

    return IndicatorResult(
        value=valor,
        unit=especificacao.unit,
        status="VALID",
        level=nivel,
        confidence=qualidade.confidence,
        sources=dados.source_ids,
        method_version=especificacao.version,
    )

## 11. Telas e produtos


**Tabela 27 do documento original**

| **Tela/produto** | **Conteúdo mínimo** |
|---|---|
| Comando estadual | Barragens, alertas, municípios, população exposta, unidades, fontes degradadas e mapa. |
| Barragem 360° | Cadastro, histórico, classificações, documentos, séries, mancha, exposição e prontidão. |
| Monitoramento ambiental | Estações, chuva, previsão, nível, vazão, disponibilidade e satélite. |
| Mapa de impacto | Mancha, ZAS/ZSS, população, saúde, água, vias e tempo de chegada. |
| Alertas | Motivos, destinatários, confirmação, ações e linha do tempo. |
| Pós-desastre | Evento, sinais de saúde, observado/esperado, água, internações e óbitos. |
| Qualidade | Fontes, idade, completude, conflitos, pipelines e confiança. |
| Sala de Situação | Linha do tempo, decisões, pendências, mapas, SITREP e comunicação de risco. |
| Painel público | Informações não sensíveis, educação, transparência e situação agregada. |


### 11.1 Produtos automáticos


Boletim estadual periódico de monitoramento.

Alerta territorializado com confirmação do gestor.

Ficha Barragem 360°.

Mapa de população e serviços potencialmente afetados.

SITREP com revisão e aprovação.

Relatório de qualidade dos dados e fontes degradadas.

Relatório pós-evento com sinais epidemiológicos e assistenciais.

Relatório de recuperação e lições aprendidas.

## 12. Segurança, privacidade e continuidade


Controle de acesso baseado em função e território.

Autenticação institucional e, para perfis críticos, múltiplo fator.

Criptografia em trânsito e em repouso.

Segregação entre ambiente público e restrito.

Minimização e agregação de dados pessoais; proibição de dados identificáveis no painel público.

Logs imutáveis de acesso, alteração, alertas e uso da IA.

Backup, replicação e plano de recuperação de desastre.

Modo degradado com última carga válida, idade e aviso explícito.

Teste de indisponibilidade das fontes e dos canais de comunicação.

Revisão jurídica e de LGPD antes de integrar bases individualizadas.

### 12.1 Estratégia de testes


**Tabela 28 do documento original**

| **Tipo** | **Exemplos** |
|---|---|
| Unitário | Acumulados de chuva, interseções, regras de nulos, classificação e deduplicação. |
| Contrato | Mudança de esquema em APIs/arquivos, campos obrigatórios e tipos. |
| Integração | Fonte → Bronze → Silver → Gold → API. |
| Geoespacial | Projeção, geometria inválida, área, distância e interseção. |
| Retrospectivo | Aplicação das regras a eventos históricos e comparação com decisões conhecidas. |
| Carga | Volume de observações, consultas espaciais e múltiplos usuários. |
| Segurança | Permissões, injeção, exposição de dados e vazamento entre perfis. |
| Operacional | Simulado com perda de fonte, falha de canal e ativação da Sala de Situação. |
| IA | Fidelidade às fontes, recusa de inferência proibida, privacidade e estrutura JSON. |


### 12.2 Critérios de aceite do MVP


**1.** Cadastro consolidado das barragens prioritárias do piloto, com identificação e fonte.

**2.** Ingestão automática de pelo menos duas fontes hidroclimáticas e uma fonte de barragens.

**3.** Banco PostGIS com manchas, setores censitários e CNES.

**4.** Cálculo reproduzível dos indicadores P1 aplicáveis.

**5.** Mapa de população, unidades de saúde e captações potencialmente atingidas.

**6.** Motor de alertas em homologação, com deduplicação e confirmação de gestor.

**7.** Painel de qualidade e idade das fontes.

**8.** Rotina de vigilância pós-desastre a partir de pelo menos uma base de saúde institucional ou pública.

**9.** Geração automática de ficha e SITREP para revisão.

**10.** Documentação, testes e recuperação de falha aprovados.

## 13. Plano de implantação


**Tabela 29 do documento original**

| **Fase** | **Escopo** | **Entregas** |
|---|---|---|
| 0 – Descoberta e governança | Inventário, acessos, owners, barragens prioritárias e validação dos indicadores. | Catálogo de dados; matriz de acesso; backlog; termos de governança. |
| 1 – Piloto Cuiabá | Cadastro, manchas disponíveis, população, CNES, água, chuva e ficha 360°. | Banco, ETL inicial, WebGIS/painel e indicadores P1. |
| 2 – MVP estadual | Expansão para barragens prioritárias e alertas territorializados. | Mapa estadual, motor de regras, contatos e qualidade. |
| 3 – Vigilância pós-desastre | Integração de SINAN, SIM, SIH, SISREG/GAL conforme acesso. | Linhas de base, sinais e relatórios pós-evento. |
| 4 – Satélite e simulação | IMERG, Sentinel, rede viária e cenários. | Chuva em bacia, inundação observada, rotas e simulações. |
| 5 – IA supervisionada | RAG, consultas e geração de produtos. | Assistente auditável, SITREP e explicações. |


### 13.1 Backlog técnico inicial


**Tabela 30 do documento original**

| **Ordem** | **Épico** | **Resultado** |
|---|---|---|
| 1 | Cadastro mestre e correspondência de IDs | Uma barragem, múltiplas fontes, histórico preservado. |
| 2 | Catálogo e qualidade das fontes | Saber o que existe, quando atualiza e se está confiável. |
| 3 | PostGIS e camadas territoriais | Base espacial única. |
| 4 | Conector SNISB/ANM/SEMA | Cadastro e situação oficial. |
| 5 | Conectores ANA/Cemaden/INMET | Monitoramento hidroclimático. |
| 6 | Integração IBGE/CNES/Sisagua | Exposição sanitária. |
| 7 | Indicadores P1 e API | Núcleo analítico consumível. |
| 8 | Painel e WebGIS | Visualização executiva e operacional. |
| 9 | Alertas e contatos | Comunicação territorializada. |
| 10 | Vigilância pós-desastre | Sinais a partir de dados rotineiros. |
| 11 | Satélite e cenários | Observação e simulação avançada. |
| 12 | IA e geração de relatórios | Apoio supervisionado. |


## 14. Decisões necessárias antes da codificação


**Tabela 31 do documento original**

| **Decisão** | **Responsáveis sugeridos** | **Impacto** |
|---|---|---|
| Lista oficial de barragens e prioridade do piloto | SEMA, Defesa Civil, Vigidesastres | Define o universo inicial. |
| Acesso às bases subjacentes do painel Power BI | Proprietário do painel/TI | Evita duplicação e raspagem inadequada. |
| Disponibilidade de manchas oficiais e ZAS/ZSS | Fiscalizadores/empreendedores | Habilita análise territorial confiável. |
| Acesso ao DW de CNES, SINAN, SIM, SIH, SIA, SISREG e GAL | SES-MT/TI/áreas técnicas | Define oportunidade dos indicadores de saúde. |
| Canais institucionais de alerta | Gestão, TI, comunicação | Define entrega, confirmação e escalonamento. |
| Pontos focais por município/região | Vigidesastres/CIEVS/Defesa Civil | Permite territorialização. |
| Validação dos indicadores e pesos | Comitê técnico | Autoriza cálculo e publicação. |
| Ambiente de hospedagem e segurança | TI/segurança da informação | Define arquitetura de produção. |
| Regras de dado sensível e agregação | Jurídico, DPO e áreas técnicas | Define views públicas e restritas. |


### 14.1 Recomendação de início


**Tabela 32 do documento original**

| O desenvolvimento deve começar pelo inventário automatizado das fontes e pelo cadastro mestre de barragens. Sem essas duas bases, a construção antecipada do painel poderá produzir indicadores não sustentáveis ou dependentes de alimentação manual. |
|---|


Após a validação do documento, a primeira entrega de código deve conter: estrutura do projeto; modelo de configuração; migrations iniciais do PostgreSQL/PostGIS; catálogo de fontes; interface abstrata de conectores; conector de uma fonte de barragens; conector de uma fonte hidroclimática; carga do IBGE e CNES; e testes automatizados. O painel deve ser construído somente após as tabelas Gold e a API apresentarem resultados validados.

## Referências e documentação oficial


1. Agência Nacional de Águas e Saneamento Básico – SNISB.

2. ANA – Dados Abertos.

3. ANA – Manual do Serviço de Disponibilização de Dados Hidrológicos / HidroWebservice.

4. ANA – Hidro-Telemetria.

5. ANM – Dados Abertos.

6. ANM – SIGBM versão pública.

7. INMET – Estações automáticas.

8. Cemaden – Mapa Interativo.

9. Cemaden – Plataforma de Entrega de Dados / Swagger.

10. NASA GPM – IMERG.

11. Copernicus Data Space – APIs.

12. IBGE – Malha de Setores Censitários.

13. DATASUS – Transferência de Arquivos.

14. CNES – Download de bases.

15. Ministério da Saúde – SINAN, dados em transparência ativa.

16. Ministério da Saúde – SIM, dados de mortalidade.

17. Ministério da Saúde – Plano de contingência para emergência em saúde pública por rompimento de barragens.

18. Portal de Dados Abertos do SUS.

Acessos verificados em 29 de julho de 2026. A disponibilidade técnica, os métodos de autenticação e os termos de uso devem ser novamente validados durante a implantação.

## Apêndice A – Checklist de prontidão para início do desenvolvimento


**Tabela 33 do documento original**

| **Eixo** | **Item** | **Status** | **Responsável/evidência** |
|---|---|---|---|
| Governança | Comitê gestor nomeado | Pendente |   |
| Governança | Responsáveis por fonte definidos | Pendente |   |
| Escopo | Lista de barragens piloto aprovada | Pendente |   |
| Dados | Acesso SNISB/ANM homologado | Pendente |   |
| Dados | Acesso SEMA-MT homologado | Pendente |   |
| Dados | Manchas e ZAS/ZSS recebidas | Pendente |   |
| Dados | Base IBGE 2022 carregada | Pendente |   |
| Dados | CNES carregado e geocodificado | Pendente |   |
| Dados | Fontes ANA/Cemaden/INMET avaliadas | Pendente |   |
| Saúde | Acesso ao DW de saúde definido | Pendente |   |
| Alertas | Cadastro de gestores disponível | Pendente |   |
| Alertas | Canal institucional aprovado | Pendente |   |
| Tecnologia | PostgreSQL/PostGIS provisionado | Pendente |   |
| Tecnologia | Ambientes dev/homologação/produção | Pendente |   |
| Segurança | Matriz de acesso e LGPD aprovada | Pendente |   |
| Indicadores | P1 validados pelo comitê | Pendente |   |
| Testes | Cenários históricos selecionados | Pendente |   |
| Operação | SLA e plantão técnico definidos | Pendente |   |


## Apêndice B – Matriz de priorização dos códigos


**Tabela 34 do documento original**

| **Pacote** | **Prioridade** | **Dependências** | **Entregável técnico** |
|---|---|---|---|
| database_core | 1 | PostgreSQL/PostGIS | Migrations, schemas, constraints, índices e views. |
| source_catalog | 1 | Governança | Cadastro de fontes, SLA, credenciais e healthcheck. |
| connector_barragens | 1 | SNISB/ANM/SEMA | Ingestão e reconciliação. |
| connector_hydro | 1 | ANA/Cemaden/INMET | Séries temporais, UTC e qualidade. |
| geo_exposure | 1 | Manchas, IBGE, CNES | Interseções e tabelas de exposição. |
| indicator_engine | 1 | Gold tables | Registro genérico e indicadores P1. |
| api_core | 1 | Banco e indicadores | FastAPI e autenticação. |
| dashboard_mvp | 2 | API | Visão estadual e Barragem 360°. |
| alert_engine | 2 | Contatos e regras | Ciclo, deduplicação, canais e confirmação. |
| post_disaster | 2 | Bases de saúde | Linhas de base e sinais. |
| satellite_pipeline | 3 | Earthdata/Copernicus | IMERG e cenas Sentinel. |
| scenario_engine | 3 | Manchas/modelos | Cenários e rotas. |
| ai_assistant | 3 | API/RAG | Consulta e produtos supervisionados. |
