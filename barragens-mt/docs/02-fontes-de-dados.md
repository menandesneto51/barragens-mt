# 2. Catálogo de fontes de dados

> Convenções deste catálogo:
>
> - **Periodicidade** é a cadência com que a fonte publica dado novo.
> - **Latência** é o atraso entre o fato no mundo e a disponibilidade do dado para consulta.
> - Valores marcados **a validar** são estimativas próprias, não compromissos publicados
>   pelo provedor. Precisam ser confirmados com o órgão ou medidos em operação.
> - Endpoints marcados **a validar** não foram testados nesta versão do documento.

## 2.1 Por que "tempo quase real" e não "tempo real"

Nenhum produto deste catálogo é tempo real. Todo dado percorre três etapas com atraso
próprio:

| Etapa | O que acontece | Exemplo de ordem de grandeza |
| --- | --- | --- |
| Aquisição | O sensor mede, o satélite passa, o profissional registra | pluviômetro: 10 min; Sentinel-1: dias entre passagens |
| Transmissão | O dado sai do ponto de coleta | telemetria por satélite/GPRS: minutos a horas; notificação em papel: dias |
| Processamento | Validação, correção, agregação, publicação | GPM Early Run: horas; SIM: meses |

Chamar o sistema de "tempo real" produziria expectativa falsa no gestor: ele decidiria
acreditando que a ausência de sinal significa ausência de evento, quando pode significar
apenas que o dado ainda não chegou. Por isso todo painel e todo alerta deve estampar a
**hora da última atualização de cada fonte**, e não apenas a hora da consulta.

---

## 2.2 Grupo A — Cadastro e regulação de barragens

### 2.2.1 SNISB / SNIRH — Agência Nacional de Águas e Saneamento Básico (ANA)

Camada consolidada que reúne o cadastro alimentado por **todos** os órgãos
fiscalizadores. É a espinha dorsal do inventário.

| Aspecto | Conteúdo |
| --- | --- |
| Endpoint | `https://www.snirh.gov.br/arcgis/rest/services/IG/SNISB/FeatureServer/0/query` |
| Filtro por UF | `where=ING_SG_UFMUNICIPIO = 'MT'` |
| Parâmetros de coleta | `outFields=*`, `returnGeometry=true`, `outSR=4326`, `resultRecordCount=2000` com paginação por `resultOffset` |
| Resultado verificado | **1.248 barragens em Mato Grosso** (extração de 29/07/2026) |
| O que fornece | Identificação, empreendedor, órgão fiscalizador, coordenada, uso, material, altura, capacidade, fase de vida, CRI, DPA, classe, nível de perigo, instrumentos da PNSB, data de inspeção, completude, recorte hidrográfico — 43 campos |
| Granularidade | Uma linha por barragem |
| Periodicidade | Contínua — os órgãos alimentam a base diretamente |
| Latência | Depende do órgão alimentador; na prática, meses para atualização de classificação (**a validar** com a ANA) |
| Formatos de export suportados | `sqlite`, `filegdb`, `shapefile`, `csv`, `geojson` |
| Limitações | Certificado TLS de `snirh.gov.br` com cadeia autoassinada — o coletor do repositório trata a exceção; nomes de município com caixa e acentuação inconsistentes (150 grafias distintas para 115 municípios); 92,5% dos registros sem data de inspeção; campo `BAR_NU_CAP_TOTAL_RESERV` publicado em hm³ apesar do nome sugerir m³ |
| Implementado em | `scripts/01_snisb_mt.py` |

### 2.2.2 Painel público do SNISB (modelo semântico Power BI) — ANA

Esta é a **fonte adicional informada pelo usuário**, e a investigação mostrou que se trata
do mesmo cadastro do SNISB, exposto pelo relatório público da ANA.

| Aspecto | Conteúdo |
| --- | --- |
| URL do relatório | `https://app.powerbi.com/view?r=eyJrIjoiNmVmZTkyMzgtMzAxMy00YzliLTgwMWYtODJkNDdkODM0MTg2IiwidCI6ImUwYmI0MDEyLTgxMGItNDY5YS04YjRkLTY2N2ZjZDFiYWY4OCJ9` |
| Chave de recurso | `6efe9238-3013-4c9b-801f-82d47d834186` (publish-to-web, consulta anônima) |
| Endpoint de consulta | `https://wabi-brazil-south-d-primary-api.analysis.windows.net/public/reports/querydata` |
| Entidade consultada | `VW_RELATORIO_BARRAGENS` |
| O que fornece a mais que o ArcGIS | 73 campos contra 43. Exclusivos e relevantes: comprimento do coroamento, altura estimada, capacidade estimada, data da última fiscalização, data da última autuação, data da inspeção de segurança regular, tipo de empreendedor, corpo hídrico, data de atualização do registro, situação do cadastro |
| Resultado verificado | 1.248 registros — mesmas barragens do ArcGIS, o que serve de verificação cruzada |
| Periodicidade | Contínua, mas o relatório publicado é um instantâneo; o ArcGIS costuma estar mais atual |
| Latência | **a validar** — depende da atualização do modelo semântico publicado |
| Limitações | **Relatórios Power BI embutidos não expõem API contratual.** O endpoint `querydata` e o formato compactado DSR de resposta são interface interna, sujeita a mudança sem aviso. Uma alteração no relatório, na chave de recurso ou no cluster quebra o coletor sem retorno de erro semântico. **O caminho correto é solicitar o dataset de origem à ANA**, ou usar exclusivamente o serviço ArcGIS, que é interface publicada. O coletor existe no repositório porque quatro campos de priorização de fiscalização só existem aqui; deve ser tratado como fonte complementar frágil, com monitoramento de quebra |
| Implementado em | `scripts/04_powerbi_snisb.py` |

### 2.2.3 SIGBM — Agência Nacional de Mineração (ANM)

