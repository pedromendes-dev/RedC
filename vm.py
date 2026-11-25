"""
vm.py — Máquina virtual da RedC.

Executa o bytecode gerado pelo codegen. É uma máquina de pilha com:
- pilha de operandos: onde as contas acontecem;
- pilha de quadros (frames): um por chamada de função em andamento,
  com as variáveis daquela chamada e o endereço de retorno;
- pc (program counter): o índice da próxima instrução.

Erros de execução (divisão por zero, recursão profunda demais, laço que
não termina) saem como ErroExecucao, com a linha e a coluna do código-fonte.
"""

from __future__ import annotations

from dataclasses import dataclass

from codegen import Bytecode
from errors import ErroExecucao

LIMITE_CHAMADAS = 1000          # profundidade máxima de recursão
LIMITE_INSTRUCOES = 5_000_000   # proteção contra laço infinito na apresentação


class ValorRegistro:
    """Um valor de registro na VM: o nome do tipo, os nomes e os valores dos campos.
    Arrays, listas e registros são passados por referência, como em Java:
    'b = a;' faz as duas variáveis apontarem para o mesmo valor."""
    __slots__ = ("tipo", "campos", "valores")

    def __init__(self, tipo: str, campos: list[str], valores: list):
        self.tipo = tipo
        self.campos = campos
        self.valores = valores


@dataclass
class Quadro:
    variaveis: list
    retorno: int            # endereço para onde voltar depois do RET
    funcao: str


def formatar(valor) -> str:
    """Como 'mostre' exibe cada tipo."""
    if isinstance(valor, bool):
        return "verdadeiro" if valor else "falso"
    if isinstance(valor, list):
        return "[" + ", ".join(_formatar_dentro(v) for v in valor) + "]"
    if isinstance(valor, ValorRegistro):
        campos = ", ".join(f"{n}: {_formatar_dentro(v)}"
                           for n, v in zip(valor.campos, valor.valores))
        return f"{valor.tipo}({campos})"
    return str(valor)


def _formatar_dentro(valor) -> str:
    # Dentro de listas e registros, textos aparecem entre aspas: ["Ana", "Bia"].
    return f'"{valor}"' if isinstance(valor, str) else formatar(valor)


def _verificar_indice(colecao: list, i: int, ins):
    if not 0 <= i < len(colecao):
        if not colecao:
            detalhe = "a coleção está vazia"
        else:
            detalhe = f"tamanho {len(colecao)}, índices de 0 a {len(colecao) - 1}"
        raise ErroExecucao(f"índice {i} fora dos limites ({detalhe})", ins.linha, ins.coluna)


def _div_inteira(a: int, b: int) -> int:
    # Trunca em direção a zero, como C e Java: -7 / 2 = -3.
    # (O '//' do Python arredonda para baixo: -7 // 2 = -4.)
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def _resto(a: int, b: int) -> int:
    # Consistente com a divisão acima: a == (a / b) * b + a % b.
    return a - _div_inteira(a, b) * b


