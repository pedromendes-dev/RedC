"""
semantic.py — Análise semântica da RedC.

Percorre a AST uma vez e faz duas coisas ao mesmo tempo:

1. Escopos (Etapa 4): preenche a tabela de símbolos e detecta
   identificador não declarado, redeclarado, variável usada como função
   (e vice-versa), 'retorne' fora de função e acesso a variável global
   dentro de função.

2. Tipos (Etapa 5 e diário #19): calcula o tipo de cada expressão e
   verifica declarações, atribuições, operadores, condições, chamadas,
   retornos, índices, campos de registro, 'escolha' e 'para cada'.

Regras de tipo (diário #15 e #19):
- inteiro cabe em real (promoção automática); real NÃO cabe em inteiro;
- + - * /  : números; se um dos lados é real, o resultado é real;
             inteiro / inteiro é divisão inteira (7 / 2 = 3), como em C e Java;
- %        : só inteiros;
- +        : também junta dois textos;
- < <= > >= : números; resultado logico;
- == !=    : dois valores do mesmo tipo básico (ou dois números); arrays,
             listas e registros não são comparados com ==;
- e ou nao : só logico;
- condição de 'se' e 'enquanto' precisa ser logico;
- toda função precisa terminar com 'retorne' em todos os caminhos;
- um literal [1, 2, 3] serve para um array do mesmo tamanho ou para uma lista;
- uma variável array ou lista só recebe outra do MESMO tipo.
"""

from errors import ErroSemantico
from redc_ast import (
    AcessoCampo, AcessoIndice, Atribuicao, Binaria, Bloco, Chamada,
    ComandoChamada, DeclaracaoVar, Enquanto, Escolha, Funcao, ListaLiteral,
    Literal, Mostre, ParaCada, Programa, Retorne, Se, TipoColecao,
    TipoRegistro, Unaria, Variavel,
)
from symbols import Simbolo, TabelaSimbolos

NUMEROS = ("inteiro", "real")
ARITMETICOS = ("+", "-", "*", "/", "%")
RELACIONAIS = ("<", "<=", ">", ">=")
IGUALDADE = ("==", "!=")

# Funções nativas: nome -> tipo de retorno. As regras de cada uma estão
# em AnalisadorSemantico._nativa. 'adicione' devolve o novo tamanho da
# lista, como o push do JavaScript. 'texto' é a conversão explícita para
# texto (diário #21): o nome do tipo usado como função, como str() no Python.
NATIVAS = {"tamanho": "inteiro", "adicione": "inteiro", "texto": "texto"}
TIPOS_BASICOS = ("inteiro", "real", "texto", "logico")


# ---------------- Regras de tipo ----------------

def cabe_em(destino, origem) -> bool:
    """Um valor do tipo 'origem' pode ser guardado em 'destino'?"""
    if destino == origem:
        return True
    if destino == "real" and origem == "inteiro":
        return True
    # Um literal [a, b, c] vira array (se o tamanho bater) ou lista.
    if (isinstance(destino, TipoColecao) and isinstance(origem, TipoColecao)
            and origem.literal and not destino.literal):
        if destino.tamanho is not None and origem.tamanho != destino.tamanho:
            return False
        return origem.elemento is None or cabe_em(destino.elemento, origem.elemento)
    return False


def unificar(a, b):
    """Tipo comum a dois elementos de um mesmo literal, ou None se não houver.
    [1, 2.5] tem elementos real; [[1, 2], [3]] tem elementos listas de inteiro."""
    if a == b:
        return a
    if a in NUMEROS and b in NUMEROS:
        return "real"
    if isinstance(a, TipoColecao) and isinstance(b, TipoColecao):
        if a.literal and b.literal:
            if a.elemento is None or b.elemento is None:
                elemento = a.elemento if b.elemento is None else b.elemento
            else:
                elemento = unificar(a.elemento, b.elemento)
                if elemento is None:
                    return None
            tamanho = a.tamanho if a.tamanho == b.tamanho else None
            return TipoColecao(elemento, tamanho, literal=True)
        if cabe_em(a, b):
            return a
        if cabe_em(b, a):
            return b
    return None


