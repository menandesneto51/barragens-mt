"""Confere os campos dos trechos BHO e localiza o trecho do rio Cuiaba na capital."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import comum

CUIABA = (-56.0979, -15.6014)
MANSO = (-55.7847, -14.8731)


def distancia_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    raio = 6371.0
    lon1, lat1, lon2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    return 2 * raio * math.asin(
        math.sqrt(
            math.sin((lat2 - lat1) / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
        )
    )


def vertices(feicao: dict) -> list[tuple[float, float]]:
    geometria = feicao.get("geometry") or {}
    coordenadas = geometria.get("coordinates") or []
    if geometria.get("type") == "LineString":
        return [(c[0], c[1]) for c in coordenadas]
    pontos: list[tuple[float, float]] = []
    for parte in coordenadas:
        pontos.extend((c[0], c[1]) for c in parte)
    return pontos


def main() -> None:
    caminho = comum.DADOS_TRATADOS / "ana_bho_trechos_bacia_cuiaba.geojson"
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    feicoes = dados["features"]
    print(f"{len(feicoes)} trechos")
    print(f"campos: {sorted((feicoes[0].get('properties') or {}).keys())}\n")
    print("exemplo de propriedades:")
    for chave, valor in sorted((feicoes[0].get("properties") or {}).items()):
        print(f"  {chave:16s} {valor}")

    for rotulo, ponto in [("CUIABA (capital)", CUIABA), ("MANSO (barragem principal)", MANSO)]:
        print(f"\n{'=' * 70}\ntrechos mais proximos de {rotulo} {ponto}\n{'=' * 70}")
        candidatos = []
        for feicao in feicoes:
            pontos = vertices(feicao)
            if not pontos:
                continue
            perto = min(distancia_km(ponto, p) for p in pontos)
            candidatos.append((perto, feicao))
        candidatos.sort(key=lambda x: x[0])
        for perto, feicao in candidatos[:8]:
            propriedades = feicao.get("properties") or {}
            print(
                f"  {perto:7.2f} km  cobacia={propriedades.get('cobacia') or propriedades.get('COBACIA'):>16s}  "
                f"rio={(propriedades.get('noriocomp') or propriedades.get('NORIOCOMP') or '-')[:24]:26s} "
                f"areamont={propriedades.get('nuareamont') or propriedades.get('NUAREAMONT')}"
            )


if __name__ == "__main__":
    main()
