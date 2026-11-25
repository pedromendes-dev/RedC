"""
Testes léxicos da RedC (Etapa 2).

Rodar a partir da pasta redc/:
    python -m unittest discover -s testes -v
"""

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from errors import ErroLexico  # noqa: E402
from lexer import analisar  # noqa: E402
from tokens import TipoToken as T  # noqa: E402


def tipos(fonte):
    return [t.tipo for t in analisar(fonte)]


class TestValidos(unittest.TestCase):
    def test_declaracao(self):
        self.assertEqual(
            tipos("seja n :: inteiro = 5;"),
            [T.SEJA, T.IDENT, T.TIPO, T.INTEIRO, T.ATRIB, T.LIT_INTEIRO,
             T.PONTO_VIRGULA, T.EOF],
        )

    def test_palavra_reservada_vs_identificador(self):
        toks = analisar("se senao sena seja2")
        self.assertEqual([t.tipo for t in toks[:-1]], [T.SE, T.SENAO, T.IDENT, T.IDENT])

    def test_literais(self):
        toks = analisar('35 3.14 "olá" verdadeiro falso')
        self.assertEqual(toks[0].valor, 35)
        self.assertEqual(toks[1].valor, 3.14)
        self.assertEqual(toks[2].valor, "olá")
        self.assertEqual([t.tipo for t in toks[3:5]], [T.VERDADEIRO, T.FALSO])

    def test_escapes_em_texto(self):
        self.assertEqual(analisar(r'"a\n\"b\""')[0].valor, 'a\n"b"')

    def test_operadores_de_dois_caracteres(self):
        self.assertEqual(
            tipos("== != <= >= :: = < >")[:-1],
            [T.IGUAL, T.DIFERENTE, T.MENOR_IGUAL, T.MAIOR_IGUAL, T.TIPO,
             T.ATRIB, T.MENOR, T.MAIOR],
        )

    def test_delimitadores(self):
        self.assertEqual(
            tipos("; , ( ) { } [ ] .")[:-1],
            [T.PONTO_VIRGULA, T.VIRGULA, T.ABRE_PAR, T.FECHA_PAR, T.ABRE_CHAVE,
             T.FECHA_CHAVE, T.ABRE_COL, T.FECHA_COL, T.PONTO],
        )

    def test_ponto_de_campo_nao_vira_real(self):
        self.assertEqual(tipos("aluno.nota")[:-1], [T.IDENT, T.PONTO, T.IDENT])

    def test_array_com_tamanho(self):
        self.assertEqual(
            tipos("[inteiro; 3]")[:-1],
            [T.ABRE_COL, T.INTEIRO, T.PONTO_VIRGULA, T.LIT_INTEIRO, T.FECHA_COL],
        )

    def test_comentario_ignorado(self):
        self.assertEqual(tipos("# nada aqui\nmostre(1); # fim")[:-1],
                         [T.MOSTRE, T.ABRE_PAR, T.LIT_INTEIRO, T.FECHA_PAR,
                          T.PONTO_VIRGULA])

    def test_linha_e_coluna(self):
        toks = analisar("seja x :: inteiro = 1;\n  mostre(x);")
        mostre = [t for t in toks if t.tipo == T.MOSTRE][0]
        self.assertEqual((mostre.linha, mostre.coluna), (2, 3))

    def test_programas_validos_da_pasta(self):
        for nome in ["exemplo_valido", "declaracao", "aritmetica",
                     "condicao", "repeticao"]:
            with self.subTest(programa=nome):
                fonte = (RAIZ / "programas" / f"{nome}.redc").read_text("utf-8")
                self.assertEqual(analisar(fonte)[-1].tipo, T.EOF)


class TestErros(unittest.TestCase):
    def assertErro(self, fonte, linha, coluna, trecho):
        with self.assertRaises(ErroLexico) as ctx:
            analisar(fonte)
        erro = ctx.exception
        self.assertEqual((erro.linha, erro.coluna), (linha, coluna))
        self.assertIn(trecho, erro.mensagem)

    def test_caractere_invalido(self):
        self.assertErro("seja x :: inteiro = 1 @ 2;", 1, 23, "'@'")

    def test_dois_pontos_sozinho(self):
        self.assertErro("seja n : inteiro = 5;", 1, 8, "'::'")

    def test_exclamacao_sozinha(self):
        self.assertErro("se (!ok) {}", 1, 5, "nao")

    def test_texto_sem_fechamento(self):
        self.assertErro('mostre("olá);', 1, 8, "aspas")

    def test_texto_com_quebra_de_linha(self):
        self.assertErro('mostre("olá\n");', 1, 8, "aspas")

    def test_escape_invalido(self):
        self.assertErro(r'"a\q"', 1, 3, "escape")

    def test_numero_malformado(self):
        self.assertErro("seja x :: inteiro = 12abc;", 1, 21, "malformado")

    def test_acento_em_identificador(self):
        self.assertErro("senão", 1, 4, "acentuado")


if __name__ == "__main__":
    unittest.main()
