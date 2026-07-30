"""Índice documental para RAG leve — Onda 3.

Varre docs/*.md e gera um índice lexical (sem embeddings).
O Streamlit (Documentos / RAG leve) consome os mesmos arquivos diretamente;
este script publica um manifesto para auditoria e futuras embeddings.

Saída: dados/tratados/rag_docs_indice.json
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import comum

DOCS = comum.RAIZ / "docs"
SAIDA = comum.DADOS_TRATADOS / "rag_docs_indice.json"


def main() -> None:
    comum.DADOS_TRATADOS.mkdir(parents=True, exist_ok=True)
    itens = []
    for path in sorted(DOCS.glob("*.md")):
        texto = path.read_text(encoding="utf-8", errors="ignore")
        palavras = set(re.findall(r"[a-zà-ú0-9]{4,}", texto.lower()))
        itens.append(
            {
                "arquivo": path.name,
                "bytes": path.stat().st_size,
                "n_palavras_unicas": len(palavras),
                "titulo": next(
                    (ln.lstrip("# ").strip() for ln in texto.splitlines() if ln.startswith("#")),
                    path.name,
                ),
            }
        )
    manifesto = {
        "gerado": datetime.now().isoformat(timespec="seconds"),
        "modo": "lexical",
        "n_docs": len(itens),
        "docs": itens,
        "nota": "Embeddings / Gold RAG só após SITREP supervisionado e CNES/PAE mínimos.",
    }
    SAIDA.write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(itens)} docs → {SAIDA.name}")


if __name__ == "__main__":
    main()
