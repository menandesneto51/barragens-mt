"""Testes do IDAP-Barragens com `unittest` da biblioteca padrão.

Execução, a partir da raiz do projeto:

    python -m unittest scripts.idap.testes
    python scripts/idap/testes.py
"""

from __future__ import annotations

import unittest
from datetime import datetime

try:
    from . import calculo, pesos, regras
    from .calculo import NivelAlerta, calcular_idap, classificar
    from .modelo import (
        CapacidadeResposta,
        CondicaoEstrutura,
        EstadoBarragem,
        ExposicaoSanitaria,
        PressaoHidroclimatica,
        SinaisOperacionais,
    )
    from .regras import aplicar_regras
    from .relatorio import RESSALVA_OBRIGATORIA, montar_alerta
except ImportError:  # python scripts/idap/testes.py
    import calculo  # type: ignore[no-redef]
    import pesos  # type: ignore[no-redef]
    import regras  # type: ignore[no-redef]
    from calculo import NivelAlerta, calcular_idap, classificar  # type: ignore[no-redef]
    from modelo import (  # type: ignore[no-redef]
        CapacidadeResposta,
        CondicaoEstrutura,
        EstadoBarragem,
        ExposicaoSanitaria,
        PressaoHidroclimatica,
        SinaisOperacionais,
    )
    from regras import aplicar_regras  # type: ignore[no-redef]
    from relatorio import RESSALVA_OBRIGATORIA, montar_alerta  # type: ignore[no-redef]

if __package__:
    from . import exemplo
else:  # python scripts/idap/testes.py
    import exemplo  # type: ignore[no-redef]

INSTANTE = datetime(2026, 7, 29, 15, 30)


def estado(**substituicoes) -> EstadoBarragem:
    """Barragem vazia por padrão: todos os indicadores em lacuna."""
    base = {
        "id_barragem": "MT-TESTE-0001",
        "nome": "Barragem de Teste",
        "municipio": "Cuiabá",
        "instante": INSTANTE,
        "municipios_zas": ("Cuiabá",),
    }
    base.update(substituicoes)
    return EstadoBarragem(**base)


def pressao_maxima() -> PressaoHidroclimatica:
    return PressaoHidroclimatica(
        chuva_24h_mm=500.0,
        chuva_72h_mm=900.0,
        chuva_prevista_24_72h_mm=400.0,
        percentil_climatologico=100.0,
        saturacao_antecedente=1.0,
        razao_nivel_cota_alerta=3.0,
        dias_consecutivos_chuva_intensa=12,
    )


def estrutura_maxima() -> CondicaoEstrutura:
    return CondicaoEstrutura(
        categoria_risco="Alto",
        nivel_emergencia="Emergência Nível 3",
        situacao_estabilidade="Não atestada",
        pior_nota_anomalia=10.0,
        razao_volume_capacidade=1.5,
        situacao_telemetria="Ausente ou sem transmissão",
    )


def exposicao_maxima() -> ExposicaoSanitaria:
    return ExposicaoSanitaria(
        populacao_zas=50_000,
        proporcao_vulneravel=0.9,
        unidades_saude_sem_internacao=10,
        unidades_saude_com_internacao=3,
        hospital_referencia_ameacado=True,
        captacao_ameacada="Captação principal de sede municipal ou única captação",
        servicos_essenciais_ameacados=12,
        tempo_chegada_onda_min=5.0,
        isolamento_rodoviario="Acesso único sem alternativa",
        contaminante_predominante="Rejeito não inerte ou perigoso",
    )


def capacidade_maxima() -> CapacidadeResposta:
    return CapacidadeResposta(
        situacao_plano_emergencia="Inexistente",
        meses_desde_ultimo_simulado=200.0,
        cobertura_alerta_zas=0.0,
        razao_vagas_abrigo=0.0,
        ambulancias_por_10mil=0.0,
        razao_leitos_demanda=0.0,
        possui_rota_alternativa=False,
        contatos_validados_90d=False,
    )


def estado_pior_caso() -> EstadoBarragem:
    return estado(
        pressao=pressao_maxima(),
        estrutura=estrutura_maxima(),
        exposicao=exposicao_maxima(),
        capacidade=capacidade_maxima(),
    )


