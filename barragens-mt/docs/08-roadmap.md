# 8. Roadmap de implantação

> Prazos são estimativas de esforço relativo, não compromissos de calendário; dependem de
> equipe alocada e de acordos institucionais que não estão no controle do projeto. Todos
> marcados **a validar**.

## 8.1 O que já está pronto

Antes de qualquer plano, o inventário honesto do que existe neste repositório hoje.

| Entregável | Situação | Números reais |
| --- | --- | --- |
| `scripts/01_snisb_mt.py` | Funcionando | **1.248 barragens** em MT extraídas do SNISB/ANA, via `https://www.snirh.gov.br/arcgis/rest/services/IG/SNISB/FeatureServer/0/query`, filtro `ING_SG_UFMUNICIPIO = 'MT'`, paginação de 2.000, `outSR=4326` |
| `scripts/02_sigbm_anm.py` | Funcionando | **183 barragens de mineração** em MT, de 909 no país, a partir de `https://dadosabertos.anm.gov.br/SIGBM/Barragens.csv` (cp1252, 124 colunas), com conversão de coordenadas de grau/minuto/segundo para decimal |
| `scripts/03_ibge_mt.py` | Funcionando | **142 municípios** e malha municipal com **141 polígonos** — divergência registrada como pendência de qualidade |
| `scripts/04_powerbi_snisb.py` | Funcionando, frágil | Atributos complementares do relatório Power BI público do SNISB. Relatórios Power BI embutidos não expõem API estável; o coletor pode quebrar sem aviso |
| `scripts/05_consolidar_inventario.py` | Funcionando | Inventário consolidado com verificações de qualidade (altura negativa, variantes de nome de município, classificação ausente) |
| `scripts/comum.py` | Funcionando | Utilidades compartilhadas: caminhos, cliente HTTP com retry, gravação de CSV/GeoJSON/JSON, recorte por bbox de MT |
| `scripts/idap/` | Funcionando e testado | Implementação de referência do IDAP: modelo, pesos versionados, cálculo, regras determinísticas, geração de alerta, exemplo executável e testes unitários |
| `docs/00` a `docs/10` | Este conjunto | Documentação técnica da plataforma |

Tradução em uma frase: **existe inventário e existe motor de índice; não existe monitoramento.**
Nenhuma série hidrometeorológica, nenhuma mancha de inundação, nenhuma integração de saúde e
nenhum cadastro de contatos foram construídos. O roadmap abaixo está ordenado por dependência,
não por atratividade.

## 8.2 Visão geral das fases

| Fase | Foco | Escopo territorial | Pergunta que a fase responde |
| --- | --- | --- | --- |
| 1 | Piloto | Cuiabá e barragens que a afetam | "O modelo funciona de ponta a ponta em um lugar?" |
| 2 | Expansão estadual | Barragens prioritárias e municípios de ZAS e ZSS | "O modelo escala para o estado?" |
| 3 | Vigilância pós-desastre | Municípios com evento ativo | "Sabemos o que aconteceu com a saúde das pessoas?" |
| 4 | IA e simulação | Estado | "Conseguimos antecipar e não só reagir?" |

---

## 8.2bis Sequência decidida (29/07/2026)

Ordem fixa — ver `docs/11-principio-estadual-e-sequencia.md`:

1. **Base estadual + IDAP** (todas as barragens de MT; impacto extraterritorial por drenagem)
2. **Coletores hidrometeorológicos** via SIS Clima Saúde + TITAN (já validados no CIEVS MT)
3. **Piloto operacional** no eixo Manso–Cuiabá

O piloto municipal não é o perímetro do sistema: é a última etapa da Fase 1.

## 8.3 Fase 1 — Do estadual ao piloto Cuiabá

**Objetivo**: primeiro cobrir o estado com inventário e IDAP honestos; em seguida ligar a
hidro já operacional (SisClima/TITAN); só então percorrer o ciclo completo (dado → índice →
alerta → confirmação → ficha) no eixo Manso–Cuiabá.

### 8.3.1 Entregáveis

