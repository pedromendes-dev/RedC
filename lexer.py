"""
lexer.py — Analisador léxico da RedC.

Percorre o código-fonte caractere por caractere (sem bibliotecas de
análise léxica, como exige o edital) e produz a lista de tokens.

Regras:
- espaços, tabs e quebras de linha são ignorados (só atualizam linha/coluna);
- '#' inicia um comentário até o fim da linha;
- identificadores: letra ASCII ou '_', seguido de letras, dígitos ou '_';
- números: '35' é inteiro, '3.14' é real;
- textos: entre aspas duplas, sem quebra de linha, com escapes \\n \\t \\" \\\\;
- '==' '!=' '<=' '>=' '::' são reconhecidos olhando 1 caractere à frente.
"""

from errors import ErroLexico
from tokens import PALAVRAS_RESERVADAS, SIMBOLOS_SIMPLES, TipoToken, Token

ESCAPES = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}


def _eh_letra(c: str) -> bool:
    # Só ASCII: identificadores sem acento (decisão #10 do diário).
    return ("a" <= c <= "z") or ("A" <= c <= "Z") or c == "_"


def _eh_digito(c: str) -> bool:
    return "0" <= c <= "9"


class Lexer:
    def __init__(self, fonte: str):
        self.fonte = fonte
        self.pos = 0       # índice do caractere atual
        self.linha = 1
        self.coluna = 1
        self.tokens: list[Token] = []

    # ---------- navegação ----------

    def _atual(self) -> str:
        return self.fonte[self.pos] if self.pos < len(self.fonte) else ""

    def _proximo(self) -> str:
        """Lookahead de 1 caractere."""
        i = self.pos + 1
        return self.fonte[i] if i < len(self.fonte) else ""

    def _avancar(self) -> str:
        c = self._atual()
        self.pos += 1
        if c == "\n":
            self.linha += 1
            self.coluna = 1
        else:
            self.coluna += 1
        return c

    def _adicionar(self, tipo, lexema, linha, coluna, valor=None):
        self.tokens.append(Token(tipo, lexema, valor, linha, coluna))

    # ---------- laço principal ----------

    def analisar(self) -> list[Token]:
        while self.pos < len(self.fonte):
            c = self._atual()
            linha, coluna = self.linha, self.coluna

            if c in " \t\r\n":
                self._avancar()
            elif c == "#":
                self._comentario()
            elif _eh_letra(c):
                self._palavra(linha, coluna)
            elif _eh_digito(c):
                self._numero(linha, coluna)
            elif c == '"':
                self._texto(linha, coluna)
            else:
                self._simbolo(linha, coluna)

        self._adicionar(TipoToken.EOF, "", self.linha, self.coluna)
        return self.tokens

    # ---------- reconhecedores ----------

    def _comentario(self):
        while self._atual() not in ("", "\n"):
            self._avancar()

    def _palavra(self, linha, coluna):
        inicio = self.pos
        while _eh_letra(self._atual()) or _eh_digito(self._atual()):
            self._avancar()

        # Letra acentuada colada no identificador: erro claro em vez de
        # dois tokens estranhos (ex.: 'senão' -> 'sen' + erro em 'ã').
        if self._atual() and not self._atual().isascii() and self._atual().isalpha():
            raise ErroLexico(
                f"caractere acentuado '{self._atual()}' em identificador; "
                "a RedC não aceita acentos fora de textos",
                self.linha, self.coluna,
            )

        lexema = self.fonte[inicio:self.pos]
        tipo = PALAVRAS_RESERVADAS.get(lexema, TipoToken.IDENT)
        self._adicionar(tipo, lexema, linha, coluna)

    def _numero(self, linha, coluna):
        inicio = self.pos
        while _eh_digito(self._atual()):
            self._avancar()

        tipo = TipoToken.LIT_INTEIRO
        # '.' só faz parte do número se vier um dígito depois: '3.14' é real,
        # mas em 'v.campo' o ponto é acesso a campo.
        if self._atual() == "." and _eh_digito(self._proximo()):
            tipo = TipoToken.LIT_REAL
            self._avancar()
            while _eh_digito(self._atual()):
                self._avancar()

        # Número colado em letra: '12abc' não é número nem identificador.
        if _eh_letra(self._atual()):
            raise ErroLexico(
                f"número malformado '{self.fonte[inicio:self.pos]}{self._atual()}'",
                linha, coluna,
            )

        lexema = self.fonte[inicio:self.pos]
        valor = int(lexema) if tipo == TipoToken.LIT_INTEIRO else float(lexema)
        self._adicionar(tipo, lexema, linha, coluna, valor)

    def _texto(self, linha, coluna):
        inicio = self.pos
        self._avancar()  # aspas de abertura
        chars = []
        while True:
            c = self._atual()
            if c == "" or c == "\n":
                raise ErroLexico("texto sem aspas de fechamento", linha, coluna)
            if c == '"':
                self._avancar()
                break
            if c == "\\":
                l, col = self.linha, self.coluna
                self._avancar()
                esc = self._atual()
                if esc not in ESCAPES:
                    raise ErroLexico(f"sequência de escape inválida '\\{esc}'", l, col)
                chars.append(ESCAPES[esc])
                self._avancar()
                continue
            chars.append(self._avancar())

        lexema = self.fonte[inicio:self.pos]
        self._adicionar(TipoToken.LIT_TEXTO, lexema, linha, coluna, "".join(chars))

    def _simbolo(self, linha, coluna):
        c = self._atual()
        prox = self._proximo()

        # Símbolos de 2 caracteres (lookahead de 1).
        duplos = {
            ("=", "="): TipoToken.IGUAL,
            ("!", "="): TipoToken.DIFERENTE,
            ("<", "="): TipoToken.MENOR_IGUAL,
            (">", "="): TipoToken.MAIOR_IGUAL,
            (":", ":"): TipoToken.TIPO,
        }
        if (c, prox) in duplos:
            self._avancar()
            self._avancar()
            self._adicionar(duplos[(c, prox)], c + prox, linha, coluna)
            return

        unicos = {"=": TipoToken.ATRIB, "<": TipoToken.MENOR, ">": TipoToken.MAIOR}
        if c in unicos:
            self._avancar()
            self._adicionar(unicos[c], c, linha, coluna)
            return

        if c in SIMBOLOS_SIMPLES:
            self._avancar()
            self._adicionar(SIMBOLOS_SIMPLES[c], c, linha, coluna)
            return

        # Mensagens específicas para os erros mais prováveis.
        if c == "!":
            raise ErroLexico("'!' sozinho não existe; use 'nao' ou '!='", linha, coluna)
        if c == ":":
            raise ErroLexico("':' sozinho não existe; para tipo use '::'", linha, coluna)
        raise ErroLexico(f"caractere inválido '{c}'", linha, coluna)


def analisar(fonte: str) -> list[Token]:
    """Atalho: texto -> lista de tokens."""
    return Lexer(fonte).analisar()
