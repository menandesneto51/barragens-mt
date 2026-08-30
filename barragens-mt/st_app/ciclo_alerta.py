"""Ciclo de alerta do piloto: emissão → confirmação → escalonamento → payload DC.

Persistência em `dados/tratados/confirmacoes/`:
  - alertas_ciclo.csv
  - confirmacoes.csv
  - escalonamentos_log.csv

Prazos (§4.6.2 / idap.relatorio): Amarelo 120, Laranja 60, Vermelho 20, Roxo 10 min.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
import uuid
from pathlib import Path
from typing import Any

import pandas as pd

TRATADOS = Path(__file__).resolve().parents[1] / "dados" / "tratados"
PASTA = TRATADOS / "confirmacoes"
ALERTAS = PASTA / "alertas_ciclo.csv"
CONFIRMACOES = PASTA / "confirmacoes.csv"
ESCALONAMENTOS = PASTA / "escalonamentos_log.csv"
PAYLOADS = PASTA / "payloads_defesa_civil"

PRAZO_MIN: dict[str, int | None] = {
    "Verde": None,
    "Amarelo": 120,
    "Laranja": 60,
    "Vermelho": 20,
    "Roxo": 10,
}

CAMPOS_ALERTA = [
    "id_alerta",
    "id_snisb",
    "nome",
    "municipio_sede",
    "municipios_afetados",
    "nivel",
    "idap",
    "instante_emissao",
    "prazo_min",
    "prazo_limite",
    "estado",
    "n_escalonamentos",
    "texto_resumo",
    "lat",
    "lon",
    "fonte",
]

CAMPOS_CONF = [
    "instante",
    "id_alerta",
    "id_snisb",
    "responsavel",
    "canal",
    "observacao",
]

CAMPOS_ESC = [
    "instante",
    "id_alerta",
    "id_snisb",
    "nivel",
    "n_escalonamento",
    "motivo",
    "estado_anterior",
    "estado_novo",
]


def _agora() -> dt.datetime:
    return dt.datetime.now().astimezone()


def _iso(d: dt.datetime | None = None) -> str:
    return (d or _agora()).isoformat(timespec="seconds")


def garantir_pasta() -> Path:
    PASTA.mkdir(parents=True, exist_ok=True)
    PAYLOADS.mkdir(parents=True, exist_ok=True)
    return PASTA


def _ler(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path, sep=";", dtype=str, encoding="utf-8-sig")


def _gravar(path: Path, rows: list[dict[str, Any]], campos: list[str]) -> None:
    garantir_pasta()
    existe = path.is_file()
    with path.open("a" if existe else "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";", extrasaction="ignore")
        if not existe:
            w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in campos})


def _reescrever(path: Path, df: pd.DataFrame, campos: list[str]) -> None:
    garantir_pasta()
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";", extrasaction="ignore")
        w.writeheader()
        for _, r in df.iterrows():
            w.writerow({k: r.get(k, "") if k in r.index else "" for k in campos})


def carregar_alertas() -> pd.DataFrame:
    df = _ler(ALERTAS)
    if df.empty:
        return pd.DataFrame(columns=CAMPOS_ALERTA)
    return df


def carregar_confirmacoes() -> pd.DataFrame:
    df = _ler(CONFIRMACOES)
    if df.empty:
        return pd.DataFrame(columns=CAMPOS_CONF)
    return df


def carregar_escalonamentos() -> pd.DataFrame:
    df = _ler(ESCALONAMENTOS)
    if df.empty:
        return pd.DataFrame(columns=CAMPOS_ESC)
    return df


def prazo_minutos(nivel: str) -> int | None:
    return PRAZO_MIN.get(str(nivel or "").strip())


def _parse_dt(raw: object) -> dt.datetime | None:
    s = str(raw or "").strip()
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s)
    except ValueError:
        return None


def emitir_alerta(
    *,
    id_snisb: str,
    nome: str,
    municipio_sede: str,
    nivel: str,
    idap: object = None,
    municipios_afetados: str = "",
    lat: object = None,
    lon: object = None,
    texto_resumo: str | None = None,
    fonte: str = "streamlit",
    agora: dt.datetime | None = None,
) -> dict[str, Any]:
    """Emite alerta no ciclo (não envia canal — só trilha auditável)."""
    nivel_n = str(nivel or "Amarelo").strip() or "Amarelo"
    prazo = prazo_minutos(nivel_n)
    if prazo is None:
        raise ValueError(f"Nível {nivel_n} não exige confirmação (Verde).")
    agora = agora or _agora()
    limite = agora + dt.timedelta(minutes=prazo)
    bid = str(id_snisb or "").strip()
    id_alerta = f"ALT-{bid or 'X'}-{agora.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    resumo = texto_resumo or (
        f"Prontidão sanitária {nivel_n} — {nome} ({municipio_sede}). "
        "Não é ordem de evacuação."
    )
    row = {
        "id_alerta": id_alerta,
        "id_snisb": bid,
        "nome": str(nome or ""),
        "municipio_sede": str(municipio_sede or ""),
        "municipios_afetados": str(municipios_afetados or ""),
        "nivel": nivel_n,
        "idap": "" if idap is None else str(idap),
        "instante_emissao": _iso(agora),
        "prazo_min": str(prazo),
        "prazo_limite": _iso(limite),
        "estado": "AGUARDANDO_CONFIRMACAO",
        "n_escalonamentos": "0",
        "texto_resumo": resumo,
        "lat": "" if lat is None else str(lat),
        "lon": "" if lon is None else str(lon),
        "fonte": fonte,
    }
    _gravar(ALERTAS, [row], CAMPOS_ALERTA)
    payload = payload_defesa_civil(row)
    caminho = PAYLOADS / f"{id_alerta}.json"
    caminho.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    row["payload_path"] = str(caminho.relative_to(TRATADOS.parent) if False else caminho.name)
    return row


def registrar_confirmacao(
    *,
    id_alerta: str,
    responsavel: str,
    canal: str = "telefone",
    observacao: str = "",
    agora: dt.datetime | None = None,
) -> dict[str, Any]:
    id_alerta = str(id_alerta or "").strip()
    responsavel = str(responsavel or "").strip()
    if not id_alerta or not responsavel:
        raise ValueError("id_alerta e responsavel são obrigatórios")
    agora = agora or _agora()
    alertas = carregar_alertas()
    id_snisb = ""
    if not alertas.empty and "id_alerta" in alertas.columns:
        hit = alertas[alertas["id_alerta"].astype(str) == id_alerta]
        if not hit.empty:
            id_snisb = str(hit.iloc[0].get("id_snisb") or "")
            alertas.loc[hit.index, "estado"] = "CONFIRMADO"
            _reescrever(ALERTAS, alertas, CAMPOS_ALERTA)
    reg = {
        "instante": _iso(agora),
        "id_alerta": id_alerta,
        "id_snisb": id_snisb,
        "responsavel": responsavel,
        "canal": canal,
        "observacao": observacao,
    }
    _gravar(CONFIRMACOES, [reg], CAMPOS_CONF)
    return reg


def processar_escalonamentos(*, agora: dt.datetime | None = None) -> list[dict[str, Any]]:
    """Marca AGUARDANDO → ESCALONADO (1º) → ESCALONADO_MAXIMO (2º) quando prazo vence."""
    agora = agora or _agora()
    alertas = carregar_alertas()
    if alertas.empty:
        return []
    eventos: list[dict[str, Any]] = []
    mudou = False
    for idx, r in alertas.iterrows():
        estado = str(r.get("estado") or "")
        if estado in {"CONFIRMADO", "ENCERRADO", "CANCELADO", "ESCALONADO_MAXIMO"}:
            continue
        if estado not in {"AGUARDANDO_CONFIRMACAO", "ESCALONADO"}:
            continue
        limite = _parse_dt(r.get("prazo_limite"))
        if limite is None:
            continue
        # Normaliza tz
        if limite.tzinfo is None:
            limite = limite.replace(tzinfo=agora.tzinfo)
        if agora < limite:
            continue
        n_esc = int(float(str(r.get("n_escalonamentos") or 0) or 0))
        estado_ant = estado
        if estado == "AGUARDANDO_CONFIRMACAO":
            estado_novo = "ESCALONADO"
            n_esc = max(1, n_esc + 1)
            motivo = "Prazo de confirmação esgotado — 1º escalonamento (substituto/regional)."
            # Novo prazo = mesmo intervalo do nível
            prazo = int(float(str(r.get("prazo_min") or 0) or 0))
            if prazo > 0:
                alertas.at[idx, "prazo_limite"] = _iso(agora + dt.timedelta(minutes=prazo))
        else:
            estado_novo = "ESCALONADO_MAXIMO"
            n_esc = max(2, n_esc + 1)
            motivo = "2º prazo esgotado — falha institucional / gabinete SES-MT."
        alertas.at[idx, "estado"] = estado_novo
        alertas.at[idx, "n_escalonamentos"] = str(n_esc)
        ev = {
            "instante": _iso(agora),
            "id_alerta": str(r.get("id_alerta") or ""),
            "id_snisb": str(r.get("id_snisb") or ""),
            "nivel": str(r.get("nivel") or ""),
            "n_escalonamento": str(n_esc),
            "motivo": motivo,
            "estado_anterior": estado_ant,
            "estado_novo": estado_novo,
        }
        eventos.append(ev)
        mudou = True
    if mudou:
        _reescrever(ALERTAS, alertas, CAMPOS_ALERTA)
    if eventos:
        _gravar(ESCALONAMENTOS, eventos, CAMPOS_ESC)
    return eventos


def payload_defesa_civil(alerta: dict[str, Any] | pd.Series) -> dict[str, Any]:
    """Payload §13.2 — prontidão sanitária, não evacuação."""
    if isinstance(alerta, pd.Series):
        alerta = alerta.to_dict()
    lat = alerta.get("lat")
    lon = alerta.get("lon")
    try:
        lat_f = float(str(lat).replace(",", ".")) if lat not in (None, "") else None
    except ValueError:
        lat_f = None
    try:
        lon_f = float(str(lon).replace(",", ".")) if lon not in (None, "") else None
    except ValueError:
        lon_f = None
    afetados = [
        p.strip()
        for p in re.split(r"[|;,]", str(alerta.get("municipios_afetados") or ""))
        if p.strip()
    ]
    return {
        "sistema": "VIGIBARRAGENS-MT",
        "tipo": "alerta_prontidao_saude",
        "instante": str(alerta.get("instante_emissao") or _iso()),
        "nivel": str(alerta.get("nivel") or ""),
        "idap": alerta.get("idap"),
        "id_alerta": str(alerta.get("id_alerta") or ""),
        "barragem_id_snisb": str(alerta.get("id_snisb") or ""),
        "barragem_nome": str(alerta.get("nome") or ""),
        "municipio_sede": str(alerta.get("municipio_sede") or ""),
        "municipios_potencialmente_afetados": afetados,
        "papel_destinatario": "potencialmente_afetado_jusante",
        "coordenadas": {"lat": lat_f, "lon": lon_f},
        "texto_resumo": str(
            alerta.get("texto_resumo")
            or "Prontidão sanitária — não é ordem de evacuação."
        ),
        "texto_completo_ref": f"confirmacoes/payloads_defesa_civil/{alerta.get('id_alerta')}.json",
        "contato_ses": "CIEVS-MT",
        "canais_sugeridos": ["telefone", "email", "telegram"],
        "ressalva": "Este alerta não constitui ordem de evacuação.",
        "estado": str(alerta.get("estado") or ""),
        "prazo_limite": str(alerta.get("prazo_limite") or ""),
    }


def resumo_ciclo() -> dict[str, Any]:
    al = carregar_alertas()
    conf = carregar_confirmacoes()
    esc = carregar_escalonamentos()
    if al.empty:
        return {
            "n_emitidos": 0,
            "n_aguardando": 0,
            "n_confirmados": 0,
            "n_escalonados": 0,
            "n_escalonado_maximo": 0,
            "n_confirmacoes": 0,
            "n_eventos_esc": 0,
        }
    est = al["estado"].fillna("").astype(str)
    return {
        "n_emitidos": len(al),
        "n_aguardando": int((est == "AGUARDANDO_CONFIRMACAO").sum()),
        "n_confirmados": int((est == "CONFIRMADO").sum()),
        "n_escalonados": int((est == "ESCALONADO").sum()),
        "n_escalonado_maximo": int((est == "ESCALONADO_MAXIMO").sum()),
        "n_confirmacoes": len(conf),
        "n_eventos_esc": len(esc),
        "sem_confirmacao": al[est.isin(["AGUARDANDO_CONFIRMACAO", "ESCALONADO", "ESCALONADO_MAXIMO"])],
    }


def alertas_sem_confirmacao_ids() -> list[str]:
    al = carregar_alertas()
    if al.empty:
        return []
    est = al["estado"].fillna("").astype(str)
    sub = al[est.isin(["AGUARDANDO_CONFIRMACAO", "ESCALONADO", "ESCALONADO_MAXIMO"])]
    return sub["id_alerta"].astype(str).tolist()
