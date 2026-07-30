"""Utilidades compartilhadas pelos scripts de coleta do inventario de barragens de MT."""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

import httpx

RAIZ = Path(__file__).resolve().parent.parent
DADOS_BRUTOS = RAIZ / "dados" / "brutos"
DADOS_TRATADOS = RAIZ / "dados" / "tratados"
RELATORIOS = RAIZ / "relatorios"

UF_SIGLA = "MT"
UF_CODIGO_IBGE = 51

# Envelope de Mato Grosso em EPSG:4326, com folga de ~0.2 grau para pegar registros
# cadastrados com coordenada levemente deslocada.
BBOX_MT = (-61.85, -18.25, -50.00, -7.15)

TIMEOUT = httpx.Timeout(120.0, connect=30.0)
CABECALHOS = {
    "User-Agent": "monitoramento-barragens-mt/0.1 (coleta de dados publicos)",
    "Accept-Language": "pt-BR,pt;q=0.9",
}


def preparar_diretorios() -> None:
    for caminho in (DADOS_BRUTOS, DADOS_TRATADOS, RELATORIOS):
        caminho.mkdir(parents=True, exist_ok=True)


def cliente(verificar_tls: bool = True) -> httpx.Client:
    """Cliente HTTP com redirecionamentos habilitados.

    Alguns portais federais servem cadeias de certificado incompletas; nesses casos
    o chamador passa verificar_tls=False.
    """
    return httpx.Client(
        timeout=TIMEOUT,
        headers=CABECALHOS,
        follow_redirects=True,
        verify=verificar_tls,
    )


def requisitar_json(
    cli: httpx.Client,
    url: str,
    parametros: dict[str, Any] | None = None,
    tentativas: int = 4,
) -> dict[str, Any]:
    erro: Exception | None = None
    for tentativa in range(1, tentativas + 1):
        try:
            resposta = cli.get(url, params=parametros)
            resposta.raise_for_status()
            return resposta.json()
        except Exception as exc:  # noqa: BLE001 - queremos reagir a qualquer falha de rede
            erro = exc
            espera = 2**tentativa
            print(f"    tentativa {tentativa}/{tentativas} falhou ({exc}); aguardando {espera}s")
            time.sleep(espera)
    raise RuntimeError(f"falha ao obter {url}") from erro


def salvar_json(caminho: Path, conteudo: Any) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8") as arquivo:
        json.dump(conteudo, arquivo, ensure_ascii=False, indent=1)
    print(f"  gravado {caminho.relative_to(RAIZ)}")


def salvar_csv(caminho: Path, registros: Sequence[dict[str, Any]], colunas: Iterable[str]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    colunas = list(colunas)
    # utf-8-sig para o Excel em pt-BR abrir os acentos corretamente.
    with caminho.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas, delimiter=";", extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(registros)
    print(f"  gravado {caminho.relative_to(RAIZ)} ({len(registros)} registros)")


def salvar_geojson(
    caminho: Path,
    registros: Sequence[dict[str, Any]],
    campo_lon: str = "longitude",
    campo_lat: str = "latitude",
) -> None:
    feicoes = []
    for registro in registros:
        lon, lat = registro.get(campo_lon), registro.get(campo_lat)
        if lon is None or lat is None:
            continue
        propriedades = {k: v for k, v in registro.items() if k not in {campo_lon, campo_lat}}
        feicoes.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": propriedades,
            }
        )
    salvar_json(caminho, {"type": "FeatureCollection", "features": feicoes})
    print(f"  {len(feicoes)} de {len(registros)} registros tinham coordenada valida")


def dentro_do_bbox(lon: float | None, lat: float | None) -> bool:
    if lon is None or lat is None:
        return False
    oeste, sul, leste, norte = BBOX_MT
    return oeste <= lon <= leste and sul <= lat <= norte
