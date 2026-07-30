# 5. VIGIPÓS-BARRAGENS — vigilância pós-desastre

> Fórmulas, limiares e pesos deste documento que não decorrem de norma ou de definição
> consagrada estão marcados como **proposta a validar**. As fórmulas do IPAPD e do IRS são
> propostas metodológicas desta especificação.

## 5.1 O que o módulo faz

O VIGIPÓS-BARRAGENS é acionado quando o evento deixa de ser risco e passa a ser fato. Ele
responde a três perguntas em sequência:

| Pergunta | Como responde |
| --- | --- |
| Quantas pessoas foram atingidas e como? | Ficha rápida + registros da Defesa Civil + atendimentos de urgência |
| A rede de saúde aguenta? | IPAPD — Índice de Pressão Assistencial Pós-Desastre |
| Está aparecendo doença acima do esperado? | Detecção estatística de excesso, comparada com a linha de base pré-desastre |
| A situação está voltando ao normal? | IRS — Índice de Recuperação Sanitária |

## 5.2 Gatilhos de ativação

| Gatilho | Definição operacional | Origem do sinal |
| --- | --- | --- |
| Rompimento confirmado | Ruptura total ou parcial da estrutura, confirmada pelo empreendedor, pelo órgão fiscalizador ou por verificação de campo | Regra R02 do IDAP |
| Inundação relevante | Área alagada atingindo ocupação humana, via estruturante ou serviço essencial | Sentinel-1, Defesa Civil, ficha rápida |
| Vazamento de rejeitos | Liberação de rejeito para fora do reservatório, com ou sem ruptura | Empreendedor, ANM, verificação de campo |
| Evacuação preventiva de grande porte | Evacuação determinada pela autoridade envolvendo mais de 100 pessoas (limiar **proposta a validar**) | Regra R05 do IDAP, Defesa Civil |
| Interrupção significativa de água | Suspensão de abastecimento afetando sistema urbano ou mais de 1.000 pessoas por mais de 12 h (limiares **propostas a validar**) | Regra R08, concessionária, Vigiagua |
| Interrupção de serviços de saúde | Unidade de saúde interditada, isolada ou sem condição de funcionamento | Regra R07, ficha rápida, gestor municipal |

A ativação é registrada como **evento** na base, com identificador próprio, e todos os
dados posteriores são vinculados a ele.

---

## 5.3 Linha de base pré-desastre

Nenhum excesso pode ser detectado sem uma referência. A linha de base é calculada
**antes** do desastre, em rotina, e congelada no momento da ativação do evento — para que
os dados do próprio desastre não contaminem a referência.

### 5.3.1 Unidades de análise

| Nível | Quando usar | Fonte da população |
| --- | --- | --- |
| Município | Sempre; é o nível com dado mais completo e estável | IBGE |
| Setor censitário | Quando a mancha atinge parte do município — evita diluir o sinal na população total | IBGE |
| Área potencialmente atingida (ZAS + ZSS) | Recorte principal do evento | Mancha × setor censitário |
| Região de saúde | Para indicadores assistenciais, porque a resposta é regionalizada | SES-MT |

### 5.3.2 Linha de base de mortalidade — SIM

| Grupo de causas | O que monitorar | Observação |
| --- | --- | --- |
| Mortalidade geral | Óbitos por todas as causas, por semana epidemiológica e por território | Base do cálculo de excesso de mortalidade |
| Causas externas | Capítulo XX da CID-10 | Grupo mais sensível ao desastre |
| Afogamentos | W65–W74 | Mortalidade direta do evento |
| Traumatismos | S00–T98 | |
| Doenças infecciosas e parasitárias | Capítulo I | Sensível ao pós-desastre |
| Doenças cardiovasculares | Capítulo IX | Sensível ao estresse agudo e à interrupção de tratamento |
| Doenças respiratórias | Capítulo X | Sensível a aspiração, umidade e aglomeração |
| Suicídios | X60–X84 | Sensível no médio prazo |
| Mortalidade infantil | Óbitos < 1 ano | Indicador sentinela de deterioração de condições de vida |
| Mortalidade por território | Todos os anteriores, desagregados por setor censitário de residência | Permite comparar área atingida e não atingida |

