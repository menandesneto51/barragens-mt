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

`scripts/17_hidro_sisclima_titan.py`:

- resolve o banco via `VIGIBARRAGENS_SISCLIMA_DB` ou, na ordem, `sis_cloud_seed.db`
  (preferido — tem `precipitacao_mm`) e `sis_integrado.db`;
- lê `met_biometeo`, `solo_saturacao_municipal`, `hidro_risco_municipal` /
  `ana_risco_municipal`;
- grava `hidro_municipios_mt.csv` e `hidro_barragens_mt.csv` (A1, A2, A5, A6 proxy, A7);
- A3 (previsão) e A4 (percentil) ficam vazios no contrato atual;
- `16_idap_estadual.py` preenche `PressaoHidroclimatica` a partir de `hidro_barragens_mt.csv`.

Aproximação espacial atual: **máximo entre município-sede e municípios a montante**
(Otto), rotulado `sede_mais_montante_max`. Agregação areal na BHO estadual completa
permanece pendente (§12.3).

## 12.5 Telemetria fluviométrica ANA (contexto — não mancha)

Etapas `52` (auditoria) e `53` (vínculo estação↔barragem):

| Variável SisClima / env | Papel |
| --- | --- |
| `USE_ANA=true` | Popula `ana_estacoes` no SQLite |
| `ANA_FETCH_SERIES=true` | Baixa séries `cota` / `vazao` / `chuva` (default `false` = só metadados) |
| `ANA_HIDROWEB_TOKEN` | Auth HidroWeb v3 |
| `ANA_ESTACOES_CSV` / `ANA_TELEMETRIA_CSV` | Fallback offline |
| Fallback local | `dados/brutos/ana_estacoes_mt.csv`, `ana_telemetria.csv`, `ana_cotas_alerta_mt.csv` |

Saídas: `auditoria_ana_sisclima.json`, `ana_estacoes_barragem.csv`; mescla em `hidro_barragens_mt.csv` de `cota_cm`, `vazao_m3s` e, **quando houver cota de alerta**, `razao_nivel_cota_alerta` com `a6_fonte=cota_medida` (substitui o proxy de cor de alerta do estágio 17).

**Fronteira de produto:** cota/vazão ANA alimentam o bloco “Contexto fluvial” na Simulação e o IDAP A6. **Não** redimensionam Circular / Trajeto / HAND — não são dam break nem mancha PAE.

## 12.6 Próximo / fora de escopo

- Agregação areal chuva/solo na BHO estadual completa
- Mancha de inundação / dam break
- Validação telefônica dos contatos (`19_contatos_alertabilidade.py` gera o esqueleto)
- Reimplementar APIs INMET/Cemaden/ANA já cobertas pelo SIS/TITAN
- Cotas oficiais de alerta por estação (hoje há amostra de demonstração em `ana_cotas_alerta_mt.csv`)

O piloto (`18`) e a ficha rápida (`painel/ficha_rapida.html`) já consomem esta hidro.
