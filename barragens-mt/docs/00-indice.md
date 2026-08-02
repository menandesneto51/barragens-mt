# 0. Índice da documentação

Documentação técnica da plataforma **VIGIBARRAGENS–MT / Saúde 360** — alerta precoce,
monitoramento de impactos e vigilância pós-desastre associada a barragens em Mato Grosso.

Toda a documentação está em português do Brasil. Onde uma pontuação, um limiar, uma latência ou
uma escolha tecnológica é proposta deste projeto e não valor oficial, está marcada como
**proposta a validar**.

## Como ler esta documentação

| Se você é... | Leia nesta ordem |
| --- | --- |
| Gestor ou tomador de decisão | 01 → 08 → 07 |
| Especialista que vai validar o índice | 03 → 02 → 09 |
| Epidemiologista ou vigilância em saúde | 05 → 02 → 01 |
| Desenvolvedor ou analista de dados | 09 → 06 → 03 → `scripts/idap/` |
| Responsável por comunicação e alerta | 04 → 01 |
| Quem só quer saber o que existe hoje | 08 §8.1 → 09 §9.9 |

## Documentos

### [01. Visão geral](01-visao-geral.md)

Conceito da plataforma: o que ela é, para quem serve e o que ela deliberadamente **não** faz.
Detalha os cinco momentos operacionais — Normalidade, Pré-impacto, Impacto, Pós-impacto agudo e
Recuperação — com objetivo, dados de entrada, produtos gerados e atores responsáveis de cada
um, e explica a aderência à diretriz do Vigidesastres. Contém a declaração de escopo negativo
mais importante de toda a documentação: o sistema **não calcula probabilidade automática de
rompimento**, porque isso exigiria modelos de engenharia e instrumentação da estrutura; ele
calcula nível de atenção e prontidão para o setor saúde.

### [02. Fontes de dados](02-fontes-de-dados.md)

Catálogo completo das fontes, com endpoint real, o que cada uma fornece, granularidade,
periodicidade, latência, forma de acesso e limitações conhecidas. Cobre cadastro e regulação
(SNISB, SIGBM/ANM, SEMA-MT, ANEEL, empreendedores), hidrometeorologia terrestre (INMET, Cemaden,
ANA/RHN), chuva por satélite (GPM-IMERG), sensoriamento remoto (Sentinel-1, Sentinel-2, Landsat,
CBERS), Copernicus EMS, GloFAS, sistemas de informação em saúde (CNES, SINAN, SIM, SIH, SIA,
e-SUS APS, SISREG, SAMU, GAL/LACEN, Sisagua, Renaveh) e fontes operacionais quase em tempo real.
Justifica a adoção da expressão **tempo quase real** e registra explicitamente por que o SIM não
serve para alerta imediato, por que a oportunidade do SINAN varia por agravo, e por que o CNES
— capacidade cadastrada — precisa ser complementado por informação operacional do momento.

### [03. IDAP-Barragens](03-idap.md)

Especificação completa do **Índice Dinâmico de Alerta e Prontidão**, escala 0–100, em quatro
dimensões: A — Pressão hidroclimática (30 pontos), B — Condição da barragem (30), C — Impacto
sanitário potencial (25) e D — Déficit de capacidade de resposta (15). Para cada um dos 29
indicadores define fonte, unidade, janela temporal, faixas de pontuação, tratamento de dado
ausente e frequência de recálculo. Define as cinco faixas de classificação, o cálculo de
completude, a governança e o versionamento dos pesos para auditoria, e as nove **regras
determinísticas de sobreposição** (R01 a R09) que elevam o nível independentemente da pontuação.
Deixa explícito que os pesos são inicialmente metodológicos e precisam de validação por
especialistas em engenharia de barragens, hidrologia, meteorologia, epidemiologia, saúde
ambiental, assistência, Defesa Civil e geoprocessamento.

### [04. Alertas](04-alertas.md)

Modelo de emissão territorializada. Estabelece que cada barragem precisa ter vínculo **prévio**
com municípios potencialmente atingidos, regiões de saúde, gestores municipais, Vigilância em
Saúde, Defesa Civil, SAMU, hospitais de referência, vigilância da qualidade da água, CIEVS,
concessionárias, transporte sanitário, empreendedor e órgãos fiscalizadores — porque cadastro
construído durante a crise já chega tarde. Traz o template de conteúdo mínimo do alerta, com
exemplo completo, os canais de entrega (painel web, e-mail, SMS, Teams, aplicativo, WhatsApp
Business quando autorizado, ligação automática em alerta crítico e integração com a Defesa
Civil) e a **máquina de estados de entrega**: um alerta só é considerado entregue após
confirmação de recebimento, identificação do responsável e registro da hora, com escalonamento
automático e prazos definidos por nível.

