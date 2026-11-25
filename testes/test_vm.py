"""
Testes de geração de código e execução na VM (Etapa 6).

Rodar a partir da pasta redc/:
    python -m unittest discover -s testes -v
"""

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import codegen  # noqa: E402
import lexer  # noqa: E402
import parser  # noqa: E402
import semantic  # noqa: E402
import vm  # noqa: E402
from errors import ErroExecucao  # noqa: E402


def compilar(fonte):
    arvore = parser.analisar(lexer.analisar(fonte))
    semantic.analisar(arvore)
    return codegen.gerar(arvore)


def rodar(fonte, **opcoes) -> list[str]:
    saida = []
    vm.executar(compilar(fonte), escrever=saida.append, **opcoes)
    return saida


class TestProgramasDaPasta(unittest.TestCase):
    ESPERADO = {
        "aritmetica": ["13", "7", "30", "3", "1", "26"],
        "condicao": ["aprovado"],
        "declaracao": ["Ana"],
        "repeticao": ["120"],
        "exemplo_valido": ["8.25", "aprovado", "120"],
        "escopos": ["sombreia o limite global", "6"],
    }

    def test_saida_de_cada_programa(self):
        for nome, esperado in self.ESPERADO.items():
            with self.subTest(programa=nome):
                fonte = (RAIZ / "programas" / f"{nome}.redc").read_text("utf-8")
                self.assertEqual(rodar(fonte), esperado)


class TestExecucao(unittest.TestCase):
    def test_tipos_no_mostre(self):
        self.assertEqual(rodar('mostre(1); mostre(2.5); mostre("oi"); mostre(verdadeiro); mostre(falso);'),
                         ["1", "2.5", "oi", "verdadeiro", "falso"])

    def test_precedencia(self):
        self.assertEqual(rodar("mostre(1 + 2 * 3); mostre((1 + 2) * 3); mostre(10 - 3 - 2);"),
                         ["7", "9", "5"])

    def test_divisao_inteira_trunca_como_c(self):
        self.assertEqual(rodar("mostre(7 / 2); mostre(-7 / 2); mostre(-7 % 2); mostre(7 / 2.0);"),
                         ["3", "-3", "-1", "3.5"])

    def test_promocao_para_real(self):
        self.assertEqual(rodar("seja r :: real = 5; mostre(r); r = r + 1; mostre(r);"),
                         ["5.0", "6.0"])

    def test_promocao_em_argumento_e_retorno(self):
        self.assertEqual(rodar("""
            funcao metade(x :: real) :: real { retorne x / 2; }
            funcao tres() :: real { retorne 3; }
            mostre(metade(7)); mostre(tres());
        """), ["3.5", "3.0"])

    def test_juntar_textos(self):
        self.assertEqual(rodar('seja n :: texto = "Ana"; mostre("Olá, " + n);'), ["Olá, Ana"])

    def test_logicos_e_comparacoes(self):
        self.assertEqual(rodar("""
            mostre(1 < 2 e 2 < 3); mostre(1 > 2 ou falso); mostre(nao (1 == 1.0));
            mostre("a" != "b");
        """), ["verdadeiro", "falso", "falso", "verdadeiro"])

    def test_curto_circuito_evita_divisao_por_zero(self):
        self.assertEqual(rodar("""
            seja n :: inteiro = 0;
            mostre(n != 0 e 10 / n > 1);
            mostre(n == 0 ou 10 / n > 1);
        """), ["falso", "verdadeiro"])

    def test_senao_se(self):
        prog = """
            funcao faixa(n :: inteiro) :: texto {
                se (n < 0) { retorne "negativo"; }
                senao se (n == 0) { retorne "zero"; }
                senao { retorne "positivo"; }
            }
            mostre(faixa(-5)); mostre(faixa(0)); mostre(faixa(9));
        """
        self.assertEqual(rodar(prog), ["negativo", "zero", "positivo"])

    def test_recursao_dupla(self):
        self.assertEqual(rodar("""
            funcao fib(n :: inteiro) :: inteiro {
                se (n < 2) { retorne n; }
                retorne fib(n - 1) + fib(n - 2);
            }
            mostre(fib(15));
        """), ["610"])

    def test_variaveis_de_chamadas_diferentes_nao_se_misturam(self):
        self.assertEqual(rodar("""
            funcao soma_ate(n :: inteiro) :: inteiro {
                seja total :: inteiro = 0;
                enquanto (n > 0) { total = total + n; n = n - 1; }
                retorne total;
            }
            seja total :: inteiro = 100;
            mostre(soma_ate(4)); mostre(total);
        """), ["10", "100"])

    def test_chamada_como_comando_descarta_valor(self):
        self.assertEqual(rodar("""
            funcao avisa(x :: inteiro) :: inteiro { mostre(x); retorne x; }
            avisa(7);
            mostre("fim");
        """), ["7", "fim"])

    def test_laco_com_sombreamento(self):
        self.assertEqual(rodar("""
            seja x :: inteiro = 1;
            seja i :: inteiro = 0;
            enquanto (i < 2) { seja x :: inteiro = i * 10; mostre(x); i = i + 1; }
            mostre(x);
        """), ["0", "10", "1"])


