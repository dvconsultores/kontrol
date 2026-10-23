"""IDF · Frontera entre el grafo de runtime y el de certificación (Spec 052, OD-IMG-01..03)

IDF-01 el manifiesto runtime no declara herramientas de certificación
IDF-02 el manifiesto de certificación incluye el runtime y solo añade sus herramientas
IDF-03 el lock runtime no contiene nada exclusivo de certificación y el de certificación lo restringe
IDF-04 las versiones del subconjunto runtime coinciden
IDF-05 la cabecera del lock de certificación hereda corte y plataforma
IDF-06 cada lock se instala en su etapa y nunca paquetes sueltos
IDF-07 la cadena runtime no copia pruebas, QA ni pyproject.toml
IDF-08 cada import de terceros del producto está en el grafo runtime
IDF-09 los analizadores detectan desviaciones
"""

from __future__ import annotations

import ast
import importlib.metadata
import re
import sys
from pathlib import Path

from tests.test_dependencias_lock import (
    _PIN,
    BACKEND,
    INSTALACION_LOCK,
    RAIZ,
    _canonico,
    _comando_de_cabecera,
    _pines,
    _python_de_la_base,
)
from tests.test_imagen_backend_etapas import _etapas_completas, _todas
from tests.test_imagen_backend_mime import _cadena_efectiva

HERRAMIENTAS_DE_CERTIFICACION = frozenset({"pytest", "httpx", "ruff", "mypy"})
EXCLUSIVOS_DE_CERTIFICACION = frozenset(
    {
        "certifi",
        "httpcore",
        "httpx",
        "iniconfig",
        "mypy",
        "mypy-extensions",
        "packaging",
        "pluggy",
        "pygments",
        "pytest",
        "ruff",
    }
)
INSTALACION_LOCK_CERTIFICACION = "pip install --no-cache-dir --no-deps -r /tmp/requirements-test.lock"

# Proveedor S3 opcional de documents/storage.py (import perezoso protegido por ImportError); deuda PRODUCT-OPTIONAL-S3-PROVIDER-DEPENDENCY-UNDECLARED.
OPCIONALES_DEL_PRODUCTO: frozenset[str] = frozenset({"boto3"})
DIRECTORIOS_DEL_PRODUCTO = (BACKEND / "app", BACKEND / "central_authority", BACKEND / "alembic")


def _vias(texto: str) -> dict[str, set[str]]:
    """Devuelve por paquete las líneas `# via` de un lock."""
    vias: dict[str, set[str]] = {}
    actual: str | None = None
    for linea in texto.splitlines():
        coincidencia = _PIN.match(linea)
        if coincidencia:
            actual = _canonico(coincidencia.group(1))
            vias[actual] = set()
            continue
        if actual is None:
            continue
        limpia = linea.strip()
        if limpia.startswith("# via "):
            vias[actual].add(limpia.removeprefix("# via ").strip())
        elif limpia == "# via":
            continue
        elif limpia.startswith("#   "):
            vias[actual].add(limpia.removeprefix("#").strip())
    return vias


def _exclusivos(runtime_txt: str, cert_txt: str) -> tuple[set[str], set[str], set[str]]:
    """Devuelve exclusivos, intersección con certificación y paquetes con constraint runtime."""
    exclusivos = set(_pines(cert_txt)) - set(_pines(runtime_txt))
    interseccion = set(_pines(runtime_txt)) & EXCLUSIVOS_DE_CERTIFICACION
    con_constraint = {paquete for paquete, origenes in _vias(cert_txt).items() if "-c requirements.lock" in origenes}
    return exclusivos, interseccion, con_constraint


def _discrepancias(runtime: dict[str, str], cert: dict[str, str]) -> list[str]:
    """Devuelve faltantes o versiones distintas entre el runtime y la certificación."""
    fallos: list[str] = []
    for paquete, version in sorted(runtime.items()):
        if paquete not in cert:
            fallos.append(f"{paquete} falta en el lock de certificación")
        elif cert[paquete] != version:
            fallos.append(f"{paquete} difiere: runtime {version} vs certificación {cert[paquete]}")
    return fallos


def _menciona_certificacion(textos: list[str]) -> bool:
    """Indica si alguno de los textos menciona requirements-test."""
    return any("requirements-test" in t for t in textos)


