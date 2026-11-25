"""
redc_ast.py — Nós da Árvore Sintática Abstrata (AST) da RedC.

O parser transforma a lista de tokens nesta árvore. Cada nó guarda
linha e coluna, para que a análise semântica e a VM apontem o lugar
exato de um erro.

Os tipos são representados assim:
- tipos básicos: as strings 'inteiro', 'real', 'texto' e 'logico';
- array e lista: TipoColecao — '[inteiro; 3]' (array) e '[inteiro]' (lista);
- registro: TipoRegistro — o nome do registro, como 'Aluno'.

O arquivo não se chama 'ast.py' para não colidir com o módulo 'ast'
da biblioteca padrão do Python.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------- Tipos compostos ----------------

@dataclass(frozen=True)
class TipoColecao:
    """Array (tamanho fixo) ou lista (tamanho None).

    'literal' marca o tipo de um literal como [1, 2, 3]: ele ainda não é
    array nem lista e pode ser guardado em qualquer um dos dois, desde que
    os elementos e o tamanho sirvam (semantic.cabe_em)."""
    elemento: object            # tipo dos elementos; None num literal vazio []
    tamanho: int | None = None
    literal: bool = False

    @property
    def eh_lista(self) -> bool:
        return self.tamanho is None and not self.literal

    def __str__(self) -> str:
        if self.elemento is None:
            return "[]"
        # Um literal ainda não é array nem lista: mostra só o tipo dos elementos.
        if self.tamanho is None or self.literal:
            return f"[{self.elemento}]"
        return f"[{self.elemento}; {self.tamanho}]"


@dataclass(frozen=True)
class TipoRegistro:
    nome: str
    # Posição onde o tipo foi escrito, para o erro "tipo não existe".
    linha: int = field(default=0, compare=False)
    coluna: int = field(default=0, compare=False)

    def __str__(self) -> str:
        return self.nome


# ---------------- Nó base ----------------

@dataclass
class No:
    linha: int = field(kw_only=True)
    coluna: int = field(kw_only=True)
    # Preenchidos pela análise semântica (não fazem parte da sintaxe):
    # o tipo de uma expressão e o símbolo a que um nome se refere.
    tipo_resolvido: object = field(default=None, kw_only=True, compare=False, repr=False)
    simbolo: object = field(default=None, kw_only=True, compare=False, repr=False)


# ---------------- Estrutura do programa ----------------

@dataclass
class Programa(No):
    funcoes: list[Funcao]
    comandos: list[No]
    registros: list[Registro] = field(default_factory=list, kw_only=True)
    # Quantas variáveis o programa principal usa (preenchido pela semântica).
    tamanho_quadro: int = field(default=0, kw_only=True, compare=False, repr=False)


@dataclass
class Parametro(No):
    nome: str
    tipo: object


@dataclass
class Funcao(No):
    nome: str
    parametros: list[Parametro]
    tipo_retorno: object
    corpo: Bloco
    # Quantas variáveis (parâmetros + locais) a função usa (preenchido pela semântica).
    tamanho_quadro: int = field(default=0, kw_only=True, compare=False, repr=False)


@dataclass
class CampoRegistro(No):
    nome: str
    tipo: object


@dataclass
class Registro(No):
    nome: str
    campos: list[CampoRegistro]


@dataclass
class Bloco(No):
    comandos: list[No]


# ---------------- Comandos ----------------

@dataclass
class DeclaracaoVar(No):
    nome: str
    tipo: object
    valor: No


@dataclass
class Atribuicao(No):
    """alvo = valor; o alvo é Variavel, AcessoIndice ou AcessoCampo."""
    alvo: No
    valor: No


@dataclass
class Se(No):
    condicao: No
    entao: Bloco
    senao: Bloco | Se | None   # 'senao se' vira um Se aninhado


@dataclass
class Enquanto(No):
    condicao: No
    corpo: Bloco


@dataclass
class Caso(No):
    valores: list[Literal]
    corpo: Bloco


@dataclass
class Escolha(No):
    expressao: No
    casos: list[Caso]
    padrao: Bloco | None
    # Posição escondida no quadro que guarda o valor comparado (semântica).
    slot_valor: int = field(default=-1, kw_only=True, compare=False, repr=False)


@dataclass
class ParaCada(No):
    variavel: str
    colecao: No
    corpo: Bloco
    # Posições escondidas no quadro: a coleção, o índice e o tamanho (semântica).
    slot_colecao: int = field(default=-1, kw_only=True, compare=False, repr=False)
    slot_indice: int = field(default=-1, kw_only=True, compare=False, repr=False)
    slot_tamanho: int = field(default=-1, kw_only=True, compare=False, repr=False)


@dataclass
class Mostre(No):
    valor: No


@dataclass
class Retorne(No):
    valor: No


@dataclass
class ComandoChamada(No):
    """Chamada de função usada como comando: 'dobro(3);'."""
    chamada: Chamada


# ---------------- Expressões ----------------

@dataclass
class Literal(No):
    valor: object
    tipo: str          # 'inteiro', 'real', 'texto' ou 'logico'


@dataclass
class ListaLiteral(No):
    elementos: list[No]


@dataclass
class Variavel(No):
    nome: str


@dataclass
class AcessoIndice(No):
    base: No
    indice: No


@dataclass
class AcessoCampo(No):
    base: No
    campo: str
    # Posição do campo dentro do registro (preenchido pela semântica).
    indice_campo: int = field(default=-1, kw_only=True, compare=False, repr=False)


@dataclass
class Binaria(No):
    op: str            # '+', '==', 'e', ...
    esquerda: No
    direita: No


@dataclass
class Unaria(No):
    op: str            # '-' ou 'nao'
    operando: No


@dataclass
class Chamada(No):
    """Chamada de função, de função nativa ou construção de registro."""
    nome: str
    argumentos: list[No]


# ---------------- Impressão da árvore ----------------

def _rotulo(no: No) -> str:
    match no:
        case Programa():
            return "Programa"
        case Registro():
            return f"Registro {no.nome}"
        case CampoRegistro():
            return f"Campo {no.nome} :: {no.tipo}"
        case Funcao():
            params = ", ".join(f"{p.nome} :: {p.tipo}" for p in no.parametros)
            return f"Funcao {no.nome}({params}) :: {no.tipo_retorno}"
        case Bloco():
            return "Bloco"
        case DeclaracaoVar():
            return f"Declaracao {no.nome} :: {no.tipo}"
        case Atribuicao(alvo=Variavel()):
            return f"Atribuicao {no.alvo.nome}"
        case Escolha():
            return "Escolha"
        case Caso():
            valores = ", ".join(repr(v.valor) if v.tipo == "texto" else str(v.valor)
                                for v in no.valores)
            return f"Caso {valores}"
        case ParaCada():
            return f"ParaCada {no.variavel}"
        case Literal(tipo="texto"):
            return f"Literal {no.valor!r} (texto)"
        case Literal(tipo="logico"):
            return f"Literal {'verdadeiro' if no.valor else 'falso'} (logico)"
        case Literal():
            return f"Literal {no.valor} ({no.tipo})"
        case ListaLiteral():
            return f"Lista ({len(no.elementos)} elementos)"
        case Variavel():
            return f"Variavel {no.nome}"
        case AcessoIndice():
            return "Indice"
        case AcessoCampo():
            return f"Campo .{no.campo}"
        case Binaria() | Unaria():
            return f"{type(no).__name__} {no.op}"
        case Chamada():
            return f"Chamada {no.nome}"
        case _:
            return type(no).__name__


def _filhos(no: No) -> list[tuple[str | None, No]]:
    """Filhos de um nó, com o papel de cada um quando ajuda a leitura."""
    match no:
        case Programa():
            return [(None, n) for n in no.registros + no.funcoes + no.comandos]
        case Registro():
            return [(None, c) for c in no.campos]
        case Funcao():
            return [(None, n) for n in no.corpo.comandos]
        case Bloco():
            return [(None, n) for n in no.comandos]
        case DeclaracaoVar() | Mostre() | Retorne():
            return [(None, no.valor)]
        case Atribuicao(alvo=Variavel()):
            return [(None, no.valor)]
        case Atribuicao():
            return [("alvo", no.alvo), ("valor", no.valor)]
        case Se():
            filhos = [("condicao", no.condicao), ("entao", no.entao)]
            if no.senao is not None:
                filhos.append(("senao", no.senao))
            return filhos
        case Enquanto():
            return [("condicao", no.condicao), ("corpo", no.corpo)]
        case Escolha():
            filhos = [("valor", no.expressao)] + [(None, c) for c in no.casos]
            if no.padrao is not None:
                filhos.append(("padrao", no.padrao))
            return filhos
        case Caso():
            return [(None, n) for n in no.corpo.comandos]
        case ParaCada():
            return [("em", no.colecao), ("corpo", no.corpo)]
        case ComandoChamada():
            return [(None, no.chamada)]
        case ListaLiteral():
            return [(None, e) for e in no.elementos]
        case AcessoIndice():
            return [("base", no.base), ("indice", no.indice)]
        case AcessoCampo():
            return [(None, no.base)]
        case Binaria():
            return [(None, no.esquerda), (None, no.direita)]
        case Unaria():
            return [(None, no.operando)]
        case Chamada():
            return [(None, a) for a in no.argumentos]
        case _:
            return []


def imprimir_ast(no: No) -> str:
    """Desenha a árvore em texto, no formato do comando 'tree'."""
    linhas = [_rotulo(no)]

    def visitar(atual: No, prefixo: str):
        filhos = _filhos(atual)
        for i, (papel, filho) in enumerate(filhos):
            ultimo = i == len(filhos) - 1
            ramo = "└── " if ultimo else "├── "
            texto = f"{papel}: {_rotulo(filho)}" if papel else _rotulo(filho)
            linhas.append(prefixo + ramo + texto)
            visitar(filho, prefixo + ("    " if ultimo else "│   "))

    visitar(no, "")
    return "\n".join(linhas)
