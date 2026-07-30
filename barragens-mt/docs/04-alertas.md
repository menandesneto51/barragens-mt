# 4. Modelo de emissão de alertas territorializados

> Prazos, canais e regras de escalonamento apresentados aqui são **propostas a validar**
> com a Defesa Civil estadual, o CIEVS e as regiões de saúde. Os campos obrigatórios do
> alerta e a ressalva de não-evacuação são requisitos fixos, não negociáveis.

## 4.1 Princípio: alerta sem endereço não é alerta

Um alerta que diz "a Barragem X está em nível laranja" e é publicado em um painel não
alerta ninguém. Para que exista alerta, três coisas precisam estar resolvidas **antes** do
evento:

1. **Vínculo territorial prévio** — quais municípios, regiões de saúde e serviços estão a
   jusante desta barragem.
2. **Vínculo institucional prévio** — quem, com nome, cargo, telefone e e-mail, recebe o
   alerta em cada um desses municípios.
3. **Máquina de entrega** — como se sabe que a pessoa recebeu, e o que acontece quando não
   recebe.

Nenhuma das três se resolve no dia do desastre.

## 4.2 Vínculo prévio obrigatório por barragem

Cada uma das 1.248 barragens do inventário precisa ter, no cadastro da plataforma, o
vínculo com os atores abaixo. Enquanto o vínculo não existir, a barragem fica marcada como
**não alertável**, e essa marcação é um indicador de gestão exibido na Tela 1
(`docs/07-telas.md`).

| Vínculo | Conteúdo mínimo | Fonte do cadastro | Responsável pela atualização |
| --- | --- | --- | --- |
| Municípios potencialmente atingidos | Lista de códigos IBGE, com a distinção entre ZAS e ZSS | Mancha de inundação × malha municipal | Plataforma, a partir do estudo de ruptura |
| Regiões de saúde | Região de cada município da lista | Cadastro da SES-MT | SES-MT |
| Gestor municipal de saúde | Nome, cargo, telefone, celular, e-mail institucional, substituto | Cadastro municipal | Município, validação trimestral |
| Vigilância em Saúde municipal | Responsável e plantão | Cadastro municipal | Município |
| Defesa Civil municipal e estadual | Coordenador, plantão 24 h | Defesa Civil | Defesa Civil |
| SAMU | Central de regulação de urgência de referência | SES-MT | SES-MT |
| Hospitais de referência | Estabelecimento CNES, diretor técnico, plantão | CNES + SES-MT | SES-MT |
| Vigilância da qualidade da água (Vigiagua) | Responsável municipal e estadual | Sisagua + SES-MT | SES-MT |
| CIEVS regional ou municipal | Plantão do CIEVS de referência | SES-MT | SES-MT |
| Concessionária de água | Contato operacional 24 h, sistemas afetados | Concessionária | Concessionária |
| Responsável pelo transporte sanitário | Coordenação de transporte, frota disponível | Município e SES-MT | Município |
| Empreendedor | Responsável técnico pela segurança da barragem, plantão | SNISB / SIGBM + contato direto | Empreendedor |
| Órgão fiscalizador | Ponto focal na SEMA-MT, ANM, ANEEL ou ANA | Órgão | Órgão |

Regra de qualidade: um contato sem validação nos últimos 90 dias pontua no indicador **D8**
do IDAP e, se o alerta não for confirmado, dispara a regra **R09**.

## 4.3 Conteúdo mínimo do alerta

Todo alerta emitido, em qualquer canal, contém obrigatoriamente:

