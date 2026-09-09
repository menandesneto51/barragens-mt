# 9. Dicionário de dados

Dicionário dos conjuntos **já coletados** e presentes em `dados/tratados/`. Os nomes de coluna
foram extraídos dos próprios arquivos e dos scripts `scripts/01_snisb_mt.py`,
`scripts/02_sigbm_anm.py`, `scripts/03_ibge_mt.py`, `scripts/04_powerbi_snisb.py` e
`scripts/05_consolidar_inventario.py`.

Todos os percentuais de lacuna desta página foram medidos diretamente nos CSVs, não estimados.

## 9.1 Arquivos existentes

| Arquivo | Registros | Colunas | Origem |
| --- | --- | --- | --- |
| `snisb_barragens_mt.csv` / `.geojson` | 1.248 | 45 | SNISB / ANA |
| `sigbm_barragens_mt.csv` / `.geojson` | 183 | 127 | SIGBM / ANM |
| `ibge_municipios_mt.csv` | 142 | 6 | IBGE localidades |
| `ibge_malha_municipios_mt.geojson` | 141 polígonos | — | IBGE malhas |
| `ibge_malha_municipios_mt_simplificada.geojson` | 141 polígonos | — | IBGE malhas (simplificada) |
| `ibge_malha_ufs_brasil.geojson` | 27 polígonos | — | IBGE malhas |
| `powerbi_snisb_mt.csv` | 1.248 | 14 | Relatório Power BI público do SNISB |
| `inventario_barragens_mt.csv` / `.geojson` | 1.248 | 71 | Consolidação SNISB + Power BI + SIGBM |

Convenções dos CSVs tratados: codificação UTF-8 com BOM, delimitador `;`, campo vazio para
dado ausente.

Legenda da coluna "Uso no IDAP" (dimensões e indicadores conforme `docs/03-idap.md`):

| Marca | Significado |
| --- | --- |
| **B1..B6** | Alimenta indicador da dimensão B (condição da barragem) |
| **C1..C8** | Alimenta indicador da dimensão C (impacto sanitário potencial) |
| **D1..D8** | Alimenta indicador da dimensão D (déficit de capacidade de resposta) |
| **R0x** | Alimenta regra determinística de sobreposição |
| Contexto | Não pontua; serve para identificação, recorte territorial ou auditoria |

---

## 9.2 `snisb_barragens_mt.csv` — cadastro consolidado SNISB / ANA

Fonte: `https://www.snirh.gov.br/arcgis/rest/services/IG/SNISB/FeatureServer/0/query`,
filtro `ING_SG_UFMUNICIPIO = 'MT'`, paginação de 2.000, `outSR=4326`.
Periodicidade da fonte: contínua, sem calendário publicado. Latência: dias a meses.

