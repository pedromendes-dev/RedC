# RedC — Resultados da execução do compilador

Gerado em 15/11/2026 20:15 com Python 3.13.18 (Linux), pelo comando `python gerar_resultados.py`.

## Resumo

| Verificação | Resultado |
| --- | --- |
| Testes automatizados (`python -m unittest discover -s testes`) | 213 de 213 passando |
| Programas de teste com a saída esperada | 20 de 20 |

## Programas de teste

| Programa | O que verifica | Teste obrigatório do edital | Resultado |
| --- | --- | --- | --- |
| `declaracao.redc` | Válido: declaração e atribuição | programa válido com declaração e atribuição | OK |
| `aritmetica.redc` | Válido: operações aritméticas | programa válido com operações aritméticas | OK |
| `condicao.redc` | Válido: condição (se / senao se / senao) | programa válido com condição | OK |
| `repeticao.redc` | Válido: repetição (enquanto) | programa válido com repetição | OK |
| `exemplo_valido.redc` | Válido: funções e recursão | — | OK |
| `escopos.redc` | Válido: escopos e sombreamento | — | OK |
| `escolha.redc` | Válido: escolha / caso / padrao | — | OK |
| `listas.redc` | Válido: listas, para cada, tamanho e adicione | — | OK |
| `arrays.redc` | Válido: arrays e matriz | — | OK |
| `conversao.redc` | Válido: conversão explícita com texto() | — | OK |
| `registros.redc` | Válido: registros | — | OK |
| `exemplo_invalido.redc` | Erro léxico: caractere inválido | exemplo com erro léxico | OK |
| `erro_lexico_dois_pontos.redc` | Erro léxico: ':' sozinho | — | OK |
| `erro_lexico_texto.redc` | Erro léxico: texto sem fechamento | — | OK |
| `erro_sintatico.redc` | Erro sintático: ';' ausente | exemplo com erro sintático | OK |
| `erro_semantico.redc` | Erro semântico: variável não declarada | exemplo com erro semântico | OK |
| `erro_tipo.redc` | Erro semântico: tipo incompatível | — | OK |
| `erro_array.redc` | Erro semântico: tamanho do array | — | OK |
| `erro_indice.redc` | Erro de execução: índice fora dos limites | — | OK |
| `erro_execucao.redc` | Erro de execução: divisão por zero | — | OK |

### declaracao.redc — Válido: declaração e atribuição

```
# declaração e atribuição
seja idade :: inteiro = 35;
seja nome :: texto = "Ana";
seja altura :: real = 1.68;
seja ativo :: logico = verdadeiro;
idade = idade + 1;
mostre(nome);
```

`python compiler.py programas/declaracao.redc`

```
Ana
```

### aritmetica.redc — Válido: operações aritméticas

```
# operações aritméticas
seja a :: inteiro = 10;
seja b :: inteiro = 3;
mostre(a + b);
mostre(a - b);
mostre(a * b);
mostre(a / b);
mostre(a % b);
mostre((a + b) * 2);
```

`python compiler.py programas/aritmetica.redc`

```
13
7
30
3
1
26
```

### condicao.redc — Válido: condição (se / senao se / senao)

```
# condição com se / senao se / senao
seja nota :: real = 8.5;
se (nota >= 7.0 e nota <= 10.0) {
    mostre("aprovado");
} senao se (nota >= 5.0) {
    mostre("recuperação");
} senao {
    mostre("reprovado");
}
```

`python compiler.py programas/condicao.redc`

```
aprovado
```

### repeticao.redc — Válido: repetição (enquanto)

```
# fatorial com enquanto
seja n :: inteiro = 5;
seja fat :: inteiro = 1;
enquanto (n > 1) {
    fat = fat * n;
    n = n - 1;
}
mostre(fat);
```

`python compiler.py programas/repeticao.redc`

```
120
```

### exemplo_valido.redc — Válido: funções e recursão

