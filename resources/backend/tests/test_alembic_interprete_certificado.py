"""AIC · Alembic con el intérprete que se certifica (Spec 054, OD-CERT-10/11; TEST-MIGRACIONES-VENV-FIJO
y E2E-HARNESS-INTERPRETER-FIXED).

- AIC-01 ningún código de certificación construye una ruta a un `.venv`;
- AIC-02 ninguna orden ejecuta alembic con `alembic`, `python` o `python3` del PATH;
- AIC-03 el detector reconoce cada variante prohibida y no rechaza docstrings ni comentarios;
- AIC-04 `orden_alembic` usa `sys.executable`;
- AIC-05 cada subproceso de alembic de las pruebas usa el contrato;
- AIC-06 la migración de la autoridad central en E2E usa el contrato, con su cwd y su entorno;
- AIC-07 el hijo alembic corre con el intérprete, alembic y SQLAlchemy del padre.

Esta prueba se excluye a sí misma del escaneo porque sus muestras contienen las variantes
prohibidas; AIC-03 prueba el detector con ellas.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import sqlalchemy

import alembic
from tests.alembic_orden import orden_alembic

BACKEND = Path(__file__).resolve().parents[1]
RAIZ = BACKEND.parents[1]

E2E_CORRIDA = RAIZ / "qa" / "e2e_corrida.py"
ESTA_PRUEBA = Path(__file__).resolve()

FICHEROS_DE_MIGRACION: tuple[str, ...] = (
    "tests/central/test_central_authority_pg.py",
    "tests/central/test_central_sync_auth_pg.py",
    "tests/test_documents_migration_0024.py",
    "tests/test_migrations_offline.py",
    "tests/test_spec004_installation_race.py",
    "tests/test_spec019_migration_0044.py",
    "tests/test_spec020_migration_0045.py",
    "tests/test_spec021_migration_0047.py",
    "tests/test_spec022_migration_0048.py",
    "tests/test_spec023_migration_0046.py",
    "tests/test_spec030_migration_0043.py",
    "tests/test_spec047_schema.py",
    "tests/test_spec052_migration_0033_legacy.py",
    "tests/test_uom_backfill.py",
    "tests/test_warehouse_migration_0018.py",
)

ORDEN_DE_LA_AUTORIDAD = (
    "[sys.executable, '-m', 'alembic', '-c', 'central_authority/alembic.ini', 'upgrade', 'head']"
)

_RUTA_VENV = re.compile(r"(?:^|[\\/])\.venv(?:[\\/]|$)")
_PYTHON = re.compile(r"python(?:3(?:\.\d+)?)?(?:\.exe)?")
_SHELL_ALEMBIC = re.compile(r"\s*(?:alembic|python(?:3(?:\.\d+)?)?\s+-m\s+alembic)(?:\s|$)")
_SUBPROCESO = frozenset({"run", "Popen", "call", "check_call", "check_output"})


def _escaneados() -> list[Path]:
    ficheros = sorted((BACKEND / "tests").rglob("*.py"))
    resultado = [f for f in ficheros if f.resolve() != ESTA_PRUEBA]
    resultado.append(E2E_CORRIDA)
    return resultado


def _docstrings(arbol: ast.Module) -> set[int]:
    ids: set[int] = set()
    for nodo in ast.walk(arbol):
        if (
            isinstance(nodo, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
            and nodo.body
        ):
            primero = nodo.body[0]
            if (
                isinstance(primero, ast.Expr)
                and isinstance(primero.value, ast.Constant)
                and isinstance(primero.value.value, str)
            ):
                ids.add(id(primero.value))
    return ids


def _nombre(funcion: ast.expr) -> str:
    if isinstance(funcion, ast.Attribute):
        return funcion.attr
    if isinstance(funcion, ast.Name):
        return funcion.id
    return ""


def _funcion_que_contiene(arbol: ast.Module, objetivo: ast.AST) -> str | None:
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.FunctionDef):
            if any(n is objetivo for n in ast.walk(nodo)):
                return nodo.name
    return None


def infracciones(fuente: str) -> list[tuple[int, str]]:
    arbol = ast.parse(fuente)
    docstrings = _docstrings(arbol)
    encontradas: set[tuple[int, str]] = set()

    for nodo in ast.walk(arbol):
        if (
            isinstance(nodo, ast.Constant)
            and isinstance(nodo.value, str)
            and id(nodo) not in docstrings
            and _RUTA_VENV.search(nodo.value)
        ):
            encontradas.add((nodo.lineno, "ruta .venv"))

        if isinstance(nodo, ast.List | ast.Tuple) and nodo.elts:
            primero = nodo.elts[0]
            if isinstance(primero, ast.Constant) and isinstance(primero.value, str):
                base = primero.value.replace("\\", "/").rsplit("/", 1)[-1].lower()
                if base in {"alembic", "alembic.exe"}:
                    encontradas.add((nodo.lineno, "alembic del PATH"))
                elif _PYTHON.fullmatch(base) and any(
                    isinstance(el, ast.Constant) and el.value == "alembic"
                    for el in nodo.elts[1:]
                ):
                    encontradas.add((nodo.lineno, "python del PATH"))

        if isinstance(nodo, ast.Call):
            nombre = _nombre(nodo.func)
            if nombre in _SUBPROCESO or nombre == "system":
                args = nodo.args
                if args and isinstance(args[0], ast.Constant) and isinstance(args[0].value, str):
                    if _SHELL_ALEMBIC.match(args[0].value):
                        encontradas.add((nodo.lineno, "orden de shell con alembic del PATH"))
            if nombre == "which" and nodo.args:
                primer = nodo.args[0]
                if isinstance(primer, ast.Constant) and primer.value == "alembic":
                    encontradas.add((nodo.lineno, "búsqueda de alembic en el PATH"))

    return sorted(encontradas)


def _sitios_de_alembic(arbol: ast.Module) -> list[ast.Call]:
    sitios: list[ast.Call] = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Call):
            if _nombre(nodo.func) in _SUBPROCESO and nodo.args:
                if "alembic" in ast.unparse(nodo.args[0]).lower():
                    sitios.append(nodo)
    return sitios


def _conforme(orden: ast.expr) -> bool:
    if (
        isinstance(orden, ast.Call)
        and isinstance(orden.func, ast.Name)
        and orden.func.id == "orden_alembic"
    ):
        return True
    if isinstance(orden, ast.List) and len(orden.elts) >= 3:
        primeros = [ast.unparse(el) for el in orden.elts[:3]]
        if primeros == ["sys.executable", "'-m'", "'alembic'"]:
            return True
    return False


def _infracciones_de_ficheros(escaneados: list[Path]) -> list[str]:
    problemas: list[str] = []
    for fichero in escaneados:
        fuente = fichero.read_text(encoding="utf-8")
        for linea, motivo in infracciones(fuente):
            problemas.append(f"{fichero.relative_to(RAIZ)}:{linea}: {motivo}")
    return problemas


PROHIBIDAS: list[tuple[str, str]] = [
    (
        "os.path.join",
        'subprocess.run([os.path.join(B, ".venv", "bin", "alembic"), "upgrade", "head"])',
    ),
    ("pathlib", 'subprocess.run([str(B / ".venv" / "bin" / "alembic"), "heads"])'),
    (
        "una cadena",
        'subprocess.run([str(B / ".venv/bin/alembic"), "-c", "x.ini", "upgrade", "head"])',
    ),
    ("variable", 'alembic_bin = B / ".venv" / "bin" / "alembic"'),
    (
        "Path()",
        'subprocess.run([str(Path(B, ".venv", "Scripts", "alembic.exe")), "upgrade", "head"])',
    ),
    ("windows", 'x = ".venv\\\\Scripts\\\\alembic.exe"'),
    (
        "intérprete .venv",
        'orden = [str(B / ".venv" / "bin" / "python"), "-m", "alembic"]',
    ),
    (
        "f-string",
        'subprocess.run(f"{B}/.venv/bin/alembic upgrade head", shell=True)',
    ),
    ("alembic", 'subprocess.run(["alembic", "upgrade", "head"])'),
    ("python", 'subprocess.run(["python", "-m", "alembic", "upgrade", "head"])'),
    ("python3", 'subprocess.run(("python3", "-m", "alembic", "heads"))'),
    ("shell", 'subprocess.run("alembic upgrade head", shell=True)'),
    ("shell python3", 'os.system("python3 -m alembic upgrade head")'),
    ("which", 'shutil.which("alembic")'),
]

PERMITIDAS: list[tuple[str, str]] = [
    (
        "sys.executable",
        'subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND)',
    ),
    ("helper", 'subprocess.run(orden_alembic("upgrade", "head"), cwd=BACKEND)'),
    (
        "docstring",
        '"""Módulo .venv/bin/alembic mencionado en docstring."""\n\ndef f():\n    """Función con .venv/bin/alembic."""\n    # antes: .venv/bin/alembic\n    return 1\n',
    ),
    ("versiones", 'MIGRACION = BACKEND / "alembic" / "versions" / "0043.py"'),
    ("otro python", 'orden = ["python", "-m", "app.modules.scheduler", "tick"]'),
    ("api", 'command.upgrade(Config(str(BACKEND / "alembic.ini")), "head")'),
    ("clamscan", 'shutil.which("clamscan", path=entorno.get("PATH"))'),
]


def test_aic_01_ningun_codigo_de_certificacion_usa_una_ruta_venv() -> None:
    escaneados = _escaneados()
    assert E2E_CORRIDA in escaneados and E2E_CORRIDA.is_file()
    for f in FICHEROS_DE_MIGRACION:
        assert BACKEND / f in escaneados, f"Falta fichero de migración en escaneo: {f}"
    problemas = _infracciones_de_ficheros(escaneados)
    rutas_venv = [p for p in problemas if p.endswith(": ruta .venv")]
    assert rutas_venv == [], rutas_venv


def test_aic_02_ninguna_orden_usa_alembic_ni_python_del_path() -> None:
    escaneados = _escaneados()
    problemas = _infracciones_de_ficheros(escaneados)
    otras = [p for p in problemas if not p.endswith(": ruta .venv")]
    assert otras == [], otras


@pytest.mark.parametrize(
    "fuente", [fuente for _, fuente in PROHIBIDAS], ids=[nombre for nombre, _ in PROHIBIDAS]
)
def test_aic_03_el_detector_reconoce_cada_variante(fuente: str) -> None:
    assert infracciones(fuente), fuente


@pytest.mark.parametrize(
    "fuente", [fuente for _, fuente in PERMITIDAS], ids=[nombre for nombre, _ in PERMITIDAS]
)
def test_aic_03_el_detector_no_rechaza_docstrings_ni_otros_usos(fuente: str) -> None:
    assert infracciones(fuente) == [], infracciones(fuente)


def test_aic_04_orden_alembic_usa_el_interprete_de_la_suite() -> None:
    assert orden_alembic() == [sys.executable, "-m", "alembic"]
    assert orden_alembic("upgrade", "head") == [sys.executable, "-m", "alembic", "upgrade", "head"]
    assert orden_alembic("-c", "central_authority/alembic.ini", "heads")[3:] == [
        "-c",
        "central_authority/alembic.ini",
        "heads",
    ]
    assert Path(sys.executable).is_absolute()


def test_aic_05_cada_subproceso_de_alembic_de_las_pruebas_usa_el_contrato() -> None:
    escaneados = _escaneados()
    registros: list[str] = []
    conteo_por_fichero: dict[str, int] = {}
    total_conformes = 0

    for fichero in escaneados:
        if fichero == E2E_CORRIDA:
            continue
        fuente = fichero.read_text(encoding="utf-8")
        arbol = ast.parse(fuente)
        sitios = _sitios_de_alembic(arbol)
        for sitio in sitios:
            if not _conforme(sitio.args[0]):
                registros.append(
                    f"{fichero.relative_to(RAIZ)}:{sitio.lineno}: {ast.unparse(sitio.args[0])}"
                )
            else:
                total_conformes += 1
                clave = fichero.relative_to(BACKEND).as_posix()
                conteo_por_fichero[clave] = conteo_por_fichero.get(clave, 0) + 1
    assert registros == [], registros
    for f in FICHEROS_DE_MIGRACION:
        assert conteo_por_fichero.get(f, 0) >= 1, f"Sin subproceso conforme en {f}"
    assert total_conformes >= 19, total_conformes


def test_aic_06_la_autoridad_central_del_e2e_migra_con_el_interprete_de_la_corrida() -> None:
    arbol = ast.parse(E2E_CORRIDA.read_text(encoding="utf-8"))
    sitios = _sitios_de_alembic(arbol)
    assert len(sitios) == 1, [ast.unparse(s.args[0]) for s in sitios]
    sitio = sitios[0]
    assert ast.unparse(sitio.args[0]) == ORDEN_DE_LA_AUTORIDAD, ast.unparse(sitio.args[0])

    palabras = {k.arg: ast.unparse(k.value) for k in sitio.keywords if k.arg}
    assert palabras == {
        "cwd": "base.BACKEND",
        "env": "entorno",
        "stdout": "registro",
        "stderr": "subprocess.STDOUT",
        "check": "False",
    }, palabras

    nombre_funcion = _funcion_que_contiene(arbol, sitio)
    assert nombre_funcion == "arrancar_autoridad", nombre_funcion


def test_aic_07_el_hijo_alembic_corre_con_el_interprete_alembic_y_sqlalchemy_del_padre(
    tmp_path: Path,
) -> None:
    (tmp_path / "sitecustomize.py").write_text(
        """import atexit