def _instalaciones_no_fijadas(runs: list[str]) -> list[str]:
    """Devuelve comandos pip install que no usan los locks."""
    desviaciones: list[str] = []
    for run in runs:
        for orden in run.split("&&"):
            limpia = orden.strip()
            if limpia.startswith("pip install") and limpia not in {INSTALACION_LOCK, INSTALACION_LOCK_CERTIFICACION}:
                desviaciones.append(limpia)
    return desviaciones


def _instala_desde(runs: list[str], instalacion: str) -> bool:
    """Indica si un comando pip install fijado tiene pip check posterior en el mismo RUN."""
    for run in runs:
        ordenes = [o.strip() for o in run.split("&&")]
        for indice, orden in enumerate(ordenes):
            if orden.startswith(instalacion) and any(o == "pip check" for o in ordenes[indice + 1 :]):
                return True
    return False


def _fuentes_prohibidas(copias: list[str]) -> list[str]:
    """Devuelve fuentes COPY/ADD que filtran pruebas, qa o pyproject.toml."""
    fuentes_prohibidas: list[str] = []
    for copia in copias:
        partes = [p for p in copia.split() if not p.startswith("--")]
        fuentes = partes[:-1]
        for fuente in fuentes:
            if {"tests", "qa"} & set(Path(fuente).parts) or Path(fuente).name == "pyproject.toml":
                fuentes_prohibidas.append(fuente)
    return fuentes_prohibidas


def _esta_protegido_por_import_error(nodo: ast.AST, padres: dict[ast.AST, ast.AST]) -> bool:
    """Indica si un import está protegido por try/except ImportError."""
    actual = nodo
    while True:
        padre = padres.get(actual)
        if padre is None:
            return False
        if isinstance(padre, ast.Try) and actual in padre.body and any(
            (isinstance(handler.type, ast.Name) and handler.type.id in {"ImportError", "ModuleNotFoundError"})
            or (isinstance(handler.type, ast.Tuple) and any(isinstance(t, ast.Name) and t.id in {"ImportError", "ModuleNotFoundError"} for t in handler.type.elts))
            for handler in padre.handlers
        ):
            return True
        actual = padre


def _modulo_esta_protegido(arbol: ast.AST, modulo: str) -> bool:
    """Indica si todos los imports de un módulo están protegidos por ImportError."""
    padres: dict[ast.AST, ast.AST] = {}
    for padre in ast.walk(arbol):
        for hijo in ast.iter_child_nodes(padre):
            padres[hijo] = padre
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            if any(alias.name.split(".")[0] == modulo and not _esta_protegido_por_import_error(nodo, padres) for alias in nodo.names):
                return False
        elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module is not None:
            if nodo.module.split(".")[0] == modulo and not _esta_protegido_por_import_error(nodo, padres):
                return False
    return True


