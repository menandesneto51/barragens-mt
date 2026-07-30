# Contatos institucionais e alertabilidade — piloto Manso–Cuiabá

Gerado em 2026-07-30T19:04:24.

## Cadastro

- Linhas de contato: **88** (8 papéis × municípios do eixo)
- Com nome preenchido: **44**
- Com telefone/celular: **44**
- Com data de validação: **44**

## Alertabilidade das barragens do piloto

- Barragens avaliadas: **105**
- Alertáveis (vínculo completo validado): **104**

Enquanto `alertavel=não`, o alerta textual continua sendo gerado para treino/simulado, mas a barragem fica marcada como **não alertável** na operação (docs/04 §4.1–4.2).

## Como validar

1. Editar `dados/tratados/contatos_institucionais_piloto.csv`.
2. Preencher nome, telefone/e-mail e `data_validacao` (AAAA-MM-DD).
3. Rodar de novo `python scripts/19_contatos_alertabilidade.py` (preserva preenchimentos).
4. Recalcular IDAP/piloto (`16` → `18`) para propagar D8 e a flag.