| Campo | Campo de origem | Tipo | Domínio / observação | Obrigatório | Uso no IDAP |
| --- | --- | --- | --- | --- | --- |
| `id_snisb` | `BAR_CD_SNISB` | texto | Chave primária do inventário | Sim | Contexto (chave) |
| `nome` | `BAR_NM_NOME` | texto | | Sim | Contexto |
| `nome_secundario` | — | texto | Nome alternativo | Não | Contexto |
| `codigo_no_orgao_fiscalizador` | — | texto | Código no sistema do órgão | Não | Contexto |
| `orgao_fiscalizador` | `ORG_NM_ORGANIZACAO` | categórico | SEMA-MT (781), ANM (183), ANEEL (154), ANA (130) | Sim | Contexto / roteamento de alerta |
| `empreendedor` | `NM_EMPREENDEDOR` | texto | | Não | Contexto / destinatário de alerta |
| `uf` | `ING_SG_UFMUNICIPIO` | texto | Sempre `MT` | Sim | Contexto |
| `municipio` | `ING_NM_MUNICIPIO` | texto | 150 grafias distintas para 142 municípios | Sim | Contexto territorial |
| `latitude_declarada` | `BAR_NU_LATITUDE` | decimal | Coordenada declarada no cadastro | Não | Conferência |
| `longitude_declarada` | `BAR_NU_LONGITUDE` | decimal | | Não | Conferência |
| `latitude` | geometria do FeatureServer | decimal | **Fonte de verdade** da localização (EPSG:4326) | Sim | Contexto territorial |
| `longitude` | geometria do FeatureServer | decimal | | Sim | Contexto territorial |
| `uso_principal` | `USO_PRINCIPAL` | categórico | Irrigação (497), Contenção de rejeitos de mineração (179), Hidroelétrica (153), Aquicultura (152), Dessedentação animal (79), Paisagismo (72), Recreação (57), Abastecimento humano (23), Industrial (22), Regularização de vazão (8), Contenção de sedimentos (4), Proteção do meio ambiente (2) | Sim | **C8** (rejeito) e contexto |
| `uso_complementar` | `USO_COMPLEMENTAR` | texto | Lista livre | Não | Contexto |
| `tipo_material` | `TIPO_MATERIAL` | categórico | Terra (831), Sem Informação (208), Terra-enrocamento (98), Concreto convencional (61), Enrocamento (10), Outros (9), Rejeitos (4), CCR (3), Alvenaria (2) | Não | Contexto |
| `altura_max_fundacao_m` | `BAR_NU_ALT_MAX_BASE_FUNDACAO` | decimal | metros | Não | Contexto (magnitude) |
| `altura_max_terreno_m` | `BAR_NU_ALT_MAX_NIVEL_TERRENO` | decimal | metros; mediana 4,9 m; máximo 73,0 m; **mínimo −11,0 m** (erro na fonte) | Não | Contexto (magnitude) |
| `capacidade_reservatorio_m3` | `BAR_NU_CAP_TOTAL_RESERV` | decimal | **Nome enganoso: o valor está em hm³**, não em m³. Mediana 0,1145 hm³; máximo 7.337 hm³ | Não | Contexto (magnitude) |
| `fase_de_vida` | `FASE_DE_VIDA` | categórico | Operação (958), Projeto (38), Construção (36), Desativada (32), Em descaracterização (8), Descaracterizada (3), Planejamento (3), 1º enchimento (3), Descomissionada (1) | Não | Filtro de elegibilidade a alerta |
| `categoria_risco` | `CATEGORIA_RISCO` | categórico | Médio (467), Baixo (313), **Não Classificado (258)**, Alto (106), Não se Aplica (104) | Sim | **B1** |
| `dano_potencial_associado` | `DANO_POTENCIAL` | categórico | Baixo (867), **Não Classificado (175)**, Médio (141), Alto (65) | Sim | **C1** (proxy de exposição) |
| `classe` | `BAR_DS_CLASSE` | categórico | A (8), B (68), C (18), D (90), E (3); 1.061 vazios | Não | Contexto |
| `nivel_de_perigo` | `NIVEL_PERIGO` | categórico | Normal (6), Atenção (4), Alerta (1), Emergência (1); 1.236 vazios | Não | **B2**, **R01** |
| `regulada_pelo_pnsb` | `REGULADA_PELO_PNSB` | categórico | Não (649), Não Classificada (342), Sim (257) | Sim | Contexto regulatório |
| `indicador_regulada` | — | numérico | Codificação de `regulada_pelo_pnsb`: 1=Sim, 2=Não, 3=Não Classificada | Sim | Contexto |
| `possui_plano_de_seguranca` | `POSSUI_PLANO_SEGURANCA` | booleano textual | Não (1.100), Sim (148) | Sim | **D1** |
| `possui_pae` | `POSSUI_PAE` | booleano textual | Sim (131), Não (22); **1.095 vazios** | Não | **D1** |
| `possui_revisao_periodica` | `POSSUI_REVISAO_PERIODICA` | booleano textual | Não (1.174), Sim (74) | Sim | **D1** |
| `barragem_autuada` | `BARRAGEM_AUTUADA` | booleano textual | Não (1.190), Sim (58) | Sim | **B4** (sinal indireto) |
| `data_ultima_inspecao` | `INS_DT_INSPECAO` | data | **1.154 vazios** | Não | **B3** |
| `tipo_ultima_inspecao` | `TP_INSPECAO` | categórico | Regular (94); 1.154 vazios | Não | **B3** |
| `completude_cadastro` | `COMPLETUDE` | categórico | ótima (824), boa (187), mínima (163), média (55), baixa (19) | Sim | Ponderação de confiabilidade |
| `data_cadastro` | — | data | | Não | Contexto |
| `numero_autorizacao` | — | texto | | Não | Contexto |
| `data_emissao_autorizacao` | — | data | | Não | Contexto |
| `possui_eclusa` | — | booleano textual | Não (525); 723 vazios | Não | Contexto |
| `regiao_hidrografica` | `ING_NM_REGIAO_HIDRO` | categórico | | Sim | Recorte de bacia (dimensão A) |
| `bacia_dnaee` | — | texto | | Não | Recorte de bacia |
| `curso_dagua` | `ING_NM_TRECHO` | texto | | Sim | Recorte de bacia |
| `codigo_trecho_curso_dagua` | — | texto | | Não | Recorte de bacia |
| `dominio_curso_dagua` | `DOMINIO_CURSO_DAGUA` | categórico | Federal (1.013), Estadual (88); 147 vazios | Não | Contexto regulatório |
| `comite_de_bacia_federal` | — | texto | | Não | Contexto |
| `comite_de_bacia_estadual` | `ING_NM_COMITEESTADUAL` | texto | 982 vazios | Não | Contexto |
| `unidade_de_gestao` | `UNIDADE_DE_GESTAO` | texto | 886 vazios | Não | Contexto |
| `origem_do_registro` | derivado | categórico | `atributo_uf` (1.248) quando o filtro de UF trouxe o registro; `envelope_sem_uf` quando só a consulta espacial trouxe | Sim | Auditoria de coleta |

### 9.2.1 Observação sobre "Não Classificado" e "Não se Aplica"

Os domínios de `categoria_risco` e `dano_potencial_associado` misturam três coisas
diferentes: uma classificação técnica (Alto/Médio/Baixo), a **ausência** de classificação (Não
Classificado) e a **inaplicabilidade** (Não se Aplica). O IDAP trata os três de forma distinta,
conforme `docs/03-idap.md` §3.10: valor classificado pontua pela banda; "Não Classificado"
recebe pontuação cautelar e entra na contagem de lacunas; "Não se Aplica" não pontua e não
conta como lacuna.

---

