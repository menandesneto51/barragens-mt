"""Perfis de impacto sanitário e estimativas de exposição (proxies).

Usado pela simulação (volume→área→população) e pelos textos de alerta.
Tudo aqui é estimativa rotulada — não substitui mancha oficial nem modelagem
epidemiológica formal (docs/05 VIGIPÓS-BARRAGENS).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# Densidade residencial aproximada (hab/km²) — fallback; etapa 26 sobrescreve com IBGE.
DENSIDADE_HAB_KM2: dict[str, float] = {
    "Cuiabá": 180.0,
    "Várzea Grande": 280.0,
    "Chapada dos Guimarães": 8.0,
    "Nossa Senhora do Livramento": 6.0,
    "Rosário Oeste": 5.0,
    "Nobres": 6.0,
    "Jangada": 5.0,
    "Acorizal": 8.0,
    "Santo Antônio de Leverger": 7.0,
    "Barão de Melgaço": 2.0,
    "Poconé": 3.0,
}
DENSIDADE_PADRAO = 15.0  # MT rural / cerrado — conservador para ordem de grandeza
_POP_IBGE_CACHE: dict[str, float] | None = None


def _carregar_densidades_ibge() -> dict[str, float]:
    global _POP_IBGE_CACHE
    if _POP_IBGE_CACHE is not None:
        return _POP_IBGE_CACHE
    out = dict(DENSIDADE_HAB_KM2)
    try:
        import csv

        import comum

        caminho = comum.DADOS_TRATADOS / "ibge_populacao_municipios_mt.csv"
        if caminho.exists():
            with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
                for r in csv.DictReader(arquivo, delimiter=";"):
                    mun = (r.get("municipio") or "").strip()
                    dens = r.get("densidade_hab_km2") or ""
                    pop = r.get("populacao") or ""
                    area = r.get("area_km2") or ""
                    if mun and dens:
                        try:
                            out[mun] = float(str(dens).replace(",", "."))
                            continue
                        except ValueError:
                            pass
                    if mun and pop and area:
                        try:
                            p = float(str(pop).replace(",", "."))
                            a = float(str(area).replace(",", "."))
                            if a > 0:
                                out[mun] = p / a
                        except ValueError:
                            pass
    except Exception:
        pass
    _POP_IBGE_CACHE = out
    return out


@dataclass(frozen=True)
class PerfilImpacto:
    codigo: str
    rotulo: str
    material: str
    efeitos_imediatos: tuple[str, ...]
    agravos_a_vigiar: tuple[str, ...]
    acoes_especificas: tuple[str, ...]
    laboratorio: tuple[str, ...]


PERFIL_AGUA = PerfilImpacto(
    codigo="agua",
    rotulo="Barragem de água / uso múltiplo",
    material="Água sem rejeito de mineração (cadastro)",
    efeitos_imediatos=(
        "Trauma, afogamento e politrauma na onda e no resgate",
        "Isolamento de localidades e interrupção de acesso a unidades de saúde",
        "Desabrigados / desalojados e sobrecarga de abrigos",
        "Interrupção de abastecimento de água e energia",
    ),
    agravos_a_vigiar=(
        "Doenças diarreicas agudas e surtos em abrigo",
        "Leptospirose (incubação típica 5–14 dias)",
        "Acidentes com animais peçonhentos deslocados pela água",
        "Infecções de pele e ferimentos contaminados",
        "Síndromes respiratórias em abrigo superlotado",
        "Sofrimento psíquico agudo e interrupção de medicamentos de uso contínuo",
        "Descompensação de gestantes de risco, dialíticos e oxigênio-dependentes",
    ),
    acoes_especificas=(
        "Ativar vigilância sindrômica (diarreia, febre, peçonhentos, pele) nos municípios a jusante",
        "Reforçar Vigiagua nas captações do eixo e distribuição de hipoclorito",
        "Organizar busca ativa de leptospirose a partir de D+5 do evento",
        "Mapear pacientes dependentes de tecnologia na área potencialmente isolada",
    ),
    laboratorio=(
        "Coprocultura / pesquisa de patógenos entéricos conforme protocolo local",
        "Sorologia / PCR para leptospirose conforme fluxo CIEVS",
        "Cloro residual, turbidez e coliformes nas redes afetadas",
    ),
)

PERFIL_REJEITO = PerfilImpacto(
    codigo="rejeito",
    rotulo="Barragem de rejeitos / mineração",
    material="Rejeito não inerte ou perigoso (cadastro / ANM)",
    efeitos_imediatos=(
        "Trauma e soterramento por lama de rejeito (alta densidade)",
        "Contaminação química imediata de solo, cursos d'água e captações",
        "Intoxicação aguda (metais, cianeto ou outros conforme minério) — hipótese a confirmar",
        "Isolamento prolongado e interdição de áreas por risco tóxico, além da inundação",
    ),
    agravos_a_vigiar=(
        "Intoxicação exógena e síndromes neurológicas / hepáticas / renais compatíveis com metais",
        "Dermatites de contato e lesões de pele por lama",
        "Doenças diarreicas e agravos de veiculação hídrica (água comprometida por longo prazo)",
        "Leptospirose e peçonhentos (como em inundação)",
        "Agravos respiratórios por poeira/particulado após secagem da lama",
        "Efeitos crônicos a médio prazo (exposição a metais) — linha de base e coorte",
        "Sofrimento psíquico e interrupção de cuidados contínuos",
    ),
    acoes_especificas=(
        "Acionar Vigiagua + vigilância em saúde ambiental com painel laboratorial ampliado",
        "Suspender captações a jusante até liberação analítica; abastecimento alternativo",
        "Não tratar a lama de rejeito como 'apenas água' — EPI e protocolo de descontaminação",
        "Coletar amostras de água, sedimento e, se indicado, biomarcadores com apoio CIEVS/LACEN",
        "Comunicar risco sem ordem de evacuação (competência da Defesa Civil / órgão fiscalizador)",
        "Preparar vigilância de médio prazo (meses a anos) para agravos de exposição química",
    ),
    laboratorio=(
        "Metais (Hg, As, Pb, Cd, Mn etc. conforme minério) em água e sedimento",
        "Cianeto livre/WAD se houver histórico de processo com cianeto",
        "pH, turbidez, sólidos e parâmetros de potabilidade",
        "Painel clínico conforme síndromes (função renal/hepática, carboxiemoglobina se couber)",
    ),
)


def eh_rejeito(uso: str | None, orgao: str | None = None, contaminante: str | None = None) -> bool:
    texto = " ".join(
        t.lower()
        for t in (uso or "", orgao or "", contaminante or "")
        if t
    )
    if "rejeito" in texto or "mineração" in texto or "mineracao" in texto or "anm" in texto:
        return True
    if contaminante and "rejeito" in contaminante.lower():
        return True
    return False


def perfil_de(
    uso: str | None = None,
    orgao: str | None = None,
    contaminante: str | None = None,
) -> PerfilImpacto:
    return PERFIL_REJEITO if eh_rejeito(uso, orgao, contaminante) else PERFIL_AGUA


def densidade_municipio(nome: str | None) -> float:
    if not nome:
        return DENSIDADE_PADRAO
    return _carregar_densidades_ibge().get(nome.strip(), DENSIDADE_PADRAO)


def area_equivalente_km2(volume_hm3: float, fracao: float, profundidade_m: float) -> float:
    """1 hm³ com 1 m de lâmina → 1 km²."""
    if profundidade_m <= 0:
        return 0.0
    return max(0.0, volume_hm3 * fracao / profundidade_m)


def estimar_populacao(
    *,
    area_km2: float,
    municipio_sede: str | None,
    municipios_afetados: list[str] | None = None,
    pop_sigbm_afetadas: float | None = None,
    pop_sigbm_jusante: float | None = None,
    fracao_volume: float = 1.0,
) -> dict[str, Any]:
    """Estima população exposta com cascata de fontes (todas rotuladas).

    Prioridade:
      1. SIGBM pessoas afetadas (quando informado)
      2. SIGBM população a jusante × fração do volume
      3. área equivalente × densidade municipal média dos afetados/sede
    """
    if pop_sigbm_afetadas is not None and pop_sigbm_afetadas > 0:
        pop = int(round(pop_sigbm_afetadas * min(1.0, max(0.05, fracao_volume))))
        return {
            "populacao_estimada": pop,
            "metodo": "sigbm_pessoas_afetadas",
            "detalhe": "Cadastro SIGBM (pessoas afetadas), ajustado pela fração liberada.",
            "densidade_hab_km2": None,
            "area_km2": round(area_km2, 2),
        }

    if pop_sigbm_jusante is not None and pop_sigbm_jusante > 0:
        pop = int(round(pop_sigbm_jusante * min(1.0, max(0.05, fracao_volume))))
        return {
            "populacao_estimada": pop,
            "metodo": "sigbm_populacao_jusante",
            "detalhe": "Cadastro SIGBM (população a jusante), ajustado pela fração liberada.",
            "densidade_hab_km2": None,
            "area_km2": round(area_km2, 2),
        }

    munis = municipios_afetados or ([municipio_sede] if municipio_sede else [])
    if munis:
        dens = sum(densidade_municipio(m) for m in munis) / len(munis)
    else:
        dens = densidade_municipio(municipio_sede)
    pop = int(round(area_km2 * dens))
    return {
        "populacao_estimada": pop,
        "metodo": "area_x_densidade",
        "detalhe": (
            f"Proxy geométrico: área equivalente × densidade média "
            f"({dens:.1f} hab/km²) dos municípios do vínculo Otto/sede."
        ),
        "densidade_hab_km2": round(dens, 1),
        "area_km2": round(area_km2, 2),
    }


def linhas_alerta(perfil: PerfilImpacto, estimativa: dict[str, Any] | None = None) -> list[str]:
    """Blocos textuais para inserir no alerta territorializado."""
    linhas: list[str] = []
    linhas.append(f"   Perfil de estrutura: {perfil.rotulo}")
    linhas.append(f"   Material considerado: {perfil.material}")
    if estimativa:
        linhas.append(
            f"   População potencialmente exposta (estimativa): "
            f"{estimativa['populacao_estimada']:,} pessoas "
            f"[método: {estimativa['metodo']}]".replace(",", ".")
        )
        if estimativa.get("area_km2") is not None:
            linhas.append(
                f"   Área equivalente de lâmina (proxy, não mancha oficial): "
                f"{estimativa['area_km2']} km²"
            )
        linhas.append(f"   {estimativa['detalhe']}")
    linhas.append("   Efeitos imediatos a considerar:")
    linhas.extend(f"   - {e}" for e in perfil.efeitos_imediatos)
    linhas.append("   Agravos / síndromes a vigiar (VIGIPÓS-BARRAGENS):")
    linhas.extend(f"   - {a}" for a in perfil.agravos_a_vigiar)
    linhas.append("   Ações sanitárias específicas deste perfil:")
    linhas.extend(f"   - {a}" for a in perfil.acoes_especificas)
    linhas.append("   Apoio laboratorial sugerido:")
    linhas.extend(f"   - {a}" for a in perfil.laboratorio)
    linhas.append(
        "   Ressalva: estimativas de área/população são proxies na ausência de mancha "
        "oficial; agravos listados são hipóteses de vigilância, não diagnóstico."
    )
    return linhas