| # | Entregável | Descrição |
| --- | --- | --- |
| 1.1 | Cadastro de barragens do piloto | Barragens que podem afetar Cuiabá, com atributos do SNISB e do SIGBM conferidos um a um contra a fonte |
| 1.2 | Manchas de inundação disponíveis | Levantamento junto a SEMA-MT, ANM e empreendedores das manchas existentes; carga em PostGIS; para as sem estudo, marcação explícita de ausência |
| 1.3 | População e serviços expostos | Interseção de mancha com setor censitário, CNES, captações do Sisagua, escolas e malha viária |
| 1.4 | Linhas de base de saúde | Série histórica de CNES, SIM e SINAN para os municípios do piloto, conforme `docs/05-vigipos-barragens.md` §5.3 |
| 1.5 | Coletores hidrometeorológicos | INMET (estações automáticas), Cemaden (pluviômetros), ANA (telemetria de nível e vazão), GPM-IMERG (chuva por satélite) |
| 1.6 | Primeiro motor de alerta em produção | `scripts/idap/` conectado ao banco, com recálculo agendado, gravação de cada cálculo e geração do texto do alerta |
| 1.7 | Ficha rápida em teste | Formulário da §5.4 implementado e testado em simulado com a Vigilância municipal |
| 1.8 | Cadastro de contatos do piloto | Contatos institucionais dos municípios do piloto, validados por telefone |

### 8.3.2 Pré-requisitos

| Pré-requisito | Responsável | Bloqueia |
| --- | --- | --- |
| Acordo com SEMA-MT para acesso a estudos e manchas | SES-MT / SEMA-MT | 1.2, e por consequência 1.3 |
| Acesso a bases de saúde identificáveis (SIM, SINAN) com base legal definida | Encarregado de dados / jurídico | 1.4 |
| Infraestrutura: PostgreSQL + PostGIS + agendador | TI da SES-MT | 1.6 |
| Chave de acesso a APIs que exigem cadastro | Equipe técnica | 1.5 |
| Definição do vínculo município → região de saúde | SES-MT | 1.3 |
| Adesão da Vigilância de Cuiabá ao simulado | SES-MT / SMS Cuiabá | 1.7, 1.8 |

### 8.3.3 Riscos

| Risco | Probabilidade | Impacto | Mitigação |
| --- | --- | --- | --- |
| Não existir mancha de inundação para nenhuma barragem do piloto | **Alta** | **Crítico** — sem mancha não há dimensão C, que vale 25 pontos | Estimativa geomorfológica preliminar, claramente rotulada como aproximação, com pressão institucional paralela pelos estudos oficiais |
| Certificado TLS autoassinado na cadeia do snirh.gov.br quebrar a coleta | Média | Médio | Já tratado no coletor; monitorar |
| Cemaden ou INMET sem estação útil nas bacias do piloto | Média | Alto | Complementar com GPM-IMERG, aceitando a latência de ~4 h do Early Run |
| Base legal para dado de saúde não sair no prazo | Média | Alto | Iniciar por linha de base agregada, que não exige dado identificável |
| O piloto virar um fim em si mesmo, sem preparar a expansão | Média | Alto | Todo entregável do piloto tem que ser parametrizável por município desde o início |

### 8.3.4 Critérios de aceite

| # | Critério | Verificação |
| --- | --- | --- |
| A1 | O IDAP de cada barragem do piloto é recalculado no prazo definido e o cálculo fica gravado com versão de pesos e estado de entrada | Consulta a `calculo_idap` mostrando cálculos consecutivos com proveniência completa |
| A2 | A completude de cada cálculo é exibida e as lacunas são nomeadas | Inspeção da tela 4 |
| A3 | Um alerta de teste percorre todo o ciclo: emissão, envio multicanal, confirmação de recebimento com identificação do responsável e hora | Registro em `confirmacao_entrega` |
| A4 | O escalonamento automático dispara quando não há confirmação no prazo | Teste com destinatário que não confirma |
| A5 | A ficha rápida é preenchida em simulado e alimenta os indicadores da §5.5 | Ficha gravada e indicadores calculados |
| A6 | As linhas de base permitem calcular esperado e limite superior para pelo menos leptospirose, doenças diarreicas agudas e acidentes com animais peçonhentos | Cálculo reproduzido |
| A7 | Nenhum alerta em Vermelho ou Roxo sai sem supervisão humana registrada | Auditoria do estado `AGUARDANDO_SUPERVISAO` |
| A8 | Falha de coletor aparece na tela como falha, e reduz a completude — nunca vira "sem risco" | Teste desligando um coletor |

O critério A8 é o mais importante da fase. Um sistema que confunde silêncio com tranquilidade é
pior do que nenhum sistema, porque produz confiança injustificada.

---

