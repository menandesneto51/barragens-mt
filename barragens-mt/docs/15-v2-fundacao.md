# VIGIBARRAGENS v2.1 — Fundação

## Objetivo

Evoluir o sistema sem interromper o painel atual. A v2.1 introduz auditabilidade, histórico e qualidade e prepara a migração progressiva de CSV para PostgreSQL/PostGIS.

## Princípios preservados

- abrangência estadual;
- limite municipal não exclui ameaça;
- Manso–Cuiabá permanece piloto sentinela, não arquitetura paralela;
- SisClima/TITAN continua como fonte hidrometeorológica integrada, sem duplicação de coletores;
- Streamlit permanece operacional durante a migração;
- fontes não oficiais ou frágeis não podem ser dependência crítica.

## Componentes iniciais

### Manifesto de execução

Cada execução passa a poder registrar identificador, início/fim, status, estágios, contagens de entrada/saída, hash da fonte e erros. Os manifestos serão persistidos em dados/metadata/runs enquanto a camada PostgreSQL não estiver ativa.

### Snapshot histórico

Cada inventário consolidado poderá gerar snapshot datado e hash SHA-256. A comparação entre snapshots produz eventos de alteração por barragem.

Campos prioritários: CRI, DPA, classe CNRH, nível de emergência, DCE, PAE, inspeção, fiscalização, completude, nível VIGIBARRAGENS e IDAP.

### Eventos de mudança

A camada de eventos será a base para responder: o que mudou desde a última execução, quais barragens pioraram, quais documentos venceram e quais municípios a jusante precisam de nova avaliação.

## Próximas integrações

1. acoplar manifesto ao executar.py sem quebrar a execução atual;
2. gerar snapshot após consolidação do inventário/IDAP;
3. classificar criticidade dos eventos;
4. criar painel de mudanças recentes;
5. definir esquema PostgreSQL/PostGIS e migração dual-write;
6. incorporar testes ao CI.

## Regra de migração

Nenhuma etapa v2 substitui uma saída operacional atual até que a nova implementação produza resultado equivalente, auditável e validado.