```
# situação de um aluno, com funções e recursão
funcao media(a :: real, b :: real) :: real {
    retorne (a + b) / 2.0;
}

funcao fatorial(n :: inteiro) :: inteiro {
    se (n <= 1) {
        retorne 1;
    }
    retorne n * fatorial(n - 1);
}

seja m :: real = media(7.5, 9.0);
mostre(m);

se (m >= 7.0) {
    mostre("aprovado");
} senao se (m >= 5.0) {
    mostre("recuperação");
} senao {
    mostre("reprovado");
}

mostre(fatorial(5));
```

`python compiler.py programas/exemplo_valido.redc`

```
8.25
aprovado
120
```

### escopos.redc — Válido: escopos e sombreamento

```
# escopos: global, função e blocos aninhados
funcao dobro(x :: inteiro) :: inteiro {
    seja resultado :: inteiro = x * 2;
    retorne resultado;
}

seja limite :: inteiro = 3;
seja i :: inteiro = 0;
enquanto (i < limite) {
    seja quadrado :: inteiro = i * i;
    se (quadrado > 1) {
        seja limite :: texto = "sombreia o limite global";
        mostre(limite);
    }
    i = i + 1;
}
mostre(dobro(limite));
```

`python compiler.py programas/escopos.redc`

```
sombreia o limite global
6
```

### escolha.redc — Válido: escolha / caso / padrao

```
# escolha / caso / padrao: o switch da RedC, sem fallthrough
funcao nome_do_dia(dia :: inteiro) :: texto {
    escolha (dia) {
        caso 1, 7 { retorne "fim de semana"; }
        caso 2 { retorne "segunda"; }
        caso 6 { retorne "sexta"; }
        padrao { retorne "meio da semana"; }
    }
}

mostre(nome_do_dia(1));
mostre(nome_do_dia(2));
mostre(nome_do_dia(4));

seja comando :: texto = "parar";
escolha (comando) {
    caso "andar" { mostre("andando"); }
    caso "parar" { mostre("parado"); }
}
```

`python compiler.py programas/escolha.redc`

```
fim de semana
segunda
meio da semana
parado
```

### listas.redc — Válido: listas, para cada, tamanho e adicione

```
# lista (tamanho variável), para cada e funções nativas
funcao media(notas :: [real]) :: real {
    seja soma :: real = 0.0;
    para cada nota em notas {
        soma = soma + nota;
    }
    retorne soma / tamanho(notas);
}

seja turma :: [real] = [7.5, 8.0, 5.5];
adicione(turma, 9);
mostre(turma);
mostre(tamanho(turma));
mostre(media(turma));

seja aprovados :: [texto] = [];
seja nomes :: [texto] = ["Ana", "Bia", "Caio", "Davi"];
seja i :: inteiro = 0;
para cada nome em nomes {
    se (turma[i] >= 7.0) {
        adicione(aprovados, nome);
    }
    i = i + 1;
}
mostre(aprovados);
```

`python compiler.py programas/listas.redc`

```
[7.5, 8.0, 5.5, 9.0]
4
7.5
["Ana", "Bia", "Davi"]
```

### arrays.redc — Válido: arrays e matriz

```
# array (tamanho fixo) e matriz
seja v :: [inteiro; 3] = [10, 20, 30];
v[1] = v[0] + v[2];
mostre(v);

# matriz 2x3: array de arrays
seja m :: [[inteiro; 3]; 2] = [[1, 2, 3], [4, 5, 6]];
seja soma :: inteiro = 0;
para cada linha em m {
    para cada x em linha {
        soma = soma + x;
    }
}
mostre(m);
mostre(soma);
mostre(m[1][2]);
```

`python compiler.py programas/arrays.redc`

```
[10, 40, 30]
[[1, 2, 3], [4, 5, 6]]
21
6
```

### conversao.redc — Válido: conversão explícita com texto()

