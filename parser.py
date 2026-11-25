"""
parser.py — Analisador sintático da RedC.

Parser de descida recursiva escrito à mão a partir da gramática
(diário #13 e #19). Cada regra da gramática vira um método; o parser
decide o caminho olhando só o token atual (gramática LL(1)).

Entrada: lista de tokens do lexer. Saída: AST (redc_ast.Programa).
"""

from contextlib import contextmanager

from errors import ErroSintatico
from redc_ast import (
    AcessoCampo, AcessoIndice, Atribuicao, Binaria, Bloco, CampoRegistro, Caso,
    Chamada, ComandoChamada, DeclaracaoVar, Enquanto, Escolha, Funcao,
    ListaLiteral, Literal, Mostre, ParaCada, Parametro, Programa, Registro,
    Retorne, Se, TipoColecao, TipoRegistro, Unaria, Variavel,
)
from tokens import PALAVRAS_RESERVADAS, SIMBOLOS_SIMPLES, TipoToken as T, Token

# Nome legível de cada tipo de token, usado nas mensagens de erro.
_NOMES = {tipo: f"'{lex}'" for lex, tipo in PALAVRAS_RESERVADAS.items()}
_NOMES |= {tipo: f"'{lex}'" for lex, tipo in SIMBOLOS_SIMPLES.items()}
_NOMES |= {
    T.IGUAL: "'=='", T.DIFERENTE: "'!='", T.MENOR: "'<'", T.MENOR_IGUAL: "'<='",
    T.MAIOR: "'>'", T.MAIOR_IGUAL: "'>='", T.ATRIB: "'='", T.TIPO: "'::'",
    T.IDENT: "um identificador", T.LIT_INTEIRO: "um número inteiro",
    T.EOF: "fim do arquivo",
}

TIPOS = (T.INTEIRO, T.REAL, T.TEXTO, T.LOGICO)

# Profundidade máxima de parênteses, blocos e operadores unários aninhados.
# Sem esse limite, um programa como '((((...1...))))' com milhares de
# níveis estouraria a pilha do próprio Python dentro do parser.
LIMITE_ANINHAMENTO = 200


