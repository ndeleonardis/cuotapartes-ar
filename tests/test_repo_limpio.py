"""Reglas 6 y 7 de la constitución: el repo es público y no versiona planillas
de la CAFCI, dumps de la base ni secretos."""

import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EXTENSIONES_PROHIBIDAS = (".xlsx", ".xls", ".csv", ".dump", ".backup")


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, check=False)


def _versionados() -> list[str]:
    return _git("ls-files").stdout.splitlines()


def test_no_se_versionan_planillas_ni_dumps():
    malos = [a for a in _versionados() if a.lower().endswith(EXTENSIONES_PROHIBIDAS)]
    assert malos == [], f"Archivos que no pueden estar en el repo público: {malos}"


def test_no_se_versiona_ningun_env():
    nombres = [Path(a).name for a in _versionados()]
    malos = [n for n in nombres if n.startswith(".env") and n != ".env.ejemplo"]
    assert malos == [], f"Secretos versionados: {malos}"


def test_gitignore_frena_secretos_planillas_y_dumps():
    for nombre in (".env", ".env.produccion", "planilla.xlsx", "datos.csv", "base.dump"):
        resultado = _git("check-ignore", "-q", "--no-index", nombre)
        assert resultado.returncode == 0, f"{nombre} no está ignorado por .gitignore"