```
# conversão explícita para texto com texto(valor)
seja nome :: texto = "Ana";
seja nota :: real = 8.5;
seja faltas :: inteiro = 3;
seja aprovado :: logico = nota >= 7.0 e faltas < 10;
mostre(nome + " tirou " + texto(nota) + " com " + texto(faltas) + " faltas");
mostre("aprovado: " + texto(aprovado));
```

`python compiler.py programas/conversao.redc`

```
Ana tirou 8.5 com 3 faltas
aprovado: verdadeiro
```

### registros.redc — Válido: registros

```
# registro: um tipo criado pelo programador
registro Aluno {
    nome :: texto;
    notas :: [real];
}

funcao media(a :: Aluno) :: real {
    seja soma :: real = 0.0;
    para cada n em a.notas {
        soma = soma + n;
    }
    retorne soma / tamanho(a.notas);
}

seja ana :: Aluno = Aluno("Ana", [8.0, 9.5]);
adicione(ana.notas, 10);
mostre(ana);
mostre(ana.nome);
mostre(media(ana));

seja turma :: [Aluno] = [ana, Aluno("Bia", [6.0])];
turma[1].nome = "Beatriz";
para cada aluno em turma {
    mostre(aluno.nome);
}
```

`python compiler.py programas/registros.redc`

```
Aluno(nome: "Ana", notas: [8.0, 9.5, 10.0])
Ana
9.166666666666666
Ana
Beatriz
```

### exemplo_invalido.redc — Erro léxico: caractere inválido

```
# erro léxico: '@' não pertence à RedC
seja total :: inteiro = 10;
seja taxa :: inteiro = total @ 2;
```

`python compiler.py programas/exemplo_invalido.redc`

```
exemplo_invalido.redc: Erro léxico (linha 3, coluna 30): caractere inválido '@'
```

### erro_lexico_dois_pontos.redc — Erro léxico: ':' sozinho

```
# erro léxico: ':' sozinho (o tipo usa '::')
seja n : inteiro = 5;
```

`python compiler.py programas/erro_lexico_dois_pontos.redc`

```
erro_lexico_dois_pontos.redc: Erro léxico (linha 2, coluna 8): ':' sozinho não existe; para tipo use '::'
```

### erro_lexico_texto.redc — Erro léxico: texto sem fechamento

```
# erro léxico: texto sem aspas de fechamento
mostre("olá);
```

`python compiler.py programas/erro_lexico_texto.redc`

```
erro_lexico_texto.redc: Erro léxico (linha 2, coluna 8): texto sem aspas de fechamento
```

### erro_sintatico.redc — Erro sintático: ';' ausente

```
# erro sintático: falta ';' no fim da declaração
seja n :: inteiro = 5
mostre(n);
```

`python compiler.py programas/erro_sintatico.redc`

```
erro_sintatico.redc: Erro sintático (linha 2, coluna 22): esperado ';' no fim do comando
```

### erro_semantico.redc — Erro semântico: variável não declarada

```
# erro semântico: variável usada sem ter sido declarada
seja total :: inteiro = 10;
mostre(totl + 1);
```

`python compiler.py programas/erro_semantico.redc`

```
erro_semantico.redc: Erro semântico (linha 3, coluna 8): 'totl' não foi declarada
```

### erro_tipo.redc — Erro semântico: tipo incompatível

```
# erro semântico de tipo: texto guardado em variável inteiro
seja idade :: inteiro = "35";
mostre(idade);
```

`python compiler.py programas/erro_tipo.redc`

```
erro_tipo.redc: Erro semântico (linha 2, coluna 25): esperado inteiro, recebido texto
```

### erro_array.redc — Erro semântico: tamanho do array

```
# erro semântico: o array tem 3 posições e o valor tem 2 elementos
seja v :: [inteiro; 3] = [1, 2];
```

`python compiler.py programas/erro_array.redc`