import json
import os
import sys


def _anotar():
    datos = {"executable": sys.executable, "version": sys.version}
    for nombre in ("alembic", "sqlalchemy"):
        modulo = sys.modules.get(nombre)
        datos[nombre] = [getattr(modulo, "__version__", None), getattr(modulo, "__file__", None)] if modulo else None
    with open(os.environ["KONTROL_PROCEDENCIA_ALEMBIC"], "w", encoding="utf-8") as f:
        json.dump(datos, f)


atexit.register(_anotar)
""",
        encoding="utf-8",
    )

    salida = tmp_path / "procedencia.json"
    previo = os.environ.get("PYTHONPATH")
    entorno = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(
            [str(tmp_path), *([previo] if previo else [])]
        ),
        "KONTROL_PROCEDENCIA_ALEMBIC": str(salida),
    }

    resultado = subprocess.run(
        orden_alembic("--version"),
        cwd=BACKEND,
        env=entorno,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert resultado.returncode == 0, resultado.stderr[-2000:]
    assert f"alembic {alembic.__version__}" in resultado.stdout

    hijo = json.loads(salida.read_text(encoding="utf-8"))
    assert hijo["executable"] == sys.executable
    assert hijo["version"] == sys.version
    assert hijo["alembic"] == [alembic.__version__, alembic.__file__]
    assert hijo["sqlalchemy"] == [sqlalchemy.__version__, sqlalchemy.__file__]


def test_aic_08_la_sonda_del_interprete_corre_con_el_cwd_y_el_entorno_de_la_migracion_y_antes_que_ella() -> None:
    arbol = ast.parse(E2E_CORRIDA.read_text(encoding="utf-8"))
    sondeos = [
        nodo
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Call)
        and _nombre(nodo.func) in _SUBPROCESO
        and nodo.args
        and ast.unparse(nodo.args[0]) == "[sys.executable, '-c', SONDA_DEL_INTERPRETE]"
    ]
    assert len(sondeos) == 1, [ast.unparse(s.args[0]) for s in sondeos]
    sonda = sondeos[0]

    palabras = {k.arg: ast.unparse(k.value) for k in sonda.keywords if k.arg}
    assert palabras == {
        "cwd": "base.BACKEND",
        "env": "entorno",
        "capture_output": "True",
        "text": "True",
        "check": "False",
    }, palabras

    migraciones = _sitios_de_alembic(arbol)
    assert len(migraciones) == 1, [ast.unparse(s.args[0]) for s in migraciones]
    migracion = migraciones[0]
    palabras_migracion = {k.arg: ast.unparse(k.value) for k in migracion.keywords if k.arg}
    assert palabras["cwd"] == palabras_migracion["cwd"], (palabras["cwd"], palabras_migracion["cwd"])
    assert palabras["env"] == palabras_migracion["env"], (palabras["env"], palabras_migracion["env"])

    nombre_funcion = _funcion_que_contiene(arbol, sonda)
    assert nombre_funcion == "anotar_interpretes", nombre_funcion

    autoridades = [
        nodo for nodo in ast.walk(arbol) if isinstance(nodo, ast.FunctionDef) and nodo.name == "arrancar_autoridad"
    ]
    assert len(autoridades) == 1, [n.name for n in autoridades]
    invocaciones = [
        nodo
        for nodo in ast.walk(autoridades[0])
        if isinstance(nodo, ast.Call) and ast.unparse(nodo) == "self.anotar_interpretes(entorno)"
    ]
    assert len(invocaciones) == 1, [ast.unparse(n) for n in invocaciones]
    assert invocaciones[0].lineno < migracion.lineno, (invocaciones[0].lineno, migracion.lineno)
