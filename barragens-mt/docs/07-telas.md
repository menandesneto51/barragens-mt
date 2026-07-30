# 7. Telas da plataforma

Oito telas, cada uma com um público e uma pergunta que responde. A regra de projeto é:
**uma tela, uma decisão**. Se a tela não muda nenhuma decisão de ninguém, ela não deve existir.

Cada seção traz, ao final, um quadro de **viabilidade hoje** separando o que é construível com
os dados já coletados (SNISB 1.248, SIGBM 183, IBGE 142 municípios) do que depende de
integração futura.

Legenda de viabilidade:

| Marca | Significado |
| --- | --- |
| ✅ | Viável hoje com os dados de `dados/tratados/` |
| ⚠️ | Parcialmente viável — funciona, mas com lacuna conhecida de qualidade ou cobertura |
| ⛔ | Depende de integração ainda inexistente |

---

## 7.1 Tela 1 — Comando estadual

| Aspecto | Definição |
| --- | --- |
| Propósito | Responder, em uma tela, "como está Mato Grosso agora e onde devo olhar primeiro" |
| Público-alvo | Secretário de Estado de Saúde, superintendências, coordenação do CIEVS, coordenação estadual da Defesa Civil |
| Granularidade | Estado, com recorte por região de saúde |
| Tecnologia | Power BI (§6.1.1) |
| Atualização | Horária; 15 min quando houver barragem em Laranja ou acima |

### Widgets e indicadores

| Widget | Indicador exibido | Fonte | Granularidade |
| --- | --- | --- | --- |
| Cartão | Barragens monitoradas | SNISB (1.248) + SIGBM (183) | Estado |
| Cartão | Alertas ativos por faixa (Verde/Amarelo/Laranja/Vermelho/Roxo) | `calculo_idap`, `alerta` | Estado |
| Cartão | Municípios ameaçados | `exposto` × `municipio` | Contagem |
| Cartão | População potencialmente exposta | Setor censitário × mancha | Pessoas |
| Cartão | Unidades de saúde ameaçadas | CNES × mancha | Contagem, com destaque para hospital e UPA |
| Mapa | Barragens por faixa de IDAP, sobre a malha municipal | `barragem`, `calculo_idap`, malha IBGE | Ponto sobre polígono |
| Mapa de calor | Chuva acumulada 24h e 72h nas bacias | INMET, Cemaden, ANA, GPM-IMERG | Bacia / pixel 0,1° |
| Semáforo | Nível de prontidão estadual (maior faixa vigente + número de barragens por faixa) | `calculo_idap` | Estado |
| Tabela | Top 10 barragens por IDAP, com município, faixa, completude e regras disparadas | `calculo_idap` | Barragem |
| Barra | Frescor das fontes (idade do dado mais recente por fonte) | Registro de proveniência (§6.2.1) | Fonte |

### Filtros

Região de saúde · município · órgão fiscalizador · faixa de IDAP · categoria de risco ·
dano potencial · tipo de barragem (água / rejeito) · janela temporal.

### Viabilidade hoje

| Elemento | Situação |
| --- | --- |
| Contagem de barragens, mapa de pontos, distribuição por CRI/DPA/classe | ✅ |
| Recorte por município e por região de saúde | ⚠️ falta a tabela `regiao_saude`; o vínculo município→região de saúde precisa ser carregado da SES-MT |
| Frescor das fontes | ⚠️ os coletores gravam data de extração; falta consolidar em métrica |
| Faixa de IDAP por barragem | ✅ `painel/index.html` (etapa 20) consome `idap_estadual_mt.csv` |
| Chuva 24/72 h (proxy sede+montante) | ✅ via SisClima/TITAN (`17_hidro_sisclima_titan.py`) |
| Alertabilidade | ⚠️ esqueleto de contatos (19); quase todas ainda não alertáveis |
| População exposta, unidades ameaçadas | ⚠️ C3 proxy CNES no eixo Cuiabá; mancha oficial ainda ⛔ |
| Entrega multicanal de alerta | ⛔; confirmação local em `painel/confirmacao_alerta.html` |

