"""
Testes de integração da RedC (Etapa 7).

Rodam o compilador do jeito que o usuário roda — 'python compiler.py
arquivo.redc' em um processo separado — e conferem a saída e o código de
saída. Também submetem o compilador a entradas estranhas para garantir que
nenhuma delas produz um erro interno do Python (traceback).

Rodar a partir da pasta redc/:
    python -m unittest discover -s testes -v
"""

import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import codegen  # noqa: E402
import lexer  # noqa: E402
import parser  # noqa: E402
import semantic  # noqa: E402
import vm  # noqa: E402
from casos import CASOS  # noqa: E402
from errors import CompilacaoErro  # noqa: E402


def rodar_compilador(*args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(RAIZ / "compiler.py"), *map(str, args)],
        capture_output=True, text=True, encoding="utf-8", cwd=RAIZ, timeout=60)


class TestProgramasDeTeste(unittest.TestCase):
    def test_todos_os_programas_da_pasta_estao_no_catalogo(self):
        na_pasta = {p.name for p in (RAIZ / "programas").glob("*.redc")}
        self.assertEqual(na_pasta, {c.arquivo for c in CASOS})

    def test_testes_obrigatorios_do_edital(self):
        cobertos = {c.obrigatorio for c in CASOS if c.obrigatorio}
        self.assertEqual(len(cobertos), 7)

    def test_saida_de_cada_programa(self):
        for caso in CASOS:
            with self.subTest(programa=caso.arquivo):
                r = rodar_compilador(f"programas/{caso.arquivo}")
                self.assertEqual(tuple(r.stdout.splitlines()), caso.saida)
                self.assertEqual(r.returncode, caso.codigo)
                self.assertEqual(r.stderr, "")


class TestLinhaDeComando(unittest.TestCase):
    def test_todas_as_fases_juntas(self):
        r = rodar_compilador("programas/repeticao.redc",
                             "--tokens", "--ast", "--simbolos", "--bytecode")
        for secao in ("--- Tokens ---", "--- AST ---", "--- Tabela de símbolos ---",
                      "--- Bytecode ---", "--- Execução ---"):
            self.assertIn(secao, r.stdout)
        self.assertTrue(r.stdout.rstrip().endswith("120"))

    def test_sem_executar(self):
        r = rodar_compilador("programas/repeticao.redc", "--sem-executar")
        self.assertIn("compilado sem erros", r.stdout)
        self.assertNotIn("120", r.stdout)

    def test_salvar(self):
        r = rodar_compilador("programas/repeticao.redc", "--salvar")
        self.assertEqual(r.returncode, 0)
        for sufixo in ("ast", "simbolos", "bytecode"):
            arquivo = RAIZ / "saida" / f"repeticao.{sufixo}.txt"
            self.assertTrue(arquivo.exists(), arquivo)
            arquivo.unlink()

    def test_erros_de_uso(self):
        self.assertEqual(rodar_compilador().returncode, 2)
        self.assertEqual(rodar_compilador("programas/repeticao.redc", "--xyz").returncode, 2)
        self.assertEqual(rodar_compilador("nao_existe.redc").returncode, 2)
        self.assertEqual(rodar_compilador("compiler.py").returncode, 2)   # extensão errada


class TestEntradasEstranhas(unittest.TestCase):
    """Nenhuma entrada pode derrubar o compilador com erro interno do Python."""

    def rodar_bytes(self, conteudo: bytes) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "teste.redc"
            arquivo.write_bytes(conteudo)
            r = rodar_compilador(arquivo)
        self.assertNotIn("Traceback", r.stdout + r.stderr)
        return r

    def test_utf8_com_bom_do_bloco_de_notas(self):
        r = self.rodar_bytes('﻿mostre("olá");\r\n'.encode("utf-8"))
        self.assertEqual(r.stdout.strip(), "olá")

    def test_arquivo_ansi_windows(self):
        r = self.rodar_bytes('mostre("ação");\n'.encode("cp1252"))
        self.assertEqual(r.stdout.strip(), "ação")

    def test_arquivo_vazio_e_so_comentario(self):
        self.assertEqual(self.rodar_bytes(b"").returncode, 0)
        self.assertEqual(self.rodar_bytes(b"# nada\n").returncode, 0)

    def test_aninhamento_profundo(self):
        for fonte in ["mostre(" + "(" * 3000 + "1" + ")" * 3000 + ");",
                      "mostre(" + "-" * 3000 + "1);",
                      "se (verdadeiro) {" * 600 + "}" * 600,
                      "seja x :: " + "[" * 300 + "inteiro" + "]" * 300 + " = [];",
                      "mostre(" + "[" * 300 + "1" + "]" * 300 + ");"]:
            r = self.rodar_bytes(fonte.encode())
            self.assertIn("aninhamento profundo demais", r.stdout)

    def test_expressao_muito_longa(self):
        r = self.rodar_bytes(("mostre(" + " + ".join(["1"] * 2000) + ");").encode())
        self.assertEqual(r.stdout.strip(), "2000")
        r = self.rodar_bytes(("mostre(" + " + ".join(["1"] * 8000) + ");").encode())
        self.assertIn("longa ou aninhada demais", r.stdout)

    def test_programas_mutados_aleatoriamente(self):
        """500 variações aleatórias dos programas de teste (semente fixa):
        cada uma compila, ou para com um erro da RedC — nunca com traceback."""
        fontes = [p.read_text("utf-8") for p in sorted((RAIZ / "programas").glob("*.redc"))]
        pedacos = list("abxyz019 \n;:,.(){}[]+-*/%=<>!\"#_") + [
            "seja ", "se ", "senao ", "enquanto ", "funcao ", "retorne ",
            "mostre", "::", " e ", " ou ", "nao ", "inteiro", "real", "texto",
            "escolha ", "caso ", "padrao ", "para cada ", " em ", "registro ",
            "tamanho(", "adicione(", "texto(", "[inteiro; 2]", "[real]", ".nome", "[0]"]
        rnd = random.Random(2026)
        for i in range(500):
            s = list(rnd.choice(fontes))
            for _ in range(rnd.randint(1, 4)):
                pos = rnd.randrange(len(s) + 1)
                if rnd.random() < 0.5 and s:
                    del s[min(pos, len(s) - 1)]
                else:
                    s.insert(pos, rnd.choice(pedacos))
            fonte = "".join(s)
            with self.subTest(mutacao=i):
                try:
                    arvore = parser.analisar(lexer.analisar(fonte))
                    semantic.analisar(arvore)
                    vm.executar(codegen.gerar(arvore), escrever=lambda _: None,
                                limite_instrucoes=20_000)
                except CompilacaoErro:
                    pass


if __name__ == "__main__":
    unittest.main()
