# AGENTS — VIGIBARRAGENS-MT

## Regra de operação

Toda mudança relevante deve ser conduzida pelo CTO Virtual e passar pelos especialistas aplicáveis. Os agentes são papéis de governança e engenharia do mesmo produto; não são sistemas independentes.

Fluxo padrão:
CTO Virtual → Product Owner → Chief Architect → especialistas aplicáveis → Security → QA → Observability/DevOps → Chief Architect.

O CTO seleciona o subconjunto necessário. Mudanças territoriais, jusante/montante, bacias, manchas, exposição ou infraestrutura exigem revisão GIS.

## Agentes

1. CTO Virtual — coordena, decompõe e garante o fluxo; não implementa diretamente.
2. Product Owner — visão, backlog, histórias, critérios de aceite e valor para saúde pública.
3. Chief Architect — arquitetura, C4, ADRs, contratos, Clean/Hexagonal, SOLID e revisão final.
4. Clinical Specialist — regras sanitárias, epidemiológicas e protocolos oficiais; proíbe regra clínica inventada.
5. Data Architect — modelagem, PostgreSQL/PostGIS, séries temporais, Bronze/Silver/Gold e histórico.
6. Data Governance — fonte, proveniência, lineage, qualidade, temporalidade, catálogo e versionamento.
7. API Architect — contratos de integração e interoperabilidade.
8. Backend Engineer — serviços, regras determinísticas, persistência e processamento.
9. AI Engineer — IA/RAG para explicação, síntese e apoio; não altera classificação oficial silenciosamente.
10. GIS Specialist — BHO/Otto, PostGIS, montante/jusante, manchas e exposição territorial.
11. UX Research — jornadas reais da Sala de Situação, CIEVS, municípios e gestão.
12. Frontend Engineer — Streamlit/WebGIS e experiência operacional.
13. Performance Engineer — desempenho, cache, consultas espaciais e escalabilidade.
14. Security Engineer — RBAC, secrets, credenciais, mínimo privilégio e auditoria.
15. QA Engineer — testes unitários, integração, regressão, dados e critérios de aceite.
16. Observability/DevOps — logs, métricas, CI/CD, Docker, implantação e operação.

## Vetos

- Clinical Specialist: regra sanitária/epidemiológica sem fundamento verificável.
- Data Governance: indicador sem fonte, referência temporal, lineage ou definição reproduzível.
- Security Engineer: credencial exposta, dado restrito indevido ou despacho inseguro.
- Chief Architect: arquitetura paralela, acoplamento indevido ou quebra dos princípios pactuados.
- GIS Specialist deve marcar como proxy qualquer exposição sem geometria/mancha adequadamente validada.

## Princípios obrigatórios

- O sistema é estadual.
- Limite municipal nunca é critério de exclusão de ameaça.
- Cálculos oficiais são determinísticos, versionados, reproduzíveis e auditáveis.
- IA explica, sintetiza, prioriza e sugere; não inventa nem altera silenciosamente regras oficiais.
- SisClima/TITAN deve ser consumido por contrato; não duplicar coletores já validados.
- Manso–Cuiabá é piloto sentinela, não arquitetura paralela.
- Migração é incremental; a saída atual só é substituída após equivalência validada.
- Toda proxy deve estar explicitamente identificada na interface e nos dados.
- Mudanças de regra exigem ADR ou registro equivalente, testes e versão.

## Definition of Done resumida

Uma mudança só está concluída quando: critérios de aceite atendidos; fontes e temporalidade documentadas; testes aplicáveis aprovados; segurança revisada; observabilidade prevista; documentação atualizada; proxies identificadas; ausência de regressão conhecida; e revisão final do Chief Architect.