def _composto(tipo) -> bool:
    return isinstance(tipo, (TipoColecao, TipoRegistro))


def _sempre_retorna(comandos: list) -> bool:
    """Todo caminho por esta lista de comandos termina em 'retorne'?"""
    for c in comandos:
        if isinstance(c, Retorne):
            return True
        if isinstance(c, Se) and _se_sempre_retorna(c):
            return True
        if isinstance(c, Escolha) and _escolha_sempre_retorna(c):
            return True
    return False


def _se_sempre_retorna(se: Se) -> bool:
    # Só conta se houver 'senao' e os DOIS lados retornarem.
    # 'enquanto' e 'para cada' nunca contam: o corpo pode não executar.
    if se.senao is None or not _sempre_retorna(se.entao.comandos):
        return False
    if isinstance(se.senao, Se):
        return _se_sempre_retorna(se.senao)
    return _sempre_retorna(se.senao.comandos)


def _escolha_sempre_retorna(esc: Escolha) -> bool:
    # Sem 'padrao', um valor fora dos casos não passa por nenhum retorne.
    return (esc.padrao is not None
            and all(_sempre_retorna(c.corpo.comandos) for c in esc.casos)
            and _sempre_retorna(esc.padrao.comandos))


def _constante_inteira(no):
    """Valor de um índice escrito como número fixo (3 ou -1), senão None."""
    if isinstance(no, Literal) and no.tipo == "inteiro":
        return no.valor
    if (isinstance(no, Unaria) and no.op == "-" and isinstance(no.operando, Literal)
            and no.operando.tipo == "inteiro"):
        return -no.operando.valor
    return None


