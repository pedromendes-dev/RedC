"""
symbols.py — Tabela de símbolos da RedC.

Guarda cada identificador declarado (variáveis, parâmetros, funções e
registros) com seu tipo, sua categoria e a posição da declaração. As
funções nativas (tamanho, adicione) já nascem registradas no escopo global.

Os escopos formam uma PILHA:
- o escopo global fica na base;
- cada função abre um escopo com seus parâmetros e variáveis locais;
- cada bloco de 'se', 'senao' e 'enquanto' abre um escopo próprio.

Para achar um nome, a busca começa no topo da pilha (escopo mais interno)
e desce até o global. Ao fechar um escopo, seus nomes deixam de ser
visíveis, mas continuam registrados para o relatório (--simbolos).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from errors import ErroSemantico


@dataclass
class Simbolo:
    nome: str
    categoria: str            # 'variavel', 'parametro', 'funcao', 'registro' ou 'nativa'
    tipo: object              # tipo da variável/parâmetro, de retorno da função ou o próprio registro
    linha: int
    coluna: int
    parametros: list = field(default_factory=list)       # tipos (só funções)
    campos: list = field(default_factory=list)           # (nome, tipo) (só registros)
    # Posição da variável no quadro (frame) da função ou do programa
    # principal. Nomes sombreados recebem posições diferentes, então a VM
    # nunca confunde o 'limite' global com o 'limite' de um bloco.
    slot: int = -1

    def assinatura(self) -> str:
        if self.categoria == "funcao":
            return f"({', '.join(map(str, self.parametros))}) :: {self.tipo}"
        if self.categoria == "registro":
            return "{" + "; ".join(f"{n} :: {t}" for n, t in self.campos) + "}"
        return str(self.tipo)


@dataclass
class Escopo:
    nome: str
    nivel: int
    pai: Escopo | None
    simbolos: dict[str, Simbolo] = field(default_factory=dict)


class TabelaSimbolos:
    def __init__(self):
        global_ = Escopo("global", 0, None)
        self.pilha: list[Escopo] = [global_]
        self.todos: list[Escopo] = [global_]   # histórico, para o relatório

    @property
    def atual(self) -> Escopo:
        return self.pilha[-1]

    def abrir_escopo(self, nome: str) -> Escopo:
        escopo = Escopo(nome, len(self.pilha), self.atual)
        self.pilha.append(escopo)
        self.todos.append(escopo)
        return escopo

    def fechar_escopo(self):
        if len(self.pilha) == 1:
            raise RuntimeError("o escopo global não pode ser fechado")
        self.pilha.pop()

    def declarar(self, simbolo: Simbolo) -> Simbolo:
        """Registra no escopo atual. O mesmo nome duas vezes no MESMO
        escopo é erro; num escopo interno é permitido (sombreamento)."""
        existente = self.atual.simbolos.get(simbolo.nome)
        if existente is not None and existente.categoria == "nativa":
            raise ErroSemantico(
                f"'{simbolo.nome}' é uma função nativa da RedC e não pode ser redeclarada",
                simbolo.linha, simbolo.coluna)
        if existente is not None:
            raise ErroSemantico(
                f"'{simbolo.nome}' já foi declarado neste escopo "
                f"(como {existente.categoria}, na linha {existente.linha})",
                simbolo.linha, simbolo.coluna,
            )
        self.atual.simbolos[simbolo.nome] = simbolo
        return simbolo

    def buscar(self, nome: str) -> Simbolo | None:
        """Procura do escopo mais interno até o global."""
        for escopo in reversed(self.pilha):
            if nome in escopo.simbolos:
                return escopo.simbolos[nome]
        return None

    def relatorio(self) -> str:
        """Todos os símbolos registrados, escopo por escopo."""
        cab = ("ESCOPO", "NÍVEL", "NOME", "CATEGORIA", "TIPO", "LINHA")
        linhas = []
        for escopo in self.todos:
            for s in escopo.simbolos.values():
                if s.categoria == "nativa":
                    continue
                linhas.append((escopo.nome, str(escopo.nivel), s.nome,
                               s.categoria, s.assinatura(), str(s.linha)))
        larguras = [max(len(x) for x in col) for col in zip(cab, *linhas)]
        fmt = "  ".join(f"{{:<{w}}}" for w in larguras)
        saida = [fmt.format(*cab), fmt.format(*("-" * w for w in larguras))]
        saida += [fmt.format(*l) for l in linhas]
        return "\n".join(l.rstrip() for l in saida)
