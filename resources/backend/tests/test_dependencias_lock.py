"""IDL · Contrato del conjunto de dependencias de despliegue (Spec 052, OD-CERT-05).

- IDL-01 el lock contiene cada directa con su pin exacto;
- IDL-02 el lock contiene reportlab, python-magic y los extras de uvicorn[standard];
- IDL-03 cada línea del lock es un pin exacto y único;
- IDL-04 la cabecera declara el comando canónico uv pip compile;
- IDL-05 el lock que corresponde (runtime o certificación) respeta los suelos de cve-review;
- IDL-06 la imagen instala el lock sin volver a resolver dependencias;
- IDL-07 los analizadores detectan desviaciones.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from packaging.version import Version

from tests.test_imagen_backend_etapas import _etapas_completas, _todas
from tests.test_imagen_backend_mime import _cadena_efectiva, _instrucciones

BACKEND = Path(__file__).resolve().parents[1]
RAIZ = BACKEND.parents[1]

# Versiones corregidas de docs/evidence/cve-review.md: el lock no puede bajar de ellas.
SUELOS_CVE: dict[str, str] = {
    "starlette": "1.3.1",
    "cryptography": "50.0.2",
    "pyjwt": "2.15.0",
    "python-multipart": "0.0.31",
}

# Suelo de cve-review que aplica al grafo de certificación, no al runtime.
SUELOS_CVE_CERTIFICACION: dict[str, str] = {"pytest": "9.0.3"}

EXTRAS_UVICORN_STANDARD = frozenset({"httptools", "uvloop", "watchfiles", "websockets", "python-dotenv", "pyyaml"})

INSTALACION_LOCK = "pip install --no-cache-dir --no-deps -r /tmp/requirements.lock"

_PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]+\])?==([^\s;#]+)\s*$")


def _canonico(nombre: str) -> str:
    """Normaliza un nombre de paquete según PEP 503, ignorando extras."""
    return re.sub(r"[-_.]+", "-", nombre).split("[", 1)[0].lower()


def _lineas_de_paquete(texto: str) -> list[str]:
    """Líneas no vacías cuyo primer carácter no es espacio ni #, sin el salto final."""
    return [linea.rstrip("\n") for linea in texto.splitlines() if linea and not linea[0].isspace() and not linea.startswith("#")]


def _pines(texto: str) -> dict[str, str]:
    """Devuelve {nombre canónico: versión} para cada pin exacto; lanza ValueError ante duplicados."""
    pines: dict[str, str] = {}
    for linea in _lineas_de_paquete(texto):
        coincidencia = _PIN.match(linea)
        if not coincidencia:
            continue
        nombre = _canonico(coincidencia.group(1))
        if nombre in pines:
            raise ValueError(nombre)
        pines[nombre] = coincidencia.group(3)
    return pines


def _lineas_no_fijadas(texto: str) -> list[str]:
    """Líneas de paquete que no son un pin exacto `nombre==versión`."""
    return [linea for linea in _lineas_de_paquete(texto) if not _PIN.match(linea)]


def _contraste(directas: dict[str, str], lock: dict[str, str]) -> tuple[list[str], list[str]]:
    """Devuelve directas faltantes y contradictorias, ambas ordenadas."""
    faltantes = sorted(set(directas) - set(lock))
    contradictorias = sorted(nombre for nombre in directas if nombre in lock and lock[nombre] != directas[nombre])
    return faltantes, contradictorias


def _comando_de_cabecera(texto: str) -> str:
    """Contenido de la primera línea con 'uv pip compile', sin el # inicial ni espacios."""
    for linea in texto.splitlines():
        limpia = linea.strip()
        if limpia.startswith("#") and "uv pip compile" in limpia:
            return limpia.lstrip("#").strip()
    raise AssertionError("No se encontró la línea de cabecera con 'uv pip compile'")