```
erro_array.redc: Erro semântico (linha 2, coluna 26): esperado [inteiro; 3], recebido [inteiro] (o array tem 3 posição(ões), e o valor tem 2 elemento(s))
```

### erro_indice.redc — Erro de execução: índice fora dos limites

```
# erro de execução: índice fora dos limites da lista
seja fila :: [texto] = ["Ana", "Bia"];
seja posicao :: inteiro = 2;
mostre(fila[posicao]);
```

`python compiler.py programas/erro_indice.redc`

```
erro_indice.redc: Erro de execução (linha 4, coluna 12): índice 2 fora dos limites (tamanho 2, índices de 0 a 1)
```

### erro_execucao.redc — Erro de execução: divisão por zero

```
# erro de execução: divisão por zero que só aparece rodando
seja total :: inteiro = 10;
seja pessoas :: inteiro = 0;
mostre("antes da divisão");
mostre(total / pessoas);
```

`python compiler.py programas/erro_execucao.redc`

```
antes da divisão
erro_execucao.redc: Erro de execução (linha 5, coluna 14): divisão por zero
```

## Saída de cada fase

Programa `repeticao.redc`, com todas as fases exibidas:

`python compiler.py programas/repeticao.redc --tokens --ast --simbolos --bytecode`

```
--- Tokens ---
2:1	SEJA           'seja'
2:6	IDENT          'n'
2:8	TIPO           '::'
2:11	INTEIRO        'inteiro'
2:19	ATRIB          '='
2:21	LIT_INTEIRO    '5'
2:22	PONTO_VIRGULA  ';'
3:1	SEJA           'seja'
3:6	IDENT          'fat'
3:10	TIPO           '::'
3:13	INTEIRO        'inteiro'
3:21	ATRIB          '='
3:23	LIT_INTEIRO    '1'
3:24	PONTO_VIRGULA  ';'
4:1	ENQUANTO       'enquanto'
4:10	ABRE_PAR       '('
4:11	IDENT          'n'
4:13	MAIOR          '>'
4:15	LIT_INTEIRO    '1'
4:16	FECHA_PAR      ')'
4:18	ABRE_CHAVE     '{'
5:5	IDENT          'fat'
5:9	ATRIB          '='
5:11	IDENT          'fat'
5:15	MULT           '*'
5:17	IDENT          'n'
5:18	PONTO_VIRGULA  ';'
6:5	IDENT          'n'
6:7	ATRIB          '='
6:9	IDENT          'n'
6:11	MENOS          '-'
6:13	LIT_INTEIRO    '1'
6:14	PONTO_VIRGULA  ';'
7:1	FECHA_CHAVE    '}'
8:1	MOSTRE         'mostre'
8:7	ABRE_PAR       '('
8:8	IDENT          'fat'
8:11	FECHA_PAR      ')'
8:12	PONTO_VIRGULA  ';'
9:1	EOF            ''

--- AST ---
Programa
├── Declaracao n :: inteiro
│   └── Literal 5 (inteiro)
├── Declaracao fat :: inteiro
│   └── Literal 1 (inteiro)
├── Enquanto
│   ├── condicao: Binaria >
│   │   ├── Variavel n
│   │   └── Literal 1 (inteiro)
│   └── corpo: Bloco
│       ├── Atribuicao fat
│       │   └── Binaria *
│       │       ├── Variavel fat
│       │       └── Variavel n
│       └── Atribuicao n
│           └── Binaria -
│               ├── Variavel n
│               └── Literal 1 (inteiro)
└── Mostre
    └── Variavel fat

--- Tabela de símbolos ---
ESCOPO  NÍVEL  NOME  CATEGORIA  TIPO     LINHA
------  -----  ----  ---------  -------  -----
global  0      n     variavel   inteiro  2
global  0      fat   variavel   inteiro  3

--- Bytecode ---
== principal (2 variáveis) ==
0000  PUSH 5                       ; linha 2
0001  STORE 0                      ; linha 2
0002  PUSH 1                       ; linha 3
0003  STORE 1                      ; linha 3
0004  LOAD 0                       ; linha 4
0005  PUSH 1                       ; linha 4
0006  GT                           ; linha 4
0007  JUMP_IF_FALSE 17             ; linha 4
0008  LOAD 1                       ; linha 5
0009  LOAD 0                       ; linha 5
0010  MUL                          ; linha 5
0011  STORE 1                      ; linha 5
0012  LOAD 0                       ; linha 6
0013  PUSH 1                       ; linha 6
0014  SUB                          ; linha 6
0015  STORE 0                      ; linha 6
0016  JUMP 4                       ; linha 4
0017  LOAD 1                       ; linha 8
0018  PRINT                        ; linha 8
0019  HALT

--- Execução ---
120
```