Limitação que define o uso: o SIM tem intervalo de meses entre ocorrência, investigação,
codificação e consolidação. **Serve para linha de base, excesso de mortalidade e análise de
médio e longo prazo. Não serve para alerta imediato.**

### 5.3.3 Linha de base de morbidade — SINAN

| Agravo | Por que é prioritário no pós-desastre |
| --- | --- |
| Leptospirose | Agravo mais característico de inundação; incubação de 1 a 30 dias, com pico em 7 a 14 dias |
| Acidentes com animais peçonhentos | Serpentes, escorpiões e aranhas deslocados pela água |
| Doenças transmitidas por água e alimentos | Diarreias, hepatite A, febre tifoide; primeiros dias após contaminação da água |
| Intoxicações exógenas | Rejeitos, produtos químicos, água contaminada, medicamentos deteriorados |
| Acidentes de trabalho | Equipes de resgate, limpeza e reconstrução |
| Tétano acidental | Ferimentos em ambiente contaminado por solo e lama |
| Violência | Interpessoal e autoprovocada; aumenta em situação de abrigo e de perda material |

Limitação que define o uso: o SINAN é insubstituível para vigilância, mas a **oportunidade
da notificação varia por agravo e por fluxo local**. Em um desastre, um atraso de três
semanas inviabiliza a resposta. Consequência: durante o evento e nas semanas seguintes o
SINAN é **complementado pela ficha rápida**, e a própria oportunidade da notificação passa a
ser indicador monitorado (§5.5.6).

### 5.3.4 Linha de base de capacidade — CNES

| Elemento | Detalhe a registrar |
| --- | --- |
| Unidades | Estabelecimento, tipo, coordenada, distância à mancha, via de acesso |
| Equipes | Equipes de Saúde da Família, de Saúde Bucal, NASF, eSB, com território adscrito |
| Leitos | Por tipo: clínico, cirúrgico, obstétrico, pediátrico, UTI adulto, UTI pediátrica, UTI neonatal, isolamento |
| Equipamentos | Raio-X, tomógrafo, ultrassom, ventilador, concentrador de oxigênio, autoclave, rede de frio |
| Serviços especializados | Diálise, hemoterapia, oncologia, radiologia, laboratório |
| Profissionais | Por categoria e por carga horária |
| Ambulâncias | Por tipo (básica, avançada), por base |
| Capacidade instalada | Consolidação por município e por região de saúde |

Limitação que define o uso: o CNES informa **capacidade cadastrada** com atualização
mensal. Precisa ser complementado por informação operacional do momento — unidade
funcionando ou interditada, profissionais presentes, leitos realmente disponíveis, estoque,
energia, água, oxigênio, acesso viário. É a razão de existir o bloco "Serviços" da ficha
rápida.

---

## 5.4 Ficha rápida de saúde pós-desastre

Instrumento de coleta ativa, aplicado pelo município. Cadência proposta: **duas vezes ao
dia** nas primeiras 72 h, **diária** até o 15º dia, **semanal** até o encerramento do evento
(**proposta a validar**).

Convenções da coluna Obrigatoriedade: **O** = obrigatório; **C** = condicional (obrigatório
se a condição for satisfeita); **F** = facultativo.

### 5.4.1 Bloco 1 — Evento

| Campo | Tipo de dado | Obrig. | Observação |
| --- | --- | --- | --- |
| Identificador do evento | Texto (chave) | O | Gerado na ativação |
| Município | Código IBGE (lista) | O | |
| Localidade | Texto livre | O | Bairro, distrito, comunidade, assentamento |
| Coordenadas da localidade | Decimal (lat, lon) | O | Captura por GPS do dispositivo, com precisão registrada |
| Data e hora do preenchimento | Data e hora (UTC-4) | O | Automático |
| Data e hora de referência dos dados | Data e hora (UTC-4) | O | Pode diferir do preenchimento |
| Nome e cargo do informante | Texto | O | Responsabilidade sobre o dado |
| População atingida (estimativa) | Inteiro >= 0 | O | Estimativa do informante |
| Desalojados | Inteiro >= 0 | O | Fora de casa, em domicílio de terceiros |
| Desabrigados | Inteiro >= 0 | O | Em abrigo público |
| Desaparecidos | Inteiro >= 0 | O | |
| Resgatados | Inteiro >= 0 | O | |
| Óbitos preliminares | Inteiro >= 0 | O | Explicitamente preliminar; não substitui o SIM |
| Pessoas isoladas | Inteiro >= 0 | O | Sem via de acesso terrestre |
| Localidades isoladas | Inteiro >= 0 | O | |
| Situação do acesso à localidade | Lista: livre / restrito / interrompido | O | |
| Observações | Texto livre | F | |

