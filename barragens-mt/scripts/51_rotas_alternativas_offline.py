"""KPI de rotas alternativas offline (C7/D7) no eixo Manso–Cuiabá.

Usa a malha tratada (`malha_dnit_osm_eixo.geojson`) sem Overpass — adequado
para notebook/local. Calcula sedes→hub Cuiabá antes/depois de remover trechos
que cruzam um círculo proxy na APM Manso.

Saídas:
  dados/tratados/rotas_alternativas_offline_eixo.csv
  relatorios/rotas_alternativas_offline_eixo.md

Uso:
  python scripts/51_rotas_alternativas_offline.py
  python executar.py 51
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import comum

# Garante import do pacote st_app a partir da raiz do projeto
sys.path.insert(0, str(comum.RAIZ))

from st_app.malha_offline import malha_offline_elements  # noqa: E402
from st_app.sedes_municipais import sedes_candidatas  # noqa: E402
from st_app.vias_isolamento import analisar_isolamento  # noqa: E402

SAIDA = comum.DADOS_TRATADOS / "rotas_alternativas_offline_eixo.csv"
REL = comum.RELATORIOS / "rotas_alternativas_offline_eixo.md"

# APM Manso (aprox.) — ponto de referência do piloto
MANSO = {"lat": -14.941, "lon": -55.789, "raio_km": 18.0}
HUB = {"la": -15.5989, "lo": -56.0949, "nome": "Cuiabá (hub ref.)"}


def main() -> None:
    comum.DADOS_TRATADOS.mkdir(parents=True, exist_ok=True)
    comum.RELATORIOS.mkdir(parents=True, exist_ok=True)

    offline = malha_offline_elements(
        lat=MANSO["lat"], lon=MANSO["lon"], raio_km=45.0
    )
    n_el = len(offline.get("elements") or [])
    if n_el == 0:
        REL.write_text(
            "# Rotas alternativas offline\n\nMalha offline vazia — rode a etapa 42.\n",
            encoding="utf-8",
        )
        print("ERRO: malha offline vazia")
        return

    sedes = sedes_candidatas(
        so_eixo=True,
        lat=MANSO["lat"],
        lon=MANSO["lon"],
        raio_km=80.0,
    )
    # Força uso da malha offline: monkey via cache file? Melhor: chamar analisar
    # com bbox do eixo e injetar elements — analisar_isolamento busca Overpass.
    # Workaround: grava cache OSM sintético no path esperado.
    from st_app import vias_isolamento as vi

    south = MANSO["lat"] - 0.9
    north = MANSO["lat"] + 0.35
    west = MANSO["lon"] - 0.9
    east = MANSO["lon"] + 0.55
    payload = malha_offline_elements(
        south=south, west=west, north=north, east=east
    )
    # Patch temporário da busca bbox
    original = vi.buscar_malha_osm_bbox

    def _offline_bbox(*_a, **_k):
        return payload

    vi.buscar_malha_osm_bbox = _offline_bbox  # type: ignore[assignment]
    try:
        iso = analisar_isolamento(
            lat=MANSO["lat"],
            lon=MANSO["lon"],
            raio_km=MANSO["raio_km"],
            hub=HUB,
            bbox=(south, west, north, east),
            geom_label="circular+offline",
            sedes=sedes,
            cnes=[],
        )
    finally:
        vi.buscar_malha_osm_bbox = original  # type: ignore[assignment]

    rows = iso.get("desvios_rota") or []
    campos = [
        "municipio",
        "codigo_ibge",
        "km_antes",
        "km_depois",
        "delta_km",
        "status",
        "populacao",
    ]
    with SAIDA.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in campos})

    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    md = [
        "# Rotas alternativas offline (eixo Manso–Cuiabá)",
        "",
        f"- Gerado: {agora}",
        f"- Fonte malha: `{offline.get('_meta', {}).get('fonte')}`",
        f"- Elementos offline na área: **{n_el}**",
        f"- Raio proxy na APM Manso: **{MANSO['raio_km']} km**",
        f"- Vias / pontes na mancha: **{iso.get('n_vias_interrompidas', 0)}** / "
        f"**{iso.get('n_pontes_comprometidas', 0)}**",
        f"- Sedes sem rota: **{iso.get('n_sedes_sem_rota', 0)}**",
        f"- Sedes com desvio: **{iso.get('n_sedes_com_desvio', 0)}**",
        f"- Desvio médio (km): **{iso.get('delta_km_medio_desvio', 0)}**",
        f"- C7 proxy: **{iso.get('nivel_c7_proxy')}** — {iso.get('rotulo_c7')}",
        f"- Arquivo: `{SAIDA.name}`",
        "",
        "Proxy operacional (Dijkstra sobre malha BR/MT tratada). "
        "A malha offline é esparsa (só refs BR-/MT-): desvios sede→hub podem ficar "
        "zerados sem a malha arterial completa do Overpass; vias/pontes na mancha "
        "ainda alimentam o C7. Não substitui tempo de chegada PAE nem SNV/DNIT oficial.",
        "",
    ]
    REL.write_text("\n".join(md), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": bool(iso.get("ok")),
                "n_desvios": len(rows),
                "sem_rota": iso.get("n_sedes_sem_rota"),
                "com_desvio": iso.get("n_sedes_com_desvio"),
                "saida": str(SAIDA),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
