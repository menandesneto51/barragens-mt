# 1. VIGIBARRAGENS–MT / Saúde 360 — visão geral

> Documento conceitual. Sempre que uma afirmação depende de decisão institucional ainda
> não tomada, ou de dado que não pôde ser verificado nesta versão, ela aparece marcada
> como **a validar**.

## 1.1 O que é

O VIGIBARRAGENS–MT / Saúde 360 é uma plataforma estadual de **alerta precoce,
monitoramento de impactos e vigilância pós-desastre** aplicada a barragens em Mato
Grosso, construída sob a ótica do setor saúde.

Ela responde a três perguntas, em ordem de urgência:

| Pergunta | Momento | Produto principal |
| --- | --- | --- |
| Quais barragens exigem atenção do setor saúde agora? | antes | IDAP-Barragens e alerta territorializado |
| O que está acontecendo com as pessoas e os serviços? | durante | painel de impacto observado e ficha rápida |
| O que mudou na saúde da população atingida? | depois | módulo VIGIPÓS-BARRAGENS e indicadores de recuperação |

O objeto de vigilância não é a estrutura de concreto e terra — esse é o objeto dos órgãos
fiscalizadores. O objeto é a **população potencialmente atingida e a rede que a atende**.

## 1.2 Escopo negativo — o que o sistema não faz

Esta seção vem antes das funcionalidades de propósito, porque a confusão sobre ela é a
principal fonte de risco institucional do projeto.

| O sistema NÃO faz | Por quê | Quem faz |
| --- | --- | --- |
| Calcular probabilidade automática de rompimento | Exige modelo de engenharia de barragens calibrado, instrumentação da própria estrutura (piezômetros, inclinômetros, marcos superficiais, medidores de vazão de drenos) e análise de estabilidade por profissional habilitado | Empreendedor e órgão fiscalizador, via Revisão Periódica de Segurança e Declaração de Condição de Estabilidade |
| Declarar que uma barragem está estável ou instável | Mesma razão | Responsável técnico do empreendedor, atestado ao órgão fiscalizador |
| Determinar evacuação | É ato de autoridade pública com consequências legais e materiais imediatas | Defesa Civil e autoridades competentes, conforme o PAE/PAEBM |
| Substituir laudo de engenharia | Não há substituição possível de inspeção técnica presencial | Engenheiro responsável |
| Confirmar causalidade epidemiológica automaticamente | Sinal estatístico não é nexo causal | Vigilância Epidemiológica, com investigação de campo |

O que o sistema calcula é **nível de atenção e prontidão para o setor saúde**: dado o que
se sabe hoje sobre a chuva, sobre a condição declarada da estrutura, sobre quem está a
jusante e sobre o que existe de capacidade de resposta, qual deve ser a postura da rede de
saúde nas próximas horas e dias.

Essa distinção é operacionalizada pelo IDAP-Barragens (`docs/03-idap.md`), cujo nome
carrega a definição: **Índice Dinâmico de Alerta e Prontidão** — não índice de risco de
ruptura.

## 1.3 Aderência ao Vigidesastres

O Vigidesastres — Vigilância em Saúde Ambiental dos Riscos Associados aos Desastres — tem
como atribuição a análise da situação de saúde **antes, durante e depois** de emergências
e desastres, com uso dos sistemas oficiais de informação e monitoramento permanente de
áreas de risco e populações vulneráveis.

| Diretriz do Vigidesastres | Como a plataforma atende |
| --- | --- |
| Análise da situação de saúde **antes** do desastre | Linhas de base municipais e por área potencialmente atingida, construídas com SIM, SINAN e CNES (`docs/05-vigipos-barragens.md`, §3) |
| Análise **durante** o desastre | Ficha rápida de saúde pós-desastre, indicadores de pressão assistencial (IPAPD) e monitoramento de abrigos |
| Análise **depois** do desastre | Detecção estatística de excesso de agravos, Índice de Recuperação Sanitária (IRS) e acompanhamento de médio prazo |
| Uso dos sistemas oficiais de informação | SIM, SINAN, SIH, SIA, CNES, e-SUS APS, SISREG, Sisagua/Vigiagua, GAL/LACEN (`docs/02-fontes-de-dados.md`, §8) |
| Monitoramento de áreas de risco | Cadastro georreferenciado de 1.248 barragens, manchas de inundação e Zonas de Autossalvamento |
| Monitoramento de populações vulneráveis | Recorte da população exposta por grupo prioritário na dimensão C do IDAP |
| Articulação intersetorial | Modelo de alerta territorializado com vínculo prévio a Defesa Civil, concessionárias, SAMU e gestores municipais (`docs/04-alertas.md`) |

A plataforma não cria um sistema de informação paralelo. Ela consome os sistemas oficiais
e acrescenta duas camadas que hoje não existem de forma integrada em Mato Grosso: o
**vínculo territorial explícito entre cada barragem e a rede de saúde a jusante**, e o
**registro auditável de emissão e confirmação de alerta**.