### 5.4.2 Bloco 2 — Saúde

| Campo | Tipo de dado | Obrig. | Observação |
| --- | --- | --- | --- |
| Feridos leves | Inteiro >= 0 | O | Atendimento ambulatorial |
| Feridos graves | Inteiro >= 0 | O | Necessidade de internação ou remoção |
| Afogamentos (não fatais) | Inteiro >= 0 | O | |
| Casos de hipotermia | Inteiro >= 0 | O | |
| Casos de intoxicação | Inteiro >= 0 | O | |
| Casos de diarreia | Inteiro >= 0 | O | Sinal sindrômico, não diagnóstico |
| Casos de febre | Inteiro >= 0 | O | |
| Casos com sintomas respiratórios | Inteiro >= 0 | O | |
| Casos de lesão de pele | Inteiro >= 0 | O | Dermatite de contato, ferimento infectado |
| Casos de sofrimento psíquico agudo | Inteiro >= 0 | O | |
| Pessoas com interrupção de medicamento de uso contínuo | Inteiro >= 0 | O | Hipertensão, diabetes, epilepsia, saúde mental, tuberculose, HIV |
| Gestantes de risco identificadas | Inteiro >= 0 | O | |
| Pacientes dependentes de oxigênio | Inteiro >= 0 | O | Requer energia e logística |
| Pacientes em diálise | Inteiro >= 0 | O | Requer transporte e vaga em serviço |
| Pessoas com mobilidade reduzida | Inteiro >= 0 | O | Determina a logística de evacuação |
| Encaminhamentos realizados | Inteiro >= 0 | F | |
| Necessidade de remoção aeromédica | Inteiro >= 0 | C | Se houver paciente grave em localidade isolada |

### 5.4.3 Bloco 3 — Serviços

| Campo | Tipo de dado | Obrig. | Observação |
| --- | --- | --- | --- |
| Unidades de saúde abertas | Inteiro >= 0 | O | |
| Unidades de saúde fechadas | Inteiro >= 0 | O | |
| Unidades de saúde danificadas | Inteiro >= 0 | O | Dano estrutural, com ou sem funcionamento |
| Unidades sem água | Inteiro >= 0 | O | |
| Unidades sem energia | Inteiro >= 0 | O | |
| Unidades sem acesso viário | Inteiro >= 0 | O | |
| Leitos disponíveis | Inteiro >= 0 | O | Vagos e operacionais, não cadastrados |
| Leitos de UTI disponíveis | Inteiro >= 0 | O | |
| Ambulâncias operacionais | Inteiro >= 0 | O | |
| Profissionais disponíveis | Inteiro >= 0 | O | Efetivamente presentes no turno |
| Profissionais previstos na escala | Inteiro >= 0 | O | Denominador do indicador de indisponibilidade |
| Autonomia de energia (horas) | Decimal >= 0 | O | Gerador e combustível |
| Autonomia de água (horas) | Decimal >= 0 | O | Reservatório e reposição |
| Autonomia de oxigênio (horas) | Decimal >= 0 | O | |
| Estoque crítico em falta | Múltipla escolha | O | Soro antiofídico, antibiótico, analgésico, insulina, hipoclorito, soro de reidratação, material de sutura, kit de higiene |
| Serviços essenciais interrompidos na unidade | Múltipla escolha | O | Laboratório, imagem, diálise, rede de frio, esterilização, farmácia |
| Necessidade de reforço | Texto estruturado + inteiro | O | Categoria (profissional, veículo, insumo, energia, água, oxigênio) e quantidade |
| Rede de frio comprometida | Booleano | O | Perda de imunobiológicos |

### 5.4.4 Bloco 4 — Água e ambiente

