"""
codegen.py — Gerador de código da RedC.

Transforma a AST (já verificada pela semântica) em bytecode para uma
máquina de PILHA: as instruções tiram operandos do topo da pilha e
colocam o resultado de volta. Exemplo, 'n * 2':

    LOAD 0        pilha: [n]
    PUSH 2        pilha: [n, 2]
    MUL           pilha: [n*2]

Layout do bytecode: o programa principal vem primeiro e termina em HALT;
depois vem o código de cada função. Saltos (JUMP) apontam para o índice
da instrução de destino.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from redc_ast import (
    AcessoCampo, AcessoIndice, Atribuicao, Binaria, Chamada, ComandoChamada,
    DeclaracaoVar, Enquanto, Escolha, Funcao, ListaLiteral, Literal, Mostre,
    ParaCada, Programa, Retorne, Se, TipoColecao, Unaria, Variavel,
)

# Conjunto de instruções (diário #16):
#   PUSH v      empilha a constante v
#   LOAD s      empilha a variável da posição s do quadro atual
#   STORE s     desempilha e guarda na posição s
#   POP         descarta o topo
#   TO_REAL     converte o topo de inteiro para real
#   TO_TEXT     converte o topo para texto, no mesmo formato do mostre
#   ADD SUB MUL DIV_INT DIV_REAL MOD CONCAT NEG     aritmética
#   EQ NE LT LE GT GE NOT                            comparação e lógica
#   JUMP a      salta para a instrução a
#   JUMP_IF_FALSE a / JUMP_IF_TRUE a                 desempilha e salta se falso / verdadeiro
#   CALL f n    chama a função f com n argumentos (que estão na pilha)
#   RET         desempilha o valor de retorno e volta para quem chamou
#   PRINT       desempilha e mostra
#   HALT        fim do programa
# Coleções e registros (diário #19):
#   MAKE_ARRAY n      desempilha n valores e empilha uma coleção com eles
#   GET_INDEX         desempilha índice e coleção; empilha o elemento
#   SET_INDEX         desempilha valor, índice e coleção; guarda o valor na posição
#   LEN               desempilha uma coleção ou texto; empilha o tamanho
#   APPEND            desempilha valor e lista; acrescenta e empilha o novo tamanho
#   NEW_RECORD r n    desempilha n valores e empilha um registro r com eles
#   GET_FIELD i       desempilha um registro; empilha o campo i
#   SET_FIELD i       desempilha valor e registro; guarda o valor no campo i

ARITMETICA = {"+": "ADD", "-": "SUB", "*": "MUL", "%": "MOD"}
COMPARACAO = {"==": "EQ", "!=": "NE", "<": "LT", "<=": "LE", ">": "GT", ">=": "GE"}


@dataclass
class Instrucao:
    op: str
    arg: object = None
    arg2: object = None
    linha: int = 0          # linha/coluna do código-fonte, para erros de execução
    coluna: int = 0

    def __str__(self) -> str:
        partes = [self.op]
        for a in (self.arg, self.arg2):
            if a is None:
                continue
            if isinstance(a, bool):
                partes.append("verdadeiro" if a else "falso")
            elif isinstance(a, str) and self.op == "PUSH":
                partes.append(repr(a))
            else:
                partes.append(str(a))
        return " ".join(partes)


@dataclass
class InfoFuncao:
    nome: str
    endereco: int
    num_parametros: int
    tamanho_quadro: int


@dataclass
class Bytecode:
    instrucoes: list[Instrucao] = field(default_factory=list)
    funcoes: dict[str, InfoFuncao] = field(default_factory=dict)
    registros: dict[str, list[str]] = field(default_factory=dict)   # nome -> campos
    tamanho_quadro_principal: int = 0

    def listagem(self) -> str:
        """Bytecode em texto, com o início de cada função marcado."""
        inicios = {f.endereco: f for f in self.funcoes.values()}
        q = self.tamanho_quadro_principal
        linhas = []
        for nome, campos in self.registros.items():
            linhas.append(f"== registro {nome} ({', '.join(campos)}) ==")
        if linhas:
            linhas.append("")
        linhas.append(f"== principal ({q} variáve{'l' if q == 1 else 'is'}) ==")
        for i, ins in enumerate(self.instrucoes):
            if i in inicios:
                f = inicios[i]
                linhas.append("")
                linhas.append(f"== funcao {f.nome} ({f.num_parametros} parâmetro(s), "
                              f"{f.tamanho_quadro} variáve{'l' if f.tamanho_quadro == 1 else 'is'}) ==")
            comentario = f" ; linha {ins.linha}" if ins.linha else ""
            linhas.append(f"{i:04d}  {str(ins):<28}{comentario}".rstrip())
        return "\n".join(linhas)


class GeradorCodigo:
    def __init__(self):
        self.bc = Bytecode()
        self.funcao_atual: Funcao | None = None

    # ---------- utilitários ----------

    def _emitir(self, op, arg=None, arg2=None, no=None) -> int:
        """Acrescenta uma instrução e devolve seu endereço."""
        linha, coluna = (no.linha, no.coluna) if no is not None else (0, 0)
        self.bc.instrucoes.append(Instrucao(op, arg, arg2, linha, coluna))
        return len(self.bc.instrucoes) - 1

    def _aqui(self) -> int:
        return len(self.bc.instrucoes)

    def _corrigir(self, endereco: int, alvo: int):
        """Backpatching: o destino de um salto só é conhecido depois que o
        código entre o salto e o destino foi gerado."""
        self.bc.instrucoes[endereco].arg = alvo

    # ---------- programa ----------

    def gerar(self, programa: Programa) -> Bytecode:
        self.bc.tamanho_quadro_principal = programa.tamanho_quadro
        self.bc.registros = {r.nome: [c.nome for c in r.campos] for r in programa.registros}
        for comando in programa.comandos:
            self._comando(comando)
        self._emitir("HALT")

        for f in programa.funcoes:
            self.funcao_atual = f
            self.bc.funcoes[f.nome] = InfoFuncao(
                f.nome, self._aqui(), len(f.parametros), f.tamanho_quadro)
            for comando in f.corpo.comandos:
                self._comando(comando)
            self.funcao_atual = None
        return self.bc

    # ---------- comandos ----------

    def _comando(self, no):
        match no:
            case DeclaracaoVar():
                self._expressao(no.valor, destino=no.tipo)
                self._emitir("STORE", no.simbolo.slot, no=no)
            case Atribuicao():
                self._atribuicao(no)
            case Se():
                self._se(no)
            case Enquanto():
                inicio = self._aqui()
                self._expressao(no.condicao)
                saida = self._emitir("JUMP_IF_FALSE", None, no=no)
                for c in no.corpo.comandos:
                    self._comando(c)
                self._emitir("JUMP", inicio, no=no)
                self._corrigir(saida, self._aqui())
            case Escolha():
                self._escolha(no)
            case ParaCada():
                self._para_cada(no)
            case Mostre():
                self._expressao(no.valor)
                self._emitir("PRINT", no=no)
            case Retorne():
                self._expressao(no.valor, destino=self.funcao_atual.tipo_retorno)
                self._emitir("RET", no=no)
            case ComandoChamada():
                self._expressao(no.chamada)
                self._emitir("POP", no=no)    # valor devolvido não é usado

    def _atribuicao(self, no: Atribuicao):
        alvo = no.alvo
        match alvo:
            case Variavel():
                self._expressao(no.valor, destino=alvo.simbolo.tipo)
                self._emitir("STORE", alvo.simbolo.slot, no=no)
            case AcessoIndice():
                #   <colecao> <indice> <valor> SET_INDEX
                self._expressao(alvo.base)
                self._expressao(alvo.indice)
                self._expressao(no.valor, destino=alvo.tipo_resolvido)
                self._emitir("SET_INDEX", no=alvo)
            case AcessoCampo():
                #   <registro> <valor> SET_FIELD i
                self._expressao(alvo.base)
                self._expressao(no.valor, destino=alvo.tipo_resolvido)
                self._emitir("SET_FIELD", alvo.indice_campo, no=alvo)

    def _escolha(self, no: Escolha):
        # O valor é calculado uma vez e guardado num slot escondido.
        # Depois, um teste por valor de caso; o primeiro igual salta para o
        # corpo do caso. Sem fallthrough: cada corpo termina saltando para o fim.
        #     <valor> STORE t
        #     LOAD t  PUSH v1  EQ  JUMP_IF_TRUE caso1      (um teste por valor)
        #     ...
        #     JUMP padrao                                  (nenhum caso bateu)
        # caso1: <corpo> JUMP fim
        # ...
        # padrao: <corpo do padrao>
        # fim:
        self._expressao(no.expressao)
        self._emitir("STORE", no.slot_valor, no=no)
        testes = []
        for i, caso in enumerate(no.casos):
            for v in caso.valores:
                self._emitir("LOAD", no.slot_valor, no=v)
                self._emitir("PUSH", v.valor, no=v)
                self._emitir("EQ", no=v)
                testes.append((self._emitir("JUMP_IF_TRUE", None, no=v), i))
        nenhum = self._emitir("JUMP", None, no=no)
        saidas = []
        for i, caso in enumerate(no.casos):
            for salto, alvo in testes:
                if alvo == i:
                    self._corrigir(salto, self._aqui())
            for c in caso.corpo.comandos:
                self._comando(c)
            saidas.append(self._emitir("JUMP", None, no=caso))
        self._corrigir(nenhum, self._aqui())
        if no.padrao is not None:
            for c in no.padrao.comandos:
                self._comando(c)
        for salto in saidas:
            self._corrigir(salto, self._aqui())

    def _para_cada(self, no: ParaCada):
        # Um 'enquanto' sobre um índice escondido:
        #     <colecao> STORE c     PUSH 0 STORE i     LOAD c LEN STORE n
        # teste:
        #     LOAD i  LOAD n  LT  JUMP_IF_FALSE fim
        #     LOAD c  LOAD i  GET_INDEX  STORE item
        #     <corpo>
        #     LOAD i  PUSH 1  ADD  STORE i  JUMP teste
        # fim:
        # O tamanho é lido uma vez: o laço percorre os elementos que existiam
        # no início, mesmo que o corpo acrescente outros à lista.
        c, i, n = no.slot_colecao, no.slot_indice, no.slot_tamanho
        self._expressao(no.colecao)
        self._emitir("STORE", c, no=no)
        self._emitir("PUSH", 0, no=no)
        self._emitir("STORE", i, no=no)
        self._emitir("LOAD", c, no=no)
        self._emitir("LEN", no=no)
        self._emitir("STORE", n, no=no)
        teste = self._emitir("LOAD", i, no=no)
        self._emitir("LOAD", n, no=no)
        self._emitir("LT", no=no)
        saida = self._emitir("JUMP_IF_FALSE", None, no=no)
        self._emitir("LOAD", c, no=no)
        self._emitir("LOAD", i, no=no)
        self._emitir("GET_INDEX", no=no)
        self._emitir("STORE", no.simbolo.slot, no=no)
        for cmd in no.corpo.comandos:
            self._comando(cmd)
        self._emitir("LOAD", i, no=no)
        self._emitir("PUSH", 1, no=no)
        self._emitir("ADD", no=no)
        self._emitir("STORE", i, no=no)
        self._emitir("JUMP", teste, no=no)
        self._corrigir(saida, self._aqui())

    def _se(self, no: Se):
        #     <condicao>
        #     JUMP_IF_FALSE senao
        #     <entao>
        #     JUMP fim            (só se houver senao)
        # senao:
        #     <senao>
        # fim:
        self._expressao(no.condicao)
        para_senao = self._emitir("JUMP_IF_FALSE", None, no=no)
        for c in no.entao.comandos:
            self._comando(c)
        if no.senao is None:
            self._corrigir(para_senao, self._aqui())
            return
        para_fim = self._emitir("JUMP", None, no=no)
        self._corrigir(para_senao, self._aqui())
        if isinstance(no.senao, Se):
            self._se(no.senao)
        else:
            for c in no.senao.comandos:
                self._comando(c)
        self._corrigir(para_fim, self._aqui())

    # ---------- expressões ----------

    def _expressao(self, no, destino: str | None = None):
        """Gera o código que deixa o valor da expressão no topo da pilha.
        Se o destino é real e o valor é inteiro, converte (promoção)."""
        match no:
            case Literal():
                self._emitir("PUSH", no.valor, no=no)
            case ListaLiteral():
                # Os elementos seguem o tipo do destino ([real] promove 1 a 1.0);
                # sem destino (ex.: dentro de mostre), seguem o tipo do literal.
                if isinstance(destino, TipoColecao) and destino.elemento is not None:
                    tipo_elemento = destino.elemento
                else:
                    tipo_elemento = no.tipo_resolvido.elemento
                for e in no.elementos:
                    self._expressao(e, destino=tipo_elemento)
                self._emitir("MAKE_ARRAY", len(no.elementos), no=no)
            case Variavel():
                self._emitir("LOAD", no.simbolo.slot, no=no)
            case AcessoIndice():
                self._expressao(no.base)
                self._expressao(no.indice)
                self._emitir("GET_INDEX", no=no)
            case AcessoCampo():
                self._expressao(no.base)
                self._emitir("GET_FIELD", no.indice_campo, no=no)
            case Binaria():
                self._binaria(no)
            case Unaria():
                self._expressao(no.operando)
                self._emitir("NEG" if no.op == "-" else "NOT", no=no)
            case Chamada():
                self._chamada(no)

        if destino == "real" and no.tipo_resolvido == "inteiro":
            self._emitir("TO_REAL", no=no)

    def _chamada(self, no: Chamada):
        simbolo = no.simbolo
        if simbolo.categoria == "nativa":
            colecao = no.argumentos[0]
            self._expressao(colecao)
            if no.nome == "tamanho":
                self._emitir("LEN", no=no)
            elif no.nome == "texto":
                self._emitir("TO_TEXT", no=no)
            else:   # adicione(lista, valor)
                self._expressao(no.argumentos[1], destino=colecao.tipo_resolvido.elemento)
                self._emitir("APPEND", no=no)
        elif simbolo.categoria == "registro":
            for arg, (_, tipo_campo) in zip(no.argumentos, simbolo.campos):
                self._expressao(arg, destino=tipo_campo)
            self._emitir("NEW_RECORD", no.nome, len(no.argumentos), no=no)
        else:
            for arg, tipo_param in zip(no.argumentos, simbolo.parametros):
                self._expressao(arg, destino=tipo_param)
            self._emitir("CALL", no.nome, len(no.argumentos), no=no)

    def _binaria(self, no: Binaria):
        if no.op in ("e", "ou"):
            return self._logico_curto(no)

        self._expressao(no.esquerda)
        self._expressao(no.direita)
        tipos = (no.esquerda.tipo_resolvido, no.direita.tipo_resolvido)
        if no.op == "+" and tipos == ("texto", "texto"):
            op = "CONCAT"
        elif no.op == "/":
            op = "DIV_INT" if tipos == ("inteiro", "inteiro") else "DIV_REAL"
        else:
            op = ARITMETICA.get(no.op) or COMPARACAO[no.op]
        self._emitir(op, no=no)

    def _logico_curto(self, no: Binaria):
        # Curto-circuito: em 'a e b', se 'a' é falso, 'b' nem é avaliado.
        # Isso permite 'n != 0 e 10 / n > 1' sem dividir por zero.
        #     <a>
        #     JUMP_IF_FALSE curto    (no 'ou': JUMP_IF_TRUE)
        #     <b>
        #     JUMP fim
        # curto:
        #     PUSH falso             (no 'ou': verdadeiro)
        # fim:
        eh_e = no.op == "e"
        self._expressao(no.esquerda)
        salto = self._emitir("JUMP_IF_FALSE" if eh_e else "JUMP_IF_TRUE", None, no=no)
        self._expressao(no.direita)
        para_fim = self._emitir("JUMP", None, no=no)
        self._corrigir(salto, self._aqui())
        self._emitir("PUSH", not eh_e, no=no)
        self._corrigir(para_fim, self._aqui())


def gerar(programa: Programa) -> Bytecode:
    """Atalho: AST verificada -> bytecode."""
    return GeradorCodigo().gerar(programa)
