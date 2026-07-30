# Análise de aderência ao Produto 04 oficial

Compara a **Especificação Funcional e Técnica VIGIBARRAGENS–MT Saúde v1.0** (documento oficial,
29/07/2026) com o que existe de concreto neste repositório e com a concepção descrita pelo usuário
no chat.

Regra adotada: **onde houver conflito, o documento oficial prevalece.** Cada ponto cita a seção ou
tabela de origem.

## Insumos analisados

| Arquivo | Origem | Pertinência |
| --- | --- | --- |
| `especificacao_funcional_tecnica_v1_0.md` | `Produto 04/VIGIBARRAGENS_MT_Especificacao_Funcional_Tecnica_v1_0.docx` | Documento-base. 14 seções, 2 apêndices, 34 tabelas |
| `Apresentação Produto 4.pdf` (não transcrito) | `Produto 04/` | Briefing do Ministério da Saúde: escopo contratual, formatação e **prazo de entrega** |
| `matriz_responsabilidades_revisada.md` | `produto 01/Produto_04_Matriz_Responsabilidades_Revisada.docx` | Produto 04 de **ciclo anterior (seca/estiagem, 2025)**. Precedente metodológico, não insumo de barragens |
| 3 imagens `WhatsApp Image 2026-07-21/24` | `Produto 04/` | Referências visuais de prancha cartográfica (Palmas/TO). Não copiadas para cá; permanecem na pasta de origem |

Nada foi encontrado sobre barragens em `produto 02` e `produto 03` — ambos tratam de calor extremo.

---

## a) O que o documento exige e já está atendido

| Exigência oficial | Onde está atendido | Observação |
| --- | --- | --- |
| **BARR-01 SNISB** — cadastro nacional, fiscalizador, CRI/DPA, "chave principal para cadastro" (Tabela 8) | `scripts/01_snisb_mt.py`, 1.248 barragens | Atende inclusive a regra "preservar data e norma da classificação": o extrator mantém os valores originais sem reclassificar |
| **BARR-02 SIGBM**, classe A prioritária, "utilizar endereço de dados abertos vigente" (Tabela 8) | `scripts/02_sigbm_anm.py`, 183 barragens | Usa exatamente `dadosabertos.anm.gov.br/SIGBM`, o endereço vigente. A migração do endpoint antigo já foi resolvida |
| **EST-01 / EST-02** — CRI e DPA oficiais vigentes como "valor original" (Tabela 13) | Inventário consolidado | Nenhum recálculo silencioso, conforme R-IND-04 |
| **CAD-02** cobertura de classificação | `relatorios/diagnostico_barragens_mt.md` | Mede 362 barragens sem CRI e DPA simultâneos. É literalmente o indicador CAD-02 |
| **CAD-05** completude crítica e **CAD-06** conflito entre fontes | Verificações do `05_consolidar_inventario.py` | Altura negativa, variantes de caixa em nomes de município e capacidade em hm³ são achados de CAD-05/CAD-06 |
| **POP-01 IBGE** | `scripts/03_ibge_mt.py` | Parcial: malha **municipal**, não setor censitário. O documento exige setor censitário para EXP-01 |
| Backlog técnico item 1, "cadastro mestre" (Tabela 30) | Inventário consolidado | Parcial — falta `xref_barragem_fonte`, ver item (b) |
| Princípio "sem probabilidade de rompimento genérica" (Sumário executivo) | Concepção do chat e `docs/01` | Convergência integral entre documento, chat e código |

Em resumo: dos 12 épicos do backlog oficial (Tabela 30), **um está parcialmente entregue** (o de
número 4, conector de barragens) e **um está iniciado** (o de número 2, catálogo e qualidade das
fontes, na forma de relatório e não de tabela).

---

## b) O que o documento exige e ainda não existe

Ordenado pela prioridade do próprio documento.

### Bloqueadores estruturais