## 9.3 `sigbm_barragens_mt.csv` — barragens de mineração, SIGBM / ANM

Fonte: `https://dadosabertos.anm.gov.br/SIGBM/Barragens.csv` (cp1252, delimitador vírgula,
124 colunas na origem) e `metadados-sigbm.ods`. Republicado diariamente; latência de horas a
dias após a atualização pelo empreendedor. 909 barragens no país, **183 em Mato Grosso**.
O arquivo tratado tem 127 colunas: as da origem mais `latitude`, `longitude` e
`coordenada_plausivel`.

Convenção da fonte: `-` significa "não informado" ou "não aplicável no fluxo atual", e não
valor vazio. Ao medir lacuna, `-` precisa ser tratado como ausência.

### 9.3.1 Campos de identificação e classificação

| Campo | Tipo | Domínio / observação | Uso no IDAP |
| --- | --- | --- | --- |
| `ID` | texto | Chave da ANM | Contexto (chave) |
| `Nome` | texto | | Contexto |
| `Empreendedor`, `CPF_CNPJ` | texto | | Destinatário de alerta |
| `Nome da mina` | texto | | Contexto |
| `UF`, `Município` | texto | | Contexto territorial |
| `Latitude`, `Longitude` | texto | **Grau/minuto/segundo**, ex. `-10°07'16.390''` | Convertido |
| `latitude`, `longitude` | decimal | Derivados, EPSG:4326 | Contexto territorial |
| `coordenada_plausivel` | categórico | `sim` (183/183) — verificação contra o bbox de MT | Auditoria |
| `Posicionamento` | texto | | Contexto |
| `Categoria de Risco - CRI` | categórico | Baixa (86), Média (81), Alta (16) | **B1** |
| `Dano Potencial Associado - DPA` | categórico | Baixa (121), Média (44), Alta (18) | **C1** |
| `Inserido na PNSB` | booleano | Não (100), Sim (83) | Contexto regulatório |
| `Gestão Operacional` | texto | | Contexto |

### 9.3.2 Campos de emergência e conformidade documental

Estes são os campos de maior valor operacional e **não têm equivalente no SNISB**.

| Campo | Tipo | Domínio / observação | Uso no IDAP |
| --- | --- | --- | --- |
| `Nível de Emergência` | categórico | Sem emergência (165), **Emergência Nível 1 (16)**, Nível de Alerta (2) | **B2**, **R01** |
| `Status DCE RISR` | categórico | `-` (104), 1ª Campanha 2026 Atestado (73), 1ª Campanha 2026 Não Enviado (4), Extraordinária Atestado (2) | **B3** |
| `Status DCE RPSB` | categórico | `-` (120), Atestado (53), Não Enviado (10) | **B3** |
| `Status da DCO Atual` | categórico | `-` (168), Campanha 2026 Atestado (13), Campanha 2026 Não Enviado (2) | **B3** |
| `Data da Finalização da DCE` | data | | **B3** |
| `Necessita de PAEBM` | booleano | Não (100), Sim (83) | **D1** |
| `As cópias físicas do PAEBM foram entregues para as Prefeituras e Defesas Civis municipais e estaduais` | categórico | Sim (76), `-` (72), Não se aplica (32), **Não (3)** | **D1** |
| `PAE - Plano de Ação Emergencial (quando exigido pelo órgão fiscalizador)` | categórico | Possui PAE (81), Não possui — não exigido (49), Não se aplica (32), **Não possui — quando exigido (15)**, PAE em elaboração (6) | **D1** |
| `Situação Operacional` | categórico | Ativa (113), Em Construção (32), Inativa (30), Em Descaracterização (8) | Elegibilidade a alerta |
| `Fase Atual do projeto de Descaracterização` | categórico | Básico (3), Executivo (3), Sem informação de projeto (2); 175 vazios | Contexto |
| `Motivo de Envio`, `RT/Declaração`, `RT/Empreendimento` | texto | Responsável técnico da declaração | Auditoria |

### 9.3.3 Campos de engenharia e alteamento

| Campo | Tipo | Domínio / observação | Uso no IDAP |
| --- | --- | --- | --- |
| `Método construtivo da barragem` | categórico | Alteamento a jusante (89), Alteamento por linha de centro (33), Etapa única (25), `-` (16), Desconhecido (2); 18 vazios. **Nenhuma barragem a montante em MT nesta carga** | **B4** (contexto de risco construtivo) |
| `Tipo de alteamento` | categórico | Contínuo (111), Por Etapas (38), `-` (16); 18 vazios | Contexto |
| `Instrumentação` | categórico | Não instrumentada em desacordo com o projeto (52), Existe em desacordo com processo de adequação (42), Existe de acordo com o projeto (40), Existe em desacordo sem processo (17), `-` (14); 18 vazios | **B6** |
| `Drenagem Interna` | categórico | Conforme projeto ou não existe (82), Em desacordo ou inexistente (53), Corretiva posterior (16), Indefinido (14); 18 vazios | **B4** |
| `Tipo de Barragem de Mineração`, `Tipo de fundação`, `Fundação`, `Tipo de barragem quanto ao material de construção`, `Controle de Compactação`, `Inclinação Média dos taludes na seção principal`, `Tempo de Recorrência da Vazão de Projeto`, `A Barragem de Mineração possui Manta Impermeabilizante` | categórico / texto | | Contexto |
| `Altura máxima do projeto licenciado (m)`, `Altura máxima atual (m)` | decimal | Altura atual: 32 vazios (17,5%) | Contexto (magnitude) |
| `Comprimento da crista do projeto (m)`, `Comprimento atual da crista (m)`, `Cota da Crista Atual (m)` | decimal | | Contexto |
| `Descarga máxima do vertedouro (m³/seg)` | decimal | | **B4** |
| `Data de Início de Construção`, `Data de Início de Operação`, `Data de Finalização do Último Alteamento` | data | | Contexto |

