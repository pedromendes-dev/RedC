"""
tokens.py — Definição dos tokens da linguagem RedC.

Um token é a menor unidade com significado no código-fonte:
uma palavra reservada, um identificador, um literal, um operador
ou um delimitador. O lexer transforma o texto em uma lista de tokens.
"""

from dataclasses import dataclass
from enum import Enum, auto


class TipoToken(Enum):
    # --- Palavras reservadas: declaração e tipos ---
    SEJA = auto()
    INTEIRO = auto()
    REAL = auto()
    TEXTO = auto()
    LOGICO = auto()

    # --- Palavras reservadas: condição ---
    SE = auto()
    SENAO = auto()
    ESCOLHA = auto()
    CASO = auto()
    PADRAO = auto()

    # --- Palavras reservadas: repetição ---
    ENQUANTO = auto()
    PARA = auto()
    CADA = auto()
    EM = auto()

    # --- Palavras reservadas: funções, saída e estruturas ---
    FUNCAO = auto()
    RETORNE = auto()
    MOSTRE = auto()
    REGISTRO = auto()

    # --- Palavras reservadas: literais e operadores lógicos ---
    VERDADEIRO = auto()
    FALSO = auto()
    E = auto()
    OU = auto()
    NAO = auto()

    # --- Identificador e literais ---
    IDENT = auto()        # nome de variável, função ou registro
    LIT_INTEIRO = auto()  # 35
    LIT_REAL = auto()     # 3.14
    LIT_TEXTO = auto()    # "olá"

    # --- Operadores aritméticos ---
    MAIS = auto()         # +
    MENOS = auto()        # -
    MULT = auto()         # *
    DIV = auto()          # /
    MOD = auto()          # %

    # --- Operadores relacionais ---
    IGUAL = auto()        # ==
    DIFERENTE = auto()    # !=
    MENOR = auto()        # <
    MENOR_IGUAL = auto()  # <=
    MAIOR = auto()        # >
    MAIOR_IGUAL = auto()  # >=

    # --- Atribuição e tipo ---
    ATRIB = auto()        # =
    TIPO = auto()         # ::

    # --- Delimitadores ---
    PONTO_VIRGULA = auto()  # ;
    VIRGULA = auto()        # ,
    ABRE_PAR = auto()       # (
    FECHA_PAR = auto()      # )
    ABRE_CHAVE = auto()     # {
    FECHA_CHAVE = auto()    # }
    ABRE_COL = auto()       # [
    FECHA_COL = auto()      # ]
    PONTO = auto()          # .

    # --- Controle ---
    EOF = auto()            # fim do arquivo


# Lexema -> tipo do token. O lexer lê uma palavra e consulta este
# dicionário: se encontrar, é palavra reservada; se não, é IDENT.
PALAVRAS_RESERVADAS = {
    "seja": TipoToken.SEJA,
    "inteiro": TipoToken.INTEIRO,
    "real": TipoToken.REAL,
    "texto": TipoToken.TEXTO,
    "logico": TipoToken.LOGICO,
    "se": TipoToken.SE,
    "senao": TipoToken.SENAO,
    "escolha": TipoToken.ESCOLHA,
    "caso": TipoToken.CASO,
    "padrao": TipoToken.PADRAO,
    "enquanto": TipoToken.ENQUANTO,
    "para": TipoToken.PARA,
    "cada": TipoToken.CADA,
    "em": TipoToken.EM,
    "funcao": TipoToken.FUNCAO,
    "retorne": TipoToken.RETORNE,
    "mostre": TipoToken.MOSTRE,
    "registro": TipoToken.REGISTRO,
    "verdadeiro": TipoToken.VERDADEIRO,
    "falso": TipoToken.FALSO,
    "e": TipoToken.E,
    "ou": TipoToken.OU,
    "nao": TipoToken.NAO,
}

# Símbolos de 1 caractere que nunca começam um símbolo de 2.
SIMBOLOS_SIMPLES = {
    "+": TipoToken.MAIS,
    "-": TipoToken.MENOS,
    "*": TipoToken.MULT,
    "/": TipoToken.DIV,
    "%": TipoToken.MOD,
    ";": TipoToken.PONTO_VIRGULA,
    ",": TipoToken.VIRGULA,
    "(": TipoToken.ABRE_PAR,
    ")": TipoToken.FECHA_PAR,
    "{": TipoToken.ABRE_CHAVE,
    "}": TipoToken.FECHA_CHAVE,
    "[": TipoToken.ABRE_COL,
    "]": TipoToken.FECHA_COL,
    ".": TipoToken.PONTO,
}


@dataclass(frozen=True)
class Token:
    tipo: TipoToken
    lexema: str     # o texto exato lido do código-fonte
    valor: object   # valor convertido (int, float, str) ou None
    linha: int
    coluna: int

    def __str__(self) -> str:
        return f"{self.linha}:{self.coluna}\t{self.tipo.name:<14} {self.lexema!r}"
