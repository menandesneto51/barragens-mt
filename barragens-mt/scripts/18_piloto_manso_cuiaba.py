"""Piloto operacional — eixo Manso–Cuiabá.

Percorre o ciclo dado → índice → alerta → ficha (esqueleto) para as barragens
que podem afetar Cuiabá / Várzea Grande, com hidro SisClima/TITAN já ligada ao IDAP.

Pré-requisitos: etapas 16 e 17.

Saídas:
  dados/tratados/piloto_manso_cuiaba.csv
  alertas/piloto/*.txt          — texto de alerta (docs/04)
  relatorios/piloto_manso_cuiaba.md
  painel/piloto_manso_cuiaba.html
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import comum
from idap.calculo import calcular_idap
from idap.impacto_sanitario import (
    area_equivalente_km2,
    estimar_populacao,
    perfil_de,
)
from idap.modelo import ExposicaoSanitaria
from idap.regras import aplicar_regras
from idap.relatorio import montar_alerta, montar_resumo

FUSO = ZoneInfo("America/Cuiaba")
MUNICIPIOS_ALVO = frozenset({"Cuiabá", "Várzea Grande"})
REGIAO_SAUDE_PILOTO = "Baixada Cuiabana"
# Cenário de referência nos alertas do piloto (mesmo default da aba simulação).
FRACAO_REF = 0.50
PROFUNDIDADE_REF_M = 2.0


def _num(valor: Any) -> float | None:
    if valor in (None, "", "None"):
        return None
    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return None


def enriquecer_exposicao(
    base: ExposicaoSanitaria,
    registro: dict[str, Any],
    afetados: list[str],
) -> ExposicaoSanitaria:
    """Injeta área/população proxy e material no estado usado pelo alerta."""
    vol = _num(registro.get("capacidade_hm3"))
    area = area_equivalente_km2(vol, FRACAO_REF, PROFUNDIDADE_REF_M) if vol else 0.0
    est = estimar_populacao(
        area_km2=area,
        municipio_sede=(registro.get("municipio") or "").strip(),
        municipios_afetados=afetados,
        pop_sigbm_afetadas=_num(registro.get("sigbm_pessoas_afetadas")),
        pop_sigbm_jusante=_num(registro.get("sigbm_populacao_jusante")),
        fracao_volume=FRACAO_REF,
    )
    detalhe = (
        f"{est['detalhe']} Cenário de referência do alerta: "
        f"{FRACAO_REF:.0%} do volume / lâmina {PROFUNDIDADE_REF_M:.0f} m."
    )
    return replace(
        base,
        populacao_zas=est["populacao_estimada"],
        area_estimada_km2=est.get("area_km2"),
        metodo_estimativa_populacao=est["metodo"],
        detalhe_estimativa_populacao=detalhe,
        proporcao_vulneravel=0.15,  # proxy até haver setor censitário na mancha
    )


def _carregar_16():
    caminho = Path(__file__).resolve().parent / "16_idap_estadual.py"
    spec = importlib.util.spec_from_file_location("idap_estadual_mt", caminho)
    if spec is None or spec.loader is None:
        raise SystemExit("não foi possível carregar 16_idap_estadual.py")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["idap_estadual_mt"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def ler_csv(caminho: Path) -> list[dict[str, Any]]:
    if not caminho.exists():
        raise SystemExit(f"base ausente: {caminho.name}. Rode as etapas 16 e 17.")
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def ler_interesse() -> dict[str, Any]:
    caminho = comum.DADOS_TRATADOS / "cuiaba_municipios_de_interesse.json"
    if not caminho.exists():
        return {}
    return json.loads(caminho.read_text(encoding="utf-8"))


def no_piloto(linha_idap: dict[str, Any]) -> bool:
    afetados = {
        p.strip()
        for p in (linha_idap.get("municipios_potencialmente_afetados") or "").split("|")
        if p.strip()
    }
    if afetados & MUNICIPIOS_ALVO:
        return True
    nome = (linha_idap.get("nome") or "").upper()
    return nome.startswith("UHE MANSO")


def main() -> None:
    comum.preparar_diretorios()
    idap16 = _carregar_16()
    instante = datetime.now(tz=FUSO)

    inventario = {r["id_snisb"]: r for r in idap16.ler_inventario()}
    hidro_por_id = idap16.ler_hidro_por_barragem()
    cnes_por_mun = idap16.ler_cnes_por_municipio()
    alertab_por_id = idap16.ler_alertabilidade()
    linhas_idap = ler_csv(comum.DADOS_TRATADOS / "idap_estadual_mt.csv")
    interesse = ler_interesse()

    piloto_ids = [r["id_snisb"] for r in linhas_idap if no_piloto(r)]
    idap_por_id = {r["id_snisb"]: r for r in linhas_idap if r["id_snisb"] in set(piloto_ids)}

    print(f"Piloto Manso–Cuiabá — {len(piloto_ids)} barragens")
    print(f"  hidro disponível: {sum(1 for i in piloto_ids if i in hidro_por_id)}")
    print(f"  alertabilidade: {sum(1 for i in piloto_ids if i in alertab_por_id)}")

    dir_alertas = comum.RAIZ / "alertas" / "piloto"
    dir_alertas.mkdir(parents=True, exist_ok=True)
    for antigo in dir_alertas.glob("*.txt"):
        antigo.unlink()

    linhas_piloto: list[dict[str, Any]] = []
    textos_alerta: list[tuple[str, str]] = []
    por_nivel: Counter[str] = Counter()

    for id_snisb in sorted(piloto_ids, key=lambda i: (-int(idap_por_id[i]["idap"]), i)):
        registro = inventario.get(id_snisb)
        if registro is None:
            continue
        base = idap_por_id[id_snisb]
        afetados_txt = base.get("municipios_potencialmente_afetados") or ""
        afetados = [p.strip() for p in afetados_txt.split("|") if p.strip()]
        alert = alertab_por_id.get(id_snisb, {})
        contatos_ok = (
            (alert.get("contatos_validados_90d") or "").lower() == "sim"
            if alert
            else None
        )
        hidro = hidro_por_id.get(id_snisb)
        exposicao = enriquecer_exposicao(
            idap16.exposicao_proxy(
                idap16.contaminante(registro), afetados, cnes_por_mun
            ),
            registro,
            afetados,
        )
        perfil = perfil_de(
            registro.get("uso_principal"),
            registro.get("orgao_fiscalizador"),
            exposicao.contaminante_predominante,
        )
        estado = replace(
            idap16.estado_de_registro(
                registro,
                instante,
                hidro,
                exposicao=exposicao,
                contatos_validados_90d=contatos_ok,
                municipios_zas=tuple(afetados),
            ),
            regiao_saude=REGIAO_SAUDE_PILOTO,
        )
        resultado = calcular_idap(estado)
        final = aplicar_regras(estado, resultado)
        texto_alerta = montar_alerta(estado, final)
        resumo = montar_resumo(final)
        por_nivel[final.nivel_final.rotulo] += 1

        nome_arquivo = f"{final.nivel_final.rotulo.lower()}_{id_snisb}.txt"
        (dir_alertas / nome_arquivo).write_text(texto_alerta + "\n", encoding="utf-8")
        textos_alerta.append((nome_arquivo, resumo))

        linhas_piloto.append(
            {
                "id_snisb": id_snisb,
                "nome": estado.nome,
                "municipio_sede": estado.municipio,
                "regiao_saude": REGIAO_SAUDE_PILOTO,
                "perfil_sanitario": perfil.codigo,
                "idap": resultado.idap,
                "nivel": final.nivel_final.rotulo,
                "completude": f"{resultado.completude:.3f}".replace(".", ","),
                "confiabilidade": resultado.confiabilidade,
                "pontos_a": resultado.dimensao("A").pontos,
                "pontos_b": resultado.dimensao("B").pontos,
                "pontos_c": resultado.dimensao("C").pontos,
                "pontos_d": resultado.dimensao("D").pontos,
                "alertavel": alert.get("alertavel") or "não",
                "area_estimada_km2": (
                    f"{exposicao.area_estimada_km2}".replace(".", ",")
                    if exposicao.area_estimada_km2 is not None
                    else ""
                ),
                "populacao_estimada": exposicao.populacao_zas or "",
                "metodo_populacao": exposicao.metodo_estimativa_populacao or "",
                "chuva_24h_mm": (hidro or {}).get("chuva_24h_mm", ""),
                "chuva_72h_mm": (hidro or {}).get("chuva_72h_mm", ""),
                "saturacao_antecedente": (hidro or {}).get("saturacao_antecedente", ""),
                "nivel_alerta_hidro": (hidro or {}).get("nivel_alerta_hidro", ""),
                "aproximacao_espacial": (hidro or {}).get("aproximacao_espacial", ""),
                "municipios_potencialmente_afetados": afetados_txt,
                "arquivo_alerta": f"alertas/piloto/{nome_arquivo}",
                "resumo": resumo,
                "instante": instante.isoformat(timespec="seconds"),
            }
        )

    comum.salvar_csv(
        comum.DADOS_TRATADOS / "piloto_manso_cuiaba.csv",
        linhas_piloto,
        list(linhas_piloto[0].keys()) if linhas_piloto else [],
    )
    escrever_sitrep(linhas_piloto, por_nivel, interesse, instante)
    escrever_painel(linhas_piloto, por_nivel, instante)
    print(f"  gravado dados/tratados/piloto_manso_cuiaba.csv ({len(linhas_piloto)})")
    print(f"  alertas em alertas/piloto/ ({len(textos_alerta)} arquivos)")
    for nivel in ("Roxo", "Vermelho", "Laranja", "Amarelo", "Verde"):
        print(f"  {nivel}: {por_nivel.get(nivel, 0)}")


def escrever_sitrep(
    linhas: list[dict[str, Any]],
    por_nivel: Counter[str],
    interesse: dict[str, Any],
    instante: datetime,
) -> None:
    top = sorted(linhas, key=lambda r: (-int(r["idap"]), r["nome"]))[:20]
    manso = [r for r in linhas if r["nome"].upper().startswith("UHE MANSO")]
    por_sede: dict[str, int] = defaultdict(int)
    for r in linhas:
        por_sede[r["municipio_sede"]] += 1

    partes = [
        "# Piloto operacional — eixo Manso–Cuiabá",
        "",
        f"Ciclo: **dado (SisClima/TITAN) → IDAP → alerta → ficha (esqueleto)**.",
        f"Emissão: {instante.strftime('%d/%m/%Y %H:%M')} (horário de Cuiabá).",
        f"Seção de controle: `{interesse.get('secao_de_controle', '896573')}`.",
        f"Região de saúde do piloto: **{REGIAO_SAUDE_PILOTO}**.",
        "",
        "## Recorte",
        "",
        f"- Barragens no piloto: **{len(linhas)}** "
        "(afetam Cuiabá e/ou Várzea Grande, ou fazem parte do complexo UHE Manso).",
        f"- Textos do complexo Manso: **{len(manso)}**.",
        "",
        "| Nível | Barragens |",
        "| --- | ---: |",
    ]
    for nivel in ("Roxo", "Vermelho", "Laranja", "Amarelo", "Verde"):
        partes.append(f"| {nivel} | {por_nivel.get(nivel, 0)} |")

    partes += [
        "",
        "## Complexo UHE Manso",
        "",
        "| IDAP | Nível | A | Nome | Municípios afetados |",
        "| ---: | --- | ---: | --- | --- |",
    ]
    for r in sorted(manso, key=lambda x: (-int(x["idap"]), x["nome"])):
        partes.append(
            f"| {r['idap']} | {r['nivel']} | {r['pontos_a']} | {r['nome']} | "
            f"{r['municipios_potencialmente_afetados']} |"
        )

    partes += [
        "",
        "## Maiores IDAP do piloto (top 20)",
        "",
        "| IDAP | Nível | Completude | Sede | Nome | Arquivo alerta |",
        "| ---: | --- | ---: | --- | --- | --- |",
    ]
    for r in top:
        partes.append(
            f"| {r['idap']} | {r['nivel']} | {r['completude']} | {r['municipio_sede']} | "
            f"{r['nome']} | `{r['arquivo_alerta']}` |"
        )

    partes += [
        "",
        "## Ficha rápida (esqueleto operacional)",
        "",
        "Campos mínimos a preencher no simulado (docs/05 §5.4) — ainda sem formulário web:",
        "",
        "1. Identificação do evento / barragem / municípios atingidos",
        "2. Horário de início da resposta e responsável municipal",
        "3. Unidades de saúde afetadas ou isoladas (CNES)",
        "4. Óbitos, feridos, desalojados, desaparecidos (contagens)",
        "5. Interrupção de água / energia / acesso",
        "6. Necessidades imediatas (transporte, abrigo, água potável, insumos)",
        "",
        "Formulário de simulado: [`painel/ficha_rapida.html`](../painel/ficha_rapida.html).",
        "Os textos em `alertas/piloto/` já trazem as ações recomendadas por nível e a",
        "ressalva obrigatória de não-evacuação.",
        "",
        "## Limitações deste ciclo",
        "",
        "- C1/C2/C4–C7 ainda sem mancha oficial; C3 usa CNES municipal do eixo (proxy).",
        "- Hidro: máximo entre sede + municípios a montante (Otto); não é agregação areal BHO.",
        "- Contatos: esqueleto em `contatos_institucionais_piloto.csv` — quase todas "
        "não alertáveis até validação telefônica.",
        "- Proxy Otto ainda inclui falsos positivos em alguns códigos grosseiros.",
        "",
    ]
    destino = comum.RELATORIOS / "piloto_manso_cuiaba.md"
    destino.write_text("\n".join(partes), encoding="utf-8")
    print(f"  gravado {destino.relative_to(comum.RAIZ)}")


def escrever_painel(
    linhas: list[dict[str, Any]],
    por_nivel: Counter[str],
    instante: datetime,
) -> None:
    """Painel leve do piloto — leitura do CSV embutido como JSON."""
    payload = json.dumps(linhas, ensure_ascii=False)
    niveis = {n: por_nivel.get(n, 0) for n in ("Roxo", "Vermelho", "Laranja", "Amarelo", "Verde")}
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Piloto Manso–Cuiabá — VIGIBARRAGENS–MT</title>
<style>
  :root {{
    --ink:#1a2332; --muted:#5c6b7a; --paper:#eef2f5; --card:#fff;
    --line:#d5dde5; --accent:#0b6e4f;
    --roxo:#5b2c6f; --verm:#c0392b; --lar:#d35400; --ama:#b7950b; --verd:#1e8449;
  }}
  * {{ box-sizing: border-box }}
  body {{
    margin:0; font-family: "Source Sans 3", "Segoe UI", sans-serif;
    background:
      radial-gradient(ellipse at 10% 0%, #d9e8df 0%, transparent 45%),
      radial-gradient(ellipse at 90% 10%, #d6e0ea 0%, transparent 40%),
      var(--paper);
    color: var(--ink); font-size: 14px;
  }}
  header {{
    padding: 28px 28px 18px; border-bottom: 1px solid var(--line);
    background: linear-gradient(180deg, rgba(255,255,255,.85), rgba(255,255,255,.55));
  }}
  header .marca {{
    font-family: "Fraunces", Georgia, serif; font-size: 28px; font-weight: 600;
    letter-spacing: -.02em; margin: 0 0 6px;
  }}
  header p {{ margin: 0; color: var(--muted); max-width: 52rem; line-height: 1.45 }}
  main {{ padding: 20px 28px 48px; max-width: 1200px }}
  .kpis {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(120px,1fr)); gap: 10px; margin-bottom: 18px }}
  .kpi {{ background: var(--card); border: 1px solid var(--line); padding: 12px 14px }}
  .kpi .n {{ font-size: 24px; font-weight: 700; font-variant-numeric: tabular-nums }}
  .kpi .r {{ font-size: 11px; color: var(--muted); margin-top: 2px; text-transform: uppercase; letter-spacing: .04em }}
  table {{ width: 100%; border-collapse: collapse; background: var(--card); border: 1px solid var(--line) }}
  th, td {{ padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--line); font-size: 13px }}
  th {{ font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); background: #f7f9fb }}
  tr:hover td {{ background: #f4f8f6 }}
  .etq {{ display: inline-block; padding: 2px 8px; color: #fff; font-size: 11px; font-weight: 600 }}
  .Roxo {{ background: var(--roxo) }} .Vermelho {{ background: var(--verm) }}
  .Laranja {{ background: var(--lar) }} .Amarelo {{ background: var(--ama) }}
  .Verde {{ background: var(--verd) }}
  .nota {{ margin-top: 16px; color: var(--muted); font-size: 12.5px; line-height: 1.55; max-width: 48rem }}
  a {{ color: var(--accent) }}
</style>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet">
</head>
<body>
<header>
  <h1 class="marca">VIGIBARRAGENS–MT</h1>
  <p>Piloto operacional — eixo Manso–Cuiabá · {instante.strftime('%d/%m/%Y %H:%M')} (Cuiabá) ·
  {len(linhas)} barragens ·
  <a href="index.html">Comando estadual</a> ·
  <a href="simulacao.html">Simulação volume/área</a> ·
  <a href="ficha_rapida.html">Ficha rápida</a> ·
  <a href="confirmacao_alerta.html">Confirmação</a></p>
</header>
<main>
  <div class="kpis" id="kpis"></div>
  <table>
    <thead>
      <tr>
        <th>Nível</th><th>IDAP</th><th>A</th><th>Barragem</th><th>Sede</th>
        <th>Completude</th><th>Alerta</th>
      </tr>
    </thead>
    <tbody id="corpo"></tbody>
  </table>
  <p class="nota">
    Hidro SisClima/TITAN (sede + montante). C3 via CNES do eixo (proxy).
    Alertas em <code>alertas/piloto/</code> ·
    <a href="ficha_rapida.html">Ficha rápida (simulado)</a> ·
    <a href="../relatorios/piloto_manso_cuiaba.md">SITREP</a> ·
    <a href="../relatorios/contatos_alertabilidade.md">Contatos / alertabilidade</a>.
  </p>
</main>
<script>
const DADOS = {payload};
const NIVEIS = {json.dumps(niveis, ensure_ascii=False)};
const kpis = document.getElementById('kpis');
[['Total', DADOS.length], ...Object.entries(NIVEIS)].forEach(([r,n]) => {{
  const d = document.createElement('div');
  d.className = 'kpi';
  d.innerHTML = `<div class="n">${{n}}</div><div class="r">${{r}}</div>`;
  kpis.appendChild(d);
}});
const corpo = document.getElementById('corpo');
DADOS.slice().sort((a,b) => Number(b.idap) - Number(a.idap)).forEach(r => {{
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td><span class="etq ${{r.nivel}}">${{r.nivel}}</span></td>
    <td>${{r.idap}}</td>
    <td>${{r.pontos_a}}</td>
    <td>${{r.nome}}</td>
    <td>${{r.municipio_sede}}</td>
    <td>${{r.completude}}</td>
    <td><a href="../${{r.arquivo_alerta}}">abrir</a></td>`;
  corpo.appendChild(tr);
}});
</script>
</body>
</html>
"""
    destino = comum.RAIZ / "painel" / "piloto_manso_cuiaba.html"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(html, encoding="utf-8")
    print(f"  gravado {destino.relative_to(comum.RAIZ)}")


if __name__ == "__main__":
    main()