## 1.4 Os cinco momentos operacionais

A plataforma opera em cinco momentos. Não são fases de projeto: são estados em que uma
barragem específica pode estar a qualquer instante, e barragens diferentes podem estar em
momentos diferentes simultaneamente.

### Momento 1 — Normalidade

| Aspecto | Conteúdo |
| --- | --- |
| **Objetivo** | Manter o cadastro atualizado, as linhas de base calculadas e a capacidade de resposta mapeada, de modo que a transição para pré-impacto seja imediata |
| **Dados que entram** | SNISB, SIGBM, IBGE, CNES, SIM, SINAN, Sisagua, cadastro de contatos institucionais, chuva observada e prevista em rotina |
| **Produtos gerados** | IDAP recalculado em rotina (faixa Verde); painel de comando estadual; relatório de pendências cadastrais; linhas de base epidemiológicas; validação trimestral de contatos |
| **Atores responsáveis** | Vigilância em Saúde Ambiental (Vigidesastres) da SES-MT como coordenadora; CIEVS estadual; órgãos fiscalizadores para o cadastro; municípios para os contatos |
| **Critério de saída** | IDAP entra na faixa Amarelo ou superior, ou qualquer regra determinística dispara |

### Momento 2 — Pré-impacto

| Aspecto | Conteúdo |
| --- | --- |
| **Objetivo** | Antecipar. Converter sinal hidroclimático e sinal estrutural em prontidão concreta da rede de saúde, antes de qualquer dano |
| **Dados que entram** | Chuva observada (INMET, Cemaden, IMERG) e prevista; nível e vazão a jusante (ANA); nível de emergência declarado; anomalias estruturais; telemetria do empreendedor; disponibilidade de leitos, ambulâncias e abrigos |
| **Produtos gerados** | Alerta territorializado por município com motivos quantificados; lista de pacientes dependentes de tecnologia na área exposta; verificação de estoques e rotas; prontidão da Sala de Situação; boletim de acompanhamento |
| **Atores responsáveis** | Vigidesastres/SES-MT; Defesa Civil estadual e municipal; SAMU; hospitais de referência; Vigiagua e concessionárias; CIEVS; empreendedor e órgão fiscalizador |
| **Critério de saída** | Ocorrência de rompimento, vazamento ou inundação relevante (vai para Momento 3), ou retorno do IDAP à faixa Verde (volta ao Momento 1) |

### Momento 3 — Impacto

| Aspecto | Conteúdo |
| --- | --- |
| **Objetivo** | Salvar vidas e manter a rede assistencial funcionando. Saber, em tempo quase real, o que foi atingido |
| **Dados que entram** | Registros da Defesa Civil; atendimentos de urgência; regulação estadual e municipal; movimentação hospitalar; imagens Sentinel-1 (delimitação de área alagada); ficha rápida de saúde; registros de abrigos; interrupções de água e energia |
| **Produtos gerados** | Delimitação preliminar da área atingida; contagem de vítimas, desalojados, desabrigados e isolados; mapa de unidades de saúde afetadas ou isoladas; IPAPD por unidade e por região; SITREP em cadência definida pelo COE |
| **Atores responsáveis** | COE estadual; Defesa Civil; SAMU; regulação; hospitais; Assistência Social; concessionárias; Vigilância em Saúde municipal |
| **Critério de saída** | Estabilização da fase de resgate e transição para o cuidado das consequências |

### Momento 4 — Pós-impacto agudo

| Aspecto | Conteúdo |
| --- | --- |
| **Objetivo** | Detectar precocemente os agravos que aparecem depois — doenças de transmissão hídrica, leptospirose, acidentes por animais peçonhentos, agravos respiratórios e dermatológicos, sofrimento mental agudo — e sustentar a assistência |
| **Dados que entram** | Ficha rápida consolidada; SINAN; atendimentos de urgência; GAL/LACEN; Sisagua e amostras de água; monitoramento de abrigos; SIH e SIA; e-SUS APS |
| **Produtos gerados** | Razão observado/esperado por agravo e por território; sinais sindrômicos; excesso de casos; indicadores de água e saneamento; monitoramento de abrigos; boletim epidemiológico do evento |
| **Atores responsáveis** | Vigilância Epidemiológica; CIEVS; LACEN; Vigiagua; APS; saúde mental; Assistência Social |
| **Critério de saída** | Retorno dos indicadores ao canal endêmico esperado e restabelecimento dos serviços essenciais |

### Momento 5 — Recuperação

