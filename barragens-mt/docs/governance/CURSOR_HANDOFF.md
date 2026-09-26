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
