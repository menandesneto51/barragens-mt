"""Exercício de mesa ponta a ponta — piloto Manso–Cuiabá (A3/A4/A7).

Escolhe 1 barragem Amarelo do eixo → emite → força escalonamento (relógio)
→ confirma → gera SITREP + payload DC.

Saídas:
  dados/tratados/confirmacoes/ (alerta, confirmação, escalonamento, payload)
  relatorios/exercicio_mesa_piloto.md (roteiro manual)

Uso:
  python scripts/57_exercicio_mesa_piloto.py
  python executar.py 57
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from st_app.ciclo_alerta import (  # noqa: E402
    emitir_alerta,
    processar_escalonamentos,
    registrar_confirmacao,
    resumo_ciclo,
)
from st_app.sitrep import montar_sitrep_md  # noqa: E402

PILOTO = ROOT / "dados" / "tratados" / "piloto_manso_cuiaba.csv"
REL = ROOT / "relatorios" / "exercicio_mesa_piloto.md"
CONF = ROOT / "dados" / "tratados" / "confirmacoes"


def _escolher_amarelo() -> dict:
    if not PILOTO.is_file():
        raise SystemExit(f"base piloto ausente: {PILOTO}")
    df = pd.read_csv(PILOTO, sep=";", dtype=str, encoding="utf-8-sig")
    if "nivel" not in df.columns:
        raise SystemExit("piloto sem coluna nivel")
    am = df[df["nivel"].astype(str).str.strip() == "Amarelo"]
    if am.empty:
        raise SystemExit("nenhuma barragem Amarelo no piloto — rode etapas 16/18")
    r = am.iloc[0]
    return r.to_dict()


def main() -> int:
    CONF.mkdir(parents=True, exist_ok=True)
    row = _escolher_amarelo()
    t0 = dt.datetime(2026, 8, 30, 10, 0, 0, tzinfo=dt.timezone(dt.timedelta(hours=-4)))

    emitido = emitir_alerta(
        id_snisb=str(row.get("id_snisb") or ""),
        nome=str(row.get("nome") or ""),
        municipio_sede=str(row.get("municipio_sede") or ""),
        nivel="Amarelo",
        idap=row.get("idap"),
        municipios_afetados=str(row.get("municipios_potencialmente_afetados") or ""),
        lat=row.get("latitude") if "latitude" in row else None,
        lon=row.get("longitude") if "longitude" in row else None,
        fonte="exercicio_mesa_57",
        agora=t0,
        texto_resumo=(
            f"Exercício de mesa — prontidão Amarelo {row.get('nome')} "
            f"({row.get('municipio_sede')}). Não é ordem de evacuação."
        ),
    )
    print(f"emitido {emitido['id_alerta']} estado={emitido['estado']} txt={emitido.get('arquivo_txt')}")

    # Força 1º escalonamento (prazo Amarelo = 120 min)
    ev1 = processar_escalonamentos(agora=t0 + dt.timedelta(minutes=121))
    print(f"escalonamentos: {len(ev1)}")
    if ev1:
        print(f"  → {ev1[0]['estado_novo']}")

    conf = registrar_confirmacao(
        id_alerta=emitido["id_alerta"],
        responsavel="Plantão CIEVS (exercício de mesa)",
        canal="telefone",
        observacao="Confirmação do roteiro 57 — exercício",
        agora=t0 + dt.timedelta(minutes=130),
    )
    print(f"confirmado por {conf['responsavel']}")

    # SITREP plantão (se base IDAP disponível)
    sitrep_txt = ""
    try:
        from st_app.data import carregar_idap

        df = carregar_idap()
        if not df.empty:
            sitrep_txt = montar_sitrep_md(df, municipio=None)
    except Exception as exc:  # noqa: BLE001
        sitrep_txt = f"(SITREP indisponível neste ambiente: {exc})"

    payload_path = CONF / "payloads_defesa_civil" / f"{emitido['id_alerta']}.json"
    payload_ok = payload_path.is_file()
    cic = resumo_ciclo()

    artefato_sitrep = CONF / f"sitrep_exercicio_{emitido['id_alerta']}.md"
    if sitrep_txt:
        artefato_sitrep.write_text(sitrep_txt, encoding="utf-8")

    REL.parent.mkdir(parents=True, exist_ok=True)
    REL.write_text(
        "\n".join(
            [
                "# Exercício de mesa — piloto Manso–Cuiabá",
                "",
                "Roteiro operacional para CIEVS repetir o ciclo em 30–45 min.",
                "",
                "## Automatizado (script 57)",
                "",
                f"- Barragem: **{emitido.get('nome')}** (`{emitido.get('id_snisb')}`) — Amarelo",
                f"- `id_alerta`: `{emitido['id_alerta']}`",
                f"- Texto: `alertas/piloto/{emitido.get('arquivo_txt')}`",
                f"- Payload DC: `{'ok' if payload_ok else 'ausente'}` → "
                f"`dados/tratados/confirmacoes/payloads_defesa_civil/{emitido['id_alerta']}.json`",
                f"- Escalonamento forçado: **{len(ev1)}** evento(s)",
                f"- Confirmação: **{conf['responsavel']}**",
                f"- Resumo ciclo: emitidos={cic['n_emitidos']} confirmados={cic['n_confirmados']}",
                "",
                "## Passos manuais (complemento)",
                "",
                "1. Abrir **Alertabilidade** no Streamlit — conferir o alerta na tabela do ciclo.",
                "2. Se emitir **Vermelho/Roxo**, preencher **Autorizar envio** (supervisor) antes do dry-run.",
                "3. Em **Contatos**, filtrar cobrança **Só CIEVS** e anotar municípios sem telefone/e-mail.",
                "4. Abrir a **ficha rápida** da barragem e o dossiê municipal (jusante).",
                "5. Rodar dry-run: botão *Emitir + dry-run despacho* ou "
                "`python scripts/29_despacho_alertas.py --id-alerta <id>`.",
                "6. Registrar confirmação na tela **Confirmação** (ou reexecutar este script).",
                "7. Baixar SITREP do plantão (Comando) e o payload DC do alerta.",
                "",
                "## Aceite",
                "",
                "- Script retorna código 0.",
                "- Artefatos em `dados/tratados/confirmacoes/`.",
                "- Este markdown atualizado em `relatorios/exercicio_mesa_piloto.md`.",
                "",
                f"Gerado por `scripts/57_exercicio_mesa_piloto.py` em "
                f"{dt.datetime.now().isoformat(timespec='seconds')}.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"roteiro: {REL.relative_to(ROOT)}")
    if payload_ok:
        meta = json.loads(payload_path.read_text(encoding="utf-8"))
        print(f"payload tipo={meta.get('tipo')} nivel={meta.get('nivel')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