| Campo | Tipo de dado | Obrig. | Observação |
| --- | --- | --- | --- |
| Abastecimento de água interrompido | Booleano | O | |
| População sem abastecimento | Inteiro >= 0 | C | Se o abastecimento estiver interrompido |
| Horas de desabastecimento acumuladas | Decimal >= 0 | C | |
| Captação comprometida | Booleano | O | |
| Identificação da captação | Texto / código Sisagua | C | Se comprometida |
| Suspeita de contaminação da água | Booleano | O | |
| Amostras coletadas | Inteiro >= 0 | O | |
| Resultado de amostras — coliformes totais | Lista: ausente / presente / pendente | C | Se houver amostra |
| Resultado de amostras — *E. coli* | Lista: ausente / presente / pendente | C | |
| Turbidez medida (uT) | Decimal >= 0 | C | |
| Cloro residual livre (mg/L) | Decimal >= 0 | C | |
| Contaminante químico suspeito | Múltipla escolha | C | Mercúrio, arsênio, cianeto, metais pesados, hidrocarbonetos, agrotóxico |
| Presença de lama ou rejeito | Lista: ausente / pontual / extensa | O | |
| Mortalidade de animais observada | Lista: não / peixes / animais domésticos / animais silvestres / múltipla | O | Sinal sentinela de contaminação |
| Produtos químicos envolvidos no evento | Texto livre | C | |
| Necessidade de água potável (litros/dia) | Inteiro >= 0 | O | Base do cálculo logístico |
| Soluções alternativas em uso | Múltipla escolha | O | Caminhão-pipa, poço, fonte, água engarrafada, tratamento domiciliar |
| Distribuição de hipoclorito realizada | Booleano | O | |

### 5.4.5 Regras de qualidade da ficha

| Regra | Motivo |
| --- | --- |
| Nenhum campo numérico aceita valor negativo | Erro de digitação |
| Desabrigados <= população atingida | Consistência interna |
| Leitos de UTI disponíveis <= leitos disponíveis | Consistência interna |
| Profissionais disponíveis <= profissionais previstos, salvo justificativa | Reforço externo é possível, mas deve ser declarado |
| Toda ficha é versionada, nunca sobrescrita | Auditoria e reconstrução da série |
| Divergência acima de 50% em relação à ficha anterior gera alerta de validação | Detecta erro de preenchimento em tempo de coleta |

---

## 5.5 Indicadores pós-desastre

### 5.5.1 Mortalidade e lesões

| Indicador | Fórmula | Unidade | Fonte |
| --- | --- | --- | --- |
| Taxa de mortalidade pelo desastre | óbitos atribuídos ao desastre ÷ população atingida × 100.000 | por 100 mil | Ficha rápida (preliminar), SIM (definitivo) |
| Letalidade entre vítimas | óbitos ÷ vítimas identificadas × 100 | % | Ficha rápida, SAMU, SIH |
| Taxa de trauma grave | traumas graves ÷ população atingida × 10.000 | por 10 mil | Ficha rápida, SIH, SAMU |
| Taxa de hospitalização | internações relacionadas ao evento ÷ população atingida × 10.000 | por 10 mil | SIH, movimentação hospitalar |
| Proporção de desaparecidos | desaparecidos ÷ população exposta × 100 | % | Ficha rápida, Defesa Civil |
| Tempo médio de resgate | soma dos tempos de resgate ÷ número de pessoas resgatadas | minutos | SAMU, Bombeiros, Defesa Civil |

Observação sobre os denominadores: "população atingida" e "população exposta" são grandezas
diferentes. **Exposta** é quem estava na área de risco; **atingida** é quem sofreu efeito.
Usar o denominador errado altera a taxa por ordens de grandeza, então cada indicador deve
carregar explicitamente qual denominador usou.

### 5.5.2 Vigilância epidemiológica

| Indicador | Fórmula | Unidade |
| --- | --- | --- |
| Razão observado/esperado (O/E) | casos observados no período ÷ casos esperados pela linha de base | razão |
| Excesso de casos | casos observados − limite superior do intervalo esperado | casos |
| Incidência em abrigos | casos em abrigados ÷ população abrigada × 1.000 | por mil |
| Positividade laboratorial | exames positivos ÷ exames realizados × 100 | % |
| Tempo entre sintomas e notificação | mediana de (data de notificação − data de início dos sintomas) | dias |
| Proporção investigada em 24 h | casos com investigação iniciada em <= 24 h ÷ casos notificados × 100 | % |
| Número de sinais sindrômicos ativos | contagem de síndromes com O/E acima do limite | contagem |

