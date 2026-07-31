"""Gera a Tela 1 — Comando estadual (docs/07-telas.md §7.1).

Painel operacional autocontido com IDAP, hidro SisClima/TITAN e alertabilidade.
Substitui `painel/index.html` como entrada principal do sistema.
O painel de inventário/fiscalização fica em `painel/inventario.html` (etapa 07).
"""

from __future__ import annotations

import csv
import datetime as dt
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import comum

SAIDA = comum.RAIZ / "painel"

# Tipologia = agrupamento operacional do uso principal (espelha st_app/data.py).
TIPOLOGIA_CORES = {
    "Irrigação": "#2a4aad",
    "Rejeito / mineração": "#b91c1c",
    "Hidroelétrica": "#0e7490",
    "Aquicultura": "#0369a1",
    "Abastecimento humano": "#1b3281",
    "Dessedentação animal": "#854d0e",
    "Recreação / paisagismo": "#64748b",
    "Industrial / outros": "#475569",
}
_TIPOLOGIA_REGRAS = (
    ("Irrigação", ("irrig",)),
    ("Rejeito / mineração", ("rejeito", "sedimento", "miner")),
    ("Hidroelétrica", ("hidroel", "hidrel")),
    ("Aquicultura", ("aquicult",)),
    ("Abastecimento humano", ("abastec", "humano")),
    ("Dessedentação animal", ("dessedent",)),
    ("Recreação / paisagismo", ("recrea", "paisag")),
)


def tipologia_de_uso(uso: object) -> str:
    u = str(uso or "").lower()
    for rotulo, chaves in _TIPOLOGIA_REGRAS:
        if any(c in u for c in chaves):
            return rotulo
    return "Industrial / outros"