class TestCalibracao(unittest.TestCase):
    def test_calibracao_publicada_e_consistente(self):
        pesos.validar_calibracao()

    def test_soma_dos_tetos_por_dimensao(self):
        self.assertEqual(pesos.teto_por_dimensao("A"), 30)
        self.assertEqual(pesos.teto_por_dimensao("B"), 30)
        self.assertEqual(pesos.teto_por_dimensao("C"), 25)
        self.assertEqual(pesos.teto_por_dimensao("D"), 15)
        self.assertEqual(sum(pesos.TETOS.values()), pesos.TETO_IDAP)

    def test_versao_dos_pesos_esta_declarada(self):
        self.assertTrue(pesos.VERSAO_PESOS)
        self.assertIn("metodologica", pesos.VERSAO_PESOS)


class TestTetosPorDimensao(unittest.TestCase):
    def test_dimensao_a_respeita_o_teto_de_30(self):
        dimensao = calculo.pontuar_pressao(pressao_maxima())
        self.assertEqual(dimensao.pontos, 30)
        self.assertEqual(dimensao.teto, 30)

    def test_dimensao_b_respeita_o_teto_de_30(self):
        dimensao = calculo.pontuar_estrutura(estrutura_maxima())
        self.assertEqual(dimensao.pontos, 30)
        self.assertEqual(dimensao.teto, 30)

    def test_dimensao_c_respeita_o_teto_de_25(self):
        dimensao = calculo.pontuar_exposicao(exposicao_maxima())
        self.assertEqual(dimensao.pontos, 25)
        self.assertEqual(dimensao.teto, 25)

    def test_dimensao_d_respeita_o_teto_de_15(self):
        dimensao = calculo.pontuar_capacidade(capacidade_maxima())
        self.assertEqual(dimensao.pontos, 15)
        self.assertEqual(dimensao.teto, 15)

    def test_nenhuma_dimensao_pode_estourar_o_teto(self):
        for dimensao in calcular_idap(estado_pior_caso()).dimensoes:
            self.assertLessEqual(dimensao.pontos, dimensao.teto)


class TestIntervaloDoIndice(unittest.TestCase):
    def test_pior_caso_chega_a_100(self):
        self.assertEqual(calcular_idap(estado_pior_caso()).idap, 100)

    def test_estado_sem_dado_resulta_em_zero(self):
        self.assertEqual(calcular_idap(estado()).idap, 0)

    def test_indice_nunca_sai_do_intervalo_0_a_100(self):
        casos = [
            estado(),
            estado_pior_caso(),
            estado(pressao=pressao_maxima()),
            estado(estrutura=estrutura_maxima(), capacidade=capacidade_maxima()),
            estado(exposicao=exposicao_maxima()),
        ]
        for caso in casos:
            with self.subTest(caso=caso.nome):
                idap = calcular_idap(caso).idap
                self.assertGreaterEqual(idap, 0)
                self.assertLessEqual(idap, pesos.TETO_IDAP)


class TestFronteirasDasFaixas(unittest.TestCase):
    FRONTEIRAS = (
        (0, NivelAlerta.VERDE),
        (19, NivelAlerta.VERDE),
        (20, NivelAlerta.AMARELO),
        (39, NivelAlerta.AMARELO),
        (40, NivelAlerta.LARANJA),
        (59, NivelAlerta.LARANJA),
        (60, NivelAlerta.VERMELHO),
        (79, NivelAlerta.VERMELHO),
        (80, NivelAlerta.ROXO),
        (100, NivelAlerta.ROXO),
    )

    def test_fronteiras_exatas(self):
        for pontuacao, esperado in self.FRONTEIRAS:
            with self.subTest(pontuacao=pontuacao):
                self.assertIs(classificar(pontuacao), esperado)

    def test_todas_as_pontuacoes_tem_faixa(self):
        for pontuacao in range(0, pesos.TETO_IDAP + 1):
            self.assertIsInstance(classificar(pontuacao), NivelAlerta)

    def test_pontuacao_fora_do_intervalo_falha(self):
        for pontuacao in (-1, 101):
            with self.subTest(pontuacao=pontuacao):
                with self.assertRaises(ValueError):
                    classificar(pontuacao)

    def test_ordem_dos_niveis(self):
        self.assertLess(NivelAlerta.VERDE, NivelAlerta.AMARELO)
        self.assertLess(NivelAlerta.AMARELO, NivelAlerta.LARANJA)
        self.assertLess(NivelAlerta.LARANJA, NivelAlerta.VERMELHO)
        self.assertLess(NivelAlerta.VERMELHO, NivelAlerta.ROXO)