| Bloco | Campo | Obrigatório | Observação |
| --- | --- | --- | --- |
| Cabeçalho | Identificador único do alerta | Sim | Formato `ALERTA-AAAAMMDD-HHMM-{id_barragem}` |
| Cabeçalho | Nível e significado | Sim | Verde/Amarelo/Laranja/Vermelho/Roxo com o significado escrito |
| Identificação | Nome e código da barragem | Sim | Código do SNISB |
| Identificação | Município da estrutura | Sim | |
| Identificação | Órgão fiscalizador e empreendedor | Sim | |
| Identificação | Uso principal | Sim | Determina se há rejeito envolvido |
| Identificação | Região de saúde | Sim | |
| Temporal | Data e hora da emissão **com fuso de Cuiabá (UTC-4)** | Sim | Nunca UTC nem hora local do servidor |
| Índice | IDAP, faixa do índice, nível final | Sim | Se o nível final divergir do índice, indicar que foi elevado por regra |
| Índice | Completude, confiabilidade e IDAP projetado | Sim | Impede leitura de falso verde |
| Índice | Versão dos pesos | Sim | Requisito de auditoria |
| 1 | **Motivos quantificados** | Sim | Um item por indicador com pontuação acima de zero, com valor, rótulo da faixa e pontos. Nunca texto genérico |
| 1 | Pontuação por dimensão | Sim | |
| 2 | **População potencialmente exposta** | Sim | Total, parcela em grupos prioritários, tempo de chegada da onda, material do reservatório |
| 3 | **Unidades de saúde em risco de inundação ou isolamento** | Sim | Contagem por tipo e destaque para hospital de referência |
| 4 | **Municípios potencialmente afetados** | Sim | Se o vínculo não existir, o alerta declara a pendência como bloqueante |
| 5 | Regras determinísticas disparadas | Sim | Com a ação automática de cada uma |
| 6 | **Ações recomendadas** | Sim | Lista por nível, mais a instrução de sanar lacunas de dado |
| 7 | **Fontes dos dados** | Sim | Uma linha por fonte efetivamente usada no cálculo |
| 8 | **Ressalvas** | Sim | Inclui obrigatoriamente: *"Este alerta não constitui ordem de evacuação."* |
| 8 | Prazo de confirmação de recebimento | Sim, exceto Verde | Conforme §4.5 |
| 8 | Advertência de subestimação | Quando completude < 80% | |

### 4.3.1 Ações recomendadas por nível

| Nível | Ações |
| --- | --- |
| **Verde** | Manter a rotina de monitoramento e a atualização cadastral. Revalidar contatos institucionais da ZAS a cada 90 dias |
| **Amarelo** | Acompanhar chuva e nível a jusante nas próximas 24 h. Confirmar com o empreendedor a condição da estrutura e da instrumentação. Verificar vigência do plano e lista de contatos |
| **Laranja** | Acionar Vigilância em Saúde e Defesa Civil dos municípios da ZAS. Conferir leitos, ambulâncias, abrigos e estoques. Reforçar monitoramento da qualidade da água a jusante. Listar pacientes dependentes de tecnologia na área exposta. Preparar — sem executar — logística de transporte sanitário e abrigos |
| **Vermelho** | Sala de Situação em prontidão com responsável de plantão definido. Notificar hospitais de referência, SAMU, CIEVS e concessionária. Pré-posicionar ambulâncias, medicamentos e água potável fora da mancha. Articular com a Defesa Civil a comunicação de risco. Confirmar rotas alternativas e pontos de encontro |
| **Roxo** | Ativar COE estadual e VIGIPÓS-BARRAGENS. Iniciar a ficha rápida nos municípios atingidos. Acionar abrigos, transporte sanitário e reforço assistencial. Suspender captações comprometidas e iniciar abastecimento alternativo. Emitir o primeiro SITREP em até 1 h |

Note que nenhuma ação em nenhum nível é "evacuar". Evacuação aparece apenas como resposta a
determinação da autoridade competente (regra R05).

## 4.4 Exemplo real gerado pela implementação

Saída literal de `python scripts/idap/exemplo.py` para o cenário 3 — barragem com índice na
faixa Amarelo, elevada a Vermelho pela regra R01. O bloco 7 aparece abreviado aqui; no
alerta real ele lista todas as fontes usadas.