Programa `exemplo_valido.redc` (funções e recursão):

`python compiler.py programas/exemplo_valido.redc --ast --simbolos --bytecode`

```
--- AST ---
Programa
├── Funcao media(a :: real, b :: real) :: real
│   └── Retorne
│       └── Binaria /
│           ├── Binaria +
│           │   ├── Variavel a
│           │   └── Variavel b
│           └── Literal 2.0 (real)
├── Funcao fatorial(n :: inteiro) :: inteiro
│   ├── Se
│   │   ├── condicao: Binaria <=
│   │   │   ├── Variavel n
│   │   │   └── Literal 1 (inteiro)
│   │   └── entao: Bloco
│   │       └── Retorne
│   │           └── Literal 1 (inteiro)
│   └── Retorne
│       └── Binaria *
│           ├── Variavel n
│           └── Chamada fatorial
│               └── Binaria -
│                   ├── Variavel n
│                   └── Literal 1 (inteiro)
├── Declaracao m :: real
│   └── Chamada media
│       ├── Literal 7.5 (real)
│       └── Literal 9.0 (real)
├── Mostre
│   └── Variavel m
├── Se
│   ├── condicao: Binaria >=
│   │   ├── Variavel m
│   │   └── Literal 7.0 (real)
│   ├── entao: Bloco
│   │   └── Mostre
│   │       └── Literal 'aprovado' (texto)
│   └── senao: Se
│       ├── condicao: Binaria >=
│       │   ├── Variavel m
│       │   └── Literal 5.0 (real)
│       ├── entao: Bloco
│       │   └── Mostre
│       │       └── Literal 'recuperação' (texto)
│       └── senao: Bloco
│           └── Mostre
│               └── Literal 'reprovado' (texto)
└── Mostre
    └── Chamada fatorial
        └── Literal 5 (inteiro)

--- Tabela de símbolos ---
ESCOPO           NÍVEL  NOME      CATEGORIA  TIPO                  LINHA
---------------  -----  --------  ---------  --------------------  -----
global           0      media     funcao     (real, real) :: real  2
global           0      fatorial  funcao     (inteiro) :: inteiro  6
global           0      m         variavel   real                  13
funcao media     1      a         parametro  real                  2
funcao media     1      b         parametro  real                  2
funcao fatorial  1      n         parametro  inteiro               6

--- Bytecode ---
== principal (1 variável) ==
0000  PUSH 7.5                     ; linha 13
0001  PUSH 9.0                     ; linha 13
0002  CALL media 2                 ; linha 13
0003  STORE 0                      ; linha 13
0004  LOAD 0                       ; linha 14
0005  PRINT                        ; linha 14
0006  LOAD 0                       ; linha 16
0007  PUSH 7.0                     ; linha 16
0008  GE                           ; linha 16
0009  JUMP_IF_FALSE 13             ; linha 16
0010  PUSH 'aprovado'              ; linha 17
0011  PRINT                        ; linha 17
0012  JUMP 22                      ; linha 16
0013  LOAD 0                       ; linha 18
0014  PUSH 5.0                     ; linha 18
0015  GE                           ; linha 18
0016  JUMP_IF_FALSE 20             ; linha 18
0017  PUSH 'recuperação'           ; linha 19
0018  PRINT                        ; linha 19
0019  JUMP 22                      ; linha 18
0020  PUSH 'reprovado'             ; linha 21
0021  PRINT                        ; linha 21
0022  PUSH 5                       ; linha 24
0023  CALL fatorial 1              ; linha 24
0024  PRINT                        ; linha 24
0025  HALT

== funcao media (2 parâmetro(s), 2 variáveis) ==
0026  LOAD 0                       ; linha 3
0027  LOAD 1                       ; linha 3
0028  ADD                          ; linha 3
0029  PUSH 2.0                     ; linha 3
0030  DIV_REAL                     ; linha 3
0031  RET                          ; linha 3

== funcao fatorial (1 parâmetro(s), 1 variável) ==
0032  LOAD 0                       ; linha 7
0033  PUSH 1                       ; linha 7
0034  LE                           ; linha 7
0035  JUMP_IF_FALSE 38             ; linha 7
0036  PUSH 1                       ; linha 8
0037  RET                          ; linha 8
0038  LOAD 0                       ; linha 10
0039  LOAD 0                       ; linha 10
0040  PUSH 1                       ; linha 10
0041  SUB                          ; linha 10
0042  CALL fatorial 1              ; linha 10
0043  MUL                          ; linha 10
0044  RET                          ; linha 10

--- Execução ---
8.25
aprovado
120
```

