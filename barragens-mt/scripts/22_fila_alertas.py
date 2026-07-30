"""Fila de alertas do piloto — Tela 4 leve (docs/07 §7.4).

Lista barragens do piloto com nível ≥ Amarelo (e top Verde do complexo Manso),
com link ao texto do alerta e cruzamento local de confirmações (localStorage).
"""

from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path
from typing import Any

import comum

SAIDA = comum.RAIZ / "painel"
ORDEM = {"Roxo": 0, "Vermelho": 1, "Laranja": 2, "Amarelo": 3, "Verde": 4}


def ler_piloto() -> list[dict[str, Any]]:
    caminho = comum.DADOS_TRATADOS / "piloto_manso_cuiaba.csv"
    if not caminho.exists():
        raise SystemExit("piloto_manso_cuiaba.csv ausente — rode a etapa 18")
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


MODELO = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fila de alertas — VIGIBARRAGENS–MT</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root{--ink:#15202b;--muted:#5a6b7a;--paper:#e9eef2;--card:#fff;--line:#d0d8e0;--accent:#0b6e4f;
--roxo:#5b2c6f;--verm:#c0392b;--lar:#d35400;--ama:#b7950b;--verd:#1e8449}
*{box-sizing:border-box}
body{margin:0;font-family:"Source Sans 3",system-ui,sans-serif;color:var(--ink);
background:radial-gradient(ellipse at 10% 0%,#d9e8df,transparent 40%),var(--paper)}
header{padding:20px 24px;border-bottom:1px solid var(--line);background:rgba(255,255,255,.85);
display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px;align-items:flex-end}
.marca{font-family:"Fraunces",Georgia,serif;font-size:1.7rem;margin:0 0 4px;font-weight:600}
header p{margin:0;color:var(--muted);font-size:14px;max-width:36rem;line-height:1.4}
nav a{color:var(--accent);font-weight:600;font-size:13px;margin-left:10px;text-decoration:none}
main{padding:16px 24px 40px;max-width:1100px;margin:0 auto}
.etq{display:inline-block;padding:2px 8px;color:#fff;font-size:11px;font-weight:600}
.Roxo{background:var(--roxo)}.Vermelho{background:var(--verm)}.Laranja{background:var(--lar)}
.Amarelo{background:var(--ama)}.Verde{background:var(--verd)}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);font-size:13px}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left}
th{font-size:11px;text-transform:uppercase;color:var(--muted);background:#f7f9fb}
.conf-ok{color:var(--verd);font-weight:600}.conf-pend{color:var(--lar);font-weight:600}
.nota{margin-top:14px;font-size:12.5px;color:var(--muted);line-height:1.5}
</style>
</head>
<body>
<header>
  <div>
    <h1 class="marca">Fila de alertas</h1>
    <p>Piloto Manso–Cuiabá · textos em <code>alertas/piloto/</code> · gerado __GERADO__</p>
  </div>
  <nav>
    <a href="index.html">Comando</a>
    <a href="confirmacao_alerta.html">Registrar confirmação</a>
    <a href="piloto_manso_cuiaba.html">Piloto</a>
  </nav>
</header>
<main>
  <table>
    <thead><tr>
      <th>Nível</th><th>IDAP</th><th>Barragem</th><th>Sede</th><th>Alertável</th>
      <th>Confirmações</th><th>Texto</th>
    </tr></thead>
    <tbody id="corpo"></tbody>
  </table>
  <p class="nota">
    Confirmações vêm do localStorage deste navegador (tela de confirmação). Exportar o JSON e
    guardar em <code>dados/tratados/confirmacoes/</code> para arquivo institucional.
    Escalonamento automático (R09) ainda não está ligado a canais reais.
  </p>
</main>
<script>
const ALERTAS = __ALERTAS__;
const KEY = 'vigibarragens_confirmacoes_alerta';
function confirmacoes() {
  try { return JSON.parse(localStorage.getItem(KEY) || '[]'); } catch { return []; }
}
function contagens(idSnisb) {
  const pref = 'ALERTA-';
  const lista = confirmacoes().filter(c =>
    (c.id_alerta||'').includes(idSnisb) || (c.id_alerta||'').endsWith('-'+idSnisb)
  );
  return lista;
}
const corpo = document.getElementById('corpo');
ALERTAS.forEach(a => {
  const conf = contagens(a.id);
  const st = conf.length
    ? `<span class="conf-ok">${conf.length} conf.</span>`
    : (a.nv === 'Verde' ? '—' : '<span class="conf-pend">pendente</span>');
  const tr = document.createElement('tr');
  tr.innerHTML = `<td><span class="etq ${a.nv}">${a.nv}</span></td>
    <td>${a.idap}</td><td>${a.no}</td><td>${a.mu}</td><td>${a.al}</td>
    <td>${st}</td>
    <td>${a.arq ? `<a href="../${a.arq}">abrir</a>` : '—'}</td>`;
  corpo.appendChild(tr);
});
</script>
</body>
</html>
"""


def main() -> None:
    piloto = ler_piloto()
    # Prioriza não-Verde; inclui Manso mesmo em Verde.
    fila = [
        r
        for r in piloto
        if r.get("nivel") != "Verde" or (r.get("nome") or "").upper().startswith("UHE MANSO")
    ]
    fila.sort(key=lambda r: (ORDEM.get(r.get("nivel") or "Verde", 9), -int(r.get("idap") or 0)))

    alertas = [
        {
            "id": r.get("id_snisb"),
            "no": r.get("nome"),
            "mu": r.get("municipio_sede"),
            "nv": r.get("nivel"),
            "idap": int(r.get("idap") or 0),
            "al": r.get("alertavel") or "não",
            "arq": r.get("arquivo_alerta") or "",
        }
        for r in fila
    ]

    html = (
        MODELO.replace("__ALERTAS__", json.dumps(alertas, ensure_ascii=False, separators=(",", ":")))
        .replace("__GERADO__", dt.datetime.now().strftime("%d/%m/%Y %H:%M"))
    )
    SAIDA.mkdir(parents=True, exist_ok=True)
    destino = SAIDA / "alertas.html"
    destino.write_text(html, encoding="utf-8")
    (comum.DADOS_TRATADOS / "confirmacoes").mkdir(parents=True, exist_ok=True)
    print(f"Fila de alertas — {len(alertas)} itens")
    print(f"  gravado {destino.relative_to(comum.RAIZ)}")


if __name__ == "__main__":
    main()