### 9.3.4 Campos de anomalia estrutural (autodeclarados)

Estes campos vêm com pontuação embutida da própria ANM (0, 2, 3, 6, 10), o que facilita o uso
direto no indicador B4.

| Campo | Domínio observado | Uso no IDAP |
| --- | --- | --- |
| `Percolação` | 0 — totalmente controlada (126); Não se aplica (32); 3 — umidade ou surgência monitorada (16); **6 — sem medidas corretivas (8)**; **10 — carreamento de material, com potencial de comprometimento (1)** | **B4** |
| `Deformações e recalque` | 0 — inexistentes (73); 2 — trincas com medidas em implantação (53); Não se aplica (32); **6 — trincas sem medidas corretivas (23)**; **10 — com potencial de comprometimento (2)** | **B4** |
| `Deteriorização dos taludes / paramentos` | Mesma escala | **B4** |
| `Drenagem superficial` | Mesma escala | **B4** |
| `Confiabilidade das estruturas extravasora` | Mesma escala | **B4** |
| `Documentação de projeto`, `Estrutura organizacional e qualificação técnica...`, `Manuais de Procedimentos para Inspeções...`, `Relatórios de inspeção e monitoramento...` | Mesma escala | **D1** (gestão de segurança) |

Ressalva importante: são valores **autodeclarados pelo empreendedor** na Declaração de
Condição de Estabilidade. Servem como sinal, não como laudo independente.

### 9.3.5 Campos de reservatório, exposição e impacto

| Campo | Tipo | Domínio / observação | Uso no IDAP |
| --- | --- | --- | --- |
| `Volume de projeto licenciado do Reservatório (m³)` | decimal | | Contexto |
| `Volume atual do Reservatório (m³)` | decimal | 8 vazios (4,4%) | **B5** |
| `Capacidade Total do Reservatório (m³)` | decimal | 34 vazios (18,6%) | **B5** (razão volume/capacidade) |
| `Área do reservatório (m²)` | decimal | | Contexto |
| `Existência de população a jusante` | categórico | Pouco frequente (66), Inexistente (61), Frequente (15), **Existente (9)**; 32 vazios | **C1**, **C2** |
| `Número de pessoas possivelmente afetadas a jusante em caso de rompimento da barragem` | inteiro | 8 vazios (4,4%) | **C1** |
| `Impacto ambiental` | categórico | Pouco significativo (91), Insignificante (31), Significativo (14), **Muito significativo — Classe II A (11)**, **Muito significativo agravado — Classe I perigosos (4)**; 32 vazios | **C8** |
| `Impacto sócio-econômico` | categórico | Baixo (74), Inexistente (71), Médio (6); 32 vazios | **C5** |
| `Minério principal presente no reservatório` | categórico | 35 vazios | **C8** |
| `A Barragem armazena rejeitos/residuos que contenham Cianeto` | booleano | 35 vazios | **C8**; qualifica a ação da regra **R08** quando a mancha atingir captação |
| `Produtos químicos utilizados`, `Processo de beneficiamento`, `Teor (%) do minério principal inserido no rejeito`, `Outras substâncias minerais presentes no reservatório` | texto / decimal | | **C8** |
| `O projeto e/ou manual de operação da barragem prevê a existência de linha de praia no reservatório?`, `A Largura da linha de praia exigida em projeto e/ou manual de operação (m)`, `Menor largura da linha de praia atual (m)` | booleano / decimal | Linha de praia estreita é sinal de risco operacional em barragem de rejeito | **B4** |

### 9.3.6 Campos de descaracterização, monitoramento e back up dam