## 8.4 Fase 2 — Expansão estadual

**Objetivo**: sair de um município para o estado, sem perder qualidade de cadastro nem de
vínculo institucional.

### 8.4.1 Entregáveis

| # | Entregável | Descrição |
| --- | --- | --- |
| 2.1 | Priorização das barragens | Critério explícito de priorização (DPA alto, classe CNRH, rejeito, população a jusante, proximidade de captação e de unidade de saúde), aplicado às 1.248 + 183 |
| 2.2 | Cadastro de barragens prioritárias | Atributos conferidos, coordenadas validadas, lacunas cobradas do órgão fiscalizador |
| 2.3 | Delimitação de ZAS e ZSS | Por estudo oficial onde existir; por estimativa rotulada onde não existir |
| 2.4 | Cadastro estadual de gestores e atores | Todos os vínculos da §4.2, com data de última validação e rotina de revalidação |
| 2.5 | Integração com regiões de saúde | Vínculo município → região de saúde, com agregação de indicadores por região |
| 2.6 | Mapa estadual operacional | WebGIS com barragens, manchas, exposição e faixa de IDAP |
| 2.7 | Alertas territorializados em produção | Emissão para todos os municípios de ZAS e ZSS das barragens prioritárias |
| 2.8 | Rotina de revalidação de contatos | Processo com periodicidade definida e indicador de contatos vencidos |

### 8.4.2 Pré-requisitos

| Pré-requisito | Responsável |
| --- | --- |
| Fase 1 com critérios de aceite atendidos | Equipe técnica |
| Critério de priorização homologado pelo comitê técnico | SES-MT + SEMA-MT + Defesa Civil |
| Acordo de fluxo de dados com ANM para as barragens de rejeito | SES-MT / ANM |
| Capacidade de contato com 142 municípios | SES-MT, via regiões de saúde |
| Resolução da divergência 142 municípios × 141 polígonos | Equipe técnica / IBGE |

### 8.4.3 Riscos

| Risco | Probabilidade | Impacto | Mitigação |
| --- | --- | --- | --- |
| Cadastro de contatos envelhecer mais rápido do que é atualizado | **Alta** | **Crítico** — alerta que não chega é alerta que não existe | Rotina de revalidação obrigatória, indicador de contatos vencidos em tela, regra R09 de escalonamento |
| Volume de alertas gerar fadiga e descrédito | Alta | Alto | Calibração conservadora das faixas Amarelo e Laranja; revisão dos limiares após 6 meses de operação; nunca alertar em Verde |
| Ausência de mancha na maioria das barragens tornar a dimensão C estruturalmente incompleta | **Alta** | Alto | Declarar completude e não punir a barragem pela falta de dado; cobrar institucionalmente |
| Heterogeneidade de capacidade entre municípios | Alta | Médio | Nível mínimo de operação para município pequeno, com apoio da região de saúde |
| Divergência de nome de município entre fontes | Média | Médio | Já tratada em `scripts/05_consolidar_inventario.py`; consolidar tabela de variantes |

### 8.4.4 Critérios de aceite

| # | Critério |
| --- | --- |
| B1 | 100% das barragens prioritárias têm município, coordenada validada e órgão fiscalizador identificado |
| B2 | 100% dos municípios de ZAS das barragens prioritárias têm ao menos dois contatos institucionais validados nos últimos 6 meses |
| B3 | O mapa estadual carrega em tempo aceitável com todas as camadas ativas (**a validar**: menos de 5 s) |
| B4 | Taxa de confirmação de alertas de teste acima de limiar acordado (**a validar**: 90% no prazo do nível) |
| B5 | Indicador de contatos vencidos é exibido e acompanhado |
| B6 | Agregação por região de saúde reproduz a soma dos municípios sem divergência |

---

## 8.5 Fase 3 — Vigilância pós-desastre

**Objetivo**: tornar o VIGIPÓS-BARRAGENS operacional, para que o pós-impacto deixe de depender
de planilha improvisada em plena crise.

### 8.5.1 Entregáveis