def _carregar_07():
    caminho = Path(__file__).resolve().parent / "07_painel.py"
    spec = importlib.util.spec_from_file_location("painel_inventario", caminho)
    if spec is None or spec.loader is None:
        raise SystemExit("não foi possível carregar 07_painel.py")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["painel_inventario"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def ler_csv(nome: str) -> list[dict[str, Any]]:
    caminho = comum.DADOS_TRATADOS / nome
    if not caminho.exists():
        raise SystemExit(f"base ausente: {nome}. Rode as etapas 05, 16 e 17.")
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def num(valor: Any) -> float | None:
    if valor in (None, "", "None"):
        return None
    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return None


def idade_arquivo(nome: str) -> dict[str, Any]:
    caminho = comum.DADOS_TRATADOS / nome
    if not caminho.exists():
        return {"arquivo": nome, "existe": False, "idade_h": None, "mtime": ""}
    mtime = dt.datetime.fromtimestamp(caminho.stat().st_mtime)
    idade_h = round((dt.datetime.now() - mtime).total_seconds() / 3600, 1)
    return {
        "arquivo": nome,
        "existe": True,
        "idade_h": idade_h,
        "mtime": mtime.strftime("%d/%m/%Y %H:%M"),
    }


def ler_historico_comando(limite: int = 30) -> dict[str, Any]:
    """Índice estadual + série IDAP das barragens não-Verde (sparklines)."""
    pasta = comum.DADOS_TRATADOS / "historico_idap"
    indice_path = pasta / "indice.csv"
    if not indice_path.exists():
        return {"indice": [], "series": {}}
    with indice_path.open(encoding="utf-8-sig", newline="") as arquivo:
        indice = list(csv.DictReader(arquivo, delimiter=";"))[-limite:]
    series: dict[str, list[dict[str, Any]]] = {}
    for linha in indice:
        arq = pasta / (linha.get("arquivo") or "")
        if not arq.exists():
            continue
        instante = (linha.get("instante") or "")[:19]
        with arq.open(encoding="utf-8-sig", newline="") as arquivo:
            for r in csv.DictReader(arquivo, delimiter=";"):
                nv = r.get("nivel") or "Verde"
                if nv == "Verde":
                    continue
                bid = (r.get("id_snisb") or "").strip()
                if not bid:
                    continue
                series.setdefault(bid, []).append(
                    {
                        "t": instante,
                        "idap": int(r["idap"]) if str(r.get("idap", "")).isdigit() else 0,
                        "nv": nv,
                    }
                )
    return {
        "indice": [
            {
                "t": (x.get("instante") or "")[:19],
                "ama": int(x.get("amarelo") or 0),
                "lar": int(x.get("laranja") or 0),
                "ver": int(x.get("vermelho") or 0),
                "rox": int(x.get("roxo") or 0),
                "n": int(x.get("n_barragens") or 0),
            }
            for x in indice
        ],
        "series": series,
    }


def montar_registros() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    inventario = {r["id_snisb"]: r for r in ler_csv("inventario_barragens_mt.csv")}
    idap = ler_csv("idap_estadual_mt.csv")
    hidro = {r["id_snisb"]: r for r in ler_csv("hidro_barragens_mt.csv")}
    piloto_path = comum.DADOS_TRATADOS / "piloto_manso_cuiaba.csv"
    piloto_ids: set[str] = set()
    if piloto_path.exists():
        with piloto_path.open(encoding="utf-8-sig", newline="") as arquivo:
            piloto_ids = {
                (r.get("id_snisb") or "").strip()
                for r in csv.DictReader(arquivo, delimiter=";")
            }

    registros: list[dict[str, Any]] = []
    for linha in idap:
        bid = linha["id_snisb"]
        inv = inventario.get(bid, {})
        h = hidro.get(bid, {})
        la = num(inv.get("latitude"))
        lo = num(inv.get("longitude"))
        registros.append(
            {
                "id": bid,
                "no": linha.get("nome") or inv.get("nome") or "",
                "mu": linha.get("municipio_sede") or inv.get("municipio") or "",
                "og": linha.get("orgao_fiscalizador") or "",
                "us": linha.get("uso_principal") or "",
                "tp": tipologia_de_uso(linha.get("uso_principal")),
                "cri": linha.get("categoria_risco") or "",
                "dpa": linha.get("dano_potencial_associado") or "",
                "la": round(la, 5) if la is not None else None,
                "lo": round(lo, 5) if lo is not None else None,
                "idap": int(linha["idap"]) if str(linha.get("idap", "")).isdigit() else 0,
                "nv": linha.get("nivel") or "Verde",
                "comp": linha.get("completude") or "",
                "conf": linha.get("confiabilidade") or "",
                "pa": int(linha.get("pontos_a") or 0),
                "pb": int(linha.get("pontos_b") or 0),
                "pc": int(linha.get("pontos_c") or 0),
                "pd": int(linha.get("pontos_d") or 0),
                "al": linha.get("alertavel") or "não avaliado",
                "reg": linha.get("regras_disparadas") or "",
                "lac": linha.get("lacunas") or "",
                "af": linha.get("municipios_potencialmente_afetados") or "",
                "nex": int(linha.get("n_municipios_extraterritoriais") or 0),
                "pi": 1 if bid in piloto_ids else 0,
                "c24": num(h.get("chuva_24h_mm")),
                "c72": num(h.get("chuva_72h_mm")),
                "cprev": num(h.get("chuva_prevista_24_72h_mm")),
                "pct": num(h.get("percentil_climatologico")),
                "sat": h.get("saturacao_antecedente") or "",
                "satn": num(h.get("saturacao_antecedente")),
                "nh": h.get("nivel_alerta_hidro") or "",
                "cem": h.get("alerta_cemaden_nivel") or "",
                "cemt": h.get("alerta_cemaden") or "",
                "aint": h.get("nivel_alerta_integrado") or "",
                "glofas": num(h.get("vazao_prevista_glofas_m3s")),
                "aprox": h.get("aproximacao_espacial") or "",
                "dh": h.get("data_referencia") or "",
                "inst": linha.get("instante") or "",
            }
        )

    niveis = Counter(r["nv"] for r in registros)
    tipologias = Counter(r["tp"] for r in registros)
    frescor = [
        idade_arquivo("idap_estadual_mt.csv"),
        idade_arquivo("hidro_barragens_mt.csv"),
        idade_arquivo("hidro_municipios_mt.csv"),
        idade_arquivo("inventario_barragens_mt.csv"),
        idade_arquivo("piloto_manso_cuiaba.csv"),
        idade_arquivo("alertabilidade_piloto.csv"),
    ]

    def _max(campo: str) -> float | None:
        vals = [r[campo] for r in registros if r.get(campo) is not None]
        return round(max(vals), 1) if vals else None

    def _media(campo: str) -> float | None:
        vals = [float(r[campo]) for r in registros if r.get(campo) is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    idaps = [r["idap"] for r in registros]
    amarelo_mais = sum(
        niveis.get(n, 0) for n in ("Amarelo", "Laranja", "Vermelho", "Roxo")
    )
    hist = ler_historico_comando()
    ind = hist.get("indice") or []
    tend = {"amarelo_mais": None, "amarelo": None, "verde": None, "piloto": None}
    if len(ind) >= 2:
        ant, atu = ind[-2], ind[-1]
        ama_ant = (ant.get("ama") or 0) + (ant.get("lar") or 0) + (ant.get("ver") or 0) + (ant.get("rox") or 0)
        ama_atu = (atu.get("ama") or 0) + (atu.get("lar") or 0) + (atu.get("ver") or 0) + (atu.get("rox") or 0)
        tend["amarelo_mais"] = ama_atu - ama_ant
        tend["amarelo"] = (atu.get("ama") or 0) - (ant.get("ama") or 0)
        verd_ant = (ant.get("n") or 0) - ama_ant
        verd_atu = (atu.get("n") or 0) - ama_atu
        tend["verde"] = verd_atu - verd_ant

    # Projeção hidro próximos dias (proxy — não é IDAP recalculado).
    limiar_atencao = 40.0
    limiar_r12 = 140.0
    prev_vals = [r["cprev"] for r in registros if r.get("cprev") is not None]
    n_prev_atencao = sum(1 for v in prev_vals if v >= limiar_atencao)
    n_prev_r12 = sum(1 for v in prev_vals if v >= limiar_r12)
    # Verde com previsão alta entraria em pressão; Amarelo+ atual permanece baseline.
    verdes = [r for r in registros if r["nv"] == "Verde"]
    n_verde_risco_prev = sum(
        1 for r in verdes if r.get("cprev") is not None and r["cprev"] >= limiar_atencao
    )
    proj_amarelo_mais = amarelo_mais + n_verde_risco_prev
    if n_prev_r12:
        # R12 eleva ao menos para Amarelo independentemente da pontuação.
        ids_r12 = {
            r["id"]
            for r in registros
            if r.get("cprev") is not None and r["cprev"] >= limiar_r12
        }
        ids_ja = {r["id"] for r in registros if r["nv"] in {"Amarelo", "Laranja", "Vermelho", "Roxo"}}
        proj_amarelo_mais = max(proj_amarelo_mais, len(ids_ja | ids_r12))

    meta = {
        "gerado": dt.datetime.now().strftime("%d/%m/%Y %H:%M"),
        "total": len(registros),
        "niveis": {k: niveis.get(k, 0) for k in ("Roxo", "Vermelho", "Laranja", "Amarelo", "Verde")},
        "com_coord": sum(1 for r in registros if r["la"] is not None and r["lo"] is not None),
        "alertaveis": sum(1 for r in registros if r["al"] == "sim"),
        "nao_alertaveis": sum(1 for r in registros if r["al"] == "não"),
        "extraterritoriais": sum(1 for r in registros if r["nex"] > 0),
        "piloto": sum(1 for r in registros if r["pi"] == 1),
        "piloto_amarelo": sum(
            1 for r in registros if r["pi"] == 1 and r["nv"] in {"Amarelo", "Laranja", "Vermelho", "Roxo"}
        ),
        "instante_idap": next((r["inst"] for r in registros if r["inst"]), ""),
        "data_hidro": next((r["dh"] for r in registros if r["dh"]), ""),
        "tipologias": [
            {"tp": tp, "n": n, "cor": TIPOLOGIA_CORES.get(tp, "#888")}
            for tp, n in tipologias.most_common()
        ],
        "cores_tipologia": TIPOLOGIA_CORES,
        "frescor": frescor,
        "tendencias": tend,
        "projecao": {
            "horizonte": "próximos 2–7 dias (chuva prevista ECMWF 24–72h como proxy)",
            "prevista_max_mm": round(max(prev_vals), 1) if prev_vals else None,
            "com_prevista_atencao": n_prev_atencao,
            "com_prevista_extrema_r12": n_prev_r12,
            "amarelo_mais_projetado": proj_amarelo_mais,
            "delta_vs_atual": proj_amarelo_mais - amarelo_mais,
            "nota": (
                "Projeção hidroclimática simplificada: não recalcula o IDAP completo. "
                "Conta Verdes com previsão ≥40 mm e aplica R12 (≥140 mm) quando houver."
            ),
        },
        "risco": {
            "amarelo_mais": amarelo_mais,
            "idap_max": max(idaps) if idaps else 0,
            "idap_medio": round(sum(idaps) / len(idaps), 1) if idaps else 0,
            "com_pressao_a": sum(1 for r in registros if r["pa"] > 0),
            "a_medio": _media("pa") or 0,
            "b_medio": _media("pb") or 0,
            "c_medio": _media("pc") or 0,
            "d_medio": _media("pd") or 0,
            "chuva24_max": _max("c24"),
            "chuva72_max": _max("c72"),
            "prevista_max": _max("cprev"),
            "percentil_max": _max("pct"),
            "cemaden_ativos": sum(
                1
                for r in registros
                if r.get("cem") and str(r["cem"]).lower() not in {"", "verde"}
            ),
            "integrado_alto": sum(
                1
                for r in registros
                if str(r.get("aint") or "").lower()
                in {"laranja", "vermelha", "vermelho", "roxa", "roxo"}
            ),
            "regras_r10": sum(1 for r in registros if "R10" in (r.get("reg") or "")),
            "regras_r11": sum(1 for r in registros if "R11" in (r.get("reg") or "")),
            "regras_r12": sum(1 for r in registros if "R12" in (r.get("reg") or "")),
            "cri_alto": sum(
                1 for r in registros if (r.get("cri") or "").strip().lower() == "alto"
            ),
            "dpa_alto": sum(
                1 for r in registros if (r.get("dpa") or "").strip().lower() == "alto"
            ),
            "rejeito": sum(
                1
                for r in registros
                if "rejeito" in (r.get("us") or "").lower()
                or "miner" in (r.get("og") or "").lower()
            ),
        },
    }

    # Indicadores sanitários / cadastro (sem CNES na geração HTML — proxy leve).
    aten = [r for r in registros if r["nv"] in {"Amarelo", "Laranja", "Vermelho", "Roxo"}]
    munis_jus: set[str] = set()
    for r in aten:
        for p in (r.get("af") or "").split("|"):
            if p.strip():
                munis_jus.add(p.strip())
    comps = []
    for r in registros:
        raw = str(r.get("comp") or "").replace("%", "").replace(",", ".")
        try:
            comps.append(float(raw))
        except ValueError:
            pass
    if comps:
        med_c = sum(comps) / len(comps)
        if med_c <= 1.5:
            med_c *= 100.0
    else:
        med_c = None
    quase = [
        r
        for r in registros
        if r["nv"] == "Verde"
        and (
            (r.get("pa") or 0) >= 8
            or (r.get("cprev") is not None and r["cprev"] >= 40)
        )
    ]
    quase.sort(key=lambda x: (-(x.get("pa") or 0), -(x.get("cprev") or 0)))
    meta["sanitario"] = {
        "n_atencao": len(aten),
        "pop_sob_pressao": None,
        "us_sob_risco": None,
        "us_prioritarias": None,
        "razao_pop_us": None,
        "municipios_jusante": len(munis_jus),
        "completude_media": round(med_c, 1) if med_c is not None else None,
        "rejeito_atencao": sum(
            1
            for r in aten
            if "rejeito" in (r.get("us") or "").lower() or "miner" in (r.get("us") or "").lower()
        ),
        "dpa_alto_sem_alerta": sum(
            1
            for r in aten
            if (r.get("dpa") or "").strip().lower() == "alto" and r.get("al") != "sim"
        ),
        "extraterritorial_ativo": sum(1 for r in aten if (r.get("nex") or 0) > 0),
        "quase_atencao": len(quase),
        "quase_lista": [
            {
                "id": r["id"],
                "no": r["no"],
                "mu": r["mu"],
                "idap": r["idap"],
                "pa": r["pa"],
                "cprev": r.get("cprev"),
                "comp": r.get("comp"),
            }
            for r in quase[:20]
        ],
        "nota": "Território, cadastro e vigília; pop/US quando CNES estadual disponível.",
    }
    try:
        raiz = Path(__file__).resolve().parent.parent
        if str(raiz) not in sys.path:
            sys.path.insert(0, str(raiz))
        from st_app.data import carregar_idap
        from st_app.indicadores import indicadores_sanitarios

        san = indicadores_sanitarios(carregar_idap())
        meta["sanitario"]["pop_sob_pressao"] = san.get("pop_sob_pressao")
        meta["sanitario"]["us_sob_risco"] = san.get("us_sob_risco")
        meta["sanitario"]["us_prioritarias"] = san.get("us_prioritarias")
        meta["sanitario"]["razao_pop_us"] = san.get("razao_pop_us")
        meta["sanitario"]["municipios_sob_pressao"] = san.get("municipios_sob_pressao")
        meta["sanitario"]["nota"] = (
            "US nos municípios sede/jusante das Em atenção+ (CNES estadual). "
            f"Método: {san.get('metodo_us')}; buffer geom. dedup: {san.get('us_buffer_dedup')}."
        )
    except Exception as exc:  # noqa: BLE001
        print(f"  sanitário pop/US não calculado: {exc}")

    for faixa in ("Roxo", "Vermelho", "Laranja", "Amarelo", "Verde"):
        if meta["niveis"].get(faixa, 0) > 0:
            meta["semaforo"] = faixa
            break
    else:
        meta["semaforo"] = "Verde"
    return registros, meta


MODELO = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Comando estadual — VIGIBARRAGENS–MT</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet">
<style>
/* Cromo institucional GOV/SES-MT: azul #1b3281 e preto #231f20.
   Cores de gravidade (roxo/vermelho/laranja/amarelo/verde) são semânticas. */
:root{
  --ink:#231f20; --muted:#5b6b80; --paper:#f4f6fb; --card:#fff; --line:#dde3f0;
  --accent:#1b3281; --accent-soft:#3b52a0; --accent-claro:#e9edf8;
  --roxo:#5b2c6f; --verm:#c0392b; --lar:#d35400; --ama:#b7950b; --verd:#1e8449;
  --ses:#1b3281;
}
*{box-sizing:border-box}
body{margin:0;font-family:"Source Sans 3",system-ui,sans-serif;color:var(--ink);
background:var(--paper);font-size:14px}
header{padding:16px 24px 14px;border-bottom:3px solid var(--ses);background:var(--card);
display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;align-items:flex-end}
.marca{font-size:clamp(1.3rem,2.2vw,1.6rem);font-weight:700;margin:0 0 2px;
letter-spacing:-.02em;color:var(--ses)}
header p{margin:0;color:var(--muted);max-width:38rem;line-height:1.4;font-size:13px}
nav{display:flex;flex-wrap:wrap;gap:6px}
nav a{color:var(--accent);text-decoration:none;font-size:12.5px;font-weight:600;
padding:5px 9px;background:var(--accent-claro)}
nav a:hover{background:#dbe2f6}
main{padding:14px 24px 40px;max-width:1600px;margin:0 auto}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));gap:8px;margin-bottom:10px}
.kpi{background:var(--card);border:1px solid var(--line);padding:10px 12px;
border-top:3px solid var(--ses);position:relative}
.kpi .n{font-size:22px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1.1}
.kpi .r{font-size:10.5px;color:var(--muted);margin-top:3px;text-transform:uppercase;letter-spacing:.04em}
.kpi .delta{font-size:11px;font-weight:600;margin-top:4px}
.kpi .delta.up{color:var(--verm)}.kpi .delta.down{color:var(--verd)}.kpi .delta.flat{color:var(--muted)}
.kpi.sev-ok .n{color:var(--verd)}.kpi.sev-ok{border-top-color:var(--verd)}
.kpi.sev-atencao .n{color:#92740a}.kpi.sev-atencao{border-top-color:var(--ama)}
.kpi.sev-elevado .n{color:#c2410c}.kpi.sev-elevado{border-top-color:var(--lar)}
.kpi.sev-alto .n{color:#b91c1c}.kpi.sev-alto{border-top-color:var(--verm)}
.kpi.sev-critico .n{color:var(--roxo)}.kpi.sev-critico{border-top-color:var(--roxo)}
.kpi.sev-neutro .n{color:var(--ses)}.kpi.sev-neutro{border-top-color:var(--ses)}
.kpi .sub{font-size:10px;color:var(--muted);margin-top:2px}
.kpi-help{font-size:12px;color:var(--muted);line-height:1.45;margin:0 0 10px;max-width:52rem;
border-left:3px solid var(--accent-claro);padding:2px 0 2px 10px}
.proj-box{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--accent);
padding:10px 12px;margin-bottom:10px}
.proj-box h2{font-size:1rem;font-weight:600;margin:0 0 4px}
.proj-box p{margin:0;color:#334155;line-height:1.45;font-size:13px}
section h2{font-size:1.1rem;font-weight:600;margin:16px 0 8px;letter-spacing:-.01em}
.semaforo{display:flex;align-items:center;gap:10px;padding:9px 12px;margin-bottom:8px;
background:var(--card);border:1px solid var(--line)}
.semaforo .luz{width:16px;height:16px;border-radius:50%}
.frescor{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0 0}
.frescor .chip{background:var(--accent-claro);border:0;padding:3px 9px 3px 8px;font-size:11.5px;
color:#35405a;display:inline-flex;align-items:center;gap:6px}
.frescor .chip::before{content:"";width:7px;height:7px;border-radius:50%;background:var(--muted);flex:none}
.frescor .ok::before{background:var(--verd)}
.frescor .velho::before{background:var(--lar)}
.frescor .morto::before{background:var(--verm)}
.filtros{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;
background:var(--card);border:1px solid var(--line);padding:12px 14px;margin-bottom:10px;align-items:end}
.filtros label{display:block;font-size:11px;font-weight:600;color:var(--muted);
text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px}
select,input[type=text],input[type=number]{width:100%;padding:7px 8px;border:1px solid var(--line);
font:inherit;background:#fff}
button{padding:8px 12px;border:0;background:var(--accent);color:#fff;font:inherit;font-weight:600;cursor:pointer}
button.sec{background:var(--accent-claro);color:var(--accent)}
.grade{display:grid;grid-template-columns:1.4fr 1fr;gap:12px;margin-bottom:10px}
@media(max-width:1100px){.grade{grid-template-columns:1fr}}
.cartao{background:var(--card);border:1px solid var(--line);overflow:hidden}
.cartao h2{margin:0;padding:9px 14px;font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;
color:var(--muted);border-bottom:1px solid var(--line);background:#fbfcfe}
#mapa{height:520px}
.rolagem{max-height:520px;overflow:auto}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th,td{padding:7px 9px;border-bottom:1px solid #f0f3f9;text-align:left;white-space:nowrap}
th{position:sticky;top:0;background:#fbfcfe;font-size:11px;color:var(--muted);
text-transform:uppercase;letter-spacing:.03em;cursor:pointer}
tbody tr{cursor:pointer} tbody tr:hover{background:var(--accent-claro)}
.etq{display:inline-block;padding:2px 7px;color:#fff;font-size:11px;font-weight:600}
.Roxo{background:var(--roxo)}.Vermelho{background:var(--verm)}.Laranja{background:var(--lar)}
/* Amarelo é faixa clara: texto escuro (branco ficaria em 2,9:1). */
.Amarelo{background:var(--ama);color:var(--ink)}.Verde{background:var(--verd)}
.legenda{display:flex;flex-wrap:wrap;gap:12px;padding:8px 14px;font-size:12px;color:var(--muted)}
.legenda i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:4px}
.nota{margin-top:12px;font-size:12.5px;color:var(--muted);line-height:1.55;max-width:52rem}
.leaflet-popup-content{font-size:12.5px;line-height:1.55}
.faixa-titulo{margin:18px 0 6px;padding-bottom:5px;border-bottom:1px solid var(--line)}
.faixa-titulo .kicker{display:block;font-size:10.5px;font-weight:700;text-transform:uppercase;
letter-spacing:.1em;color:var(--ses);margin-bottom:1px}
.faixa-titulo .titulo{display:block;font-size:1.18rem;font-weight:700;letter-spacing:-.02em;
color:var(--ink);line-height:1.2}
.faixa-titulo .sub{display:block;font-size:0.82rem;font-weight:400;color:var(--muted);margin-top:1px}
details.bloco{background:var(--card);border:1px solid var(--line);margin-bottom:10px;padding:0}
details.bloco>summary{cursor:pointer;padding:9px 14px;font-size:11.5px;text-transform:uppercase;
letter-spacing:.05em;color:var(--muted);font-weight:600;background:#fbfcfe;list-style:none}
details.bloco>summary::-webkit-details-marker{display:none}
details.bloco>summary:hover{background:var(--accent-claro)}
details.bloco[open]>summary{border-bottom:1px solid var(--line)}
.atalhos{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 10px}
.atalhos a{color:var(--accent);font-weight:600;font-size:12.5px;text-decoration:none;
padding:7px 11px;background:var(--accent-claro)}
.atalhos a:hover{background:#dbe2f6}
.tip-linha{display:grid;grid-template-columns:170px 1fr 92px;gap:10px;align-items:center;
margin-bottom:5px;font-size:12.5px}
.tip-linha .rot{color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tip-barra{position:relative;height:14px;background:#eff2f8}
.tip-barra i{display:block;height:100%}
.tip-barra b{position:absolute;top:-3px;bottom:-3px;width:3px;background:var(--ink)}
.tip-linha .num{color:var(--muted);font-variant-numeric:tabular-nums;text-align:right}
.dist{display:flex;flex-wrap:wrap;gap:14px;margin:0 0 10px;font-size:12.5px;color:var(--muted)}
.dist-item{display:inline-flex;align-items:center;gap:5px}
.dist-item i{width:9px;height:9px;border-radius:50%;display:inline-block}
.dist-item b{color:var(--ink);font-variant-numeric:tabular-nums}
</style>
</head>
<body>
<header>
  <div>
    <h1 class="marca">VIGIBARRAGENS–MT</h1>
    <p>Comando estadual — como está Mato Grosso agora e onde olhar primeiro.
    Jornada Situação → Território → Ação → Dados · __GERADO__</p>
  </div>
  <nav>
    <a href="hidro.html">Hidro municipal</a>
    <a href="piloto_manso_cuiaba.html">Eixo Manso–Cuiabá</a>
    <a href="tipologia.html">Mapa por tipologia</a>
    <a href="barragem.html">Barragem 360°</a>
    <a href="alertas.html">Fila de alertas</a>
    <a href="simulacao.html">Simulação</a>
    <a href="glossario.html">Interpretação</a>
    <a href="ficha_rapida.html">Ficha rápida</a>
    <a href="confirmacao_alerta.html">Confirmação</a>
    <a href="inventario.html">Inventário</a>
  </nav>
</header>
<main>
  <!-- Faixa 1 — Agora -->
  <div class="faixa-titulo"><span class="kicker">Faixa 1</span>
    <span class="titulo">Agora</span>
    <span class="sub">Prontidão do recorte e tendência que manda na decisão</span></div>
  <div class="semaforo" id="semaforo"></div>
  <div class="kpis" id="kpis"></div>
  <div class="dist" id="kpiFaixas"></div>
  <p class="kpi-help" id="kpiHelp"></p>
  <div class="proj-box" id="projSemana"></div>
  <details class="bloco">
    <summary id="frescorResumo">Frescor das fontes</summary>
    <div style="padding:10px 14px"><div class="frescor" id="frescor"></div>
      <p style="margin:8px 0 0;font-size:11.5px;color:var(--muted)">
        Verde ≤24 h · laranja ≤72 h · vermelho acima disso ou ausente.</p></div>
  </details>

  <!-- Faixa 2 — Pessoas e resposta -->
  <div class="faixa-titulo"><span class="kicker">Faixa 2</span>
    <span class="titulo">Pessoas e resposta</span>
    <span class="sub">Exposição sanitária e capacidade assistencial sob pressão</span></div>
  <div class="kpis" id="sanKpis"></div>
  <p id="sanNota" style="margin:0 0 8px;font-size:12px;color:var(--muted)"></p>
  <details class="bloco">
    <summary>Cadastro e tipológico (detalhe)</summary>
    <div class="kpis" id="sanKpisExtra" style="padding:12px 14px;margin:0"></div>
  </details>

  <!-- Faixa 3 — Onde olhar -->
  <div class="faixa-titulo"><span class="kicker">Faixa 3</span>
    <span class="titulo">Onde olhar</span>
    <span class="sub">Mapa, Top 15, vigília (quase atenção) e tipologia</span></div>
  <div class="filtros">
    <div><label>Nível IDAP</label>
      <select id="fNivel"><option value="">Todos</option>
        <option>Roxo</option><option>Vermelho</option><option>Laranja</option>
        <option>Amarelo</option><option>Verde</option></select></div>
    <div><label>Município (sede ou afetado a jusante)</label>
      <input type="text" id="fMun" placeholder="ex.: Cuiabá — inclui jusante"></div>
    <div><label>Órgão</label><input type="text" id="fOrg" placeholder="SEMA, ANM…"></div>
    <div><label>Alertável</label>
      <select id="fAl"><option value="">Todos</option><option value="sim">sim</option>
        <option value="não">não</option><option value="não avaliado">não avaliado</option></select></div>
    <div><label>Recorte</label>
      <select id="fPi"><option value="">Estado todo</option><option value="1">Só eixo Manso–Cuiabá</option></select></div>
    <div><label>Só extraterritorial</label>
      <select id="fExt"><option value="">Não</option><option value="1">Sim</option></select></div>
    <div><label>Busca</label><input type="text" id="fBusca" placeholder="nome ou id SNISB"></div>
    <div><button type="button" id="btnFiltrar">Filtrar</button>
      <button type="button" class="sec" id="btnLimpar">Limpar</button>
      <button type="button" class="sec" id="btnAmarelo" title="Filtra e enquadra no mapa">Focar em atenção+</button></div>
  </div>
  <div class="grade">
    <div class="cartao">
      <h2>Mapa — <span id="tituloMapa">faixa de prontidão</span></h2>
      <div style="padding:8px 14px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <label for="fCor" style="font-size:11px;font-weight:600;color:var(--muted);
          text-transform:uppercase;letter-spacing:.04em;margin:0">Colorir por</label>
        <select id="fCor" style="width:auto">
          <option value="nv">Prontidão</option>
          <option value="tp">Tipologia (uso principal)</option>
        </select>
      </div>
      <div id="mapa"></div>
      <div class="legenda" id="legenda"></div>
    </div>
    <div class="cartao">
      <h2>Top 15 — olhar primeiro</h2>
      <div class="rolagem" style="max-height:280px"><table>
        <thead><tr>
          <th data-k="idap">IDAP</th><th>Nível</th><th>A</th><th>Barragem</th><th>Sede</th>
          <th>Comp.</th><th>Chuva 24h</th><th>Alertável</th>
        </tr></thead>
        <tbody id="top"></tbody>
      </table></div>
      <h2>Quase atenção — vigília</h2>
      <div class="rolagem" style="max-height:180px"><table>
        <thead><tr><th>Barragem</th><th>Sede</th><th>Índice</th><th>Pressão A</th><th>Prevista</th><th>Completude</th></tr></thead>
        <tbody id="quaseLista"></tbody>
      </table></div>
    </div>
  </div>
  <div class="cartao" style="margin-bottom:14px">
    <h2>Tipologia — para que serve cada barragem</h2>
    <p style="margin:10px 14px 4px;font-size:12px;color:var(--muted);line-height:1.45">
      Agrupamento operacional do uso principal (SNISB). Barra cheia = estado inteiro;
      marca escura = quantas estão no recorte filtrado. Rejeito/mineração e abastecimento
      humano puxam decisão sanitária diferente de irrigação.
    </p>
    <div id="tipologiaBarras" style="padding:4px 14px 14px"></div>
  </div>
  <div class="atalhos">
    <a href="piloto_manso_cuiaba.html">Eixo Manso–Cuiabá</a>
    <a href="alertas.html">Cobertura / fila de alertas</a>
    <a href="tipologia.html">Mapa por tipologia</a>
  </div>

  <!-- Faixa 4 — Fila e clima -->
  <div class="faixa-titulo"><span class="kicker">Faixa 4</span>
    <span class="titulo">Fila e clima</span>
    <span class="sub">Detalhe operacional — abrir só quando precisar aprofundar</span></div>
  <details class="bloco">
    <summary>Pressão climática e regras (dimensões A–D + hidro)</summary>
    <div class="kpis" id="riscoKpis" style="padding:12px 14px;margin:0"></div>
    <p style="margin:0 14px 12px;font-size:12px;color:var(--muted);line-height:1.45">
      Linguagem operacional (sem siglas na primeira leitura). Borda/número mudam de cor com a
      gravidade. Filtro de município inclui sede <b>e</b> potencialmente afetados a jusante.
    </p>
    <div class="rolagem" style="max-height:220px"><table>
      <thead><tr>
        <th>Nível</th><th>IDAP</th><th>A</th><th>Chuva 24h</th><th>Chuva 72h</th>
        <th>Prevista</th><th>Saturação</th><th>Cemaden</th><th>Barragem</th><th>Sede</th>
      </tr></thead>
      <tbody id="clima"></tbody>
    </table></div>
    <p style="margin:8px 14px 12px;font-size:12px;color:var(--muted)">
      Lista: nível ≠ Verde <em>ou</em> pontos A &gt; 0. Clique na linha para ir ao mapa.
    </p>
  </details>
  <div class="cartao">
    <h2>Fila operacional (<span id="nFila">0</span>)</h2>
    <div class="rolagem"><table>
      <thead><tr>
        <th data-k="idap">IDAP</th><th>Nível</th><th>A</th><th>B</th><th>C</th><th>D</th>
        <th>Barragem</th><th>Sede</th><th>Afetados</th><th>Chuva 72h</th><th>Alertável</th>
      </tr></thead>
      <tbody id="fila"></tbody>
    </table></div>
  </div>
  <details class="bloco">
    <summary>Histórico de snapshots do índice</summary>
    <div id="histEstado" style="padding:10px 14px"></div>
    <div class="rolagem" style="max-height:160px"><table>
      <thead><tr><th>Barragem</th><th>Nível</th><th>Série</th><th>Último IDAP</th></tr></thead>
      <tbody id="histBarragens"></tbody>
    </table></div>
  </details>
  <p class="nota">
    Completude baixa não é “verde seguro”: leia lacunas no popup. Hidro = máximo sede+montante (Otto).
    C3 no eixo Cuiabá é proxy CNES (sem mancha). Alertável exige contatos validados (etapa 19).
    Instantâneo IDAP: <code>__INSTANTE__</code> · hidro ref.: <code>__DATA_HIDRO__</code>.
  </p>
</main>
<script>
const DADOS = __DADOS__;
const MALHA = __MALHA__;
const META = __META__;
const HIST = __HIST__;
const CORES = {Roxo:'#5b2c6f',Vermelho:'#c0392b',Laranja:'#d35400',Amarelo:'#b7950b',Verde:'#1e8449'};

function sparkMini(pts){
  if(!pts || !pts.length) return '—';
  const w=90,h=22,pad=2;
  const vals=pts.map(p=>p.idap);
  const min=Math.min(...vals,0), max=Math.max(...vals,20);
  const xs=pts.map((_,i)=>pad+i*((w-2*pad)/Math.max(pts.length-1,1)));
  const ys=pts.map(p=>h-pad-((p.idap-min)/(max-min||1))*(h-2*pad));
  const d=xs.map((x,i)=>(i?'L':'M')+x.toFixed(1)+','+ys[i].toFixed(1)).join(' ');
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><path d="${d}" fill="none" stroke="#0b6e4f" stroke-width="1.5"/></svg>`;
}

(function renderHist(){
  const ind = HIST.indice||[];
  const el = document.getElementById('histEstado');
  if(!ind.length){ el.textContent = 'Sem snapshots ainda (rode a etapa 16).'; return; }
  const ultimo = ind[ind.length-1];
  el.innerHTML = `<div style="font-size:13px;line-height:1.5">
    ${ind.length} snapshot(s) · último <code>${ultimo.t||'—'}</code>:
    Amarelo <b>${ultimo.ama||0}</b> · Laranja <b>${ultimo.lar||0}</b> ·
    Vermelho <b>${ultimo.ver||0}</b> · Roxo <b>${ultimo.rox||0}</b>
    <div style="margin-top:6px;color:var(--muted);font-size:12px">
      Contagem estadual por rodada:
      ${ind.map(x=>`${(x.t||'').slice(5,16)}→A${x.ama}`).join(' · ')}
    </div>
  </div>`;
  const ids = Object.keys(HIST.series||{});
  const linhas = ids.map(id => {
    const s = HIST.series[id];
    const d = porIdBase(id);
    const last = s[s.length-1];
    return {id, s, no: d?d.no:id, nv: last.nv, idap: last.idap};
  }).sort((a,b)=>b.idap-a.idap);
  document.getElementById('histBarragens').innerHTML = linhas.map(r =>
    `<tr data-id="${r.id}"><td><a href="barragem.html?id=${encodeURIComponent(r.id)}" style="color:var(--accent);font-weight:600;text-decoration:none">${r.no}</a></td>
     <td><span class="etq ${r.nv}">${r.nv}</span></td>
     <td>${sparkMini(r.s)}</td><td>${r.idap}</td></tr>`
  ).join('') || '<tr><td colspan="4">Nenhuma barragem acima de Verde nos snapshots.</td></tr>';
})();

function porIdBase(id){ return DADOS.find(d=>d.id===id); }

document.getElementById('semaforo').innerHTML =
  `<div class="luz" style="background:${CORES[META.semaforo]}"></div>
   <div><strong>Prontidão estadual: ${META.semaforo}</strong>
   — maior faixa vigente · ${META.total} barragens · eixo Manso–Cuiabá ${META.piloto||0}
   (em atenção+ no eixo: ${META.piloto_amarelo||0})</div>`;

const frescorEl = document.getElementById('frescor');
(META.frescor||[]).forEach(f => {
  const h = f.idade_h;
  let cls = 'morto';
  if (f.existe && h != null && h <= 24) cls = 'ok';
  else if (f.existe && h != null && h <= 72) cls = 'velho';
  const d = document.createElement('div');
  d.className = 'chip ' + cls;
  d.textContent = f.existe
    ? `${f.arquivo.replace('.csv','')}: ${h} h (${f.mtime})`
    : `${f.arquivo}: ausente`;
  frescorEl.appendChild(d);
});

(function resumoFrescor(){
  const el = document.getElementById('frescorResumo');
  if (!el) return;
  const fontes = META.frescor || [];
  const ausentes = fontes.filter(f => !f.existe).map(f => f.arquivo.replace('.csv',''));
  const idades = fontes.filter(f => f.existe && f.idade_h != null).map(f => f.idade_h);
  const pior = idades.length ? Math.max(...idades) : null;
  const velhas = idades.filter(h => h > 24).length;
  if (ausentes.length) el.textContent = `Fontes: ${ausentes.length} ausente(s) — ${ausentes.join(', ')}`;
  else if (velhas) el.textContent = `Fontes: mais antiga com ${Math.round(pior)} h (${velhas} acima de 24 h)`;
  else el.textContent = pior==null ? 'Frescor das fontes' : `Fontes atualizadas — mais antiga com ${Math.round(pior)} h`;
})();

function fmtDelta(d){
  if (d==null || d==='') return '';
  if (d===0) return '<div class="delta flat">→ 0 vs rodada anterior</div>';
  const seta = d>0 ? '▲' : '▼';
  const cls = d>0 ? 'up' : 'down';
  const sinal = d>0 ? '+' : '';
  return `<div class="delta ${cls}">${seta} ${sinal}${d} vs rodada anterior</div>`;
}

const TEND = META.tendencias || {};
const amareloMais = (META.risco && META.risco.amarelo_mais!=null)
  ? META.risco.amarelo_mais
  : ((META.niveis.Amarelo||0)+(META.niveis.Laranja||0)+(META.niveis.Vermelho||0)+(META.niveis.Roxo||0));

const kpis = document.getElementById('kpis');
// Faixa 1 só com o que decide; a distribuição por faixa vai numa linha compacta.
[
  ['Barragens monitoradas', META.total, 'sev-neutro', null],
  ['Em atenção+', amareloMais, 'sev-atencao', TEND.amarelo_mais],
  ['Situação estável (verde)', META.niveis.Verde||0, 'sev-ok', TEND.verde],
  ['Eixo Manso–Cuiabá', META.piloto||0, 'sev-neutro', null],
  ['Com canal de alerta', META.alertaveis, 'sev-neutro', null],
].forEach(([rotulo, n, tom, delta]) => {
  const d = document.createElement('div');
  d.className = 'kpi ' + tom;
  d.innerHTML = `<div class="n">${n}</div><div class="r">${rotulo}</div>${fmtDelta(delta)}`;
  kpis.appendChild(d);
});

(function distribuicaoFaixas(){
  const el = document.getElementById('kpiFaixas');
  if (!el) return;
  const itens = [
    ['Amarelo', META.niveis.Amarelo||0],
    ['Laranja', META.niveis.Laranja||0],
    ['Vermelho', META.niveis.Vermelho||0],
    ['Roxo', META.niveis.Roxo||0],
  ].map(([nv, n]) => `<span class="dist-item"><i style="background:${CORES[nv]}"></i>${nv} <b>${n}</b></span>`);
  itens.push(`<span class="dist-item"><i style="background:var(--ses)"></i>Impacto fora da sede <b>${META.extraterritoriais||0}</b></span>`);
  el.innerHTML = itens.join('');
})();

document.getElementById('kpiHelp').innerHTML =
  `<b>Como ler:</b> <b>Em atenção+</b> = barragens fora do Verde (Amarelo+Laranja+Vermelho+Roxo).
  Nesta rodada ${amareloMais} = só Faixa Amarelo (${META.niveis.Amarelo||0}), porque não há Laranja/Vermelho/Roxo.
  <b>Faixa Amarelo</b> = apenas IDAP 20–39. <b>Eixo Manso–Cuiabá</b> = ${META.piloto||0} barragens do recorte
  operacional (destas, ${META.piloto_amarelo||0} em atenção+) — não é contagem de risco estadual.`;

(function renderProj(){
  const P = META.projecao || {};
  const el = document.getElementById('projSemana');
  if (!el) return;
  const maxp = P.prevista_max_mm!=null ? String(P.prevista_max_mm).replace('.',',')+' mm' : '—';
  const delta = P.delta_vs_atual;
  const deltaTxt = delta==null ? '—' : (delta===0 ? 'estável (0)' : (delta>0?`+${delta}`:`${delta}`));
  el.innerHTML = `<h2>Projeção hidro — próximos dias (proxy)</h2>
    <p><b>Em atenção+ projetado:</b> ${P.amarelo_mais_projetado??'—'}
    (${deltaTxt} vs atual) · chuva prevista máx. ${maxp} ·
    sedes com previsão ≥40 mm: ${P.com_prevista_atencao??0} ·
    ≥140 mm (R12): ${P.com_prevista_extrema_r12??0}.<br>
    <span style="color:var(--muted)">${P.horizonte||''}. ${P.nota||''}</span></p>`;
})();

(function renderSanitario(){
  const S = META.sanitario || {};
  const el = document.getElementById('sanKpis');
  if (!el) return;
  const fmtN = (v) => (v==null || v==='') ? '—' : String(v).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  const razao = S.razao_pop_us;
  const principais = [
    ['População sob pressão sanitária', fmtN(S.pop_sob_pressao), S.pop_sob_pressao?'sev-atencao':'sev-ok'],
    ['US nos municípios sob pressão', fmtN(S.us_sob_risco), S.us_sob_risco?'sev-atencao':'sev-ok'],
    ['Razão pop. / US prioritária', razao==null?'—':fmtN(Math.round(razao)),
      razao==null?'sev-neutro':(razao>=2000?'sev-alto':razao>=800?'sev-atencao':'sev-ok')],
    ['Municípios sob pressão', S.municipios_sob_pressao??S.municipios_jusante, 'sev-atencao'],
    ['Completude média do índice', S.completude_media==null?'—':(S.completude_media+'%'),
      (S.completude_media!=null && S.completude_media>=70)?'sev-ok':((S.completude_media||0)>=40?'sev-atencao':'sev-alto')],
  ];
  const extras = [
    ['US prioritárias (hosp/UPA/UBS)', fmtN(S.us_prioritarias), S.us_prioritarias?'sev-atencao':'sev-ok'],
    ['Rejeito em atenção+', S.rejeito_atencao, S.rejeito_atencao?'sev-alto':'sev-ok'],
    ['Dano potencial alto sem canal', S.dpa_alto_sem_alerta, S.dpa_alto_sem_alerta?'sev-critico':'sev-ok'],
    ['Impacto extraterritorial ativo', S.extraterritorial_ativo, S.extraterritorial_ativo?'sev-atencao':'sev-ok'],
    ['Quase atenção (vigília)', S.quase_atencao, S.quase_atencao?'sev-atencao':'sev-ok'],
  ];
  const fill = (node, itens) => {
    if (!node) return;
    node.innerHTML = '';
    itens.forEach(([rotulo, n, tom]) => {
      const d = document.createElement('div');
      d.className = 'kpi ' + tom;
      d.innerHTML = `<div class="n">${n??'—'}</div><div class="r">${rotulo}</div>`;
      node.appendChild(d);
    });
  };
  fill(el, principais);
  fill(document.getElementById('sanKpisExtra'), extras);
  const nota = document.getElementById('sanNota');
  if (nota) nota.textContent = S.nota || '';
  const tb = document.getElementById('quaseLista');
  if (!tb) return;
  const lista = S.quase_lista || [];
  tb.innerHTML = lista.length
    ? lista.map(r => `<tr data-id="${r.id}"><td>${r.no}</td><td>${r.mu}</td><td>${r.idap}</td>
        <td>${r.pa}</td><td>${r.cprev??'—'}</td><td>${r.comp||'—'}</td></tr>`).join('')
    : '<tr><td colspan="6">Nenhuma barragem verde sob pressão climática relevante.</td></tr>';
})();

(function renderRisco(){
  const R = META.risco || {};
  const P = META.projecao || {};
  const fmt = (v, s='') => (v==null || v==='') ? '—' : (typeof v==='number' ? String(v).replace('.',',')+s : v);
  const sevPct = (p) => {
    if (p==null) return 'sev-neutro';
    if (p>=80) return 'sev-critico';
    if (p>=60) return 'sev-alto';
    if (p>=40) return 'sev-elevado';
    if (p>=20) return 'sev-atencao';
    return 'sev-ok';
  };
  const el = document.getElementById('riscoKpis');
  if (!el) return;
  const aPct = (R.a_medio!=null) ? (100*R.a_medio/30) : null;
  const bPct = (R.b_medio!=null) ? (100*R.b_medio/30) : null;
  const cPct = (R.c_medio!=null) ? (100*R.c_medio/25) : null;
  const dPct = (R.d_medio!=null) ? (100*R.d_medio/15) : null;
  const itens = [
    ['Índice de alerta máximo', R.idap_max, sevPct(R.idap_max), '0–100'],
    ['Índice de alerta médio', R.idap_medio, sevPct(R.idap_medio), ''],
    ['Pressão climática média', aPct==null?'—':Math.round(aPct)+'%', sevPct(aPct), fmt(R.a_medio)+' / 30'],
    ['Condição da estrutura', bPct==null?'—':Math.round(bPct)+'%', sevPct(bPct), fmt(R.b_medio)+' / 30'],
    ['Impacto sanitário potencial', cPct==null?'—':Math.round(cPct)+'%', sevPct(cPct), fmt(R.c_medio)+' / 25'],
    ['Déficit de resposta', dPct==null?'—':Math.round(dPct)+'%', sevPct(dPct), fmt(R.d_medio)+' / 15'],
    ['Chuva 24 h (máx.)', fmt(R.chuva24_max,' mm'), sevPct(R.chuva24_max), ''],
    ['Chuva 72 h (máx.)', fmt(R.chuva72_max,' mm'), sevPct(R.chuva72_max!=null?R.chuva72_max*0.5:null), ''],
    ['Chuva prevista (próx. dias)', fmt(R.prevista_max,' mm'),
      sevPct(R.prevista_max==null?null:(R.prevista_max>=140?100:R.prevista_max>=80?70:R.prevista_max>=40?40:10)), ''],
    ['Alertas oficiais de chuva/hidro', R.cemaden_ativos, R.cemaden_ativos?'sev-alto':'sev-ok', ''],
    ['Alertas externos / previsão extrema', (R.regras_r10||0)+(R.regras_r11||0)+(R.regras_r12||0),
      ((R.regras_r10||0)+(R.regras_r11||0)+(R.regras_r12||0))?'sev-elevado':'sev-ok', ''],
    ['Cadastro: risco estrutural alto', R.cri_alto, R.cri_alto?'sev-alto':'sev-ok', ''],
    ['Cadastro: dano potencial alto', R.dpa_alto, R.dpa_alto?'sev-alto':'sev-ok', ''],
    ['Em atenção+ projetado (próx. dias)', P.amarelo_mais_projetado, sevPct(P.amarelo_mais_projetado), 
      (P.delta_vs_atual==null?'':((P.delta_vs_atual>0?'+':'')+P.delta_vs_atual+' vs hoje'))],
  ];
  itens.forEach(([rotulo, val, sev, sub]) => {
    const d = document.createElement('div');
    d.className = 'kpi ' + (sev||'sev-neutro');
    d.innerHTML = `<div class="n">${val==null?'—':val}</div><div class="r">${rotulo}</div>` +
      (sub ? `<div class="sub">${sub}</div>` : '');
    el.appendChild(d);
  });
})();

const CORES_TIP = META.cores_tipologia || {};

function modoCor(){
  const el = document.getElementById('fCor');
  return el ? el.value : 'nv';
}

function corDe(d){
  return modoCor() === 'tp'
    ? (CORES_TIP[d.tp] || '#888')
    : (CORES[d.nv] || '#888');
}

function renderLegenda(){
  const porTipologia = modoCor() === 'tp';
  const pares = porTipologia ? Object.entries(CORES_TIP) : Object.entries(CORES);
  document.getElementById('legenda').innerHTML = pares.map(
    ([n,c]) => `<span><i style="background:${c}"></i>${n}</span>`
  ).join('');
  document.getElementById('tituloMapa').textContent =
    porTipologia ? 'tipologia (uso principal)' : 'faixa de prontidão';
}
renderLegenda();

function renderTipologia(lista){
  const el = document.getElementById('tipologiaBarras');
  if (!el) return;
  const estado = META.tipologias || [];
  if (!estado.length) { el.innerHTML = '<p style="margin:0;color:var(--muted)">Uso principal ausente no cadastro.</p>'; return; }
  const noRecorte = {};
  (lista||[]).forEach(d => { noRecorte[d.tp] = (noRecorte[d.tp]||0) + 1; });
  const maxN = Math.max(...estado.map(t => t.n), 1);
  el.innerHTML = estado.map(t => {
    const n = noRecorte[t.tp] || 0;
    const pctEstado = 100 * t.n / maxN;
    const pctRecorte = 100 * n / maxN;
    return `<div class="tip-linha" title="${t.tp}: ${t.n} no estado · ${n} no recorte">
      <span class="rot">${t.tp}</span>
      <span class="tip-barra"><i style="width:${pctEstado.toFixed(1)}%;background:${t.cor}"></i>
        ${n ? `<b style="left:calc(${pctRecorte.toFixed(1)}% - 1px)"></b>` : ''}</span>
      <span class="num">${t.n} · <b style="color:var(--ink)">${n}</b></span>
    </div>`;
  }).join('')
  + '<p style="margin:8px 0 0;font-size:11.5px;color:var(--muted)">'
  + 'Números: estado · recorte filtrado.</p>';
}

const mapa = L.map('mapa').setView([-13.0, -55.8], 6);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap', maxZoom: 12
}).addTo(mapa);
L.geoJSON(MALHA, {style:{color:'#8aa0b2',weight:0.6,fillOpacity:0.04}}).addTo(mapa);
const camada = L.layerGroup().addTo(mapa);
const porId = Object.fromEntries(DADOS.map(d => [d.id, d]));

function filtrados() {
  const nv = document.getElementById('fNivel').value;
  const mu = document.getElementById('fMun').value.trim().toLowerCase();
  const og = document.getElementById('fOrg').value.trim().toLowerCase();
  const al = document.getElementById('fAl').value;
  const pi = document.getElementById('fPi').value;
  const ext = document.getElementById('fExt').value;
  const q = document.getElementById('fBusca').value.trim().toLowerCase();
  return DADOS.filter(d => {
    if (nv && d.nv !== nv) return false;
    if (mu) {
      const sede = (d.mu||'').toLowerCase();
      const afet = (d.af||'').toLowerCase();
      const noSede = !(sede.includes(mu));
      const noAf = !afet.split('|').some(p => p.trim() && (p.trim()===mu || p.trim().includes(mu)));
      if (noSede && noAf) return false;
    }
    if (og && !(d.og||'').toLowerCase().includes(og)) return false;
    if (al && d.al !== al) return false;
    if (pi && !(d.pi === 1)) return false;
    if (ext && !(d.nex > 0)) return false;
    if (q && !(`${d.no} ${d.id}`).toLowerCase().includes(q)) return false;
    return true;
  });
}

function papelMun(d, mu) {
  if (!mu) return '';
  const sede = (d.mu||'').toLowerCase();
  const afet = (d.af||'').toLowerCase().split('|').map(p=>p.trim()).filter(Boolean);
  const isSede = sede.includes(mu);
  const isAf = afet.some(p => p===mu || p.includes(mu));
  if (isSede && isAf) return 'Sede e jusante';
  if (isSede) return 'Sede';
  if (isAf) return 'Afetado a jusante (barragem pode estar em outro município)';
  return '';
}

function popup(d) {
  const mu = document.getElementById('fMun').value.trim().toLowerCase();
  const papel = papelMun(d, mu);
  return `<b>${d.no}</b><br>Índice de alerta ${d.idap}/100 — <b>${d.nv}</b><br>
  Completude ${d.comp} (${d.conf})<br>
  Pressão clima ${d.pa} · Estrutura ${d.pb} · Impacto sanitário ${d.pc} · Déficit resposta ${d.pd}<br>
  Sede: ${d.mu}<br>
  Tipologia: ${d.tp || '—'}${d.us ? ` (${d.us})` : ''}<br>
  ${papel ? `<b>${papel}</b><br>` : ''}
  <b>Clima</b> — chuva 24h/72h: ${d.c24 ?? '—'} / ${d.c72 ?? '—'} mm<br>
  Prevista (próx. dias): ${d.cprev ?? '—'} mm<br>
  Alertas oficiais: ${d.cem || '—'} · integrado: ${d.aint || '—'}<br>
  Canal de alerta: ${d.al}<br>
  Potencialmente afetados: ${d.af || '—'}<br>
  ${d.reg ? 'Regras: '+d.reg+'<br>' : ''}
  <a href="barragem.html?id=${encodeURIComponent(d.id)}">Abrir Barragem 360°</a>`;
}

const ORDEM_NV = {Roxo:0,Vermelho:1,Laranja:2,Amarelo:3,Verde:4};

function render() {
  const lista = filtrados().slice().sort((a,b) => b.idap - a.idap || a.no.localeCompare(b.no));
  camada.clearLayers();
  const desenho = lista.slice().sort((a,b) => (ORDEM_NV[b.nv]??9) - (ORDEM_NV[a.nv]??9));
  const porTipologia = modoCor() === 'tp';
  desenho.forEach(d => {
    if (d.la == null || d.lo == null) return;
    const critico = d.nv !== 'Verde';
    const m = L.circleMarker([d.la, d.lo], {
      radius: porTipologia ? 5 : (critico ? 10 : (d.pi ? 5 : 3.5)),
      color: porTipologia ? '#fff' : (critico ? '#111' : (d.pi ? '#0b6e4f' : '#555')),
      weight: porTipologia ? 1 : (critico ? 2 : (d.pi ? 1.2 : 0.4)),
      fillColor: corDe(d),
      fillOpacity: porTipologia ? 0.9 : (critico ? 0.95 : 0.55)
    });
    m.bindPopup(popup(d));
    m.on('click', () => destacar(d.id));
    camada.addLayer(m);
  });

  const top = lista.slice(0, 15);
  document.getElementById('top').innerHTML = top.map(d => `<tr data-id="${d.id}">
    <td>${d.idap}</td><td><span class="etq ${d.nv}">${d.nv}</span></td>
    <td>${d.pa}</td>
    <td><a href="barragem.html?id=${encodeURIComponent(d.id)}" onclick="event.stopPropagation()"
      style="color:inherit;font-weight:600">${d.no}</a></td>
    <td>${d.mu}</td><td>${d.comp}</td>
    <td>${d.c24 ?? '—'}</td><td>${d.al}</td></tr>`).join('');

  document.getElementById('nFila').textContent = lista.length;
  document.getElementById('fila').innerHTML = lista.map(d => `<tr data-id="${d.id}">
    <td>${d.idap}</td><td><span class="etq ${d.nv}">${d.nv}</span></td>
    <td>${d.pa}</td><td>${d.pb}</td><td>${d.pc}</td><td>${d.pd}</td>
    <td title="${d.id}"><a href="barragem.html?id=${encodeURIComponent(d.id)}"
      onclick="event.stopPropagation()" style="color:inherit">${d.no}</a></td>
    <td>${d.mu}</td>
    <td title="${d.af}">${d.af ? d.af.split(' | ').length : 0}</td>
    <td>${d.c72 ?? '—'}</td><td>${d.al}</td></tr>`).join('');

  const climaEl = document.getElementById('clima');
  if (climaEl) {
    const clima = DADOS.filter(d => d.nv !== 'Verde' || (d.pa||0) > 0)
      .slice().sort((a,b) => b.idap - a.idap || (b.pa||0)-(a.pa||0));
    climaEl.innerHTML = clima.slice(0, 80).map(d => `<tr data-id="${d.id}">
      <td><span class="etq ${d.nv}">${d.nv}</span></td>
      <td>${d.idap}</td><td>${d.pa}</td>
      <td>${d.c24 ?? '—'}</td><td>${d.c72 ?? '—'}</td>
      <td>${d.cprev ?? '—'}</td>
      <td>${d.sat || '—'}</td><td>${d.cem || d.nh || '—'}</td>
      <td>${d.no}</td><td>${d.mu}</td></tr>`).join('')
      || '<tr><td colspan="10">Nenhuma barragem com pressão A ou nível acima de Verde.</td></tr>';
  }

  renderTipologia(lista);

  document.querySelectorAll('tbody tr[data-id]').forEach(tr => {
    tr.onclick = () => {
      const d = porId[tr.dataset.id];
      if (d && d.la != null) {
        mapa.setView([d.la, d.lo], 11);
        destacar(d.id);
      }
    };
  });
}

function destacar(id) {
  document.querySelectorAll('tbody tr').forEach(tr => {
    tr.style.background = tr.dataset.id === id ? '#e7f3ec' : '';
  });
}

document.getElementById('btnFiltrar').onclick = render;
document.getElementById('btnLimpar').onclick = () => {
  ['fNivel','fMun','fOrg','fAl','fPi','fExt','fBusca'].forEach(id => {
    const el = document.getElementById(id); el.value = '';
  });
  render();
  mapa.setView([-13.0, -55.8], 6);
};
const btnAm = document.getElementById('btnAmarelo');
if (btnAm) btnAm.onclick = () => {
  const pts = DADOS.filter(d => d.nv !== 'Verde' && d.la != null && d.lo != null);
  if (!pts.length) { alert('Nenhuma barragem em atenção+ com coordenada nesta rodada.'); return; }
  document.getElementById('fNivel').value = '';
  document.getElementById('fPi').value = '';
  document.getElementById('fMun').value = '';
  render();
  camada.clearLayers();
  pts.forEach(d => {
    const m = L.circleMarker([d.la, d.lo], {
      radius: 12, color:'#111', weight:2.5,
      fillColor: CORES[d.nv], fillOpacity:0.95
    });
    m.bindPopup(popup(d));
    camada.addLayer(m);
  });
  mapa.fitBounds(L.latLngBounds(pts.map(d => [d.la, d.lo])).pad(0.4));
};
['fNivel','fAl','fPi','fExt'].forEach(id => document.getElementById(id).onchange = render);
const selCor = document.getElementById('fCor');
if (selCor) selCor.onchange = () => { renderLegenda(); render(); };
['fMun','fOrg','fBusca'].forEach(id => {
  document.getElementById(id).addEventListener('keydown', e => { if (e.key==='Enter') render(); });
});
render();
(function destacarCriticosInicial() {
  const pts = DADOS.filter(d => d.nv !== 'Verde' && d.la != null);
  if (pts.length && pts.length <= 40) {
    setTimeout(() => mapa.fitBounds(L.latLngBounds(pts.map(d => [d.la, d.lo])).pad(0.55)), 350);
  }
})();
</script>
</body>
</html>
"""


def main() -> None:
    painel07 = _carregar_07()
    registros, meta = montar_registros()
    hist = ler_historico_comando()
    print(f"Comando estadual — {meta['total']} barragens · semáforo {meta['semaforo']}")
    print(f"  histórico: {len(hist['indice'])} snapshots · {len(hist['series'])} séries Amarelo+")

    malha = json.loads(
        (comum.DADOS_TRATADOS / "ibge_malha_municipios_mt_simplificada.geojson").read_text(
            encoding="utf-8"
        )
    )
    simplificada = painel07.simplificar_malha(malha)

    # Remove None para JSON mais enxuto (JS trata undefined via ??)
    for r in registros:
        for k in list(r):
            if r[k] is None:
                del r[k]

    dados_json = json.dumps(registros, ensure_ascii=False, separators=(",", ":"))
    malha_json = json.dumps(simplificada, ensure_ascii=False, separators=(",", ":"))
    meta_json = json.dumps(meta, ensure_ascii=False, separators=(",", ":"))
    hist_json = json.dumps(hist, ensure_ascii=False, separators=(",", ":"))
    print(f"  dados {len(dados_json)/1024:.0f} KB | malha {len(malha_json)/1024:.0f} KB")

    html = (
        MODELO.replace("__DADOS__", dados_json)
        .replace("__MALHA__", malha_json)
        .replace("__META__", meta_json)
        .replace("__HIST__", hist_json)
        .replace("__GERADO__", meta["gerado"])
        .replace("__INSTANTE__", meta["instante_idap"] or "—")
        .replace("__DATA_HIDRO__", meta["data_hidro"] or "—")
    )

    SAIDA.mkdir(parents=True, exist_ok=True)
    destino = SAIDA / "index.html"
    destino.write_text(html, encoding="utf-8")
    # Cópia nomeada para link estável
    (SAIDA / "comando.html").write_text(html, encoding="utf-8")
    print(f"  gravado {destino.relative_to(comum.RAIZ)}")
    print(f"  gravado painel/comando.html")


if __name__ == "__main__":
    main()