| Aspecto | Conteúdo |
| --- | --- |
| **Objetivo** | Acompanhar o restabelecimento da rede e da saúde da população, e registrar as lições que alteram o plano |
| **Dados que entram** | CNES atualizado; produção da APS; Sisagua; SIM (para excesso de mortalidade); acompanhamento de saúde mental; monitoramento ambiental; registro de pendências |
| **Produtos gerados** | Índice de Recuperação Sanitária (IRS); excesso de mortalidade do período; relatório pós-desastre; revisão do PAE, do plano de contingência municipal e dos pesos do IDAP |
| **Atores responsáveis** | Vigidesastres/SES-MT; gestão municipal; Defesa Civil; órgãos fiscalizadores; academia, quando houver cooperação |
| **Critério de saída** | Encerramento formal do evento, com relatório publicado e pendências atribuídas |

## 1.5 Como os momentos se conectam ao índice e às regras

```
                    +--------------------------+
   Fontes  ------->  |  IDAP-Barragens (0-100) |  ---->  faixa de cor
   (docs/02)         +--------------------------+
                                  |
                                  v
                    +--------------------------+
                    | Regras determinísticas   |  ---->  nível final e
                    | de sobreposição (R01-R09)|         ação automática
                    +--------------------------+
                                  |
        Verde        Amarelo       Laranja       Vermelho       Roxo
      Momento 1     Momento 2     Momento 2     Momento 2/3   Momento 3
      normalidade   atenção       mobilização   emergência    resposta
                                                potencial     crítica
```

A faixa de cor **sugere** o momento operacional, mas não o determina sozinha. A transição
para o Momento 3 depende de fato observado — rompimento, vazamento, inundação — e não de
pontuação. Essa é exatamente a função das regras determinísticas de sobreposição
(`docs/03-idap.md`, §7).

## 1.6 O que já existe hoje

O que sustenta esta especificação não é hipótese: há um inventário coletado e verificado.

| Base | Registros | Data da extração | Origem |
| --- | ---: | --- | --- |
| Barragens cadastradas em MT (SNISB/ANA) | 1.248 | 29/07/2026 | Serviço ArcGIS do SNIRH |
| Barragens de mineração em MT (SIGBM/ANM) | 183 | 29/07/2026 | CSV de dados abertos da ANM |
| Municípios de MT (IBGE) | 142 | 29/07/2026 | API de localidades |
| Polígonos na malha municipal (IBGE) | 141 | 29/07/2026 | API de malhas — divergência registrada em `docs/09-dicionario-de-dados.md` |
| Atributos complementares do painel SNISB | 1.248 | 29/07/2026 | Modelo semântico do Power BI público |

Recortes que dimensionam o problema:

- 106 barragens com Categoria de Risco alta e 65 com Dano Potencial Associado alto.
- 63 barragens de classe A (maior exigência legal), das quais **12 sem Plano de Segurança
  registrado** e **15 sem PAE registrado**.
- 18 barragens de mineração com nível de emergência declarado (16 em Emergência Nível 1,
  2 em Nível de Alerta), concentradas em Nossa Senhora do Livramento, Poconé e Pontes e
  Lacerda.
- Apenas 94 das 1.248 barragens (7,5%) têm data de inspeção registrada.
- Barragens presentes em 115 dos 141 municípios com polígono.

Esses números são a razão pela qual a dimensão D do IDAP (déficit de capacidade de
resposta) tem peso próprio: a lacuna não é de sensor, é de plano.

## 1.7 Governança e limites institucionais

| Papel | Responsabilidade proposta (**a validar**) |
| --- | --- |
| Vigilância em Saúde Ambiental / Vigidesastres — SES-MT | Coordenação técnica da plataforma, calibração do IDAP, publicação de alertas ao setor saúde |
| CIEVS estadual | Recebimento e resposta a sinais, articulação de plantão |
| Defesa Civil estadual | Decisão sobre evacuação, articulação municipal, acionamento do Copernicus EMS quando cabível |
| Órgãos fiscalizadores (SEMA-MT, ANM, ANEEL, ANA) | Cadastro, classificação, fiscalização e declaração de condição da estrutura |
| Empreendedor | Instrumentação, inspeção, declaração de nível de emergência, PAE/PAEBM, sirenes |
| Municípios | Contatos atualizados, plano de contingência, ficha rápida, abrigos, confirmação de recebimento de alerta |

A plataforma é **consumidora** de decisão regulatória, não produtora. Quando o dado
oficial falta, ela registra a lacuna e reduz a confiabilidade declarada do cálculo — nunca
preenche por estimativa silenciosa.

## 1.8 Próximos documentos

- Catálogo de fontes, com endpoint, periodicidade e latência: `docs/02-fontes-de-dados.md`
- Especificação do índice: `docs/03-idap.md`
- Modelo de alerta e máquina de estados de entrega: `docs/04-alertas.md`
- Módulo pós-desastre: `docs/05-vigipos-barragens.md`
- Arquitetura de referência: `docs/06-arquitetura.md`
