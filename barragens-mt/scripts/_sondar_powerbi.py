"""Sondagem exploratoria do relatorio Power BI publicado (publish-to-web).

Nao faz parte do pipeline: serve para descobrir o modelo semantico por tras do painel
e quais tabelas/colunas podem ser consultadas anonimamente.

O visualizador chama um host "-api" derivado do cluster: o sufixo "-redirect" e
removido do primeiro rotulo do hostname e "-api" e acrescentado.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import httpx

warnings.filterwarnings("ignore")

CHAVE = "6efe9238-3013-4c9b-801f-82d47d834186"
CLUSTER = "https://wabi-brazil-south-d-primary-api.analysis.windows.net"
SAIDA = Path("dados/brutos")

CABECALHOS = {
    "Accept": "application/json",
    "X-PowerBI-ResourceKey": CHAVE,
    "ActivityId": "11111111-1111-1111-1111-111111111111",
    "RequestId": "22222222-2222-2222-2222-222222222222",
    "Origin": "https://app.powerbi.com",
    "Referer": "https://app.powerbi.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0",
}


def resumir_visual(container: dict) -> str:
    config = container.get("config")
    if not config:
        return "(sem config)"
    try:
        cfg = json.loads(config)
    except (TypeError, json.JSONDecodeError):
        return "(config ilegivel)"
    unico = cfg.get("singleVisual", {})
    tipo = unico.get("visualType", "?")
    titulo = ""
    for objeto in (unico.get("vcObjects", {}) or {}).get("title", []):
        expr = ((objeto.get("properties", {}) or {}).get("text", {}) or {}).get("expr", {})
        titulo = (expr.get("Literal", {}) or {}).get("Value", "").strip("'")
    campos = []
    for projecoes in (unico.get("projections", {}) or {}).values():
        for projecao in projecoes:
            campos.append(projecao.get("queryRef", "?"))
    return f"{tipo:22s} {titulo[:38]:40s} {', '.join(campos[:6])}"


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    # O ambiente tem proxy TLS interceptador; o conteudo e publico e anonimo.
    with httpx.Client(timeout=90, headers=CABECALHOS, follow_redirects=True, verify=False) as cli:
        print("1) modelsAndExploration")
        resposta = cli.get(
            f"{CLUSTER}/public/reports/{CHAVE}/modelsAndExploration",
            params={"preferReadOnlySession": "true"},
        )
        resposta.raise_for_status()
        corpo = resposta.json()
        (SAIDA / "powerbi_modelsAndExploration.json").write_text(
            json.dumps(corpo, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print(f"   salvo ({len(resposta.text)} bytes) | chaves: {list(corpo.keys())}")

        for modelo in corpo.get("models", []):
            print(f"   modelId={modelo.get('id')} dbName={modelo.get('dbName')}")

        exploracao = corpo.get("exploration", {}) or {}
        print(f"\n   nome do relatorio: {exploracao.get('name')}")
        for secao in exploracao.get("sections", []):
            containers = secao.get("visualContainers", [])
            print(f"\n   PAGINA '{secao.get('displayName')}' ({len(containers)} visuais)")
            for container in containers:
                print(f"      {resumir_visual(container)}")

        print("\n2) conceptualschema")
        esquema = cli.get(f"{CLUSTER}/public/reports/{CHAVE}/conceptualschema")
        print(f"   HTTP {esquema.status_code} ({len(esquema.text)} bytes)")
        if esquema.status_code == 200:
            dados = esquema.json()
            (SAIDA / "powerbi_conceptualschema.json").write_text(
                json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8"
            )
            for schema in dados.get("schemas", []):
                for entidade in schema.get("schema", {}).get("Entities", []):
                    propriedades = [p.get("Name") for p in entidade.get("Properties", [])]
                    print(f"   TABELA {entidade.get('Name')} ({len(propriedades)} colunas)")
                    for nome in propriedades:
                        print(f"        - {nome}")


if __name__ == "__main__":
    main()
