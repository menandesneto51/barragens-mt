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
