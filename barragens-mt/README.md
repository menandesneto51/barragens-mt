# Sistema de Monitoramento de Barragens — Mato Grosso

Pipeline de coleta, consolidação e visualização das barragens cadastradas em Mato
Grosso, a partir das bases oficiais dos quatro órgãos que fiscalizam segurança de
barragens no estado.

**Situação atual:** 1.248 barragens cadastradas, em 115 dos 141 municípios.

## O que já está pronto

| Entregável | Caminho |
| --- | --- |
| Painel de monitoramento interativo | `painel/index.html` |
| Mapas cartográficos | `figuras/mapa_barragens_mt_cri.png`, `figuras/mapa_barragens_mt_orgao.png` |
| Relatório de diagnóstico | `relatorios/diagnostico_barragens_mt.md` |
| Inventário consolidado | `dados/tratados/inventario_barragens_mt.csv` e `.geojson` |

O painel é um arquivo HTML autocontido: abre com duplo clique, sem servidor. Traz mapa
filtrável, indicadores, gráficos por classificação de risco, fila de priorização e
tabela pesquisável com exportação para CSV.

## Como executar

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python executar.py
```

Para rodar etapas isoladas: `python executar.py 05 06 07`.

## Fontes de dados

| Fonte | O que fornece | Como é acessada | Atualização |
| --- | --- | --- | --- |
| **SNISB / SNIRH** (ANA) | Cadastro consolidado das barragens de todos os fiscalizadores, com 43 atributos e coordenadas | Serviço ArcGIS REST | Contínua |
| **Painel público do SNISB** (ANA) | O mesmo cadastro, porém com 73 atributos no modelo semântico | API pública do Power BI (publish-to-web, anônima) | Contínua |
| **SIGBM** (ANM) | Barragens de mineração com 124 atributos de engenharia e emergência | CSV em `dadosabertos.anm.gov.br` | Diária |
| **IBGE** | Malha municipal, códigos oficiais e regionalização | API de localidades e de malhas | Anual |

A SEMA-MT fiscaliza 63% do inventário e alimenta o SNISB diretamente, conforme as
Instruções Normativas nº 02/2020 e nº 04/2021. Não existe API estadual independente:
o SNISB é o ponto de coleta para as barragens estaduais.

### Por que duas fontes para o mesmo cadastro

O serviço ArcGIS expõe 43 campos; o modelo por trás do painel público expõe 73. Campos
decisivos para priorizar fiscalização — comprimento do coroamento, data da última
fiscalização, data da última autuação e tipo de empreendedor — só existem no segundo.
O script `04_powerbi_snisb.py` consulta esse modelo e casa os resultados por
`BAR_CD_SNISB`. As duas fontes retornam as mesmas 1.248 barragens, o que serve de
verificação cruzada.

## Estrutura

```
scripts/
  comum.py                    utilidades compartilhadas (HTTP, CSV, GeoJSON)
  01_snisb_mt.py              inventário SNISB, por atributo e por envelope espacial
  02_sigbm_anm.py             barragens de mineração, com conversão de coordenadas DMS
  03_ibge_mt.py               municípios, malha municipal e contorno das UFs
  04_powerbi_snisb.py         atributos complementares, com decodificação do formato DSR
  05_consolidar_inventario.py junção das fontes e tratamento de qualidade
  06_mapas.py                 pranchas cartográficas
  07_painel.py                gerador do painel HTML
  08_diagnostico.py           relatório em Markdown
  _sondar_powerbi.py          exploração do modelo do Power BI (fora do pipeline)
  _validar_painel.py          checagem do painel gerado (fora do pipeline)
dados/
  brutos/                     respostas cruas das APIs (regeneráveis, fora do Git)
  tratados/                   CSV e GeoJSON prontos para uso
