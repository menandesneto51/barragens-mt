# Fluxo de agentes

## Entrada

Toda feature, correção relevante ou alteração de regra inicia com uma ficha contendo problema, usuário, decisão apoiada, fontes afetadas, risco e critério de sucesso.

## Gate 1 — Produto

Product Owner define história, valor e critérios de aceite. Clinical Specialist participa quando houver interpretação sanitária/epidemiológica.

## Gate 2 — Arquitetura e dados

Chief Architect define impacto arquitetural. Data Architect e Data Governance definem contratos, modelo, temporalidade, qualidade e lineage. GIS é obrigatório para lógica territorial.

## Gate 3 — Implementação

API/Backend, AI/GIS e Frontend implementam conforme a natureza do slice. IA não substitui regras determinísticas.

## Gate 4 — Garantias

Performance revisa gargalos relevantes. Security revisa superfície de ataque e dados. QA executa testes e regressão. Observability/DevOps garante execução observável e implantação reproduzível.

## Gate 5 — Aceite arquitetural

Chief Architect verifica aderência aos ADRs, ausência de arquitetura paralela e compatibilidade com a migração incremental.

## Evidência mínima

PR deve registrar agentes aplicáveis, critérios de aceite, testes, fontes/versões, mudanças de schema, proxies, riscos conhecidos e decisão arquitetural quando necessária.
