"""Checagem rapida do painel gerado: sintaxe do JavaScript e integridade dos dados.

Nao faz parte do pipeline. Extrai o ultimo bloco <script> do HTML e roda `node --check`
usando o Node que acompanha o Playwright, evitando dependencia externa.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import comum

PAINEL = comum.RAIZ / "painel" / "index.html"
NODE = comum.RAIZ / ".venv" / "Lib" / "site-packages" / "playwright" / "driver" / "node.exe"


def main() -> None:
    html = PAINEL.read_text(encoding="utf-8")
    print(f"painel: {len(html) / 1024:.0f} KB")

    blocos = re.findall(r"<script>(.*?)</script>", html, re.DOTALL)
    if not blocos:
        sys.exit("nenhum bloco <script> inline encontrado")
    codigo = blocos[-1]
    print(f"bloco JS: {len(codigo) / 1024:.0f} KB")

    for marcador in ("__DADOS__", "__MALHA__", "__DATA__"):
        if marcador in html:
            sys.exit(f"marcador {marcador} nao foi substituido")
    print("marcadores substituidos: ok")

    dados = re.search(r"const DADOS = (\[.*?\]);\n", codigo, re.DOTALL)
    if not dados:
        sys.exit("nao foi possivel isolar a constante DADOS")
    registros = json.loads(dados.group(1))
    print(f"registros embutidos: {len(registros)}")
    com_coordenada = sum(1 for r in registros if "la" in r and "lo" in r)
    com_cri = sum(1 for r in registros if r.get("cri"))
    print(f"  com coordenada: {com_coordenada} | com categoria de risco: {com_cri}")

    if not NODE.exists():
        print("node indisponivel; checagem de sintaxe ignorada")
        return

    with tempfile.TemporaryDirectory() as pasta:
        arquivo = Path(pasta) / "painel.js"
        arquivo.write_text(codigo, encoding="utf-8")
        resultado = subprocess.run(
            [str(NODE), "--check", str(arquivo)], capture_output=True, text=True
        )
    if resultado.returncode == 0:
        print("sintaxe do JavaScript: ok")
    else:
        print("sintaxe do JavaScript: ERRO")
        print(resultado.stderr[:2000])
        sys.exit(1)


if __name__ == "__main__":
    main()