| Grupo | Campos | Uso |
| --- | --- | --- |
| Descaracterização | `Data de emissão do projeto Básico de Descaracterização`, `Data estimada de emissão do projeto executivo`, `Data de emissão do projeto executivo`, `Qual foi a solução adotada para a descaracterização?`, `Descrição da Estrutura Remanescente`, `Data de início das obras de estabilização ou descaracterização`, `Duração estimada em projeto das obras (em meses)`, `A barragem voltará a operar?`, `Data de conclusão das obras` | Contexto |
| Monitoramento | `Data de Início do Monitoramento Ativo`, `Duração estimada em projeto do monitoramento ativo (em meses)`, `Data de Início do Monitoramento Passivo`, `Data de conclusão estimada em projeto Monitoramento Passivo` | Contexto |
| Back up dam | `A barragem de mineração possui Back Up Dam` (Não 182, **Sim 1**), `Esta Back Up Dam está operando pós rompimento da barragem de mineração`, `Nome da Back Up Dam`, `UF (Back Up Dam)`, `Município (Back Up Dam)`, `Situação operacional da Back Up Dam`, `Desde (Back Up Dam)`, `Vida útil prevista (Anos)`, `Previsão de término de construção`, `A Back Up Dam está dentro da Área do Processo ANM ou da Área de Servidão`, `Processos associados`, `Posicionamento`, `Latitude`, `Longitude`, `Altura Máxima do projeto (m)`, `Comprimento da Crista do projeto (m)`, `Volume do projeto (m³)`, `Descarga Máxima do vertedouro (m³/seg)`, `Existe documento que ateste a segurança estrutural... com ART`, `Existe manual de operação`, `A Back up Dam passou por auditoria de terceira parte`, `A Back Up Dam garante a redução da área da mancha de inundação à jusante`, `Tipo quanto ao material de construção`, `Tipo de fundação`, `Vazão de projeto`, `Método construtivo`, `Tipo de auscultação` | Contexto; a existência de back up dam efetiva reduz a mancha esperada e afeta **C1** |
| Estruturas internas | `A Barragem de Mineração possui outra estrutura de mineração interna selante de reservatório`, `Quantidade Diques Internos`, `Quantidade Diques Selantes`, `Estrutura com o Objetivo de Contenção`, `A Barragem de Mineração está dentro da Área do Processo ANM ou da Área de Servidão`, `Barragem de mineração é alimentado por usina`, `Usinas` | Contexto |
| Certificação | `Possui certificações em vigor e/ou adota padrões da indústria`, `Quais certificações e/ou padrões` | **D1** |
| Gestão | `Unidade Gestora` | Contexto |

---

## 9.4 `ibge_municipios_mt.csv` — base municipal

Fonte: `https://servicodados.ibge.gov.br/api/v1/localidades/estados/51/municipios`.
Periodicidade: anual ou por alteração da divisão territorial. Latência: dias.

| Campo | Tipo | Observação | Obrigatório | Uso no IDAP |
| --- | --- | --- | --- | --- |
| `codigo_ibge` | inteiro (7 dígitos) | Chave territorial de todo o sistema | Sim | Contexto territorial |
| `municipio` | texto | Grafia oficial — referência para normalizar as variantes das outras fontes | Sim | Contexto |
| `microrregiao` | texto | | Sim | Agregação |
| `mesorregiao` | texto | | Sim | Agregação |
| `regiao_imediata` | texto | | Sim | Agregação |
| `regiao_intermediaria` | texto | | Sim | Agregação |

## 9.5 `ibge_malha_municipios_mt.geojson` — malha municipal

Fonte: `https://servicodados.ibge.gov.br/api/v3/malhas/estados/51?formato=application/vnd.geo+json&intrarregiao=municipio&qualidade=maxima`.

| Elemento | Tipo | Observação |
| --- | --- | --- |
| `features[].properties.codarea` | texto | Código IBGE do município — única propriedade retornada |
| `features[].geometry` | MultiPolygon (EPSG:4326) | **141 polígonos para 142 municípios** — ver §9.9.2 |

## 9.6 `powerbi_snisb_mt.csv` — atributos complementares

Fonte: relatório Power BI público do SNISB.
**Fonte frágil por natureza**: relatórios Power BI embutidos não expõem API estável; o coletor
pode quebrar sem aviso e sem mudança de contrato. O caminho correto é obter o dataset de
origem junto ao órgão.

| Campo | Tipo | Nulos | Uso no IDAP |
| --- | --- | --- | --- |
| `id_snisb` | texto | 0 (0,0%) | Chave de junção com o SNISB |
| `nome_powerbi` | texto | 0 (0,0%) | Conferência de nome |
| `municipio_powerbi` | texto | 0 (0,0%) | Conferência de município |
| `comprimento_coroamento_m` | decimal | 215 (17,2%) | Contexto (magnitude) |
| `altura_estimada_m` | decimal | 841 (67,4%) | Preenchimento de lacuna de altura |
| `capacidade_estimada_m3` | decimal | 838 (67,1%) | Preenchimento de lacuna de capacidade |
| `data_ultima_fiscalizacao` | data | 1.070 (85,7%) | **B3** |
| `data_ultima_autuacao` | data | 1.190 (95,4%) | **B4** (sinal indireto) |
| `data_inicio_fase_de_vida` | data | 166 (13,3%) | Contexto |
| `data_inspecao_seguranca_regular` | data | 1.170 (93,8%) | **B3** |
| `tipo_empreendedor` | categórico | 296 (23,7%) | Contexto / destinatário |
| `corpo_hidrico` | texto | 147 (11,8%) | Recorte de bacia |
| `data_atualizacao_registro` | data | 505 (40,5%) | Frescor do cadastro |
| `situacao_cadastro` | categórico | 1.098 (88,0%) | Auditoria |

## 9.7 `inventario_barragens_mt.csv` — inventário consolidado

Gerado por `scripts/05_consolidar_inventario.py`, unindo SNISB (base), Power BI (complemento
por `id_snisb`) e SIGBM (casamento por nome e coordenada). 1.248 registros, 71 colunas — as 45
do SNISB mais as derivadas abaixo.

