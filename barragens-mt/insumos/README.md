# insumos/

Documentos oficiais recebidos de fora do projeto, transcritos para markdown, e a análise de como
eles se relacionam com o que foi construído aqui.

Nada nesta pasta é gerado pelo pipeline (`executar.py`). São insumos e leitura crítica.

## Conteúdo

| Arquivo | O que é |
| --- | --- |
| `extrair_docx.py` | Conversor de `.docx` para markdown preservando títulos, listas, tabelas e imagens, com marcação explícita de trechos não transcritíveis |
| `produto-04/especificacao_funcional_tecnica_v1_0.md` | Transcrição literal da Especificação Funcional e Técnica VIGIBARRAGENS–MT Saúde v1.0 (29/07/2026). Documento oficial de referência |
| `produto-04/matriz_responsabilidades_revisada.md` | Transcrição do Produto 04 de seca/estiagem (2025). Ciclo anterior, serve de precedente metodológico |
| `produto-04/analise-de-aderencia.md` | Comparação entre o documento oficial, o repositório e a concepção discutida em chat: o que está atendido, o que falta, o que excede e onde há contradição |

## Dependência

A transcrição usa `python-docx`, instalado no `.venv` do projeto mas **não declarado** em
`requirements.txt` nem em `requirements-dev.txt`, por serem arquivos de outra frente de trabalho:

```
.venv\Scripts\pip install python-docx
```

Como o conversor não faz parte do pipeline, a ausência da dependência não quebra `executar.py`.

## Uso do conversor

```
.venv\Scripts\python insumos\extrair_docx.py <origem.docx> <destino.md> [--figuras PASTA] [--prefixo NOME]
```

Trechos que o markdown não representa — SmartArt, gráficos do Word, equações, tabelas aninhadas —
são marcados como `**[LACUNA: ...]**` no ponto correspondente, para que a transcrição não passe
falsa impressão de completude. Texto dentro de caixas de texto é recuperado e sinalizado.