def _python_de_la_base(texto_dockerfile: str) -> str:
    """Versión Python de la imagen del FROM de la etapa raíz de la cadena efectiva."""
    etapas, final = _etapas_completas(texto_dockerfile)
    cadena = _cadena_efectiva(etapas, final)
    raiz = cadena[0]
    for instruccion, argumentos in _instrucciones(texto_dockerfile):
        if instruccion != "FROM":
            continue
        partes = re.split(r"\s+AS\s+", argumentos, flags=re.IGNORECASE)
        imagen = partes[0].strip()
        nombre = partes[1].strip() if len(partes) > 1 else imagen
        if nombre != raiz:
            continue
        coincidencia = re.search(r"^python:(\d+\.\d+)", imagen)
        if coincidencia:
            return coincidencia.group(1)
    raise AssertionError("No se encontró la imagen Python de la etapa raíz")


def _instala_desde_lock(runs: list[str]) -> bool:
    """True si un RUN instala el lock y luego ejecuta pip check en el mismo RUN."""
    for run in runs:
        ordenes = [orden.strip() for orden in run.split("&&")]
        for indice, orden in enumerate(ordenes):
            if orden.startswith(INSTALACION_LOCK):
                if any(candidata == "pip check" for candidata in ordenes[indice + 1 :]):
                    return True
    return False


def _reinstala_requirements(runs: list[str]) -> bool:
    """True si alguna orden instala pip desde requirements.txt."""
    for run in runs:
        for orden in run.split("&&"):
            if "pip install" in orden and "requirements.txt" in orden:
                return True
    return False


def _lock_texto() -> str:
    """Lee requirements.lock."""
    return (BACKEND / "requirements.lock").read_text()


def _lock_certificacion_texto() -> str:
    """Lee requirements-test.lock."""
    return (BACKEND / "requirements-test.lock").read_text(encoding="utf-8")


def _requirements_texto() -> str:
    """Lee requirements.txt."""
    return (BACKEND / "requirements.txt").read_text()


def _dockerfile_texto() -> str:
    """Lee Dockerfile.backend."""
    return (RAIZ / "Dockerfile.backend").read_text()


def test_idl_01_el_lock_contiene_cada_directa_con_su_pin_exacto() -> None:
    directas = _pines(_requirements_texto())
    lock = _pines(_lock_texto())
    faltantes, contradictorias = _contraste(directas, lock)
    assert faltantes == [] and contradictorias == [], f"Faltantes: {faltantes}, contradictorias: {contradictorias}"


def test_idl_02_el_lock_contiene_reportlab_python_magic_y_los_extras_de_uvicorn_standard() -> None:
    lock = _pines(_lock_texto())
    requeridos = {"reportlab", "python-magic", "pyyaml"} | set(EXTRAS_UVICORN_STANDARD)
    ausentes = sorted(requeridos - set(lock))
    assert not ausentes, f"Faltan en el lock: {ausentes}"


def test_idl_03_cada_linea_del_lock_es_un_pin_exacto_y_unico() -> None:
    lock = _lock_texto()
    assert _lineas_no_fijadas(lock) == []
    assert len(_pines(lock)) == len(_lineas_de_paquete(lock))


def test_idl_04_la_cabecera_declara_el_comando_canonico() -> None:
    comando = _comando_de_cabecera(_lock_texto())
    assert comando.startswith("uv pip compile requirements.txt ")
    version = re.search(r"--python-version (\d+\.\d+)", comando)
    assert version is not None
    assert version.group(1) == _python_de_la_base(_dockerfile_texto())
    assert "--python-platform x86_64-unknown-linux-gnu" in comando
    assert re.search(r"--exclude-newer \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,9})?Z", comando)
    assert re.search(r"(^|\s)--upgrade(\s|$)", comando)
    assert comando.endswith("-o requirements.lock")


def test_idl_05_el_lock_respeta_el_suelo_de_cve_review() -> None:
    lock_runtime = _pines(_lock_texto())
    for paquete, suelo in SUELOS_CVE.items():
        assert paquete in lock_runtime, f"{paquete} no está en el lock"
        assert Version(lock_runtime[paquete]) >= Version(suelo), f"{paquete}: lock {lock_runtime[paquete]} < suelo {suelo}"

    lock_certificacion = _pines(_lock_certificacion_texto())
    for paquete, suelo in SUELOS_CVE_CERTIFICACION.items():
        assert paquete in lock_certificacion, f"{paquete} no está en el lock de certificación"
        assert Version(lock_certificacion[paquete]) >= Version(
            suelo
        ), f"{paquete}: lock certificación {lock_certificacion[paquete]} < suelo {suelo}"

    for paquete in SUELOS_CVE_CERTIFICACION:
        assert paquete not in lock_runtime, f"{paquete} es de certificación y no debe estar en el lock runtime"