| Campo derivado | Tipo | Regra de derivação | Uso no IDAP |
| --- | --- | --- | --- |
| `codigo_ibge` | inteiro | Casamento do nome do município com a base IBGE, após normalização de acento e caixa. **0 registros sem código** | Contexto territorial |
| `mesorregiao`, `regiao_intermediaria` | texto | Herdados do IBGE | Agregação |
| `altura_m` | decimal | Valor absoluto de `altura_max_terreno_m` | Contexto |
| `alerta_altura_negativa` | booleano textual | `sim` quando a altura na fonte é negativa. **1 registro** | Qualidade |
| `capacidade_hm3` | decimal | Cópia de `capacidade_reservatorio_m3` (que está em hm³) | Contexto |
| `capacidade_m3` | decimal | `capacidade_hm3 × 1.000.000` — conversão correta para m³ | Contexto |
| `alerta_coordenada` | booleano textual | `sim` quando a coordenada cai fora do bbox de MT | Qualidade |
| `classe_cnrh` | categórico | Matriz CRI × DPA: A (63), B (23), C (185), D (380), E (235); **362 sem classe** por falta de CRI ou DPA classificados | **B1** + **C1** |
| `prioridade_fiscalizacao` | inteiro 1–9 | Produto de pesos de CRI e DPA; nulo quando falta classificação | Priorização |
| `comprimento_coroamento_m`, `altura_estimada_m`, `capacidade_estimada_m3`, `data_ultima_fiscalizacao`, `data_ultima_autuacao`, `tipo_empreendedor`, `corpo_hidrico`, `data_atualizacao_registro` | vários | Herdados do Power BI | ver §9.6 |
| `sigbm_metodo_construtivo` | categórico | Herdado do SIGBM | **B4** |
| `sigbm_tipo_alteamento` | categórico | Herdado do SIGBM | Contexto |
| `sigbm_nivel_emergencia` | categórico | Herdado do SIGBM. **177 registros casados** (de 183 do SIGBM) | **B2**, **R01** |
| `sigbm_situacao_operacional` | categórico | Herdado do SIGBM | Elegibilidade |
| `sigbm_status_dce` | categórico | Herdado do SIGBM | **B3** |
| `sigbm_populacao_jusante` | categórico | Herdado do SIGBM | **C1**, **C2** |
| `sigbm_pessoas_afetadas` | inteiro | Herdado do SIGBM | **C1** |
| `sigbm_minerio` | texto | Herdado do SIGBM | **C8** |

---

## 9.8 Campos que o IDAP exige e que NENHUMA fonte coletada fornece

Este é o quadro mais importante deste documento para dimensionar o esforço restante.

| Dimensão | Indicadores sem fonte hoje | O que falta integrar |
| --- | --- | --- |
| **A — Pressão hidroclimática (30 pts)** | A1 a A7 — **todos** | INMET, Cemaden, ANA, GPM-IMERG; delimitação de bacia contribuinte por barragem |
| **B — Condição (30 pts)** | B5 (elevação anormal do reservatório) para barragens não-mineração; B6 (telemetria) para todas | Telemetria do empreendedor; sensores |
| **C — Impacto sanitário (25 pts)** | C1 a C7 em rigor — hoje só existe *proxy* categórico via DPA e via campo de população a jusante do SIGBM | Mancha de inundação (ZAS/ZSS), setor censitário, CNES, Sisagua, malha viária, tempo de chegada da onda |
| **D — Déficit de capacidade (15 pts)** | D2 (simulado), D3 (sirenes), D4 (abrigos), D5 (ambulâncias), D6 (capacidade hospitalar), D7 (rotas alternativas), D8 (contatos) | Defesa Civil, CNES, SAMU, cadastro de abrigos, cadastro de contatos institucionais |

Consequência prática: se o IDAP fosse calculado hoje com os dados existentes, a completude
ficaria em torno de **20% a 25%** — apenas parte da dimensão B, mais os *proxies* de C1. O
índice funcionaria, declararia a própria fragilidade e nomearia as lacunas, o que é o
comportamento correto. Mas ele não seria um instrumento de alerta ainda; seria um instrumento
de diagnóstico do que falta.

---

## 9.9 Qualidade dos dados

### 9.9.1 Lacunas medidas nos campos críticos do SNISB (n = 1.248)

| Campo crítico | Preenchidos | Nulos | % nulo | Consequência |
| --- | --- | --- | --- | --- |
| `nivel_de_perigo` | 12 | 1.236 | **99,0%** | O indicador B2 (10 pontos, o de maior peso individual do índice) fica sem fonte para 99% das barragens de água. Só o SIGBM cobre a lacuna, e apenas para as 183 de mineração |
| `data_ultima_inspecao` | 94 | 1.154 | **92,5%** | B3 inaplicável para 92,5% do inventário |
| `tipo_ultima_inspecao` | 94 | 1.154 | **92,5%** | Idem |
| `possui_pae` | 153 | 1.095 | **87,7%** | D1 (ausência de plano) fica cego para 87,7% |
| `classe` | 187 | 1.061 | **85,0%** | Suprido por `classe_cnrh` derivado de CRI × DPA |
| `comite_de_bacia_estadual` | 266 | 982 | 78,7% | Contexto apenas |
| `unidade_de_gestao` | 362 | 886 | 71,0% | Contexto apenas |
| `altura_max_fundacao_m` | 953 | 295 | 23,6% | Contexto de magnitude |
| `fase_de_vida` | 1.082 | 166 | 13,3% | 166 barragens sem saber se estão em operação |
| `dominio_curso_dagua` | 1.101 | 147 | 11,8% | Contexto regulatório |
| `altura_max_terreno_m` | 1.124 | 124 | 9,9% | Contexto de magnitude |
| `capacidade_reservatorio_m3` | 1.130 | 118 | 9,5% | Contexto de magnitude |
| `empreendedor` | 1.134 | 114 | 9,1% | 114 barragens sem responsável identificado — problema de alerta, não só de cadastro |
| `tipo_material` | 1.226 | 22 | 1,8% | Somado aos 208 "Sem Informação", 18,4% do inventário não tem material conhecido |
| `categoria_risco` | 1.248 | 0 | 0,0% | Mas **258 (20,7%) são "Não Classificado"** e 104 (8,3%) são "Não se Aplica" |
| `dano_potencial_associado` | 1.248 | 0 | 0,0% | Mas **175 (14,0%) são "Não Classificado"** |