Programa `escopos.redc` (tabela de símbolos com sombreamento):

`python compiler.py programas/escopos.redc --simbolos`

```
--- Tabela de símbolos ---
ESCOPO              NÍVEL  NOME       CATEGORIA  TIPO                  LINHA
------------------  -----  ---------  ---------  --------------------  -----
global              0      dobro      funcao     (inteiro) :: inteiro  2
global              0      limite     variavel   inteiro               7
global              0      i          variavel   inteiro               8
funcao dobro        1      x          parametro  inteiro               2
funcao dobro        1      resultado  variavel   inteiro               3
enquanto (linha 9)  1      quadrado   variavel   inteiro               10
se (linha 11)       2      limite     variavel   texto                 12

--- Execução ---
sombreia o limite global
6
```

Programa `escolha.redc` (AST e bytecode de escolha/caso):

`python compiler.py programas/escolha.redc --ast --bytecode`

```
--- AST ---
Programa
├── Funcao nome_do_dia(dia :: inteiro) :: texto
│   └── Escolha
│       ├── valor: Variavel dia
│       ├── Caso 1, 7
│       │   └── Retorne
│       │       └── Literal 'fim de semana' (texto)
│       ├── Caso 2
│       │   └── Retorne
│       │       └── Literal 'segunda' (texto)
│       ├── Caso 6
│       │   └── Retorne
│       │       └── Literal 'sexta' (texto)
│       └── padrao: Bloco
│           └── Retorne
│               └── Literal 'meio da semana' (texto)
├── Mostre
│   └── Chamada nome_do_dia
│       └── Literal 1 (inteiro)
├── Mostre
│   └── Chamada nome_do_dia
│       └── Literal 2 (inteiro)
├── Mostre
│   └── Chamada nome_do_dia
│       └── Literal 4 (inteiro)
├── Declaracao comando :: texto
│   └── Literal 'parar' (texto)
└── Escolha
    ├── valor: Variavel comando
    ├── Caso 'andar'
    │   └── Mostre
    │       └── Literal 'andando' (texto)
    └── Caso 'parar'
        └── Mostre
            └── Literal 'parado' (texto)

--- Bytecode ---
== principal (2 variáveis) ==
0000  PUSH 1                       ; linha 11
0001  CALL nome_do_dia 1           ; linha 11
0002  PRINT                        ; linha 11
0003  PUSH 2                       ; linha 12
0004  CALL nome_do_dia 1           ; linha 12
0005  PRINT                        ; linha 12
0006  PUSH 4                       ; linha 13
0007  CALL nome_do_dia 1           ; linha 13
0008  PRINT                        ; linha 13
0009  PUSH 'parar'                 ; linha 15
0010  STORE 0                      ; linha 15
0011  LOAD 0                       ; linha 16
0012  STORE 1                      ; linha 16
0013  LOAD 1                       ; linha 17
0014  PUSH 'andar'                 ; linha 17
0015  EQ                           ; linha 17
0016  JUMP_IF_TRUE 22              ; linha 17
0017  LOAD 1                       ; linha 18
0018  PUSH 'parar'                 ; linha 18
0019  EQ                           ; linha 18
0020  JUMP_IF_TRUE 25              ; linha 18
0021  JUMP 28                      ; linha 16
0022  PUSH 'andando'               ; linha 17
0023  PRINT                        ; linha 17
0024  JUMP 28                      ; linha 17
0025  PUSH 'parado'                ; linha 18
0026  PRINT                        ; linha 18
0027  JUMP 28                      ; linha 18
0028  HALT

== funcao nome_do_dia (1 parâmetro(s), 2 variáveis) ==
0029  LOAD 0                       ; linha 3
0030  STORE 1                      ; linha 3
0031  LOAD 1                       ; linha 4
0032  PUSH 1                       ; linha 4
0033  EQ                           ; linha 4
0034  JUMP_IF_TRUE 48              ; linha 4
0035  LOAD 1                       ; linha 4
0036  PUSH 7                       ; linha 4
0037  EQ                           ; linha 4
0038  JUMP_IF_TRUE 48              ; linha 4
0039  LOAD 1                       ; linha 5
0040  PUSH 2                       ; linha 5
0041  EQ                           ; linha 5
0042  JUMP_IF_TRUE 51              ; linha 5
0043  LOAD 1                       ; linha 6
0044  PUSH 6                       ; linha 6
0045  EQ                           ; linha 6
0046  JUMP_IF_TRUE 54              ; linha 6
0047  JUMP 57                      ; linha 3
0048  PUSH 'fim de semana'         ; linha 4
0049  RET                          ; linha 4
0050  JUMP 59                      ; linha 4
0051  PUSH 'segunda'               ; linha 5
0052  RET                          ; linha 5
0053  JUMP 59                      ; linha 5
0054  PUSH 'sexta'                 ; linha 6
0055  RET                          ; linha 6
0056  JUMP 59                      ; linha 6
0057  PUSH 'meio da semana'        ; linha 7
0058  RET                          ; linha 7

--- Execução ---
fim de semana
segunda
meio da semana
parado
```