| # | Entregável | Descrição |
| --- | --- | --- |
| 3.1 | Ficha rápida em operação | Formulário da §5.4 em produção, com versão para banda estreita e uso offline |
| 3.2 | Integração com urgência e emergência | Atendimentos de urgência, SAMU, regulação estadual e municipal |
| 3.3 | Integração hospitalar | Movimentação hospitalar, disponibilidade de leitos, notificações hospitalares |
| 3.4 | Integração laboratorial | GAL / LACEN, com positividade e tempo entre coleta e resultado |
| 3.5 | Detecção de excesso de agravos | Canal endêmico, CUSUM, EWMA, Poisson e binomial negativa implementados, com recomendação de uso por situação (§5.6) |
| 3.6 | Monitoramento de abrigos | Indicadores da §5.5.6, com atualização diária durante evento |
| 3.7 | Acompanhamento do abastecimento de água | Integração com Sisagua/Vigiagua e concessionárias; indicadores da §5.5.4 |
| 3.8 | IPAPD e IRS em produção | Índices calculados com dado real, com decomposição visível |
| 3.9 | SITREP estruturado | Relatório de situação gerado a partir dos indicadores (sem IA nesta fase — só template) |

### 8.5.2 Pré-requisitos

| Pré-requisito | Responsável |
| --- | --- |
| Base legal e instrumentos formais para o dado de saúde identificável | Encarregado de dados / jurídico |
| Acordo com municípios sobre o fluxo da ficha rápida | SES-MT / SMS |
| Acesso técnico a SINAN, SIM, SIH, SIA, e-SUS APS, SISREG e GAL | SES-MT / DATASUS |
| Definição das nove síndromes e de seus critérios operacionais | Vigilância Epidemiológica |
| Segregação de base para dado identificável, com Row Level Security | TI |

### 8.5.3 Riscos

| Risco | Probabilidade | Impacto | Mitigação |
| --- | --- | --- | --- |
| Ficha rápida não ser preenchida durante a crise, por sobrecarga da equipe | **Alta** | **Crítico** | Ficha curta, obrigatoriedade mínima, preenchimento em minutos, possibilidade de envio parcial, treinamento em simulado |
| Oportunidade de notificação do SINAN insuficiente para o tempo do evento | Alta | Alto | Ficha rápida como complemento explícito, nunca como substituto |
| Falso sinal estatístico gerar mobilização desnecessária e desgaste | Média | Alto | Sinal sempre acompanhado de método, parâmetros e limite superior; classificação em níveis; validação humana antes de ação |
| Linha de base insuficiente em município pequeno (contagens baixas) | Alta | Médio | Agregação por região de saúde e uso de modelo adequado a contagem baixa |
| Vazamento de dado de saúde identificável | Baixa | **Crítico** | Medidas da §6.6; supressão de célula pequena; registro de todo acesso |

### 8.5.4 Critérios de aceite

| # | Critério |
| --- | --- |
| C1 | A ficha rápida é preenchida em até 10 minutos por informante treinado (**a validar** em teste de usabilidade) |
| C2 | O sistema calcula razão O/E e excesso de casos para as síndromes definidas, com método e parâmetros registrados |
| C3 | O exemplo trabalhado de leptospirose da §5.6.4 é reproduzido pelo sistema: 12 observados em 7 dias, esperado 1,8, limite superior 4, razão O/E 6,7, classificação de sinal crítico |
| C4 | IPAPD e IRS são calculados com dado real e a decomposição por termo é visível |
| C5 | Nenhum dado individual aparece em painel, boletim ou saída de IA |
| C6 | O SITREP é gerado sem digitação manual de indicadores |
| C7 | Célula com contagem de 1 a 4 casos por localidade é suprimida nas saídas publicadas |

---

## 8.6 Fase 4 — IA e simulação

**Objetivo**: passar de reação a antecipação, sem transferir decisão para o modelo.

### 8.6.1 Entregáveis

| # | Entregável | Descrição |
| --- | --- | --- |
| 4.1 | Cenários hidroclimáticos | Simulação de trajetórias de chuva e nível, com IDAP projetado por cenário |
| 4.2 | Projeção de impacto | População atingida, unidades afetadas e captações comprometidas por cenário |
| 4.3 | Estimativa de demanda | Demanda projetada de atendimentos, leitos, ambulâncias, medicamentos e água segura |
| 4.4 | Rotas alternativas | Cálculo de rotas de acesso considerando trechos interrompidos, com tempo adicional |
| 4.5 | SITREP automático | Redação do relatório de situação por IA, sobre indicadores já calculados, com revisão humana registrada |
| 4.6 | Assistente de Sala de Situação | Consulta em linguagem natural sobre dados agregados da plataforma |
| 4.7 | Explicação de sinais | Interpretação textual de sinais estatísticos, com contexto territorial e temporal |
| 4.8 | Boletins e notas de comunicação de risco | Adaptação do mesmo conteúdo técnico a públicos distintos, com revisão obrigatória |