```
==============================================================================
ALERTA VIGIBARRAGENS-MT — NÍVEL VERMELHO (EMERGÊNCIA POTENCIAL)
==============================================================================
Identificador do alerta : ALERTA-20260729-1530-MT-EX-0003
Barragem                : Barragem de Rejeitos São Bento II (código MT-EX-0003)
Município da estrutura  : Poconé — MT
Órgão fiscalizador      : Agência Nacional de Mineração - ANM
Empreendedor            : São Bento Extração Mineral Ltda. (fictícia)
Uso principal           : Contenção de rejeitos de mineração
Região de saúde         : Região de Saúde Baixada Cuiabana
Data e hora da emissão  : 29/07/2026 15:30 (horário de Cuiabá, UTC-4)
IDAP                    : 30 de 100 pontos (faixa Amarelo: atenção)
Nível final             : Vermelho — elevado por regra determinística
Completude do cálculo   : 100% (confiabilidade suficiente; IDAP projetado 30)
Versão dos pesos        : 0.1.0-metodologica

1. MOTIVOS
   - [B2] Nível oficial de emergência declarado: Emergência Nivel 2 — Emergência Nível 2 (9 de 10 pontos)
   - [B1] Categoria de Risco (CRI) oficial: Média (3 de 5 pontos)
   - [B3] Ausência de estabilidade declarada: Atestada mas vencida (3 de 5 pontos)
   - [B4] Anomalia estrutural ativa: 3 de nota (escala 0 a 10 do SIGBM) — anomalia com medidas corretivas em implantação (2 de 5 pontos)
   - [C1] População residente na Zona de Autossalvamento: 150 habitantes — 50 a 199 residentes (2 de 5 pontos)
   - [C6] Tempo de chegada da onda à primeira ocupação humana: 90 minutos — 1 h a 2 h (2 de 4 pontos)
   - [C8] Presença de contaminantes ou rejeitos no reservatório: Rejeito não inerte ou perigoso (2 de 2 pontos)
   - [A1] Chuva acumulada em 24 h na bacia: 15 mm — chuva moderada (1 de 5 pontos)
   - [A2] Chuva acumulada em 72 h na bacia: 40 mm — acumulado moderado (1 de 5 pontos)
   - [A3] Chuva prevista para a janela de 24 a 72 h: 25 mm previstos — previsão moderada (1 de 5 pontos)
   - [A4] Percentil climatológico do acumulado observado: 60 de percentil — acima da mediana (1 de 4 pontos)
   - [A5] Saturação antecedente do solo na bacia: 0,50 de índice (0 a 1) — solo parcialmente úmido (1 de 4 pontos)
   - [C2] Proporção de população vulnerável na ZAS: 0,18 de proporção — 10% a 19% (1 de 3 pontos)
   - [C3] Unidades de saúde ameaçadas: Uma unidade sem internação (1 de 4 pontos)

   Pontuação por dimensão:
   - A. Pressão hidroclimática: 5/30 (completude 100%)
   - B. Condição da barragem: 17/30 (completude 100%)
   - C. Impacto sanitário potencial: 8/25 (completude 100%)
   - D. Déficit de capacidade de resposta: 0/15 (completude 100%)

2. POPULAÇÃO POTENCIALMENTE EXPOSTA
   População residente estimada na ZAS: 150 pessoas.
   Em grupos prioritários: cerca de 27 pessoas (18%).
   Tempo estimado de chegada da onda à primeira ocupação: 90 min.
   Material predominante no reservatório: Rejeito não inerte ou perigoso.

3. UNIDADES DE SAÚDE EM RISCO DE INUNDAÇÃO OU ISOLAMENTO
   Unidades sem internação na mancha ou sem via de acesso: 1.
   Unidades com internação ou urgência: 0.

4. MUNICÍPIOS POTENCIALMENTE AFETADOS
   - Poconé

5. REGRAS DETERMINÍSTICAS DISPARADAS
   - [R01] Emergência oficial de nível 2 ou 3 declarada — eleva o alerta a no mínimo
     Vermelho; ação: notificar imediatamente Defesa Civil estadual e municipal, CIEVS,
     SAMU e gestores da ZAS; colocar a Sala de Situação em prontidão

6. AÇÕES RECOMENDADAS
   - Colocar a Sala de Situação em prontidão e definir o responsável de plantão.
   - Notificar hospitais de referência, SAMU, CIEVS e concessionária de água.
   - Pré-posicionar ambulâncias, kits de medicamento e água potável fora da mancha.
   - Articular com a Defesa Civil a comunicação de risco à população da ZAS.
   - Confirmar rotas alternativas e pontos de encontro previstos no plano.

7. FONTES DOS DADOS
   - SIGBM/ANM (Nível de Emergência), SNISB (NIVEL_PERIGO) e comunicação do empreendedor
   - SIGBM/ANM — Status DCE RISR, Status DCE RPSB e Status da DCO Atual
   - INMET (estações automáticas), Cemaden (pluviômetros) e NASA GPM-IMERG
   - CNES cruzado com a mancha de inundação e com as vias de acesso
   [... demais fontes usadas no cálculo ...]

8. RESSALVAS
   Este alerta não constitui ordem de evacuação. A determinação de evacuação é competência
   exclusiva da Defesa Civil e das autoridades responsáveis pela estrutura.
   O IDAP mede nível de atenção e prontidão do setor saúde; não estima
   probabilidade de rompimento, que depende de modelo de engenharia e de
   instrumentação da própria barragem.
   Confirmação de recebimento obrigatória em até 20 min, com identificação
   do responsável; a ausência de confirmação escalona o alerta (regra R09).
==============================================================================
```