| Aspecto | Conteúdo |
| --- | --- |
| Endpoint | `https://dadosabertos.anm.gov.br/SIGBM/Barragens.csv` |
| Metadados | `https://dadosabertos.anm.gov.br/SIGBM/metadados-sigbm.ods` |
| Formato | CSV, codificação cp1252, delimitador vírgula, 124 colunas |
| Resultado verificado | 909 barragens no país; **183 em Mato Grosso** |
| Coordenadas | Grau/minuto/segundo, ex.: `-10°07'16.390''` — exigem conversão para grau decimal |
| Granularidade | Uma linha por barragem de mineração, incluindo os campos da Back Up Dam associada |
| Periodicidade | **Diária** — republicação automática do SIGBM |
| Latência | Até 24 h desde a atualização no SIGBM (**a validar**) |
| Limitações | Cadeia de certificados incompleta em vários pontos de saída; a string `-` é usada como sentinela de ausência, o que exige tratamento explícito (91,8% dos registros de MT têm `-` no Status da DCO Atual); não carrega o identificador do SNISB, obrigando casamento por nome + município (177 das 183 casaram) |
| Implementado em | `scripts/02_sigbm_anm.py` |

Colunas de alto valor para monitoramento que **não existem no SNISB**:

| Coluna do SIGBM | Para que serve no monitoramento |
| --- | --- |
| `Nível de Emergência` | Alimenta o indicador B2 do IDAP (10 pontos) e a regra determinística R01 |
| `Status DCE RISR`, `Status DCE RPSB`, `Status da DCO Atual` | Alimentam B3 — ausência de estabilidade declarada |
| `Método construtivo da barragem`, `Tipo de alteamento` | Identificam alteamento a montante, proibido pela Resolução ANM nº 95/2022 |
| `Instrumentação` | Alimenta B6 — falha ou ausência de telemetria |
| `Volume atual do Reservatório (m³)` | Alimenta B5 — elevação anormal do reservatório |
| `Existência de população a jusante` | Alimenta C1 e a definição da ZAS |
| `Número de pessoas possivelmente afetadas a jusante em caso de rompimento da barragem` | Estimativa oficial de exposição, usada como piso quando não há mancha modelada |
| `Necessita de PAEBM` | Alimenta D1 |
| `As cópias físicas do PAEBM foram entregues para as Prefeituras e Defesas Civis municipais e estaduais` | Prova de articulação municipal — diferencia D1 = 0 de D1 = 1 |
| `Fase Atual do projeto de Descaracterização` | Contexto de risco de estruturas em desativação |
| `A Barragem armazena rejeitos/residuos que contenham Cianeto` | Alimenta C8 — contaminante prioritário |
| `Minério principal presente no reservatório` | Alimenta C8 e a definição do painel laboratorial pós-desastre |
| `Percolação`, `Deformações e recalque`, `Deteriorização dos taludes / paramentos`, `Drenagem interna`, `Confiabilidade das estruturas extravasora` | Escala 0–10 que alimenta B4 — anomalia estrutural ativa |
| `Impacto ambiental`, `Impacto sócio-econômico` | Contexto de dano potencial declarado |

### 2.2.4 SEMA-MT — Secretaria de Estado do Meio Ambiente

| Aspecto | Conteúdo |
| --- | --- |
| Competência | Fiscaliza barragens de acumulação de água para usos múltiplos em corpos hídricos de domínio estadual |
| Marco normativo | Instrução Normativa nº 02/2020, alterada pela IN nº 04/2021 — define cadastro obrigatório, outorga de obra hidráulica e classificação por CRI e DPA |
| Participação no inventário | 781 das 1.248 barragens (62,6%), das quais 85 com CRI alta |
| Endpoint próprio | **Não existe API estadual independente.** O ponto de coleta é o SNISB |
| Periodicidade de alimentação | Contínua, por processo administrativo |
| Latência | Meses entre o ato administrativo e o reflexo no SNISB (**a validar**) |
| Evolução observada | Em 2025 a SEMA-MT passou de 419 para 661 barragens cadastradas no SNISB — salto de 58% que indica esforço ativo de recadastramento |
| Pendência | Solicitar à SEMA-MT acesso ao cadastro de origem, com o campo de outorga e o histórico de classificação, que o SNISB não expõe (**a validar** viabilidade) |

### 2.2.5 ANEEL e ANA como fiscalizadores

| Órgão | Barragens em MT | O que fiscaliza | Acesso |
| --- | ---: | --- | --- |
| ANEEL | 154 (42 com DPA alto) | Barragens de geração de energia elétrica | Via SNISB; SIGEL e dados abertos da ANEEL como complemento (**a validar** endpoint) |
| ANA | 130 | Barragens em corpos hídricos de domínio federal para usos múltiplos | Via SNISB |

As 154 barragens da ANEEL concentram 42 dos 65 casos de DPA alto do estado — inclusive as
três estruturas da UHE Manso, com 7.337 hm³ de reservatório. É o subconjunto com maior
consequência potencial por evento.

### 2.2.6 Empreendedores

| Aspecto | Conteúdo |
| --- | --- |
| O que fornece | Telemetria de nível e vazão, leitura de instrumentação (piezômetros, inclinômetros, medidores de vazão de drenos, marcos superficiais), relatórios de inspeção, nível de emergência declarado, estudo de ruptura hipotética (dam break) com mancha e tempo de chegada da onda, PAE/PAEBM, cadastro de sirenes |
| Granularidade | Por estrutura, por sensor |
| Periodicidade | Variável: telemetria de minutos a horas; inspeção regular semestral ou anual conforme classe |
| Latência | Minutos a horas para telemetria; dias a meses para relatório |
| Forma de acesso | **Não existe hoje.** Depende de acordo de compartilhamento ou de obrigação normativa que determine o envio ao Estado (**a validar** — é a pendência institucional mais relevante do projeto) |
| Limitações | Dado autodeclarado; qualidade heterogênea; empreendedores de pequeno porte, que são a maioria em MT, frequentemente não têm instrumentação — 52 das 183 barragens de mineração de MT estão declaradas como não instrumentadas em desacordo com o projeto |

---

## 2.3 Grupo B — Hidrometeorologia terrestre