class TestDadoAusente(unittest.TestCase):
    def test_ausencia_total_nao_infla_pontuacao(self):
        resultado = calcular_idap(estado())
        self.assertEqual(resultado.idap, 0)
        self.assertEqual(resultado.completude, 0.0)
        self.assertEqual(resultado.confiabilidade, "insuficiente")
        self.assertEqual(len(resultado.lacunas), len(pesos.INDICADORES))

    def test_ausencia_parcial_nunca_aumenta_o_indice(self):
        completo = calcular_idap(estado_pior_caso())
        parcial = calcular_idap(
            estado(
                pressao=pressao_maxima(),
                estrutura=estrutura_maxima(),
                exposicao=exposicao_maxima(),
            )
        )
        self.assertLess(parcial.idap, completo.idap)
        self.assertLess(parcial.completude, completo.completude)

    def test_categoria_declarada_de_desconhecimento_pontua_precaucao(self):
        # "Não Classificado" existe de fato no SNISB e rende 2 pontos de precaução;
        # `None` significa "não avaliado" e rende zero. A distinção é o núcleo da regra.
        declarado = calculo.pontuar_estrutura(CondicaoEstrutura(categoria_risco="Não Classificado"))
        ausente = calculo.pontuar_estrutura(CondicaoEstrutura(categoria_risco=None))
        self.assertEqual(declarado.pontos, 2)
        self.assertEqual(ausente.pontos, 0)
        self.assertIn("B1", ausente.lacunas)
        self.assertNotIn("B1", declarado.lacunas)

    def test_categoria_fora_do_dominio_vira_lacuna(self):
        dimensao = calculo.pontuar_estrutura(CondicaoEstrutura(categoria_risco="Altíssimo"))
        self.assertEqual(dimensao.pontos, 0)
        self.assertIn("B1", dimensao.lacunas)

    def test_indice_projetado_nao_classifica_alerta(self):
        # Só a pressão máxima foi apurada: o índice é 30, mas o projetado é 100.
        resultado = calcular_idap(estado(pressao=pressao_maxima()))
        self.assertEqual(resultado.idap, 30)
        self.assertEqual(resultado.idap_projetado, 100.0)
        self.assertIs(resultado.nivel, NivelAlerta.AMARELO)

    def test_completude_por_dimensao(self):
        resultado = calcular_idap(estado(pressao=pressao_maxima()))
        self.assertEqual(resultado.dimensao("A").completude, 1.0)
        self.assertEqual(resultado.dimensao("B").completude, 0.0)


