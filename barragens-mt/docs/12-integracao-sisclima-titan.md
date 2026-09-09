# 12. Integração hidrometeorológica — SIS Clima Saúde e TITAN

> Etapa `17_hidro_sisclima_titan.py` no pipeline (roda antes do IDAP `16`). Não
> reimplementar coleta: consome o SQLite já validado pelo CIEVS MT.

## 12.1 Repositórios de referência

| Sistema | Caminho no ambiente | Documentação-chave |
| --- | --- | --- |
| SIS Clima Saúde | `OneDrive/CIEVS MT/SIS-Monitoramento-Clima-Saude-GITHUB-LIMPO` | `docs/ARQUITETURA.md`, `docs/TEMPO_REAL.md`, `docs/VISAO_OPERACIONAL_SIS_CLIMA_SAUDE.md` |
| TITAN (camada no SIS) | mesmo repositório + material em `CIEVS MT/Prêmio de inovação TITAN` e `Área de Trabalho/TITAN_V40_DEV` | `docs/INTEGRACAO_TITAN_SOLO_ALERTAS.md`, `docs/SENTINELA_SG_E_ANA.md` |

## 12.2 Contratos de dado a consumir

| Tabela / produto (SIS/TITAN) | Indicador IDAP | Observação |
| --- | --- | --- |
| Precipitação municipal (Open-Meteo / estações) | A1, A2, A7 | Agregar à bacia contribuinte da barragem (não só ao município-sede) |
| Previsão de chuva | A3 | Mesma granularidade espacial |
| `indice_saturacao_solo` / `solo_saturacao_municipal` | A5 | TITAN |
| `ana_risco_municipal` / telemetria ANA | A6 | Nível vs. cota de alerta |
| `inmet_alertas`, `cemaden_alertas` | regras R0x de chuva extrema | Consolidados em `alerta_integrado_sis_titan` |
| `hidro_risco_municipal` | contexto operacional | Não substitui mancha de inundação |

## 12.3 Regra espacial

Chuva e solo do **município-sede** da barragem são proxy insuficiente. O coletor deve:

1. identificar a área de drenagem a montante da estrutura (BHO / Otto);
2. agregar precipitação e saturação sobre essa área;
3. se a agregação por bacia ainda não existir no SIS, usar o município-sede **e** os
   municípios imediatamente a montante, rotulando a aproximação.

## 12.4 Entregável (implementado)

`scripts/59_sisclima_cloud_seed.py` + `scripts/17_hidro_sisclima_titan.py`:

- o clone público do SisClima só tem `sis_integrado.db` sanitizado (sem solo TITAN,
  sem `inmet_alertas`/`cemaden_alertas`, sem `ana_*`). Solo TITAN institucional,
  alertas e séries ANA reais exigem `sis_cloud_seed.db` com `USE_ANA=true` +
  `ANA_FETCH_SERIES=true` no ETL SisClima (CIEVS/OneDrive) **ou** a etapa `59`, que
  monta `dados/brutos/sisclima/sis_cloud_seed.db` com o mesmo contrato via fontes
  públicas (INMET, Cemaden `wsAlertas2`, ANA SOAP, solo Open-Meteo proxy);
- a etapa 17 resolve o banco via `VIGIBARRAGENS_SISCLIMA_DB` ou, na ordem,
  `dados/brutos/sisclima/sis_cloud_seed.db`, `../sisclima-repo/data/cloud/…`, e
  `sis_integrado.db`;
- lê `met_biometeo`, `solo_saturacao_municipal`, `hidro_risco_municipal` /
  `ana_risco_municipal`, `inmet_alertas`, `cemaden_alertas`;
- se `met_biometeo` existir **sem** coluna de chuva (caso comum do `sis_integrado.db`
  sanitizado), complementa precipitação observada com **Open-Meteo** nas coordenadas
  municipais do próprio banco (`fonte=openmeteo_sisclima_fallback`) e segue o ETL;
- grava `hidro_municipios_mt.csv` e `hidro_barragens_mt.csv` (A1, A2, A5, A6 proxy, A7);
- A3 (previsão) vem do Open-Meteo ECMWF; A4 (percentil) é estimado na série espacial;
- `16_idap_estadual.py` preenche `PressaoHidroclimatica` a partir de `hidro_barragens_mt.csv`.

