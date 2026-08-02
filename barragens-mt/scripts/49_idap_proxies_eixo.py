"""Preenche proxies C4/C5/C7 do IDAP para o eixo Manso–Cuiabá (offline).

Usa captações Sisagua, escolas, ativos essenciais e malha OSM já tratados.
Não inventa mancha PAE: buffer geométrico a partir da barragem (proxy).

Saídas:
  dados/tratados/idap_proxies_eixo.csv
  relatorios/idap_proxies_eixo.md

Uso:
  python scripts/49_idap_proxies_eixo.py
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pandas as pd

import json

import comum

INV = comum.DADOS_TRATADOS / "inventario_barragens_mt.csv"
EIXO = comum.DADOS_TRATADOS / "barragens_montante_cuiaba.csv"
RECORTE = comum.DADOS_TRATADOS / "cuiaba_municipios_de_interesse.json"
CAP = comum.DADOS_TRATADOS / "sisagua_captacoes_eixo.csv"
ESC = comum.DADOS_TRATADOS / "escolas_eixo_cuiaba.csv"
ATV = comum.DADOS_TRATADOS / "ativos_essenciais_osm_eixo.csv"
MALHA = comum.DADOS_TRATADOS / "malha_dnit_osm_eixo.csv"
SAIDA = comum.DADOS_TRATADOS / "idap_proxies_eixo.csv"
REL = comum.RELATORIOS / "idap_proxies_eixo.md"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def _f(v: Any) -> float | None:
    try:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _raio_km(altura: float | None, cap_hm3: float | None) -> float:
    """Raio proxy (km) — alinhado à ordem de grandeza da simulação."""
    r = 8.0
    if altura and altura > 0:
        r = max(r, min(30.0, 2.0 * math.sqrt(altura)))
    if cap_hm3 and cap_hm3 > 0:
        # volume / 2 m lâmina → área → raio
        area_km2 = (cap_hm3 * 1e6 / 2.0) / 1e6
        r = max(r, min(35.0, math.sqrt(area_km2 / math.pi)))
    return round(r, 2)


def _cat_captacao(n: int, tem_sede: bool) -> str:
    if n <= 0:
        return "Nenhuma"
    if tem_sede:
        return "Captação principal de sede municipal ou única captação"
    if n >= 3:
        return "Sistema urbano de pequeno ou médio porte"
    return "Sistema isolado ou rural"


def _cat_isolamento(n_vias: int, n_pontes: int, n_refs: int) -> str:
    if n_vias <= 0 and n_pontes <= 0:
        return "Rotas alternativas pavimentadas"
    if n_refs <= 1 and n_pontes >= 1:
        return "Acesso único sem alternativa"
    if n_refs <= 1:
        return "Rota única com desvio precário"
    return "Rotas alternativas pavimentadas"


def main() -> int:
    if not INV.is_file():
        print("Inventário ausente.")
        return 1

    eixo_ids: set[str] = set()
    if EIXO.is_file():
        eixo_ids = set(
            pd.read_csv(EIXO, sep=";", dtype=str)["id_snisb"].astype(str).str.strip()
        )
    mun_eixo: set[str] = set()
    if RECORTE.is_file():
        rec = json.loads(RECORTE.read_text(encoding="utf-8"))
        for chave in (
            "municipios_com_barragens_a_montante",
            "eixo_manso_capital",
            "eixo_jusante_capital",
        ):
            for m in rec.get(chave) or []:
                mun_eixo.add(str(m).strip())

    inv = pd.read_csv(INV, sep=";", dtype=str).fillna("")
    mask = inv["id_snisb"].astype(str).isin(eixo_ids)
    if mun_eixo:
        mask = mask | inv["municipio"].astype(str).str.strip().isin(mun_eixo)
    mask = mask | inv["nome"].astype(str).str.contains("MANSO", case=False, na=False)
    inv = inv[mask].copy()
    print(f"Barragens candidatas ao proxy C4/C5/C7: {len(inv)}")

    caps = pd.read_csv(CAP, sep=";") if CAP.is_file() else pd.DataFrame()
    escs = pd.read_csv(ESC, sep=";") if ESC.is_file() else pd.DataFrame()
    atvs = pd.read_csv(ATV, sep=";") if ATV.is_file() else pd.DataFrame()
    malha = pd.read_csv(MALHA, sep=";") if MALHA.is_file() else pd.DataFrame()

    # Filtra abrigos ruidosos do OSM (lavagens etc.) — mantém ETA/ETE/energia
    if not atvs.empty and "categoria" in atvs.columns:
        atvs = atvs[atvs["categoria"].astype(str).str.lower().isin(
            {"eta", "ete", "energia", "subestacao", "subestação", "tratamento_agua", "tratamento_esgoto"}
        ) | atvs["categoria"].astype(str).str.contains("eta|ete|energia|water|plant", case=False, na=False)]

    rows = []
    for _, r in inv.iterrows():
        lat = _f(r.get("latitude"))
        lon = _f(r.get("longitude"))
        if lat is None or lon is None:
            continue
        alt = _f(r.get("altura_m"))
        cap = _f(r.get("capacidade_hm3"))
        raio = _raio_km(alt, cap)
        mun = str(r.get("municipio") or "")

        def _count(df: pd.DataFrame) -> int:
            if df.empty or "latitude" not in df.columns:
                return 0
            n = 0
            for _, p in df.iterrows():
                pla, plo = _f(p.get("latitude")), _f(p.get("longitude"))
                if pla is None or plo is None:
                    continue
                if haversine_km(lat, lon, pla, plo) <= raio:
                    n += 1
            return n

        n_cap = _count(caps)
        n_esc = _count(escs)
        n_atv = _count(atvs)
        n_serv = n_esc + n_atv

        n_vias = 0
        n_pontes = 0
        refs: set[str] = set()
        if not malha.empty:
            for _, m in malha.iterrows():
                pla, plo = _f(m.get("latitude")), _f(m.get("longitude"))
                if pla is None or plo is None:
                    continue
                if haversine_km(lat, lon, pla, plo) > raio:
                    continue
                n_vias += 1
                if str(m.get("bridge") or "").lower() in {"yes", "1", "true", "sim"}:
                    n_pontes += 1
                ref = str(m.get("ref") or "").strip()
                if ref:
                    refs.add(ref.split(";")[0].strip())

        tem_sede = False
        if n_cap > 0 and not caps.empty:
            for _, p in caps.iterrows():
                pla, plo = _f(p.get("latitude")), _f(p.get("longitude"))
                if pla is None or plo is None:
                    continue
                if haversine_km(lat, lon, pla, plo) > raio:
                    continue
                mcap = str(p.get("municipio") or "")
                if mcap.lower() in {"cuiabá", "cuiaba", "várzea grande", "varzea grande"}:
                    tem_sede = True
                    break

        captacao = _cat_captacao(n_cap, tem_sede)
        isolamento = _cat_isolamento(n_vias, n_pontes, len(refs))

        rows.append(
            {
                "id_snisb": str(r.get("id_snisb")),
                "nome": str(r.get("nome") or ""),
                "municipio": mun,
                "raio_proxy_km": raio,
                "n_captacoes": n_cap,
                "n_escolas": n_esc,
                "n_ativos": n_atv,
                "servicos_essenciais_ameacados": n_serv,
                "captacao_ameacada": captacao,
                "n_vias_malha": n_vias,
                "n_pontes": n_pontes,
                "n_refs": len(refs),
                "isolamento_rodoviario": isolamento,
                "fonte": "proxy buffer eixo Manso–Cuiabá (Sisagua/INEP/OSM) — não é mancha PAE",
            }
        )

    out = pd.DataFrame(rows)
    comum.DADOS_TRATADOS.mkdir(parents=True, exist_ok=True)
    comum.RELATORIOS.mkdir(parents=True, exist_ok=True)
    out.to_csv(SAIDA, sep=";", index=False, encoding="utf-8-sig")

    md = [
        "# Proxies IDAP C4/C5/C7 — eixo Manso–Cuiabá",
        "",
        f"- Barragens do eixo com proxy: **{len(out)}**",
        f"- Com ≥1 captação no buffer: **{int((out['n_captacoes'] > 0).sum()) if len(out) else 0}**",
        f"- Com ≥1 serviço essencial (escola+ativo): **{int((out['servicos_essenciais_ameacados'] > 0).sum()) if len(out) else 0}**",
        "",
        "## Distribuição C4 (captação)",
        "",
    ]
    if len(out):
        for k, v in out["captacao_ameacada"].value_counts().items():
            md.append(f"- {k}: **{v}**")
        md += ["", "## Distribuição C7 (isolamento)", ""]
        for k, v in out["isolamento_rodoviario"].value_counts().items():
            md.append(f"- {k}: **{v}**")
    md += [
        "",
        f"CSV: `{SAIDA.relative_to(comum.RAIZ)}`",
        "",
        "_Proxy geométrico — lacuna permanece fora do eixo._",
        "",
    ]
    REL.write_text("\n".join(md), encoding="utf-8")
    print(f"OK {SAIDA} ({len(out)} linhas)")
    print(f"OK {REL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