### 8.6.2 Pré-requisitos

| Pré-requisito | Responsável |
| --- | --- |
| Fases 1 a 3 em operação — sem dado consolidado, IA só produz texto bonito sobre nada | Equipe técnica |
| Política de uso de IA homologada, com os limites da §6.5.2 implementados tecnicamente | SES-MT / TI / jurídico |
| Modelo digital de elevação e malha viária atualizada | Equipe técnica |
| Definição de quem revisa e assina o conteúdo gerado | SES-MT |

### 8.6.3 Riscos

| Risco | Probabilidade | Impacto | Mitigação |
| --- | --- | --- | --- |
| Confiança excessiva na saída da IA em decisão crítica | **Alta** | **Crítico** | Limites da §6.5.2 implementados em código, não apenas em norma; marcação de conteúdo gerado; nenhum caminho de código em que saída de modelo altere nível de alerta ou dispare envio |
| Alucinação em texto operacional | Média | Alto | IA opera apenas sobre indicadores já calculados, com os números injetados no contexto; revisão humana obrigatória |
| Simulação ser confundida com previsão de rompimento | Média | **Crítico** | Rótulo obrigatório em toda saída de cenário; reafirmação do escopo negativo de `docs/01-visao-geral.md` §1.2 |
| Custo e dependência de fornecedor de modelo | Média | Médio | Arquitetura desacoplada, com interface substituível |
| Dado individual chegar ao contexto do modelo | Baixa | **Crítico** | Segregação técnica: o serviço de IA não tem credencial para as tabelas identificáveis |

### 8.6.4 Critérios de aceite

| # | Critério |
| --- | --- |
| D1 | Todo texto gerado por IA é marcado, com data, modelo e versão do prompt |
| D2 | Nenhum caminho de código permite que saída de IA altere nível de alerta ou dispare envio |
| D3 | O serviço de IA não possui credencial de acesso a tabela com identificação individual |
| D4 | Toda saída de cenário traz o rótulo de simulação e a reafirmação de que o sistema não calcula probabilidade de rompimento |
| D5 | O SITREP gerado é aprovado por revisor humano identificado antes da distribuição |
| D6 | A projeção de demanda é comparada, após o evento, com o observado, e o desvio é registrado para calibração |

---

## 8.7 Marcos transversais a todas as fases

| Marco | Descrição | Fase |
| --- | --- | --- |
| Comitê técnico de validação | Especialistas em engenharia de barragens, hidrologia, meteorologia, epidemiologia, saúde ambiental, assistência, Defesa Civil e geoprocessamento, para validar os pesos do IDAP | Início da Fase 1 |
| Primeira recalibração dos pesos | Revisão da versão `0.1.0-metodologica` após operação real, conforme a governança da §3.11 | Fim da Fase 2 |
| Simulado com município | Exercício completo de alerta, confirmação e ficha rápida | Uma vez por fase, no mínimo |
| Plano de continuidade | Procedimento manual documentado para quando a plataforma estiver indisponível durante evento | Fase 1 |
| Revisão de limiares e faixas | Avaliação de falso positivo e falso negativo, com ajuste registrado | Semestral, a partir da Fase 2 |
| Auditoria de proteção de dados | Verificação das medidas da §6.6 | Anual, a partir da Fase 3 |

## 8.8 Sequência mínima recomendada

Se houver que escolher poucas coisas por escassez de equipe, esta é a ordem que maximiza
utilidade por esforço:

1. **Integrar o CNES.** É a fonte de saúde mais simples de integrar e destrava as dimensões C
   e D do IDAP, além das telas 1, 3 e 7.
2. **Coletar chuva.** INMET e GPM-IMERG são acessíveis e destravam a dimensão A, que vale 30
   pontos e hoje está inteiramente vazia.
3. **Cadastrar contatos institucionais.** Não exige tecnologia nenhuma, exige trabalho
   institucional, e sem isso nada do que for construído chega a ninguém.
4. **Obter manchas de inundação.** É o maior bloqueio da dimensão C e o de resolução mais
   demorada; começar cedo pela via institucional.
5. **Testar a ficha rápida em simulado.** Descobrir agora que o formulário não é preenchível
   custa uma tarde; descobrir durante um rompimento custa muito mais.
