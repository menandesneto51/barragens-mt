"""Sondagem: verifica o que o SipamHidro (Censipam) expoe do produto 'Anomalia Bacias'.

Nao faz parte do pipeline. O briefing do Produto 04 nomeia essa fonte explicitamente,
entao o relatorio precisa dizer com precisao o que ela oferece e o que nao oferece.
"""

from __future__ import annotations

import re
import warnings

import httpx

warnings.filterwarnings("ignore")

NAVEGADOR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

ALVOS = {
    "portal SipamHidro": "https://hidro.sipam.gov.br/",
    "anomalia de bacias": "https://hidro.sipam.gov.br/anomalia",
    "api de estacoes": "https://hidro.sipam.gov.br/api/estacoes",
    "panorama Censipam": "https://panorama.sipam.gov.br/home",
}


def main() -> None:
    with httpx.Client(timeout=120, verify=False, follow_redirects=True, headers=NAVEGADOR) as cli:
        for rotulo, url in ALVOS.items():
            print(f"\n{'=' * 70}\n{rotulo}\n{url}\n{'=' * 70}")
            try:
                resposta = cli.get(url)
                tipo = resposta.headers.get("content-type") or ""
                print(f"  HTTP {resposta.status_code} | {tipo} | {len(resposta.content) // 1024} KB")
                if "json" in tipo:
                    print(f"  corpo: {resposta.text[:400]}")
                    continue
                texto = resposta.text
                titulo = re.search(r"<title[^>]*>(.*?)</title>", texto, re.S | re.I)
                if titulo:
                    print(f"  título: {titulo.group(1).strip()[:120]}")
                # Um SPA entrega apenas o esqueleto; os termos abaixo indicam se ha
                # conteudo servido no HTML ou se tudo vem por JavaScript.
                for termo in ("anomalia", "bacia", "download", "geoserver", "wms", "api"):
                    print(f"  ocorrências de {termo!r}: {len(re.findall(termo, texto, re.I))}")
                scripts = re.findall(r'src="([^"]+\.js[^"]*)"', texto)
                print(f"  scripts carregados: {scripts[:5]}")
            except Exception as exc:  # noqa: BLE001
                print(f"  ERRO {type(exc).__name__} {str(exc)[:160]}")


if __name__ == "__main__":
    main()
