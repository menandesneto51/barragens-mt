# Cursor handoff — VIGIBARRAGENS v2.2 Inteligência

## Regra de trabalho

Este repositório é a fonte de verdade compartilhada entre ChatGPT, GitHub e Cursor. Antes de alterar código no Cursor:

1. checkout da branch `feat/vigibarragens-v2-foundation`;
2. `git pull`;
3. ler `AGENTS.md`, `PROJECT_CONTEXT.md`, `docs/governance/definition-of-done.md` e `docs/16-v2.2-inteligencia.md`;
4. preservar as decisões arquiteturais e metodológicas existentes;
5. nunca recalcular IDAP ou regras de sobreposição na camada Streamlit.

## Estado atual

A v2.2 mantém **IDAP + regras determinísticas** como única fonte do nível operacional. Inteligência, mudança, freshness, lineage e confiança da evidência são camadas explicativas e de governança.

Produtos relevantes:
- `idap_estadual_mt.csv` — estado operacional;
- `idap_evidencias_indicadores_mt.csv` — trilha A1…D8 produzida pelo próprio motor IDAP;
- `mudancas_recentes.csv` — eventos classificados da rodada;
- `inteligencia_estadual_mt.csv` — estado integrado v2.2;
- `proveniencia_freshness_mt.csv` — freshness semântico, fontes, proxies e estado da evidência.

## Próxima tarefa no Cursor

Executar o gate técnico da v2.2:

```powershell
cd barragens-mt
python -m pytest -q
python executar.py 17 19 16 35 36 37
streamlit run streamlit_app.py
```

Validar:
- etapa 16 gera `idap_evidencias_indicadores_mt.csv`;
- cada barragem possui uma linha por indicador aplicável A1…D8;
- soma de `pontos` por barragem = `idap` bruto, antes de regras de sobreposição;
- `versao_pesos` da evidência = versão do IDAP;
- Barragem 360° abre sem exceção e apresenta a trilha dos indicadores;
- freshness semântico usa `data_referencia`, nunca `mtime`;
- proxies Otto/territoriais permanecem explicitamente rotulados;
- nenhuma tela altera nível, pontos ou regra;
- nenhum segredo é versionado.

## Correções obrigatórias se algum teste falhar

Corrigir a causa no backend/contrato, não mascarar na UI. Adicionar teste de regressão correspondente. Não fazer merge na `main` sem aprovação explícita.

## Próximo incremento após o gate

Evoluir lineage por indicador para ligar `fonte_metodologica` à **fonte observacional efetivamente usada na rodada** (ex.: SisClima/TITAN/ANA/Cemaden/INMET/CNES/IBGE/SNISB/SIGBM), com timestamp de referência, run_id/hash quando disponíveis e classificação oficial/proxy/derivada.


## Gate automatizado no GitHub

O workflow `.github/workflows/vigibarragens-v22-ci.yml` executa:
- `python -m compileall` nos módulos críticos;
- `python -m pytest tests -q`.

O Cursor deve executar os mesmos testes antes de commit relevante. CI verde é condição necessária, mas não suficiente, para merge.

## Lineage observacional A1…D8

A etapa 16 agora anexa à trilha de cada indicador:
- produto observacional;
- campo observacional;
- fonte observacional;
- referência temporal quando disponível;
- tipo de evidência;
- método/proxy quando aplicável.

Regras atuais:
- A1–A7: produto hidrometeorológico normalizado;
- B1/B2/B3 e D1: cadastro oficial SNISB/SIGBM;
- C1/C3: proxies territoriais com IBGE/CNES + Otto provisório;
- C8: derivação operacional do cadastro;
- D8: validação operacional de contatos;
- indicadores ainda não implementados permanecem explicitamente `ausente`.

Nunca preencher lineage faltante por inferência silenciosa.


## Lineage temporal e fingerprint — estado atual

Cada linha de `idap_evidencias_indicadores_mt.csv` deve carregar, quando aplicável:
- `referencia_temporal`: data/período do dado;
- `artifact_materialized_at`: quando o arquivo local foi materializado;
- `artifact_sha256`: hash SHA-256 do artefato consumido;
- `artifact_size_bytes`;
- `run_id`: execução do pipeline que produziu a trilha.

Esses campos têm semânticas diferentes e não devem ser colapsados.

