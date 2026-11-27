"""
Catálogo dos programas de teste em programas/: o que cada um verifica e a
saída exata esperada ao rodar 'python compiler.py programas/<arquivo>'.

Usado por testes/test_integracao.py e por gerar_resultados.py.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Caso:
    arquivo: str
    categoria: str
    obrigatorio: str | None   # item da seção 8 do edital que o caso cobre
    saida: tuple[str, ...]    # linhas esperadas na saída
    codigo: int = 0           # código de saída do processo (0 = sucesso, 1 = erro)


CASOS = (
    # ---------- programas válidos ----------
    Caso("declaracao.redc", "Válido: declaração e atribuição",
         "programa válido com declaração e atribuição",
         ("Ana",)),
    Caso("aritmetica.redc", "Válido: operações aritméticas",
         "programa válido com operações aritméticas",
         ("13", "7", "30", "3", "1", "26")),
    Caso("condicao.redc", "Válido: condição (se / senao se / senao)",
         "programa válido com condição",
         ("aprovado",)),
    Caso("repeticao.redc", "Válido: repetição (enquanto)",
         "programa válido com repetição",
         ("120",)),
    Caso("exemplo_valido.redc", "Válido: funções e recursão", None,
         ("8.25", "aprovado", "120")),
    Caso("escopos.redc", "Válido: escopos e sombreamento", None,
         ("sombreia o limite global", "6")),
    Caso("escolha.redc", "Válido: escolha / caso / padrao", None,
         ("fim de semana", "segunda", "meio da semana", "parado")),
    Caso("listas.redc", "Válido: listas, para cada, tamanho e adicione", None,
         ("[7.5, 8.0, 5.5, 9.0]", "4", "7.5", '["Ana", "Bia", "Davi"]')),
    Caso("arrays.redc", "Válido: arrays e matriz", None,
         ("[10, 40, 30]", "[[1, 2, 3], [4, 5, 6]]", "21", "6")),
    Caso("conversao.redc", "Válido: conversão explícita com texto()", None,
         ("Ana tirou 8.5 com 3 faltas", "aprovado: verdadeiro")),
    Caso("registros.redc", "Válido: registros", None,
         ('Aluno(nome: "Ana", notas: [8.0, 9.5, 10.0])', "Ana", "9.166666666666666",
          "Ana", "Beatriz")),
    Caso("meu_programa.redc",
         "Válido: programa completo com função, lista, condição e repetição", None,
         ("Ana tem media 8.333333333333334", "aprovada",
          "contagem: 3", "contagem: 2", "contagem: 1")),

    # ---------- programas com erro ----------
    Caso("exemplo_invalido.redc", "Erro léxico: caractere inválido",
         "exemplo com erro léxico",
         ("exemplo_invalido.redc: Erro léxico (linha 3, coluna 30): caractere inválido '@'",),
         1),
    Caso("erro_lexico_dois_pontos.redc", "Erro léxico: ':' sozinho", None,
         ("erro_lexico_dois_pontos.redc: Erro léxico (linha 2, coluna 8): "
          "':' sozinho não existe; para tipo use '::'",),
         1),
    Caso("erro_lexico_texto.redc", "Erro léxico: texto sem fechamento", None,
         ("erro_lexico_texto.redc: Erro léxico (linha 2, coluna 8): "
          "texto sem aspas de fechamento",),
         1),
    Caso("erro_sintatico.redc", "Erro sintático: ';' ausente",
         "exemplo com erro sintático",
         ("erro_sintatico.redc: Erro sintático (linha 2, coluna 22): "
          "esperado ';' no fim do comando",),
         1),
    Caso("erro_semantico.redc", "Erro semântico: variável não declarada",
         "exemplo com erro semântico",
         ("erro_semantico.redc: Erro semântico (linha 3, coluna 8): "
          "'totl' não foi declarada",),
         1),
    Caso("erro_tipo.redc", "Erro semântico: tipo incompatível", None,
         ("erro_tipo.redc: Erro semântico (linha 2, coluna 25): "
          "esperado inteiro, recebido texto",),
         1),
    Caso("erro_array.redc", "Erro semântico: tamanho do array", None,
         ("erro_array.redc: Erro semântico (linha 2, coluna 26): esperado [inteiro; 3], "
          "recebido [inteiro] (o array tem 3 posição(ões), e o valor tem 2 elemento(s))",),
         1),
    Caso("erro_indice.redc", "Erro de execução: índice fora dos limites", None,
         ("erro_indice.redc: Erro de execução (linha 4, coluna 12): "
          "índice 2 fora dos limites (tamanho 2, índices de 0 a 1)",),
         1),
    Caso("erro_execucao.redc", "Erro de execução: divisão por zero", None,
         ("antes da divisão",
          "erro_execucao.redc: Erro de execução (linha 5, coluna 14): divisão por zero"),
         1),
)