Telemetria pontual no eixo (etapa `39`) continua disponível como overlay no ponto da
barragem quando se quer reforçar A1–A4 sem depender do SQLite municipal.
Aproximação espacial atual: **máximo entre município-sede e municípios a montante**
(Otto), rotulado `sede_mais_montante_max`. Agregação areal na BHO estadual completa
permanece pendente (§12.3).

### Receita rápida — refresh hidro + IDAP (preserva A6)

O pipeline padrão já encadeia `59 → 17 → 60 → 52 → 53 → 16`. Atalho explícito
(incluindo overlay pontual 39 e painéis):

```bash
python executar.py 59 17 39 60 52 53 16 18 20 21
```

Sem `52/53` (ou `60`), um refresh só com a etapa 17 deixa `a6_fonte=cota_medida`
vazio — a cota medida só entra no vínculo estação↔barragem.

## 12.5 Telemetria fluviométrica ANA (contexto — não mancha)

Etapas `60` (cotas de alerta), `52` (auditoria) e `53` (vínculo estação↔barragem):

| Variável SisClima / env | Papel |
| --- | --- |
| `USE_ANA=true` | Popula `ana_estacoes` no SQLite |
| `ANA_FETCH_SERIES=true` | Baixa séries `cota` / `vazao` / `chuva` (default `false` = só metadados) |
| `ANA_HIDROWEB_TOKEN` | Auth HidroWeb v3 |
| `ANA_ESTACOES_CSV` / `ANA_TELEMETRIA_CSV` | Fallback offline |
| Fallback local | `dados/tratados/ana_*_sample.csv` (e opcionalmente `dados/brutos/ana_*.csv`) |

Saídas: `auditoria_ana_sisclima.json`, `ana_estacoes_barragem.csv`; mescla em `hidro_barragens_mt.csv` de `cota_cm`, `vazao_m3s` e, **quando houver cota de alerta**, `razao_nivel_cota_alerta` com `a6_fonte=cota_medida` (substitui o proxy de cor de alerta do estágio 17).

**Fronteira de produto:** cota/vazão ANA alimentam o bloco “Contexto fluvial” na Simulação e o IDAP A6. **Não** redimensionam Circular / Trajeto / HAND — não são dam break nem mancha PAE.

## 12.5bis IndicaSUS / leitos (termo O do IPAPD)

Checklist de carga (capacidade assistencial):

1. Extrato IndicaSUS/DW com leitos operacionais, ocupados e disponíveis por município (e, se possível, por CNES).
2. Enquanto o DW não estiver disponível no ambiente, `python executar.py 56` popula o **eixo piloto** a partir de `dados/config/exemplos/indicasus_leitos.exemplo.csv` (`fonte=seed_exemplo_eixo`).
3. Substituir os CSVs seed pelo extrato oficial e rodar a etapa `43` quando o conector DW estiver ativo.
4. Status em `dados/tratados/indicasus_leitos_status.json` (visível na Simulação / DW status).

## 12.6 Cotas de alerta (etapa 60)

`scripts/60_ana_cotas_alerta.py` lê, nesta ordem:

1. `dados/brutos/ana_cotas_alerta_mt.csv` (oficial, quando a SES/Defesa Civil entregar)
2. `dados/tratados/ana_cotas_alerta_mt_sample.csv` (demonstração — fonte `ANA_SAMPLE`)

Aplica `cota_alerta_cm` no seed SQLite (`ana_telemetria`) e grava
`dados/tratados/ana_cotas_alerta_status.json` para a faixa A8 distinguir sample vs
oficial. Em seguida a etapa `53` calcula `razao_nivel_cota_alerta` com
`a6_fonte=cota_medida` nas barragens ≤30 km.

## 12.7 Próximo / fora de escopo

- Agregação areal chuva/solo na BHO estadual completa
- Mancha de inundação / dam break
- Validação telefônica dos contatos (`19_contatos_alertabilidade.py` gera o esqueleto)
- Reimplementar APIs INMET/Cemaden/ANA já cobertas pelo SIS/TITAN

O piloto (`18`) e a ficha rápida (`painel/ficha_rapida.html`) já consomem esta hidro.
