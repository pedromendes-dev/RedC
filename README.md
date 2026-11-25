# RedC — linguagem e compilador

Projeto A3 de Teoria da Computação e Compiladores (UNA, 2026/2).

Grupo: Gabriel Guimarães Borges Pereira, Pedro Elias Mendes Pedrosa, Renan
Christian de Lima Souza, Victor Lobato de Vasconcelos e Yuri Lucas Fonseca de Sousa.

A RedC é uma linguagem didática para quem está saindo do pseudocódigo
(Portugol, VisuAlg) e indo para linguagens como C, Java e Python: palavras em
português, mas com tipos explícitos, blocos com chaves e funções com escopo.
Este compilador, escrito em Python sem bibliotecas de análise, lê programas
`.redc`, verifica erros, gera bytecode e o executa em uma máquina virtual.

```
# situação de um aluno
funcao media(a :: real, b :: real) :: real {
    retorne (a + b) / 2.0;
}

seja m :: real = media(7.5, 9.0);
se (m >= 7.0) {
    mostre("aprovado");
} senao {
    mostre("reprovado");
}
```

## Requisitos

Python **3.10 ou mais novo** (o código usa `match`). Não há dependências
para instalar.

## Como executar

Na pasta `redc/`:

```
python compiler.py programas/exemplo_valido.redc
```

| Opção | Mostra |
| --- | --- |
| `--tokens` | a lista de tokens (análise léxica) |
| `--ast` | a árvore sintática abstrata |
| `--simbolos` | a tabela de símbolos, escopo por escopo |
| `--bytecode` | o bytecode gerado |
| `--salvar` | grava AST, tabela e bytecode em `saida/` |
| `--sem-executar` | compila sem rodar na máquina virtual |

As opções podem ser combinadas:

```
python compiler.py programas/repeticao.redc --tokens --ast --simbolos --bytecode
```

Erros saem com a fase, a linha e a coluna:

```
erro_tipo.redc: Erro semântico (linha 2, coluna 25): esperado inteiro, recebido texto
```

## Testes

```
python -m unittest discover -s testes -v     # 213 testes
python gerar_resultados.py                   # gera resultados/RESULTADOS.md
```

O `RESULTADOS.md` traz cada programa de teste com o código-fonte, a saída real e
a comparação com a saída esperada, além da saída de cada fase do compilador.

## Estrutura

```
redc/
├── compiler.py          coordena as fases e trata a linha de comando
├── tokens.py            tipos de token e palavras reservadas
├── lexer.py             análise léxica, caractere por caractere
├── parser.py            análise sintática por descida recursiva
├── redc_ast.py          nós da AST e impressão da árvore
├── symbols.py           tabela de símbolos com pilha de escopos
├── semantic.py          escopos e verificação de tipos
├── codegen.py           geração de bytecode para máquina de pilha
├── vm.py                máquina virtual que executa o bytecode
├── errors.py            erros léxicos, sintáticos, semânticos e de execução
├── gerar_resultados.py  relatório de evidências de execução
├── programas/           programas de teste .redc (válidos e com erro)
└── testes/              testes automatizados e catálogo dos casos (casos.py)
```

Fluxo: programa `.redc` → léxico → tokens → sintático → AST → semântica
(tabela de símbolos e tipos) → bytecode → máquina virtual → resultado.

## A linguagem em resumo

| Recurso | Sintaxe |
| --- | --- |
| Declaração | `seja n :: inteiro = 5;` |
| Tipos | `inteiro`, `real`, `texto`, `logico` |
| Atribuição | `n = n + 1;` |
| Saída | `mostre(n);` |
| Condição | `se (n > 0) { ... } senao se (n == 0) { ... } senao { ... }` |
| Repetição | `enquanto (n > 1) { ... }` |
| Escolha | `escolha (dia) { caso 1, 7 { ... } caso 2 { ... } padrao { ... } }` |
| Percorrer coleção | `para cada nota em notas { ... }` |
| Função | `funcao dobro(x :: inteiro) :: inteiro { retorne x * 2; }` |
| Array (tamanho fixo) | `seja v :: [inteiro; 3] = [1, 2, 3];` e `v[0] = 5;` |
| Lista (tamanho variável) | `seja l :: [real] = [];` e `adicione(l, 7.5);` |
| Matriz | `seja m :: [[inteiro; 2]; 2] = [[1, 2], [3, 4]];` |
| Registro | `registro Aluno { nome :: texto; nota :: real; }` |
| Criar e usar registro | `seja a :: Aluno = Aluno("Ana", 8.5);` e `a.nota = 9.0;` |
| Funções nativas | `tamanho(x)` (array, lista ou texto), `adicione(lista, valor)` |
| Conversão para texto | `mostre("faltas: " + texto(3));` |
| Operadores | `+ - * / %`, `== != < <= > >=`, `e ou nao` |
| Comentário | `# até o fim da linha` |

Regras principais: toda variável nasce com valor; `inteiro` é promovido a
`real` automaticamente, mas não o contrário; texto e número só se juntam com
a conversão explícita `texto(valor)`; `inteiro / inteiro` é divisão
inteira (`7 / 2` dá `3`); condições precisam ser `logico`; funções enxergam só
seus parâmetros e variáveis locais e precisam terminar com `retorne`; `escolha`
não tem fallthrough; o literal `[1, 2, 3]` serve para array do mesmo tamanho ou
para lista; arrays, listas e registros são passados por referência, como em Java.
