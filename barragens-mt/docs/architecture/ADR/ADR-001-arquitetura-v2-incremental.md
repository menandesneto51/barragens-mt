# ADR-001 — Evolução incremental para a arquitetura VIGIBARRAGENS v2

Status: Aceito

## Contexto

O sistema atual entrega valor operacional por scripts Python, CSVs, Streamlit e HTML, enquanto a arquitetura documentada aponta PostgreSQL/PostGIS, histórico, serviços analíticos e observabilidade. Uma reescrita integral criaria risco operacional e duplicaria funcionalidades maduras.

## Decisão

Adotar migração incremental.

1. Preservar saídas atuais durante a transição.
2. Introduzir pacote de domínio e camada de repositórios.
3. Implantar auditabilidade, snapshots e detecção de mudanças antes da troca de persistência.
4. Adotar PostgreSQL/PostGIS como fonte central progressivamente.
5. Manter CSV como contrato transitório enquanto houver consumidores dependentes.
6. Consumir SisClima/TITAN por contrato, sem duplicação desnecessária de coletores.
7. Manter Manso–Cuiabá como piloto sentinela dentro da arquitetura estadual.
8. Exigir equivalência validada antes de substituir qualquer saída operacional.

## Consequências

A migração será mais gradual, porém reduz risco de regressão. Durante o período transitório haverá coexistência controlada entre arquivos e banco, exigindo lineage e testes de equivalência.

## Restrições

Nenhum novo módulo deve criar uma segunda fonte de verdade para o mesmo conceito. Proxies territoriais devem ser identificadas até substituição por geometria validada.