class MaquinaVirtual:
    def __init__(self, bytecode: Bytecode, escrever=print,
                 limite_instrucoes: int = LIMITE_INSTRUCOES):
        self.bc = bytecode
        self.escrever = escrever
        self.limite_instrucoes = limite_instrucoes

    def executar(self):
        codigo = self.bc.instrucoes
        pilha: list = []
        quadros = [Quadro([None] * self.bc.tamanho_quadro_principal, -1, "principal")]
        pc = 0
        passos = 0

        while True:
            ins = codigo[pc]
            pc += 1
            passos += 1
            if passos > self.limite_instrucoes:
                raise ErroExecucao(
                    f"o programa executou mais de {self.limite_instrucoes:,} instruções "
                    "sem terminar; provável laço infinito".replace(",", "."),
                    ins.linha, ins.coluna)

            op = ins.op
            if op == "PUSH":
                pilha.append(ins.arg)
            elif op == "LOAD":
                pilha.append(quadros[-1].variaveis[ins.arg])
            elif op == "STORE":
                quadros[-1].variaveis[ins.arg] = pilha.pop()
            elif op == "POP":
                pilha.pop()
            elif op == "TO_REAL":
                pilha.append(float(pilha.pop()))
            elif op == "TO_TEXT":
                pilha.append(formatar(pilha.pop()))

            elif op in ("ADD", "SUB", "MUL", "DIV_INT", "DIV_REAL", "MOD", "CONCAT",
                        "EQ", "NE", "LT", "LE", "GT", "GE"):
                b = pilha.pop()
                a = pilha.pop()
                pilha.append(self._binaria(op, a, b, ins))
            elif op == "NEG":
                pilha.append(-pilha.pop())
            elif op == "NOT":
                pilha.append(not pilha.pop())

            elif op == "JUMP":
                pc = ins.arg
            elif op == "JUMP_IF_FALSE":
                if not pilha.pop():
                    pc = ins.arg
            elif op == "JUMP_IF_TRUE":
                if pilha.pop():
                    pc = ins.arg

            elif op == "CALL":
                info = self.bc.funcoes[ins.arg]
                if len(quadros) >= LIMITE_CHAMADAS:
                    raise ErroExecucao(
                        f"estouro de pilha: mais de {LIMITE_CHAMADAS} chamadas "
                        f"aninhadas ('{info.nome}' nunca para de chamar a si mesma?)",
                        ins.linha, ins.coluna)
                variaveis = [None] * info.tamanho_quadro
                n = ins.arg2
                if n:
                    variaveis[:n] = pilha[-n:]   # argumentos viram os primeiros slots
                    del pilha[-n:]
                quadros.append(Quadro(variaveis, pc, info.nome))
                pc = info.endereco
            elif op == "RET":
                quadro = quadros.pop()
                pc = quadro.retorno               # o valor de retorno fica na pilha

            elif op == "MAKE_ARRAY":
                n = ins.arg
                if n:
                    elementos = pilha[-n:]
                    del pilha[-n:]
                else:
                    elementos = []
                pilha.append(elementos)
            elif op == "GET_INDEX":
                i = pilha.pop()
                colecao = pilha.pop()
                _verificar_indice(colecao, i, ins)
                pilha.append(colecao[i])
            elif op == "SET_INDEX":
                valor = pilha.pop()
                i = pilha.pop()
                colecao = pilha.pop()
                _verificar_indice(colecao, i, ins)
                colecao[i] = valor
            elif op == "LEN":
                pilha.append(len(pilha.pop()))
            elif op == "APPEND":
                valor = pilha.pop()
                lista = pilha.pop()
                lista.append(valor)
                pilha.append(len(lista))
            elif op == "NEW_RECORD":
                n = ins.arg2
                valores = pilha[-n:]
                del pilha[-n:]
                pilha.append(ValorRegistro(ins.arg, self.bc.registros[ins.arg], valores))
            elif op == "GET_FIELD":
                pilha.append(pilha.pop().valores[ins.arg])
            elif op == "SET_FIELD":
                valor = pilha.pop()
                pilha.pop().valores[ins.arg] = valor

            elif op == "PRINT":
                self.escrever(formatar(pilha.pop()))
            elif op == "HALT":
                return
            else:
                raise RuntimeError(f"instrução desconhecida: {op}")

    def _binaria(self, op, a, b, ins):
        match op:
            case "ADD": return a + b
            case "SUB": return a - b
            case "MUL": return a * b
            case "CONCAT": return a + b
            case "DIV_INT" | "DIV_REAL" | "MOD" if b == 0:
                raise ErroExecucao("divisão por zero", ins.linha, ins.coluna)
            case "DIV_INT": return _div_inteira(a, b)
            case "DIV_REAL": return a / b
            case "MOD": return _resto(a, b)
            case "EQ": return a == b
            case "NE": return a != b
            case "LT": return a < b
            case "LE": return a <= b
            case "GT": return a > b
            case "GE": return a >= b


def executar(bytecode: Bytecode, escrever=print, **opcoes):
    MaquinaVirtual(bytecode, escrever, **opcoes).executar()