def test_idl_06_la_imagen_instala_el_lock_sin_volver_a_resolver() -> None:
    dockerfile = _dockerfile_texto()
    etapas, final = _etapas_completas(dockerfile)
    cadena_final = _cadena_efectiva(etapas, final)
    cadena_dev = _cadena_efectiva(etapas, "dev")

    for cadena in (cadena_final, cadena_dev):
        runs = _todas(etapas, cadena, "RUN")
        copies = _todas(etapas, cadena, "COPY")
        mensaje = f"Cadena {cadena}: copies={copies}, runs={runs}"
        assert "resources/backend/requirements.lock /tmp/requirements.lock" in copies, mensaje
        assert _instala_desde_lock(runs) is True, mensaje
        assert _reinstala_requirements(runs) is False, mensaje

    runs_raiz = _todas(etapas, [cadena_final[0]], "RUN")
    assert _instala_desde_lock(runs_raiz) is True


def test_idl_07_los_analizadores_detectan_desviaciones() -> None:
    # (a) contraste de directas
    assert _contraste({"a": "1.0", "b": "2.0"}, {"a": "1.0"}) == (["b"], [])
    assert _contraste({"a": "1.0", "b": "2.0"}, {"a": "1.1", "b": "2.0"}) == ([], ["a"])

    # (b) líneas sin fijar, duplicados y normalización
    assert _lineas_no_fijadas("anyio>=4\nh11==0.16.0\n    # via x\n") == ["anyio>=4"]
    with pytest.raises(ValueError):
        _pines("A_b==1\na-b==2\n")
    assert _pines("Uvicorn[standard]==0.32.1\n") == {"uvicorn": "0.32.1"}

    # (c) Dockerfile que instala requirements.txt
    dockerfile_requirements = "FROM python:3.13-slim AS base\nCOPY r.txt /tmp/requirements.txt\nRUN pip install --no-cache-dir -r /tmp/requirements.txt\nFROM base AS runtime\n"
    etapas_c, final_c = _etapas_completas(dockerfile_requirements)
    cadena_c = _cadena_efectiva(etapas_c, final_c)
    runs_c = _todas(etapas_c, cadena_c, "RUN")
    assert _instala_desde_lock(runs_c) is False
    assert _reinstala_requirements(runs_c) is True

    # (d) lock instalado solo en dev
    dockerfile_dev = "FROM python:3.13-slim AS base\nFROM base AS dev\nRUN pip install --no-cache-dir --no-deps -r /tmp/requirements.lock && pip check\nFROM base AS runtime\n"
    etapas_d, final_d = _etapas_completas(dockerfile_dev)
    cadena_runtime = _cadena_efectiva(etapas_d, final_d)
    cadena_dev_d = _cadena_efectiva(etapas_d, "dev")
    assert _instala_desde_lock(_todas(etapas_d, cadena_runtime, "RUN")) is False
    assert _instala_desde_lock(_todas(etapas_d, cadena_dev_d, "RUN")) is True

    # (e) orden y presencia de pip check
    assert _instala_desde_lock(["pip install --no-cache-dir --no-deps -r /tmp/requirements.lock"]) is False
    assert _instala_desde_lock(["pip check && pip install --no-cache-dir --no-deps -r /tmp/requirements.lock"]) is False

    # (f) versión Python de la etapa raíz, incluida una etapa cuyo nombre contiene "AS"
    assert _python_de_la_base("FROM python:3.12-slim AS base\nFROM base AS runtime\n") == "3.12"
    assert _python_de_la_base("FROM python:3.11-slim AS BASE\nFROM BASE AS runtime\n") == "3.11"