---

## 7.2 Tela 2 — Monitoramento ambiental

| Aspecto | Definição |
| --- | --- |
| Propósito | Acompanhar a pressão hidroclimática que alimenta a dimensão A do IDAP e antecipar agravamento |
| Público-alvo | Analistas da Sala de Situação, Cemaden estadual, Defesa Civil, SEMA-MT, meteorologia |
| Granularidade | Estação, pixel de satélite, bacia |
| Tecnologia | WebGIS + banco de séries temporais (§6.1.1) |
| Atualização | 30 min (IMERG), 1 h (INMET), 10 min a 1 h (Cemaden), 1 h a 24 h (ANA) |

### Widgets e indicadores

| Widget | Indicador | Fonte | Periodicidade / latência |
| --- | --- | --- | --- |
| Mapa de estações | Estações automáticas do INMET, com chuva horária, temperatura, umidade, pressão, vento e rajada | `https://apitempo.inmet.gov.br/` | horária / ~1 h |
| Mapa de pluviômetros | Chuva acumulada e intensidade nos pluviômetros do Cemaden | `http://sjc.salvar.cemaden.gov.br/resources/dados/` | 10 min a 1 h / minutos a 1 h |
| Mapa de estações fluviométricas | Nível, vazão, cota de alerta e cota de inundação (ANA / Rede Hidrometeorológica Nacional) | `https://www.snirh.gov.br/hidrotelemetria/` e API HidroWeb | 1 h a 24 h / 1 h a dias |
| Mosaico de satélite | Chuva por pixel a cada 30 min (GPM-IMERG Early Run) e acumulados de 1/3/6/12/24/72 h | `https://gpm.nasa.gov/data` · GES DISC | 30 min / ~4 h (Early) e ~14 h (Late) |
| Painel de previsão | Chuva prevista 24–72 h e previsão de risco geo-hidrológico | Cemaden, INMET, GloFAS | diária a 6 h |
| Série temporal | Chuva acumulada por bacia, com limiar de atenção marcado | Composto | 30 min |
| Indicador derivado | Percentual da bacia acima do limiar; chuva máxima localizada; anomalia frente à climatologia; persistência de chuva intensa; saturação antecedente estimada | Calculado (`docs/02-fontes-de-dados.md` §2.4.1) | 30 min a 1 h |
| Comparador de imagens | Sentinel-1 (radar) e Sentinel-2 / Landsat / CBERS (óptico), antes e depois | Copernicus Data Space, USGS, INPE | 6 a 12 dias (S1), 5 dias (S2) / horas a dias |
| Aviso de cobertura | Data e hora da última passagem orbital útil por barragem, com aviso de nuvem para os ópticos | Metadado das imagens | por passagem |

### Filtros

Bacia · região hidrográfica · município · barragem · janela (1/3/6/12/24/72 h) ·
fonte (terrestre / satélite) · limiar.

### Ressalva permanente na tela

Um rodapé fixo deve informar: *"Sentinel-1 e Sentinel-2 não são sensores contínuos da
barragem. A disponibilidade depende do horário da passagem orbital, da área coberta, da
latência e do processamento. Não substituem piezômetros, inclinômetros, medidores de vazão,
sensores de nível, inspeções técnicas nem telemetria do empreendedor."*

### Viabilidade hoje

| Elemento | Situação |
| --- | --- |
| Todo o conteúdo desta tela | ⚠️ choropleth municipal SisClima/TITAN em `painel/hidro.html` (etapa 21); sem estações pontuais nem IMERG neste painel |
| Localização das barragens para associar a estações e pixels | ✅ coordenadas de 1.248 barragens já disponíveis |
| Delimitação de bacia contribuinte por barragem | ⚠️ proxy Otto sede+montante na etapa 17; MDE/BHO areal ainda ⛔ |

---

## 7.3 Tela 3 — Barragem 360°

