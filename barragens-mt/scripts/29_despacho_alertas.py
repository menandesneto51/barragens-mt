"""Despacho unificado de alertas (Telegram → e-mail) — Onda 2.

Lê textos em alertas/piloto/ e contatos em dados/tratados/.
Por padrão roda em dry-run (só grava log). Envio real exige variáveis de ambiente:

  VIGI_TELEGRAM_BOT_TOKEN  — token do bot
  VIGI_TELEGRAM_CHAT_ID    — chat/grupo destino (piloto)
  VIGI_SMTP_HOST / VIGI_SMTP_PORT / VIGI_SMTP_USER / VIGI_SMTP_PASS / VIGI_SMTP_FROM

Uso:
  python scripts/29_despacho_alertas.py           # dry-run
  python scripts/29_despacho_alertas.py --enviar  # tenta canais configurados
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import smtplib
import ssl
import urllib.error
import urllib.parse
import urllib.request
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import comum

FILA = comum.RAIZ / "alertas" / "piloto"
LOG = comum.DADOS_TRATADOS / "despacho_alertas_log.csv"
CONTATOS = comum.DADOS_TRATADOS / "contatos_institucionais_piloto.csv"


def ler_contatos() -> list[dict[str, str]]:
    if not CONTATOS.exists():
        return []
    with CONTATOS.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def textos_fila() -> list[Path]:
    if not FILA.exists():
        return []
    return sorted(FILA.glob("*.txt"))


def enviar_telegram(texto: str) -> tuple[bool, str]:
    token = os.environ.get("VIGI_TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("VIGI_TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat:
        return False, "credenciais Telegram ausentes"
    body = urllib.parse.urlencode(
        {"chat_id": chat, "text": texto[:3900], "disable_web_page_preview": "true"}
    ).encode()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        req = urllib.request.Request(url, data=body, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status == 200, f"http {resp.status}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, str(exc)


def enviar_email(assunto: str, texto: str, destinatarios: list[str]) -> tuple[bool, str]:
    host = os.environ.get("VIGI_SMTP_HOST", "").strip()
    user = os.environ.get("VIGI_SMTP_USER", "").strip()
    password = os.environ.get("VIGI_SMTP_PASS", "").strip()
    remetente = os.environ.get("VIGI_SMTP_FROM", user).strip()
    port = int(os.environ.get("VIGI_SMTP_PORT", "587") or "587")
    if not host or not remetente or not destinatarios:
        return False, "SMTP ou destinatários ausentes"
    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = ", ".join(destinatarios)
    msg.set_content(texto)
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.starttls(context=context)
            if user and password:
                smtp.login(user, password)
            smtp.send_message(msg)
        return True, f"enviado a {len(destinatarios)} destino(s)"
    except (OSError, smtplib.SMTPException) as exc:
        return False, str(exc)


def emails_piloto(limite: int = 20) -> list[str]:
    outs: list[str] = []
    for c in ler_contatos():
        em = (c.get("email") or "").strip()
        if "@" in em and em not in outs:
            outs.append(em)
        if len(outs) >= limite:
            break
    return outs


def gravar_log(linhas: list[dict[str, Any]]) -> None:
    comum.DADOS_TRATADOS.mkdir(parents=True, exist_ok=True)
    campos = ["instante", "arquivo", "canal", "status", "detalhe", "dry_run"]
    existe = LOG.exists()
    with LOG.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";")
        if not existe:
            w.writeheader()
        for row in linhas:
            w.writerow({k: row.get(k, "") for k in campos})


def despachar(*, dry_run: bool = True, limite: int = 30) -> int:
    agora = dt.datetime.now().isoformat(timespec="seconds")
    arquivos = textos_fila()[:limite]
    if not arquivos:
        print("nenhum texto em alertas/piloto/")
        return 0
    logs: list[dict[str, Any]] = []
    emails = emails_piloto()
    for path in arquivos:
        texto = path.read_text(encoding="utf-8", errors="ignore")
        assunto = f"[VIGIBARRAGENS] {path.stem}"
        if dry_run:
            logs.append(
                {
                    "instante": agora,
                    "arquivo": path.name,
                    "canal": "telegram+email",
                    "status": "dry-run",
                    "detalhe": f"chars={len(texto)}; emails_piloto={len(emails)}",
                    "dry_run": "sim",
                }
            )
            continue
        ok_tg, det_tg = enviar_telegram(texto)
        logs.append(
            {
                "instante": agora,
                "arquivo": path.name,
                "canal": "telegram",
                "status": "ok" if ok_tg else "falha",
                "detalhe": det_tg,
                "dry_run": "não",
            }
        )
        ok_em, det_em = enviar_email(assunto, texto, emails)
        logs.append(
            {
                "instante": agora,
                "arquivo": path.name,
                "canal": "email",
                "status": "ok" if ok_em else "falha",
                "detalhe": det_em,
                "dry_run": "não",
            }
        )
    gravar_log(logs)
    print(f"despacho: {len(logs)} registro(s) → {LOG.name} (dry_run={dry_run})")
    return len(logs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Despacho de alertas VIGIBARRAGENS")
    parser.add_argument("--enviar", action="store_true", help="Tenta envio real (requer env)")
    parser.add_argument("--limite", type=int, default=30)
    args = parser.parse_args()
    despachar(dry_run=not args.enviar, limite=args.limite)


if __name__ == "__main__":
    main()