Leitura crítica: campo preenchido não é campo informativo. `categoria_risco` tem 0% de nulo e
29% de valores que não informam risco algum. Medir só nulidade subestima a lacuna real.

### 9.9.2 Lacunas medidas no SIGBM (n = 183)

| Campo | Nulos | % | Observação |
| --- | --- | --- | --- |
| `Fase Atual do projeto de Descaracterização` | 175 | 95,6% | Esperado: só 8 barragens estão em descaracterização |
| `A Barragem armazena rejeitos/residuos que contenham Cianeto` | 35 | 19,1% | Lacuna relevante para C8 e para a regra R08 |
| `Minério principal presente no reservatório` | 35 | 19,1% | Idem |
| `Capacidade Total do Reservatório (m³)` | 34 | 18,6% | Impede calcular a razão volume/capacidade de B5 |
| `Existência de população a jusante` | 32 | 17,5% | Lacuna direta em C1 e C2 |
| `Impacto ambiental` | 32 | 17,5% | Lacuna em C8 |
| `Impacto sócio-econômico` | 32 | 17,5% | Lacuna em C5 |
| `Altura máxima atual (m)` | 32 | 17,5% | |
| `Instrumentação` | 18 | 9,8% | Lacuna em B6 |
| `Drenagem Interna` | 18 | 9,8% | Lacuna em B4 |
| `Método construtivo da barragem` | 18 | 9,8% | Mais 16 com `-` e 2 "Desconhecido": 19,7% sem método construtivo conhecido |
| `Tipo de alteamento` | 18 | 9,8% | Mais 16 com `-` |
| `Volume atual do Reservatório (m³)` | 8 | 4,4% | |
| `Número de pessoas possivelmente afetadas a jusante` | 8 | 4,4% | |

Observação metodológica: os campos de status (`Status DCE RISR`, `Status DCE RPSB`,
`Status da DCO Atual`) têm 0% de nulo, mas 57%, 66% e 92% dos valores são `-`. A lacuna real é
essa, não a nulidade.

Achado com valor operacional imediato: **16 barragens de mineração em MT estão em Emergência
Nível 1 e 2 em Nível de Alerta** nesta carga. Pela regra R01 de `docs/03-idap.md`, Nível 1 não
força alerta vermelho (que é reservado a níveis 2 e 3), mas eleva substancialmente o indicador
B2 e merece verificação caso a caso.

### 9.9.3 Divergência 142 municípios × 141 polígonos

| Aspecto | Situação |
| --- | --- |
| Fato medido | A API de localidades retorna **142** municípios para MT; a API de malhas com `intrarregiao=municipio` e `qualidade=maxima` retorna **141** polígonos |
| Consequência | Um município fica sem geometria. Toda análise espacial que dependa de recorte municipal — exposição, agregação por município, mapa coroplético — tem um vazio silencioso |
| Gravidade | Média em rotina; **alta durante evento**, se o município faltante for justamente um dos atingidos |
| Hipóteses | (a) alteração recente na divisão territorial não refletida na malha; (b) omissão na resposta da API de malhas; (c) falha de paginação ou de parsing na coleta |
| Encaminhamento | Identificar qual código IBGE está ausente comparando as duas listas; se for omissão da fonte, obter a geometria pelo FTP do IBGE ou pela malha do ano anterior; registrar como pendência aberta até a resolução |

Esta divergência **não deve ser silenciada** por junção que descarte o município sem
geometria. A junção correta preserva o município e marca a geometria como ausente.

### 9.9.4 Outros achados de qualidade