| Aspecto | Definição |
| --- | --- |
| Propósito | Reunir, em uma página por estrutura, tudo o que se sabe sobre ela — a tela de referência para decisão sobre uma barragem específica |
| Público-alvo | Analistas da Sala de Situação, Defesa Civil, órgão fiscalizador, vigilância municipal |
| Granularidade | Uma barragem |
| Tecnologia | WebGIS + Python (composição) |
| Atualização | Cadastro: diária a mensal. Séries: 30 min a 1 h |

### Widgets e indicadores

| Bloco | Conteúdo | Fonte |
| --- | --- | --- |
| Identificação | Nome, id SNISB, empreendedor, órgão fiscalizador, município, coordenadas, uso principal, tipo de material, altura, capacidade, fase de vida | SNISB |
| Classificação | CRI, DPA, classe CNRH, regulada pelo PNSB, nível de perigo, possui PAE, plano de segurança, revisão periódica, barragem autuada | SNISB |
| Classificação (mineração) | Nível de emergência, status DCE (RISR e RPSB), status da DCO, necessita PAEBM, cópias do PAEBM entregues, fase da descaracterização, presença de cianeto, minério principal | SIGBM |
| Engenharia (mineração) | Método construtivo, tipo de alteamento, instrumentação, volume atual do reservatório | SIGBM |
| Inspeções | Data e tipo da última inspeção, dias desde a inspeção, histórico | SNISB |
| Sensores | Piezômetro, inclinômetro, medidor de vazão, régua de nível, situação da transmissão, última leitura | Empreendedor (**a validar** — não há integração) |
| Anomalias | Percolação, deformações e recalque, deterioração de taludes, drenagem interna, confiabilidade do extravasor | SIGBM (autodeclarado) |
| Chuva na bacia | Acumulados 24 h e 72 h, previsão 24–72 h, percentil climatológico, saturação antecedente | INMET, Cemaden, ANA, IMERG |
| Nível e vazão | Nível do reservatório, nível do rio a jusante, vazão, cotas de referência | ANA, empreendedor |
| Histórico | Série do IDAP nos últimos 30, 90 e 365 dias; mudanças de classificação; alertas emitidos | `calculo_idap`, `classificacao`, `alerta` |
| Mancha | ZAS, ZSS, cenários, tempo de chegada da onda | Estudo do empreendedor ou estimativa própria |
| População e serviços | População na ZAS, população vulnerável, unidades de saúde, captações, escolas, vias | Setor censitário, CNES, Sisagua, INEP, malha viária |
| IDAP detalhado | Pontuação por dimensão e por indicador, completude, lacunas, regras disparadas | `scripts/idap/` |

### Filtros

Barragem (busca por nome, id SNISB, município ou empreendedor) · janela histórica ·
cenário de mancha.

### Viabilidade hoje

| Elemento | Situação |
| --- | --- |
| Identificação, classificação, engenharia de mineração, anomalias autodeclaradas | ✅ para os campos preenchidos |
| Classificação — lacunas | ⚠️ CRI e DPA sem classificação em parte significativa da base; ver `docs/09-dicionario-de-dados.md` |
| Inspeções | ⚠️ campo existe; muitas datas ausentes |
| Cruzamento com SIGBM | ⚠️ 183 barragens de mineração; o casamento com o registro SNISB depende de nome e coordenada, não de chave comum |
| Sensores, chuva, nível, mancha, população, histórico do IDAP | ⛔ |

---

## 7.4 Tela 4 — Alerta antecipado

| Aspecto | Definição |
| --- | --- |
| Propósito | Operar o ciclo de alerta: ver o que foi emitido, por quê, para quem, e quem ainda não confirmou |
| Público-alvo | Sala de Situação, CIEVS, coordenação de Vigilância em Saúde, Defesa Civil |
| Granularidade | Alerta (barragem × instante) e destinatário |
| Tecnologia | Aplicação Python + serviço de alertas (§6.1.1) |
| Atualização | Tempo quase real (evento a evento) |

### Widgets e indicadores

