"""Extrai as barragens de mineracao (SIGBM/ANM) e recorta as de Mato Grosso.

O SNISB ja consolida as barragens de mineracao, mas o SIGBM traz atributos que nao
existem la e que sao decisivos para monitoramento: metodo construtivo (alteamento a
montante, a jusante ou por linha de centro), nivel de emergencia declarado, volume de
rejeito, existencia de comunidade na Zona de Autossalvamento e a ultima Declaracao de
Condicao de Estabilidade.

Fonte: portal de dados abertos da ANM, que republica o SIGBM diariamente em
https://dadosabertos.anm.gov.br/SIGBM/Barragens.csv
"""

from __future__ import annotations

import csv
import io
import re
import unicodedata
from pathlib import Path
from typing import Any

import comum

BASE = "https://dadosabertos.anm.gov.br/SIGBM"
ARQUIVO_BRUTO = comum.DADOS_BRUTOS / "sigbm_barragens_nacional.csv"
ARQUIVO_METADADOS = comum.DADOS_BRUTOS / "sigbm_metadados.ods"

CODIFICACOES = ("utf-8-sig", "utf-8", "cp1252", "latin-1")


def _sem_acento(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in normalizado if not unicodedata.combining(c)).lower().strip()


def baixar(nome_remoto: str, destino: Path) -> None:
    if destino.exists():
        print(f"Reaproveitando {destino.relative_to(comum.RAIZ)} (apague para rebaixar)")
        return
    print(f"Baixando {nome_remoto}")
    # A cadeia de certificados da ANM e incompleta em varios pontos de saida; o
    # conteudo e publico e nao ha credencial em transito.
    with comum.cliente(verificar_tls=False) as cli:
        resposta = cli.get(f"{BASE}/{nome_remoto}")
        resposta.raise_for_status()
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(resposta.content)
    print(f"  gravado {destino.relative_to(comum.RAIZ)} ({destino.stat().st_size / 1024:.0f} KB)")


def decodificar(bruto: bytes) -> str:
    for codificacao in CODIFICACOES:
        try:
            texto = bruto.decode(codificacao)
        except UnicodeDecodeError:
            continue
        # cp1252/latin-1 nunca falham, então checamos se o resultado tem sentido.
        if "\ufffd" not in texto:
            print(f"  codificacao detectada: {codificacao}")
            return texto
    return bruto.decode("latin-1", errors="replace")


def ler_csv(caminho: Path) -> tuple[list[str], list[dict[str, Any]]]:
    texto = decodificar(caminho.read_bytes())
    amostra = texto[:8192]
    try:
        dialeto = csv.Sniffer().sniff(amostra, delimiters=";,\t|")
        delimitador = dialeto.delimiter
    except csv.Error:
        delimitador = ";"
    print(f"  delimitador detectado: {delimitador!r}")

    leitor = csv.DictReader(io.StringIO(texto), delimiter=delimitador)
    cabecalho = [c.strip() for c in (leitor.fieldnames or [])]
    registros: list[dict[str, Any]] = []
    for linha in leitor:
        registros.append({(k or "").strip(): (v.strip() or None) if isinstance(v, str) else v
                          for k, v in linha.items()})
    return cabecalho, registros


def achar_coluna(cabecalho: list[str], *termos: str) -> str | None:
    for coluna in cabecalho:
        normalizada = _sem_acento(coluna)
        if all(termo in normalizada for termo in termos):
            return coluna
    return None


def para_float(valor: Any) -> float | None:
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().replace(" ", "")
    if not texto:
        return None
    # Planilha em pt-BR: ponto como separador de milhar, virgula como decimal.
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


NUMERO = re.compile(r"\d+(?:[.,]\d+)?")


def dms_para_decimal(valor: Any) -> float | None:
    """Converte coordenadas do SIGBM, gravadas como -10°07'16.390'', para grau decimal."""
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    if not any(marca in texto for marca in ("°", "º", "'", '"')):
        return para_float(texto)

    partes = [float(n.replace(",", ".")) for n in NUMERO.findall(texto)[:3]]
    if not partes:
        return None
    graus = partes[0]
    minutos = partes[1] if len(partes) > 1 else 0.0
    segundos = partes[2] if len(partes) > 2 else 0.0
    decimal = graus + minutos / 60 + segundos / 3600

    negativo = texto.startswith("-") or re.search(r"[SWO]\s*$", texto, re.IGNORECASE)
    return -decimal if negativo else decimal


def main() -> None:
    comum.preparar_diretorios()
    baixar("Barragens.csv", ARQUIVO_BRUTO)
    baixar("metadados-sigbm.ods", ARQUIVO_METADADOS)

    cabecalho, registros = ler_csv(ARQUIVO_BRUTO)
    print(f"  base nacional: {len(registros)} barragens, {len(cabecalho)} colunas")

    coluna_uf = achar_coluna(cabecalho, "uf") or achar_coluna(cabecalho, "estado")
    if coluna_uf is None:
        raise RuntimeError(f"coluna de UF nao encontrada. Colunas: {cabecalho}")
    coluna_lat = achar_coluna(cabecalho, "latitude")
    coluna_lon = achar_coluna(cabecalho, "longitude")

    de_mt = [r for r in registros if str(r.get(coluna_uf) or "").strip().upper() == comum.UF_SIGLA]
    print(f"  coluna de UF: {coluna_uf!r} -> {len(de_mt)} barragens em {comum.UF_SIGLA}")

    fora_do_bbox = 0
    for registro in de_mt:
        registro["latitude"] = dms_para_decimal(registro.get(coluna_lat)) if coluna_lat else None
        registro["longitude"] = dms_para_decimal(registro.get(coluna_lon)) if coluna_lon else None
        dentro = comum.dentro_do_bbox(registro["longitude"], registro["latitude"])
        registro["coordenada_plausivel"] = "sim" if dentro else "nao"
        if not dentro:
            fora_do_bbox += 1
    if fora_do_bbox:
        print(f"  atencao: {fora_do_bbox} registros com coordenada fora do envelope de MT")

    colunas = [*cabecalho, "latitude", "longitude", "coordenada_plausivel"]
    comum.salvar_csv(comum.DADOS_TRATADOS / "sigbm_barragens_mt.csv", de_mt, colunas)
    comum.salvar_geojson(comum.DADOS_TRATADOS / "sigbm_barragens_mt.geojson", de_mt)

    print("\nColunas disponiveis no SIGBM:")
    for coluna in cabecalho:
        print(f"  - {coluna}")


if __name__ == "__main__":
    main()