### 2.3.1 INMET — estações meteorológicas automáticas

| Aspecto | Conteúdo |
| --- | --- |
| O que fornece | Observação horária de precipitação, temperatura do ar, umidade relativa, pressão atmosférica, direção e velocidade do vento e **rajada máxima** |
| Endpoints | Lista de estações automáticas: `https://apitempo.inmet.gov.br/estacoes/T`; série por estação: `https://apitempo.inmet.gov.br/estacao/{data_inicio}/{data_fim}/{codigo_estacao}`; histórico: `https://portal.inmet.gov.br/dadoshistoricos` (**a validar** — API sem contrato de estabilidade publicado) |
| Granularidade | Pontual, por estação; agregação horária |
| Periodicidade | Horária |
| Latência | 1 a 2 h (**a validar**) |
| Limitações | Densidade espacial baixa para a área de Mato Grosso; uma bacia de contribuição pequena pode não ter nenhuma estação dentro; falhas de transmissão produzem lacunas na série, que precisam ser distinguidas de "não chuveu" |
| Uso no IDAP | A1, A2, A4, A7 |

### 2.3.2 Cemaden — Centro Nacional de Monitoramento e Alertas de Desastres Naturais

| Aspecto | Conteúdo |
| --- | --- |
| O que fornece | Chuva acumulada e intensidade por pluviômetro automático; estações hidrológicas (nível); radares meteorológicos onde disponíveis; **previsão de risco geo-hidrológico**; rede observacional com dados de campo |
| Endpoints | Mapa interativo: `https://mapainterativo.cemaden.gov.br/`; portal de dados abertos: `https://dadosabertos.cemaden.gov.br/` (**a validar** — necessário confirmar o endpoint programático e as condições de uso) |
| Granularidade | Pontual, por pluviômetro; municipal para o risco geo-hidrológico |
| Periodicidade | 10 min para pluviômetro; diária para o boletim de risco |
| Latência | 10 a 30 min para pluviômetro; horas para o boletim (**a validar**) |
| Limitações | Cobertura de pluviômetro concentrada em municípios monitorados por critério de risco geo-hidrológico, que não coincide com a distribuição das barragens; a previsão de risco é municipal, granularidade grosseira para uma ZAS de poucos quilômetros; radar meteorológico com cobertura muito limitada em MT (**a validar** situação atual) |
| Uso no IDAP | A1, A2, A3, A5, A7 |

### 2.3.3 ANA — Rede Hidrometeorológica Nacional e telemetria

| Aspecto | Conteúdo |
| --- | --- |
| O que fornece | Chuva, **nível (cota)**, **vazão**, qualidade da água e sedimentos, em estações convencionais e telemétricas |
| Endpoints | HidroWeb (série histórica): `https://www.snirh.gov.br/hidroweb/`; telemetria (serviço legado SOAP): `http://telemetriaws1.ana.gov.br/ServiceANA.asmx`; HidroWebService (API atual, exige cadastro): `https://www.ana.gov.br/hidrowebservice/` (**a validar** — confirmar credenciamento e cotas de uso) |
| Granularidade | Pontual, por estação |
| Periodicidade | 15 min a 1 h na telemetria; mensal na consistência da série convencional |
| Latência | 15 min a algumas horas na telemetria; **meses a anos** para dado consistido |
| Limitações | Distinguir dado bruto de dado consistido é essencial: o bruto serve para alerta, o consistido para climatologia; estações telemétricas podem ficar fora do ar por dias; a cota de alerta e a cota de inundação, necessárias ao indicador A6, precisam ser cadastradas por estação em conjunto com a Defesa Civil (**a validar** disponibilidade) |
| Uso no IDAP | A6 (nível/vazão a jusante) e monitoramento pós-desastre de qualidade da água |

---

## 2.4 Grupo C — Chuva por satélite

### 2.4.1 NASA GPM-IMERG

Integrated Multi-satellitE Retrievals for GPM. É a fonte que resolve o problema de
cobertura: garante estimativa de chuva sobre **toda** bacia, inclusive onde não há
pluviômetro — situação da maior parte das 1.248 barragens de MT.

| Aspecto | Conteúdo |
| --- | --- |
| O que fornece | Estimativa de precipitação em grade global |
| Resolução temporal | 30 minutos |
| Resolução espacial | 0,1° × 0,1° (aproximadamente 11 km na latitude de MT) |
| Produtos e latência | **Early Run**: latência nominal de aproximadamente 4 h — é o produto de alerta. **Late Run**: latência maior (aproximadamente 14 h, **a validar**), com mais observações incorporadas e melhor qualidade. **Final Run**: latência de meses, ajustado por pluviômetro, é o produto de climatologia |
| Acesso | `https://gpm.nasa.gov/data/imerg`; distribuição pelo GES DISC: `https://disc.gsfc.nasa.gov/`; acesso quase em tempo real: servidor PPS (`https://arthurhouhttps.pps.eosdis.nasa.gov/`) — exige registro Earthdata |
| Periodicidade | Contínua, a cada 30 min |
| Limitações | Estimativa indireta: subestima chuva orográfica e pode superestimar em nuvens de alto topo sem precipitação à superfície; a resolução de 11 km é grosseira para bacias pequenas — em barragem com bacia de 10 km², um pixel cobre a bacia inteira e não resolve o gradiente; requer validação contra pluviômetro sempre que houver um |

Indicadores derivados do IMERG que a plataforma deve calcular:

| Indicador derivado | Definição | Uso |
| --- | --- | --- |
| Precipitação por pixel em 30 min | Valor bruto do produto | Insumo de todos os demais |
| Acumulados de 1 h, 3 h, 6 h, 12 h, 24 h e 72 h | Soma móvel sobre a bacia | A1 e A2 do IDAP; gatilho de inspeção |
| Chuva média na bacia | Média ponderada por área dos pixels que intersectam a bacia contribuinte | A1, A2 — é o valor que entra no índice |
| Chuva máxima localizada | Máximo entre os pixels da bacia | Detecta célula convectiva intensa que a média dilui |
| Percentual da bacia acima de limiar | Fração da área da bacia com acumulado acima de 50 mm/24 h (limiar **proposto a validar**) | Distingue chuva generalizada de chuva pontual |
| Anomalia frente à climatologia | Diferença ou razão entre o acumulado observado e a climatologia do mesmo período (IMERG Final Run ou normais do INMET) | A4 — percentil climatológico |
| Persistência de chuva intensa | Número de dias consecutivos com acumulado diário acima de 20 mm (limiar **proposto a validar**) | A7 |
| Índice de saturação antecedente estimada | Índice de precipitação antecedente com decaimento exponencial sobre 30 dias, normalizado de 0 a 1 | A5 |

---

## 2.5 Grupo D — Sensoriamento remoto

### 2.5.1 Sentinel-1 (radar de abertura sintética, banda C)

| Aspecto | Conteúdo |
| --- | --- |
| O que fornece | Imagem de radar, que **opera com nuvem e à noite** — a diferença decisiva em relação aos sensores ópticos durante um evento de chuva |
| Aplicações | Delimitar áreas alagadas; detectar mudança de superfície; comparar antes e depois; acompanhar expansão e retração da inundação; identificar interrupções territoriais (vias submersas, localidades cercadas por água) |
| Resolução espacial | 10 m (produto GRD IW) |
| Revisita | 6 a 12 dias na América do Sul, dependendo da constelação em operação (**a validar** — a configuração mudou com a perda do Sentinel-1B e a entrada do Sentinel-1C) |
| Latência | Produto NRT em 3 h após a passagem; produto padrão em até 24 h (**a validar**) |
| Acesso | Copernicus Data Space Ecosystem: `https://dataspace.copernicus.eu/`; catálogo OData: `https://catalogue.dataspace.copernicus.eu/odata/v1`; API STAC e Sentinel Hub para processamento sob demanda |

**Ressalva obrigatória, a repetir em todo painel que exiba imagem de radar:**

> O Sentinel-1 **não é sensor contínuo da barragem**. O que se vê depende do horário da
> passagem orbital, da área coberta pela faixa de imageamento, da latência de
> disponibilização e do tempo de processamento. Entre duas passagens podem transcorrer
> dias, e o rompimento pode ocorrer inteiramente nesse intervalo.
>
> O Sentinel-1 **complementa e não substitui**: piezômetros, inclinômetros, medidores de
> vazão de drenos, sensores de nível, inspeções técnicas presenciais e telemetria própria
> do empreendedor. Ele responde "qual a extensão da área alagada agora que já alagou", não
> "esta barragem vai romper".

### 2.5.2 Sentinel-2, Landsat e CBERS (sensores ópticos)

| Sensor | Resolução | Revisita | Acesso |
| --- | --- | --- | --- |
| Sentinel-2 (MSI) | 10 a 20 m | 5 dias (constelação) | `https://dataspace.copernicus.eu/` |
| Landsat 8/9 (OLI) | 30 m | 16 dias por satélite, 8 dias combinados | `https://earthexplorer.usgs.gov/` |
| CBERS-4A (WPM/MUX) | 2 m a 16,5 m | variável | INPE: `https://data.inpe.br/` e `http://www2.dgi.inpe.br/catalogo/explore` |

Aplicações: alterações na área e no nível do reservatório; exposição de solo e supressão
de vegetação na estrutura e na bacia; uso e cobertura da terra; **detecção de moradias
novas em área de risco a jusante**; avaliação de danos após o evento; estado da vegetação;
turbidez aparente da água.

**Limitação central:** nuvem. E a limitação é perversa, porque a cobertura de nuvem é
**maior justamente durante a chuva intensa** — o momento em que a imagem seria mais útil.
Em Mato Grosso, na estação chuvosa (novembro a março), há semanas em que nenhuma cena
óptica utilizável é adquirida sobre a área de interesse.

### 2.5.3 Regra de prioridade entre sensores

| Situação | Sensor prioritário | Justificativa |
| --- | --- | --- |
| Durante o evento, para delimitar inundação | **Sentinel-1 (radar)** | Atravessa nuvem e opera à noite |
| Depois do evento, para avaliação detalhada de danos | **Ópticos (Sentinel-2, Landsat, CBERS)**, quando houver cena limpa | Resolução e interpretação visual superiores; permitem identificar dano em edificação, deposição de lama e supressão de vegetação |
| Monitoramento de rotina do reservatório | Ópticos em cadência mensal, com radar como reserva | Custo de processamento menor e série mais interpretável |
| Detecção de ocupação nova na ZAS | Ópticos de alta resolução (CBERS-4A WPM) em cadência anual | Necessário distinguir edificação de vegetação |

### 2.5.4 Modelo digital de elevação (MDE) — relevo para proxy de mancha

Fonte **aberta e gratuita** para estimar, por relevo, quais terrenos perto da calha
ficam abaixo de uma lâmina proxy (HAND — *Height Above Nearest Drainage*).
**Não substitui** estudo de dam break / mancha PAE.

| Aspecto | Conteúdo |
| --- | --- |
| Produtos | **SRTM 30 m** (via OpenTopoData); **Copernicus DEM GLO-30**; **NASADEM**; **INPE Topodata** (derivado SRTM para o Brasil) |
| Acesso amostragem | OpenTopoData: `https://api.opentopodata.org/v1/srtm30m?locations=lat,lon\|…` (até 100 pontos/requisição; cadência ~1 req/s) |
| Acesso raster | Copernicus DEM / OpenTopography / Earthdata (NASA) — arquivos GeoTIFF regionais; Topodata INPE: `http://www.dsr.inpe.br/topodata/` |
| Granularidade | ~30 m (SRTM/Copernicus GLO-30) |
| Periodicidade | Estático (missão); não atualiza com o evento |
| Latência | Imediata após download/amostragem |
| Uso no projeto | Terceira geometria da simulação: células com HAND ≤ lâmina e ao longo do eixo jusante; cruzamento com CNES, vias OSM e população |
| Limitações | Resolução vertical e vegetação/edificações; não modela velocidade nem tempo de chegada da onda; vale estreito pode ser subamostrado |
| Implementado em | `scripts/35_mde_hand_piloto.py` → `dados/tratados/hand_piloto_manso_cuiaba.*`; consumo em `st_app/relevo_hand.py` |