Referências atuais:
- A1–A7: `data_referencia` do produto hidro;
- C1: `ano_referencia` do IBGE;
- C3: maior `data_atualizacao` disponível no CNES consumido;
- D8: data crítica mais antiga do conjunto de contatos validado, pois é o elo que vence primeiro;
- B1/B2/B3/D1/C8: sem data semântica específica enquanto a fonte não expuser um campo inequívoco; usar apenas fingerprint/materialização do artefato, sem inferir data de validade.

O `executar.py` propaga `VIGIBARRAGENS_RUN_ID` e `VIGIBARRAGENS_STAGE` aos subprocessos. Não remover essa propagação.


## Auditoria R01–R12

A etapa 16 materializa `dados/tratados/idap_regras_lineage_mt.csv`.

Cada linha representa **uma regra disparada × uma evidência relacionada** e deve preservar:
- código e nome da regra;
- nível por pontuação e nível final;
- piso operacional da regra;
- fundamento;
- ação automática;
- código/tipo/valor da evidência;
- `evidencia_ativa` para distinguir o operando que efetivamente sustentou condições OR;
- produto/campo/fonte observacional;
- referência temporal;
- natureza da evidência;
- run_id e fingerprint do artefato quando disponíveis.

Regras de arquitetura:
1. `aplicar_regras()` continua sendo a única função decisória para R01–R12.
2. `rule_lineage.py` nunca reavalia condição nem altera nível.
3. Streamlit apenas lê `idap_regras_lineage_mt.csv`.
4. Sinais operacionais ainda não materializados devem permanecer como `sinal_sem_fonte_materializada`.
5. Não inferir origem de R02/R03/R05/R07/R08/R09 até existirem produtos persistentes correspondentes.
6. Evidência inativa em uma condição OR pode ser mostrada para auditabilidade, mas deve aparecer com `evidencia_ativa=False`.


## Etapa 38 — sinais operacionais persistentes

A ordem v2.2 agora é:

`17 hidro → 19 alertabilidade → 38 sinais operacionais → 16 IDAP → 35 mudanças → 36 inteligência → 37 proveniência`.

Arquivo persistente:
`dados/tratados/sinais_operacionais_mt.csv`

A etapa 38:
- adiciona barragens novas ao esqueleto;
- preserva valores existentes;
- mantém fonte, referência temporal, documento e observação;
- não confirma rompimento, evacuação, falha de sensores ou impacto de mancha por ausência/presunção;
- não deve sobrescrever evidência operacional humana ou oficial.

Quando um sinal persistido dispara R02/R03/R05/R07/R08/R09, o lineage deve apontar para esse arquivo e carregar seu hash/run_id. Sem fonte persistida, manter `sinal_sem_fonte_materializada`.

## Registro operacional governado — eventos append-only

Fonte de verdade:
`dados/metadata/sinais_operacionais_eventos.jsonl`

Materializações:
- `dados/tratados/sinais_operacionais_mt.csv` — estado largo consumido pelo motor;
- `dados/tratados/sinais_operacionais_estado_mt.csv` — estado longo por barragem × sinal, usado para auditoria e UI.

Registro explícito de evento:

```powershell
python scripts/39_registrar_sinal_operacional.py ^
  --id-snisb <ID> ^
  --signal rompimento_confirmado ^
  --action confirm ^
  --value sim ^
  --observed-at 2026-09-27T10:30:00-04:00 ^
  --source-type defesa_civil ^
  --source-name "Defesa Civil Municipal" ^
  --document-reference "SITREP 001/2026" ^
  --confirmed-by "Nome do responsável" ^
  --confirmer-role "Coordenador"
python executar.py 38 16 35 36 37
```

Para revogar/corrigir um fato, registrar novo evento com `--action revoke`. Nunca editar ou excluir linha anterior do JSONL.

Controles obrigatórios:
- barragem deve existir no inventário;
- sinal e tipo de fonte devem pertencer aos vocabulários permitidos;
- `observed_at`, fonte, responsável e função são obrigatórios;
- cada evento recebe UUID e SHA-256 canônico;
- revogação não apaga histórico;
- ausência de evento continua sendo lacuna, não normalidade;
- lineage de R02/R03/R05/R07/R08/R09 deve usar metadata específica do sinal, não metadata agregada da barragem.