| Widget | Conteúdo | Fonte |
| --- | --- | --- |
| Painel de IDAP | Valor, faixa, IDAP projetado, completude e confiabilidade | `calculo_idap` |
| Decomposição | Pontuação por dimensão (A 0–30, B 0–30, C 0–25, D 0–15) em barras | `calculo_idap` |
| Justificativas | Lista de motivos por indicador, na ordem de pontuação (campo "Motivos" do alerta) | `calculo_idap.pontos_por_indicador` |
| Lacunas | Indicadores sem dado, com a fonte que deveria fornecê-los | `calculo_idap.lacunas` |
| Regras disparadas | R01–R09 acionadas, com a ação automática correspondente | `regras.py` |
| Mapa de destinatários | Municípios da ZAS e da ZSS, com estado de confirmação por cor | `vinculo_barragem_ator`, `confirmacao_entrega` |
| Tabela de entrega | Destinatário, instituição, papel, canal, hora de envio, hora de confirmação, quem confirmou, escalonamentos | `confirmacao_entrega` |
| Cronômetro | Tempo restante para o prazo de confirmação por nível (§4.6.3) | `alerta.prazo_confirmacao_min` |
| Ações recomendadas | Lista por nível, com marcação de executada | `docs/04-alertas.md` |
| Prévia do alerta | Texto formatado exatamente como será enviado | `relatorio.py` |
| Fila de supervisão | Alertas em Vermelho ou Roxo aguardando liberação humana | `alerta.estado_atual` |

### Filtros

Barragem · município · nível · estado de entrega (enviado / entregue / confirmado /
escalonado / não confirmado) · janela temporal · responsável.

### Viabilidade hoje

| Elemento | Situação |
| --- | --- |
| Motor de cálculo, justificativas, lacunas, regras, texto formatado do alerta | ✅ implementado e testado em `scripts/idap/` |
| Cálculo com dado real | ⚠️ apenas a dimensão B tem dado hoje, e parcialmente |
| Destinatários, entrega, confirmação, escalonamento | ⛔ depende do cadastro de contatos institucionais e do serviço de alertas |

---

## 7.5 Tela 5 — Impacto observado

| Aspecto | Definição |
| --- | --- |
| Propósito | Mostrar o que efetivamente aconteceu no território: até onde a água chegou e o que ficou inacessível |
| Público-alvo | Sala de Situação, COE, Defesa Civil, gestores municipais, logística |
| Granularidade | Localidade, setor censitário, via, estabelecimento |
| Tecnologia | WebGIS (§6.1.1) |
| Atualização | A cada nova imagem, produto do Copernicus EMS ou ficha rápida |

### Widgets e indicadores

| Widget | Conteúdo | Fonte | Latência |
| --- | --- | --- | --- |
| Comparador antes / depois | Imagem pré e pós-evento, com cortina deslizante | Sentinel-1 (radar, opera com nuvem e à noite), Sentinel-2, Landsat, CBERS | horas a dias |
| Extensão da inundação | Polígono da área alagada, área em km², evolução (expansão / retração) | Sentinel-1 preferencialmente; Copernicus EMS quando ativado | horas |
| Vias interrompidas | Trechos rodoviários cortados, com identificação da rodovia | Malha viária × polígono de inundação; confirmação por Defesa Civil | horas |
| Localidades isoladas | Localidades sem rota terrestre disponível, com população estimada | Análise de conectividade em PostGIS | horas |
| Unidades afetadas | Unidades de saúde inundadas, isoladas ou sem acesso, por tipo | CNES × inundação × conectividade | horas |
| População atingida | Estimativa por setor censitário com área ponderada, e número informado pela ficha rápida | IBGE / Censo, ficha rápida | horas |
| Painel de divergência | Comparação entre estimativa por sensoriamento e número informado pelo município | Composto | por atualização |

Regra de prioridade de sensor, repetida na tela: **Sentinel-1 para delimitar inundação durante
o evento** (opera com nuvem e à noite); **ópticos para avaliação detalhada de dano quando
houver imagem sem nuvem** — e a nuvem é justamente maior durante chuva intensa.

