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

_CHAVES_ENV = (
    "VIGI_TELEGRAM_BOT_TOKEN",
    "VIGI_TELEGRAM_CHAT_ID",
    "VIGI_SMTP_HOST",
    "VIGI_SMTP_PORT",
    "VIGI_SMTP_USER",
    "VIGI_SMTP_PASS",
    "VIGI_SMTP_FROM",
)


_ALIAS_SECRET = {
    "VIGI_TELEGRAM_BOT_TOKEN": ("telegram_bot_token", "TELEGRAM_BOT_TOKEN"),
    "VIGI_TELEGRAM_CHAT_ID": ("telegram_chat_id", "TELEGRAM_CHAT_ID"),
    "VIGI_SMTP_HOST": ("smtp_host", "SMTP_HOST"),
    "VIGI_SMTP_PORT": ("smtp_port", "SMTP_PORT"),
    "VIGI_SMTP_USER": ("smtp_user", "SMTP_USER"),
    "VIGI_SMTP_PASS": ("smtp_pass", "SMTP_PASS"),
    "VIGI_SMTP_FROM": ("smtp_from", "SMTP_FROM"),
}


def _pegar_secret(fonte: Any, *nomes: str) -> str | None:
    for nome in nomes:
        try:
            if hasattr(fonte, "get"):
                val = fonte.get(nome)
            else:
                val = fonte[nome]  # type: ignore[index]
        except Exception:  # noqa: BLE001
            val = None
        if val not in (None, ""):
            return str(val)
    return None


def _carregar_secrets_locais() -> None:
    """Injeta secrets do Streamlit / arquivo local se as env vars estiverem vazias."""
    # 1) Streamlit secrets (Cloud / local .streamlit/secrets.toml)
    try:
        import streamlit as st  # type: ignore

        sec = getattr(st, "secrets", None)
        if sec is not None:
            try:
                bloco = sec["vigi"]
            except Exception:  # noqa: BLE001
                bloco = sec
            for chave, aliases in _ALIAS_SECRET.items():
                if os.environ.get(chave):
                    continue
                val = _pegar_secret(bloco, chave, *aliases)
                if val:
                    os.environ[chave] = val
    except Exception:  # noqa: BLE001
        pass

    # 2) Arquivo simples dados/tratados/despacho_secrets.env (não versionar)
    env_path = comum.DADOS_TRATADOS / "despacho_secrets.env"
    if not env_path.exists():
        return
    for linha in env_path.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        k, _, v = linha.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k in _CHAVES_ENV and v and not os.environ.get(k):
            os.environ[k] = v


def credenciais_status() -> dict[str, bool]:
    _carregar_secrets_locais()
    return {
        "telegram": bool(
            os.environ.get("VIGI_TELEGRAM_BOT_TOKEN") and os.environ.get("VIGI_TELEGRAM_CHAT_ID")
        ),
        "smtp": bool(os.environ.get("VIGI_SMTP_HOST") and os.environ.get("VIGI_SMTP_FROM")),
    }


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
    _carregar_secrets_locais()
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
    _carregar_secrets_locais()
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
    campos = ["instante", "arquivo", "canal", "status", "detalhe", "dry_run", "id_alerta"]
    existe = LOG.exists()
    # Se log legado sem id_alerta, ainda grava com extrasaction ignore via DictWriter campos fixos
    with LOG.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";", extrasaction="ignore")
        if not existe:
            w.writeheader()
        for row in linhas:
            w.writerow({k: row.get(k, "") for k in campos})


def _id_alerta_do_arquivo(path: Path, texto: str) -> str:
    # Nome ciclo_*_ALT-...txt ou linha "Identificador do alerta"
    stem = path.stem
    if "ALT-" in stem:
        return "ALT-" + stem.split("ALT-", 1)[1]
    for linha in texto.splitlines()[:20]:
        if "Identificador do alerta" in linha and ":" in linha:
            return linha.split(":", 1)[1].strip()
    return ""


def _bloquear_por_supervisao(id_alerta: str) -> str | None:
    """Retorna motivo de bloqueio se alerta do ciclo ainda aguarda supervisão."""
    if not id_alerta:
        return None
    try:
        import sys

        root = Path(__file__).resolve().parents[1]
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from st_app.ciclo_alerta import carregar_alertas, pode_despachar

        al = carregar_alertas()
        if al.empty:
            return None
        hit = al[al["id_alerta"].astype(str) == id_alerta]
        if hit.empty:
            return None
        ok, motivo = pode_despachar(hit.iloc[0])
        if not ok:
            return motivo
    except Exception:  # noqa: BLE001
        return None
    return None


def despachar(
    *,
    dry_run: bool = True,
    limite: int = 30,
    apenas_arquivo: str | None = None,
    id_alerta: str | None = None,
) -> int:
    agora = dt.datetime.now().isoformat(timespec="seconds")
    if apenas_arquivo:
        path = FILA / apenas_arquivo
        arquivos = [path] if path.is_file() else []
    elif id_alerta:
        arquivos = [p for p in textos_fila() if id_alerta in p.name or id_alerta in p.read_text(encoding="utf-8", errors="ignore")[:500]]
        arquivos = arquivos[:limite]
    else:
        arquivos = textos_fila()[:limite]
    if not arquivos:
        print("nenhum texto em alertas/piloto/")
        return 0
    logs: list[dict[str, Any]] = []
    emails = emails_piloto()
    for path in arquivos:
        texto = path.read_text(encoding="utf-8", errors="ignore")
        id_a = id_alerta or _id_alerta_do_arquivo(path, texto)
        bloqueio = _bloquear_por_supervisao(id_a)
        assunto = f"[VIGIBARRAGENS] {path.stem}"
        if bloqueio:
            logs.append(
                {
                    "instante": agora,
                    "arquivo": path.name,
                    "canal": "—",
                    "status": "bloqueado",
                    "detalhe": bloqueio,
                    "dry_run": "sim" if dry_run else "não",
                    "id_alerta": id_a,
                }
            )
            continue
        if dry_run:
            logs.append(
                {
                    "instante": agora,
                    "arquivo": path.name,
                    "canal": "telegram+email",
                    "status": "dry-run",
                    "detalhe": f"chars={len(texto)}; emails_piloto={len(emails)}",
                    "dry_run": "sim",
                    "id_alerta": id_a,
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
                "id_alerta": id_a,
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
                "id_alerta": id_a,
            }
        )
    gravar_log(logs)
    print(f"despacho: {len(logs)} registro(s) → {LOG.name} (dry_run={dry_run})")
    return len(logs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Despacho de alertas VIGIBARRAGENS")
    parser.add_argument("--enviar", action="store_true", help="Tenta envio real (requer env)")
    parser.add_argument("--limite", type=int, default=30)
    parser.add_argument("--arquivo", type=str, default=None, help="Despacha só este .txt da fila")
    parser.add_argument("--id-alerta", type=str, default=None, help="Filtra pelo id_alerta do ciclo")
    args = parser.parse_args()
    despachar(
        dry_run=not args.enviar,
        limite=args.limite,
        apenas_arquivo=args.arquivo,
        id_alerta=args.id_alerta,
    )


if __name__ == "__main__":
    main()