### 2.5.5 MapBiomas — uso e cobertura da terra

| Aspecto | Conteúdo |
| --- | --- |
| O que fornece | Séries anuais de uso/cobertura (vegetação, agropecuária, área urbana, água) |
| Acesso | Estatísticas públicas: `https://brasil.mapbiomas.org/estatisticas/`; módulo urbano Col. 10 (municípios) |
| Uso pretendido | Pressão de ocupação na faixa de atenção a jusante; contexto de exposição (não entra no IDAP numérico nesta fase) |
| Periodicidade | Anual |
| Status no repositório | Implementado no eixo: `scripts/41_mapbiomas_eixo.py` → `mapbiomas_pressao_eixo_cuiaba.csv` (área urbana 2024, crescimento 10 anos, urbana em drenagem ≤3 m) |

### 2.5.6 IBGE — setores censitários (Censo 2022)

| Aspecto | Conteúdo |
| --- | --- |
| O que fornece | Malha e população por setor censitário — granularidade abaixo do município |
| Acesso | IBGE downloads / FTP de malhas e resultados do Censo |
| Uso pretendido | População exposta e isolada na mancha proxy (C1 do IDAP com rigor) |
| Status no repositório | Implementado no eixo Manso–Cuiabá: `scripts/37_ibge_setores_eixo.py` → `dados/tratados/setores_censitarios_eixo_cuiaba.csv` (+ GeoJSON). KPI na Simulação via `st_app/setores_ibge.py` (centróide do setor na mancha). População municipal permanece em `ibge_populacao_municipios_mt.csv` para o proxy C7 estadual. **Proxy ribeirinhos (dossiê por localidade):** `st_app/localidade.py` → `proxy_ribeirinhos_municipio` usa setores do eixo (com destaque a rurais) + exposição ≤5 km; **não** é cadastro de comunidade ribeirinha — municípios fora do eixo permanecem lacuna explícita |

### 2.5.7 Sisagua — captações de água (C4)

| Aspecto | Conteúdo |
| --- | --- |
| O que fornece | Pontos de captação / sistemas de abastecimento na faixa do eixo |
| Acesso | Cadastro oficial Dados Abertos SUS: `cadastro_pontos_captacao_csv.zip` (S3 CKAN); catálogo em `dadosabertos.saude.gov.br/dataset/sisagua-pontos-de-captacao`. Fallback espacial OSM (`waterway=intake`, `man_made=water_works`) se o zip falhar |
| Uso pretendido | Contagem de captações na mancha proxy (KPI C4) |
| Implementado em | `scripts/38_sisagua_captacoes.py` → `sisagua_captacoes_eixo.csv` + `sisagua_captacoes_mt.csv` (sedes com barragem); UI em `st_app/sisagua_captacoes.py`; proxies C4 na etapa `49` |

### 2.5.8 Telemetria pontual — dimensão A do IDAP

| Aspecto | Conteúdo |
| --- | --- |
| O que fornece | Chuva 24h/72h e previsão no **ponto da barragem** (não só centroide municipal) |
| Fontes | INMET estações automáticas (API pública, se ≤80 km); Open-Meteo no ponto (proxy modelo/IMERG); alertas Cemaden/INMET/ANA do SisClima preservados |
| Implementado em | `scripts/39_telemetria_hidro_a.py` → `telemetria_hidro_a.csv` + mescla em `hidro_barragens_mt.csv` (`aproximacao_espacial=ponto_barragem_telemetria`) |

### 2.5.8b Telemetria fluviométrica ANA — rios (contexto / A6)

| Aspecto | Conteúdo |
| --- | --- |
| O que fornece | Estações fluviométricas próximas à barragem: **cota (cm)**, **vazão (m³/s)**, cota de alerta quando cadastrada |
| Fonte | SisClima (`ana_estacoes` / `ana_telemetria` com `ANA_FETCH_SERIES=true`) ou CSV fallback em `dados/brutos/ana_*.csv` |
| Uso | Bloco “Contexto fluvial” na Simulação; IDAP **A6** com `razao = cota/cota_alerta` quando ambos existem (`a6_fonte=cota_medida`) |
| Fronteira | **Não** redefine a mancha Circular/Trajeto/HAND — telemetria de rio não é hidrodinâmica de ruptura |
| Implementado em | `scripts/52_auditoria_ana_sisclima.py`, `scripts/53_estacoes_ana_eixo.py` → `ana_estacoes_barragem.csv`; UI `st_app/ana_fluvial.py` |

### 2.5.9 Ativos essenciais OSM (C5 — ETA/ETE/energia/abrigos)

| Aspecto | Conteúdo |
| --- | --- |
| O que fornece | Pontos OSM de ETA (`water_works`), ETE (`wastewater_plant`), subestações, abrigos e bases de ambulância no eixo |
| Acesso | OpenStreetMap / Overpass |
| Uso pretendido | Ampliar C5 além de escolas/captações/pontes; proxy até haver cadastro oficial |
| Implementado em | `scripts/46_ativos_essenciais_osm_eixo.py` → `ativos_essenciais_osm_eixo.csv`; UI `st_app/ativos_essenciais.py` + demanda `st_app/demanda_cenario.py` (internação 2%, água 15 L/p/dia) |

### 2.5.10 Malha viária e desvio de rota (C7 / D7 proxy)

| Aspecto | Conteúdo |
| --- | --- |
| O que fornece | Arteriais e pontes OSM; km de rota sede→hub antes/depois do corte da mancha |
| Acesso | OpenStreetMap / Overpass (já na Simulação); DNIT/Sinfra-MT ainda sem ETL oficial |
| Uso pretendido | Isolamento e desvio de rota (roadmap 4.4); nível C7 proxy |
| Implementado em | `st_app/vias_isolamento.py` — campos `desvios_rota`, `delta_km_medio_desvio`, `n_sedes_sem_rota`; fallback offline em `st_app/malha_offline.py` + etapa `51_rotas_alternativas_offline.py` |