def _descrever(tok: Token) -> str:
    """Como o token encontrado aparece na mensagem de erro."""
    if tok.tipo == T.EOF:
        return "fim do arquivo"
    if tok.tipo == T.IDENT:
        return f"identificador '{tok.lexema}'"
    return f"'{tok.lexema}'"


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
        self.profundidade = 0

    # ---------- navegação ----------

    def _atual(self) -> Token:
        return self.tokens[self.pos]

    def _anterior(self) -> Token:
        return self.tokens[self.pos - 1]

    def _verifica(self, *tipos: T) -> bool:
        return self._atual().tipo in tipos

    def _avancar(self) -> Token:
        tok = self._atual()
        if tok.tipo != T.EOF:
            self.pos += 1
        return tok

    def _aceitar(self, *tipos: T) -> Token | None:
        return self._avancar() if self._verifica(*tipos) else None

    def _erro(self, mensagem: str, tok: Token | None = None) -> ErroSintatico:
        tok = tok or self._atual()
        return ErroSintatico(mensagem, tok.linha, tok.coluna)

    def _consumir(self, tipo: T, dica: str | None = None) -> Token:
        if self._verifica(tipo):
            return self._avancar()
        msg = f"esperado {_NOMES[tipo]}, encontrado {_descrever(self._atual())}"
        raise self._erro(f"{msg} ({dica})" if dica else msg)

    @contextmanager
    def _nivel(self):
        """Marca a entrada em um nível de aninhamento (bloco, expressão, tipo ou unário)."""
        self.profundidade += 1
        if self.profundidade > LIMITE_ANINHAMENTO:
            raise self._erro(f"aninhamento profundo demais: mais de {LIMITE_ANINHAMENTO} "
                             "níveis de blocos, parênteses ou operadores seguidos")
        try:
            yield
        finally:
            self.profundidade -= 1

    def _fim_comando(self):
        """';' ausente é apontado logo após o último token do comando,
        e não no início da linha seguinte."""
        if self._aceitar(T.PONTO_VIRGULA):
            return
        ant = self._anterior()
        raise ErroSintatico("esperado ';' no fim do comando",
                            ant.linha, ant.coluna + len(ant.lexema))

    def _bloco_nao_fechado(self, abre: Token) -> ErroSintatico:
        return self._erro(f"o bloco aberto na linha {abre.linha} não foi fechado; esperado '}}'")

    # ---------- programa ----------

    def analisar(self) -> Programa:
        # programa → { registro | funcao | comando } EOF
        registros, funcoes, comandos = [], [], []
        while not self._verifica(T.EOF):
            if self._verifica(T.REGISTRO):
                registros.append(self._registro())
            elif self._verifica(T.FUNCAO):
                funcoes.append(self._funcao())
            else:
                comandos.append(self._comando())
        return Programa(funcoes, comandos, registros=registros, linha=1, coluna=1)

    def _registro(self) -> Registro:
        # registro → "registro" IDENT "{" campo { campo } "}"
        # campo    → IDENT "::" tipo ";"
        inicio = self._avancar()
        nome = self._consumir(T.IDENT, "nome do registro")
        abre = self._consumir(T.ABRE_CHAVE)
        campos = []
        while not self._verifica(T.FECHA_CHAVE):
            if self._verifica(T.EOF):
                raise self._bloco_nao_fechado(abre)
            campo = self._consumir(T.IDENT, "nome do campo")
            self._consumir(T.TIPO, "todo campo declara o tipo com '::'")
            tipo = self._tipo()
            self._fim_comando()
            campos.append(CampoRegistro(campo.lexema, tipo,
                                        linha=campo.linha, coluna=campo.coluna))
        self._avancar()
        if not campos:
            raise self._erro(f"o registro '{nome.lexema}' precisa de pelo menos um campo", nome)
        return Registro(nome.lexema, campos, linha=inicio.linha, coluna=inicio.coluna)

    def _funcao(self) -> Funcao:
        # funcao → "funcao" IDENT "(" [ parametro { "," parametro } ] ")" "::" tipo bloco
        inicio = self._avancar()
        nome = self._consumir(T.IDENT, "nome da função")
        self._consumir(T.ABRE_PAR)
        parametros = []
        if not self._verifica(T.FECHA_PAR):
            parametros.append(self._parametro())
            while self._aceitar(T.VIRGULA):
                parametros.append(self._parametro())
        self._consumir(T.FECHA_PAR)
        self._consumir(T.TIPO, "toda função declara o tipo de retorno com '::'")
        tipo = self._tipo()
        corpo = self._bloco()
        return Funcao(nome.lexema, parametros, tipo, corpo,
                      linha=inicio.linha, coluna=inicio.coluna)

    def _parametro(self) -> Parametro:
        # parametro → IDENT "::" tipo
        nome = self._consumir(T.IDENT, "nome do parâmetro")
        self._consumir(T.TIPO, "todo parâmetro declara o tipo com '::'")
        return Parametro(nome.lexema, self._tipo(), linha=nome.linha, coluna=nome.coluna)

    def _tipo(self):
        # tipo → "inteiro" | "real" | "texto" | "logico"
        #      | IDENT                              (registro)
        #      | "[" tipo [ ";" LIT_INTEIRO ] "]"    (array com tamanho; lista sem)
        if self._verifica(*TIPOS):
            return self._avancar().lexema
        if self._verifica(T.IDENT):
            tok = self._avancar()
            return TipoRegistro(tok.lexema, linha=tok.linha, coluna=tok.coluna)
        if self._aceitar(T.ABRE_COL):
            with self._nivel():
                elemento = self._tipo()
            tamanho = None
            if self._aceitar(T.PONTO_VIRGULA):
                tamanho = self._consumir(T.LIT_INTEIRO, "tamanho do array").valor
            self._consumir(T.FECHA_COL)
            return TipoColecao(elemento, tamanho)
        raise self._erro("esperado um tipo (inteiro, real, texto, logico, um registro, "
                         f"[tipo] ou [tipo; tamanho]), encontrado {_descrever(self._atual())}")

    def _bloco(self) -> Bloco:
        # bloco → "{" { comando } "}"
        abre = self._consumir(T.ABRE_CHAVE)
        comandos = []
        with self._nivel():
            while not self._verifica(T.FECHA_CHAVE):
                if self._verifica(T.EOF):
                    raise self._bloco_nao_fechado(abre)
                comandos.append(self._comando())
        self._avancar()
        return Bloco(comandos, linha=abre.linha, coluna=abre.coluna)

    # ---------- comandos ----------

    def _comando(self):
        tok = self._atual()
        match tok.tipo:
            case T.SEJA:
                return self._declaracao()
            case T.SE:
                return self._se()
            case T.ENQUANTO:
                return self._enquanto()
            case T.ESCOLHA:
                return self._escolha()
            case T.PARA:
                return self._para_cada()
            case T.MOSTRE:
                return self._mostre()
            case T.RETORNE:
                return self._retorne()
            case T.IDENT:
                return self._comando_ident()
            case T.FUNCAO:
                raise self._erro("funções só podem ser declaradas fora de blocos")
            case T.REGISTRO:
                raise self._erro("registros só podem ser declarados fora de blocos")
            case T.SENAO:
                raise self._erro("'senao' sem 'se' correspondente")
            case T.CASO | T.PADRAO:
                raise self._erro(f"'{tok.lexema}' só pode aparecer dentro de 'escolha'")
            case _:
                raise self._erro("comando inválido: um comando não pode começar "
                                 f"com {_descrever(tok)}")

    def _declaracao(self) -> DeclaracaoVar:
        # declaracao → "seja" IDENT "::" tipo "=" expressao ";"
        inicio = self._avancar()
        nome = self._consumir(T.IDENT, "nome da variável")
        self._consumir(T.TIPO, "a declaração é 'seja nome :: tipo = valor;'")
        tipo = self._tipo()
        self._consumir(T.ATRIB, "toda variável começa com um valor")
        valor = self._expressao()
        self._fim_comando()
        return DeclaracaoVar(nome.lexema, tipo, valor,
                             linha=inicio.linha, coluna=inicio.coluna)

    def _comando_ident(self):
        # comando_ident → IDENT ( chamada | { acesso } "=" expressao ) ";"
        # Fatorado à esquerda: chamada e atribuição começam com IDENT, e o
        # token seguinte decide: '(' é chamada; '[', '.' ou '=' é atribuição.
        ident = self._avancar()
        if self._verifica(T.ABRE_PAR):
            chamada = self._chamada(ident)
            self._fim_comando()
            return ComandoChamada(chamada, linha=ident.linha, coluna=ident.coluna)
        alvo = Variavel(ident.lexema, linha=ident.linha, coluna=ident.coluna)
        while self._verifica(T.ABRE_COL, T.PONTO):
            alvo = self._acesso(alvo)
        if self._aceitar(T.ATRIB):
            valor = self._expressao()
            self._fim_comando()
            return Atribuicao(alvo, valor, linha=ident.linha, coluna=ident.coluna)
        esperado = "'='" if alvo is not None and not isinstance(alvo, Variavel) else "'=' ou '('"
        raise self._erro(f"esperado {esperado} depois de '{ident.lexema}', "
                         f"encontrado {_descrever(self._atual())}")

    def _se(self) -> Se:
        # se → "se" "(" expressao ")" bloco [ "senao" ( se | bloco ) ]
        inicio = self._avancar()
        self._consumir(T.ABRE_PAR)
        condicao = self._expressao()
        self._consumir(T.FECHA_PAR)
        entao = self._bloco()
        senao = None
        if self._aceitar(T.SENAO):
            senao = self._se() if self._verifica(T.SE) else self._bloco()
        return Se(condicao, entao, senao, linha=inicio.linha, coluna=inicio.coluna)

    def _enquanto(self) -> Enquanto:
        # enquanto → "enquanto" "(" expressao ")" bloco
        inicio = self._avancar()
        self._consumir(T.ABRE_PAR)
        condicao = self._expressao()
        self._consumir(T.FECHA_PAR)
        corpo = self._bloco()
        return Enquanto(condicao, corpo, linha=inicio.linha, coluna=inicio.coluna)

    def _escolha(self) -> Escolha:
        # escolha → "escolha" "(" expressao ")" "{" caso { caso } [ "padrao" bloco ] "}"
        # caso    → "caso" valor_caso { "," valor_caso } bloco
        inicio = self._avancar()
        self._consumir(T.ABRE_PAR)
        expressao = self._expressao()
        self._consumir(T.FECHA_PAR)
        abre = self._consumir(T.ABRE_CHAVE)
        casos, padrao = [], None
        with self._nivel():
            while not self._verifica(T.FECHA_CHAVE):
                if self._verifica(T.EOF):
                    raise self._bloco_nao_fechado(abre)
                if self._verifica(T.CASO):
                    if padrao is not None:
                        raise self._erro("'caso' depois de 'padrao'; o 'padrao' "
                                         "precisa ser o último")
                    tok = self._avancar()
                    valores = [self._valor_caso()]
                    while self._aceitar(T.VIRGULA):
                        valores.append(self._valor_caso())
                    corpo = self._bloco()
                    casos.append(Caso(valores, corpo, linha=tok.linha, coluna=tok.coluna))
                elif self._verifica(T.PADRAO):
                    if padrao is not None:
                        raise self._erro("'padrao' repetido; cada 'escolha' tem no máximo um")
                    self._avancar()
                    padrao = self._bloco()
                else:
                    raise self._erro("esperado 'caso' ou 'padrao' dentro de 'escolha', "
                                     f"encontrado {_descrever(self._atual())}")
        self._avancar()
        if not casos:
            raise self._erro("'escolha' precisa de pelo menos um 'caso'", inicio)
        return Escolha(expressao, casos, padrao, linha=inicio.linha, coluna=inicio.coluna)

    def _valor_caso(self) -> Literal:
        # valor_caso → [ "-" ] LIT_INTEIRO | LIT_TEXTO
        tok = self._atual()
        pos = {"linha": tok.linha, "coluna": tok.coluna}
        if self._aceitar(T.MENOS):
            numero = self._consumir(T.LIT_INTEIRO, "depois do '-' de um caso")
            return Literal(-numero.valor, "inteiro", **pos)
        if self._aceitar(T.LIT_INTEIRO):
            return Literal(tok.valor, "inteiro", **pos)
        if self._aceitar(T.LIT_TEXTO):
            return Literal(tok.valor, "texto", **pos)
        raise self._erro("o valor de um 'caso' precisa ser um número inteiro ou um texto "
                         f"fixo, encontrado {_descrever(tok)}")

    def _para_cada(self) -> ParaCada:
        # para_cada → "para" "cada" IDENT "em" expressao bloco
        inicio = self._avancar()
        self._consumir(T.CADA, "o laço é 'para cada item em colecao { ... }'")
        nome = self._consumir(T.IDENT, "nome da variável do laço")
        self._consumir(T.EM, "o laço é 'para cada item em colecao { ... }'")
        colecao = self._expressao()
        corpo = self._bloco()
        return ParaCada(nome.lexema, colecao, corpo, linha=inicio.linha, coluna=inicio.coluna)

    def _mostre(self) -> Mostre:
        # mostre → "mostre" "(" expressao ")" ";"
        inicio = self._avancar()
        self._consumir(T.ABRE_PAR)
        valor = self._expressao()
        self._consumir(T.FECHA_PAR)
        self._fim_comando()
        return Mostre(valor, linha=inicio.linha, coluna=inicio.coluna)

    def _retorne(self) -> Retorne:
        # retorne → "retorne" expressao ";"
        inicio = self._avancar()
        valor = self._expressao()
        self._fim_comando()
        return Retorne(valor, linha=inicio.linha, coluna=inicio.coluna)

    # ---------- expressões (da menor para a maior precedência) ----------

    def _expressao(self):
        with self._nivel():
            return self._ou()

    def _binaria(self, proximo, *operadores: T):
        """Regra genérica: proximo { op proximo }, associativa à esquerda."""
        esquerda = proximo()
        while self._verifica(*operadores):
            op = self._avancar()
            direita = proximo()
            esquerda = Binaria(op.lexema, esquerda, direita,
                               linha=op.linha, coluna=op.coluna)
        return esquerda

    def _ou(self):
        return self._binaria(self._e, T.OU)

    def _e(self):
        return self._binaria(self._igualdade, T.E)

    def _igualdade(self):
        return self._binaria(self._relacional, T.IGUAL, T.DIFERENTE)

    def _relacional(self):
        return self._binaria(self._aditiva, T.MENOR, T.MENOR_IGUAL,
                             T.MAIOR, T.MAIOR_IGUAL)

    def _aditiva(self):
        return self._binaria(self._multiplicativa, T.MAIS, T.MENOS)

    def _multiplicativa(self):
        return self._binaria(self._unaria, T.MULT, T.DIV, T.MOD)

    def _unaria(self):
        # unaria → ( "-" | "nao" ) unaria | posfixa
        if self._verifica(T.MENOS, T.NAO):
            op = self._avancar()
            with self._nivel():
                operando = self._unaria()
            return Unaria(op.lexema, operando, linha=op.linha, coluna=op.coluna)
        return self._posfixa()

    def _posfixa(self):
        # posfixa → primaria { acesso }
        base = self._primaria()
        while self._verifica(T.ABRE_COL, T.PONTO):
            base = self._acesso(base)
        return base

    def _acesso(self, base):
        # acesso → "[" expressao "]" | "." IDENT
        if self._verifica(T.ABRE_COL):
            abre = self._avancar()
            indice = self._expressao()
            self._consumir(T.FECHA_COL)
            return AcessoIndice(base, indice, linha=abre.linha, coluna=abre.coluna)
        ponto = self._avancar()
        campo = self._consumir(T.IDENT, "nome do campo")
        return AcessoCampo(base, campo.lexema, linha=ponto.linha, coluna=ponto.coluna)

    def _primaria(self):
        # primaria → literal | IDENT [ chamada ] | "texto" chamada
        #          | "(" expressao ")" | "[" [ expressao { "," expressao } ] "]"
        tok = self._atual()
        pos = {"linha": tok.linha, "coluna": tok.coluna}
        match tok.tipo:
            case T.LIT_INTEIRO:
                self._avancar()
                return Literal(tok.valor, "inteiro", **pos)
            case T.LIT_REAL:
                self._avancar()
                return Literal(tok.valor, "real", **pos)
            case T.LIT_TEXTO:
                self._avancar()
                return Literal(tok.valor, "texto", **pos)
            case T.VERDADEIRO | T.FALSO:
                self._avancar()
                return Literal(tok.tipo == T.VERDADEIRO, "logico", **pos)
            case T.IDENT:
                self._avancar()
                if self._verifica(T.ABRE_PAR):
                    return self._chamada(tok)
                return Variavel(tok.lexema, **pos)
            case T.TEXTO:
                # O nome do tipo usado como conversão explícita: texto(10).
                # Um tipo nunca começa uma expressão de outro jeito, então
                # a gramática continua LL(1).
                self._avancar()
                if not self._verifica(T.ABRE_PAR):
                    raise self._erro("esperado '(' depois de 'texto' (a conversão "
                                     f"é texto(valor)), encontrado {_descrever(self._atual())}")
                return self._chamada(tok)
            case T.ABRE_PAR:
                self._avancar()
                expr = self._expressao()
                self._consumir(T.FECHA_PAR)
                return expr
            case T.ABRE_COL:
                self._avancar()
                elementos = []
                if not self._verifica(T.FECHA_COL):
                    elementos.append(self._expressao())
                    while self._aceitar(T.VIRGULA):
                        elementos.append(self._expressao())
                self._consumir(T.FECHA_COL)
                return ListaLiteral(elementos, **pos)
            case _:
                raise self._erro(f"esperado uma expressão, encontrado {_descrever(tok)}")

    def _chamada(self, ident: Token) -> Chamada:
        # chamada → "(" [ expressao { "," expressao } ] ")"
        self._consumir(T.ABRE_PAR)
        argumentos = []
        if not self._verifica(T.FECHA_PAR):
            argumentos.append(self._expressao())
            while self._aceitar(T.VIRGULA):
                argumentos.append(self._expressao())
        self._consumir(T.FECHA_PAR)
        return Chamada(ident.lexema, argumentos, linha=ident.linha, coluna=ident.coluna)


def analisar(tokens: list[Token]) -> Programa:
    """Atalho: tokens -> AST."""
    return Parser(tokens).analisar()