### 5.5.3 Síndromes de vigilância sindrômica recomendadas

| Síndrome | Definição operacional proposta | Principais agravos rastreados |
| --- | --- | --- |
| **Diarreica** | 3 ou mais evacuações líquidas em 24 h | Doenças de transmissão hídrica e alimentar, cólera, rotavírus |
| **Febril** | Febre referida ou medida >= 37,8 °C sem foco definido | Leptospirose, arboviroses, infecções bacterianas |
| **Febril-ictérica** | Febre com icterícia | Leptospirose, hepatites virais, febre amarela, malária |
| **Respiratória** | Tosse, dispneia ou dor torácica de início recente | Pneumonia aspirativa, infecção respiratória aguda, agudização de asma e DPOC |
| **Dermatológica** | Lesão de pele de início após o evento | Dermatite de contato, celulite, larva migrans, escabiose em abrigos |
| **Neurológica** | Cefaleia intensa, alteração de consciência, convulsão, déficit focal | Meningite, intoxicação por metais, trauma cranioencefálico, interrupção de anticonvulsivante |
| **Intoxicação** | Sintomas compatíveis com exposição química | Rejeitos, cianeto, mercúrio, agrotóxicos, medicamento deteriorado |
| **Traumática** | Ferimento, fratura, contusão relacionados ao evento ou à limpeza | Trauma, tétano acidental, acidente de trabalho |
| **Sofrimento mental agudo** | Ansiedade intensa, insônia, ideação suicida, reação aguda ao estresse | Transtorno de estresse pós-traumático, luto, agudização psiquiátrica |

Cada síndrome tem sua própria linha de base e seu próprio limite superior esperado. Um
sinal sindrômico é um **alerta para investigação**, não um diagnóstico coletivo.

### 5.5.4 Água e saneamento

| Indicador | Fórmula | Unidade |
| --- | --- | --- |
| Percentual de sistemas interrompidos | sistemas de abastecimento interrompidos ÷ sistemas cadastrados na área × 100 | % |
| População sem água segura | soma da população sem abastecimento ou sem água potável comprovada | pessoas |
| Captações afetadas | contagem de captações comprometidas | contagem |
| Percentual de amostras fora do padrão | amostras fora do padrão de potabilidade ÷ amostras analisadas × 100 | % |
| Positividade para coliformes totais | amostras com coliformes presentes ÷ amostras analisadas × 100 | % |
| Positividade para *E. coli* | amostras com *E. coli* presente ÷ amostras analisadas × 100 | % |
| Turbidez acima do padrão | amostras com turbidez > 5 uT ÷ amostras analisadas × 100 | % |
| Contaminantes químicos prioritários detectados | contagem de contaminantes acima do valor máximo permitido | contagem |
| Dias de desabastecimento | soma dos dias com abastecimento interrompido por localidade | dias |
| Litros de água segura por pessoa por dia | volume distribuído ÷ população atendida ÷ dias | L/pessoa/dia |
| Cobertura de inspeção sanitária | soluções de abastecimento inspecionadas ÷ soluções existentes × 100 | % |
| Tempo de restabelecimento | horas entre a interrupção e o restabelecimento comprovado | horas |

Parâmetro de referência para o volume mínimo: 15 L/pessoa/dia em situação de emergência,
com meta de 50 L/pessoa/dia (**proposta a validar** com a Vigilância da Qualidade da Água e
a Defesa Civil, com base nas referências humanitárias internacionais).

### 5.5.5 Rede assistencial — IPAPD

O **IPAPD (Índice de Pressão Assistencial Pós-Desastre)** mede, de 0 a 1, quanto uma unidade
ou região está pressionada. É calculado por unidade e agregado por município e por região de
saúde (média ponderada pela população de referência).

```
IPAPD = 0,25 · O  +  0,20 · A  +  0,15 · P  +  0,15 · E  +  0,15 · C  +  0,10 · S
```

Os pesos somam 1,00 e são **propostas a validar**.