### 2.5.11 INEP — Censo Escolar (escolas na mancha, C5)

| Aspecto | Conteúdo |
| --- | --- |
| O que fornece | Escolas de educação básica com município e dependência; coordenadas **não** vêm nos microdados 2023/2024 (LGPD) |
| Acesso | Microdados Censo Escolar: `https://download.inep.gov.br/dados_abertos/microdados_censo_escolar_YYYY.zip` (download por faixas; TLS do host costuma exigir `verify=False`) |
| Camada espacial | OpenStreetMap `amenity=school\|kindergarten\|college` no bbox do eixo — usada na Simulação |
| Uso pretendido | Contagem de escolas na mancha proxy — serviço essencial não assistencial (C5), junto com captações e pontes |
| Implementado em | `scripts/40_escolas_inep_eixo.py` → `escolas_eixo_cuiaba.csv` (OSM) + `escolas_inep_contagem_municipio.csv` (INEP); UI em `st_app/escolas_inep.py` |

### 2.5.12 Malha BR/MT no eixo — proxy DNIT/SNV

| Aspecto | Conteúdo |
| --- | --- |
| O que fornece | Trechos com `ref` BR-/MT- (e pontes) no bbox do eixo Manso–Cuiabá; km aproximado por ref |
| Acesso preferido | SNV / portal DNIT (`dnitcloud`) — neste ambiente o download institucional costuma falhar (connection reset) |
| Proxy aberto | Overpass: ways `highway` arterial com `ref` ~ `^(BR\|MT)-` + bridges com a mesma ref |
| Uso pretendido | Contagem de refs federais/estaduais e pontes na mancha (complemento C7); substituir por SNV oficial quando disponível |
| Implementado em | `scripts/42_malha_dnit_osm_eixo.py` → `malha_dnit_osm_eixo.csv` / `.geojson`; UI em `st_app/malha_dnit.py` |

### 2.5.13 Capacidade assistencial CNES + IndicaSUS/DW (D6)

| Aspecto | Conteúdo |
| --- | --- |
| O que fornece | Tipologia hospital/UPA/UBS na mancha; **leitos operacionais, ocupados, disponíveis e taxa de ocupação** via IndicaSUS/DW; razão leitos/demanda (2% pop. exposta) |
| CNES aberto | Estabelecimentos e tipificação espacial (API não expõe leitos) |
| IndicaSUS / DW | Extrato institucional de leitos e ocupação — conector `scripts/dw_saude.py` + etapa `43` |
| CNES LT | Leitos **cadastrados** (SAU-01) — etapa `45`; dump CSV/DBC/DW (FTP DATASUS costuma falhar aqui) |
| Outros bancos DW | Etapa `44` + catálogo (`sih`, `sia`, `sisreg`, `sinan`) em `dados/config/dw_catalogo.json` |
| Uso pretendido | D6 com ocupação IndicaSUS; SAU-01 com LT; tipológico como fallback |
| Implementado em | `43`/`44`/`45`, `st_app/leitos_indicasus.py`, `st_app/dw_status.py`, `st_app/capacidade_cnes.py`, IDAP `razao_leitos_demanda`; docs `15-integracao-indicasus-dw.md` |

### 2.5.14 Cobertura de PAE (SNISB) e IPAPD proxy

| Aspecto | Conteúdo |
| --- | --- |
| PAE | `possui_pae` do inventário SNISB → `pae_manchas_cobertura.csv` (etapa `47`); mancha ZAS oficial continua pendente |
| Checklist PAE | `st_app/pae_checklist.py` — SNISB + cobertura 47 + SIGBM (PAEBM/cópias) por barragem; CSV na Simulação e na ficha 360°; ranking estadual etapa `48` → `pae_checklist_lacunas.csv` |
| IDAP C4/C5/C7 | Proxies do eixo Manso–Cuiabá (etapa `49` → `idap_proxies_eixo.csv`) consumidos por `16_idap_estadual.py`; buffer geométrico — não é mancha PAE |
| VIGIPÓS O/E | Canal endêmico + razão O/E (`st_app/vigipos.py`, etapa `50`); reproduz §5.6.4; tela Streamlit «VIGIPÓS O/E»; série sintética até haver SINAN/DW |
| IPAPD | Proxy na Simulação (`st_app/ipapd.py`): O (ocupação IndicaSUS), E (isolamento), S (essenciais na mancha); A/P/C lacuna até ficha rápida |
| IRS | Proxy de recuperação (`st_app/irs.py`, §5.5.7): média das dimensões disponíveis (1 = recuperado); ficha + sinais da mancha |
| Limite | IPAPD/IRS renormalizam pelos termos disponíveis — não preenchem lacuna com zero |
| Ficha rápida | JSON em `dados/tratados/fichas_rapidas/` ou upload na Simulação → termos A/P/C e dimensões IRS |
| SITREP cenário | Download Markdown na Simulação (`st_app/sitrep.py` · `montar_sitrep_cenario_md`) |
| KPIs cenário | CSV (`st_app/cenario_export.py`) com exposição, C7, demanda, IPAPD, IRS e lacunas PAE |

---

## 2.6 Grupo E — Copernicus EMS (Emergency Management Service)