## 4.5 Canais de emissão

| Canal | Níveis em que é usado | Latência esperada | Requisitos e limitações |
| --- | --- | --- | --- |
| **Painel web** | Todos | Imediata | Sempre disponível; não constitui entrega, porque não há garantia de que alguém esteja olhando |
| **E-mail institucional** | Todos | Segundos a minutos | Registro formal; sujeito a filtro de spam e a caixa não monitorada fora do horário |
| **SMS** | Laranja e acima | Segundos a minutos | Funciona sem dado móvel e em aparelho simples; limite de caracteres exige link para o alerta completo; depende de operadora |
| **Microsoft Teams** | Todos | Segundos | Bom para grupos de trabalho e Sala de Situação; requer que o destinatário use o ambiente institucional |
| **Aplicativo próprio** | Todos | Segundos | Permite confirmação com um toque, geolocalização do respondente e checklist de ações; exige instalação e manutenção |
| **WhatsApp Business institucional** | Laranja e acima, **quando autorizado** | Segundos | Canal de maior taxa de leitura efetiva no Brasil; depende de autorização institucional e de conformidade com a política da plataforma; nunca deve transportar dado de saúde identificável |
| **Ligação automática (voz)** | Vermelho e Roxo | Segundos | Único canal que acorda alguém à noite; exige confirmação por tecla e transcrição registrada |
| **Integração com sistemas da Defesa Civil** | Laranja e acima | Segundos a minutos | Coloca o alerta no fluxo em que a Defesa Civil já trabalha (S2iD e sistema estadual); requer acordo técnico (**a validar**) |

Regra de redundância: em Vermelho e Roxo, **no mínimo três canais independentes** são
acionados simultaneamente para cada destinatário, sendo pelo menos um deles ligação
automática (**proposta a validar**).

## 4.6 Máquina de estados de entrega

Um alerta **só é considerado entregue** quando há confirmação de recebimento, identificação
do responsável que confirmou e registro da hora da confirmação. Enviar não é entregar.

### 4.6.1 Estados

| Estado | Definição | Transição de saída |
| --- | --- | --- |
| `GERADO` | O cálculo produziu o alerta; ainda não foi despachado | Vai para `AGUARDANDO_SUPERVISAO` (Vermelho e Roxo) ou `ENVIADO` (Verde a Laranja) |
| `AGUARDANDO_SUPERVISAO` | Alerta crítico aguardando validação humana antes do despacho | `ENVIADO` após validação; `CANCELADO` se a supervisão identificar erro |
| `ENVIADO` | Despachado por todos os canais previstos para o nível | `RECEBIDO` quando o canal confirma entrega técnica; `FALHA_TECNICA` se nenhum canal entregou |
| `FALHA_TECNICA` | Nenhum canal conseguiu entregar (número inválido, e-mail rejeitado) | `ESCALONADO` imediato, sem esperar prazo |
| `RECEBIDO` | Entrega técnica confirmada pelo canal, mas nenhuma pessoa confirmou | `CONFIRMADO` ou `ESCALONADO` ao esgotar o prazo |
| `CONFIRMADO` | Pessoa identificada confirmou o recebimento, com hora registrada | `ENCERRADO` ou nova emissão por mudança de nível |
| `ESCALONADO` | Prazo esgotado sem confirmação; acionados contato substituto, gestor regional e Defesa Civil estadual | `CONFIRMADO` quando alguém confirmar; `ESCALONADO_MAXIMO` se o segundo prazo também esgotar |
| `ESCALONADO_MAXIMO` | Nenhum nível da cadeia confirmou | Registro de falha institucional no evento, comunicação ao gabinete da SES-MT |
| `ENCERRADO` | O alerta foi substituído por outro, ou a barragem retornou à faixa Verde | Terminal |
| `CANCELADO` | Alerta retirado por erro identificado na supervisão | Terminal, com registro do motivo |

### 4.6.2 Prazos por nível (**propostas a validar**)

