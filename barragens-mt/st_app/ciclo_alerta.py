"""Ciclo de alerta do piloto: emissão → supervisão → despacho → confirmação → escalonamento.

Persistência em `dados/tratados/confirmacoes/`:
  - alertas_ciclo.csv
  - confirmacoes.csv
  - escalonamentos_log.csv
  - payloads_defesa_civil/*.json

Textos territorializados em `alertas/piloto/ciclo_*.txt` para o despacho 29.

Prazos (§4.6.2): Amarelo 120, Laranja 60, Vermelho 20, Roxo 10 min.
Vermelho/Roxo exigem supervisão humana antes do despacho (A7).
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

RAIZ = Path(__file__).resolve().parents[1]
TRATADOS = RAIZ / "dados" / "tratados"
PASTA = TRATADOS / "confirmacoes"
ALERTAS = PASTA / "alertas_ciclo.csv"
CONFIRMACOES = PASTA / "confirmacoes.csv"
ESCALONAMENTOS = PASTA / "escalonamentos_log.csv"
PAYLOADS = PASTA / "payloads_defesa_civil"
FILA_TXT = RAIZ / "alertas" / "piloto"

PRAZO_MIN: dict[str, int | None] = {
    "Verde": None,
    "Amarelo": 120,
    "Laranja": 60,
    "Vermelho": 20,
    "Roxo": 10,
}

NIVEIS_SUPERVISAO = frozenset({"Vermelho", "Roxo"})

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
    "arquivo_txt",
    "supervisor",
    "instante_supervisao",
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
    FILA_TXT.mkdir(parents=True, exist_ok=True)
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
    # Garante colunas novas em CSVs legados
    for c in campos:
        if c not in df.columns:
            df[c] = ""
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";", extrasaction="ignore")
        w.writeheader()
        for _, r in df.iterrows():
            w.writerow({k: ("" if pd.isna(r.get(k)) else r.get(k, "")) for k in campos})


def carregar_alertas() -> pd.DataFrame:
    df = _ler(ALERTAS)
    if df.empty:
        return pd.DataFrame(columns=CAMPOS_ALERTA)
    for c in CAMPOS_ALERTA:
        if c not in df.columns:
            df[c] = ""
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


def exige_supervisao(nivel: str) -> bool:
    return str(nivel or "").strip() in NIVEIS_SUPERVISAO


def _parse_dt(raw: object) -> dt.datetime | None:
    s = str(raw or "").strip()
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s)
    except ValueError:
        return None


def montar_texto_piloto(alerta: dict[str, Any]) -> str:
    """Texto curto territorializado para a fila alertas/piloto/."""
    nivel = str(alerta.get("nivel") or "")
    linhas = [
        "=" * 78,
        f"ALERTA VIGIBARRAGENS-MT — NÍVEL {nivel.upper()}",
        "=" * 78,
        f"Identificador do alerta : {alerta.get('id_alerta')}",
        f"Barragem                : {alerta.get('nome')} (código {alerta.get('id_snisb')})",
        f"Município da estrutura  : {alerta.get('municipio_sede')} — MT",
        f"Data e hora da emissão  : {alerta.get('instante_emissao')}",
        f"IDAP                    : {alerta.get('idap') or '—'}",
        f"Nível final             : {nivel}",
        f"Estado do ciclo         : {alerta.get('estado')}",
        f"Prazo confirmação até   : {alerta.get('prazo_limite')} ({alerta.get('prazo_min')} min)",
        "",
        "1. RESUMO",
        f"   {alerta.get('texto_resumo')}",
        "",
        "2. MUNICÍPIOS POTENCIALMENTE AFETADOS",
        f"   {alerta.get('municipios_afetados') or '—'}",
        "",
        "3. RESSALVA OBRIGATÓRIA",
        "   Este alerta NÃO constitui ordem de evacuação.",
        "   Evacuação é exclusividade da Defesa Civil.",
        "",
        "4. CONFIRMAÇÃO",
        "   Confirmar recebimento com nome e cargo na tela",
        "   Alertabilidade / Confirmação (ciclo auditável).",
        "",
        f"Arquivo gerado pelo ciclo · fonte={alerta.get('fonte')}",
        "=" * 78,
        "",
    ]
    return "\n".join(linhas)


def _gravar_txt_piloto(alerta: dict[str, Any]) -> str:
    garantir_pasta()
    nivel = str(alerta.get("nivel") or "alerta").casefold()
    bid = str(alerta.get("id_snisb") or "x")
    nome = f"ciclo_{nivel}_{bid}_{alerta.get('id_alerta')}.txt"
    path = FILA_TXT / nome
    path.write_text(montar_texto_piloto(alerta), encoding="utf-8")
    return nome


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
    gravar_txt: bool = True,
) -> dict[str, Any]:
    """Emite alerta no ciclo. Vermelho/Roxo ficam AGUARDANDO_SUPERVISAO."""
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
    estado = (
        "AGUARDANDO_SUPERVISAO"
        if exige_supervisao(nivel_n)
        else "AGUARDANDO_CONFIRMACAO"
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
        "estado": estado,
        "n_escalonamentos": "0",
        "texto_resumo": resumo,
        "lat": "" if lat is None else str(lat),
        "lon": "" if lon is None else str(lon),
        "fonte": fonte,
        "arquivo_txt": "",
        "supervisor": "",
        "instante_supervisao": "",
    }
    if gravar_txt:
        row["arquivo_txt"] = _gravar_txt_piloto(row)
    _gravar(ALERTAS, [row], CAMPOS_ALERTA)
    payload = payload_defesa_civil(row)
    caminho = PAYLOADS / f"{id_alerta}.json"
    caminho.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    row["payload_path"] = caminho.name
    return row


def autorizar_supervisao(
    *,
    id_alerta: str,
    supervisor: str,
    agora: dt.datetime | None = None,
) -> dict[str, Any]:
    """Autoriza envio de alerta Vermelho/Roxo (A7)."""
    id_alerta = str(id_alerta or "").strip()
    supervisor = str(supervisor or "").strip()
    if not id_alerta or not supervisor:
        raise ValueError("id_alerta e supervisor são obrigatórios")
    agora = agora or _agora()
    alertas = carregar_alertas()
    if alertas.empty:
        raise ValueError("nenhum alerta no ciclo")
    hit = alertas[alertas["id_alerta"].astype(str) == id_alerta]
    if hit.empty:
        raise ValueError(f"alerta {id_alerta} não encontrado")
    idx = hit.index[0]
    estado = str(alertas.at[idx, "estado"] or "")
    nivel = str(alertas.at[idx, "nivel"] or "")
    if estado != "AGUARDANDO_SUPERVISAO":
        raise ValueError(f"alerta em estado {estado} — supervisão só em AGUARDANDO_SUPERVISAO")
    if not exige_supervisao(nivel):
        raise ValueError(f"nível {nivel} não exige supervisão")
    alertas.at[idx, "estado"] = "AGUARDANDO_CONFIRMACAO"
    alertas.at[idx, "supervisor"] = supervisor
    alertas.at[idx, "instante_supervisao"] = _iso(agora)
    # Regenera texto com estado atualizado
    row = alertas.loc[idx].to_dict()
    row["arquivo_txt"] = _gravar_txt_piloto(row)
    alertas.at[idx, "arquivo_txt"] = row["arquivo_txt"]
    _reescrever(ALERTAS, alertas, CAMPOS_ALERTA)
    return row


def pode_despachar(alerta: dict[str, Any] | pd.Series) -> tuple[bool, str]:
    """Dry-run/--enviar só após supervisão (quando exigida) e antes de CONFIRMADO."""
    if isinstance(alerta, pd.Series):
        alerta = alerta.to_dict()
    estado = str(alerta.get("estado") or "")
    nivel = str(alerta.get("nivel") or "")
    if estado == "AGUARDANDO_SUPERVISAO":
        return False, "aguardando supervisão humana (Vermelho/Roxo)"
    if estado in {"CONFIRMADO", "ENCERRADO", "CANCELADO"}:
        return False, f"estado terminal {estado}"
    if exige_supervisao(nivel) and not str(alerta.get("supervisor") or "").strip():
        return False, "supervisor não registrado"
    if estado in {"AGUARDANDO_CONFIRMACAO", "ESCALONADO", "ESCALONADO_MAXIMO", "ENVIADO"}:
        return True, "ok"
    return False, f"estado {estado} não despachável"


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
            estado = str(hit.iloc[0].get("estado") or "")
            if estado == "AGUARDANDO_SUPERVISAO":
                raise ValueError("confirme só após supervisão (Vermelho/Roxo)")
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
    """Marca AGUARDANDO_CONFIRMACAO → ESCALONADO → ESCALONADO_MAXIMO."""
    agora = agora or _agora()
    alertas = carregar_alertas()
    if alertas.empty:
        return []
    eventos: list[dict[str, Any]] = []
    mudou = False
    for idx, r in alertas.iterrows():
        estado = str(r.get("estado") or "")
        if estado in {
            "CONFIRMADO",
            "ENCERRADO",
            "CANCELADO",
            "ESCALONADO_MAXIMO",
            "AGUARDANDO_SUPERVISAO",
        }:
            continue
        if estado not in {"AGUARDANDO_CONFIRMACAO", "ESCALONADO", "ENVIADO"}:
            continue
        limite = _parse_dt(r.get("prazo_limite"))
        if limite is None:
            continue
        if limite.tzinfo is None:
            limite = limite.replace(tzinfo=agora.tzinfo)
        if agora < limite:
            continue
        n_esc = int(float(str(r.get("n_escalonamentos") or 0) or 0))
        estado_ant = estado
        if estado in {"AGUARDANDO_CONFIRMACAO", "ENVIADO"}:
            estado_novo = "ESCALONADO"
            n_esc = max(1, n_esc + 1)
            motivo = "Prazo de confirmação esgotado — 1º escalonamento (substituto/regional)."
            prazo = int(float(str(r.get("prazo_min") or 0) or 0))
            if prazo > 0:
                alertas.at[idx, "prazo_limite"] = _iso(agora + dt.timedelta(minutes=prazo))
        else:
            estado_novo = "ESCALONADO_MAXIMO"
            n_esc = max(2, n_esc + 1)
            motivo = "2º prazo esgotado — falha institucional / gabinete SES-MT."
        alertas.at[idx, "estado"] = estado_novo
        alertas.at[idx, "n_escalonamentos"] = str(n_esc)
        eventos.append(
            {
                "instante": _iso(agora),
                "id_alerta": str(r.get("id_alerta") or ""),
                "id_snisb": str(r.get("id_snisb") or ""),
                "nivel": str(r.get("nivel") or ""),
                "n_escalonamento": str(n_esc),
                "motivo": motivo,
                "estado_anterior": estado_ant,
                "estado_novo": estado_novo,
            }
        )
        mudou = True
    if mudou:
        _reescrever(ALERTAS, alertas, CAMPOS_ALERTA)
    if eventos:
        _gravar(ESCALONAMENTOS, eventos, CAMPOS_ESC)
    return eventos


def payload_defesa_civil(alerta: dict[str, Any] | pd.Series) -> dict[str, Any]:
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
        "texto_completo_ref": f"alertas/piloto/{alerta.get('arquivo_txt') or ''}",
        "contato_ses": "CIEVS-MT",
        "canais_sugeridos": ["telefone", "email", "telegram"],
        "ressalva": "Este alerta não constitui ordem de evacuação.",
        "estado": str(alerta.get("estado") or ""),
        "prazo_limite": str(alerta.get("prazo_limite") or ""),
        "supervisor": str(alerta.get("supervisor") or ""),
    }


def resumo_ciclo() -> dict[str, Any]:
    al = carregar_alertas()
    conf = carregar_confirmacoes()
    esc = carregar_escalonamentos()
    if al.empty:
        return {
            "n_emitidos": 0,
            "n_aguardando": 0,
            "n_aguardando_supervisao": 0,
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
        "n_aguardando_supervisao": int((est == "AGUARDANDO_SUPERVISAO").sum()),
        "n_confirmados": int((est == "CONFIRMADO").sum()),
        "n_escalonados": int((est == "ESCALONADO").sum()),
        "n_escalonado_maximo": int((est == "ESCALONADO_MAXIMO").sum()),
        "n_confirmacoes": len(conf),
        "n_eventos_esc": len(esc),
        "sem_confirmacao": al[
            est.isin(
                [
                    "AGUARDANDO_CONFIRMACAO",
                    "AGUARDANDO_SUPERVISAO",
                    "ESCALONADO",
                    "ESCALONADO_MAXIMO",
                ]
            )
        ],
    }


def alertas_sem_confirmacao_ids() -> list[str]:
    al = carregar_alertas()
    if al.empty:
        return []
    est = al["estado"].fillna("").astype(str)
    sub = al[
        est.isin(
            [
                "AGUARDANDO_CONFIRMACAO",
                "AGUARDANDO_SUPERVISAO",
                "ESCALONADO",
                "ESCALONADO_MAXIMO",
            ]
        )
    ]
    return sub["id_alerta"].astype(str).tolist()
