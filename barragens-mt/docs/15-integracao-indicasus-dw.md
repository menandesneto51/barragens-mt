# 15. Integração IndicaSUS e DW de saúde (SES-MT)

> Etapa `43_indicasus_leitos_dw.py`. Consome leitos e ocupação já disponíveis no
> IndicaSUS / DW institucional — **não** recolhe planilha manual nem inventa ocupação.

## 15.1 Por que

| Necessidade | Fonte |
| --- | --- |
| Capacidade cadastrada (estabelecimento, tipologia) | CNES aberto (já no projeto) |
| Leitos operacionais e ocupação | **IndicaSUS** (e/ou extrato DW) |
| Razão leitos / demanda (IDAP D6) | IndicaSUS + pop. exposta (2% — §3.6.7) |
| Outros bancos do DW (SIH, SIA, SISREG, SINAN…) | Catálogo extensível |

A API pública de estabelecimentos CNES **não expõe leitos**. O proxy tipológico
(hospital/UPA/UBS) permanece como fallback estrutural.

## 15.2 Variáveis de ambiente / secrets

| Variável | Uso |
| --- | --- |
| `VIGIBARRAGENS_INDICASUS_CSV` | Caminho absoluto do dump CSV de leitos |
| `VIGIBARRAGENS_DW_CSV_DIR` | Pasta com dumps (`indicasus_leitos.csv`, …) |
| `VIGIBARRAGENS_DW_SQLITE` | SQLite espelho do extrato |
| `VIGIBARRAGENS_DW_URL` | URL SQLAlchemy (Postgres, SQL Server via pyodbc, etc.) |
| `VIGIBARRAGENS_INDICASUS_SCHEMA` | Schema SQL (default `dbo`) |
| `VIGIBARRAGENS_INDICASUS_TABELA` | Tabela/view (default `indicasus_leitos`) |

Ordem de resolução: **CSV → SQLite → DW_URL**.

Credenciais **não** vão para o git. Use `despacho_secrets.env` / Streamlit secrets
(seção `[vigi]` ou env do host).

## 15.3 Contrato canônico do extrato

Colunas normalizadas em `dados/tratados/indicasus_leitos_mt.csv`:

`codigo_cnes`, `nome_estabelecimento`, `codigo_municipio_ibge`, `municipio`,
`tipo_leito`, `leitos_cadastrados`, `leitos_operacionais`, `leitos_ocupados`,
`leitos_disponiveis`, `taxa_ocupacao`, `atualizado_em`, `fonte`, `banco_dw`.

Aliases de colunas de origem estão em `dados/config/dw_catalogo.json`
(`extratos.indicasus_leitos.aliases`). Ajuste ali se o nome no DW for diferente.

Exemplo de dump (somente formato): `dados/config/exemplos/indicasus_leitos.exemplo.csv`.
Para testar:

```bash
mkdir -p dados/brutos
cp dados/config/exemplos/indicasus_leitos.exemplo.csv dados/brutos/indicasus_leitos.csv
python executar.py 43
```

## 15.4 Outros bancos do DW

O mesmo conector (`scripts/dw_saude.py`) lê o catálogo. Entradas reservadas:

| Extrato | Status |
| --- | --- |
| `indicasus_leitos` | **implementado** (etapa 43) |
| `sih_internacoes` | reservado |
| `sia_ambulatorial` | reservado |
| `sisreg_leitos` | reservado |
| `sinan_notificacoes` | reservado |

Para plugar um novo banco: (1) preencher aliases/sql no catálogo; (2) copiar o
padrão da etapa 43 num `44_…py` (ou generalizar); (3) gravar em `dados/tratados/`.

## 15.5 Onde entra no produto

| Destino | Uso |
| --- | --- |
| Simulação | Métricas de leitos/ocupação na mancha + razão D6 |
| `st_app/capacidade_cnes.py` | Join por `codigo_cnes` com pontos CNES |
| `16_idap_estadual.py` | Preenche `CapacidadeResposta.razao_leitos_demanda` quando houver agregados municipais |

## 15.6 Pendências institucionais

- Confirmar nome real da view/tabela IndicaSUS no DW e liberar leitura ao serviço.
- Definir cadência (horária em evento / diária em rotina) com a TI SES-MT.
- SIH/SIA/SINAN: mesma esteira quando os extratos forem liberados no DW.