O painel de divergência não é um detalhe: divergir é o normal, e explicitar a divergência
evita que a Sala de Situação decida sobre um número que ninguém sabe de onde veio.

### Filtros

Evento · município · localidade · sensor · data da imagem · tipo de ativo afetado.

### Viabilidade hoje

| Elemento | Situação |
| --- | --- |
| Malha municipal para contexto | ⚠️ 141 polígonos para 142 municípios (pendência registrada) |
| Todo o restante | ⛔ depende de coletor de imagens, de processamento de inundação e do módulo de ficha rápida |

---

## 7.6 Tela 6 — Vigilância pós-desastre

| Aspecto | Definição |
| --- | --- |
| Propósito | Detectar e acompanhar o impacto do desastre sobre a saúde da população atingida |
| Público-alvo | CIEVS, Vigilância Epidemiológica, Vigilância Ambiental, Vigiagua, laboratório |
| Granularidade | Município, localidade, abrigo, agravo, síndrome |
| Tecnologia | Python (modelos) + Power BI (visualização) |
| Atualização | Diária em rotina; a cada carga de ficha ou de resultado durante evento |

### Widgets e indicadores

| Bloco | Indicadores | Fonte | Referência |
| --- | --- | --- | --- |
| Vítimas | Taxa de mortalidade pelo desastre, letalidade entre vítimas, taxa de trauma grave, taxa de hospitalização, proporção de desaparecidos, tempo médio de resgate | Ficha rápida, SIM, SIH, SAMU, Defesa Civil | `docs/05-vigipos-barragens.md` §5.5.1 |
| Agravos | Casos por agravo e por semana epidemiológica: leptospirose, animais peçonhentos, doenças transmitidas por água e alimentos, intoxicações exógenas, acidentes de trabalho, tétano acidental, violência | SINAN, ficha rápida | §5.3.3 |
| Sinais sindrômicos | Nove síndromes (diarreica, febril, febril-ictérica, respiratória, dermatológica, neurológica, intoxicação, traumática, sofrimento mental agudo), com contagem e tendência | Ficha rápida, e-SUS APS, urgência | §5.5.3 |
| Observado / esperado | Razão O/E, esperado, limite superior da linha de base, excesso de casos, método usado, classificação do sinal | `sinal_epidemiologico` | §5.5.2 e §5.6 |
| Resultados laboratoriais | Positividade por agravo, tempo entre coleta e resultado, exames pendentes | GAL / LACEN | §5.5.2 |
| Abrigos | Abrigos ativos, ocupação frente à lotação máxima, densidade por área, banheiros por pessoa, água disponível, diarreia, sintomas respiratórios, doenças de pele, necessidades especiais, gestantes, idosos, crianças, cobertura vacinal, atendimento em saúde mental, incidentes de violência | Ficha rápida, registro de abrigos | §5.5.6 |
| Água | Percentual de sistemas interrompidos, população sem água segura, captações afetadas, percentual de amostras fora do padrão, coliformes e E. coli, turbidez, contaminantes químicos prioritários, dias de desabastecimento, litros por pessoa/dia, cobertura de inspeção sanitária, tempo de restabelecimento | Sisagua/Vigiagua, concessionária, ficha rápida | §5.5.4 |
| Oportunidade | Tempo entre sintomas e notificação, proporção investigada em 24 h | SINAN, ficha rápida | §5.5.2 |

### Filtros

Evento · município · localidade · abrigo · agravo ou síndrome · semana epidemiológica ·
faixa etária · sexo · método de detecção.

### Nota metodológica na tela

Rodapé fixo: *"Os sinais desta tela são produzidos por algoritmo estatístico reproduzível
(canal endêmico, CUSUM, EWMA, Poisson, binomial negativa). O assistente de IA pode explicar
um sinal, nunca produzi-lo. Sinal estatístico não é confirmação de nexo causal."*

### Viabilidade hoje

| Elemento | Situação |
| --- | --- |
| Todo o conteúdo | ⛔ depende de integração com SINAN, SIM, SIH, GAL e do módulo de ficha rápida |
| Métodos de detecção | ⚠️ especificados em `docs/05-vigipos-barragens.md`, ainda não implementados |