class AnalisadorSemantico:
    def __init__(self):
        self.tabela = TabelaSimbolos()
        self.funcao_atual: Funcao | None = None
        self.globais: dict[str, int] = {}     # nome -> linha, para mensagens
        self.registros: dict[str, Simbolo] = {}
        self.proximo_slot = 0                  # próxima posição livre no quadro

    # ---------- programa ----------

    def analisar(self, programa: Programa) -> TabelaSimbolos:
        for nome, tipo in NATIVAS.items():
            self.tabela.declarar(Simbolo(nome, "nativa", tipo, 0, 0))
        self.globais = {c.nome: c.linha for c in programa.comandos
                        if isinstance(c, DeclaracaoVar)}

        # 1ª passada: nomes dos registros, depois seus campos. Em duas etapas
        # para que um registro possa usar outro declarado mais abaixo.
        for r in programa.registros:
            r.simbolo = self.tabela.declarar(Simbolo(
                r.nome, "registro", TipoRegistro(r.nome), r.linha, r.coluna))
            self.registros[r.nome] = r.simbolo
        for r in programa.registros:
            vistos = set()
            for c in r.campos:
                if c.nome in vistos:
                    raise ErroSemantico(f"o campo '{c.nome}' aparece duas vezes no "
                                        f"registro '{r.nome}'", c.linha, c.coluna)
                vistos.add(c.nome)
                self._validar_tipo(c.tipo, c)
            r.simbolo.campos = [(c.nome, c.tipo) for c in r.campos]
        self._verificar_ciclos(programa.registros)

        # 2ª passada: assinaturas de todas as funções (permite recursão e
        # chamar uma função declarada mais abaixo no arquivo).
        for f in programa.funcoes:
            for p in f.parametros:
                self._validar_tipo(p.tipo, p)
            self._validar_tipo(f.tipo_retorno, f)
            f.simbolo = self.tabela.declarar(Simbolo(
                f.nome, "funcao", f.tipo_retorno, f.linha, f.coluna,
                parametros=[p.tipo for p in f.parametros]))

        # 3ª passada: corpo de cada função, no seu próprio escopo.
        for f in programa.funcoes:
            self._funcao(f)

        # 4ª passada: programa principal, no escopo global.
        self.proximo_slot = 0
        for comando in programa.comandos:
            self._comando(comando)
        programa.tamanho_quadro = self.proximo_slot
        return self.tabela

    def _validar_tipo(self, tipo, no):
        """Confere se um tipo escrito no programa existe e faz sentido."""
        if isinstance(tipo, TipoRegistro):
            if tipo.nome not in self.registros:
                raise ErroSemantico(f"o tipo '{tipo.nome}' não existe",
                                    tipo.linha or no.linha, tipo.coluna or no.coluna)
        elif isinstance(tipo, TipoColecao):
            if tipo.tamanho is not None and tipo.tamanho < 1:
                raise ErroSemantico("um array precisa ter tamanho maior que zero",
                                    no.linha, no.coluna)
            self._validar_tipo(tipo.elemento, no)

    def _verificar_ciclos(self, registros):
        """Um registro que contém a si mesmo (direto ou por outro registro)
        não pode ser criado: seria preciso um valor dele para criar ele mesmo.
        Dentro de uma LISTA é permitido, porque a lista pode começar vazia."""
        def dependencias(tipo):
            while isinstance(tipo, TipoColecao) and tipo.tamanho is not None:
                tipo = tipo.elemento                     # array: precisa dos elementos
            return [tipo.nome] if isinstance(tipo, TipoRegistro) else []

        def visitar(nome, caminho):
            if nome in caminho:
                ciclo = " → ".join(caminho[caminho.index(nome):] + [nome])
                inicio = self.registros[caminho[0]]
                raise ErroSemantico(
                    f"o registro '{caminho[0]}' contém a si mesmo ({ciclo}); não há "
                    "como criar um valor dele (use uma lista para estruturas recursivas)",
                    inicio.linha, inicio.coluna)
            for _, tipo in self.registros[nome].campos:
                for dep in dependencias(tipo):
                    visitar(dep, caminho + [nome])

        for r in registros:
            visitar(r.nome, [])

    def _novo_slot(self) -> int:
        slot = self.proximo_slot
        self.proximo_slot += 1
        return slot

    def _declarar_variavel(self, nome, categoria, tipo, linha, coluna) -> Simbolo:
        return self.tabela.declarar(Simbolo(nome, categoria, tipo, linha, coluna,
                                            slot=self._novo_slot()))

    def _funcao(self, f: Funcao):
        self.funcao_atual = f
        self.proximo_slot = 0
        self.tabela.abrir_escopo(f"funcao {f.nome}")
        for p in f.parametros:
            p.simbolo = self._declarar_variavel(p.nome, "parametro", p.tipo,
                                                p.linha, p.coluna)
        for comando in f.corpo.comandos:
            self._comando(comando)
        self.tabela.fechar_escopo()

        if not _sempre_retorna(f.corpo.comandos):
            raise ErroSemantico(
                f"a função '{f.nome}' pode terminar sem 'retorne'; todo caminho "
                f"precisa devolver um valor {f.tipo_retorno}", f.linha, f.coluna)
        f.tamanho_quadro = self.proximo_slot
        self.funcao_atual = None

    def _bloco(self, bloco: Bloco, nome: str):
        self.tabela.abrir_escopo(f"{nome} (linha {bloco.linha})")
        for comando in bloco.comandos:
            self._comando(comando)
        self.tabela.fechar_escopo()

    # ---------- comandos ----------

    def _comando(self, no):
        match no:
            case DeclaracaoVar():
                self._validar_tipo(no.tipo, no)
                # O valor é analisado ANTES de declarar o nome:
                # em 'seja x :: inteiro = x;' o 'x' da direita não existe.
                tipo_valor = self._expressao(no.valor)
                self._exigir_tipo(no.tipo, tipo_valor, no.valor)
                no.simbolo = self._declarar_variavel(no.nome, "variavel", no.tipo,
                                                     no.linha, no.coluna)
            case Atribuicao():
                tipo_alvo = self._alvo(no.alvo)
                tipo_valor = self._expressao(no.valor)
                self._exigir_tipo(tipo_alvo, tipo_valor, no.valor)
            case Se():
                self._condicao(no.condicao, "se")
                self._bloco(no.entao, "se")
                if isinstance(no.senao, Se):
                    self._comando(no.senao)
                elif no.senao is not None:
                    self._bloco(no.senao, "senao")
            case Enquanto():
                self._condicao(no.condicao, "enquanto")
                self._bloco(no.corpo, "enquanto")
            case Escolha():
                self._escolha(no)
            case ParaCada():
                self._para_cada(no)
            case Mostre():
                self._expressao(no.valor)          # mostre aceita qualquer tipo
            case Retorne():
                if self.funcao_atual is None:
                    raise ErroSemantico("'retorne' só pode ser usado dentro de uma função",
                                        no.linha, no.coluna)
                tipo_valor = self._expressao(no.valor)
                esperado = self.funcao_atual.tipo_retorno
                if not cabe_em(esperado, tipo_valor):
                    raise ErroSemantico(
                        f"a função '{self.funcao_atual.nome}' retorna {esperado}, "
                        f"mas 'retorne' recebeu {tipo_valor}", no.valor.linha, no.valor.coluna)
            case ComandoChamada():
                self._expressao(no.chamada)        # o valor devolvido é descartado

    def _alvo(self, alvo) -> object:
        """Tipo do lado esquerdo de uma atribuição: variável, índice ou campo."""
        if isinstance(alvo, Variavel):
            alvo.simbolo = self._resolver_variavel(alvo.nome, alvo.linha, alvo.coluna)
            alvo.tipo_resolvido = alvo.simbolo.tipo
            return alvo.simbolo.tipo
        return self._expressao(alvo)

    def _escolha(self, no: Escolha):
        tipo = self._expressao(no.expressao)
        if tipo not in ("inteiro", "texto"):
            raise ErroSemantico(f"'escolha' compara valores inteiro ou texto, recebido {tipo}",
                                no.expressao.linha, no.expressao.coluna)
        no.slot_valor = self._novo_slot()
        vistos: dict = {}
        for caso in no.casos:
            for v in caso.valores:
                v.tipo_resolvido = v.tipo
                if v.tipo != tipo:
                    raise ErroSemantico(f"caso do tipo {v.tipo} em uma 'escolha' de {tipo}",
                                        v.linha, v.coluna)
                if v.valor in vistos:
                    exibicao = f'"{v.valor}"' if tipo == "texto" else v.valor
                    raise ErroSemantico(f"o caso {exibicao} já apareceu na linha "
                                        f"{vistos[v.valor]}", v.linha, v.coluna)
                vistos[v.valor] = v.linha
            self._bloco(caso.corpo, "caso")
        if no.padrao is not None:
            self._bloco(no.padrao, "padrao")

    def _para_cada(self, no: ParaCada):
        tipo = self._expressao(no.colecao)
        if not isinstance(tipo, TipoColecao):
            raise ErroSemantico(f"'para cada' percorre arrays e listas, recebido {tipo}",
                                no.colecao.linha, no.colecao.coluna)
        if tipo.elemento is None:
            raise ErroSemantico("não dá para percorrer uma lista vazia sem tipo; guarde-a "
                                "antes em uma variável com tipo", no.colecao.linha,
                                no.colecao.coluna)
        # Posições escondidas: a coleção, o índice atual e o tamanho no início.
        no.slot_colecao = self._novo_slot()
        no.slot_indice = self._novo_slot()
        no.slot_tamanho = self._novo_slot()
        # A variável do laço vive no escopo do laço, junto com o corpo.
        self.tabela.abrir_escopo(f"para cada (linha {no.linha})")
        no.simbolo = self._declarar_variavel(no.variavel, "variavel",
                                             self._concreto(tipo.elemento, no.colecao),
                                             no.linha, no.coluna)
        for comando in no.corpo.comandos:
            self._comando(comando)
        self.tabela.fechar_escopo()

    def _concreto(self, tipo, no):
        """Tipo de variável para um elemento vindo de um literal: [inteiro; 2]
        se todos os elementos tinham o mesmo tamanho, senão [inteiro]."""
        if not isinstance(tipo, TipoColecao) or not tipo.literal:
            return tipo
        if tipo.elemento is None:
            raise ErroSemantico("não dá para deduzir o tipo dos elementos de uma lista "
                                "vazia; guarde-a antes em uma variável com tipo",
                                no.linha, no.coluna)
        return TipoColecao(self._concreto(tipo.elemento, no), tipo.tamanho)

    def _exigir_tipo(self, esperado, recebido, no):
        if cabe_em(esperado, recebido):
            return
        msg = f"esperado {esperado}, recebido {recebido}"
        if esperado == "inteiro" and recebido == "real":
            msg += " (um real não cabe em inteiro sem perder as casas decimais)"
        elif isinstance(esperado, TipoColecao) and isinstance(recebido, TipoColecao):
            if (recebido.literal and esperado.tamanho is not None
                    and recebido.tamanho != esperado.tamanho):
                msg += (f" (o array tem {esperado.tamanho} posição(ões), e o valor tem "
                        f"{recebido.tamanho} elemento(s))")
            elif not recebido.literal and (esperado.tamanho is None) != (recebido.tamanho is None):
                msg += " (array e lista são tipos diferentes)"
        raise ErroSemantico(msg, no.linha, no.coluna)

    def _condicao(self, no, comando: str):
        tipo = self._expressao(no)
        if tipo != "logico":
            raise ErroSemantico(
                f"a condição do '{comando}' precisa ser logico, recebido {tipo}",
                no.linha, no.coluna)

    # ---------- expressões ----------

    def _expressao(self, no):
        """Devolve o tipo da expressão e o anota no próprio nó."""
        match no:
            case Literal():
                tipo = no.tipo
            case ListaLiteral():
                tipo = self._lista_literal(no)
            case Variavel():
                no.simbolo = self._resolver_variavel(no.nome, no.linha, no.coluna)
                tipo = no.simbolo.tipo
            case AcessoIndice():
                tipo = self._indice(no)
            case AcessoCampo():
                tipo = self._campo(no)
            case Binaria():
                tipo = self._binaria(no)
            case Unaria():
                tipo = self._unaria(no)
            case Chamada():
                tipo = self._chamada(no)
        no.tipo_resolvido = tipo
        return tipo

    def _lista_literal(self, no: ListaLiteral):
        if not no.elementos:
            return TipoColecao(None, 0, literal=True)
        elemento = self._expressao(no.elementos[0])
        for e in no.elementos[1:]:
            t = self._expressao(e)
            comum = unificar(elemento, t)
            if comum is None:
                raise ErroSemantico(f"elementos de tipos diferentes na mesma lista: "
                                    f"{elemento} e {t}", e.linha, e.coluna)
            elemento = comum
        return TipoColecao(elemento, len(no.elementos), literal=True)

    def _indice(self, no: AcessoIndice):
        tb = self._expressao(no.base)
        ti = self._expressao(no.indice)
        if not isinstance(tb, TipoColecao):
            raise ErroSemantico(f"só arrays e listas têm posições com '[ ]', recebido {tb}",
                                no.linha, no.coluna)
        if ti != "inteiro":
            raise ErroSemantico(f"o índice precisa ser inteiro, recebido {ti}",
                                no.indice.linha, no.indice.coluna)
        if tb.elemento is None:
            raise ErroSemantico("a lista vazia [] não tem elementos", no.linha, no.coluna)
        n = _constante_inteira(no.indice)
        if n is not None and n < 0:
            raise ErroSemantico(f"índice negativo ({n}); o primeiro elemento é o 0",
                                no.indice.linha, no.indice.coluna)
        if n is not None and tb.tamanho is not None and n >= tb.tamanho:
            raise ErroSemantico(f"índice {n} fora dos limites: o array tem {tb.tamanho} "
                                f"elemento(s), de 0 a {tb.tamanho - 1}",
                                no.indice.linha, no.indice.coluna)
        return tb.elemento

    def _campo(self, no: AcessoCampo):
        tb = self._expressao(no.base)
        if not isinstance(tb, TipoRegistro):
            raise ErroSemantico(f"'.{no.campo}' só funciona com registros, recebido {tb}",
                                no.linha, no.coluna)
        campos = self.registros[tb.nome].campos
        for i, (nome, tipo) in enumerate(campos):
            if nome == no.campo:
                no.indice_campo = i
                return tipo
        disponiveis = ", ".join(nome for nome, _ in campos)
        raise ErroSemantico(f"o registro '{tb.nome}' não tem o campo '{no.campo}' "
                            f"(campos: {disponiveis})", no.linha, no.coluna)

    def _binaria(self, no: Binaria):
        te = self._expressao(no.esquerda)
        td = self._expressao(no.direita)
        op = no.op

        if op in ARITMETICOS:
            if op == "+" and te == td == "texto":
                return "texto"
            if te in NUMEROS and td in NUMEROS:
                if op == "%" and (te, td) != ("inteiro", "inteiro"):
                    raise self._erro_op(no, f"'%' só aceita inteiros, recebeu {te} e {td}")
                if op in ("/", "%") and isinstance(no.direita, Literal) and no.direita.valor == 0:
                    raise ErroSemantico("divisão por zero", no.direita.linha, no.direita.coluna)
                return "real" if "real" in (te, td) else "inteiro"
            dica = ""
            if op == "+" and "texto" in (te, td):
                outro = td if te == "texto" else te
                dica = (" (a RedC não transforma números em texto automaticamente; "
                        f"converta com texto(...))" if outro in TIPOS_BASICOS else "")
            raise self._erro_op(no, f"operador '{op}' não aceita {te} e {td}{dica}")

        if op in RELACIONAIS:
            if te in NUMEROS and td in NUMEROS:
                return "logico"
            raise self._erro_op(no, f"operador '{op}' compara números, recebeu {te} e {td}")

        if op in IGUALDADE:
            if _composto(te) or _composto(td):
                raise self._erro_op(no, f"'{op}' não compara arrays, listas ou registros; "
                                        "compare os elementos ou os campos")
            if te == td or (te in NUMEROS and td in NUMEROS):
                return "logico"
            raise self._erro_op(no, f"não dá para comparar {te} com {td}")

        # e / ou
        if te == td == "logico":
            return "logico"
        raise self._erro_op(no, f"'{op}' precisa de dois valores logico, recebeu {te} e {td}")

    def _unaria(self, no: Unaria):
        tipo = self._expressao(no.operando)
        if no.op == "-" and tipo in NUMEROS:
            return tipo
        if no.op == "nao" and tipo == "logico":
            return "logico"
        esperado = "um número" if no.op == "-" else "um valor logico"
        raise self._erro_op(no, f"'{no.op}' precisa de {esperado}, recebeu {tipo}")

    def _chamada(self, no: Chamada):
        simbolo = self._resolver_chamavel(no.nome, no.linha, no.coluna)
        no.simbolo = simbolo
        if simbolo.categoria == "nativa":
            return self._nativa(no)
        if simbolo.categoria == "registro":
            esperados = simbolo.campos
            descricao = f"o registro '{no.nome}' tem {len(esperados)} campo(s)"
        else:
            esperados = [(None, t) for t in simbolo.parametros]
            descricao = f"'{no.nome}' espera {len(esperados)} argumento(s)"
        if len(no.argumentos) != len(esperados):
            raise ErroSemantico(f"{descricao}, recebeu {len(no.argumentos)}",
                                no.linha, no.coluna)
        for i, (arg, (campo, esperado)) in enumerate(zip(no.argumentos, esperados), 1):
            recebido = self._expressao(arg)
            if not cabe_em(esperado, recebido):
                onde = (f"campo '{campo}' de '{no.nome}'" if campo
                        else f"argumento {i} de '{no.nome}'")
                raise ErroSemantico(f"{onde}: esperado {esperado}, recebido {recebido}",
                                    arg.linha, arg.coluna)
        return simbolo.tipo

    def _nativa(self, no: Chamada):
        quantos = {"tamanho": 1, "adicione": 2, "texto": 1}[no.nome]
        if len(no.argumentos) != quantos:
            raise ErroSemantico(f"'{no.nome}' espera {quantos} argumento(s), "
                                f"recebeu {len(no.argumentos)}", no.linha, no.coluna)
        primeiro = no.argumentos[0]
        tipo = self._expressao(primeiro)
        if no.nome == "texto":
            if tipo not in TIPOS_BASICOS:
                raise ErroSemantico(f"texto() converte inteiro, real e logico, recebido {tipo}",
                                    primeiro.linha, primeiro.coluna)
            return "texto"
        if no.nome == "tamanho":
            if not (isinstance(tipo, TipoColecao) or tipo == "texto"):
                raise ErroSemantico(f"tamanho() funciona com arrays, listas e textos, "
                                    f"recebido {tipo}", primeiro.linha, primeiro.coluna)
            return "inteiro"
        # adicione(lista, valor)
        if not (isinstance(tipo, TipoColecao) and tipo.eh_lista):
            if isinstance(tipo, TipoColecao) and tipo.tamanho is not None and not tipo.literal:
                msg = "adicione() só funciona com listas; arrays têm tamanho fixo"
            else:
                msg = f"adicione() precisa de uma lista guardada em variável, recebido {tipo}"
            raise ErroSemantico(msg, primeiro.linha, primeiro.coluna)
        valor = no.argumentos[1]
        recebido = self._expressao(valor)
        if not cabe_em(tipo.elemento, recebido):
            raise ErroSemantico(f"a lista guarda {tipo.elemento}, recebido {recebido}",
                                valor.linha, valor.coluna)
        return "inteiro"

    def _erro_op(self, no, mensagem: str) -> ErroSemantico:
        return ErroSemantico(mensagem, no.linha, no.coluna)

    # ---------- nomes ----------

    def _resolver_variavel(self, nome: str, linha: int, coluna: int) -> Simbolo:
        simbolo = self.tabela.buscar(nome)
        if simbolo is None:
            msg = f"'{nome}' não foi declarada"
            if self.funcao_atual is not None and nome in self.globais:
                msg += (f" dentro da função '{self.funcao_atual.nome}'; funções só "
                        "enxergam seus parâmetros e variáveis locais "
                        f"('{nome}' é global, linha {self.globais[nome]})")
            raise ErroSemantico(msg, linha, coluna)
        if simbolo.categoria in ("funcao", "nativa"):
            raise ErroSemantico(f"'{nome}' é uma função; para chamá-la use {nome}(...)",
                                linha, coluna)
        if simbolo.categoria == "registro":
            raise ErroSemantico(f"'{nome}' é um registro; para criar um valor use {nome}(...)",
                                linha, coluna)
        return simbolo

    def _resolver_chamavel(self, nome: str, linha: int, coluna: int) -> Simbolo:
        simbolo = self.tabela.buscar(nome)
        if simbolo is None:
            raise ErroSemantico(f"função '{nome}' não foi declarada", linha, coluna)
        if simbolo.categoria not in ("funcao", "nativa", "registro"):
            raise ErroSemantico(f"'{nome}' é uma {simbolo.categoria}, não uma função",
                                linha, coluna)
        return simbolo


def analisar(programa: Programa) -> TabelaSimbolos:
    """Atalho: AST -> tabela de símbolos preenchida, com tipos verificados."""
    return AnalisadorSemantico().analisar(programa)
