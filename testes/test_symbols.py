"""
Testes da tabela de símbolos e dos escopos (Etapa 4).

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
from symbols import Simbolo, TabelaSimbolos  # noqa: E402


def var(nome, tipo="inteiro", linha=1):
    return Simbolo(nome, "variavel", tipo, linha, 1)


def tabela_de(fonte):
    return semantic.analisar(parser.analisar(lexer.analisar(fonte)))


class TestTabela(unittest.TestCase):
    """A estrutura de dados, isolada do resto do compilador."""

    def test_declarar_e_buscar(self):
        t = TabelaSimbolos()
        t.declarar(var("n"))
        self.assertEqual(t.buscar("n").tipo, "inteiro")
        self.assertIsNone(t.buscar("x"))

    def test_busca_desce_a_pilha(self):
        t = TabelaSimbolos()
        t.declarar(var("global_"))
        t.abrir_escopo("bloco")
        self.assertIsNotNone(t.buscar("global_"))

    def test_escopo_fechado_some(self):
        t = TabelaSimbolos()
        t.abrir_escopo("bloco")
        t.declarar(var("local"))
        t.fechar_escopo()
        self.assertIsNone(t.buscar("local"))

    def test_sombreamento(self):
        t = TabelaSimbolos()
        t.declarar(var("x", "inteiro"))
        t.abrir_escopo("bloco")
        t.declarar(var("x", "texto"))
        self.assertEqual(t.buscar("x").tipo, "texto")
        t.fechar_escopo()
        self.assertEqual(t.buscar("x").tipo, "inteiro")

    def test_redeclaracao_no_mesmo_escopo(self):
        t = TabelaSimbolos()
        t.declarar(var("x", linha=1))
        with self.assertRaises(ErroSemantico) as ctx:
            t.declarar(var("x", linha=5))
        self.assertIn("linha 1", ctx.exception.mensagem)

    def test_niveis(self):
        t = TabelaSimbolos()
        self.assertEqual(t.abrir_escopo("a").nivel, 1)
        self.assertEqual(t.abrir_escopo("b").nivel, 2)

    def test_global_nao_fecha(self):
        with self.assertRaises(RuntimeError):
            TabelaSimbolos().fechar_escopo()


class TestEscoposNoPrograma(unittest.TestCase):
    """O analisador preenchendo a tabela a partir da AST."""

    def test_registra_funcao_parametros_e_locais(self):
        t = tabela_de("funcao f(a :: real) :: real { seja b :: real = a; retorne b; }")
        globais, func = t.todos[0], t.todos[1]
        self.assertEqual(globais.simbolos["f"].assinatura(), "(real) :: real")
        self.assertEqual(func.nome, "funcao f")
        self.assertEqual(func.simbolos["a"].categoria, "parametro")
        self.assertEqual(func.simbolos["b"].categoria, "variavel")

    def test_recursao_e_chamada_antes_da_declaracao(self):
        tabela_de("""
            mostre(f(3));
            funcao f(n :: inteiro) :: inteiro { retorne f(n - 1); }
        """)

    def test_sombreamento_em_bloco(self):
        tabela_de("""
            seja x :: inteiro = 1;
            se (verdadeiro) { seja x :: texto = "outro"; mostre(x); }
            mostre(x);
        """)

    def test_programas_validos_da_pasta(self):
        for nome in ["exemplo_valido", "declaracao", "aritmetica",
                     "condicao", "repeticao", "escopos"]:
            with self.subTest(programa=nome):
                fonte = (RAIZ / "programas" / f"{nome}.redc").read_text("utf-8")
                tabela_de(fonte)


class TestErrosDeEscopo(unittest.TestCase):
    def assertErro(self, fonte, linha, coluna, trecho):
        with self.assertRaises(ErroSemantico) as ctx:
            tabela_de(fonte)
        erro = ctx.exception
        self.assertEqual((erro.linha, erro.coluna), (linha, coluna), erro.mensagem)
        self.assertIn(trecho, erro.mensagem)

    def test_variavel_nao_declarada(self):
        self.assertErro("mostre(x);", 1, 8, "'x' não foi declarada")

    def test_atribuicao_sem_declaracao(self):
        self.assertErro("x = 1;", 1, 1, "não foi declarada")

    def test_variavel_redeclarada(self):
        self.assertErro("seja x :: inteiro = 1;\nseja x :: real = 2.0;", 2, 1,
                        "já foi declarado")

    def test_local_com_nome_de_parametro(self):
        self.assertErro("funcao f(a :: inteiro) :: inteiro { seja a :: inteiro = 1; retorne a; }",
                        1, 37, "parametro")

    def test_parametro_duplicado(self):
        self.assertErro("funcao f(a :: inteiro, a :: real) :: inteiro { retorne 1; }",
                        1, 24, "já foi declarado")

    def test_funcao_duplicada(self):
        self.assertErro("funcao f() :: inteiro { retorne 1; }\n"
                        "funcao f() :: real { retorne 1.0; }", 2, 1, "já foi declarado")

    def test_variavel_de_bloco_nao_existe_fora(self):
        self.assertErro("se (verdadeiro) { seja y :: inteiro = 1; }\nmostre(y);",
                        2, 8, "'y' não foi declarada")

    def test_declaracao_usando_ela_mesma(self):
        self.assertErro("seja x :: inteiro = x + 1;", 1, 21, "não foi declarada")

    def test_funcao_nao_enxerga_global(self):
        self.assertErro("funcao f() :: inteiro { retorne g; }\nseja g :: inteiro = 1;",
                        1, 33, "é global")

    def test_funcao_nao_declarada(self):
        self.assertErro("mostre(soma(1, 2));", 1, 8, "função 'soma' não foi declarada")

    def test_variavel_chamada_como_funcao(self):
        self.assertErro("seja x :: inteiro = 1;\nx(2);", 2, 1, "não uma função")

    def test_funcao_usada_como_variavel(self):
        self.assertErro("funcao f() :: inteiro { retorne 1; }\nmostre(f + 1);", 2, 8,
                        "use f(...)")

    def test_retorne_fora_de_funcao(self):
        self.assertErro("retorne 1;", 1, 1, "dentro de uma função")


if __name__ == "__main__":
    unittest.main()
