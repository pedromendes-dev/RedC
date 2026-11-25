"""
Testes semânticos de tipos da RedC (Etapa 5).
Os testes de escopo e declaração estão em test_symbols.py.

Rodar a partir da pasta redc/:
    python -m unittest discover -s testes -v
"""

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import lexer  # noqa: E402
import parser  # noqa: E402
import semantic  # noqa: E402
from errors import ErroSemantico  # noqa: E402


def programa(fonte):
    arvore = parser.analisar(lexer.analisar(fonte))
    semantic.analisar(arvore)
    return arvore


def tipo_de(expr, declaracoes=""):
    """Tipo resolvido de uma expressão, via 'mostre(...)'."""
    arvore = programa(f"{declaracoes}\nmostre({expr});")
    return arvore.comandos[-1].valor.tipo_resolvido


DECL = """
seja i :: inteiro = 1;
seja r :: real = 1.5;
seja t :: texto = "a";
seja b :: logico = verdadeiro;
"""


class TestTiposValidos(unittest.TestCase):
    def test_aritmetica(self):
        self.assertEqual(tipo_de("i + i", DECL), "inteiro")
        self.assertEqual(tipo_de("i * r", DECL), "real")
        self.assertEqual(tipo_de("i / i", DECL), "inteiro")   # divisão inteira
        self.assertEqual(tipo_de("r / i", DECL), "real")
        self.assertEqual(tipo_de("i % 2", DECL), "inteiro")
        self.assertEqual(tipo_de("-r", DECL), "real")

    def test_juncao_de_textos(self):
        self.assertEqual(tipo_de('t + "b"', DECL), "texto")

    def test_comparacoes_e_logicos(self):
        self.assertEqual(tipo_de("i < r", DECL), "logico")
        self.assertEqual(tipo_de('t == "a"', DECL), "logico")
        self.assertEqual(tipo_de("i != r", DECL), "logico")
        self.assertEqual(tipo_de("b e nao b ou i > 0", DECL), "logico")

    def test_inteiro_cabe_em_real(self):
        programa("seja r :: real = 5; r = 2;")

    def test_chamada_com_promocao_de_argumento(self):
        programa("funcao metade(x :: real) :: real { retorne x / 2.0; }\n"
                 "seja m :: real = metade(7);")

    def test_retorne_em_todos_os_caminhos(self):
        programa("""
            funcao sinal(n :: inteiro) :: inteiro {
                se (n > 0) { retorne 1; }
                senao se (n < 0) { retorne -1; }
                senao { retorne 0; }
            }
        """)

    def test_mostre_aceita_qualquer_tipo(self):
        programa(DECL + "mostre(i); mostre(r); mostre(t); mostre(b);")

    def test_slots_diferentes_para_nomes_sombreados(self):
        arvore = programa("""
            seja x :: inteiro = 1;
            se (verdadeiro) { seja x :: texto = "y"; }
        """)
        externo = arvore.comandos[0].simbolo
        interno = arvore.comandos[1].entao.comandos[0].simbolo
        self.assertNotEqual(externo.slot, interno.slot)
        self.assertEqual(arvore.tamanho_quadro, 2)

    def test_programas_validos_da_pasta(self):
        for nome in ["exemplo_valido", "declaracao", "aritmetica",
                     "condicao", "repeticao", "escopos"]:
            with self.subTest(programa=nome):
                programa((RAIZ / "programas" / f"{nome}.redc").read_text("utf-8"))


class TestErrosDeTipo(unittest.TestCase):
    def assertErro(self, fonte, linha, coluna, trecho):
        with self.assertRaises(ErroSemantico) as ctx:
            programa(fonte)
        erro = ctx.exception
        self.assertEqual((erro.linha, erro.coluna), (linha, coluna), erro.mensagem)
        self.assertIn(trecho, erro.mensagem)

    def test_texto_em_inteiro(self):
        self.assertErro('seja idade :: inteiro = "35";', 1, 25,
                        "esperado inteiro, recebido texto")

    def test_real_em_inteiro(self):
        self.assertErro("seja n :: inteiro = 2.5;", 1, 21, "casas decimais")

    def test_atribuicao_de_tipo_errado(self):
        self.assertErro("seja ok :: logico = falso;\nok = 1;", 2, 6,
                        "esperado logico, recebido inteiro")

    def test_soma_de_texto_com_numero(self):
        self.assertErro('mostre("total: " + 10);', 1, 18, "não transforma números")

    def test_modulo_com_real(self):
        self.assertErro("mostre(7.5 % 2);", 1, 12, "só aceita inteiros")

    def test_divisao_por_zero_literal(self):
        self.assertErro("mostre(10 / 0);", 1, 13, "divisão por zero")

    def test_comparar_texto_com_numero(self):
        self.assertErro('mostre("1" == 1);', 1, 12, "comparar texto com inteiro")

    def test_relacional_com_texto(self):
        self.assertErro('mostre("a" < "b");', 1, 12, "compara números")

    def test_logico_com_numero(self):
        self.assertErro("mostre(verdadeiro e 1);", 1, 19, "dois valores logico")

    def test_nao_com_numero(self):
        self.assertErro("mostre(nao 5);", 1, 8, "um valor logico")

    def test_menos_com_texto(self):
        self.assertErro('mostre(-"a");', 1, 8, "um número")

    def test_condicao_do_se_nao_logica(self):
        self.assertErro("seja n :: inteiro = 1;\nse (n) { }", 2, 5,
                        "condição do 'se' precisa ser logico")

    def test_condicao_do_enquanto_nao_logica(self):
        self.assertErro('enquanto ("sim") { }', 1, 11, "condição do 'enquanto'")

    def test_numero_de_argumentos(self):
        self.assertErro("funcao f(a :: inteiro) :: inteiro { retorne a; }\nmostre(f(1, 2));",
                        2, 8, "espera 1 argumento(s), recebeu 2")

    def test_tipo_de_argumento(self):
        self.assertErro('funcao f(a :: inteiro) :: inteiro { retorne a; }\nmostre(f("x"));',
                        2, 10, "argumento 1 de 'f': esperado inteiro, recebido texto")

    def test_retorno_de_tipo_errado(self):
        self.assertErro('funcao f() :: inteiro { retorne "x"; }', 1, 33,
                        "retorna inteiro, mas 'retorne' recebeu texto")

    def test_funcao_sem_retorne(self):
        self.assertErro("funcao f() :: inteiro { mostre(1); }", 1, 1, "pode terminar sem")

    def test_se_sem_senao_nao_garante_retorno(self):
        self.assertErro("funcao f(n :: inteiro) :: inteiro { se (n > 0) { retorne 1; } }",
                        1, 1, "pode terminar sem")

    def test_enquanto_nao_garante_retorno(self):
        self.assertErro("funcao f() :: inteiro { enquanto (verdadeiro) { retorne 1; } }",
                        1, 1, "pode terminar sem")


if __name__ == "__main__":
    unittest.main()