| Aspecto | Conteúdo |
| --- | --- |
| O que fornece | Mapeamento de emergência: delimitação de inundação (*delineation*), monitoramento da evolução (*monitoring*) e avaliação de danos (*grading*), produzidos por equipe especializada a partir de imagem de satélite adquirida sob demanda |
| Acesso | `https://emergency.copernicus.eu/` — **acionamento restrito**: só usuário autorizado pode solicitar. No Brasil, a solicitação passa pela Defesa Civil ou por autoridade nacional autorizada |
| Periodicidade | Por acionamento, não contínua |
| Latência | Horas a poucos dias após a ativação, dependendo da disponibilidade de imagem e da complexidade do produto (**a validar**) |
| Quando usar | Desastre de maior magnitude, em que a delimitação própria por Sentinel-1 é insuficiente ou não há capacidade interna de processamento no momento crítico |
| Limitações | Não é fonte de rotina; não serve para alerta precoce; depende de cadeia institucional de acionamento que precisa estar pré-acordada **antes** do evento — deixar o acordo para o dia do desastre inviabiliza o uso |
| Pendência | Formalizar com a Defesa Civil estadual o fluxo de acionamento e o ponto focal (**a validar**) |

---

## 2.7 Grupo F — GloFAS (Global Flood Awareness System)

| Aspecto | Conteúdo |
| --- | --- |
| O que fornece | Previsão diária de vazão e probabilidade de inundação em rios de médio e grande porte, e perspectiva sazonal |
| Acesso | `https://global-flood.emergency.copernicus.eu/` |
| Granularidade | Trecho de rio em grade global (aproximadamente 0,05°) |
| Periodicidade | Diária para a previsão; mensal para a perspectiva sazonal |
| Latência | Menos de 24 h (**a validar**) |
| Uso pretendido | **Sinal complementar e indicador de contexto regional.** Serve para responder "a bacia do Paraguai ou do Araguaia está em regime de cheia acima do normal neste mês?" |
| Limitação determinante | A resolução global não representa bacia de barragem pequena nem trecho a jusante de poucos quilômetros. **Nunca substitui** dado local da ANA, da SEMA-MT, do Cemaden ou do empreendedor. Se o GloFAS indicar risco e a telemetria local não, prevalece a telemetria local; se a telemetria local indicar risco e o GloFAS não, prevalece a telemetria local |

---

## 2.8 Grupo G — Sistemas de informação em saúde

| Sistema | O que fornece | Granularidade | Periodicidade | Latência | Acesso |
| --- | --- | --- | --- | --- | --- |
| **CNES** | Estabelecimentos, equipes, leitos por tipo, equipamentos, serviços especializados, profissionais, veículos (ambulâncias) | Estabelecimento, com endereço e coordenada | Mensal (competência) | 1 a 2 meses | `https://cnes.datasus.gov.br/`; arquivos em `https://datasus.saude.gov.br/transferencia-de-arquivos/` |
| **SINAN** | Notificação compulsória: leptospirose, animais peçonhentos, doenças de transmissão hídrica e alimentar, intoxicação exógena, acidente de trabalho, tétano acidental, violência | Caso individual, município de notificação e de residência | Semanal (transferência) | Dias a semanas, variável por agravo | DATASUS / TabNet; base estadual da SES-MT |
| **SIM** | Mortalidade por causa básica, local de ocorrência e de residência | Óbito individual | Contínua na captação, consolidação anual | Meses a anos para base definitiva | DATASUS; base estadual preliminar da SES-MT |
| **SIH/SUS** | Internações hospitalares (AIH): diagnóstico, procedimento, tempo de permanência, óbito hospitalar | Internação individual | Mensal | 1 a 2 meses | DATASUS |
| **SIA/SUS** | Produção ambulatorial | Procedimento agregado | Mensal | 1 a 2 meses | DATASUS |
| **e-SUS APS** | Atendimento individual na Atenção Primária, território de equipe, condições de saúde, cadastro domiciliar | Indivíduo e domicílio | Contínua, com envio periódico | Dias a semanas | Base municipal e estadual; PEC e-SUS |
| **SISREG** | Solicitação e autorização de leitos e procedimentos; fila de regulação | Solicitação individual | Contínua | Minutos a horas | `https://sisregiii.saude.gov.br/` — acesso por perfil |
| **SAMU** | Ocorrências, tempo-resposta, natureza do atendimento, destino | Ocorrência individual | Contínua | Minutos | Sistema da central de regulação de urgência |
| **GAL / LACEN** | Resultado laboratorial: sorologia, cultura, PCR, análise de água | Amostra individual | Contínua | Horas a dias, por exame | GAL (Gerenciador de Ambiente Laboratorial) |
| **Sisagua / Vigiagua** | Vigilância da qualidade da água para consumo humano: cadastro de sistemas e soluções, análises de controle e de vigilância, parâmetros microbiológicos e físico-químicos | Sistema de abastecimento e ponto de coleta | Mensal a trimestral | Semanas a meses | `https://sisagua.saude.gov.br/` |
| **Renaveh** | Vigilância epidemiológica hospitalar em unidades sentinela | Caso hospitalar | Contínua | Dias | Núcleos hospitalares de vigilância |

### 2.8.1 Limitações conhecidas que mudam o uso do dado

Estas três limitações não são detalhes técnicos: definem para que cada sistema pode e não
pode ser usado.

**SIM — não serve para alerta imediato.**
Existe um intervalo estrutural entre a ocorrência do óbito, a investigação, a codificação
da causa básica e a consolidação da base. Esse intervalo é de meses. Consequência prática:
o SIM é a fonte para **linha de base de mortalidade**, para cálculo de **excesso de
mortalidade** e para **análise de médio e longo prazo** do impacto do desastre. Nunca para
contagem de óbitos durante o evento — essa contagem vem da ficha rápida e dos registros da
Defesa Civil, e é preliminar por definição.

**SINAN — essencial, mas com oportunidade variável.**
É a fonte insubstituível de vigilância de leptospirose, acidentes por animais peçonhentos,
doenças de transmissão hídrica e intoxicações — exatamente os agravos que aumentam depois
de uma inundação. Mas a **oportunidade da notificação varia por agravo e por fluxo local**:
um caso pode ser notificado em 24 h em um município e em três semanas em outro. Em um
desastre, três semanas é tempo demais. Consequência prática: o SINAN precisa ser
**complementado por ficha rápida** durante o evento e nas semanas seguintes, e a própria
oportunidade da notificação passa a ser um indicador monitorado (`docs/05-vigipos-barragens.md`, §5.5.2).