class TestRegrasDeterministicas(unittest.TestCase):
    def _final(self, **substituicoes):
        caso = estado(**substituicoes)
        return caso, aplicar_regras(caso, calcular_idap(caso))

    def test_r01_emergencia_nivel_2_eleva_a_vermelho(self):
        _, final = self._final(
            estrutura=CondicaoEstrutura(nivel_emergencia="Emergência Nivel 2")
        )
        self.assertIs(final.nivel_final, NivelAlerta.VERMELHO)
        self.assertIn("R01", [r.codigo for r in final.regras_disparadas])
        self.assertTrue(final.elevado_por_regra)

    def test_r01_emergencia_nivel_3_eleva_a_vermelho_no_minimo(self):
        _, final = self._final(
            estrutura=CondicaoEstrutura(nivel_emergencia="Emergência Nível 3")
        )
        self.assertGreaterEqual(final.nivel_final, NivelAlerta.VERMELHO)

    def test_r01_nao_dispara_em_nivel_1(self):
        _, final = self._final(
            estrutura=CondicaoEstrutura(nivel_emergencia="Emergência Nivel 1")
        )
        self.assertNotIn("R01", [r.codigo for r in final.regras_disparadas])

    def test_r02_rompimento_confirmado_eleva_a_roxo(self):
        _, final = self._final(sinais=SinaisOperacionais(rompimento_confirmado=True))
        self.assertIs(final.nivel_final, NivelAlerta.ROXO)
        self.assertIn("R02", [r.codigo for r in final.regras_disparadas])

    def test_r03_exige_perda_de_nivel_e_anomalia_ativa(self):
        _, so_perda = self._final(sinais=SinaisOperacionais(perda_subita_de_nivel=True))
        self.assertNotIn("R03", [r.codigo for r in so_perda.regras_disparadas])

        _, com_anomalia = self._final(
            sinais=SinaisOperacionais(perda_subita_de_nivel=True),
            estrutura=CondicaoEstrutura(pior_nota_anomalia=6.0),
        )
        self.assertIn("R03", [r.codigo for r in com_anomalia.regras_disparadas])
        self.assertIs(com_anomalia.nivel_final, NivelAlerta.ROXO)

    def test_r04_chuva_extrema_com_anomalia_eleva_a_vermelho(self):
        _, final = self._final(
            pressao=PressaoHidroclimatica(chuva_24h_mm=pesos.LIMIAR_CHUVA_EXTREMA_24H_MM),
            estrutura=CondicaoEstrutura(pior_nota_anomalia=pesos.LIMIAR_ANOMALIA_ATIVA),
        )
        self.assertIn("R04", [r.codigo for r in final.regras_disparadas])
        self.assertGreaterEqual(final.nivel_final, NivelAlerta.VERMELHO)

    def test_r04_nao_dispara_sem_anomalia(self):
        _, final = self._final(
            pressao=PressaoHidroclimatica(chuva_24h_mm=300.0),
            estrutura=CondicaoEstrutura(pior_nota_anomalia=1.0),
        )
        self.assertNotIn("R04", [r.codigo for r in final.regras_disparadas])

    def test_r05_evacuacao_determinada_eleva_a_roxo(self):
        _, final = self._final(sinais=SinaisOperacionais(evacuacao_determinada=True))
        self.assertIs(final.nivel_final, NivelAlerta.ROXO)

    def test_r06_dispara_por_sensores_e_nao_altera_nivel(self):
        caso, final = self._final(
            estrutura=estrutura_maxima(),
            sinais=SinaisOperacionais(
                sensores_criticos_em_falha=pesos.LIMIAR_SENSORES_CRITICOS_EM_FALHA
            ),
        )
        disparadas = {r.codigo: r for r in final.regras_disparadas}
        self.assertIn("R06", disparadas)
        self.assertIsNone(disparadas["R06"].nivel_minimo)

    def test_r06_dispara_por_cadastro_insuficiente_da_dimensao_b(self):
        _, final = self._final()
        self.assertIn("R06", [r.codigo for r in final.regras_disparadas])
        self.assertIs(final.nivel_final, NivelAlerta.VERDE)

    def test_r07_unidade_estrategica_eleva_a_laranja(self):
        _, final = self._final(
            sinais=SinaisOperacionais(mancha_atinge_unidade_estrategica=True)
        )
        self.assertGreaterEqual(final.nivel_final, NivelAlerta.LARANJA)
        self.assertIn("R07", [r.codigo for r in final.regras_disparadas])

    def test_r08_captacao_eleva_a_laranja(self):
        _, final = self._final(sinais=SinaisOperacionais(mancha_atinge_captacao=True))
        self.assertGreaterEqual(final.nivel_final, NivelAlerta.LARANJA)
        self.assertIn("R08", [r.codigo for r in final.regras_disparadas])

    def test_r09_falta_de_confirmacao_escalona_sem_elevar(self):
        _, final = self._final(
            sinais=SinaisOperacionais(municipios_zas_sem_confirmacao=("Poconé",))
        )
        disparadas = {r.codigo: r for r in final.regras_disparadas}
        self.assertIn("R09", disparadas)
        self.assertIsNone(disparadas["R09"].nivel_minimo)

    def test_regra_nunca_rebaixa_o_nivel_do_indice(self):
        caso = estado(
            pressao=pressao_maxima(),
            estrutura=estrutura_maxima(),
            exposicao=exposicao_maxima(),
            capacidade=capacidade_maxima(),
            sinais=SinaisOperacionais(mancha_atinge_captacao=True),
        )
        final = aplicar_regras(caso, calcular_idap(caso))
        self.assertIs(final.nivel_final, NivelAlerta.ROXO)
        self.assertGreaterEqual(final.nivel_final, final.nivel_indice)

    def test_todas_as_regras_tem_acao_e_fundamento(self):
        self.assertEqual(len(regras.REGRAS), 9)
        for regra in regras.REGRAS:
            with self.subTest(regra=regra.codigo):
                self.assertTrue(regra.acao.strip())
                self.assertTrue(regra.fundamento.strip())


