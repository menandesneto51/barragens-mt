# Streamlit Cloud — secrets de despacho (VIGI_*)

Cole em **App settings → Secrets** (formato TOML):

```toml
[vigi]
telegram_bot_token = "SEU_TOKEN"
telegram_chat_id = "SEU_CHAT_ID"
smtp_host = ""
smtp_port = "587"
smtp_user = ""
smtp_pass = ""
smtp_from = ""
```

O app lê esses campos via `scripts/29_despacho_alertas.py` (`credenciais_status` /
`_carregar_secrets_locais`). Sem token, o despacho permanece em **dry-run**.

Modelo versionado: [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example).
Detalhes: [`docs/04-alertas.md`](docs/04-alertas.md) §4.8.