| Termo | Nome | Normalização proposta para 0–1 | Interpretação de 0 e de 1 |
| --- | --- | --- | --- |
| **O** | Ocupação | `O = limitar[(taxa de ocupação de leitos − 0,70) ÷ 0,30 ; 0 ; 1]` | 0 = ocupação de 70% ou menos (sem pressão); 1 = ocupação de 100% ou mais |
| **A** | Aumento de atendimentos | `A = limitar[(atendimentos observados ÷ média esperada − 1) ÷ 1,00 ; 0 ; 1]` | 0 = volume igual ou abaixo do esperado; 1 = volume dobrado ou mais |
| **P** | Indisponibilidade de profissionais | `P = limitar[1 − (profissionais presentes ÷ profissionais previstos na escala) ; 0 ; 1]` | 0 = escala completa; 1 = nenhum profissional presente |
| **E** | Perda de acesso | `E = população da área de cobertura sem rota transitável até a unidade ÷ população da área de cobertura` | 0 = todos alcançam a unidade; 1 = unidade inalcançável |
| **C** | Autonomia crítica | `C = limitar[1 − (menor autonomia entre energia, água e oxigênio, em horas ÷ 72) ; 0 ; 1]` | 0 = 72 h ou mais de autonomia em tudo; 1 = algum insumo crítico esgotado |
| **S** | Interrupção de serviços | `S = serviços essenciais interrompidos ÷ serviços essenciais habilitados na unidade (CNES)` | 0 = todos os serviços operando; 1 = todos interrompidos |

`limitar[x ; a ; b]` significa truncar x ao intervalo [a, b].

Interpretação da escala (**proposta a validar**):

| IPAPD | Situação | Ação |
| --- | --- | --- |
| < 0,25 | Operação normal | Monitoramento |
| 0,25 a < 0,50 | Pressão moderada | Reforço pontual, acompanhamento de 12 h |
| 0,50 a < 0,75 | Pressão alta | Reforço de equipe e insumo; abrir remanejamento pela regulação |
| >= 0,75 | Saturação | Redirecionar demanda, acionar apoio regional, considerar unidade de campanha |

Por que os pesos: **ocupação (0,25)** é o gargalo mais direto e imediato; **aumento de
atendimentos (0,20)** é o que antecede a saturação e permite antecipá-la;
**indisponibilidade de profissionais, perda de acesso e autonomia crítica (0,15 cada)** são
os três modos de falha que tornam a capacidade nominal irrelevante; **interrupção de
serviços (0,10)** é grave mas geralmente compensável por referência a outra unidade.

### 5.5.6 Abrigos

| Indicador | Fórmula ou definição | Unidade |
| --- | --- | --- |
| Abrigos ativos | contagem de abrigos em funcionamento | contagem |
| Ocupação | pessoas abrigadas | pessoas |
| Lotação máxima | capacidade cadastrada do abrigo | pessoas |
| Taxa de lotação | ocupação ÷ lotação máxima × 100 | % |
| Densidade por área | área útil ÷ pessoas abrigadas | m²/pessoa (referência mínima: 3,5 m²/pessoa, **a validar**) |
| Banheiros por pessoa | pessoas abrigadas ÷ banheiros funcionais | pessoas/banheiro (referência: <= 20, **a validar**) |
| Disponibilidade de água | litros de água potável ÷ pessoas abrigadas ÷ dia | L/pessoa/dia |
| Incidência de diarreia no abrigo | casos de diarreia ÷ pessoas abrigadas × 1.000 | por mil |
| Incidência de sintomas respiratórios | casos ÷ pessoas abrigadas × 1.000 | por mil |
| Incidência de doenças de pele | casos ÷ pessoas abrigadas × 1.000 | por mil |
| Pessoas com necessidades especiais | contagem por tipo de necessidade | contagem |
| Gestantes abrigadas | contagem | contagem |
| Idosos abrigados | contagem (>= 60 anos) | contagem |
| Crianças abrigadas | contagem (< 12 anos) e (< 5 anos) | contagem |
| Cobertura vacinal verificada | pessoas com situação vacinal avaliada ÷ pessoas abrigadas × 100 | % |
| Atendimentos de saúde mental | atendimentos realizados ÷ pessoas abrigadas × 100 | % |
| Incidentes de violência registrados | contagem por tipo | contagem |

### 5.5.7 Recuperação — IRS

O **IRS (Índice de Recuperação Sanitária)** mede, de 0 a 1, quanto do funcionamento normal
foi restabelecido. Diferente do IPAPD, aqui **1 é bom**.

```
IRS = média das onze dimensões normalizadas de 0 a 1
```