| Exigência | Seção | Situação |
| --- | --- | --- |
| PostgreSQL 16+ / PostGIS 3+ como repositório primário | §3.2 Tabela 7 | **Não existe banco algum.** O projeto persiste em CSV e GeoJSON |
| Camadas Bronze / Silver / Gold | §3.1 | Existem `dados/brutos` e `dados/tratados` — aproximadamente Bronze e Silver. **Não há camada Gold** |
| Migrations, constraints, índices GiST, particionamento temporal | §5.2, Tabela 34 `database_core` prioridade 1 | Inexistente |
| API FastAPI com 12 endpoints | §10.1 Tabela 25 | Inexistente |
| Estrutura de diretórios `C:\SES_MT_INTELIGENCIA_SAUDE\05_vigibarragens_mt\` | §3.3 | O projeto vive em `Projeto VSR\barragens-mt` com `scripts/` plano |
| 20 tabelas do modelo lógico | §5.1 Tabela 11 | Nenhuma. Falta em especial `xref_barragem_fonte`, que é o mecanismo oficial para reconciliar SNISB × SIGBM × SEMA |
| Contrato padrão do registro de indicador (13 campos) | §5.3 Tabela 12 | Inexistente. Nenhum indicador é gravado com `source_ids`, `method_version`, `confidence_class` |

### Dados ausentes que travam blocos inteiros de indicadores

| Fonte ausente | Código | O que fica impossível |
| --- | --- | --- |
| Manchas oficiais PAE/PAEBM, ZAS/ZSS | GEO-01, classe C/D | **Toda a família EXP-01 a EXP-10** e a dimensão I do índice. Sem mancha não há população exposta, nem unidade de saúde ameaçada, nem captação ameaçada |
| ANA HidroWeb / telemetria | HID-01, classe A | HID-08 a HID-11 |
| INMET, Cemaden | MET-01, MET-02 | HID-01 a HID-04 |
| GPM-IMERG, Sentinel | SAT-01 a SAT-03 | HID-06, HID-12, impacto observado |
| IBGE setor censitário | POP-01 | EXP-01, EXP-02, EXP-04, EXP-05 |
| CNES | SAU-01 | EXP-06, SAU-01 a SAU-03 |
| Sisagua, SIM, SINAN, SIH, SISREG, GAL | SAU-02 a SAU-08, AMB-01 | Módulo pós-desastre inteiro |

### Componentes funcionais ausentes

Motor de alertas com deduplicação e confirmação (M05); cadastro de contatos e pontos focais;
módulo de qualidade e auditoria M09 com `fact_pipeline_run` e `fact_data_quality`; Sala de Situação
M07; assistente de IA M08 com o contrato JSON de oito campos (§9.3 Tabela 24); as nove categorias
de teste do §12.1; e todos os controles de segurança e LGPD do §12.

O **Apêndice A** lista 18 itens de prontidão para iniciar o desenvolvimento. **Os 18 estão marcados
"Pendente" no próprio documento oficial** — incluindo comitê gestor nomeado, lista de barragens
piloto aprovada, acesso SEMA-MT homologado e manchas recebidas.

---

## c) O que construímos que vai além do documento

| Entrega | Comentário |
| --- | --- |
| Painel `painel/index.html` com 1.248 barragens, sete filtros e exportação | Útil, mas ver divergência **D14**: o documento manda construir painel **depois** da API |
| Mapas em prancha cartográfica (`figuras/`) | Não são exigidos por nenhuma seção; atendem à referência visual de Palmas/TO |
| `relatorios/diagnostico_barragens_mt.md` | Vai além do exigido. Achados que o documento não pede e que têm valor operacional imediato: 18 barragens de mineração com emergência declarada (16 Nível 1, 2 Alerta) concentradas em Nossa Senhora do Livramento e Poconé; 63 barragens classe A das quais 12 sem Plano de Segurança e 15 sem PAE; nenhuma barragem em MT com alteamento a montante |
| Três armadilhas de dados detectadas e tratadas | Capacidade publicada em hm³ com nome de campo em m³; 150 variantes de caixa para 141 municípios; altura negativa. São insumo direto de CAD-05 e CAD-06 |
| `scripts/idap/` executável e testado | Antecipa o `indicator_engine` (Tabela 34, prioridade 1), embora com nome e mecânica divergentes — ver **D1** |
| Verificação cruzada SNISB ArcGIS × modelo semântico | As duas fontes retornam as mesmas 1.248 barragens. Metodologicamente valioso, mas ver **D4** |

---

## d) Divergências e contradições

### D1 — O índice tem outro nome e outra mecânica de cálculo

| | Documento oficial (§7.1, Tabela 15) | Chat e `docs/03-idap.md` |
| --- | --- | --- |
| Nome | **IPS-B — Índice de Prioridade Sanitária Integrada** | IDAP-Barragens — Índice Dinâmico de Alerta e Prontidão |
| Fórmula | `IPS-B = 0,30×H + 0,30×E + 0,25×I + 0,15×D`, cada componente de **0 a 100** | Soma de pontos por indicador (0–5, 0–10…) com tetos de 30/30/25/15 |
| Dimensão B | "Condição oficial/estrutural" | "Condição da barragem" |
| Dimensão D | "Déficit de prontidão" | "Déficit de capacidade de resposta" |

Pesos (30/30/25/15) e faixas de cor coincidem. **A mecânica não é equivalente.** No modelo oficial
cada dimensão é normalizada de 0 a 100 e depois ponderada, o que permite reescalar uma dimensão
parcialmente observada. No modelo do `docs/`, um indicador sem dado simplesmente não pontua, o que
**deprime artificialmente o índice** e faz uma barragem mal cadastrada parecer mais segura que uma
bem cadastrada. O documento oficial resolve isso pela via da suficiência (D2); o nosso, não.

### D2 — Falta a pré-condição de suficiência, que é regra dura no oficial

§7.2, Tabela 16: se **menos de 70%** dos componentes P1 aplicáveis estiverem válidos, o sistema
**não emite escore numérico**; devolve `PRIORIDADE INDETERMINADA – DADOS INSUFICIENTES` com a lista
de lacunas. Reforçado por R-IND-01 (§6.1) com status `INSUFFICIENT_DATA`, pelo indicador PRE-07
"Prontidão de dados" e pelo parâmetro `minimum_score_for_integrated_index: 0.70` (§10.4).

Não existe na concepção do chat nem em `scripts/idap/calculo.py`. É a divergência de maior impacto
sobre o código já escrito.

### D3 — A ficha rápida contraria o princípio central do documento

Esta é a contradição mais séria.

O documento estabelece **demanda assistencial zero** como princípio central, em quatro lugares:

- Tabela 3 (Sumário executivo): "nenhum indicador crítico do módulo operacional poderá depender de coleta extraordinária realizada pela assistência durante a fase aguda do desastre";
- §1.3 Fora de escopo: "Criar prontuário, sistema assistencial ou **nova ficha obrigatória durante a fase aguda**";
- §8, título da seção: "Vigilância pós-desastre **sem nova demanda assistencial**";
- §8.4, Tabela 23: "Contagem de sintomas em abrigo depende de nova ficha → **Não ativar** até existir sistema rotineiro ou integração autorizada".

A concepção do chat propõe uma **ficha rápida de saúde pós-desastre com cerca de 40 campos**,
preenchida por município, unidade ou equipe de campo, e ela está documentada em
`docs/05-vigipos-barragens.md` §5.4 e listada como **entregável 1.7 da Fase 1** em `docs/08-roadmap.md`.

O documento não proíbe cadastro em normalidade — proíbe coleta pela assistência **na fase aguda**.
Há um caminho de conciliação, mas exige reposicionar a ficha (ver ajustes).

### D4 — O Power BI é classificado como fonte proibida

| Documento oficial | O que fizemos |
| --- | --- |
| PBI-01, disponibilidade **classe E — "não usar como fonte"** (Tabela 8) | `scripts/04_powerbi_snisb.py` consulta o modelo semântico e alimenta o inventário consolidado com quatro campos |
| §1.3 Fora de escopo: "**Raspar o painel público do Power BI como fonte primária**" | O coletor é executado no pipeline padrão (`executar.py`) |
| §4: "deve ser tratado apenas como referência visual até que suas bases subjacentes sejam identificadas" | — |
| §14, decisão pendente: "Acesso às bases subjacentes do painel Power BI — Proprietário do painel/TI" | — |

O documento não diz apenas "é frágil"; diz **classe E, não usar em cálculos críticos**. `docs/02`
§2.2.2 já registra a fragilidade técnica, mas trata a fonte como complementar aceitável, o que é
mais permissivo que a norma oficial.

### D5 — "VIGIPÓS-BARRAGENS" não existe no documento oficial

O módulo se chama **M06 – Vigilância pós-desastre** (§3, Tabela 5). O nome VIGIPÓS-BARRAGENS é
criação do chat e não aparece em nenhuma seção.

### D6 — São seis fases, não quatro

| Documento oficial (§13, Tabela 29) | `docs/08-roadmap.md` |
| --- | --- |
| **0 – Descoberta e governança** | *(ausente)* |
| 1 – Piloto Cuiabá | Fase 1 — Piloto Cuiabá |
| 2 – MVP estadual | Fase 2 — Expansão estadual |
| 3 – Vigilância pós-desastre | Fase 3 — Vigilância pós-desastre |
| **4 – Satélite e simulação** | *(fundida na Fase 4)* |
| **5 – IA supervisionada** | *(fundida na Fase 4)* |

A ausência da Fase 0 é relevante: suas entregas são catálogo de dados, matriz de acesso, backlog e
termos de governança — precisamente os pré-requisitos que hoje bloqueiam quase tudo.

### D7 — São nove telas, não oito

Oficial (§11, Tabela 27): Comando estadual; Barragem 360°; Monitoramento ambiental; **Mapa de
impacto**; Alertas; Pós-desastre; **Qualidade**; Sala de Situação; **Painel público**.

`docs/07-telas.md` tem oito, faltando **Qualidade**, **Sala de Situação** e **Painel público**, e
criando duas que não são telas oficiais: "Assistência e logística" e "Recuperação". A tela de
Qualidade não é decorativa — é a materialização do módulo M09 e da classe de confiança A–E.

### D8 — O IPAPD não existe no documento e boa parte de seus insumos é proibida

O oficial tem **POS-10, Índice de recuperação sanitária** (P3, "composição configurável"), que
corresponde ao IRS do chat. **Não há IPAPD.** Além disso, seus componentes esbarram na regra de
demanda zero: ocupação operacional é SAU-07 com a ressalva "não solicitar planilha manual", e
estoque por unidade está em Tabela 23 como "não incluir no painel operacional".

### D9 — Existe um catálogo oficial de indicadores codificados que não estamos usando

§6, Tabela 13, define cerca de **60 indicadores** com código estável, fórmula, fonte,
granularidade, latência, prioridade **P1/P2/P3**, ação e limitações, agrupados em CAD, HID, EST,
EXP, SAU, PRE, ALT e POS. Somam-se as sete regras obrigatórias de publicação R-IND-01 a R-IND-07
(§6.1, Tabela 14). A documentação em `docs/` não adota essa codificação, o que impede rastrear cada
indicador nosso até a exigência oficial correspondente.

### D10 — Os prazos de confirmação de alerta já estão fixados no documento

§10.4 fixa, em YAML: laranja **60 min**, vermelho **30 min**, roxo **15 min**; janela de
deduplicação **120 min**; suficiência mínima **0,70**; supressão de contagens abaixo de **5**;
fuso `America/Cuiaba`. Eu havia instruído o agente de documentação a propor esses prazos; os
valores oficiais devem substituir qualquer proposta.

### D11 — O ciclo de vida do alerta tem nove estados nomeados

§7.5: `DETECTADO → GERADO → AGUARDANDO VALIDAÇÃO → VALIDADO → PUBLICADO → ENTREGUE → CONFIRMADO →
EM ACOMPANHAMENTO → ENCERRADO/CANCELADO`. Com a distinção de que alertas informativos de baixo
risco podem ser automáticos, mas **alertas de ação e críticos exigem validação do CIEVS**. A
confirmação do gestor tem quatro respostas possíveis: recebido, em avaliação, plano ativado,
necessita apoio.

### D12 — As regras determinísticas divergem em pontos específicos

| Diferença | Documento oficial (§7.4, Tabela 18) |
| --- | --- |
| Regra do chat "perda súbita de nível associada a anomalia" | **Não existe** no documento |
| Falha de telemetria | Gera "alerta técnico de **perda de observabilidade**, **não** alerta de rompimento" — o documento é explícito contra a leitura alarmista |
| Emergência oficial 2 ou 3 | "Aplicar severidade mínima definida… **sem reduzir o nível oficial**" |
| Ordem oficial de evacuação | Regra ausente no chat: "Exibir ordem e fonte; **suspender qualquer texto ambíguo da IA**" |
| Fonte crítica desatualizada | Regra ausente no chat: "Marcar painel como **degradado** e usar fonte de contingência" |

### D13 — A pilha tecnológica e a estrutura de diretórios são normativas

§3.2 e §3.3 especificam PostgreSQL 16+/PostGIS 3+, TimescaleDB ou particionamento, FastAPI +
OpenAPI, Polars/Pandas/GeoPandas/Rasterio/Xarray/SQLAlchemy/Pydantic, **PowerShell + Agendador de
Tarefas do Windows** para orquestração do MVP (justificado como "compatível com o ambiente
operacional atual da SES-MT"), WebGIS com MapLibre ou Leaflet, e a árvore de diretórios completa.
Nosso projeto diverge em todos esses pontos.

### D14 — A ordem de construção foi invertida

§14.1: "O desenvolvimento deve começar pelo **inventário automatizado das fontes e pelo cadastro
mestre**… O **painel deve ser construído somente após** as tabelas Gold e a API apresentarem
resultados validados", com a justificativa de que a construção antecipada do painel "poderá
produzir indicadores não sustentáveis ou dependentes de alimentação manual".

Construímos o painel primeiro. Ele é útil como prova de conceito e como instrumento de diagnóstico
cadastral, mas não é o caminho que o documento define, e o risco apontado é real: os indicadores do
painel hoje são estáticos.

### D15 — Há três modelos de cinco estágios em circulação

| Origem | Modelo |
| --- | --- |
| Chat | Normalidade, Pré-impacto, Impacto, Pós-impacto agudo, Recuperação |
| VIGIBARRAGENS oficial (§7.3) | Verde normalidade, Amarelo **atenção**, Laranja **mobilização**, Vermelho emergência potencial, Roxo resposta crítica |
| Produto 04 de seca/estiagem (2025) | Verde Normalidade, Amarelo **Mobilização**, Laranja **Alerta**, Vermelho Emergência, Roxo Crise |

Note a inversão: "mobilização" é **amarelo** no produto de seca e **laranja** no de barragens. Os
"cinco momentos operacionais" do chat **não constam do documento oficial** — o que o documento tem
é a hierarquia temporal de fontes do §8.1 (minutos a horas / horas a dias / dias a semanas).

### D16 — O produto contratual é um relatório de 6 a 10 páginas, com prazo em 3 de agosto

A apresentação do Ministério da Saúde define o Produto 04 como **relatório técnico** com a análise
da capacidade de preparação e resposta do setor saúde frente a rompimento de barragens, e impõe:

- **6 a 10 páginas** A4, incluindo capa e referências (apêndices e anexos não contam);
- margens 3 cm superior/esquerda e 2 cm inferior/direita; Arial ou Times New Roman 12; espaçamento 1,5; justificado; ABNT;
- assinatura GOV.BR ou de próprio punho em caneta azul;
- envio para `vigidesastres@saude.gov.br` em **03/08/2026**.

O conteúdo esperado inclui distribuição das barragens por região, classificação por DPA e CRI,
barragens de mineração, de abastecimento e de rejeitos, histórico de rompimentos, municípios com
barragens de alto risco, áreas suscetíveis, **comunidades indígenas, quilombolas, assentamentos
rurais e populações ribeirinhas**, e avaliação de planos de contingência, monitoramento e sistemas
de alerta.

**A especificação funcional de 34 tabelas não é o produto contratual** — é documento-base para
desenvolvimento futuro. E boa parte do que o relatório contratual pede já pode ser respondida com
os dados que temos: distribuição por região, CRI/DPA, mineração, alto risco por município. O que
falta é o recorte de populações vulneráveis (indígenas, quilombolas, assentamentos, ribeirinhas),
que não foi coletado.

### D17 — Faltam a reconciliação de identificadores e a vigência temporal

§5.1 exige `xref_barragem_fonte` (barragem_id, source_id, source_record_id, confiança, data de
validação) e `fact_classificacao_barragem` com vigência. §5.2: "Nunca sobrescrever histórico;
aplicar vigência temporal e versionamento das classificações". Nosso inventário consolidado faz o
cruzamento de forma implícita e sobrescreve a cada execução — é um retrato, não uma série.

### D18 — Convenções de projeção, fuso e integridade

§5.2 exige **SIRGAS 2000 (EPSG:4674)** para intercâmbio, armazenamento em UTC com exibição em
`America/Cuiaba`, e preservação dos brutos com **hash SHA-256** e data de obtenção. Nossos GeoJSON
saem em EPSG:4326 sem CRS declarado e sem hash.

---

## e) Terminologia e numeração oficiais a adotar

| Usar | Em vez de |
| --- | --- |
| **IPS-B — Índice de Prioridade Sanitária Integrada** | IDAP-Barragens |
| **M06 – Vigilância pós-desastre** | VIGIPÓS-BARRAGENS |
| **Condição oficial/estrutural** (dimensão E) | Condição da barragem |
| **Déficit de prontidão** (dimensão D) | Déficit de capacidade de resposta |
| **Impacto sanitário potencial** (dimensão I) | *(igual)* |
| **Pressão hidroclimática** (dimensão H) | *(igual)* |
| **POS-10 – Índice de recuperação sanitária** | IRS |
| **Módulos M01 a M09** | *(sem equivalente na documentação atual)* |
| **Códigos de indicador** CAD, HID, EST, EXP, SAU, PRE, ALT, POS com prioridade P1/P2/P3 | Indicadores sem código |
| **Códigos de fonte** BARR-01…04, HID-01, MET-01/02, SAT-01…03, POP-01, GEO-01, SAU-01…08, AMB-01, INF-01, DES-01, PBI-01 | Fontes sem código |
| **Classes de disponibilidade A, B, C, D, E** | Sem classificação |
| **Classe de confiança A–E** no registro do indicador | Sem classe |
| **Fases 0 a 5** | Fases 1 a 4 |
| **PRIORIDADE INDETERMINADA – DADOS INSUFICIENTES** e status `INSUFFICIENT_DATA` | Sem estado equivalente |
| **Bronze / Silver / Gold** | brutos / tratados |

---

## Ajustes recomendados em `docs/`

Lista acionável para o agente responsável pela pasta. Nenhum arquivo foi editado por esta análise.

### `docs/03-idap.md` — reescrita substancial

1. Renomear o índice para **IPS-B – Índice de Prioridade Sanitária Integrada** em todo o documento; manter "IDAP" apenas em nota de equivalência histórica, se desejado.
2. Substituir a mecânica de soma de pontos pela fórmula oficial `IPS-B = 0,30×H + 0,30×E + 0,25×I + 0,15×D`, com **cada componente normalizado de 0 a 100** (§7.1).
3. Acrescentar seção sobre a **pré-condição de suficiência de 70%** e o resultado `PRIORIDADE INDETERMINADA – DADOS INSUFICIENTES` (§7.2, Tabela 16), amarrando ao parâmetro `minimum_score_for_integrated_index: 0.70` (§10.4).
4. Renomear as dimensões B e D conforme a seção (e) desta análise.
5. Revisar a tabela de regras determinísticas conforme **D12**: remover "perda súbita de nível", acrescentar "ordem oficial de evacuação" e "fonte crítica desatualizada", e reescrever a regra de telemetria como perda de observabilidade.
6. Mapear cada indicador das quatro dimensões para o **código oficial** correspondente da Tabela 13 (HID-01…12, EST-01…06, EXP-01…10, PRE-01…07).
7. Incorporar as sete regras **R-IND-01 a R-IND-07** (§6.1) e o contrato de registro de indicador de 13 campos (§5.3).

### `scripts/idap/` — alinhamento de código

8. `calculo.py`: implementar a normalização 0–100 por dimensão e a média ponderada, no lugar da soma de pontos.
9. `calculo.py`: implementar o corte de suficiência de 70% devolvendo `INSUFFICIENT_DATA` em vez de um número.
10. `modelo.py`/`pesos.py`: renomear a estrutura para IPS-B e adotar os códigos oficiais de indicador como chaves.
11. `regras.py`: refletir a Tabela 18 revisada.
12. `relatorio.py`: adotar os oito campos obrigatórios do alerta (§7.6, Tabela 20), incluindo `Auditoria` com versão da regra e hash do conteúdo.
13. `testes.py`: acrescentar casos para o corte de suficiência e para a precedência das regras determinísticas sobre o escore.

### `docs/04-alertas.md`

14. Substituir quaisquer prazos propostos pelos oficiais do §10.4: laranja 60 min, vermelho 30 min, roxo 15 min, deduplicação 120 min.
15. Adotar os **nove estados** do ciclo de alerta (§7.5) e as quatro respostas de confirmação do gestor.
16. Registrar que alertas de ação e críticos **exigem validação do CIEVS/Vigidesastres**, e que apenas informativos de baixo risco podem ser automáticos.
17. Adotar a estrutura de oito campos do alerta (Tabela 20).

### `docs/05-vigipos-barragens.md`

18. Renomear o módulo para **M06 – Vigilância pós-desastre**.
19. **Reposicionar a ficha rápida**: apresentá-la como instrumento de cadastro em normalidade e de simulado, explicitando que, na fase aguda, os indicadores devem vir de sistemas rotineiros. Marcar cada campo hoje previsto conforme a Tabela 23 (§8.4) — o que é obtenível de sistema existente e o que exigiria coleta nova e, portanto, não pode ser ativado.
20. Substituir o IPAPD por **SAU-07 e correlatos**, ou mantê-lo como proposta explicitamente marcada como não prevista no documento oficial.
21. Renomear o IRS para **POS-10 – Índice de recuperação sanitária** (P3).
22. Adotar a hierarquia temporal de fontes do §8.1 (minutos–horas / horas–dias / dias–semanas).
23. Mapear as síndromes para os códigos POS-01 a POS-10 e adotar os métodos estatísticos da Tabela 22 com as saídas mínimas ali exigidas.
24. Incorporar a exigência de que todo sinal seja descrito como **associação temporal ou anomalia estatística, nunca causalidade confirmada** (§8.3).

### `docs/02-fontes-de-dados.md`

25. Adotar os **códigos oficiais de fonte** e a **classificação de disponibilidade A–E** (§4, Tabelas 8 e 9).
26. Reclassificar o painel Power BI como **PBI-01, classe E, "não usar como fonte"**, alinhando ao §1.3 e ao §4 — a redação atual é mais permissiva que a norma.
27. Acrescentar o **catálogo de metadados de 16 campos** exigido no §4.2 (Tabela 10) como estrutura a ser preenchida por fonte.
28. Incluir as fontes que hoje faltam no documento: INF-01 (DER-MT/DNIT) e DES-01 (S2ID/Atlas Digital).

### `docs/06-arquitetura.md`

29. Adotar a árvore de diretórios oficial do §3.3 e registrar a divergência atual do repositório.
30. Adotar a nomenclatura **Bronze/Silver/Gold** e a pilha do §3.2, incluindo a escolha de PowerShell + Agendador de Tarefas para o MVP.
31. Acrescentar os **nove módulos M01 a M09** e o modelo lógico de 20 tabelas (§5.1), com destaque para `xref_barragem_fonte`.
32. Acrescentar os 12 endpoints da API (§10.1), os oito métodos obrigatórios do conector (§10.2) e as regras de idempotência (§10.3).
33. Acrescentar SIRGAS 2000 (EPSG:4674), UTC com exibição em America/Cuiaba e hash SHA-256 dos brutos (§5.2).
34. Substituir a seção de limites da IA pelo **contrato JSON de oito campos** do §9.3 (Tabela 24), incluindo `prohibited_inference`.

### `docs/07-telas.md`

35. Passar para **nove telas** conforme a Tabela 27: acrescentar **Qualidade**, **Sala de Situação** e **Painel público**; renomear "Impacto observado" para **Mapa de impacto**; reposicionar "Assistência e logística" e "Recuperação" como conteúdo de outras telas ou marcá-las como extensões não previstas.

### `docs/08-roadmap.md`

36. Passar para **seis fases (0 a 5)** conforme a Tabela 29, criando a **Fase 0 – Descoberta e governança** com suas quatro entregas.
37. Separar satélite (Fase 4) de IA supervisionada (Fase 5).
38. Acrescentar os **dez critérios de aceite do MVP** (§12.2) e o **backlog de 12 épicos** (Tabela 30) com suas dependências.
39. Incorporar o **Apêndice A** como checklist de prontidão, com os 18 itens e seus responsáveis.
40. Registrar a diretriz do §14.1 de que o painel vem **depois** das tabelas Gold e da API — e posicionar o painel atual como protótipo de diagnóstico, não como entrega da arquitetura-alvo.

### `docs/01-visao-geral.md`

41. Substituir os "cinco momentos operacionais" pelos instrumentos oficiais: faixas de cor (§7.3), ciclo de alerta (§7.5) e hierarquia temporal de fontes (§8.1) — ou mantê-los como camada narrativa, deixando explícito que não constam do documento oficial.
42. Acrescentar as seis **decisões de desenho já estabelecidas** do Sumário executivo e os seis itens de **fora de escopo** do §1.3.
43. Acrescentar os oito perfis de usuário e a governança mínima do §2.

### `docs/09-dicionario-de-dados.md`

44. Acrescentar o mapeamento de cada coluna nossa para a entidade oficial correspondente do §5.1.
45. Registrar as três armadilhas de dados (hm³, caixa de município, altura negativa) como instâncias de CAD-05 e CAD-06.

### `docs/10-glossario.md`

46. Acrescentar: IPS-B, M01 a M09, Bronze/Silver/Gold, classes A–E de disponibilidade e de confiança, P1/P2/P3, `INSUFFICIENT_DATA`, DCO, S2ID, FN-SUS, RAG, SITREP, ZAS/ZSS.

---

## O que precisa de decisão do usuário

1. **O prazo de 03/08/2026 muda a prioridade?** O produto contratual é um relatório de 6 a 10 páginas, e faltam cinco dias. A plataforma é um objetivo de médio prazo. Convém suspender a engenharia e produzir o relatório com os dados que já temos?

2. **Manter ou desativar o coletor do Power BI?** O documento o classifica como classe E, não usar. Os quatro campos exclusivos (comprimento do coroamento, data da última fiscalização, data da última autuação, tipo de empreendedor) sustentam indicadores de priorização. As opções são desativar e perder os campos, manter marcado como não conforme, ou solicitar o dataset à ANA conforme §14.

3. **A ficha rápida permanece?** Reposicioná-la para normalidade e simulado resolve o conflito com o princípio de demanda zero, mas retira do módulo pós-desastre boa parte da granularidade que o chat previa.

4. **Renomear IDAP para IPS-B agora ou manter os dois nomes?** A renomeação atinge `docs/03-idap.md`, os oito arquivos de `scripts/idap/` e o nome da pasta.

5. **Migrar para PostgreSQL/PostGIS e a árvore oficial de diretórios, ou seguir em arquivos?** É a decisão que separa protótipo de sistema, e depende da infraestrutura da SES-MT, que o Apêndice A registra como pendente.

6. **Coletar o recorte de populações vulneráveis** — indígenas, quilombolas, assentamentos rurais e ribeirinhas — que o relatório contratual pede explicitamente e que não está no inventário atual.

7. **Qual dos três modelos de cinco estágios** é o oficial para o programa, dada a inversão de cores entre o produto de seca e o de barragens?