---

## 7.7 Tela 7 — Assistência e logística

| Aspecto | Definição |
| --- | --- |
| Propósito | Dizer se a rede aguenta a demanda e o que falta onde |
| Público-alvo | Regulação estadual e municipal, SAMU, logística, assistência farmacêutica, COE |
| Granularidade | Estabelecimento CNES, município, região de saúde |
| Tecnologia | Power BI + Python (IPAPD) |
| Atualização | Tempo quase real durante evento; diária em rotina |

### Widgets e indicadores

| Widget | Indicadores | Fonte |
| --- | --- | --- |
| Leitos | Leitos por tipo (clínico, UTI adulto, UTI pediátrica, obstétrico), ocupados, disponíveis, taxa de ocupação | CNES (capacidade cadastrada) + movimentação hospitalar e SISREG (situação do momento) |
| Equipes | Profissionais previstos, presentes, ausentes, percentual de indisponibilidade | CNES + ficha rápida |
| Ambulâncias | Ambulâncias por tipo, operacionais, em deslocamento, indisponíveis, tempo médio de resposta | SAMU, CNES, ficha rápida |
| Estoques | Medicamentos essenciais, soro, antibiótico, soro antiveneno, imunobiológico, insumo de diálise, com dias de autonomia | Assistência farmacêutica, centrais de abastecimento |
| Rotas | Rotas de acesso a cada unidade, rotas interrompidas, rotas alternativas, tempo adicional estimado | Malha viária × inundação, Defesa Civil |
| Utilidades | Unidades sem água, sem energia, sem oxigênio, com gerador, com autonomia em horas | Ficha rápida, concessionárias, dados de falta de energia e água |
| **IPAPD** | Índice de Pressão Assistencial Pós-Desastre por unidade e por município, com decomposição dos seis termos | Calculado (§5.5.5) |
| Necessidades | Lista consolidada de necessidades declaradas, por município, com status de atendimento | Ficha rápida |
| Fila de transferência | Pacientes aguardando transferência, por criticidade e destino | SISREG |

### Filtros

Evento · região de saúde · município · tipo de estabelecimento · criticidade ·
status de necessidade.

### Viabilidade hoje

| Elemento | Situação |
| --- | --- |
| Capacidade cadastrada (leitos, equipes, equipamentos, ambulâncias) | ⛔ o CNES não foi integrado ainda; a integração é tecnicamente simples e é um bom candidato à Fase 1 |
| Situação operacional do momento | ⛔ depende de ficha rápida e de integração com regulação e movimentação hospitalar |
| IPAPD | ⚠️ fórmula e normalização definidas; sem dado de entrada |

Ressalva estrutural, repetida de `docs/02-fontes-de-dados.md` §2.8.1: o CNES informa **capacidade cadastrada**, com
atualização periódica. Sem a informação operacional do momento — unidade funcionando ou
interditada, profissionais presentes, leitos realmente disponíveis, estoque, energia, água,
oxigênio e acesso viário — esta tela mostra o hospital que existe no cadastro, não o que está
de pé.

---

## 7.8 Tela 8 — Recuperação

| Aspecto | Definição |
| --- | --- |
| Propósito | Acompanhar o retorno à normalidade e impedir que o evento seja encerrado antes da hora |
| Público-alvo | Gestão estadual e municipal, COE em desmobilização, vigilância, controle social |
| Granularidade | Município, localidade, serviço |
| Tecnologia | Power BI |
| Atualização | Semanal, com marcos quando houver restabelecimento relevante |

### Widgets e indicadores