### [05. VIGIPÓS-BARRAGENS](05-vigipos-barragens.md)

Módulo de vigilância em saúde pós-desastre. Define os gatilhos de ativação, a construção da
linha de base pré-desastre com SIM, SINAN e CNES, e especifica campo a campo a **ficha rápida de
saúde pós-desastre** nos blocos Evento, Saúde, Serviços e Água e ambiente. Traz a fórmula
explícita de todos os indicadores pós-desastre: mortalidade e lesões, vigilância epidemiológica
com razão observado/esperado e as nove síndromes recomendadas, água e saneamento, rede
assistencial com o **IPAPD** (Índice de Pressão Assistencial Pós-Desastre), abrigos, e
recuperação com o **IRS** (Índice de Recuperação Sanitária). Detalha os métodos de detecção
automática de excesso de agravos — canal endêmico, CUSUM, EWMA, Poisson, binomial negativa,
bayesianos, controle sintético e séries temporais interrompidas — com recomendação de uso por
situação e o exemplo trabalhado de leptospirose. Deixa explícito que a detecção deve ser feita
por algoritmo estatístico reproduzível: a IA pode explicar o sinal, não produzi-lo.

### [06. Arquitetura](06-arquitetura.md)

Arquitetura de referência em cinco camadas — fontes, ingestão, banco central, motores analíticos
e saídas — com esboço do modelo de dados relacional (tabelas, chaves e o motivo de separar
`classificacao` de `barragem`). Contém a recomendação estratégica central: **não tentar construir
tudo dentro do Power BI**, com o quadro do que ele não resolve e a divisão de responsabilidades
recomendada entre Power BI para gestão, PostGIS/WebGIS para território, Python para ETL e
modelos, banco de séries temporais para sensores, e serviço específico para envio e confirmação
de alertas. Inclui os usos apropriados da IA e seus **limites obrigatórios**, além da seção de
proteção de dados (LGPD) para o dado de saúde identificável — incluindo a tensão real entre
proteger o dado e localizar o paciente em diálise que mora na ZAS.

### [07. Telas](07-telas.md)

As oito telas da plataforma, cada uma com propósito, público-alvo, widgets, indicadores,
filtros, granularidade e fonte de cada elemento: Comando estadual, Monitoramento ambiental,
Barragem 360°, Alerta antecipado, Impacto observado, Vigilância pós-desastre, Assistência e
logística, e Recuperação. Cada tela traz um quadro de **viabilidade hoje**, separando o que é
construível com os dados já coletados do que depende de integração futura — e a síntese é
direta: hoje existe inventário, não monitoramento. Fecha com os requisitos transversais de
interface, entre eles o de que dado velho nunca pode ter aparência de dado novo.

### [08. Roadmap](08-roadmap.md)

Plano de implantação em quatro fases — piloto Cuiabá, expansão estadual, vigilância
pós-desastre, IA e simulação — cada uma com entregáveis, pré-requisitos, riscos e critérios de
aceite verificáveis. Abre com a seção **"o que já está pronto"**, com os coletores existentes e
os números reais coletados, e fecha com a sequência mínima recomendada para o caso de equipe
escassa: integrar o CNES, coletar chuva, cadastrar contatos institucionais, obter manchas de
inundação e testar a ficha rápida em simulado.

### [09. Dicionário de dados](09-dicionario-de-dados.md)

Dicionário dos conjuntos **já coletados**, com nomes de coluna extraídos dos próprios arquivos:
SNISB (1.248 registros, 45 colunas), SIGBM (183 registros, 127 colunas), IBGE, Power BI e
inventário consolidado. Para cada campo: origem, tipo, domínio de valores, obrigatoriedade e uso
previsto no IDAP. Contém a seção de qualidade de dados com as **lacunas medidas** nos CSVs — e o
achado central de que campo preenchido não é campo informativo — a divergência entre 142
municípios e 141 polígonos, e a seção "Dependências adicionais sugeridas", que registra as
dependências propostas sem alterar o `requirements.txt`.

### [11. Princípio estadual e sequência](11-principio-estadual-e-sequencia.md)