```

## Dicionário do inventário consolidado

`dados/tratados/inventario_barragens_mt.csv` — separador `;`, codificação UTF-8 com BOM.

### Identificação

| Campo | Descrição |
| --- | --- |
| `id_snisb` | Identificador da barragem no SNISB — chave primária |
| `nome`, `nome_secundario` | Denominação da barragem |
| `empreendedor`, `tipo_empreendedor` | Responsável legal pela estrutura |
| `orgao_fiscalizador` | SEMA-MT, ANM, ANEEL ou ANA |
| `codigo_no_orgao_fiscalizador` | Identificador no sistema do órgão |

### Localização

| Campo | Descrição |
| --- | --- |
| `latitude`, `longitude` | Coordenadas em SIRGAS 2000 (EPSG:4674), vindas da geometria |
| `latitude_declarada`, `longitude_declarada` | Coordenadas do formulário, mantidas para conferência |
| `municipio`, `codigo_ibge` | Município normalizado contra a base do IBGE |
| `mesorregiao`, `regiao_intermediaria` | Regionalização do IBGE |
| `corpo_hidrico`, `curso_dagua`, `dominio_curso_dagua` | Corpo hídrico barrado e sua dominialidade |
| `regiao_hidrografica`, `comite_de_bacia_estadual` | Recorte de gestão de recursos hídricos |

### Características físicas

| Campo | Descrição |
| --- | --- |
| `altura_m` | Altura máxima em metros, com o sinal corrigido |
| `altura_max_terreno_m`, `altura_max_fundacao_m` | Valores originais do cadastro |
| `capacidade_hm3` | Capacidade do reservatório em **hm³** (milhões de m³) |
| `capacidade_m3` | Mesma capacidade convertida para m³ |
| `comprimento_coroamento_m` | Comprimento da crista |
| `tipo_material` | Terra, enrocamento, concreto etc. |
| `uso_principal`, `uso_complementar` | Finalidade da barragem |
| `fase_de_vida` | Projeto, construção, operação, desativada, descaracterizada |

### Classificação e conformidade

| Campo | Descrição |
| --- | --- |
| `categoria_risco` | CRI — condição da estrutura e do seu gerenciamento |
| `dano_potencial_associado` | DPA — consequência de um eventual rompimento |
| `classe_cnrh` | Classe A a E, pelo cruzamento CRI × DPA (Resolução CNRH nº 143/2012) |
| `prioridade_fiscalizacao` | Escala 1 a 9, produto dos pesos de CRI e DPA |
| `regulada_pelo_pnsb` | Se está sujeita à Lei Federal 12.334/2010 |
| `possui_plano_de_seguranca`, `possui_pae`, `possui_revisao_periodica` | Instrumentos exigidos pela PNSB |
| `data_ultima_inspecao`, `data_ultima_fiscalizacao`, `data_ultima_autuacao` | Marcos de acompanhamento |
| `barragem_autuada`, `nivel_de_perigo` | Situação de enforcement |
| `completude_cadastro` | Índice de completude atribuído pelo próprio SNISB |

### Mineração (apenas para barragens casadas com o SIGBM)

| Campo | Descrição |
| --- | --- |
| `sigbm_metodo_construtivo`, `sigbm_tipo_alteamento` | Método de alteamento — o de montante é proibido pela Resolução ANM nº 95/2022 |
| `sigbm_nivel_emergencia` | Sem emergência, Nível de Alerta, Emergência Nível 1 a 3 |
| `sigbm_situacao_operacional`, `sigbm_status_dce` | Operação e Declaração de Condição de Estabilidade |
| `sigbm_populacao_jusante`, `sigbm_pessoas_afetadas` | Exposição a jusante |

### Sinalizadores de qualidade

| Campo | Descrição |
| --- | --- |
| `alerta_altura_negativa` | Altura declarada abaixo de zero na fonte |
| `alerta_coordenada` | Coordenada fora do envelope de Mato Grosso |
| `origem_do_registro` | Se o registro veio do filtro por UF ou do filtro espacial |

## Cuidados com os dados

- **Unidade da capacidade.** O campo `BAR_NU_CAP_TOTAL_RESERV` do SNISB é publicado em
  hm³, apesar do nome sugerir m³. O inventário expõe as duas colunas para evitar erro de
  escala de seis ordens de grandeza.
- **Nome de município.** Os órgãos alimentam o SNISB com caixa e acentuação
  inconsistentes, o que produz 150 nomes distintos para 141 municípios. A consolidação
  normaliza contra o IBGE e anexa o código municipal.
- **Cobertura da classificação.** 362 barragens (29%) não têm CRI e DPA definidos
  simultaneamente e ficam fora de qualquer priorização por risco.
- **Casamento com o SIGBM.** Feito por nome e município, já que o SIGBM não carrega o
  identificador do SNISB; 177 das 183 barragens de mineração casaram.

## Próximas etapas do sistema

A coleta e o diagnóstico cobrem o retrato estático do inventário. Para virar
monitoramento de fato, faltam:

1. **Histórico.** Executar o pipeline em cadência fixa e versionar cada extração, para
   detectar mudança de classificação, novas autuações e alteração de nível de emergência.
2. **Alertas.** Disparar notificação quando uma barragem mudar de nível de emergência,
   entrar em classe A, vencer o prazo de revisão periódica ou perder a DCE.
3. **Chuva e imagem de satélite.** Cruzar com precipitação (CEMADEN, INMET, satélite GPM)
   e com séries Sentinel-1/2 para acompanhar a lâmina d'água dos reservatórios críticos.
4. **Exposição a jusante.** Estimar população e infraestrutura na mancha de inundação
   das barragens de classe A, combinando setores censitários do IBGE com modelo de
   propagação.
5. **Publicação.** Servir o painel como página estática com atualização automática.
