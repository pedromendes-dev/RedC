"""
compiler.py — Ponto de entrada do compilador RedC.

Executa o fluxo completo:
    programa .redc → léxico → tokens → sintático → AST → semântica
    → bytecode → máquina virtual → resultado

Uso:
    python compiler.py programas/exemplo_valido.redc               # compila e executa
    python compiler.py programas/exemplo_valido.redc --tokens      # mostra os tokens
    python compiler.py programas/exemplo_valido.redc --ast         # mostra a AST
    python compiler.py programas/exemplo_valido.redc --simbolos    # mostra a tabela de símbolos
    python compiler.py programas/exemplo_valido.redc --bytecode    # mostra o bytecode
    python compiler.py programas/exemplo_valido.redc --salvar      # grava AST, tabela e bytecode em saida/
    python compiler.py programas/exemplo_valido.redc --sem-executar
As opções podem ser combinadas.
"""

import sys
from pathlib import Path

import codegen
import lexer
import parser
import semantic
import vm
from errors import CompilacaoErro
from redc_ast import imprimir_ast

PASTA_SAIDA = Path(__file__).resolve().parent / "saida"

# As fases percorrem a AST de forma recursiva. O limite padrão do Python
# (1000 chamadas) é pouco para expressões longas como uma soma de 2000 termos.
sys.setrecursionlimit(10_000)
OPCOES = {"--tokens", "--ast", "--simbolos", "--bytecode", "--salvar", "--sem-executar"}


def _secao(titulo: str, conteudo: str):
    print(f"--- {titulo} ---")
    print(conteudo)
    print()


def ler_fonte(arquivo: Path) -> str:
    """Lê o programa aceitando os formatos comuns no Windows:
    UTF-8 com BOM (Bloco de Notas) e ANSI/Windows-1252 (editores antigos)."""
    dados = arquivo.read_bytes()
    try:
        return dados.decode("utf-8-sig")
    except UnicodeDecodeError:
        return dados.decode("cp1252", errors="replace")


def compilar(caminho: str, opcoes: set[str] = frozenset()) -> int:
    arquivo = Path(caminho)
    if arquivo.suffix != ".redc":
        print(f"Arquivo '{caminho}' não é um programa RedC (extensão .redc).")
        return 2
    try:
        fonte = ler_fonte(arquivo)
    except FileNotFoundError:
        print(f"Arquivo '{caminho}' não encontrado.")
        return 2

    try:
        tokens = lexer.analisar(fonte)
        if "--tokens" in opcoes:
            _secao("Tokens", "\n".join(str(t) for t in tokens))

        arvore = parser.analisar(tokens)
        if "--ast" in opcoes:
            _secao("AST", imprimir_ast(arvore))

        tabela = semantic.analisar(arvore)
        if "--simbolos" in opcoes:
            _secao("Tabela de símbolos", tabela.relatorio())

        bytecode = codegen.gerar(arvore)
        if "--bytecode" in opcoes:
            _secao("Bytecode", bytecode.listagem())

        if "--salvar" in opcoes:
            PASTA_SAIDA.mkdir(exist_ok=True)
            for sufixo, conteudo in [("ast", imprimir_ast(arvore)),
                                     ("simbolos", tabela.relatorio()),
                                     ("bytecode", bytecode.listagem())]:
                (PASTA_SAIDA / f"{arquivo.stem}.{sufixo}.txt").write_text(
                    conteudo + "\n", encoding="utf-8")
            print(f"AST, tabela de símbolos e bytecode gravados em saida/{arquivo.stem}.*.txt\n")

        if "--sem-executar" in opcoes:
            print(f"{arquivo.name}: compilado sem erros ({len(bytecode.instrucoes)} instruções).")
            return 0

        if opcoes & (OPCOES - {"--sem-executar"}):
            print("--- Execução ---")
        vm.executar(bytecode)
    except CompilacaoErro as erro:
        print(f"{arquivo.name}: {erro}")
        return 1
    except RecursionError:
        print(f"{arquivo.name}: Erro: expressão longa ou aninhada demais para o "
              "compilador; divida-a em partes menores usando variáveis.")
        return 1
    return 0


if __name__ == "__main__":
    # No Windows, a saída redirecionada para arquivo usa cp1252, que não tem
    # os caracteres da árvore (├──). Forçar UTF-8 evita erro ao gravar.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    args = sys.argv[1:]
    desconhecidas = [a for a in args[1:] if a not in OPCOES]
    if not args or desconhecidas:
        if desconhecidas:
            print(f"Opção desconhecida: {' '.join(desconhecidas)}")
        print("Uso: python compiler.py <arquivo.redc> [" + "] [".join(sorted(OPCOES)) + "]")
        sys.exit(2)
    sys.exit(compilar(args[0], set(args[1:])))