class TestReprodutibilidade(unittest.TestCase):
    def test_dois_calculos_do_mesmo_estado_sao_identicos(self):
        caso = estado_pior_caso()
        primeiro = calcular_idap(caso)
        segundo = calcular_idap(caso)
        self.assertEqual(primeiro, segundo)
        self.assertEqual(primeiro.justificativas(), segundo.justificativas())

    def test_alerta_gerado_duas_vezes_e_identico(self):
        caso = estado_pior_caso()
        um = montar_alerta(caso, aplicar_regras(caso, calcular_idap(caso)))
        outro = montar_alerta(caso, aplicar_regras(caso, calcular_idap(caso)))
        self.assertEqual(um, outro)

    def test_resultado_registra_a_versao_dos_pesos(self):
        self.assertEqual(calcular_idap(estado()).versao_pesos, pesos.VERSAO_PESOS)

    def test_ordem_das_justificativas_e_estavel_por_peso(self):
        resultado = calcular_idap(estado_pior_caso())
        justificativas = resultado.justificativas()
        self.assertTrue(justificativas)
        self.assertIn("[B2]", justificativas[0])


class TestAlerta(unittest.TestCase):
    def test_alerta_contem_ressalva_obrigatoria(self):
        caso = estado_pior_caso()
        texto = montar_alerta(caso, aplicar_regras(caso, calcular_idap(caso)))
        self.assertIn(RESSALVA_OBRIGATORIA, texto)

    def test_alerta_declara_fuso_de_cuiaba_e_versao(self):
        caso = estado_pior_caso()
        texto = montar_alerta(caso, aplicar_regras(caso, calcular_idap(caso)))
        self.assertIn("horário de Cuiabá, UTC-4", texto)
        self.assertIn(pesos.VERSAO_PESOS, texto)
        self.assertIn("29/07/2026 15:30", texto)

    def test_alerta_avisa_quando_a_completude_e_baixa(self):
        caso = estado()
        texto = montar_alerta(caso, aplicar_regras(caso, calcular_idap(caso)))
        self.assertIn("subestimado", texto)


class TestExemplo(unittest.TestCase):
    def test_cenarios_do_exemplo_caem_nas_faixas_previstas(self):
        esperado = {
            "MT-EX-0001": NivelAlerta.VERDE,
            "MT-EX-0002": NivelAlerta.LARANJA,
            "MT-EX-0003": NivelAlerta.VERMELHO,
            "MT-EX-0004": NivelAlerta.ROXO,
        }
        for _, construtor in exemplo.CENARIOS:
            caso = construtor()
            final = aplicar_regras(caso, calcular_idap(caso))
            with self.subTest(barragem=caso.id_barragem):
                self.assertIs(final.nivel_final, esperado[caso.id_barragem])

    def test_cenario_3_e_elevado_por_regra_e_nao_por_pontuacao(self):
        caso = exemplo.cenario_vermelho_por_regra()
        final = aplicar_regras(caso, calcular_idap(caso))
        self.assertIs(final.nivel_indice, NivelAlerta.AMARELO)
        self.assertIs(final.nivel_final, NivelAlerta.VERMELHO)
        self.assertTrue(final.elevado_por_regra)


if __name__ == "__main__":
    unittest.main(verbosity=2)
