# 13. Gancho Defesa Civil — payload padronizado

> Especificação de **intercâmbio**, não de API inventada. O envio real depende de
> acordo institucional entre SES-MT / CIEVS e a Defesa Civil estadual.

## 13.1 Princípio

O VIGIBARRAGENS emite **prontidão sanitária** e texto territorializado. **Não** emite
ordem de evacuação. Qualquer payload para a Defesa Civil deve carregar essa ressalva.

## 13.2 Campos mínimos (JSON)

```json
{
  "sistema": "VIGIBARRAGENS-MT",
  "tipo": "alerta_prontidao_saude",
  "instante": "2026-07-30T12:00:00-04:00",
  "nivel": "Amarelo",
  "idap": 28,
  "barragem_id_snisb": "12345",
  "barragem_nome": "Exemplo",
  "municipio_sede": "Nobres",
  "municipios_potencialmente_afetados": ["Cuiabá", "Várzea Grande"],
  "papel_destinatario": "potencialmente_afetado_jusante",
  "coordenadas": { "lat": -14.7, "lon": -56.1 },
  "texto_resumo": "Prontidão sanitária — não é ordem de evacuação.",
  "texto_completo_ref": "alertas/piloto/....txt",
  "contato_ses": "CIEVS-MT",
  "canais_sugeridos": ["telefone", "email", "telegram"]
}
```

## 13.3 Confirmação

- Persistência: `dados/tratados/confirmacoes/confirmacoes.csv` (Streamlit) e/ou
  painel HTML (localStorage — protótipo).
- Prazos por nível: ver `docs/04-alertas.md` e `painel/confirmacao_alerta.html`.

## 13.4 Despacho técnico

- Script: `scripts/29_despacho_alertas.py` (Telegram primeiro, SMTP depois).
- Dry-run por padrão; envio real só com variáveis `VIGI_TELEGRAM_*` / `VIGI_SMTP_*`.
- Credenciais locais: `dados/tratados/despacho_secrets.env` (modelo `.example`, não versionado)
  ou Streamlit secrets `[vigi]`.

## 13.5 Destinatários de e-mail

| Papel no CSV | Quem deveria receber | Status atual no repositório |
| --- | --- | --- |
| `cievs` | CIEVS / SES-MT (plantão) | Sem e-mail — preencher |
| `gestor_municipal_saude` | SMS do município sede/afetado | Sem e-mail — telefone exercício |
| `vigilancia_saude` | Vigilância municipal | Sem e-mail — telefone exercício |
| `defesa_civil_municipal` | Coordenação DC municipal | Sem e-mail — telefone exercício |
| `samu` / `hospital_referencia` / `vigiagua` / `concessionaria_agua` | Rede de resposta | Esqueleto — validar |

Fluxo operacional (pode esperar o arquivo completo da SES):

1. Quando o cadastro completo chegar, importar na tela **Alertabilidade / despacho**
   em modo **replace** (ou `python scripts/36_contatos_importar_emails.py arquivo.csv --modo replace`).
2. Alternativa parcial: baixar o modelo de 88 linhas do eixo, preencher só `email`, importar em **patch**.
3. Rodar `python executar.py 19 16 18` para propagar flag alertável / D8.
4. Configurar SMTP/Telegram (`despacho_secrets.env.example`) e fazer dry-run → envio em exercício.

Enquanto o arquivo não chega, telefones de exercício já destravam D8 no eixo — e-mail não é bloqueante.

Registros de impacto (aba **Notificações e impactos**) geram texto em `alertas/piloto/notif_*.txt`
e entram na mesma fila de despacho.

## 13.6 Parceria (checklist)

1. Definir ponto focal DC estadual e municipal do eixo.
2. Validar contatos em `contatos_institucionais_piloto.csv` (telefone **e** e-mail).
3. Acordar se o receptor é e-mail institucional, grupo Telegram ou sistema próprio.
4. Testar payload em ambiente de exercício (sem público).
5. Documentar que evacuação permanece exclusividade da Defesa Civil.