Pesos iguais (1/11 ≈ 0,0909 cada) como ponto de partida — **proposta a validar**; o painel
de especialistas pode redistribuir.

| Dimensão | Normalização proposta (0 = não recuperado, 1 = recuperado) |
| --- | --- |
| Restabelecimento da APS | equipes de APS em funcionamento ÷ equipes existentes antes do evento |
| Funcionamento hospitalar | leitos operacionais ÷ leitos operacionais antes do evento |
| Retorno do abastecimento de água | população com abastecimento restabelecido e água dentro do padrão ÷ população afetada |
| Acesso rodoviário | vias estruturantes transitáveis ÷ vias estruturantes afetadas |
| Retorno das equipes | profissionais presentes ÷ profissionais previstos na escala |
| Redução da população em abrigos | 1 − (pessoas ainda abrigadas ÷ pico de pessoas abrigadas) |
| Controle dos agravos | proporção das síndromes monitoradas com O/E dentro do limite esperado |
| Recuperação da rede de frio | unidades com rede de frio operante e validada ÷ unidades com rede de frio |
| Continuidade dos tratamentos | pacientes crônicos com tratamento retomado ÷ pacientes com tratamento interrompido |
| Acompanhamento de saúde mental | pessoas em acompanhamento ÷ pessoas identificadas com necessidade |
| Monitoramento ambiental | pontos de monitoramento com resultado dentro do padrão ÷ pontos monitorados |

Critério proposto de encerramento do evento: **IRS >= 0,90 mantido por 4 semanas
consecutivas**, sem sinal sindrômico ativo e sem pendência crítica em aberto
(**proposta a validar**).

---

## 5.6 Detecção automática de excesso de agravos

### 5.6.1 Princípio inegociável

A detecção de excesso é feita por **algoritmo estatístico reproduzível**, com parâmetros
declarados e resultado auditável. Rodar o mesmo algoritmo sobre os mesmos dados produz
sempre o mesmo sinal.