**CNES — capacidade cadastrada, não capacidade operante.**
O CNES informa o que está cadastrado, com atualização mensal. Em um desastre, o que importa
é o que está funcionando **agora**. Consequência prática: o CNES define o universo de
estabelecimentos e a capacidade instalada de referência, e precisa ser complementado por
informação operacional do momento:

| Informação operacional necessária | Fonte no evento |
| --- | --- |
| Unidade funcionando ou interditada | Ficha rápida, gestor municipal |
| Profissionais efetivamente presentes | Ficha rápida, gestor municipal |
| Leitos realmente disponíveis | SISREG, central estadual de regulação |
| Estoque de medicamento e insumo | Farmácia e central de abastecimento |
| Energia elétrica | Ficha rápida, concessionária |
| Água | Ficha rápida, concessionária |
| Oxigênio | Ficha rápida, fornecedor |
| Acesso viário | Defesa Civil, imagem de satélite, ficha rápida |

---

## 2.9 Grupo H — Fontes operacionais em tempo quase real

Estas fontes não são sistemas nacionais consolidados. São fluxos operacionais que precisam
ser integrados caso a caso, e é neles que está a diferença entre um painel retrospectivo e
uma sala de situação.

| Fonte | O que fornece | Granularidade | Periodicidade | Latência | Forma de acesso e limitações |
| --- | --- | --- | --- | --- | --- |
| Atendimentos de urgência (UPA, pronto-socorro) | Volume e motivo de atendimento, agrupável em síndromes | Atendimento individual | Contínua | Minutos a horas | Depende de integração com o sistema de cada unidade; heterogeneidade de sistemas é o obstáculo principal |
| Regulação estadual e municipal | Solicitações, autorizações, transferências, fila | Solicitação | Contínua | Minutos | SISREG e centrais locais; requer perfil de acesso |
| Movimentação hospitalar | Admissões, altas, óbitos, transferências | Internação | Contínua a diária | Horas | Sistema de gestão hospitalar; nem toda unidade tem |
| Disponibilidade de leitos | Leitos vagos por tipo (clínico, UTI adulto, UTI pediátrica, obstétrico) | Estabelecimento | Contínua a diária | Minutos a horas | Central de regulação; qualidade depende de atualização manual |
| Notificações hospitalares | Casos de interesse detectados na porta hospitalar | Caso | Contínua | Horas | Núcleos de vigilância hospitalar (Renaveh) |
| Registros de abrigos | Abrigos ativos, ocupação, perfil dos abrigados, necessidades | Abrigo e pessoa | Diária durante o evento | Horas | Assistência Social e Defesa Civil municipal; frequentemente em planilha |
| Formulários rápidos municipais | Ficha rápida de saúde pós-desastre (`docs/05-vigipos-barragens.md`, §4) | Localidade e evento | 2 vezes ao dia no agudo | Minutos a horas | Formulário próprio da plataforma — é a fonte que a plataforma cria |
| Registros da Defesa Civil | Desalojados, desabrigados, desaparecidos, óbitos preliminares, danos, vias interrompidas | Município e localidade | Diária | Horas | S2iD e sistema estadual; integração a acordar (**a validar**) |
| Farmácias e centrais de abastecimento | Estoque de medicamentos e insumos críticos, soro antiofídico, antibióticos, hipoclorito | Unidade de armazenamento | Diária | Horas | Sistema de gestão farmacêutica estadual (**a validar** qual) |
| Falta de energia elétrica | Interrupções por localidade | Localidade | Contínua | Minutos a horas | Concessionária de distribuição; requer acordo de compartilhamento |
| Falta de água | Interrupção de abastecimento, sistemas fora de operação | Sistema e localidade | Contínua | Minutos a horas | Concessionária e serviços autônomos municipais; requer acordo |

---

## 2.10 Matriz-resumo de latência

Ordenada da menor para a maior latência, porque é essa ordem que determina o que pode ser
usado para alerta e o que só serve para análise.

| Faixa de latência | Fontes | Uso possível |
| --- | --- | --- |
| Minutos | Telemetria da ANA e do empreendedor, SAMU, regulação, pluviômetro Cemaden | Alerta e resposta |
| 1 a 4 horas | INMET horário, GPM-IMERG Early Run, Sentinel-1 NRT, ficha rápida | Alerta |
| 4 a 24 horas | GPM-IMERG Late Run, SIGBM, Sentinel-1 padrão, GloFAS, registros de abrigo e de Defesa Civil | Acompanhamento do evento |
| Dias a semanas | SINAN, GAL/LACEN, e-SUS APS, Copernicus EMS | Vigilância pós-desastre |
| 1 a 3 meses | CNES, SIH, SIA, Sisagua | Linha de base e recuperação |
| Meses a anos | SIM, série consistida da ANA, GPM-IMERG Final Run | Excesso de mortalidade, climatologia, avaliação de impacto |

## 2.11 Pendências de acesso a resolver

| Pendência | Por que é bloqueante | Responsável proposto |
| --- | --- | --- |
| Acordo de compartilhamento de telemetria com empreendedores | Sem ele, os indicadores B5 e B6 do IDAP ficam permanentemente em lacuna para a maioria das barragens | SES-MT com órgãos fiscalizadores |
| Manchas de inundação (estudos de dam break) | Sem mancha, toda a dimensão C do IDAP é estimada por proxy | Empreendedores, via órgão fiscalizador |
| Cotas de alerta e de inundação por estação da ANA | Indicador A6 depende delas | ANA e Defesa Civil estadual |
| Fluxo de acionamento do Copernicus EMS | Precisa estar acordado antes do evento | Defesa Civil estadual |
| Endpoint programático estável do Cemaden | Hoje o acesso depende de interface de portal | Cemaden |
| Dataset de origem do SNISB junto à ANA | Elimina a dependência do endpoint interno do Power BI | ANA |
| Compartilhamento de interrupção de água e energia | Indicadores de serviços essenciais e do IRS dependem disso | Concessionárias |