| Nível | Prazo de confirmação | 1º escalonamento (ao esgotar o prazo) | 2º escalonamento |
| --- | --- | --- | --- |
| **Verde** | Não exige confirmação | — | — |
| **Amarelo** | 120 min | Contato substituto do município | Gestor regional de saúde, após 120 min adicionais |
| **Laranja** | 60 min | Contato substituto + gestor regional de saúde | Defesa Civil estadual, após 60 min adicionais |
| **Vermelho** | 20 min | Contato substituto + gestor regional + Defesa Civil estadual, com ligação automática | CIEVS estadual e gabinete da SES-MT, após 20 min adicionais |
| **Roxo** | 10 min | Toda a cadeia simultaneamente, com ligação automática repetida | Gabinete da SES-MT e Casa Militar / Defesa Civil estadual, após 10 min adicionais |

### 4.6.3 O que se registra de cada tentativa

| Campo | Conteúdo |
| --- | --- |
| `id_alerta` | Identificador do alerta |
| `destinatario` | Pessoa e instituição |
| `canal` | Painel, e-mail, SMS, Teams, app, WhatsApp, voz, integração |
| `hora_envio` | Com fuso de Cuiabá |
| `hora_entrega_tecnica` | Retorno do canal |
| `hora_confirmacao` | Quando a pessoa confirmou |
| `identificacao_de_quem_confirmou` | Nome e cargo — não basta "confirmado" |
| `estado_final` | Estado da máquina ao encerrar |
| `numero_de_escalonamentos` | Quantas vezes escalonou |

Esse registro é o que permite responder, depois do evento, à pergunta que sempre aparece:
*"o município foi avisado?"* — com hora, canal e nome de quem recebeu, em vez de
impressões.

### 4.6.4 Indicadores de desempenho da comunicação

| Indicador | Fórmula | Meta proposta (**a validar**) |
| --- | --- | --- |
| Taxa de confirmação no prazo | alertas confirmados no prazo ÷ alertas emitidos × 100 | >= 95% para Vermelho e Roxo |
| Tempo mediano até a confirmação | mediana de (hora de confirmação − hora de envio) | <= 50% do prazo do nível |
| Taxa de escalonamento | alertas escalonados ÷ alertas emitidos × 100 | <= 10% |
| Municípios com contato desatualizado | municípios sem validação em 90 dias ÷ municípios vinculados × 100 | 0% |
| Barragens não alertáveis | barragens sem vínculo territorial ÷ total de barragens × 100 | Tendendo a 0 ao longo das fases do roteiro |

## 4.7 Regras de contenção de ruído

Um sistema que alerta demais deixa de ser lido. Quatro travas (**propostas a validar**):

| Trava | Regra |
| --- | --- |
| Histerese na descida | A barragem só sai de uma faixa depois de permanecer 3 ciclos consecutivos de cálculo na faixa inferior. Evita oscilação por variação de leitura |
| Reemissão | Um novo alerta do mesmo nível só é reemitido se algum motivo mudar, ou a cada 12 h em Laranja, 6 h em Vermelho e 1 h em Roxo |
| Agrupamento por município | Quando várias barragens de um mesmo município estão em alerta, o gestor municipal recebe um alerta consolidado, com detalhe por barragem — não um alerta por estrutura |
| Supressão de alerta técnico | O alerta técnico da regra R06 é agrupado em relatório diário, exceto quando a barragem estiver em Laranja ou acima, caso em que é imediato |

## 4.8 Despacho unificado (implementação)

A fila textual do piloto (`alertas/piloto/*.txt`) é despachável por:

1. **Telegram** — `VIGI_TELEGRAM_BOT_TOKEN` + `VIGI_TELEGRAM_CHAT_ID`
2. **E-mail SMTP** — `VIGI_SMTP_HOST`, `VIGI_SMTP_PORT`, `VIGI_SMTP_USER`, `VIGI_SMTP_PASS`, `VIGI_SMTP_FROM`

Script: `scripts/29_despacho_alertas.py` (dry-run por padrão; `--enviar` para tentativa real).
Log: `dados/tratados/despacho_alertas_log.csv`.

Confirmação persistente: `dados/tratados/confirmacoes/confirmacoes.csv` (Streamlit) além do
protótipo HTML em localStorage. Payload para Defesa Civil: `docs/13-defesa-civil-gancho.md`.