Programa `registros.redc` (registros, listas e para cada):

`python compiler.py programas/registros.redc --simbolos --bytecode`

```
--- Tabela de símbolos ---
ESCOPO                NÍVEL  NOME   CATEGORIA  TIPO                              LINHA
--------------------  -----  -----  ---------  --------------------------------  -----
global                0      Aluno  registro   {nome :: texto; notas :: [real]}  2
global                0      media  funcao     (Aluno) :: real                   7
global                0      ana    variavel   Aluno                             15
global                0      turma  variavel   [Aluno]                           21
funcao media          1      a      parametro  Aluno                             7
funcao media          1      soma   variavel   real                              8
para cada (linha 9)   2      n      variavel   real                              9
para cada (linha 23)  1      aluno  variavel   Aluno                             23

--- Bytecode ---
== registro Aluno (nome, notas) ==

== principal (6 variáveis) ==
0000  PUSH 'Ana'                   ; linha 15
0001  PUSH 8.0                     ; linha 15
0002  PUSH 9.5                     ; linha 15
0003  MAKE_ARRAY 2                 ; linha 15
0004  NEW_RECORD Aluno 2           ; linha 15
0005  STORE 0                      ; linha 15
0006  LOAD 0                       ; linha 16
0007  GET_FIELD 1                  ; linha 16
0008  PUSH 10                      ; linha 16
0009  TO_REAL                      ; linha 16
0010  APPEND                       ; linha 16
0011  POP                          ; linha 16
0012  LOAD 0                       ; linha 17
0013  PRINT                        ; linha 17
0014  LOAD 0                       ; linha 18
0015  GET_FIELD 0                  ; linha 18
0016  PRINT                        ; linha 18
0017  LOAD 0                       ; linha 19
0018  CALL media 1                 ; linha 19
0019  PRINT                        ; linha 19
0020  LOAD 0                       ; linha 21
0021  PUSH 'Bia'                   ; linha 21
0022  PUSH 6.0                     ; linha 21
0023  MAKE_ARRAY 1                 ; linha 21
0024  NEW_RECORD Aluno 2           ; linha 21
0025  MAKE_ARRAY 2                 ; linha 21
0026  STORE 1                      ; linha 21
0027  LOAD 1                       ; linha 22
0028  PUSH 1                       ; linha 22
0029  GET_INDEX                    ; linha 22
0030  PUSH 'Beatriz'               ; linha 22
0031  SET_FIELD 0                  ; linha 22
0032  LOAD 1                       ; linha 23
0033  STORE 2                      ; linha 23
0034  PUSH 0                       ; linha 23
0035  STORE 3                      ; linha 23
0036  LOAD 2                       ; linha 23
0037  LEN                          ; linha 23
0038  STORE 4                      ; linha 23
0039  LOAD 3                       ; linha 23
0040  LOAD 4                       ; linha 23
0041  LT                           ; linha 23
0042  JUMP_IF_FALSE 55             ; linha 23
0043  LOAD 2                       ; linha 23
0044  LOAD 3                       ; linha 23
0045  GET_INDEX                    ; linha 23
0046  STORE 5                      ; linha 23
0047  LOAD 5                       ; linha 24
0048  GET_FIELD 0                  ; linha 24
0049  PRINT                        ; linha 24
0050  LOAD 3                       ; linha 23
0051  PUSH 1                       ; linha 23
0052  ADD                          ; linha 23
0053  STORE 3                      ; linha 23
0054  JUMP 39                      ; linha 23
0055  HALT

== funcao media (1 parâmetro(s), 6 variáveis) ==
0056  PUSH 0.0                     ; linha 8
0057  STORE 1                      ; linha 8
0058  LOAD 0                       ; linha 9
0059  GET_FIELD 1                  ; linha 9
0060  STORE 2                      ; linha 9
0061  PUSH 0                       ; linha 9
0062  STORE 3                      ; linha 9
0063  LOAD 2                       ; linha 9
0064  LEN                          ; linha 9
0065  STORE 4                      ; linha 9
0066  LOAD 3                       ; linha 9
0067  LOAD 4                       ; linha 9
0068  LT                           ; linha 9
0069  JUMP_IF_FALSE 83             ; linha 9
0070  LOAD 2                       ; linha 9
0071  LOAD 3                       ; linha 9
0072  GET_INDEX                    ; linha 9
0073  STORE 5                      ; linha 9
0074  LOAD 1                       ; linha 10
0075  LOAD 5                       ; linha 10
0076  ADD                          ; linha 10
0077  STORE 1                      ; linha 10
0078  LOAD 3                       ; linha 9
0079  PUSH 1                       ; linha 9
0080  ADD                          ; linha 9
0081  STORE 3                      ; linha 9
0082  JUMP 66                      ; linha 9
0083  LOAD 1                       ; linha 12
0084  LOAD 0                       ; linha 12
0085  GET_FIELD 1                  ; linha 12
0086  LEN                          ; linha 12
0087  DIV_REAL                     ; linha 12
0088  RET                          ; linha 12

--- Execução ---
Aluno(nome: "Ana", notas: [8.0, 9.5, 10.0])
Ana
9.166666666666666
Ana
Beatriz
```