**A inteligência artificial pode explicar o sinal, não produzi-lo.** A IA redige a
narrativa ("houve 12 casos de leptospirose contra 1,8 esperado, concentrados em duas
localidades atingidas pela mancha, com início de sintomas compatível com a data do
evento"), sugere hipóteses e prioriza a investigação. Ela não decide que existe surto, não
substitui o teste estatístico e não é a fonte do número. A razão é simples: um sinal
epidemiológico é ato de vigilância com consequência sanitária e jurídica, e precisa ser
reproduzível e defensável — propriedade que um modelo generativo não oferece.

### 5.6.2 Referências de comparação

Um mesmo agravo deve ser comparado contra mais de uma referência, porque cada uma falha de
um modo diferente.

| Referência | Como se calcula | Falha quando |
| --- | --- | --- |
| Média histórica | Média dos casos no mesmo período em anos anteriores | A série tem tendência ou surtos passados que inflam a média |
| Mediana histórica | Mediana no mesmo período | Perde informação sobre variabilidade |
| Semanas epidemiológicas equivalentes | Comparação com a mesma SE de anos anteriores | Sazonalidade deslocada por variação climática |
| Municípios-controle não atingidos | Municípios pareados por porte, perfil e região, fora da mancha | Não há controle comparável, ou o controle também foi afetado |
| Limite superior esperado | Percentil 95 ou limite superior do canal endêmico | Série curta ou com muitos zeros |
| Modelo de série temporal | Previsão contrafactual a partir da série pré-evento | Série curta; mudança de definição de caso |

### 5.6.3 Métodos e quando usar cada um

| Método | O que faz | Quando usar | Limitação |
| --- | --- | --- | --- |
| **Canal endêmico** | Faixa esperada por semana epidemiológica, a partir de média e desvio de anos anteriores | Primeira linha, agravo com sazonalidade conhecida e série de 5 anos ou mais (leptospirose, diarreia) | Requer série longa e estável; sensível a surtos passados incluídos na referência |
| **CUSUM** | Soma cumulativa dos desvios; detecta mudança pequena e persistente | Monitoramento contínuo de síndrome com contagem baixa; detecção precoce | Sensível à escolha do parâmetro de referência; pode acumular ruído |
| **EWMA** | Média móvel com peso exponencial; detecta mudança gradual | Vigilância sindrômica de rotina em abrigos e pronto-socorro | Suaviza picos abruptos, que é justamente o que interessa em desastre |
| **Regressão de Poisson** | Modela contagem esperada com tendência, sazonalidade e população | Agravo com contagem moderada e denominador conhecido | Assume variância igual à média; falha com superdispersão |
| **Regressão binomial negativa** | Como Poisson, mas admite superdispersão | Padrão para dado de notificação, que quase sempre é superdisperso | Requer mais dados para estimar o parâmetro extra |
| **Modelos bayesianos** | Estimativa com incerteza explícita e uso de informação a priori | Área pequena, contagem muito baixa, necessidade de suavização espacial | Exige especificação de priori, que precisa ser justificada |
| **Controle sintético** | Constrói um "município contrafactual" ponderando municípios-controle | Avaliação de impacto do desastre com um único município atingido | Requer vários controles e período pré-evento longo |
| **Séries temporais interrompidas** | Compara nível e tendência antes e depois de uma data de corte | Avaliação de impacto retrospectiva, com data de evento bem definida | Não serve para detecção em tempo quase real |

Recomendação operacional:

| Situação | Método recomendado |
| --- | --- |
| Detecção diária durante o evento, síndromes | EWMA + CUSUM em paralelo, com canal endêmico como contexto |
| Detecção semanal de agravo de notificação | Canal endêmico como triagem, binomial negativa para confirmar |
| Contagem muito baixa em área pequena | Modelo bayesiano com suavização espacial |
| Avaliação do impacto, meses depois | Séries temporais interrompidas e controle sintético |
| Comparação com território não atingido | Municípios-controle pareados, com binomial negativa |

### 5.6.4 Exemplo trabalhado — leptospirose

| Elemento | Valor |
| --- | --- |
| Agravo | Leptospirose |
| Janela de observação | 7 dias |
| Casos observados | **12** |
| Casos esperados pela linha de base histórica | **1,8** |
| Limite superior do intervalo esperado | **4** |
| Razão observado/esperado (O/E) | 12 ÷ 1,8 = **6,7** |
| Excesso de casos | 12 − 4 = **8 casos acima do limite superior** |
| Classificação | **Sinal epidemiológico crítico** |

Leitura: o observado é quase sete vezes o esperado e ultrapassa em 8 casos o limite superior
do intervalo de normalidade. Não é variação aleatória plausível.

Ações automáticas disparadas por um sinal crítico (**proposta a validar**):

1. Notificar CIEVS estadual e Vigilância Epidemiológica municipal em até 1 h.
2. Iniciar investigação de campo dos 12 casos, com busca ativa nas localidades de residência.
3. Solicitar confirmação laboratorial ao LACEN e acompanhar a positividade.
4. Revisar a cobertura de quimioprofilaxia nos grupos de exposição (equipes de limpeza,
   moradores em contato com lama e água contaminada).
5. Reforçar a comunicação de risco sobre contato com água de enchente.
6. Verificar a situação do abastecimento de água nas localidades dos casos.
7. Registrar o sinal no evento, com o método usado, os parâmetros e a data — para auditoria.

O que a IA faz neste exemplo: redige o parágrafo interpretativo para o boletim, cruza os
casos com a mancha e com as localidades de abrigo, aponta que a distribuição temporal do
início de sintomas é compatível com o período de incubação a partir da data do evento e
lista as pendências de investigação. O número 6,7 e a classificação "crítico" vêm do
algoritmo, não do modelo de linguagem.

---

## 5.7 Cadência de produtos do módulo

| Produto | Cadência na fase aguda | Cadência na recuperação | Responsável |
| --- | --- | --- | --- |
| SITREP | A cada 6 h nas primeiras 72 h, depois diário | Semanal | COE / Sala de Situação |
| Boletim epidemiológico do evento | Diário | Semanal | Vigilância Epidemiológica |
| Painel de IPAPD | Contínuo, atualizado a cada ficha | Diário | Plataforma |
| Relatório de abrigos | Diário | Semanal | Assistência Social + Vigilância |
| Boletim de qualidade da água | Diário | Semanal | Vigiagua |
| IRS | Semanal | Semanal | Plataforma |
| Relatório pós-desastre consolidado | — | Ao encerramento, com revisão dos planos | Vigidesastres / SES-MT |
