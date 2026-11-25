"""
gerar_resultados.py — Gera resultados/RESULTADOS.md, a evidência de
execução do compilador RedC para o documento final.

O relatório traz:
- o resultado da suíte de testes automatizados;
- cada programa de teste: o que verifica, o código-fonte e a saída real
  do compilador, comparada com a saída esperada;
- a saída de cada fase (tokens, AST, tabela de símbolos e bytecode).

Uso (na pasta redc/):
    python gerar_resultados.py
"""

import io
import platform
import subprocess
import sys
import unittest
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "testes"))
from casos import CASOS  # noqa: E402

PASTA = RAIZ / "resultados"


def rodar(*args) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "compiler.py", *args], capture_output=True,
                          text=True, encoding="utf-8", cwd=RAIZ, timeout=60)


def rodar_testes() -> unittest.TestResult:
    suite = unittest.defaultTestLoader.discover(str(RAIZ / "testes"), top_level_dir=str(RAIZ / "testes"))
    return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)


def bloco(conteudo: str, linguagem: str = "") -> str:
    return f"```{linguagem}\n{conteudo.rstrip()}\n```"


def main() -> int:
    PASTA.mkdir(exist_ok=True)
    print("Rodando a suíte de testes...")
    testes = rodar_testes()
    falhas_testes = len(testes.failures) + len(testes.errors)

    print("Rodando os programas de teste...")
    execucoes = []
    for caso in CASOS:
        r = rodar(f"programas/{caso.arquivo}")
        ok = tuple(r.stdout.splitlines()) == caso.saida and r.returncode == caso.codigo
        execucoes.append((caso, r, ok))
    falhas_programas = sum(not ok for _, _, ok in execucoes)

    md = [
        "# RedC — Resultados da execução do compilador",
        "",
        f"Gerado em {datetime.now():%d/%m/%Y %H:%M} com Python {platform.python_version()} "
        f"({platform.system()}), pelo comando `python gerar_resultados.py`.",
        "",
        "## Resumo",
        "",
        "| Verificação | Resultado |",
        "| --- | --- |",
        f"| Testes automatizados (`python -m unittest discover -s testes`) | "
        f"{testes.testsRun - falhas_testes} de {testes.testsRun} passando |",
        f"| Programas de teste com a saída esperada | "
        f"{len(execucoes) - falhas_programas} de {len(execucoes)} |",
        "",
        "## Programas de teste",
        "",
        "| Programa | O que verifica | Teste obrigatório do edital | Resultado |",
        "| --- | --- | --- | --- |",
    ]
    for caso, _, ok in execucoes:
        md.append(f"| `{caso.arquivo}` | {caso.categoria} | {caso.obrigatorio or '—'} | "
                  f"{'OK' if ok else 'FALHOU'} |")

    for caso, r, ok in execucoes:
        fonte = (RAIZ / "programas" / caso.arquivo).read_text("utf-8")
        md += ["", f"### {caso.arquivo} — {caso.categoria}", "", bloco(fonte), "",
               f"`python compiler.py programas/{caso.arquivo}`", "", bloco(r.stdout or "(sem saída)")]
        if not ok:
            md += ["", "**Saída esperada:**", "", bloco("\n".join(caso.saida))]

    md += ["", "## Saída de cada fase", "",
           "Programa `repeticao.redc`, com todas as fases exibidas:", "",
           "`python compiler.py programas/repeticao.redc --tokens --ast --simbolos --bytecode`", "",
           bloco(rodar("programas/repeticao.redc", "--tokens", "--ast", "--simbolos",
                       "--bytecode").stdout),
           "", "Programa `exemplo_valido.redc` (funções e recursão):", "",
           "`python compiler.py programas/exemplo_valido.redc --ast --simbolos --bytecode`", "",
           bloco(rodar("programas/exemplo_valido.redc", "--ast", "--simbolos",
                       "--bytecode").stdout),
           "", "Programa `escopos.redc` (tabela de símbolos com sombreamento):", "",
           "`python compiler.py programas/escopos.redc --simbolos`", "",
           bloco(rodar("programas/escopos.redc", "--simbolos").stdout),
           "", "Programa `escolha.redc` (AST e bytecode de escolha/caso):", "",
           "`python compiler.py programas/escolha.redc --ast --bytecode`", "",
           bloco(rodar("programas/escolha.redc", "--ast", "--bytecode").stdout),
           "", "Programa `registros.redc` (registros, listas e para cada):", "",
           "`python compiler.py programas/registros.redc --simbolos --bytecode`", "",
           bloco(rodar("programas/registros.redc", "--simbolos", "--bytecode").stdout)]

    destino = PASTA / "RESULTADOS.md"
    destino.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Testes: {testes.testsRun - falhas_testes}/{testes.testsRun} passando. "
          f"Programas: {len(execucoes) - falhas_programas}/{len(execucoes)} com a saída esperada.")
    print(f"Relatório gravado em {destino.relative_to(RAIZ)}")
    return 1 if falhas_testes or falhas_programas else 0


if __name__ == "__main__":
    sys.exit(main())
