# Exercício de mesa — piloto Manso–Cuiabá

Roteiro operacional para CIEVS repetir o ciclo em 30–45 min.

## Automatizado (script 57)

- Barragem: **Barragem de Rejeitos Bom Futuro** (`5603`) — Amarelo
- `id_alerta`: `ALT-5603-20260830100000-930af2`
- Texto: `alertas/piloto/ciclo_amarelo_5603_ALT-5603-20260830100000-930af2.txt`
- Payload DC: `ok` → `dados/tratados/confirmacoes/payloads_defesa_civil/ALT-5603-20260830100000-930af2.json`
- Escalonamento forçado: **1** evento(s)
- Confirmação: **Plantão CIEVS (exercício de mesa)**
- Resumo ciclo: emitidos=1 confirmados=1

## Passos manuais (complemento)

1. Abrir **Alertabilidade** no Streamlit — conferir o alerta na tabela do ciclo.
2. Se emitir **Vermelho/Roxo**, preencher **Autorizar envio** (supervisor) antes do dry-run.
3. Em **Contatos**, filtrar cobrança **Só CIEVS** e anotar municípios sem telefone/e-mail.
4. Abrir a **ficha rápida** da barragem e o dossiê municipal (jusante).
5. Rodar dry-run: botão *Emitir + dry-run despacho* ou `python scripts/29_despacho_alertas.py --id-alerta <id>`.
6. Registrar confirmação na tela **Confirmação** (ou reexecutar este script).
7. Baixar SITREP do plantão (Comando) e o payload DC do alerta.

## Aceite

- Script retorna código 0.
- Artefatos em `dados/tratados/confirmacoes/`.
- Este markdown atualizado em `relatorios/exercicio_mesa_piloto.md`.

Gerado por `scripts/57_exercicio_mesa_piloto.py` em 2026-08-30T22:17:25.
