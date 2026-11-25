"""
Testes dos recursos de estruturas de dados e controle (diário #19):
escolha/caso/padrao, para cada, arrays, listas, registros e as funções
nativas tamanho() e adicione().

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
from errors import CompilacaoErro, ErroExecucao, ErroSemantico, ErroSintatico  # noqa: E402
from redc_ast import Escolha, ParaCada, TipoColecao, TipoRegistro  # noqa: E402

PONTO = "registro Ponto { x :: inteiro; y :: inteiro; }\n"


def rodar(fonte, **opcoes) -> list[str]:
    arvore = parser.analisar(lexer.analisar(fonte))
    semantic.analisar(arvore)
    saida = []
    vm.executar(codegen.gerar(arvore), escrever=saida.append, **opcoes)
    return saida


class Erros(unittest.TestCase):
    def assertErro(self, classe, fonte, linha, coluna, trecho):
        with self.assertRaises(CompilacaoErro) as ctx:
            rodar(fonte)
        erro = ctx.exception
        self.assertIsInstance(erro, classe, str(erro))
        self.assertEqual((erro.linha, erro.coluna), (linha, coluna), erro.mensagem)
        self.assertIn(trecho, erro.mensagem)


# ---------------------------------------------------------------- escolha

class TestEscolha(Erros):
    def test_caso_padrao_e_sem_fallthrough(self):
        prog = """
            funcao f(n :: inteiro) :: texto {
                escolha (n) {
                    caso 1 { retorne "um"; }
                    caso 2, 3 { retorne "dois ou três"; }
                    padrao { retorne "outro"; }
                }
            }
            mostre(f(1)); mostre(f(3)); mostre(f(9));
            escolha (2) { caso 2 { mostre("só este"); } caso 3 { mostre("não"); } }
        """
        self.assertEqual(rodar(prog), ["um", "dois ou três", "outro", "só este"])

    def test_sem_padrao_e_nenhum_caso(self):
        self.assertEqual(rodar('escolha (5) { caso 1 { mostre("x"); } }\nmostre("fim");'),
                         ["fim"])

    def test_texto_e_negativo(self):
        self.assertEqual(rodar('escolha ("b") { caso "a" { mostre(1); } caso "b" { mostre(2); } }'),
                         ["2"])
        self.assertEqual(rodar("escolha (-1) { caso -1 { mostre(1); } }"), ["1"])

    def test_valor_calculado_uma_vez(self):
        prog = """
            funcao conta(n :: inteiro) :: inteiro { mostre("calculou"); retorne n; }
            escolha (conta(3)) { caso 1 { } caso 2 { } caso 3 { mostre("três"); } }
        """
        self.assertEqual(rodar(prog), ["calculou", "três"])

    def test_escopo_de_cada_caso(self):
        rodar("escolha (1) { caso 1 { seja x :: inteiro = 1; } caso 2 { seja x :: texto = \"a\"; } }")

    def test_retorne_em_todos_os_casos_com_padrao(self):
        self.assertEqual(rodar("""
            funcao f(n :: inteiro) :: inteiro {
                escolha (n) { caso 1 { retorne 10; } padrao { retorne 0; } }
            }
            mostre(f(1)); mostre(f(2));"""), ["10", "0"])

    def test_ast(self):
        arvore = parser.analisar(lexer.analisar("escolha (1) { caso 1, 2 { } padrao { } }"))
        no = arvore.comandos[0]
        self.assertIsInstance(no, Escolha)
        self.assertEqual([v.valor for v in no.casos[0].valores], [1, 2])
        self.assertIsNotNone(no.padrao)

    # erros
    def test_tipo_da_escolha(self):
        self.assertErro(ErroSemantico, "escolha (1.5) { caso 1 { } }", 1, 10,
                        "inteiro ou texto, recebido real")

    def test_caso_de_outro_tipo(self):
        self.assertErro(ErroSemantico, 'escolha (1) { caso "a" { } }', 1, 20,
                        "caso do tipo texto em uma 'escolha' de inteiro")

    def test_caso_repetido(self):
        self.assertErro(ErroSemantico, "escolha (1) { caso 1 { } caso 2, 1 { } }", 1, 34,
                        "o caso 1 já apareceu na linha 1")

    def test_caso_com_variavel(self):
        self.assertErro(ErroSintatico, "seja a :: inteiro = 1;\nescolha (1) { caso a { } }",
                        2, 20, "número inteiro ou um texto fixo")

    def test_padrao_antes_de_caso(self):
        self.assertErro(ErroSintatico, "escolha (1) { padrao { } caso 1 { } }", 1, 26,
                        "precisa ser o último")

    def test_padrao_repetido(self):
        self.assertErro(ErroSintatico, "escolha (1) { caso 1 { } padrao { } padrao { } }",
                        1, 37, "'padrao' repetido")

    def test_comando_solto_na_escolha(self):
        self.assertErro(ErroSintatico, "escolha (1) { mostre(1); }", 1, 15,
                        "esperado 'caso' ou 'padrao'")

    def test_caso_fora_de_escolha(self):
        self.assertErro(ErroSintatico, "caso 1 { }", 1, 1, "só pode aparecer dentro de 'escolha'")

    def test_sem_padrao_nao_garante_retorno(self):
        self.assertErro(ErroSemantico,
                        "funcao f(n :: inteiro) :: inteiro { escolha (n) { caso 1 { retorne 1; } } }",
                        1, 1, "pode terminar sem 'retorne'")


# ---------------------------------------------------------------- para cada

class TestParaCada(Erros):
    def test_percorre_lista_e_array(self):
        self.assertEqual(rodar("""
            seja l :: [texto] = ["a", "b"];
            para cada x em l { mostre(x); }
            seja v :: [inteiro; 3] = [1, 2, 3];
            para cada n em v { mostre(n * 10); }"""), ["a", "b", "10", "20", "30"])

    def test_literal_e_matriz(self):
        self.assertEqual(rodar("""
            seja s :: inteiro = 0;
            para cada linha em [[1, 2], [3, 4]] { para cada x em linha { s = s + x; } }
            mostre(s);"""), ["10"])

    def test_tamanho_lido_no_inicio(self):
        # Acrescentar à lista dentro do laço não faz o laço ser infinito.
        self.assertEqual(rodar("""
            seja l :: [inteiro] = [1, 2];
            para cada x em l { adicione(l, x); }
            mostre(l);"""), ["[1, 2, 1, 2]"])

    def test_lista_vazia_nao_executa(self):
        self.assertEqual(rodar("seja l :: [inteiro] = [];\npara cada x em l { mostre(x); }\nmostre(\"fim\");"),
                         ["fim"])

    def test_variavel_do_laco_em_escopo_proprio(self):
        tabela = semantic.analisar(parser.analisar(lexer.analisar("para cada x em [1] { }")))
        escopo = tabela.todos[-1]
        self.assertTrue(escopo.nome.startswith("para cada"))
        self.assertEqual(escopo.simbolos["x"].tipo, "inteiro")

    def test_ast(self):
        no = parser.analisar(lexer.analisar("para cada x em l { }")).comandos[0]
        self.assertIsInstance(no, ParaCada)
        self.assertEqual(no.variavel, "x")

    # erros
    def test_colecao_invalida(self):
        self.assertErro(ErroSemantico, "para cada x em 5 { }", 1, 16,
                        "percorre arrays e listas, recebido inteiro")

    def test_lista_vazia_literal(self):
        self.assertErro(ErroSemantico, "para cada x em [] { }", 1, 16, "lista vazia sem tipo")

    def test_sem_cada(self):
        self.assertErro(ErroSintatico, "para x em [1] { }", 1, 6, "esperado 'cada'")

    def test_variavel_nao_existe_depois(self):
        self.assertErro(ErroSemantico, "para cada x em [1] { }\nmostre(x);", 2, 8,
                        "'x' não foi declarada")

    def test_redeclarar_variavel_do_laco(self):
        self.assertErro(ErroSemantico, "para cada x em [1] { seja x :: inteiro = 2; }", 1, 22,
                        "já foi declarado")


# ---------------------------------------------------------------- arrays e listas

class TestColecoes(Erros):
    def test_array_indice_e_atribuicao(self):
        self.assertEqual(rodar("seja v :: [inteiro; 3] = [1, 2, 3];\nv[0] = v[1] + v[2];\nmostre(v);"),
                         ["[5, 2, 3]"])

    def test_lista_adicione_e_tamanho(self):
        self.assertEqual(rodar("""
            seja l :: [inteiro] = [];
            mostre(adicione(l, 7)); adicione(l, 8);
            mostre(l); mostre(tamanho(l)); mostre(tamanho("olá"));"""),
            ["1", "[7, 8]", "2", "3"])

    def test_promocao_nos_elementos(self):
        self.assertEqual(rodar("seja r :: [real] = [1, 2];\nadicione(r, 3);\nmostre(r);"),
                         ["[1.0, 2.0, 3.0]"])
        self.assertEqual(rodar("mostre([1, 2.5]);"), ["[1.0, 2.5]"])

    def test_matriz(self):
        self.assertEqual(rodar("""
            seja m :: [[inteiro; 2]; 2] = [[1, 2], [3, 4]];
            m[1][0] = 9;
            mostre(m); mostre(m[1][0] * 2);"""), ["[[1, 2], [9, 4]]", "18"])

    def test_lista_de_listas_com_tamanhos_diferentes(self):
        self.assertEqual(rodar("seja t :: [[inteiro]] = [[1], [2, 3]];\nmostre(t);"),
                         ["[[1], [2, 3]]"])

    def test_passagem_por_referencia(self):
        self.assertEqual(rodar("""
            funcao zera(v :: [inteiro; 2]) :: inteiro { v[0] = 0; retorne 0; }
            seja a :: [inteiro; 2] = [5, 6];
            seja b :: [inteiro; 2] = a;
            b[1] = 7;
            zera(a);
            mostre(a);"""), ["[0, 7]"])

    def test_funcao_que_devolve_lista(self):
        self.assertEqual(rodar("""
            funcao ate(n :: inteiro) :: [inteiro] {
                seja l :: [inteiro] = [];
                seja i :: inteiro = 1;
                enquanto (i <= n) { adicione(l, i); i = i + 1; }
                retorne l;
            }
            mostre(ate(3)); mostre(ate(4)[3]);"""), ["[1, 2, 3]", "4"])

    def test_tipos(self):
        tipo = parser.analisar(lexer.analisar("seja m :: [[real; 2]] = [];")).comandos[0].tipo
        self.assertEqual(tipo, TipoColecao(TipoColecao("real", 2)))
        self.assertEqual(str(tipo), "[[real; 2]]")

    # erros de compilação
    def test_array_tamanho_diferente(self):
        self.assertErro(ErroSemantico, "seja v :: [inteiro; 3] = [1, 2];", 1, 26,
                        "o array tem 3 posição(ões), e o valor tem 2 elemento(s)")

    def test_array_tamanho_zero(self):
        self.assertErro(ErroSemantico, "seja v :: [inteiro; 0] = [];", 1, 1,
                        "tamanho maior que zero")

    def test_indice_constante_fora_do_array(self):
        self.assertErro(ErroSemantico, "seja v :: [inteiro; 3] = [1, 2, 3];\nmostre(v[3]);",
                        2, 10, "índice 3 fora dos limites: o array tem 3 elemento(s), de 0 a 2")

    def test_indice_negativo(self):
        self.assertErro(ErroSemantico, "seja l :: [inteiro] = [1];\nmostre(l[-1]);",
                        2, 10, "índice negativo")

    def test_indice_nao_inteiro(self):
        self.assertErro(ErroSemantico, "seja l :: [inteiro] = [1];\nmostre(l[1.0]);",
                        2, 10, "o índice precisa ser inteiro")

    def test_adicione_em_array(self):
        self.assertErro(ErroSemantico, "seja v :: [inteiro; 1] = [1];\nadicione(v, 2);",
                        2, 10, "arrays têm tamanho fixo")

    def test_adicione_tipo_errado(self):
        self.assertErro(ErroSemantico, 'seja l :: [inteiro] = [];\nadicione(l, "x");',
                        2, 13, "a lista guarda inteiro, recebido texto")

    def test_lista_em_array(self):
        self.assertErro(ErroSemantico, "seja l :: [inteiro] = [1];\nseja v :: [inteiro; 1] = l;",
                        2, 26, "array e lista são tipos diferentes")

    def test_lista_de_inteiro_em_lista_de_real(self):
        self.assertErro(ErroSemantico, "seja l :: [inteiro] = [1];\nseja r :: [real] = l;",
                        2, 20, "esperado [real], recebido [inteiro]")

    def test_elementos_misturados(self):
        self.assertErro(ErroSemantico, 'mostre([1, "a"]);', 1, 12,
                        "elementos de tipos diferentes")

    def test_matriz_com_linha_curta(self):
        self.assertErro(ErroSemantico, "seja m :: [[inteiro; 2]; 2] = [[1, 2], [3]];", 1, 31,
                        "esperado [[inteiro; 2]; 2]")

    def test_indexar_numero(self):
        self.assertErro(ErroSemantico, "seja n :: inteiro = 1;\nmostre(n[0]);", 2, 9,
                        "só arrays e listas")

    def test_comparar_listas(self):
        self.assertErro(ErroSemantico, "seja a :: [inteiro] = [1];\nmostre(a == a);", 2, 10,
                        "não compara arrays, listas ou registros")

    def test_redeclarar_nativa(self):
        self.assertErro(ErroSemantico, "seja tamanho :: inteiro = 1;", 1, 1,
                        "função nativa")

    def test_tamanho_de_numero(self):
        self.assertErro(ErroSemantico, "mostre(tamanho(5));", 1, 16,
                        "arrays, listas e textos")

    # erros de execução
    def test_indice_fora_em_execucao(self):
        self.assertErro(ErroExecucao, "seja l :: [inteiro] = [1, 2];\nseja i :: inteiro = 2;\nmostre(l[i]);",
                        3, 9, "índice 2 fora dos limites (tamanho 2, índices de 0 a 1)")

    def test_atribuir_fora_em_execucao(self):
        self.assertErro(ErroExecucao, "seja l :: [inteiro] = [];\nseja i :: inteiro = 0;\nl[i] = 1;",
                        3, 2, "a coleção está vazia")


# ---------------------------------------------------------------- texto()

class TestConversaoTexto(Erros):
    """texto(valor): conversão explícita para texto (diário #21)."""

    def test_converte_cada_tipo_basico(self):
        self.assertEqual(rodar('mostre(texto(10)); mostre(texto(2.5)); mostre(texto(falso)); '
                               'mostre(texto("já é texto"));'),
                         ["10", "2.5", "falso", "já é texto"])

    def test_junta_texto_e_numero(self):
        self.assertEqual(rodar('seja n :: inteiro = 3;\nmostre("faltas: " + texto(n));'),
                         ["faltas: 3"])

    def test_mesmo_formato_do_mostre(self):
        self.assertEqual(rodar("mostre(texto(7 / 2.0)); mostre(texto(7 / 2)); "
                               "seja r :: real = 5; mostre(texto(r));"),
                         ["3.5", "3", "5.0"])

    def test_resultado_e_texto(self):
        self.assertEqual(rodar("mostre(tamanho(texto(12345)));"), ["5"])

    def test_gera_to_text(self):
        arvore = parser.analisar(lexer.analisar("mostre(texto(1));"))
        semantic.analisar(arvore)
        self.assertIn("TO_TEXT", [i.op for i in codegen.gerar(arvore).instrucoes])

    def test_dica_no_erro_do_mais(self):
        self.assertErro(ErroSemantico, 'mostre("total: " + 10);', 1, 18,
                        "converta com texto(...)")

    def test_sem_parenteses(self):
        self.assertErro(ErroSintatico, "mostre(texto);", 1, 13, "a conversão é texto(valor)")

    def test_numero_de_argumentos(self):
        self.assertErro(ErroSemantico, "mostre(texto(1, 2));", 1, 8,
                        "'texto' espera 1 argumento(s), recebeu 2")

    def test_colecao_nao_converte(self):
        self.assertErro(ErroSemantico, "mostre(texto([1, 2]));", 1, 14,
                        "converte inteiro, real e logico, recebido [inteiro]")

    def test_resultado_nao_cabe_em_inteiro(self):
        self.assertErro(ErroSemantico, "seja t :: inteiro = texto(5);", 1, 21,
                        "esperado inteiro, recebido texto")


# ---------------------------------------------------------------- registros

class TestRegistros(Erros):
    def test_criar_ler_e_alterar(self):
        self.assertEqual(rodar(PONTO + """
            seja p :: Ponto = Ponto(1, 2);
            p.x = p.x + 10;
            mostre(p.x); mostre(p);"""), ["11", "Ponto(x: 11, y: 2)"])

    def test_registro_com_lista_e_lista_de_registros(self):
        self.assertEqual(rodar("""
            registro Aluno { nome :: texto; notas :: [real]; }
            seja t :: [Aluno] = [Aluno("Ana", [9]), Aluno("Bia", [])];
            adicione(t[1].notas, 7.5);
            t[0].nome = "Ana Maria";
            mostre(t);"""),
            ['[Aluno(nome: "Ana Maria", notas: [9.0]), Aluno(nome: "Bia", notas: [7.5])]'])

    def test_registro_usa_registro_declarado_depois(self):
        self.assertEqual(rodar("""
            registro Linha { a :: Ponto; b :: Ponto; }
            registro Ponto { x :: inteiro; y :: inteiro; }
            seja l :: Linha = Linha(Ponto(0, 0), Ponto(3, 4));
            mostre(l.b.y);"""), ["4"])

    def test_estrutura_recursiva_por_lista(self):
        self.assertEqual(rodar("""
            registro No { valor :: inteiro; filhos :: [No]; }
            funcao soma(n :: No) :: inteiro {
                seja s :: inteiro = n.valor;
                para cada f em n.filhos { s = s + soma(f); }
                retorne s;
            }
            seja arvore :: No = No(1, [No(2, []), No(3, [No(4, [])])]);
            mostre(soma(arvore));"""), ["10"])

    def test_referencia(self):
        self.assertEqual(rodar(PONTO + """
            funcao move(p :: Ponto) :: inteiro { p.x = 99; retorne 0; }
            seja a :: Ponto = Ponto(1, 1);
            move(a);
            mostre(a.x);"""), ["99"])

    def test_tabela_de_simbolos(self):
        tabela = semantic.analisar(parser.analisar(lexer.analisar(PONTO)))
        ponto = tabela.buscar("Ponto")
        self.assertEqual(ponto.categoria, "registro")
        self.assertEqual(ponto.assinatura(), "{x :: inteiro; y :: inteiro}")
        self.assertEqual(ponto.tipo, TipoRegistro("Ponto"))

    # erros
    def test_tipo_inexistente(self):
        self.assertErro(ErroSemantico, "seja a :: Alnuo = 1;", 1, 11, "o tipo 'Alnuo' não existe")

    def test_campo_inexistente(self):
        self.assertErro(ErroSemantico, PONTO + "seja p :: Ponto = Ponto(1, 2);\nmostre(p.z);",
                        3, 9, "não tem o campo 'z' (campos: x, y)")

    def test_campo_repetido(self):
        self.assertErro(ErroSemantico, "registro Q { a :: inteiro; a :: real; }", 1, 28,
                        "aparece duas vezes")

    def test_registro_vazio(self):
        self.assertErro(ErroSintatico, "registro Q { }", 1, 10, "pelo menos um campo")

    def test_ciclo(self):
        self.assertErro(ErroSemantico, "registro A { b :: B; }\nregistro B { a :: A; }", 1, 1,
                        "contém a si mesmo (A → B → A)")

    def test_numero_de_campos(self):
        self.assertErro(ErroSemantico, PONTO + "seja p :: Ponto = Ponto(1);", 2, 19,
                        "tem 2 campo(s), recebeu 1")

    def test_tipo_de_campo_na_criacao(self):
        self.assertErro(ErroSemantico, PONTO + 'seja p :: Ponto = Ponto(1, "2");', 2, 28,
                        "campo 'y' de 'Ponto': esperado inteiro, recebido texto")

    def test_atribuir_campo_com_tipo_errado(self):
        self.assertErro(ErroSemantico, PONTO + 'seja p :: Ponto = Ponto(1, 2);\np.x = "a";',
                        3, 7, "esperado inteiro, recebido texto")

    def test_registro_usado_como_variavel(self):
        self.assertErro(ErroSemantico, PONTO + "mostre(Ponto);", 2, 8, "é um registro")

    def test_campo_de_numero(self):
        self.assertErro(ErroSemantico, "seja n :: inteiro = 1;\nmostre(n.x);", 2, 9,
                        "só funciona com registros")

    def test_registro_dentro_de_bloco(self):
        self.assertErro(ErroSintatico, "se (verdadeiro) { registro Q { a :: inteiro; } }", 1, 19,
                        "fora de blocos")


if __name__ == "__main__":
    unittest.main()