| Widget | Indicadores | Fonte |
| --- | --- | --- |
| **IRS** | Índice de Recuperação Sanitária, com as onze dimensões abertas | Calculado (§5.5.7) |
| Serviços restabelecidos | Percentual de unidades de APS em funcionamento, hospitais em capacidade plena, equipes retornadas, rede de frio recuperada | CNES, ficha rápida |
| População em abrigos | Série da população abrigada, número de abrigos ativos, previsão de encerramento | Registro de abrigos |
| Qualidade da água | Percentual de amostras dentro do padrão, cobertura de análise, sistemas restabelecidos, dias acumulados de desabastecimento | Sisagua/Vigiagua |
| Agravos persistentes | Agravos que seguem acima do esperado, com a razão O/E e semanas consecutivas acima do limite | `sinal_epidemiologico` |
| Saúde mental | Pessoas em acompanhamento, atendimentos realizados, cobertura frente à população atingida, casos de sofrimento psíquico grave | e-SUS APS, CAPS, ficha rápida |
| Continuidade de tratamento | Percentual de pacientes de diálise, tuberculose, HIV, saúde mental e oncologia com tratamento retomado | Sistemas assistenciais |
| Monitoramento ambiental | Presença residual de lama ou rejeito, resultados de amostras de solo e água, mortalidade de animais | Vigilância Ambiental, SEMA-MT |
| Pendências | Lista de pendências por responsável, com prazo e status | Registro do COE |
| Marco de encerramento | Critérios de encerramento do evento e quais já foram atendidos | `docs/05-vigipos-barragens.md` |

### Filtros

Evento · município · localidade · dimensão do IRS · status de pendência · responsável.

### Viabilidade hoje

| Elemento | Situação |
| --- | --- |
| Todo o conteúdo | ⛔ depende dos módulos de evento, ficha rápida e integrações de saúde |
| IRS | ⚠️ dimensões e normalização definidas; sem dado de entrada |

---

## 7.9 Síntese de viabilidade

| Tela | Viável hoje | Principal bloqueio |
| --- | --- | --- |
| 1 — Comando estadual | Parcial (inventário, mapa, distribuição por classificação) | Mancha de inundação, coletores de chuva, contatos |
| 2 — Monitoramento ambiental | Não | Coletores de INMET, Cemaden, ANA, IMERG e imagens |
| 3 — Barragem 360° | Parcial (cadastro, classificação, anomalias autodeclaradas) | Sensores, séries, mancha, população |
| 4 — Alerta antecipado | Parcial (motor de cálculo pronto e testado) | Dado de entrada das dimensões A, C e D; cadastro de contatos |
| 5 — Impacto observado | Não | Imagens, processamento de inundação, ficha rápida |
| 6 — Vigilância pós-desastre | Não | SINAN, SIM, SIH, GAL, ficha rápida |
| 7 — Assistência e logística | Não | CNES, SISREG, movimentação hospitalar, ficha rápida |
| 8 — Recuperação | Não | Dependência das telas 6 e 7 |

Leitura honesta deste quadro: hoje existe **inventário**, não **monitoramento**. As telas 1, 3
e 4 podem entrar no ar em versão reduzida e útil — um inventário navegável, com classificação
oficial, lacunas explícitas e o motor de IDAP rodando com completude declarada. As demais
dependem de integrações que a Fase 1 do roadmap (`docs/08-roadmap.md`) organiza em ordem de
dependência.

## 7.10 Requisitos transversais de interface

| Requisito | Descrição |
| --- | --- |
| Frescor visível | Toda tela mostra a hora do dado mais recente por fonte. Dado velho com aparência de dado novo é o pior defeito possível em sistema de alerta |
| Lacuna visível | Ausência de dado aparece como ausência, nunca como zero e nunca como "sem risco" |
| Completude do índice | Todo IDAP exibido vem acompanhado da completude e da confiabilidade |
| Fuso horário | Todo horário em horário de Cuiabá (UTC−4), com o fuso escrito |
| Rastreabilidade | Todo número permite chegar à fonte, à hora de coleta e à versão de pesos usada |
| Acessibilidade | Faixas de alerta nunca dependem só de cor; sempre há rótulo textual |
| Operação em banda estreita | A tela usada em campo precisa funcionar em conexão ruim; versão leve obrigatória |
| Marcação de conteúdo gerado por IA | Todo texto produzido por modelo de linguagem é identificado como tal (§6.5.2) |