| Achado | Medida | Encaminhamento |
| --- | --- | --- |
| Altura negativa | **1 registro** com `altura_max_terreno_m = −11,0 m` | Erro de digitação na fonte. O consolidador preserva o valor original e sinaliza em `alerta_altura_negativa`, sem mascarar |
| Variantes de grafia de município | **150 grafias distintas** no SNISB para 142 municípios reais | Normalização por acento e caixa já implementada; 0 registros ficaram sem `codigo_ibge` |
| Unidade enganosa | `capacidade_reservatorio_m3` está em **hm³**, apesar do nome | Corrigido no consolidado (`capacidade_hm3` e `capacidade_m3`). O nome herdado da fonte é uma armadilha para quem usar o CSV do SNISB diretamente |
| Casamento SNISB × SIGBM | **177 de 183** barragens de mineração casadas | 6 sem correspondência. Não há chave comum entre as bases; o casamento depende de nome e coordenada |
| Barragens sem empreendedor | 114 (9,1%) | Impede acionar o responsável pela estrutura em situação de alerta |
| Barragens sem `fase_de_vida` | 166 (13,3%) | Impede saber se a estrutura deve ou não entrar no monitoramento ativo |
| Certificado TLS de `snirh.gov.br` | Autoassinado na cadeia | Já tratado no coletor; monitorar, porque a solução é frágil por natureza |
| Fonte Power BI | Sem API estável | Coletor pode quebrar sem aviso; obter o dataset de origem junto ao órgão |
| Ausência de histórico | Nenhuma das fontes coletadas guarda série temporal de classificação | Sem histórico não se detecta agravamento. A tabela `classificacao` com `data_referencia` (§6.3.1) resolve, desde que a carga seja versionada a partir de agora |

### 9.9.5 Contexto regulatório com efeito sobre a qualidade

A SEMA-MT saltou de **419 para 661 barragens cadastradas** no SNISB em 2025. Isso significa
que o inventário está em expansão rápida, e que a proporção de registros com cadastro incompleto
tende a **crescer** antes de melhorar: barragem recém-cadastrada entra com o mínimo de campos.

Implicação para o IDAP: a completude do índice não é apenas uma característica técnica; ela é
um indicador de gestão. A série da completude média por órgão fiscalizador e por município é,
por si só, um produto útil da plataforma.

---

## 9.10 Dependências adicionais sugeridas

O `requirements.txt` do projeto (`httpx==0.28.1`, `openpyxl==3.1.5`) **não foi alterado**,
conforme a divisão de responsabilidades do repositório. As dependências abaixo ficam registradas
aqui como sugestão, para decisão de quem mantém o arquivo.

### 9.10.1 O pacote `scripts/idap/` não precisa de nenhuma dependência nova

A implementação de referência do IDAP usa **apenas a biblioteca padrão** do Python 3.12
(`dataclasses`, `enum`, `datetime`, `typing`, `unittest`). Isso é deliberado: o motor de cálculo
do alerta é a parte do sistema que menos pode falhar por problema de ambiente. Nada nele exige
`numpy`, mesmo estando disponível.

### 9.10.2 Já instalados no ambiente, ainda não declarados no `requirements.txt`

| Pacote | Situação | Usado para |
| --- | --- | --- |
| `numpy` | Instalado, não declarado | Estatística e álgebra nos motores analíticos |
| `shapely` | Instalado, não declarado | Geometria em memória (interseção, área, buffer) |

Sugestão: declarar o que já está em uso, para que o ambiente seja reproduzível.

### 9.10.3 Sugeridas por fase do roadmap

| Fase | Pacote sugerido | Para quê | Alternativa com biblioteca padrão |
| --- | --- | --- | --- |
| 1 | `psycopg[binary]` | Acesso a PostgreSQL / PostGIS | Não há |
| 1 | `pyproj` | Reprojeção de coordenadas | Não há; conversão manual só para casos simples |
| 1 | `python-dateutil` | Parsing tolerante de datas heterogêneas | `datetime.strptime` com múltiplos formatos |
| 1 | `tenacity` | Retry estruturado nos coletores | Já resolvido manualmente em `scripts/comum.py` |
| 2 | `fiona` ou `pyogrio` | Leitura de shapefile e filegdb (formatos que o SNISB exporta) | Não há |
| 2 | `rasterio` | Leitura de grade de chuva (GPM-IMERG) e raster em geral | Não há |
| 2 | `netCDF4` ou `h5py` | Formato nativo dos produtos do IMERG | Não há |
| 3 | `statsmodels` | Regressão de Poisson e binomial negativa para detecção de excesso | Implementação própria: viável, mas propensa a erro |
| 3 | `scipy` | Distribuições e testes estatísticos | Parcialmente supríveis com `statistics` |
| 4 | `networkx` | Cálculo de rotas alternativas sobre a malha viária | Dijkstra/`heapq` em `st_app/vias_isolamento.py` (+ fallback offline `st_app/malha_offline.py`) |
| 4 | `pydantic` | Validação de esquema da ficha rápida | `dataclasses` com validação manual |

Observação sobre `pandas` e `geopandas`: **não estão instalados e não são necessários**. Todo o
processamento tabular deste repositório é feito com `csv` e `json`, e funciona. Introduzir
`pandas` traria conveniência e, com ela, uma dependência pesada em um sistema que precisa
rodar de forma previsível. Se vier a ser adotado, que seja por necessidade demonstrada, não
por hábito.

### 9.10.4 Infraestrutura (não são pacotes Python)

| Componente | Versão sugerida | Para quê |
| --- | --- | --- |
| PostgreSQL | 16 | Banco central |
| PostGIS | 3.4 | Operações geoespaciais |
| TimescaleDB | Compatível com o PostgreSQL escolhido | Séries temporais de chuva, nível, vazão e sensores |
| GDAL/OGR | 3.8 | Conversão de formatos geoespaciais |
| GeoServer ou QGIS Server | — | Publicação de serviços para o WebGIS |

Todas as versões acima são **propostas a validar** com a área de TI da SES-MT.
