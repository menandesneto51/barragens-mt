"""Checklist operacional de PAE/PAEBM por barragem (lacunas explícitas)."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

TRATADOS = Path(__file__).resolve().parents[1] / "dados" / "tratados"
COBERTURA = TRATADOS / "pae_manchas_cobertura.csv"
SIGBM = TRATADOS / "sigbm_barragens_mt.csv"

COL_PAEBM_NEC = "Necessita de PAEBM"
COL_PAE_SIGBM = (
    "PAE - Plano de Ação Emergencial (quando exigido pelo órgão fiscalizador)"
)
COL_COPIAS = (
    "As cópias físicas do PAEBM foram entregues para as Prefeituras e "
    "Defesas Civis municipais e estaduais"
)


def _norm(s: Any) -> str:
    t = str(s or "").strip().lower()
    t = (
        t.replace("á", "a")
        .replace("à", "a")
        .replace("ã", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    return re.sub(r"\s+", " ", t)


def _vazio(v: Any) -> bool:
    if v is None:
        return True
    try:
        if pd.isna(v):
            return True
    except Exception:
        pass
    s = str(v).strip()
    return s == "" or s in {"-", "nan", "None", "não informado", "nao informado"}


def _status_sim_nao_lacuna(v: Any) -> str:
    if _vazio(v):
        return "lacuna"
    s = _norm(v)
    if s in {"sim", "s", "yes", "true", "1"}:
        return "ok"
    if s in {"nao", "não", "n", "no", "false", "0"}:
        return "nao"
    if "desconhec" in s or "nao classif" in s or "não classif" in s:
        return "lacuna"
    return "atencao"


@lru_cache(maxsize=1)
def _cobertura_df() -> pd.DataFrame:
    if not COBERTURA.is_file():
        return pd.DataFrame()
    return pd.read_csv(COBERTURA, sep=";", dtype=str).fillna("")


@lru_cache(maxsize=1)
def _sigbm_df() -> pd.DataFrame:
    if not SIGBM.is_file():
        return pd.DataFrame()
    return pd.read_csv(SIGBM, sep=";", dtype=str).fillna("")


def _lookup_cobertura(id_snisb: Any) -> dict[str, Any]:
    df = _cobertura_df()
    if df.empty or "id_snisb" not in df.columns:
        return {}
    sid = str(id_snisb or "").strip()
    hit = df[df["id_snisb"].astype(str) == sid]
    if hit.empty:
        return {}
    return hit.iloc[0].to_dict()


def _lookup_sigbm(nome: Any, municipio: Any) -> dict[str, Any]:
    df = _sigbm_df()
    if df.empty or "Nome" not in df.columns:
        return {}
    nn = _norm(nome)
    mm = _norm(municipio)
    if not nn:
        return {}
    cand = df[df["Nome"].map(_norm) == nn]
    if cand.empty:
        # prefixo curto
        cand = df[df["Nome"].map(_norm).str.startswith(nn[:12])]
    if cand.empty:
        return {}
    if mm and "Município" in cand.columns:
        m2 = cand[cand["Município"].map(_norm) == mm]
        if not m2.empty:
            cand = m2
    return cand.iloc[0].to_dict()


def _item(codigo: str, titulo: str, status: str, detalhe: str, fonte: str) -> dict[str, str]:
    return {
        "codigo": codigo,
        "titulo": titulo,
        "status": status,
        "detalhe": detalhe,
        "fonte": fonte,
    }


def montar_checklist_pae(registro: dict[str, Any] | pd.Series) -> dict[str, Any]:
    """Monta checklist a partir de uma linha do inventário / IDAP."""
    if isinstance(registro, pd.Series):
        r = registro.to_dict()
    else:
        r = dict(registro or {})

    id_snisb = r.get("id_snisb")
    nome = r.get("nome") or r.get("Nome") or ""
    mun = r.get("municipio_sede") or r.get("municipio") or ""
    cob = _lookup_cobertura(id_snisb)
    sig = _lookup_sigbm(nome, mun)

    itens: list[dict[str, str]] = []

    # 1 — PAE SNISB
    pae_raw = r.get("possui_pae")
    if cob.get("tem_pae"):
        tem = str(cob.get("tem_pae")).lower()
        if tem == "sim":
            st_pae, det = "ok", "SNISB declara possui_pae = Sim"
        elif tem == "nao":
            st_pae, det = "nao", "SNISB declara possui_pae = Não"
        else:
            st_pae, det = "lacuna", cob.get("observacao") or "possui_pae vazio no SNISB"
    else:
        st_pae = _status_sim_nao_lacuna(pae_raw)
        det = f"possui_pae={pae_raw!r}" if not _vazio(pae_raw) else "campo vazio"
    itens.append(_item("PAE-01", "Possui PAE (SNISB)", st_pae, det, "SNISB / etapa 47"))

    # 2 — Plano de segurança
    ps = r.get("possui_plano_de_seguranca")
    itens.append(
        _item(
            "PAE-02",
            "Plano de segurança da barragem",
            _status_sim_nao_lacuna(ps),
            f"possui_plano_de_seguranca={ps!r}" if not _vazio(ps) else "campo vazio",
            "SNISB",
        )
    )

    # 3 — Revisão periódica
    rev = r.get("possui_revisao_periodica")
    itens.append(
        _item(
            "PAE-03",
            "Revisão periódica de segurança",
            _status_sim_nao_lacuna(rev),
            f"possui_revisao_periodica={rev!r}" if not _vazio(rev) else "campo vazio",
            "SNISB",
        )
    )

    # 4 — Mancha ZAS oficial
    zas = cob.get("tem_mancha_zas") or "nao"
    if str(zas).lower() in {"sim", "ok", "1"}:
        st_zas, det_zas = "ok", cob.get("caminho_geojson") or "mancha registrada"
    else:
        st_zas, det_zas = "lacuna", "Mancha ZAS oficial ainda não ingerida (SEMA/empreendedor/ANM)"
    itens.append(_item("PAE-04", "Mancha ZAS oficial disponível", st_zas, det_zas, "etapa 47"))

    # 5 — Canal de alerta / alertável
    alert = r.get("alertavel")
    canal = r.get("canal_alerta") or r.get("regras_disparadas")
    if not _vazio(alert) and _norm(alert) in {"sim", "true", "1"}:
        st_al, det_al = "ok", f"alertavel={alert}"
    elif not _vazio(canal):
        st_al, det_al = "atencao", f"sinal de canal/regras: {canal}"
    else:
        st_al, det_al = "lacuna", "sem flag alertável / canal no recorte"
    itens.append(_item("PAE-05", "Canal de alerta operacional", st_al, det_al, "IDAP / hidro"))

    # 6–8 — SIGBM (mineração), quando houver match
    if sig:
        nec = sig.get(COL_PAEBM_NEC)
        st_nec = _status_sim_nao_lacuna(nec)
        # "Não" para "necessita" é ok (não exige)
        if st_nec == "nao":
            st_nec, det_nec = "ok", "Não necessita PAEBM"
        elif st_nec == "ok":
            st_nec, det_nec = "atencao", "Necessita PAEBM — verificar cumprimento"
        else:
            det_nec = f"{COL_PAEBM_NEC}={nec!r}"
        itens.append(_item("PAE-06", "Necessita PAEBM (SIGBM)", st_nec, det_nec, "SIGBM/ANM"))

        pae_s = sig.get(COL_PAE_SIGBM)
        if _vazio(pae_s):
            st_ps, det_ps = "lacuna", "campo PAE SIGBM vazio"
        else:
            ns = _norm(pae_s)
            if "possui pae" in ns and "nao possui" not in ns and "não possui" not in ns:
                st_ps, det_ps = "ok", str(pae_s)
            elif "elaboracao" in ns or "elaboração" in ns:
                st_ps, det_ps = "atencao", str(pae_s)
            elif "nao e exigido" in ns or "não é exigido" in ns or "nao se aplica" in ns:
                st_ps, det_ps = "ok", str(pae_s)
            elif "nao possui" in ns or "não possui" in ns:
                st_ps, det_ps = "nao", str(pae_s)
            else:
                st_ps, det_ps = "atencao", str(pae_s)
        itens.append(_item("PAE-07", "PAE/PAEBM (SIGBM)", st_ps, det_ps, "SIGBM/ANM"))

        cop = sig.get(COL_COPIAS)
        if _vazio(cop) or _norm(cop) in {"-", "nao se aplica", "não se aplica"}:
            if st_nec == "ok" and "Não necessita" in det_nec:
                st_c, det_c = "ok", "não se aplica (sem exigência PAEBM)"
            else:
                st_c, det_c = "lacuna", f"cópias PAEBM={cop!r}"
        elif _norm(cop) in {"sim"}:
            st_c, det_c = "ok", "Cópias físicas entregues às prefeituras/DCs"
        elif _norm(cop) in {"nao", "não"}:
            st_c, det_c = "nao", "Cópias físicas NÃO entregues"
        else:
            st_c, det_c = "atencao", str(cop)
        itens.append(
            _item("PAE-08", "Cópias PAEBM entregues (prefeitura/DC)", st_c, det_c, "SIGBM/ANM")
        )
    else:
        itens.append(
            _item(
                "PAE-06",
                "Necessita PAEBM (SIGBM)",
                "lacuna",
                "sem match SIGBM por nome/município (não mineração ou nome diverge)",
                "SIGBM/ANM",
            )
        )
        itens.append(
            _item(
                "PAE-07",
                "PAE/PAEBM (SIGBM)",
                "lacuna",
                "sem match SIGBM",
                "SIGBM/ANM",
            )
        )
        itens.append(
            _item(
                "PAE-08",
                "Cópias PAEBM entregues (prefeitura/DC)",
                "lacuna",
                "sem match SIGBM",
                "SIGBM/ANM",
            )
        )

    cont = {"ok": 0, "nao": 0, "lacuna": 0, "atencao": 0}
    for it in itens:
        cont[it["status"]] = cont.get(it["status"], 0) + 1

    return {
        "ok": True,
        "id_snisb": str(id_snisb or ""),
        "nome": str(nome or ""),
        "municipio": str(mun or ""),
        "itens": itens,
        "resumo": cont,
        "n_itens": len(itens),
        "n_lacunas": cont.get("lacuna", 0) + cont.get("nao", 0),
        "fonte": "Checklist PAE proxy — SNISB + cobertura 47 + SIGBM (quando houver)",
    }


def checklist_para_dataframe(checklist: dict[str, Any]) -> pd.DataFrame:
    itens = checklist.get("itens") or []
    return pd.DataFrame(itens)


def exportar_checklist_csv(checklist: dict[str, Any]) -> str:
    df = checklist_para_dataframe(checklist)
    return df.to_csv(sep=";", index=False, encoding="utf-8-sig")