class TestErrosDeExecucao(unittest.TestCase):
    def assertErro(self, fonte, linha, coluna, trecho, **opcoes):
        saida = []
        with self.assertRaises(ErroExecucao) as ctx:
            vm.executar(compilar(fonte), escrever=saida.append, **opcoes)
        erro = ctx.exception
        self.assertEqual((erro.linha, erro.coluna), (linha, coluna), erro.mensagem)
        self.assertIn(trecho, erro.mensagem)
        return saida

    def test_divisao_por_zero(self):
        saida = self.assertErro('seja z :: inteiro = 0;\nmostre("antes");\nmostre(5 / z);',
                                3, 10, "divisão por zero")
        self.assertEqual(saida, ["antes"])      # o que veio antes do erro já foi mostrado

    def test_resto_por_zero(self):
        self.assertErro("seja z :: inteiro = 0;\nmostre(5 % z);", 2, 10, "divisão por zero")

    def test_divisao_real_por_zero(self):
        self.assertErro("seja z :: real = 0.0;\nmostre(1.0 / z);", 2, 12, "divisão por zero")

    def test_recursao_infinita(self):
        self.assertErro("funcao f(n :: inteiro) :: inteiro { retorne f(n + 1); }\nmostre(f(0));",
                        1, 45, "estouro de pilha")

    def test_laco_infinito(self):
        self.assertErro("enquanto (verdadeiro) { }", 1, 1, "laço infinito",
                        limite_instrucoes=10_000)


class TestBytecode(unittest.TestCase):
    def ops(self, fonte):
        return [i.op for i in compilar(fonte).instrucoes]

    def test_maquina_de_pilha(self):
        self.assertEqual(self.ops("seja n :: inteiro = 2 * 3;"),
                         ["PUSH", "PUSH", "MUL", "STORE", "HALT"])

    def test_divisao_escolhe_instrucao_pelo_tipo(self):
        self.assertIn("DIV_INT", self.ops("mostre(7 / 2);"))
        self.assertIn("DIV_REAL", self.ops("mostre(7 / 2.0);"))

    def test_conversao_explicita_para_real(self):
        self.assertIn("TO_REAL", self.ops("seja r :: real = 5;"))

    def test_saltos_do_enquanto(self):
        bc = compilar("seja i :: inteiro = 0;\nenquanto (i < 3) { i = i + 1; }")
        ins = bc.instrucoes
        salto_saida = next(i for i in ins if i.op == "JUMP_IF_FALSE")
        volta = next(i for i in ins if i.op == "JUMP")
        self.assertEqual(ins[salto_saida.arg].op, "HALT")   # sai para depois do laço
        self.assertEqual(volta.arg, 2)                      # volta para a condição

    def test_funcoes_depois_do_halt(self):
        bc = compilar("funcao um() :: inteiro { retorne 1; }\nmostre(um());")
        halt = [i.op for i in bc.instrucoes].index("HALT")
        self.assertGreater(bc.funcoes["um"].endereco, halt)


if __name__ == "__main__":
    unittest.main()