O sistema é **estadual**; o município de sede não limita o impacto. Define impacto
extraterritorial por drenagem, a ordem fixa base estadual → SisClima/TITAN → piloto, e o
mapeamento preliminar dos indicadores hidroclimáticos para as fontes já validadas no CIEVS MT.

### [12. Integração SisClima / TITAN](12-integracao-sisclima-titan.md)

Contrato e implementação (`17_hidro_sisclima_titan.py`) do consumo da hidro CIEVS MT na
dimensão A do IDAP, sem recriar coletores. Piloto Manso–Cuiabá: `18_piloto_manso_cuiaba.py`.
Contatos/alertabilidade: `19_contatos_alertabilidade.py`. Ficha rápida (simulado):
`painel/ficha_rapida.html`.

### [13. Gancho Defesa Civil](13-defesa-civil-gancho.md)

Payload padronizado de prontidão sanitária para articulação com a Defesa Civil (sem inventar
API nem ordem de evacuação). Despacho técnico: `scripts/29_despacho_alertas.py`.

### [14. Secrets Streamlit (despacho)](14-streamlit-secrets-despacho.md)

Como colar `[vigi]` no Streamlit Cloud para Telegram/SMTP. Dry-run funciona sem credenciais.

### [15. Integração IndicaSUS / DW de saúde](15-integracao-indicasus-dw.md)

Leitos e ocupação via IndicaSUS/DW (etapa `43`), conector extensível para SIH/SIA/SISREG/SINAN,
preenchimento do D6 (`razao_leitos_demanda`) e métricas na Simulação.

### [10. Glossário](10-glossario.md)

Siglas e termos, organizados em marco regulatório e cadastro de barragens, vigilância em saúde e
gestão de desastres, sistemas de informação em saúde, índices e conceitos criados neste projeto,
fontes de dado ambiental e sensoriamento, e termos técnicos de arquitetura. Inclui PNSB, SNISB,
SIGBM, CRI, DPA, PAE, PAEBM, ZAS, ZSS, DCE, DCO, RISR, RPSB, descaracterização, alteamento a
montante/jusante/linha de centro, back up dam, linha de praia, mancha de inundação,
Vigidesastres, Vigiagua, CIEVS, COE, SITREP, APS, IDAP, IPAPD, IRS e tempo quase real.

## Implementação de referência

### `scripts/idap/`

Pacote Python que torna o IDAP **executável, testável e auditável**, usando apenas a biblioteca
padrão do Python 3.12 — nenhuma dependência externa, deliberadamente, porque o motor de cálculo
do alerta é a parte do sistema que menos pode falhar por problema de ambiente.

| Módulo | Conteúdo |
| --- | --- |
| `modelo.py` | *Dataclasses* do estado de uma barragem em um instante, com campos opcionais para representar dado ausente |
| `pesos.py` | Pesos, tetos e faixas de pontuação em estrutura versionada (`VERSAO_PESOS`), para que recalibrar não exija mexer na lógica |
| `calculo.py` | Funções puras que pontuam cada dimensão, somam o IDAP, classificam na faixa, devolvem a justificativa por indicador e informam a completude |
| `regras.py` | As nove regras determinísticas de sobreposição, aplicadas após o índice |
| `relatorio.py` | Geração do texto do alerta no template de `docs/04-alertas.md` |
| `exemplo.py` | Quatro cenários fictícios e plausíveis de MT, executável sem rede e sem arquivos de entrada |
| `testes.py` | Testes com `unittest`: tetos por dimensão, limites de 0–100, fronteiras exatas das cinco faixas, efeito de cada regra, dado ausente que não infla pontuação e reprodutibilidade |

Execução, a partir da raiz do projeto:

```powershell
python scripts\idap\exemplo.py
python scripts\idap\testes.py
```

## Convenções adotadas em toda a documentação

| Convenção | Detalhe |
| --- | --- |
| Idioma | Português do Brasil, inclusive em identificadores de código, docstrings e comentários |
| Fuso horário | Horário de Cuiabá (UTC−4), sempre escrito junto ao horário |
| Coordenadas | EPSG:4326, graus decimais |
| Incerteza | Toda proposta deste projeto que não seja valor oficial está marcada como **proposta a validar** |
| Dado ausente | Ausência é registrada como ausência, nunca como zero e nunca como "sem risco" |
| Referência cruzada | Citações usam número de documento e seção, por exemplo `docs/03-idap.md` §3.10 |