def _modulos_importados(arbol: ast.AST) -> set[str]:
    """Devuelve los módulos top-level importados en un AST."""
    modulos: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos.update(alias.name.split(".")[0] for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module is not None:
            modulos.add(nodo.module.split(".")[0])
    return modulos


def test_idf_01_el_manifiesto_runtime_no_declara_herramientas() -> None:
    runtime = set(_pines((BACKEND / "requirements.txt").read_text(encoding="utf-8")))
    certificacion = set(_pines((BACKEND / "requirements-test.txt").read_text(encoding="utf-8")))
    assert runtime & HERRAMIENTAS_DE_CERTIFICACION == set()
    assert runtime & certificacion == set()


def test_idf_02_el_manifiesto_de_certificacion_incluye_el_runtime_y_solo_anade_sus_herramientas() -> None:
    texto = (BACKEND / "requirements-test.txt").read_text(encoding="utf-8")
    primera = next(
        (
            linea.strip()
            for linea in texto.splitlines()
            if linea.strip() and not linea.strip().startswith("#")
        ),
        None,
    )
    assert primera == "-r requirements.txt"
    pines = _pines(texto)
    assert set(pines) == HERRAMIENTAS_DE_CERTIFICACION
    lock_cert_texto = (BACKEND / "requirements-test.lock").read_text(encoding="utf-8")
    cert = _pines(lock_cert_texto)
    assert all(cert.get(n) == v for n, v in pines.items())


def test_idf_03_el_lock_runtime_no_contiene_nada_exclusivo_de_certificacion_y_el_de_certificacion_lo_restringe() -> None:
    runtime_txt = (BACKEND / "requirements.lock").read_text(encoding="utf-8")
    cert_txt = (BACKEND / "requirements-test.lock").read_text(encoding="utf-8")
    exclusivos, interseccion, con_constraint = _exclusivos(runtime_txt, cert_txt)
    assert exclusivos == EXCLUSIVOS_DE_CERTIFICACION
    assert interseccion == set()
    assert con_constraint == set(_pines(runtime_txt))


def test_idf_04_las_versiones_del_subconjunto_runtime_coinciden_en_ambos_locks() -> None:
    runtime = _pines((BACKEND / "requirements.lock").read_text(encoding="utf-8"))
    cert = _pines((BACKEND / "requirements-test.lock").read_text(encoding="utf-8"))
    assert _discrepancias(runtime, cert) == []


def test_idf_05_la_cabecera_del_lock_de_certificacion_hereda_la_configuracion_del_runtime() -> None:
    cert_cabecera = _comando_de_cabecera((BACKEND / "requirements-test.lock").read_text(encoding="utf-8"))
    runtime_cabecera = _comando_de_cabecera((BACKEND / "requirements.lock").read_text(encoding="utf-8"))
    dockerfile = (RAIZ / "Dockerfile.backend").read_text(encoding="utf-8")
    assert cert_cabecera.startswith("uv pip compile requirements-test.txt --constraint requirements.lock ")
    assert f"--python-version {_python_de_la_base(dockerfile)}" in cert_cabecera
    assert "--python-platform x86_64-unknown-linux-gnu" in cert_cabecera
    assert re.search(r"(?:^|\s)--upgrade(?:\s|$)", cert_cabecera)
    assert cert_cabecera.endswith("-o requirements-test.lock")
    coincidencia_cert = re.search(r"--exclude-newer (\S+)", cert_cabecera)
    coincidencia_runtime = re.search(r"--exclude-newer (\S+)", runtime_cabecera)
    assert coincidencia_cert is not None
    assert coincidencia_runtime is not None
    assert coincidencia_cert.group(1) == coincidencia_runtime.group(1)


def test_idf_06_la_imagen_instala_cada_lock_en_su_etapa_y_nunca_paquetes_sueltos() -> None:
    dockerfile = (RAIZ / "Dockerfile.backend").read_text(encoding="utf-8")
    etapas, final = _etapas_completas(dockerfile)
    cadena_final = _cadena_efectiva(etapas, final)
    textos_runtime = _todas(etapas, cadena_final, "RUN") + _todas(etapas, cadena_final, "COPY")
    assert not _menciona_certificacion(textos_runtime)
    cadena_dev = _cadena_efectiva(etapas, "dev")
    assert _instala_desde(_todas(etapas, cadena_dev, "RUN"), INSTALACION_LOCK_CERTIFICACION)
    assert "resources/backend/requirements-test.lock /tmp/requirements-test.lock" in _todas(etapas, cadena_dev, "COPY")
    for etapa in etapas:
        assert _instalaciones_no_fijadas(_todas(etapas, [etapa], "RUN")) == []


def test_idf_07_la_cadena_runtime_no_copia_pruebas_qa_ni_pyproject_toml() -> None:
    dockerfile = (RAIZ / "Dockerfile.backend").read_text(encoding="utf-8")
    etapas, final = _etapas_completas(dockerfile)
    cadena_final = _cadena_efectiva(etapas, final)
    copias = _todas(etapas, cadena_final, "COPY") + _todas(etapas, cadena_final, "ADD")
    assert copias
    assert _fuentes_prohibidas(copias) == []


def test_idf_08_cada_import_de_terceros_del_producto_esta_en_el_grafo_runtime() -> None:
    ficheros = [ruta for directorio in DIRECTORIOS_DEL_PRODUCTO if directorio.exists() for ruta in directorio.rglob("*.py")]
    assert ficheros
    pines_lock = set(_pines((BACKEND / "requirements.lock").read_text(encoding="utf-8")))
    distribuciones = importlib.metadata.packages_distributions()
    fallos: list[str] = []
    sin_distribucion: set[str] = set()
    for ruta in ficheros:
        arbol = ast.parse(ruta.read_text(encoding="utf-8"))
        for top in sorted(_modulos_importados(arbol)):
            if top in sys.stdlib_module_names or top in {"app", "central_authority"}:
                continue
            if top in OPCIONALES_DEL_PRODUCTO and not _modulo_esta_protegido(arbol, top):
                fallos.append(f"{ruta.relative_to(BACKEND)}: import de {top} sin proteger por ImportError")
            dists = distribuciones.get(top, [])
            if not dists:
                sin_distribucion.add(top)
                continue
            if not any(_canonico(d) in pines_lock for d in dists):
                fallos.append(f"{top}: {sorted(dists)} fuera de requirements.lock")
    assert fallos == [], fallos
    assert sin_distribucion == OPCIONALES_DEL_PRODUCTO, sin_distribucion


def test_idf_09_los_analizadores_detectan_desviaciones() -> None:
    assert _vias("pytest==9.0.3\n    # via -r requirements-test.txt\n") == {"pytest": {"-r requirements-test.txt"}}
    assert _vias("pytest==9.0.3\n    # via\n    #   -r requirements-test.txt\n    #   otro\n") == {"pytest": {"-r requirements-test.txt", "otro"}}
    exclusivos_b, interseccion_b, _ = _exclusivos("pytest==9.0.3\n", "pytest==9.0.3\n    # via -r requirements-test.txt\n")
    assert interseccion_b == {"pytest"}
    assert exclusivos_b != EXCLUSIVOS_DE_CERTIFICACION
    assert _discrepancias({"a": "1.0"}, {"a": "2.0"}) == ["a difiere: runtime 1.0 vs certificación 2.0"]
    assert _discrepancias({"a": "1.0"}, {}) == ["a falta en el lock de certificación"]
    assert _instalaciones_no_fijadas(["pip install pytest"]) == ["pip install pytest"]
    assert _instalaciones_no_fijadas(["pip install pytest httpx"]) == ["pip install pytest httpx"]
    assert _instalaciones_no_fijadas([INSTALACION_LOCK_CERTIFICACION + " && pip check"]) == []
    assert _instalaciones_no_fijadas([INSTALACION_LOCK + " && pip check"]) == []
    assert _instala_desde([INSTALACION_LOCK_CERTIFICACION + " && pip check"], INSTALACION_LOCK_CERTIFICACION)
    assert not _instala_desde(["pip check && " + INSTALACION_LOCK_CERTIFICACION], INSTALACION_LOCK_CERTIFICACION)
    sintetico_f = "FROM python:3.13-slim AS base\nRUN pip install --no-cache-dir --no-deps -r /tmp/requirements.lock && pip check\nFROM base AS runtime\nRUN pip install --no-cache-dir --no-deps -r /tmp/requirements-test.lock\n"
    etapas_s, final_s = _etapas_completas(sintetico_f)
    assert _menciona_certificacion(_todas(etapas_s, _cadena_efectiva(etapas_s, final_s), "RUN"))
    sintetico_g = "FROM python:3.13-slim AS base\nFROM base AS runtime\nCOPY resources/backend/tests ./tests\n"
    etapas_g, final_g = _etapas_completas(sintetico_g)
    assert _fuentes_prohibidas(_todas(etapas_g, _cadena_efectiva(etapas_g, final_g), "COPY")) == ["resources/backend/tests"]
    assert _fuentes_prohibidas(["resources/backend/pyproject.toml ./pyproject.toml", "resources/backend/app ./app"]) == ["resources/backend/pyproject.toml"]
    assert _modulo_esta_protegido(ast.parse("def f():\n    try:\n        import boto3\n    except ImportError:\n        pass\n"), "boto3")
    assert not _modulo_esta_protegido(ast.parse("import boto3\n"), "boto3")
    assert not _modulo_esta_protegido(ast.parse("try:\n    import boto3\nexcept ValueError:\n    pass\n"), "boto3")
    assert _modulos_importados(ast.parse("def f():\n    import boto3\nfrom os import path\nfrom . import x\n")) == {"boto3", "os"}
