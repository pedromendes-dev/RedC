"""
Testes sintáticos da RedC (Etapa 3).

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
from errors import ErroSintatico  # noqa: E402
from redc_ast import (  # noqa: E402
    Atribuicao, Binaria, Bloco, Chamada, ComandoChamada, DeclaracaoVar,
    Enquanto, Literal, Mostre, Se, Unaria, Variavel,
)


def ast(fonte):
    return parser.analisar(lexer.analisar(fonte))


def expr(fonte_expr):
    """AST de uma expressão isolada, via 'mostre(...)'."""
    return ast(f"mostre({fonte_expr});").comandos[0].valor


class TestComandos(unittest.TestCase):
    def test_declaracao(self):
        cmd = ast("seja n :: inteiro = 5;").comandos[0]
        self.assertIsInstance(cmd, DeclaracaoVar)
        self.assertEqual((cmd.nome, cmd.tipo), ("n", "inteiro"))
        self.assertEqual(cmd.valor, Literal(5, "inteiro", linha=1, coluna=21))

    def test_atribuicao_e_chamada_comecam_com_ident(self):
        a, c = ast("n = 1; dobro(2);").comandos
        self.assertIsInstance(a, Atribuicao)
        self.assertIsInstance(c, ComandoChamada)
        self.assertEqual(c.chamada.nome, "dobro")

    def test_se_senao_se_senao(self):
        cmd = ast("se (a) { } senao se (b) { } senao { }").comandos[0]
        self.assertIsInstance(cmd, Se)
        self.assertIsInstance(cmd.senao, Se)
        self.assertIsInstance(cmd.senao.senao, Bloco)

    def test_enquanto(self):
        cmd = ast("enquanto (n > 1) { n = n - 1; }").comandos[0]
        self.assertIsInstance(cmd, Enquanto)
        self.assertEqual(len(cmd.corpo.comandos), 1)

    def test_funcao(self):
        prog = ast("funcao soma(a :: inteiro, b :: inteiro) :: inteiro { retorne a + b; }")
        f = prog.funcoes[0]
        self.assertEqual(f.nome, "soma")
        self.assertEqual([(p.nome, p.tipo) for p in f.parametros],
                         [("a", "inteiro"), ("b", "inteiro")])
        self.assertEqual(f.tipo_retorno, "inteiro")

    def test_funcao_sem_parametros(self):
        f = ast("funcao um() :: inteiro { retorne 1; }").funcoes[0]
        self.assertEqual(f.parametros, [])

    def test_programas_validos_da_pasta(self):
        for nome in ["exemplo_valido", "declaracao", "aritmetica",
                     "condicao", "repeticao"]:
            with self.subTest(programa=nome):
                fonte = (RAIZ / "programas" / f"{nome}.redc").read_text("utf-8")
                ast(fonte)


class TestExpressoes(unittest.TestCase):
    def assertArvore(self, no, esperado):
        """Compara a forma da árvore: ('op', esq, dir) / ('op', operando) / folha."""
        if isinstance(esperado, tuple):
            self.assertIn(no.op, esperado[0:1])
            if len(esperado) == 3:
                self.assertIsInstance(no, Binaria)
                self.assertArvore(no.esquerda, esperado[1])
                self.assertArvore(no.direita, esperado[2])
            else:
                self.assertIsInstance(no, Unaria)
                self.assertArvore(no.operando, esperado[1])
        elif isinstance(no, Variavel):
            self.assertEqual(no.nome, esperado)
        else:
            self.assertEqual(no.valor, esperado)

    def test_multiplicacao_antes_da_soma(self):
        self.assertArvore(expr("1 + 2 * 3"), ("+", 1, ("*", 2, 3)))

    def test_associatividade_a_esquerda(self):
        self.assertArvore(expr("10 - 3 - 2"), ("-", ("-", 10, 3), 2))

    def test_parenteses(self):
        self.assertArvore(expr("(1 + 2) * 3"), ("*", ("+", 1, 2), 3))

    def test_e_antes_de_ou(self):
        self.assertArvore(expr("a ou b e c"), ("ou", "a", ("e", "b", "c")))

    def test_relacional_antes_de_logico(self):
        self.assertArvore(expr("n > 0 e n < 10"),
                          ("e", (">", "n", 0), ("<", "n", 10)))

    def test_unarios(self):
        self.assertArvore(expr("nao a e b"), ("e", ("nao", "a"), "b"))
        self.assertArvore(expr("-n * 2"), ("*", ("-", "n"), 2))

    def test_chamada_aninhada(self):
        no = expr("media(fatorial(3), 2.0)")
        self.assertIsInstance(no, Chamada)
        self.assertIsInstance(no.argumentos[0], Chamada)


class TestErros(unittest.TestCase):
    def assertErro(self, fonte, linha, coluna, trecho):
        with self.assertRaises(ErroSintatico) as ctx:
            ast(fonte)
        erro = ctx.exception
        self.assertEqual((erro.linha, erro.coluna), (linha, coluna), erro.mensagem)
        self.assertIn(trecho, erro.mensagem)

    def test_ponto_e_virgula_apontado_no_fim_da_linha(self):
        self.assertErro("seja n :: inteiro = 5\nmostre(n);", 1, 22, "';'")

    def test_parentese_nao_fechado(self):
        self.assertErro("se (n > 0 { }", 1, 11, "esperado ')'")

    def test_bloco_nao_fechado(self):
        self.assertErro("enquanto (verdadeiro) {\n  mostre(1);\n", 3, 1,
                        "aberto na linha 1")

    def test_expressao_ausente(self):
        self.assertErro("seja n :: inteiro = ;", 1, 21, "esperado uma expressão")

    def test_tipo_invalido(self):
        # 'numero' seria um nome de registro (verificado na semântica);
        # um número no lugar do tipo é erro sintático.
        self.assertErro("seja n :: 5 = 5;", 1, 11, "esperado um tipo")

    def test_declaracao_sem_valor(self):
        self.assertErro("seja n :: inteiro;", 1, 18, "valor")

    def test_comando_invalido(self):
        self.assertErro("5 = n;", 1, 1, "comando inválido")

    def test_identificador_sozinho(self):
        self.assertErro("n;", 1, 2, "esperado '=' ou '('")

    def test_senao_sem_se(self):
        self.assertErro("senao { }", 1, 1, "sem 'se'")

    def test_funcao_dentro_de_bloco(self):
        self.assertErro("se (a) { funcao f() :: inteiro { retorne 1; } }", 1, 10,
                        "fora de blocos")

    def test_funcao_sem_tipo_de_retorno(self):
        self.assertErro("funcao f() { retorne 1; }", 1, 12, "'::'")

    def test_escolha_sem_caso(self):
        self.assertErro("escolha (n) { }", 1, 1, "pelo menos um 'caso'")


if __name__ == "__main__":
    unittest.main()
