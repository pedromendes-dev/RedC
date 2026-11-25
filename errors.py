"""
errors.py — Erros do compilador RedC.

Toda fase lança um erro com linha e coluna. O compiler.py captura
CompilacaoErro e exibe a mensagem em português, sem traceback do Python.
"""


class CompilacaoErro(Exception):
    """Base de todos os erros da RedC."""

    fase = "Erro"

    def __init__(self, mensagem: str, linha: int, coluna: int):
        self.mensagem = mensagem
        self.linha = linha
        self.coluna = coluna
        super().__init__(str(self))

    def __str__(self) -> str:
        return f"{self.fase} (linha {self.linha}, coluna {self.coluna}): {self.mensagem}"


class ErroLexico(CompilacaoErro):
    fase = "Erro léxico"


class ErroSintatico(CompilacaoErro):
    fase = "Erro sintático"


class ErroSemantico(CompilacaoErro):
    fase = "Erro semântico"


class ErroExecucao(CompilacaoErro):
    fase = "Erro de execução"
