"""Coleta a hidrografia ottocodificada da ANA para a bacia do rio Cuiaba.

Motivacao. O inventario traz o campo `codigo_trecho_curso_dagua`, que e o codigo
de bacia de Otto Pfafstetter (COBACIA) da Base Hidrografica Ottocodificada da ANA.
Esse codigo permite decidir montante e jusante por topologia de drenagem, e nao
por limite municipal — que era o vies a corrigir: uma barragem em Chapada dos
Guimaraes pode ameacar Cuiaba muito mais do que qualquer barragem dentro de
Cuiaba, porque esta a montante na mesma calha.

Esta etapa baixa:
  * trechos de drenagem (BHO 2017 50K) no recorte da bacia do alto/medio Cuiaba,
    com COBACIA, nome do rio e area de drenagem a montante;
  * massas d'agua, para desenhar o espelho do reservatorio de Manso nos mapas.

Fonte: SNIRH/ANA, ArcGIS REST. Escala 50K = cursos d'agua com area de drenagem
maior ou igual a 50 km2, mais todos os trechos de dominio federal. E a escala
adequada para carta em formato A4; a 5K geraria excesso de tracos ilegiveis.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import comum
import httpx

BHO_TRECHOS = "https://www.snirh.gov.br/arcgis/rest/services/SPR/BHO2017_50K_TRECHODRENAGEM/FeatureServer/0/query"
MASSA_DAGUA = "https://www.snirh.gov.br/arcgis/rest/services/SPR/Massa_dagua/FeatureServer/0/query"
SPR_SERVICOS = "https://www.snirh.gov.br/arcgis/rest/services/SPR?f=json"

# Recorte: das cabeceiras do rio Manso, na Chapada, ate a entrada no Pantanal,
# passando por Cuiaba. Cobre tambem o eixo Livramento-Pocone a oeste.
BBOX_BACIA_CUIABA = (-57.2, -17.8, -54.8, -14.2)

CAMPOS_TRECHO = "*"


def paginar(
    cli: httpx.Client,
    url: str,
    where: str,
    campos: str,
    bbox: tuple[float, float, float, float] | None = None,
    passo: int = 1000,
) -> list[dict[str, Any]]:
    """Percorre um FeatureServer respeitando o MaxRecordCount do servico."""
    feicoes: list[dict[str, Any]] = []
    deslocamento = 0
    while True:
        parametros: dict[str, Any] = {
            "where": where,
            "outFields": campos,
            "returnGeometry": "true",
            "outSR": 4326,
            "f": "geojson",
            "resultOffset": deslocamento,
            "resultRecordCount": passo,
        }
        if bbox is not None:
            parametros.update(
                {
                    "geometry": json.dumps(
                        {
                            "xmin": bbox[0],
                            "ymin": bbox[1],
                            "xmax": bbox[2],
                            "ymax": bbox[3],
                            "spatialReference": {"wkid": 4326},
                        }
                    ),
                    "geometryType": "esriGeometryEnvelope",
                    "inSR": 4326,
                    "spatialRel": "esriSpatialRelIntersects",
                }
            )
        dados = comum.requisitar_json(cli, url, parametros)
        lote = dados.get("features") or []
        feicoes.extend(lote)
        print(f"    +{len(lote):5d} feicoes (total {len(feicoes)})")
        if len(lote) < passo:
            return feicoes
        deslocamento += passo


def listar_camadas_massa_dagua(cli: httpx.Client) -> list[str]:
    """Procura no diretorio do SNIRH um servico de massa d'agua."""
    try:
        dados = comum.requisitar_json(cli, SPR_SERVICOS, tentativas=2)
    except RuntimeError as exc:
        print(f"  nao foi possivel listar servicos SPR: {exc}")
        return []
    nomes = [s.get("name", "") for s in dados.get("services", [])]
    candidatos = [n for n in nomes if any(t in n.upper() for t in ("MASSA", "ESPELHO", "RESERV", "LAGO"))]
    print(f"  {len(nomes)} servicos no SPR; candidatos a massa d'agua:")
    for nome in candidatos:
        print(f"    {nome}")
    return candidatos


def main() -> None:
    comum.preparar_diretorios()

    with comum.cliente(verificar_tls=False) as cli:
        print("Trechos de drenagem BHO 2017 50K — recorte da bacia do rio Cuiaba")
        trechos = paginar(
            cli,
            BHO_TRECHOS,
            where="1=1",
            campos=CAMPOS_TRECHO,
            bbox=BBOX_BACIA_CUIABA,
        )
        comum.salvar_json(
            comum.DADOS_TRATADOS / "ana_bho_trechos_bacia_cuiaba.geojson",
            {"type": "FeatureCollection", "features": trechos},
        )

        rios: dict[str, float] = {}
        for feicao in trechos:
            propriedades = feicao.get("properties") or {}
            nome = (propriedades.get("NORIOCOMP") or propriedades.get("NOCURSODAG") or "").strip()
            if not nome:
                continue
            area = propriedades.get("NUAREAMONT") or 0
            rios[nome] = max(rios.get(nome, 0.0), float(area or 0))
        print(f"\n  {len(rios)} cursos d'agua nomeados no recorte; os 20 maiores por area a montante:")
        for nome, area in sorted(rios.items(), key=lambda x: -x[1])[:20]:
            print(f"    {area:12,.1f} km2  {nome}")

        # O filtro espacial dessa camada se mostrou inconsistente (a consulta paginada
        # ignorava o envelope e varria o pais). Filtramos por atributo, que e confiavel:
        # grandes espelhos artificiais de MT. O recorte fino fica para o desenho do mapa.
        print("\nMassas d'agua — grandes espelhos de MT (filtro por atributo)")
        massas = paginar(
            cli,
            MASSA_DAGUA,
            where="nuareakm2 > 5 AND nmufe = 'MATO GROSSO'",
            campos="*",
        )
        comum.salvar_json(
            comum.DADOS_TRATADOS / "ana_massas_dagua_mt.geojson",
            {"type": "FeatureCollection", "features": massas},
        )
        maiores = sorted(
            massas,
            key=lambda f: float((f.get("properties") or {}).get("nuareakm2") or 0),
            reverse=True,
        )
        print("  15 maiores espelhos artificiais de MT:")
        for feicao in maiores[:15]:
            propriedades = feicao.get("properties") or {}
            rotulo = (
                propriedades.get("nmoriginal", " ").strip()
                or propriedades.get("nmalternat", " ").strip()
                or propriedades.get("nmriocomp", " ").strip()
                or "(sem nome)"
            )
            print(
                f"    {float(propriedades.get('nuareakm2') or 0):9,.1f} km2  "
                f"vol={float(propriedades.get('nuvolumhm3') or 0):10,.1f} hm3  "
                f"{propriedades.get('nmmun', '').strip()[:24]:26s} {rotulo}"
            )


if __name__ == "__main__":
    main()
