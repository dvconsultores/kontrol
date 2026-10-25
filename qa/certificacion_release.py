"""Orden canónica de certificación de release de KONTROL.

El ciclo es:

* se crea un espacio de trabajo por corrida bajo el home de certificación y se protege con
  un cerrojo para que solo exista una certificación a la vez;
* las etapas se ejecutan en orden y la primera que falla corta las siguientes y fija el RC;
* las etapas de cierre 120/130/140 se ejecutan siempre;
* nada se reintenta;
* el manifiesto se reescribe saneado tras cada etapa.

Requiere Python 3.11 o superior (biblioteca estándar únicamente).
Las etapas 0..110 están pendientes de implementación en tareas posteriores y fallan cerrado.
"""
from __future__ import annotations

import argparse
import base64
import csv
import difflib
import fcntl
import hashlib
import http.client
import io
import json
import math
import os
import re
import secrets
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

#: Raíz del repositorio KONTROL.
RAIZ = Path(__file__).resolve().parent.parent
#: Evidencia versionable de cada corrida (fuera de Git vía .gitignore).
EVIDENCIA = RAIZ / "qa" / "certificaciones"
VARIABLE_HOME = "KONTROL_QA_CERT_HOME"
HOME_POR_DEFECTO = "~/.cache/kontrol-qa/certificacion"
#: Marca de propiedad dentro de cada espacio de corrida.
MARCA = ".kontrol-certificacion.json"
#: Cerrojo global en la raíz del home de certificación.
CERROJO = ".certificacion.lock"
ESQUEMA_MANIFIESTO = 1
BASE_CERTIFICADA = RAIZ / "specs" / "001-fundacion" / "certified-deployment-base.json"
LOCK_RUNTIME = RAIZ / "resources" / "backend" / "requirements.lock"
LOCK_CERTIFICACION = RAIZ / "resources" / "backend" / "requirements-test.lock"
REFERENCIA = RAIZ / "qa" / "certificacion_referencia.json"

RC_PASS = 0
RC_FALLO_CERTIFICACION = 1
RC_ENTORNO_INVALIDO = 3
RC_SOLO_DIAGNOSTICO = 4
RC_INTERNO = 70

VEREDICTO_PASS = "PASS"
VEREDICTO_FALLO = "CERTIFICATION_FAILURE"
VEREDICTO_ENTORNO = "INVALID_ENVIRONMENT"
VEREDICTO_INTERNO = "INTERNAL_OR_PREFLIGHT_FAILURE"
VEREDICTO_DIAGNOSTICO = "PREFLIGHT_ONLY_NOT_CERTIFIED"
VEREDICTO_INTERRUMPIDA = "INTERRUPTED"

PASS = "PASS"
FAIL = "FAIL"
INVALIDO = "INVALID_ENVIRONMENT"
ERROR = "ERROR"
NO_EJECUTADA = "NOT_RUN"

ESPERA_SALUD_MIN_POR_DEFECTO = 30
URL_CON_CREDENCIALES = re.compile(r"://[^/\s:@]+:[^@\s]+@")
VARIABLES_DE_PYTHON_EXCLUIDAS = (
    "PYTHONPATH",
    "PYTHONHOME",
    "PYTHONSTARTUP",
    "PYTHONUSERBASE",
    "PYTHONSAFEPATH",
    "VIRTUAL_ENV",
    "CONDA_PREFIX",
    "__PYVENV_LAUNCHER__",
)
#: Política versionada del entorno heredado: CANONICALIZED y SECRET tienen precedencia al clasificar; solo se registran nombres, nunca valores.
POLITICA_DE_ENTORNO_VERSION = 1
VARIABLES_CANONICALIZADAS = ("CI", "PYTHONDONTWRITEBYTECODE", *VARIABLES_DE_PYTHON_EXCLUIDAS)
VARIABLES_HEREDADAS_PERMITIDAS = ("PATH", "HOME", "USER", "LOGNAME", "SHELL", "LANG", "LANGUAGE", "TERM", "TMPDIR", "TZ",
    "XDG_CACHE_HOME", "XDG_RUNTIME_DIR", "SSL_CERT_FILE", "SSL_CERT_DIR", "NODE_EXTRA_CA_CERTS", "PLAYWRIGHT_BROWSERS_PATH",
    "PYTHONIOENCODING", "PYTHONUTF8", "PYTHONUNBUFFERED", "KONTROL_QA_CERT_HOME", "KONTROL_CLAMSCAN_PATH", "KONTROL_CLAMAV_DB")
PREFIJOS_HEREDADOS_PERMITIDOS = ("LC_",)
PREFIJOS_PROHIBIDOS = (
    "PYTEST_", "PWTEST_", "PLAYWRIGHT_", "PYTHON", "KONTROL_", "UV_", "PIP_", "NPM_CONFIG_", "npm_config_", "COVERAGE_",
    "PG", "GIT_CONFIG",
)
VARIABLES_PROHIBIDAS = (
    "PWDEBUG", "NODE_OPTIONS", "NODE_PATH", "NODE_ENV", "LD_PRELOAD", "LD_LIBRARY_PATH", "LD_AUDIT",
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR", "GIT_NAMESPACE", "GIT_CEILING_DIRECTORIES", "GIT_DISCOVERY_ACROSS_FILESYSTEM", "GIT_ATTR_SOURCE",
    "GIT_GRAFT_FILE", "GIT_REPLACE_REF_BASE", "GIT_NO_REPLACE_OBJECTS",
)
MARCAS_DE_SECRETO = ("TOKEN", "SECRET", "PASSWORD", "PASSWD", "CREDENTIAL", "PRIVATE_KEY", "API_KEY", "ACCESS_KEY")
CLASES_DE_ENTORNO = ("CANONICALIZED", "ALLOWED_INHERITED", "FORBIDDEN", "SECRET", "IRRELEVANT")
CAMPOS_DEL_MANIFIESTO = (
    "RUN_ID",
    "STARTED_AT",
    "FINISHED_AT",
    "GIT_HEAD",
    "DIRTY_STATE",
    "CERTIFICATION_INPUT_TREE_HASH",
    "ENVIRONMENT_POLICY",
    "BASE_INDEX_DIGEST",
    "AMD64_MANIFEST_DIGEST",
    "V6R_PYTHON",
    "V6R_LOCK_HASH",
    "V6R_FREEZE_HASH",
    "V6C_LOCK_HASH",
    "RUNTIME_SUBSET_EQUAL",
    "POSTGRES_VERSION",
    "POSTGRES_QA_SOURCE",
    "SQLITE_RESULT",
    "POSTGRES_RESULT",
    "E2E_RESULT",
    "CANONICAL_E2E_WORKERS",
    "CANONICAL_E2E_RETRIES",
    "OPENAPI_RESULT",
    "PIP_AUDIT_PYPI",
    "PIP_AUDIT_OSV",
    "ALEMBIC_PARITY",
    "E2E_AUTHORITY_PARITY",
    "E2E_HELPER_PARITY",
    "ENVIRONMENT_VALIDITY",
    "RESIDUE_STATUS",
    "FINAL_VERDICT",
)
CAMPOS_DE_CIERRE = ("RUN_ID", "STARTED_AT", "FINISHED_AT", "RESIDUE_STATUS", "FINAL_VERDICT")
POLITICA_DEL_ARBOL_VERSION = 1
VERSION_HASH_DE_ENTRADA = 2
#: Rutas que no forman parte del árbol certificado: evidencia y documentos que se escriben al cerrar (ninguna etapa los
#: lee), material de la dueña (queda como en HEAD) y ficheros con secretos.
EXCLUSIONES_DEL_ARBOL = (":(exclude,glob)specs/**/evidence/**", ":(exclude,glob)specs/**/*.md", ":(exclude,glob)docs/roadmap/**",
    ":(exclude)requerimientos", ":(exclude,glob)**/.env", ":(exclude,glob)**/.env.*", ":(exclude,glob)**/*.pem",
    ":(exclude,glob)**/*.key", ":(exclude,glob)**/id_rsa*", ":(exclude,glob)**/id_ed25519*", ":(exclude,glob)**/*.p12",
    ":(exclude,glob)**/*.pfx")
ARBOL_GIT = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")


class FalloDeEtapa(Exception):
    """Base para los fallos que fijan el RC y el manifiesto."""

    rc = RC_INTERNO
    estado = ERROR

    def __init__(self, motivo: str, detalle: Mapping[str, Any] | None = None) -> None:
        super().__init__(motivo)
        self.motivo = motivo
        self.detalle = dict(detalle or {})


class FalloDeCertificacion(FalloDeEtapa):
    """Fallo que niega la certificación del release."""

    rc = RC_FALLO_CERTIFICACION
    estado = FAIL


class EntornoInvalido(FalloDeEtapa):
    """El entorno de certificación no cumple el contrato."""

    rc = RC_ENTORNO_INVALIDO
    estado = INVALIDO


class FalloDePreflight(FalloDeEtapa):
    """Fallo previo a la creación del contexto de corrida."""

    rc = RC_INTERNO
    estado = FAIL


class ErrorInterno(FalloDeEtapa):
    """Fallo interno del orquestador."""

    rc = RC_INTERNO
    estado = ERROR


class Interrumpida(BaseException):
    """La corrida recibió una señal: se limpia y se sale."""


def _al_recibir_senal(numero: int, _marco: Any) -> None:
    raise Interrumpida(signal.Signals(numero).name)


@dataclass(frozen=True)
class Etapa:
    """Una etapa de la certificación: código, nombre, función y si es de cierre."""
    codigo: int
    nombre: str
    funcion: Callable[[Contexto], dict[str, Any]]
    de_cierre: bool = False


@dataclass
class ResultadoSujeto:
    """RC y salida cruda (solo en memoria) de un sujeto."""
    rc: int
    salida: str


@dataclass
class Contexto:
    """Estado compartido de una corrida de certificación."""
    run_id: str
    opciones: argparse.Namespace
    home: Path
    espacio: Path
    evidencia: Path
    raices: dict[str, str]
    manifiesto: dict[str, Any]
    datos: dict[str, Any] = field(default_factory=dict)
    vivos: dict[int, str] = field(default_factory=dict)
    fallo_previo: bool = False
    rc: int = RC_PASS
    inicio_monotonico: float = field(default_factory=time.monotonic)


def ahora_utc() -> str:
    """Devuelve el instante actual UTC en formato ISO-8601 de segundos."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def nuevo_run_id(ahora: datetime | None = None) -> str:
    """Genera el RUN_ID único de una corrida."""
    instante = ahora or datetime.now(UTC)
    return "cert_" + instante.strftime("%Y%m%dT%H%M%SZ") + "_" + secrets.token_hex(3)


def home_de_certificacion(entorno: Mapping[str, str] | None = None) -> Path:
    """Resuelve el home de certificación según KONTROL_QA_CERT_HOME."""
    entorno = os.environ if entorno is None else entorno
    valor = entorno.get(VARIABLE_HOME, "")
    if valor:
        ruta = Path(valor)
        if not ruta.is_absolute():
            raise FalloDePreflight(f"{VARIABLE_HOME} debe ser una ruta absoluta")
        return ruta
    return Path(HOME_POR_DEFECTO).expanduser()


def raices_a_sanear(entorno: Mapping[str, str], home: Path) -> dict[str, str]:
    """Ordena por longitud las raíces que el saneado debe reemplazar."""
    raices = {str(RAIZ): "<repo>", str(home): "<cert-home>", tempfile.gettempdir(): "<tmp>"}
    if entorno.get("HOME", ""):
        raices[entorno["HOME"]] = "<home>"
    return dict(sorted(raices.items(), key=lambda raiz: len(raiz[0]), reverse=True))


def sanear(texto: str, raices: Mapping[str, str]) -> str:
    """Sanea un texto reemplazando raíces y credenciales en URLs."""
    for raiz, marca in raices.items():
        texto = texto.replace(raiz, marca)
    return URL_CON_CREDENCIALES.sub("://<credenciales>@", texto)


def sanear_objeto(valor: Any, raices: Mapping[str, str]) -> Any:
    """Aplica saneado recursivo a estructuras JSON."""
    if isinstance(valor, dict):
        return {sanear(clave, raices): sanear_objeto(elemento, raices) for clave, elemento in valor.items()}
    if isinstance(valor, list | tuple):
        return [sanear_objeto(elemento, raices) for elemento in valor]
    if isinstance(valor, str):
        return sanear(valor, raices)
    return valor


def sha256_de_fichero(ruta: Path) -> str:
    """Calcula el SHA-256 de un fichero leyéndolo por bloques."""
    digest = hashlib.sha256()
    with ruta.open("rb") as fichero:
        for bloque in iter(lambda: fichero.read(1024 * 1024), b""):
            digest.update(bloque)
    return digest.hexdigest()


def hash_de_entrada(
    *,
    head: str,
    arbol: str,
    digests: Mapping[str, str],
    locks: Mapping[str, str],
    plataforma: str,
    referencia: str,
    postgres_qa: str,
) -> str:
    """Calcula el hash canónico de los insumos de la corrida."""
    semilla = json.dumps(
        {
            "version": VERSION_HASH_DE_ENTRADA,
            "head": head,
            "arbol": arbol,
            "politica_del_arbol": POLITICA_DEL_ARBOL_VERSION,
            "digests": dict(digests),
            "locks": dict(locks),
            "plataforma": plataforma,
            "referencia": referencia,
            "postgres_qa": postgres_qa,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return "sha256:" + hashlib.sha256(semilla).hexdigest()


def espacios_previos(home: Path) -> list[dict[str, str]]:
    """Lista los espacios previos incompletos para el manifiesto."""
    if not home.exists():
        return []
    previos: list[dict[str, str]] = []
    for hijo in sorted(
        path
        for path in home.iterdir()
        if path.is_dir() and not path.is_symlink() and path.name != DIRECTORIO_POSTGRES_QA
    ):
        marca = hijo / MARCA
        if not marca.exists():
            previos.append({"nombre": hijo.name, "estado": "SIN_MARCA"})
            continue
        try:
            contenido = json.loads(marca.read_text())
            estado = contenido.get("estado", "SIN_ESTADO")
        except (OSError, json.JSONDecodeError):
            previos.append({"nombre": hijo.name, "estado": "MARCA_ILEGIBLE"})
            continue
        if estado != "COMPLETA":
            previos.append({"nombre": hijo.name, "estado": estado})
    return previos


def crear_espacio(home: Path, run_id: str) -> Path:
    """Crea y marca el espacio de trabajo de la corrida."""
    espacio = home / run_id
    try:
        espacio.mkdir(mode=0o700)
    except FileExistsError:
        raise ErrorInterno("el espacio de la corrida ya existe") from None
    marca = {
        "run_id": run_id,
        "pid": os.getpid(),
        "creado": ahora_utc(),
        "estado": "EN_CURSO",
    }
    (espacio / MARCA).write_text(json.dumps(marca, indent=2, ensure_ascii=False))
    return espacio


def marcar_espacio(espacio: Path, estado: str) -> None:
    """Actualiza el estado en la marca del espacio."""
    ruta = espacio / MARCA
    marca = json.loads(ruta.read_text())
    marca["estado"] = estado
    ruta.write_text(json.dumps(marca, indent=2, ensure_ascii=False))


def es_propio(espacio: Path, home: Path, run_id: str) -> bool:
    """Comprueba que el espacio pertenece a esta corrida."""
    if espacio.parent != home or espacio.name != run_id or espacio.is_symlink() or not espacio.is_dir():
        return False
    try:
        marca = json.loads((espacio / MARCA).read_text())
    except (OSError, json.JSONDecodeError):
        return False
    return marca.get("run_id") == run_id


def eliminar_espacio(espacio: Path, home: Path, run_id: str) -> dict[str, Any]:
    """Elimina el espacio solo si pertenece a esta corrida."""
    if not espacio.exists():
        return {"eliminado": True, "motivo": "ya no existe"}
    if es_propio(espacio, home, run_id):
        shutil.rmtree(espacio)
        return {"eliminado": True}
    return {"eliminado": False, "motivo": "no es de esta corrida"}


def tomar_cerrojo(home: Path) -> int:
    """Toma el cerrojo global de certificación."""
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(home / CERROJO, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        raise FalloDePreflight("otra certificación está en curso") from None
    return fd


def clase_de_variable(nombre: str) -> str:
    """Devuelve la clase de una variable de entorno heredada, aplicando el orden de precedencia de la política."""
    if nombre in VARIABLES_CANONICALIZADAS:
        return "CANONICALIZED"
    if nombre in VARIABLES_HEREDADAS_PERMITIDAS or nombre.startswith(PREFIJOS_HEREDADOS_PERMITIDOS):
        return "ALLOWED_INHERITED"
    if nombre in VARIABLES_PROHIBIDAS or nombre.startswith(PREFIJOS_PROHIBIDOS):
        return "FORBIDDEN"
    if any(marca in nombre.upper() for marca in MARCAS_DE_SECRETO):
        return "SECRET"
    return "IRRELEVANT"


def clasificar_entorno(entorno: Mapping[str, str]) -> dict[str, list[str]]:
    """Clasifica las variables de un entorno, devolviendo únicamente los nombres ordenados por clase."""
    clases: dict[str, list[str]] = {clase: [] for clase in CLASES_DE_ENTORNO}
    for nombre in entorno:
        clases[clase_de_variable(nombre)].append(nombre)
    return {clase: sorted(nombres) for clase, nombres in clases.items()}


def comprobar_politica_de_entorno(entorno: Mapping[str, str]) -> dict[str, Any]:
    """Comprueba la política de entorno heredado y devuelve un resumen con clases, nunca valores."""
    clases = clasificar_entorno(entorno)
    if clases["FORBIDDEN"]:
        raise FalloDePreflight("variables de entorno prohibidas", {"prohibidas": clases["FORBIDDEN"]})
    return {
        "version": POLITICA_DE_ENTORNO_VERSION,
        "canonicalizadas": clases["CANONICALIZED"],
        "heredadas_permitidas": clases["ALLOWED_INHERITED"],
        "prohibidas": [],
        "secretas": clases["SECRET"],
        "irrelevantes": len(clases["IRRELEVANT"]),
    }


def entorno_de_sujeto(base: Mapping[str, str], extra: Mapping[str, str] | None = None) -> dict[str, str]:
    """Construye el entorno saneado para un proceso del sujeto."""
    entorno = {
        clave: valor
        for clave, valor in base.items()
        if clase_de_variable(clave) not in ("CANONICALIZED", "SECRET")
    }
    entorno["PYTHONDONTWRITEBYTECODE"] = "1"
    if extra:
        entorno.update(extra)
    return entorno


def ejecutar_sujeto(
    ctx: Contexto,
    etapa: str,
    argv: Sequence[str],
    *,
    cwd: Path,
    entorno: Mapping[str, str],
    timeout_s: float,
    nombre: str,
) -> ResultadoSujeto:
    """Ejecuta un proceso del sujeto con timeout y registro saneado."""
    if not argv:
        raise ErrorInterno("el programa del sujeto no puede estar vacío")
    programa = Path(argv[0])
    if not programa.is_absolute() or not programa.exists() or not os.access(programa, os.X_OK):
        raise ErrorInterno("el programa del sujeto debe ser una ruta absoluta ejecutable")
    if not math.isfinite(timeout_s) or timeout_s <= 0:
        raise ErrorInterno("el timeout del sujeto debe ser finito y mayor que cero")
    if re.fullmatch(r"[A-Za-z0-9_.-]+", nombre) is None:
        raise ErrorInterno("el nombre del sujeto solo admite [A-Za-z0-9_.-]+")

    carpeta_cruda = ctx.espacio / "registros"
    carpeta_cruda.mkdir(parents=True, exist_ok=True)
    registro_crudo = carpeta_cruda / f"{nombre}.log"

    inicio = time.monotonic()
    with registro_crudo.open("wb") as fichero:
        proceso = subprocess.Popen(
            list(argv),
            stdin=subprocess.DEVNULL,
            stdout=fichero,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            env=dict(entorno),
            start_new_session=True,
        )
    ctx.vivos[proceso.pid] = etapa
    rc: int | None = None
    try:
        try:
            rc = proceso.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            rc = None
            try:
                os.killpg(proceso.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proceso.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proceso.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proceso.wait()
    except BaseException:
        if proceso.poll() is None:
            try:
                os.killpg(proceso.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proceso.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proceso.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proceso.wait()
        ctx.vivos.pop(proceso.pid, None)
        raise

    ctx.vivos.pop(proceso.pid, None)

    duracion_s = round(time.monotonic() - inicio, 1)
    salida_cruda = registro_crudo.read_text(errors="replace")
    ctx.manifiesto["sujetos"].append(
        {
            "etapa": etapa,
            "nombre": nombre,
            "SUBJECT_COMMAND": sanear(shlex.join(argv), ctx.raices),
            "SUBJECT_RC": rc,
            "duracion_s": duracion_s,
            "timeout_s": timeout_s,
            "registro": f"registros/{nombre}.log",
        }
    )

    carpeta_evidencia = ctx.evidencia / "registros"
    carpeta_evidencia.mkdir(parents=True, exist_ok=True)
    (carpeta_evidencia / f"{nombre}.log").write_text(sanear(salida_cruda, ctx.raices))

    if rc is None:
        raise FalloDeCertificacion(f"{nombre}: superó el tiempo máximo de {timeout_s:.0f} s")
    return ResultadoSujeto(rc, salida_cruda)


def terminar_vivos(ctx: Contexto) -> list[int]:
    """Termina los procesos vivos y devuelve los que quedaron tras esperar."""
    pids = list(ctx.vivos)
    for pid in pids:
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            continue
    for _ in range(50):
        vivos = []
        for pid in pids:
            try:
                resultado = os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                continue
            if resultado == (0, 0):
                vivos.append(pid)
        pids = vivos
        if not pids:
            break
        time.sleep(0.2)
    for pid in pids:
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass
    ctx.vivos.clear()
    return pids


def escribir_manifiesto(ctx: Contexto) -> None:
    """Reescribe el manifiesto saneado en la evidencia."""
    saneado = sanear_objeto(ctx.manifiesto, ctx.raices)
    contenido = json.dumps(saneado, indent=2, ensure_ascii=False, sort_keys=False)
    temporal = ctx.evidencia / "manifest.json.tmp"
    temporal.write_text(contenido)
    os.replace(temporal, ctx.evidencia / "manifest.json")


def manifiesto_inicial(
    run_id: str,
    opciones: argparse.Namespace,
    argv: Sequence[str],
    previos: list[dict[str, str]],
) -> dict[str, Any]:
    """Construye el manifiesto inicial de la corrida."""
    manifiesto: dict[str, Any] = {"esquema": ESQUEMA_MANIFIESTO}
    for campo in CAMPOS_DEL_MANIFIESTO:
        manifiesto[campo] = "NOT_RUN"
    manifiesto["RUN_ID"] = run_id
    manifiesto["STARTED_AT"] = ahora_utc()
    manifiesto["CANONICAL_RUN_INPUT_HASH"] = None
    manifiesto["CANONICAL_RUN_INPUT_HASH_VERSION"] = VERSION_HASH_DE_ENTRADA
    manifiesto["TREE_HASH_BOUND_TO_RUN_INPUT"] = 0
    manifiesto["RC"] = None
    manifiesto["CANONICAL_COMMAND"] = shlex.join(["python3", "qa/certificar-release.py", *argv])
    manifiesto["OPTIONS"] = {
        "incluir_v0_historico": bool(opciones.incluir_v0_historico),
        "espera_salud_min": opciones.espera_salud_min,
        "conservar_espacio": bool(opciones.conservar_espacio),
        "solo_preflight": bool(opciones.solo_preflight),
    }
    manifiesto["MANUAL_STEPS"] = 0
    manifiesto["EXACT_RUNTIME_IMAGE_CONTENTS_CERTIFIED"] = 0
    manifiesto["RELEASE_DEPLOYMENT_PARITY_CERTIFIED"] = 0
    manifiesto["V0_STATUS"] = {
        "modo": "HISTORICAL_CONTROL" if opciones.incluir_v0_historico else "NOT_RUN",
        "afecta_veredicto": False,
    }
    manifiesto["ESPACIOS_PREVIOS_INCOMPLETOS"] = previos
    manifiesto["etapas"] = []
    manifiesto["sujetos"] = []
    return manifiesto


def ejecutar_etapas(ctx: Contexto, etapas: Sequence[Etapa]) -> int:
    """Ejecuta las etapas en orden y devuelve el RC fijado."""
    for etapa in etapas:
        inicio = time.monotonic()
        registro = {
            "codigo": etapa.codigo,
            "nombre": etapa.nombre,
            "estado": NO_EJECUTADA,
            "inicio": ahora_utc(),
            "duracion_s": 0.0,
            "motivo": None,
            "detalle": None,
        }
        if ctx.fallo_previo and not etapa.de_cierre:
            ctx.manifiesto["etapas"].append(registro)
            escribir_manifiesto(ctx)
            continue
        try:
            detalle = etapa.funcion(ctx)
            registro["estado"] = PASS
            registro["detalle"] = detalle
        except FalloDeEtapa as e:
            registro["estado"] = e.estado
            registro["motivo"] = e.motivo
            registro["detalle"] = e.detalle
            if e.estado == INVALIDO:
                # Cualquier etapa que declare el entorno inválido deja el manifiesto coherente con el veredicto.
                ctx.manifiesto["ENVIRONMENT_VALIDITY"] = "INVALID"
            if not ctx.fallo_previo:
                ctx.fallo_previo = True
                ctx.rc = e.rc
        except Interrumpida as e:
            registro["estado"] = ERROR
            registro["motivo"] = f"interrumpida: {e}"
            if not ctx.fallo_previo:
                ctx.fallo_previo = True
                ctx.rc = RC_INTERNO
            ctx.datos["interrumpida"] = True
        except Exception as e:
            # Única captura amplia del módulo: una excepción imprevista en una etapa nunca puede dar RC 0.
            registro["estado"] = ERROR
            registro["motivo"] = f"{type(e).__name__}: {e}"
            if not ctx.fallo_previo:
                ctx.fallo_previo = True
                ctx.rc = RC_INTERNO
        registro["duracion_s"] = round(time.monotonic() - inicio, 1)
        ctx.manifiesto["etapas"].append(registro)
        escribir_manifiesto(ctx)
    return ctx.rc


REGISTRO = "https://registry-1.docker.io"
URL_TOKEN = "https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/{repositorio}:pull"
ACEPTA_MANIFIESTOS = ",".join((
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
))
TIPOS_DE_CAPA = (
    "application/vnd.oci.image.layer.v1.tar+gzip",
    "application/vnd.docker.image.rootfs.diff.tar.gzip",
    "application/vnd.oci.image.layer.v1.tar",
)
TIMEOUT_MANIFIESTO_S = 60.0
TIMEOUT_BLOB_S = 300.0
TIMEOUT_TOKEN_S = 60.0
ESPERAS_ENTRE_DESCARGAS_S = (3.0, 6.0, 12.0)
VERSION_LIBMAGIC = "1:5.46-5"
PAQUETES_LIBMAGIC = ("libmagic1t64", "libmagic-mgc")
LD_LINUX = "lib/x86_64-linux-gnu/ld-linux-x86-64.so.2"
RUTAS_DE_BIBLIOTECAS = ("usr/local/lib", "usr/lib/x86_64-linux-gnu", "lib/x86_64-linux-gnu")
LANZADORES = ("python", "python3", "python3.13")
ENTORNO_PIP = {
    "PIP_CONFIG_FILE": os.devnull,
    "PIP_DISABLE_PIP_VERSION_CHECK": "1",
    "PIP_NO_INPUT": "1",
    "PYTHONNOUSERSITE": "1",
}
ORDEN_PIP_INSTALL = ("-m", "pip", "install", "--no-cache-dir", "--no-deps", "--retries", "5", "--timeout", "60", "-r")
PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==(\S+)$")
#: fichero real de libmagic-mgc; las otras rutas son enlaces a él
MAGIC_MGC = "usr/lib/file/magic.mgc"
#: Configuración sintética y mínima para importar el producto en el humo: sin red, sin base real, sin `.env`.
ENTORNO_DE_HUMO = {"KONTROL_ENVIRONMENT": "local", "KONTROL_DB_URL": "postgresql+psycopg2://humo@127.0.0.1:9/humo"}
PROGRAMA_DE_HUMO = '''"""Humo del runtime puro (V6R): sin pytest/httpx. Se ejecuta con cwd = resources/backend y PYTHONPATH = resources/backend.
Imprime un JSON con cada comprobación; sale 1 si alguna falla."""
import asyncio, importlib, importlib.util, json, pkgutil, sys, traceback
from datetime import UTC, datetime, timedelta

res = {"python": ".".join(map(str, sys.version_info[:3]))}
HERRAMIENTAS = ["pytest", "_pytest", "httpx", "httpcore", "certifi", "ruff", "mypy", "mypy_extensions", "packaging", "pygments", "pluggy", "iniconfig"]
res["herramientas_importables"] = [h for h in HERRAMIENTAS if importlib.util.find_spec(h) is not None]
fallos = []
def paso(nombre, fn):
    try:
        res[nombre] = fn() or "PASS"
    except Exception as e:  # noqa: BLE001 - herramienta de medida
        res[nombre] = f"FAIL {type(e).__name__}: {e}"; fallos.append(nombre); traceback.print_exc(file=sys.stderr)

def modulos():
    vistos, errores = 0, []
    for raiz in ("app", "central_authority"):
        paquete = importlib.import_module(raiz)
        for info in pkgutil.walk_packages(paquete.__path__, raiz + "."):
            if info.name.endswith("__main__"):
                continue
            try:
                importlib.import_module(info.name); vistos += 1
            except Exception as e:  # noqa: BLE001
                errores.append(f"{info.name}: {type(e).__name__}: {e}")
    if errores:
        raise RuntimeError("; ".join(errores[:5]))
    return f"PASS ({vistos} módulos)"
paso("importar_todo_el_producto", modulos)

def app_y_lifespan():
    from app.main import create_app
    app = create_app()
    async def ciclo():
        async with app.router.lifespan_context(app):
            pass
    asyncio.run(ciclo())
    s = app.openapi()
    ops = [(p, m, o) for p, d in s["paths"].items() for m, o in d.items() if m in ("get", "post", "put", "patch", "delete")]
    sec = sum(1 for _, _, o in ops if any("BearerAccessToken" in x for x in (o.get("security") or s.get("security") or [])))
    return f"PASS openapi {len(ops)}/{sec}/{len(ops) - sec}"
paso("create_app_lifespan_openapi", app_y_lifespan)

def jwt_():
    import jwt
    t = jwt.encode({"sub": "x", "exp": datetime.now(UTC) + timedelta(minutes=1)}, "k" * 40, algorithm="HS256")
    assert jwt.decode(t, "k" * 40, algorithms=["HS256"])["sub"] == "x"
paso("jwt_hs256", jwt_)

def ed25519():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    k = Ed25519PrivateKey.generate(); f = k.sign(b"kontrol"); k.public_key().verify(f, b"kontrol")
paso("cryptography_ed25519", ed25519)

def licencias():
    importlib.import_module("app.core.license_contract"); importlib.import_module("app.modules.licensing.service")
paso("licenciamiento", licencias)

def pdf():
    import io
    from reportlab.pdfgen import canvas
    b = io.BytesIO(); c = canvas.Canvas(b); c.drawString(72, 720, "KONTROL"); c.save()
    assert b.getvalue().startswith(b"%PDF")
    import magic
    assert magic.from_buffer(b.getvalue(), mime=True) == "application/pdf"
paso("reportlab_pdf_y_mime", pdf)

res["resultado"] = "FAIL" if fallos or res["herramientas_importables"] else "PASS"
print(json.dumps(res, ensure_ascii=False))
sys.exit(1 if res["resultado"] == "FAIL" else 0)
'''


def canonico_pep503(nombre: str) -> str:
    """Devuelve la forma canónica PEP 503 del nombre de un paquete."""
    return re.sub(r"[-_.]+", "-", nombre).lower()


def pines_de_lock(texto: str) -> dict[str, str]:
    """Extrae los pines exactos de un fichero lock."""
    pines: dict[str, str] = {}
    for numero, linea in enumerate(texto.splitlines(), 1):
        cruda = linea.rstrip("\r")
        if not cruda or cruda.startswith("#") or cruda.startswith((" ", "\t")):
            continue
        pareja = PIN.match(cruda)
        if not pareja:
            raise FalloDeCertificacion("línea del lock no fijada", {"linea": numero})
        nombre = canonico_pep503(pareja.group(1))
        if nombre in pines:
            raise FalloDeCertificacion("paquete repetido en el lock", {"paquete": nombre})
        pines[nombre] = pareja.group(2)
    return pines


def pines_de_freeze(texto: str) -> dict[str, str]:
    """Extrae los pines exactos de la salida de pip freeze."""
    pines: dict[str, str] = {}
    for numero, linea in enumerate(texto.splitlines(), 1):
        cruda = linea.strip()
        if not cruda:
            continue
        pareja = PIN.match(cruda)
        if not pareja:
            raise FalloDeCertificacion("freeze con una entrada no fijada", {"linea": numero})
        pines[canonico_pep503(pareja.group(1))] = pareja.group(2)
    return pines


def huella_de_pines(pines: Mapping[str, str]) -> str:
    """Calcula la huella sha256 de un conjunto de pines."""
    cuerpo = "".join(f"{n}=={v}\n" for n, v in sorted(pines.items())).encode()
    return "sha256:" + hashlib.sha256(cuerpo).hexdigest()


def diferencias_de_pines(esperado: Mapping[str, str], real: Mapping[str, str]) -> list[str]:
    """Lista las diferencias ordenadas entre dos conjuntos de pines."""
    nombres = sorted(set(esperado) | set(real))
    diferencias: list[str] = []
    for nombre in nombres:
        if nombre not in esperado:
            diferencias.append(f"sobra {nombre}=={real[nombre]}")
        elif nombre not in real:
            diferencias.append(f"falta {nombre}=={esperado[nombre]}")
        elif esperado[nombre] != real[nombre]:
            diferencias.append(f"{nombre}: {esperado[nombre]} != {real[nombre]}")
    return diferencias


def diferencias_de_subconjunto(runtime: Mapping[str, str], certificacion: Mapping[str, str]) -> list[str]:
    """Lista las diferencias del runtime dentro de certificación."""
    diferencias: list[str] = []
    for nombre in sorted(runtime):
        if nombre not in certificacion:
            diferencias.append(f"falta {nombre}")
        elif runtime[nombre] != certificacion[nombre]:
            diferencias.append(f"{nombre}: {runtime[nombre]} != {certificacion[nombre]}")
    return diferencias


def leer_base_certificada() -> dict[str, Any]:
    """Lee la base certificada y comprueba sus digest y claves mínimas."""
    try:
        base = json.loads(BASE_CERTIFICADA.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ErrorInterno("base certificada ilegible", {"motivo": str(exc)}) from exc
    bi = base.get("base_image", {})
    ca = base.get("ca_certificates", {})
    claves = (
        bi.get("repository"),
        bi.get("index_digest"),
        bi.get("platform_manifest_digest"),
        bi.get("config_digest"),
        bi.get("cpython"),
        bi.get("platform"),
        ca.get("pinned_version"),
        ca.get("deb_sha256"),
    )
    if any(clave is None for clave in claves):
        raise ErrorInterno("base certificada incompleta", {})
    digests = (bi["index_digest"], bi["platform_manifest_digest"], bi["config_digest"])
    if any(re.fullmatch(r"^sha256:[0-9a-f]{64}$", digest) is None for digest in digests):
        raise ErrorInterno("base certificada incompleta", {"digests": list(digests)})
    if re.fullmatch(r"^[0-9a-f]{64}$", ca["deb_sha256"]) is None:
        raise ErrorInterno("base certificada incompleta", {"deb_sha256": ca["deb_sha256"]})
    return base


def digest_de_plataforma(indice: Mapping[str, Any], plataforma: str) -> str:
    """Devuelve el digest del manifiesto de una plataforma concreta del índice."""
    sistema, arquitectura = plataforma.split("/")
    candidatos = [
        m for m in indice.get("manifests", [])
        if m.get("platform", {}).get("os") == sistema
        and m.get("platform", {}).get("architecture") == arquitectura
        and not m.get("platform", {}).get("variant")
    ]
    if len(candidatos) != 1:
        raise FalloDeCertificacion(f"el índice no tiene un único manifiesto para {plataforma}")
    return candidatos[0]["digest"]


def ruta_dentro(raiz: Path, relativa: str) -> Path:
    """Normaliza una ruta relativa a raiz y rechaza las que escapan."""
    if os.path.isabs(relativa):
        raise FalloDeCertificacion("ruta absoluta dentro del rootfs", {"ruta": relativa})
    normalizada = os.path.normpath(relativa)
    if normalizada == ".." or normalizada.startswith("../"):
        raise FalloDeCertificacion("ruta que escapa del rootfs", {"ruta": relativa})
    candidata = raiz / normalizada
    raiz_real = os.path.realpath(raiz)
    padre_real = os.path.realpath(candidata.parent)
    if os.path.commonpath((raiz_real, padre_real)) != raiz_real:
        raise FalloDeCertificacion("ruta que escapa del rootfs", {"ruta": relativa})
    return candidata


def _borrar(ruta: Path) -> None:
    """Borra un fichero, enlace simbólico o directorio si existe."""
    if ruta.is_symlink() or ruta.is_file():
        ruta.unlink()
    elif ruta.is_dir():
        shutil.rmtree(ruta)


def aplicar_capa(capa: Path, rootfs: Path) -> dict[str, int]:
    """Aplica una capa OCI con whiteouts y extracción protegida."""
    whiteouts = 0
    with tarfile.open(capa, "r:*") as archivo:
        miembros = archivo.getmembers()
        normales = [m for m in miembros if not os.path.basename(m.name).startswith(".wh.")]
        for miembro in miembros:
            base = os.path.basename(miembro.name)
            if base.startswith(".wh."):
                directorio = os.path.dirname(miembro.name)
                objetivo = rootfs if not directorio else ruta_dentro(rootfs, directorio)
                if base == ".wh..wh..opq":
                    if objetivo.exists():
                        for hijo in list(objetivo.iterdir()):
                            _borrar(hijo)
                else:
                    _borrar(ruta_dentro(rootfs, os.path.join(directorio, base[len(".wh."):])))
                whiteouts += 1
        archivo.extractall(rootfs, members=normales, filter="tar")
    return {"miembros": len(miembros), "whiteouts": whiteouts}


def crts_a_retirar(presentes: Iterable[str], del_paquete: set[str]) -> list[str]:
    """Lista los certificados presentes que el paquete nuevo ya no trae."""
    return sorted(set(presentes) - del_paquete)


def regenerar_bundle(rootfs: Path) -> int:
    """Regenera el bundle de CA según ca-certificates.conf."""
    conf = rootfs / "etc" / "ca-certificates.conf"
    lineas = conf.read_text().splitlines() if conf.exists() else []
    elegidas = [
        linea.strip() for linea in lineas
        if linea.strip() and not linea.startswith("#") and not linea.startswith("!")
    ]
    contenido = bytearray()
    total = 0
    for relativa in elegidas:
        candidata = rootfs / "usr" / "share" / "ca-certificates" / relativa
        if candidata.is_file():
            contenido.extend(candidata.read_bytes())
            if contenido and not contenido.endswith(b"\n"):
                contenido.extend(b"\n")
            total += 1
    if total == 0:
        raise FalloDeCertificacion("bundle de CA vacío")
    destino = rootfs / "etc" / "ssl" / "certs" / "ca-certificates.crt"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(contenido)
    return total


def texto_del_lanzador(rootfs: Path, venv: Path, bundle: Path, mgc: Path) -> str:
    """Genera el lanzador sh que arranca el Python del venv con el rootfs."""
    python = rootfs / "usr" / "local" / "bin" / "python3.13"
    python_venv = venv / "bin" / "python"
    bibliotecas = shlex.quote(":".join(str(rootfs / ruta) for ruta in RUTAS_DE_BIBLIOTECAS))
    ld = shlex.quote(str(rootfs / LD_LINUX))
    argv0 = shlex.quote(str(python_venv))
    cpython = shlex.quote(str(python))
    return "\n".join((
        "#!/bin/sh",
        f"export SSL_CERT_FILE={shlex.quote(str(bundle))}",
        f"export MAGIC={shlex.quote(str(mgc))}",
        f'exec {ld} --inhibit-cache --library-path {bibliotecas} --argv0 {argv0} {cpython} "$@"',
    )) + "\n"


def escribir_entorno_virtual(venv: Path, rootfs: Path, bundle: Path, mgc: Path, cpython: str) -> Path:
    """Escribe los lanzadores y pyvenv.cfg de un entorno virtual."""
    binario = venv / "bin"
    binario.mkdir(parents=True, exist_ok=True)
    lanzador = texto_del_lanzador(rootfs, venv, bundle, mgc)
    for nombre in LANZADORES:
        (binario / nombre).write_text(lanzador)
        (binario / nombre).chmod(0o755)
    (venv / "pyvenv.cfg").write_text(
        f"home = {rootfs / 'usr' / 'local' / 'bin'}\n"
        "include-system-site-packages = false\n"
        f"version = {cpython}\n"
    )
    return binario / "python"


class _SinRedireccion(urllib.request.HTTPRedirectHandler):
    """Manejador que no sigue redirecciones: llegan como HTTPError 3xx."""

    def redirect_request(self, req: urllib.request.Request, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        """Cancela la redirección automática."""
        return None


class ClienteDeRegistro:
    """Cliente del registro OCI que descarga por digest con reintento acotado."""

    def __init__(
        self,
        repositorio: str,
        *,
        abrir: Callable[[urllib.request.Request, float], Any] | None = None,
        abrir_sin_redireccion: Callable[[urllib.request.Request, float], Any] | None = None,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        """Prepara el cliente para un repositorio con punteros de descarga opcionales."""
        self.repositorio = repositorio
        self.abrir = abrir or (lambda peticion, timeout: urllib.request.urlopen(peticion, timeout=timeout))
        self.abrir_sin_redireccion = (
            abrir_sin_redireccion
            or (lambda peticion, timeout: urllib.request.build_opener(_SinRedireccion()).open(peticion, timeout=timeout))
        )
        self.dormir = dormir
        self.tokens_renovados: int = 0
        self.reintentos: list[str] = []
        self._token: str | None = None

    def _renovar_token(self) -> None:
        """Renueva el token anónimo del registro."""
        peticion = urllib.request.Request(URL_TOKEN.format(repositorio=self.repositorio))
        with self.abrir(peticion, TIMEOUT_TOKEN_S) as respuesta:
            datos = json.loads(respuesta.read().decode())
        self._token = datos.get("token") or datos.get("access_token")
        if not self._token:
            raise ErrorInterno("el registro no devolvió token")

    def descargar(self, ruta: str, digest: str, *, accept: str, timeout: float, destino: Path | None = None) -> bytes:
        """Descarga un digest del registro con reintento acotado SOLO de red."""
        if not ruta.endswith(digest):
            raise ErrorInterno("descarga sin digest")
        intentos = len(ESPERAS_ENTRE_DESCARGAS_S) + 1
        for intento in range(intentos):
            try:
                if not self._token:
                    self._renovar_token()
                peticion = urllib.request.Request(f"{REGISTRO}/v2/library/{self.repositorio}/{ruta}")
                peticion.add_header("Authorization", f"Bearer {self._token}")
                peticion.add_header("Accept", accept)
                try:
                    respuesta = self.abrir_sin_redireccion(peticion, timeout)
                except urllib.error.HTTPError as error:
                    if error.code in (301, 302, 303, 307, 308):
                        respuesta = self.abrir(urllib.request.Request(error.headers["Location"]), timeout)
                    elif error.code == 401:
                        self._token = None
                        self.tokens_renovados += 1
                        if intento < intentos - 1:
                            self.dormir(ESPERAS_ENTRE_DESCARGAS_S[intento])
                        continue
                    elif 500 <= error.code < 600:
                        self.reintentos.append(f"HTTPError {error.code}")
                        if intento < intentos - 1:
                            self.dormir(ESPERAS_ENTRE_DESCARGAS_S[intento])
                        continue
                    else:
                        raise FalloDeCertificacion(f"el registro respondió {error.code} para {digest}") from error
                with respuesta:
                    if destino:
                        parcial = destino.with_suffix(".parcial")
                        sha = hashlib.sha256()
                        with parcial.open("wb") as salida:
                            while bloque := respuesta.read(1024 * 1024):
                                sha.update(bloque)
                                salida.write(bloque)
                        if "sha256:" + sha.hexdigest() != digest:
                            parcial.unlink(missing_ok=True)
                            raise FalloDeCertificacion(f"sha256 distinto para {digest}")
                        parcial.replace(destino)
                        return b""
                    sha = hashlib.sha256()
                    cuerpo = bytearray()
                    while bloque := respuesta.read(1024 * 1024):
                        sha.update(bloque)
                        cuerpo.extend(bloque)
                    if "sha256:" + sha.hexdigest() != digest:
                        raise FalloDeCertificacion(f"sha256 distinto para {digest}")
                    return bytes(cuerpo)
            except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.IncompleteRead, OSError) as error:
                self.reintentos.append(type(error).__name__)
                if intento < intentos - 1:
                    self.dormir(ESPERAS_ENTRE_DESCARGAS_S[intento])
        raise EntornoInvalido(
            f"red: no se pudo descargar {digest} tras {intentos} intentos",
            {"reintentos": self.reintentos},
        )


def campos_de_control(texto: str) -> dict[str, str]:
    """Convierte la salida de dpkg-deb -f en un diccionario."""
    campos: dict[str, str] = {}
    for linea in texto.splitlines():
        if ":" not in linea:
            continue
        clave, valor = linea.split(":", 1)
        campos[clave.strip()] = valor.strip()
    return campos


def etapa_v6r(ctx: Contexto) -> dict[str, Any]:
    """Reconstruye el rootfs V6R desde la base certificada y requirements.lock."""
    base = leer_base_certificada()
    bi = base["base_image"]
    ca = base["ca_certificates"]
    if bi["platform"] != "linux/amd64":
        raise FalloDeCertificacion("plataforma no soportada por la base certificada")
    oci = ctx.espacio / "oci"
    oci.mkdir(exist_ok=True)
    rootfs = ctx.espacio / "rootfs"
    rootfs.mkdir(exist_ok=True)
    debs = ctx.espacio / "debs"
    debs.mkdir(exist_ok=True)
    cliente = ClienteDeRegistro("python")
    indice = json.loads(cliente.descargar(f"manifests/{bi['index_digest']}", bi["index_digest"], accept=ACEPTA_MANIFIESTOS, timeout=TIMEOUT_MANIFIESTO_S))
    if digest_de_plataforma(indice, bi["platform"]) != bi["platform_manifest_digest"]:
        raise FalloDeCertificacion("el digest de plataforma no coincide con la base certificada")
    manifiesto = json.loads(cliente.descargar(f"manifests/{bi['platform_manifest_digest']}", bi["platform_manifest_digest"], accept=ACEPTA_MANIFIESTOS, timeout=TIMEOUT_MANIFIESTO_S))
    if manifiesto.get("config", {}).get("digest") != bi["config_digest"]:
        raise FalloDeCertificacion("el digest de la config no coincide con la base certificada")
    config = json.loads(cliente.descargar(f"blobs/{bi['config_digest']}", bi["config_digest"], accept="*/*", timeout=TIMEOUT_BLOB_S))
    if f"PYTHON_VERSION={bi['cpython']}" not in config.get("config", {}).get("Env", []):
        raise FalloDeCertificacion("la config no declara el cpython certificado")
    digests = []
    for capa in manifiesto.get("layers", []):
        if capa.get("mediaType") not in TIPOS_DE_CAPA:
            raise FalloDeCertificacion("tipo de capa no soportado")
        cliente.descargar(f"blobs/{capa['digest']}", capa["digest"], accept="*/*", timeout=TIMEOUT_BLOB_S, destino=oci / capa["digest"].split(":")[1])
        aplicar_capa(oci / capa["digest"].split(":")[1], rootfs)
        digests.append(capa["digest"])
    apt_get = ctx.datos["herramientas"].get("apt-get")
    dpkg_deb = ctx.datos["herramientas"].get("dpkg-deb")
    if not apt_get:
        raise ErrorInterno("herramienta no resuelta en el preflight: apt-get")
    if not dpkg_deb:
        raise ErrorInterno("herramienta no resuelta en el preflight: dpkg-deb")
    resultado = ejecutar_sujeto(
        ctx, "30-apt-get-download",
        [apt_get, "download", f"libmagic1t64={VERSION_LIBMAGIC}", f"libmagic-mgc={VERSION_LIBMAGIC}", f"ca-certificates={ca['pinned_version']}"],
        cwd=debs, entorno=entorno_de_sujeto(os.environ), timeout_s=600.0, nombre="30-apt-get-download",
    )
    if resultado.rc != 0:
        raise FalloDeCertificacion("apt-get download no pudo obtener los .deb", {"salida": resultado.salida})
    ficheros = sorted(debs.glob("*.deb"))
    if len(ficheros) != 3:
        raise FalloDeCertificacion("no hay exactamente tres .deb descargados")
    debs_sha: dict[str, str] = {}
    paquetes_permitidos = {
        "libmagic1t64": VERSION_LIBMAGIC,
        "libmagic-mgc": VERSION_LIBMAGIC,
        "ca-certificates": ca["pinned_version"],
    }
    vistos = {nombre: 0 for nombre in paquetes_permitidos}
    deb_por_paquete: dict[str, Path] = {}
    for i, deb in enumerate(ficheros):
        resultado = ejecutar_sujeto(
            ctx, f"30-dpkg-campos-{i}",
            [dpkg_deb, "-f", str(deb), "Package", "Version"],
            cwd=ctx.espacio, entorno=entorno_de_sujeto(os.environ), timeout_s=60.0,
            nombre=f"30-dpkg-campos-{i}",
        )
        if resultado.rc != 0:
            raise FalloDeCertificacion("dpkg-deb falló", {"salida": resultado.salida})
        campos = campos_de_control(resultado.salida)
        paquete = campos.get("Package")
        if paquete not in paquetes_permitidos:
            raise FalloDeCertificacion("paquete .deb no esperado", {"paquete": paquete})
        vistos[paquete] += 1
        if vistos[paquete] > 1:
            raise FalloDeCertificacion("paquete .deb repetido", {"paquete": paquete})
        if campos.get("Version") != paquetes_permitidos[paquete]:
            raise FalloDeCertificacion("el .deb no coincide con la versión esperada")
        sha = sha256_de_fichero(deb)
        debs_sha[paquete] = sha
        deb_por_paquete[paquete] = deb
        if paquete == "ca-certificates" and sha != ca["deb_sha256"]:
            raise FalloDeCertificacion("el sha256 del .deb de CA no coincide con la base certificada")
        resultado = ejecutar_sujeto(
            ctx, f"30-dpkg-extraer-{paquete}",
            [dpkg_deb, "-x", str(deb), str(rootfs)],
            cwd=ctx.espacio, entorno=entorno_de_sujeto(os.environ), timeout_s=300.0,
            nombre=f"30-dpkg-extraer-{paquete}",
        )
        if resultado.rc != 0:
            raise FalloDeCertificacion("dpkg-deb falló", {"salida": resultado.salida})
    if any(conteo != 1 for conteo in vistos.values()):
        raise FalloDeCertificacion("no aparecen exactamente una vez los paquetes esperados")
    resultado = ejecutar_sujeto(
        ctx, "30-dpkg-contenido-ca-certificates",
        [dpkg_deb, "-c", str(deb_por_paquete["ca-certificates"])],
        cwd=ctx.espacio, entorno=entorno_de_sujeto(os.environ), timeout_s=60.0,
        nombre="30-dpkg-contenido-ca-certificates",
    )
    if resultado.rc != 0:
        raise FalloDeCertificacion("dpkg-deb falló", {"salida": resultado.salida})
    del_paquete = {linea.split()[-1].lstrip("./") for linea in resultado.salida.splitlines() if ".crt" in linea}
    presentes = [str(ruta.relative_to(rootfs)) for ruta in (rootfs / "usr" / "share" / "ca-certificates" / "mozilla").glob("*.crt")] if (rootfs / "usr" / "share" / "ca-certificates" / "mozilla").exists() else []
    retirados = crts_a_retirar(presentes, del_paquete)
    for relativa in retirados:
        _borrar(ruta_dentro(rootfs, relativa))
    total_ca = regenerar_bundle(rootfs)
    mgc = rootfs / MAGIC_MGC
    if mgc.is_symlink() or not mgc.is_file():
        raise FalloDeCertificacion("falta el magic.mgc de libmagic-mgc en el rootfs", {"ruta": MAGIC_MGC})
    if not (rootfs / LD_LINUX).exists() or not (rootfs / "usr" / "local" / "bin" / "python3.13").exists():
        raise FalloDeCertificacion("el rootfs no tiene el cargador o el cpython certificados")
    v6r = ctx.espacio / "v6r"
    bundle = rootfs / "etc" / "ssl" / "certs" / "ca-certificates.crt"
    python = escribir_entorno_virtual(v6r, rootfs, bundle, mgc, bi["cpython"])
    resultado = ejecutar_sujeto(ctx, "30-ensurepip", [str(python), "-m", "ensurepip"], cwd=ctx.espacio, entorno=entorno_de_sujeto(os.environ, ENTORNO_PIP), timeout_s=300.0, nombre="30-ensurepip")
    if resultado.rc != 0:
        raise FalloDeCertificacion("ensurepip falló", {"salida": resultado.salida})
    resultado = ejecutar_sujeto(ctx, "30-pip-install-runtime", [str(python), *ORDEN_PIP_INSTALL, str(LOCK_RUNTIME)], cwd=ctx.espacio, entorno=entorno_de_sujeto(os.environ, ENTORNO_PIP), timeout_s=1800.0, nombre="30-pip-install-runtime")
    if resultado.rc != 0:
        raise FalloDeCertificacion("la instalación del lock de runtime falló", {"salida": resultado.salida})
    ctx.datos["v6r"] = {"python": str(python), "venv": str(v6r), "rootfs": str(rootfs), "bundle": str(bundle), "mgc": str(mgc)}
    ctx.manifiesto["BASE_INDEX_DIGEST"] = bi["index_digest"]
    ctx.manifiesto["AMD64_MANIFEST_DIGEST"] = bi["platform_manifest_digest"]
    ctx.manifiesto["V6R_LOCK_HASH"] = "sha256:" + sha256_de_fichero(LOCK_RUNTIME)
    return {"capas": digests, "debs": debs_sha, "ca_certificados": total_ca, "ca_retirados": retirados, "tokens_renovados": cliente.tokens_renovados, "reintentos_de_descarga": cliente.reintentos}


def etapa_certificacion_v6r(ctx: Contexto) -> dict[str, Any]:
    """Certifica V6R con versiones, pip check, freeze y programa de humo."""
    v6r = ctx.datos.get("v6r")
    if not isinstance(v6r, Mapping):
        raise ErrorInterno("V6R no construido")
    python = Path(v6r["python"])
    cpython = leer_base_certificada()["base_image"]["cpython"]
    entorno = entorno_de_sujeto(os.environ, ENTORNO_PIP)
    resultado = ejecutar_sujeto(ctx, "40-version", [str(python), "-I", "-c", "import json, platform, ssl; print(json.dumps({'python': platform.python_version(), 'openssl': ssl.OPENSSL_VERSION, 'libc': platform.libc_ver()}))"], cwd=ctx.espacio, entorno=entorno, timeout_s=300.0, nombre="40-version")
    if resultado.rc != 0:
        raise FalloDeCertificacion("la sonda de versión de V6R falló", {"salida": resultado.salida})
    lineas = [linea for linea in resultado.salida.splitlines() if linea.strip()]
    if not lineas:
        raise FalloDeCertificacion("la sonda de versión de V6R no produjo salida")
    ultima = lineas[-1]
    try:
        versiones = json.loads(ultima)
    except json.JSONDecodeError as exc:
        raise FalloDeCertificacion("la versión de V6R no es JSON", {"linea": ultima}) from exc
    if versiones.get("python") != cpython:
        raise FalloDeCertificacion("la versión de Python de V6R no coincide con la certificada")
    ctx.manifiesto["V6R_PYTHON"] = versiones["python"]
    resultado = ejecutar_sujeto(ctx, "40-pip-check", [str(python), "-m", "pip", "check"], cwd=ctx.espacio, entorno=entorno, timeout_s=300.0, nombre="40-pip-check")
    if resultado.rc != 0:
        raise FalloDeCertificacion("pip check de V6R falló", {"salida": resultado.salida})
    resultado = ejecutar_sujeto(ctx, "40-pip-freeze", [str(python), "-m", "pip", "freeze"], cwd=ctx.espacio, entorno=entorno, timeout_s=300.0, nombre="40-pip-freeze")
    if resultado.rc != 0:
        raise FalloDeCertificacion("pip freeze de V6R falló", {"salida": resultado.salida})
    freeze = pines_de_freeze(resultado.salida)
    esperado = pines_de_lock(LOCK_RUNTIME.read_text())
    diferencias = diferencias_de_pines(esperado, freeze)
    if diferencias:
        raise FalloDeCertificacion("freeze de V6R distinto del lock de runtime", {"diferencias": diferencias})
    ctx.manifiesto["V6R_FREEZE_HASH"] = huella_de_pines(freeze)
    ctx.datos["freeze_v6r"] = freeze
    humo_ruta = ctx.espacio / "humo_v6r.py"
    humo_ruta.write_text(PROGRAMA_DE_HUMO)
    resultado = ejecutar_sujeto(
        ctx,
        "40-humo",
        [str(python), str(humo_ruta)],
        cwd=RAIZ / "resources" / "backend",
        entorno=entorno_de_sujeto(
            os.environ,
            {
                **ENTORNO_PIP,
                **ENTORNO_DE_HUMO,
                "KONTROL_SECRET_KEY": secrets.token_urlsafe(48),
                "KONTROL_CENTRAL_DB_URL": f"sqlite:///{ctx.espacio / 'central-humo.db'}",
                "PYTHONPATH": str(RAIZ / "resources" / "backend"),
            },
        ),
        timeout_s=600.0,
        nombre="40-humo",
    )
    if resultado.rc != 0:
        raise FalloDeCertificacion("humo de V6R fallido", {"humo": resultado.salida})
    lineas = [linea for linea in resultado.salida.splitlines() if linea.strip()]
    if not lineas:
        raise FalloDeCertificacion("humo de V6R sin salida")
    try:
        humo = json.loads(lineas[-1])
    except json.JSONDecodeError as exc:
        raise FalloDeCertificacion("humo de V6R sin JSON válido", {"humo": resultado.salida}) from exc
    if humo.get("resultado") != "PASS" or humo.get("herramientas_importables"):
        raise FalloDeCertificacion("humo de V6R fallido", {"humo": humo})
    ctx.datos["humo_v6r"] = humo
    return {"version": versiones["python"], "paquetes": len(freeze), "humo": humo}


def etapa_v6c(ctx: Contexto) -> dict[str, Any]:
    """Construye V6C como V6R más requirements-test.lock."""
    v6r = ctx.datos.get("v6r")
    if not isinstance(v6r, Mapping):
        raise ErrorInterno("V6R no construido")
    v6r_venv = Path(v6r["venv"])
    v6c = ctx.espacio / "v6c"
    v6c.mkdir(parents=True, exist_ok=True)
    for hijo in v6r_venv.iterdir():
        if hijo.name in ("bin", "pyvenv.cfg"):
            continue
        destino = v6c / hijo.name
        if hijo.is_dir():
            shutil.copytree(hijo, destino, symlinks=True)
        else:
            shutil.copy2(hijo, destino)
    python_c = escribir_entorno_virtual(v6c, Path(v6r["rootfs"]), Path(v6r["bundle"]), Path(v6r["mgc"]), leer_base_certificada()["base_image"]["cpython"])
    bin_v6r = v6r_venv / "bin"
    for fichero in bin_v6r.iterdir():
        if fichero.name in LANZADORES:
            continue
        destino = v6c / "bin" / fichero.name
        if fichero.is_symlink():
            shutil.copy2(fichero, destino, follow_symlinks=False)
        elif fichero.is_file():
            datos = fichero.read_bytes()
            python_r = str(bin_v6r / "python").encode()
            if python_r in datos:
                # Cubre el shebang `#!<ruta>` y el trampolín sh que pip usa con rutas largas.
                destino.write_bytes(datos.replace(python_r, str(python_c).encode()))
                destino.chmod(fichero.stat().st_mode)
            else:
                shutil.copy2(fichero, destino, follow_symlinks=False)
    entorno = entorno_de_sujeto(os.environ, ENTORNO_PIP)
    resultado = ejecutar_sujeto(ctx, "50-pip-install-certificacion", [str(python_c), *ORDEN_PIP_INSTALL, str(LOCK_CERTIFICACION)], cwd=ctx.espacio, entorno=entorno, timeout_s=1800.0, nombre="50-pip-install-certificacion")
    if resultado.rc != 0:
        raise FalloDeCertificacion("la instalación del lock de certificación falló", {"salida": resultado.salida})
    resultado = ejecutar_sujeto(ctx, "50-pip-check", [str(python_c), "-m", "pip", "check"], cwd=ctx.espacio, entorno=entorno, timeout_s=300.0, nombre="50-pip-check")
    if resultado.rc != 0:
        raise FalloDeCertificacion("pip check de V6C falló", {"salida": resultado.salida})
    resultado = ejecutar_sujeto(ctx, "50-pip-freeze", [str(python_c), "-m", "pip", "freeze"], cwd=ctx.espacio, entorno=entorno, timeout_s=300.0, nombre="50-pip-freeze")
    if resultado.rc != 0:
        raise FalloDeCertificacion("pip freeze de V6C falló", {"salida": resultado.salida})
    freeze = pines_de_freeze(resultado.salida)
    esperado = pines_de_lock(LOCK_CERTIFICACION.read_text())
    diferencias = diferencias_de_pines(esperado, freeze)
    if diferencias:
        raise FalloDeCertificacion("freeze de V6C distinto del lock de certificación", {"diferencias": diferencias})
    apuntan = []
    for fichero in (v6c / "bin").iterdir():
        if fichero.is_file() and str(v6r_venv).encode() in fichero.read_bytes():
            apuntan.append(str(fichero))
    if apuntan:
        raise FalloDeCertificacion("V6C apunta a V6R", {"ficheros": apuntan})
    ctx.datos["v6c"] = {"python": str(python_c), "venv": str(v6c)}
    ctx.datos["freeze_v6c"] = freeze
    ctx.manifiesto["V6C_LOCK_HASH"] = "sha256:" + sha256_de_fichero(LOCK_CERTIFICACION)
    return {"paquetes": len(freeze)}


def etapa_subconjunto(ctx: Contexto) -> dict[str, Any]:
    """Comprueba que el runtime de V6C es un subconjunto igual a V6R."""
    freeze_v6r = ctx.datos.get("freeze_v6r")
    freeze_v6c = ctx.datos.get("freeze_v6c")
    if not isinstance(freeze_v6r, Mapping) or not isinstance(freeze_v6c, Mapping):
        raise ErrorInterno("V6R o V6C no certificados")
    diferencias = diferencias_de_subconjunto(freeze_v6r, freeze_v6c)
    if diferencias:
        ctx.manifiesto["RUNTIME_SUBSET_EQUAL"] = 0
        raise FalloDeCertificacion("el subconjunto runtime de V6C difiere de V6R", {"diferencias": diferencias})
    ctx.manifiesto["RUNTIME_SUBSET_EQUAL"] = 1
    return {"runtime": len(freeze_v6r), "certificacion": len(freeze_v6c), "iguales": len(freeze_v6r)}


POSTGRES_QA = RAIZ / "qa" / "postgres_qa.json"
PGDATA_QA = Path("/tmp/kontrol-pgdata-045")
DIRECTORIO_POSTGRES_QA = "postgres-qa"
TIMEOUT_DESCARGA_POSTGRES_S = 300.0
PREFIJOS_DE_LA_RUEDA = ("pgserver/pginstall/", "pgserver.libs/")
MARCA_POSTGRES_COMPLETA = ".completo"


def _abrir_url(url: str, timeout_s: float) -> Any:
    """Abre una URL https fijada con cabecera de usuario del control de QA."""
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "kontrol-qa-certificacion"}), timeout=timeout_s)


def descargar_verificado(url: str, sha256: str, destino: Path, timeout_s: float) -> Path:
    """Descarga una fuente fijada por https y comprueba su suma sha256."""
    if not url.startswith("https://"):
        raise ErrorInterno("solo se descargan fuentes https", {"url": url})
    if destino.exists() and sha256_de_fichero(destino) == sha256:
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        destino.unlink()
    temporal = Path(tempfile.NamedTemporaryFile(dir=destino.parent, delete=False, prefix=".descarga-").name)
    hecho = False
    try:
        try:
            with _abrir_url(url, timeout_s) as respuesta:
                if not respuesta.geturl().startswith("https://"):
                    raise FalloDeCertificacion("la descarga se redirigió fuera de https")
                digesto = hashlib.sha256()
                with temporal.open("wb") as salida:
                    while True:
                        bloque = respuesta.read(1024 * 1024)
                        if not bloque:
                            break
                        salida.write(bloque)
                        digesto.update(bloque)
        except (urllib.error.URLError, OSError, http.client.HTTPException) as e:
            raise FalloDeCertificacion("no se pudo descargar la fuente fijada", {"url": url}) from e
        if digesto.hexdigest() != sha256:
            raise FalloDeCertificacion("sha256 de la descarga no coincide con el fijado", {"url": url})
        os.replace(temporal, destino)
        hecho = True
    finally:
        if not hecho and temporal.exists():
            temporal.unlink()
    return destino


def _record_de_la_rueda(rueda: zipfile.ZipFile) -> dict[str, str]:
    """Devuelve el contenido RECORD de la rueda limitado a los prefijos de PostgreSQL."""
    nombres = [n for n in rueda.namelist() if n.endswith(".dist-info/RECORD")]
    if not nombres:
        raise FalloDeCertificacion("la rueda no tiene RECORD")
    texto = rueda.read(nombres[0]).decode("utf-8")
    resultado: dict[str, str] = {}
    for fila in csv.reader(io.StringIO(texto)):
        if len(fila) < 2:
            continue
        ruta, firma = fila[0], fila[1]
        if not ruta.startswith(PREFIJOS_DE_LA_RUEDA) or not firma.startswith("sha256="):
            continue
        resultado[ruta] = firma[len("sha256="):]
    return resultado


def _sha256_urlsafe(contenido: bytes) -> str:
    """Calcula el sha256 urlsafe base64 sin relleno de un contenido binario."""
    return base64.urlsafe_b64encode(hashlib.sha256(contenido).digest()).rstrip(b"=").decode("ascii")


def extraer_postgres_de_la_rueda(rueda: Path, destino: Path) -> int:
    """Extrae de la rueda los miembros de PostgreSQL verificados contra su RECORD."""
    escritos = 0
    with zipfile.ZipFile(rueda) as archivo:
        registro = _record_de_la_rueda(archivo)
        destino_resuelto = destino.resolve()
        miembros = []
        for info in archivo.infolist():
            nombre = info.filename
            if not nombre.startswith(PREFIJOS_DE_LA_RUEDA) or info.is_dir():
                continue
            partes = PurePosixPath(nombre).parts
            if nombre.startswith("/") or ".." in partes:
                raise FalloDeCertificacion("miembro de la rueda fuera del destino", {"miembro": nombre})
            objetivo = (destino / nombre).resolve()
            if not objetivo.is_relative_to(destino_resuelto):
                raise FalloDeCertificacion("miembro de la rueda fuera del destino", {"miembro": nombre})
            miembros.append((info, objetivo))
        for info, objetivo in miembros:
            nombre = info.filename
            datos = archivo.read(info)
            if nombre not in registro or _sha256_urlsafe(datos) != registro[nombre]:
                raise FalloDeCertificacion("la rueda no coincide con su RECORD", {"miembro": nombre})
            objetivo.parent.mkdir(parents=True, exist_ok=True)
            objetivo.write_bytes(datos)
            modo = (info.external_attr >> 16) & 0o755
            if modo:
                os.chmod(objetivo, modo)
            escritos += 1
    return escritos


def verificar_contra_record(rueda: Path, destino: Path) -> list[str]:
    """Comprueba los ficheros extraídos de la rueda contra su RECORD."""
    fallos = []
    with zipfile.ZipFile(rueda) as archivo:
        registro = _record_de_la_rueda(archivo)
        for ruta, firma in registro.items():
            fichero = destino / ruta
            if not fichero.exists() or _sha256_urlsafe(fichero.read_bytes()) != firma:
                fallos.append(ruta)
    return sorted(fallos)


def _leer_miembro(archivo: tarfile.TarFile, miembro: tarfile.TarInfo) -> bytes:
    """Lee un miembro regular del tar; un miembro ilegible invalida el paquete."""
    flujo = archivo.extractfile(miembro)
    if flujo is None:
        raise FalloDeCertificacion("el paquete no contiene btree_gist")
    return flujo.read()


def ficheros_de_btree_gist(deb: Path) -> dict[str, bytes]:
    """Extrae btree_gist.so y sus extensiones SQL del paquete Debian de PostgreSQL."""
    contenido = deb.read_bytes()
    if not contenido.startswith(b"!<arch>\n"):
        raise FalloDeCertificacion("el paquete de btree_gist no es un archivo ar")
    datos_tar = None
    desplazamiento = 8
    while desplazamiento + 60 <= len(contenido):
        cabecera = contenido[desplazamiento:desplazamiento + 60]
        nombre = cabecera[0:16].strip().decode("ascii", "replace")
        if nombre.endswith("/"):
            nombre = nombre[:-1]
        tamano = int(cabecera[48:58].strip() or b"0")
        datos = contenido[desplazamiento + 60:desplazamiento + 60 + tamano]
        if nombre in ("data.tar.xz", "data.tar.gz"):
            datos_tar = datos
            break
        desplazamiento += 60 + tamano + (tamano % 2)
    if datos_tar is None:
        raise FalloDeCertificacion("el paquete no tiene data.tar")
    resultado: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(datos_tar), mode="r:*") as archivo:
        for miembro in archivo.getmembers():
            if not miembro.isfile():
                continue
            nombre = miembro.name
            base = nombre[2:] if nombre.startswith("./") else nombre
            if base == "usr/lib/postgresql/16/lib/btree_gist.so":
                resultado["lib/postgresql/btree_gist.so"] = _leer_miembro(archivo, miembro)
            elif base.startswith("usr/share/postgresql/16/extension/"):
                basename = base.rsplit("/", 1)[-1]
                if basename == "btree_gist.control" or basename.startswith("btree_gist--") and basename.endswith(".sql"):
                    resultado["share/postgresql/extension/" + basename] = _leer_miembro(archivo, miembro)
    if "lib/postgresql/btree_gist.so" not in resultado or "share/postgresql/extension/btree_gist.control" not in resultado:
        raise FalloDeCertificacion("el paquete no contiene btree_gist")
    return resultado


HERRAMIENTAS_DEL_ANFITRION = ("git", "apt-get", "dpkg-deb", "node", "uv", "bash", "timedatectl")
PG_PROVISION = RAIZ / "qa" / "pg-provision.sh"
PUERTO_PG_QA = 55432
BASE_DE_PRUEBAS = "ktest"
DOCKERFILE_BACKEND = RAIZ / "Dockerfile.backend"
REQUERIDOS = (BASE_CERTIFICADA, LOCK_RUNTIME, LOCK_CERTIFICACION, RAIZ / "resources" / "backend" / "requirements.txt", RAIZ / "resources" / "backend" / "requirements-test.txt", DOCKERFILE_BACKEND, RAIZ / "qa" / "e2e-run.py", RAIZ / "qa" / "e2e_corrida.py", RAIZ / "qa" / "suite_tiempos.py", RAIZ / "qa" / "clamav_qa.py", PG_PROVISION, REFERENCIA, POSTGRES_QA)
RUTAS_DE_MATERIAL_DE_LA_DUENA = ("requerimientos/",)
FROM_CERTIFICADO = re.compile(r"^FROM\s+([^\s:@]+):([^\s@]+)@(sha256:[0-9a-f]{64})\s+AS\s+base\s*$", re.MULTILINE)
ORDEN_LOCK_RUNTIME = "uv pip compile requirements.txt --python-version 3.13 --python-platform x86_64-unknown-linux-gnu --exclude-newer {corte} --upgrade -o requirements.lock"
ORDEN_LOCK_CERTIFICACION = "uv pip compile requirements-test.txt --constraint requirements.lock --python-version 3.13 --python-platform x86_64-unknown-linux-gnu --exclude-newer {corte} --upgrade -o requirements-test.lock"
CORTE = re.compile(r"--exclude-newer (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)")
PUERTOS_DE_LA_CORRIDA = (8000, 5173, 8010)
ESPACIO_MINIMO_HOME = 5 * 1024**3
ESPACIO_MINIMO_REPO = 2 * 1024**3
LOAD1_MAXIMO = 3.0
MEMORIA_MINIMA_KB = 5_000_000
PSWPIN_MAXIMO_POR_MIN = 2000
MUESTRAS_SANAS = 3
INTERVALO_SALUD_S = 60.0
TIMEOUT_GIT_S = 60.0
TIMEOUT_UV_S = 600.0
TIMEOUT_PG_S = 600.0
TIMEOUT_PSQL_S = 60.0


def clasificar_estado_git(salida: str) -> dict[str, Any]:
    """Clasifica las entradas de `git status --porcelain=v1 -z` en listas ordenadas."""
    entradas = salida.split("\0")
    modificados: list[str] = []
    no_versionados: list[str] = []
    material_de_la_duena: list[str] = []
    i = 0
    while i < len(entradas):
        entrada = entradas[i]
        if not entrada:
            i += 1
            continue
        estado = entrada[:2]
        ruta = entrada[3:]
        i += 1
        if "R" in estado or "C" in estado:
            # La entrada siguiente es la ruta de origen: se consume y el destino cuenta como modificado.
            i += 1
        if estado == "??" and ruta.startswith(RUTAS_DE_MATERIAL_DE_LA_DUENA):
            material_de_la_duena.append(ruta)
        elif estado == "??":
            no_versionados.append(ruta)
        else:
            modificados.append(ruta)
    return {
        "limpio": not modificados and not no_versionados and not material_de_la_duena,
        "modificados": sorted(modificados),
        "no_versionados": sorted(no_versionados),
        "material_de_la_duena": sorted(material_de_la_duena),
    }


#: Configuración git fija para que el árbol certificado sea el mismo en cualquier anfitrión.
CONFIGURACION_GIT_DEL_ARBOL = (
    "-c", "core.autocrlf=false", "-c", "core.filemode=true", "-c", "core.symlinks=true",
    "-c", "core.excludesFile=/dev/null", "-c", "core.attributesFile=/dev/null",
)


def arbol_certificado(ctx: Contexto, raiz: Path, trabajo: Path) -> dict[str, Any]:
    """Calcula el árbol Git del árbol de trabajo bajo una política de exclusiones explícita."""
    git = _herramienta(ctx, "git")
    trabajo.mkdir(parents=True, exist_ok=True)
    objetos_temporales = trabajo / "objetos"
    objetos_temporales.mkdir(parents=True, exist_ok=True)

    resultado_path = ejecutar_sujeto(
        ctx,
        "00",
        [git, *CONFIGURACION_GIT_DEL_ARBOL, "rev-parse", "--git-path", "objects"],
        cwd=raiz,
        entorno=entorno_de_sujeto(os.environ, {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"}),
        timeout_s=TIMEOUT_GIT_S,
        nombre=f"{trabajo.name}-git-path",
    )
    if resultado_path.rc != 0:
        raise FalloDePreflight("git no pudo calcular el árbol certificado", {"paso": f"{trabajo.name}-git-path"})
    objetos_repo = (raiz / resultado_path.salida.strip()).resolve()

    arboles: dict[str, str] = {}
    indices = {
        "certificado": ["add", "-A", "--", ".", *EXCLUSIONES_DEL_ARBOL],
        "total": ["add", "-A", "--", "."],
    }
    for tipo, comando_add in indices.items():
        indice = trabajo / f"indice-{tipo}"
        entorno = entorno_de_sujeto(
            os.environ,
            {
                "GIT_INDEX_FILE": str(indice),
                "GIT_OBJECT_DIRECTORY": str(objetos_temporales),
                "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(objetos_repo),
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": "/dev/null",
            },
        )
        pasos = {
            "read-tree": [git, *CONFIGURACION_GIT_DEL_ARBOL, "read-tree", "HEAD"],
            "add": [git, *CONFIGURACION_GIT_DEL_ARBOL, *comando_add],
            "write-tree": [git, *CONFIGURACION_GIT_DEL_ARBOL, "write-tree"],
        }
        for paso, argv in pasos.items():
            resultado = ejecutar_sujeto(
                ctx,
                "00",
                argv,
                cwd=raiz,
                entorno=entorno,
                timeout_s=TIMEOUT_GIT_S,
                nombre=f"{trabajo.name}-{tipo}-{paso}",
            )
            if resultado.rc != 0:
                raise FalloDePreflight(
                    "git no pudo calcular el árbol certificado",
                    {"paso": f"{trabajo.name}-{tipo}-{paso}"},
                )
            if paso == "write-tree":
                arbol = resultado.salida.strip()
                if not ARBOL_GIT.fullmatch(arbol):
                    raise FalloDePreflight(
                        "git no pudo calcular el árbol certificado",
                        {"paso": f"{trabajo.name}-{tipo}-{paso}"},
                    )
                arboles[tipo] = arbol

    entorno_total = entorno_de_sujeto(
        os.environ,
        {
            "GIT_INDEX_FILE": str(trabajo / "indice-total"),
            "GIT_OBJECT_DIRECTORY": str(objetos_temporales),
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(objetos_repo),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
        },
    )
    resultado_diff = ejecutar_sujeto(
        ctx,
        "00",
        [git, *CONFIGURACION_GIT_DEL_ARBOL, "diff-tree", "-r", "--name-only", "-z", arboles["certificado"], arboles["total"]],
        cwd=raiz,
        entorno=entorno_total,
        timeout_s=TIMEOUT_GIT_S,
        nombre=f"{trabajo.name}-diff-tree",
    )
    if resultado_diff.rc != 0:
        raise FalloDePreflight("git no pudo calcular el árbol certificado", {"paso": f"{trabajo.name}-diff-tree"})
    excluidos = sorted(p for p in resultado_diff.salida.split("\0") if p)

    return {"arbol": arboles["certificado"], "excluidos_con_cambios": excluidos}


def orden_de_cabecera(texto: str) -> str:
    """Extrae la orden de regeneración de la cabecera canónica de un lock."""
    lineas = texto.splitlines()
    if len(lineas) < 2 or not lineas[1].startswith("#    uv pip compile "):
        raise FalloDePreflight("cabecera de lock no canónica")
    return lineas[1][len("#    "):]


def corte_de_orden(orden: str) -> str:
    """Devuelve el único `--exclude-newer` presente en la orden."""
    cortes = CORTE.findall(orden)
    if len(cortes) != 1:
        raise FalloDePreflight("corte de lock no canónico")
    return cortes[0]


def orden_de_regeneracion(uv: str, orden: str, salida: Path) -> list[str]:
    """Construye el argv de regeneración sustituyendo el destino del `-o`."""
    partes = shlex.split(orden)
    if partes[:3] != ["uv", "pip", "compile"]:
        raise FalloDePreflight("orden de lock no canónica")
    if partes.count("-o") != 1:
        raise FalloDePreflight("orden de lock no canónica")
    indice_o = partes.index("-o")
    if indice_o + 1 >= len(partes):
        raise FalloDePreflight("orden de lock no canónica")
    partes[indice_o + 1] = str(salida)
    return [uv, *partes[1:], "--no-config", "--custom-compile-command", orden]


def leer_salud(proc: Path = Path("/proc")) -> dict[str, float]:
    """Lee las métricas de salud del anfitrión desde procfs."""
    load1 = float((proc / "loadavg").read_text().split()[0])
    meminfo = {}
    for linea in (proc / "meminfo").read_text().splitlines():
        clave, valor, *_ = linea.split()
        meminfo[clave.rstrip(":")] = float(valor)
    vmstat = {}
    for linea in (proc / "vmstat").read_text().splitlines():
        partes = linea.split()
        if len(partes) == 2:
            vmstat[partes[0]] = float(partes[1])
    return {
        "load1": load1,
        "mem_disponible_kb": meminfo["MemAvailable"],
        "pswpin": vmstat["pswpin"],
        "pswpout": vmstat["pswpout"],
        "swap_usada_kb": meminfo["SwapTotal"] - meminfo["SwapFree"],
    }


def muestra_sana(previa: Mapping[str, float], actual: Mapping[str, float], segundos: float) -> bool:
    """Indica si una muestra de salud cumple las condiciones acotadas."""
    if segundos <= 0:
        return False
    pswpin_por_min = (actual["pswpin"] - previa["pswpin"]) * 60.0 / segundos
    return (
        actual["load1"] < LOAD1_MAXIMO
        and actual["mem_disponible_kb"] > MEMORIA_MINIMA_KB
        and pswpin_por_min < PSWPIN_MAXIMO_POR_MIN
    )


def esperar_salud(espera_min: int, *, leer: Callable[[], dict[str, float]] = leer_salud, dormir: Callable[[float], None] = time.sleep, reloj: Callable[[], float] = time.monotonic) -> dict[str, Any]:
    """Espera muestras de salud consecutivas dentro de un límite acotado."""
    limite_s = max(espera_min * 60, MUESTRAS_SANAS * INTERVALO_SALUD_S)
    inicio = reloj()
    previa = leer()
    instante_previo = reloj()
    muestras: list[dict[str, Any]] = []
    seguidas = 0
    while reloj() - inicio < limite_s:
        dormir(INTERVALO_SALUD_S)
        actual = leer()
        ahora = reloj()
        segundos = ahora - instante_previo
        sana = muestra_sana(previa, actual, segundos)
        pswpin_por_min = (actual["pswpin"] - previa["pswpin"]) * 60.0 / segundos if segundos > 0 else 0.0
        muestras.append({
            "load1": actual["load1"],
            "mem_disponible_kb": actual["mem_disponible_kb"],
            "pswpin_por_min": pswpin_por_min,
            "sana": sana,
        })
        previa = actual
        instante_previo = ahora
        seguidas = seguidas + 1 if sana else 0
        if seguidas >= MUESTRAS_SANAS:
            return {"valido": True, "muestras": muestras, "espera_s": reloj() - inicio}
    return {"valido": False, "muestras": muestras, "espera_s": reloj() - inicio}


def puerto_ocupado(puerto: int) -> bool:
    """Indica si el puerto TCP local está ocupado."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", puerto)) == 0


def desvio_de_suspension() -> float:
    """Devuelve la diferencia entre BOOTTIME y MONOTONIC para detectar suspensiones."""
    return time.clock_gettime(time.CLOCK_BOOTTIME) - time.monotonic()


def _herramienta(ctx: Contexto, nombre: str) -> str:
    """Devuelve la ruta resuelta de una herramienta del preflight."""
    ruta = ctx.datos.get("herramientas", {}).get(nombre)
    if not ruta:
        raise ErrorInterno(f"herramienta no resuelta en el preflight: {nombre}")
    return ruta


def _psql(ctx: Contexto, base: str, sql: str, nombre: str) -> str:
    """Ejecuta una consulta en PostgreSQL de QA y devuelve la salida sin espacios."""
    argv = [_herramienta(ctx, "psql"), "-h", "localhost", "-p", str(PUERTO_PG_QA), "-U", "postgres", "-d", base, "-XAtq", "-v", "ON_ERROR_STOP=1", "-c", sql]
    resultado = ejecutar_sujeto(ctx, "70", argv, cwd=ctx.espacio, entorno=entorno_de_sujeto(os.environ, {"PGCONNECT_TIMEOUT": "10"}), timeout_s=TIMEOUT_PSQL_S, nombre=nombre)
    if resultado.rc != 0:
        raise EntornoInvalido(f"PostgreSQL de QA no responde: {nombre}")
    return resultado.salida.strip()


def _pg_provision(ctx: Contexto, *argumentos: str, nombre: str) -> int:
    """Ejecuta pg-provision.sh con el PostgreSQL de QA fijado y sin compilar nada."""
    argv = [_herramienta(ctx, "bash"), str(PG_PROVISION), *argumentos]
    resultado = ejecutar_sujeto(
        ctx,
        "70",
        argv,
        cwd=RAIZ,
        entorno=entorno_de_sujeto(
            os.environ,
            {
                "KONTROL_PGPORT": str(PUERTO_PG_QA),
                "KONTROL_PGBIN": ctx.datos["postgres_qa"]["bin"],
                "KONTROL_PGDATA": str(PGDATA_QA),
                "KONTROL_PG_SIN_COMPILAR": "1",
            },
        ),
        timeout_s=TIMEOUT_PG_S,
        nombre=nombre,
    )
    return resultado.rc


def aprovisionar_postgres_qa(ctx: Contexto) -> dict[str, Any]:
    """Descarga, verifica e instala la versión fijada de PostgreSQL de QA."""
    contenido = POSTGRES_QA.read_bytes()
    pin = json.loads(contenido)
    id_ = hashlib.sha256(contenido).hexdigest()[:16]
    base = ctx.home / DIRECTORIO_POSTGRES_QA
    descargas = base / "descargas"
    rueda = descargar_verificado(
        pin["rueda"]["url"],
        pin["rueda"]["sha256"],
        descargas / pin["rueda"]["fichero"],
        TIMEOUT_DESCARGA_POSTGRES_S,
    )
    deb = descargar_verificado(
        pin["btree_gist"]["url"],
        pin["btree_gist"]["sha256"],
        descargas / pin["btree_gist"]["fichero"],
        TIMEOUT_DESCARGA_POSTGRES_S,
    )
    btree = ficheros_de_btree_gist(deb)
    instalacion = base / id_
    pginstall = instalacion / "pgserver" / "pginstall"
    if (instalacion / MARCA_POSTGRES_COMPLETA).exists():
        discrepancias = verificar_contra_record(rueda, instalacion) + sorted(
            clave
            for clave, datos in btree.items()
            if not (pginstall / clave).is_file() or (pginstall / clave).read_bytes() != datos
        )
        if discrepancias:
            raise EntornoInvalido(
                "la instalación fijada de PostgreSQL de QA está alterada",
                {"discrepancias": discrepancias},
            )
        reutilizada = True
    else:
        if instalacion.exists():
            if instalacion.is_symlink() or instalacion.parent != base:
                raise EntornoInvalido("la instalación de PostgreSQL de QA está en una ruta inesperada")
            shutil.rmtree(instalacion)
        instalacion.mkdir(parents=True)
        extraer_postgres_de_la_rueda(rueda, instalacion)
        for clave, datos in btree.items():
            destino = pginstall / clave
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(datos)
        (instalacion / MARCA_POSTGRES_COMPLETA).write_text(
            json.dumps(
                {
                    "postgres": pin["postgres"],
                    "rueda_sha256": pin["rueda"]["sha256"],
                    "btree_gist_sha256": pin["btree_gist"]["sha256"],
                },
                indent=2,
            )
        )
        reutilizada = False
    resultado = {
        "bin": str(pginstall / "bin"),
        "id": id_,
        "postgres": pin["postgres"],
        "rueda_sha256": pin["rueda"]["sha256"],
        "btree_gist_sha256": pin["btree_gist"]["sha256"],
        "reutilizada": reutilizada,
    }
    ctx.datos["postgres_qa"] = resultado
    ctx.datos.setdefault("herramientas", {})["psql"] = str(pginstall / "bin" / "psql")
    ctx.manifiesto["POSTGRES_QA_SOURCE"] = {
        "postgres": pin["postgres"],
        "rueda_sha256": pin["rueda"]["sha256"],
        "btree_gist_sha256": pin["btree_gist"]["sha256"],
        "id": id_,
        "reutilizada": reutilizada,
        "verificada": 1,
        "venv_preexistente_requerido": 0,
    }
    return resultado


def ejecutable_del_postmaster(pgdata: Path) -> Path | None:
    """Devuelve la ruta resuelta del binario ejecutado por el postmaster."""
    try:
        primera_linea = (pgdata / "postmaster.pid").read_text().splitlines()[0]
        pid = int(primera_linea)
    except (OSError, ValueError, IndexError):
        return None
    exe = Path(f"/proc/{pid}/exe")
    return exe.resolve() if exe.exists() else None


def etapa_preflight(ctx: Contexto) -> dict[str, Any]:
    """Comprueba herramientas, ficheros, git, base Docker, locks, disco, reloj y puertos."""
    ctx.manifiesto["ENVIRONMENT_POLICY"] = comprobar_politica_de_entorno(os.environ)
    herramientas: dict[str, str] = {}
    faltan: list[str] = []
    for nombre in HERRAMIENTAS_DEL_ANFITRION:
        ruta = shutil.which(nombre)
        if ruta:
            herramientas[nombre] = ruta
        else:
            faltan.append(nombre)
    if faltan:
        raise FalloDePreflight("faltan herramientas", {"faltan": faltan})
    ctx.datos["herramientas"] = herramientas

    faltan_ficheros = [str(ruta.relative_to(RAIZ)) for ruta in REQUERIDOS if not ruta.exists()]
    if faltan_ficheros:
        raise FalloDePreflight("faltan ficheros requeridos", {"faltan": faltan_ficheros})

    resultado_head = ejecutar_sujeto(ctx, "00", [_herramienta(ctx, "git"), "rev-parse", "HEAD"], cwd=RAIZ, entorno=entorno_de_sujeto(os.environ), timeout_s=TIMEOUT_GIT_S, nombre="00-git-head")
    head = resultado_head.salida.strip()
    if resultado_head.rc != 0 or not re.fullmatch(r"[0-9a-f]{40}", head):
        raise FalloDePreflight("git rev-parse HEAD no devolvió un hash válido")
    resultado_status = ejecutar_sujeto(ctx, "00", [_herramienta(ctx, "git"), "status", "--porcelain=v1", "-z", "--untracked-files=all"], cwd=RAIZ, entorno=entorno_de_sujeto(os.environ), timeout_s=TIMEOUT_GIT_S, nombre="00-git-status")
    if resultado_status.rc != 0:
        raise FalloDePreflight("git status no pudo ejecutarse")
    dirty_state = clasificar_estado_git(resultado_status.salida)
    arbol = arbol_certificado(ctx, RAIZ, ctx.espacio / "arbol-preflight")

    base_certificada = leer_base_certificada()
    dockerfile = DOCKERFILE_BACKEND.read_text()
    coincidencias = FROM_CERTIFICADO.findall(dockerfile)
    if len(coincidencias) != 1:
        raise FalloDePreflight("el FROM de Dockerfile.backend no es la base certificada", {"coincidencias": len(coincidencias)})
    repositorio, etiqueta, digest = coincidencias[0]
    if (repositorio, etiqueta, digest) != (base_certificada["base_image"]["repository"], base_certificada["base_image"]["tag"], base_certificada["base_image"]["index_digest"]):
        raise FalloDePreflight("el FROM de Dockerfile.backend no es la base certificada", {"FROM": f"{repositorio}:{etiqueta}@{digest}"})

    orden_runtime = orden_de_cabecera(LOCK_RUNTIME.read_text())
    orden_cert = orden_de_cabecera(LOCK_CERTIFICACION.read_text())
    corte_runtime = corte_de_orden(orden_runtime)
    corte_cert = corte_de_orden(orden_cert)
    if corte_runtime != corte_cert:
        raise FalloDePreflight("los locks no comparten el mismo corte")
    if orden_runtime != ORDEN_LOCK_RUNTIME.format(corte=corte_runtime) or orden_cert != ORDEN_LOCK_CERTIFICACION.format(corte=corte_cert):
        raise FalloDePreflight("orden de lock no canónica")
    ctx.datos["ordenes_de_lock"] = {"requirements.lock": orden_runtime, "requirements-test.lock": orden_cert}
    ctx.datos["corte"] = corte_runtime

    uso_home = shutil.disk_usage(ctx.home)
    uso_repo = shutil.disk_usage(RAIZ)
    if uso_home.free < ESPACIO_MINIMO_HOME or uso_repo.free < ESPACIO_MINIMO_REPO:
        raise EntornoInvalido("espacio en disco insuficiente", {"home_free": uso_home.free, "repo_free": uso_repo.free})

    resultado_ntp = ejecutar_sujeto(ctx, "00", [_herramienta(ctx, "timedatectl"), "show", "-p", "NTPSynchronized", "--value"], cwd=RAIZ, entorno=entorno_de_sujeto(os.environ), timeout_s=TIMEOUT_GIT_S, nombre="00-ntp")
    if resultado_ntp.rc != 0 or resultado_ntp.salida.strip() != "yes":
        raise EntornoInvalido("el reloj no está sincronizado por NTP")

    puertos_ocupados = [puerto for puerto in PUERTOS_DE_LA_CORRIDA if puerto_ocupado(puerto)]
    if puertos_ocupados:
        raise EntornoInvalido("puertos de la corrida ocupados", {"puertos": puertos_ocupados})

    ctx.manifiesto["GIT_HEAD"] = head
    ctx.manifiesto["DIRTY_STATE"] = dirty_state
    ctx.manifiesto["CERTIFICATION_INPUT_TREE_HASH"] = arbol["arbol"]
    ctx.manifiesto["ARBOL_POLITICA"] = {
        "version": POLITICA_DEL_ARBOL_VERSION,
        "exclusiones": list(EXCLUSIONES_DEL_ARBOL),
        "excluidos_con_cambios": arbol["excluidos_con_cambios"],
    }
    return {
        "herramientas": sorted(herramientas),
        "arbol": arbol["arbol"],
        "head": head,
        "limpio": dirty_state["limpio"],
        "corte": corte_runtime,
        "espacios_previos_incompletos": len(ctx.manifiesto["ESPACIOS_PREVIOS_INCOMPLETOS"]),
    }


def etapa_validez(ctx: Contexto) -> dict[str, Any]:
    """Evalúa la condición de salud del anfitrión durante el límite acotado."""
    resultado = esperar_salud(ctx.opciones.espera_salud_min)
    ctx.datos["salud_base"] = leer_salud()
    ctx.datos["suspension_base_s"] = desvio_de_suspension()
    if not resultado["valido"]:
        ctx.manifiesto["ENVIRONMENT_VALIDITY"] = "INVALID"
        raise EntornoInvalido("el anfitrión no alcanzó la condición de salud", resultado)
    ctx.manifiesto["ENVIRONMENT_VALIDITY"] = "VALID"
    return resultado


def etapa_dependencias(ctx: Contexto) -> dict[str, Any]:
    """Regenera los locks con uv y exige igualdad byte a byte con los versionados."""
    locks_identicos: list[str] = []
    carpeta_locks = ctx.espacio / "locks"
    carpeta_locks.mkdir(parents=True, exist_ok=True)
    for nombre, lock in (("requirements.lock", LOCK_RUNTIME), ("requirements-test.lock", LOCK_CERTIFICACION)):
        salida = carpeta_locks / nombre
        argv = orden_de_regeneracion(_herramienta(ctx, "uv"), ctx.datos["ordenes_de_lock"][nombre], salida)
        resultado = ejecutar_sujeto(ctx, "20", argv, cwd=RAIZ / "resources" / "backend", entorno=entorno_de_sujeto(os.environ), timeout_s=TIMEOUT_UV_S, nombre=f"20-uv-{nombre}")
        if resultado.rc != 0:
            raise FalloDeCertificacion("uv no pudo regenerar el lock", {"lock": nombre})
        if salida.read_bytes() != lock.read_bytes():
            diff = list(difflib.unified_diff(lock.read_text().splitlines(), salida.read_text().splitlines(), fromfile=str(lock), tofile=str(salida)))[:40]
            raise FalloDeCertificacion("el lock regenerado difiere del versionado", {"lock": nombre, "diff": diff})
        locks_identicos.append(nombre)
    return {"locks_identicos": locks_identicos}


def etapa_postgres(ctx: Contexto) -> dict[str, Any]:
    """Prepara y valida el PostgreSQL de QA y la base de pruebas ktest."""
    aprovisionar_postgres_qa(ctx)
    rc = _pg_provision(ctx, "status", nombre="70-pg-status")
    if rc != 0:
        rc = _pg_provision(ctx, "start", nombre="70-pg-start")
        if rc != 0:
            raise EntornoInvalido("el PostgreSQL de QA no arranca")

    postmaster = ejecutable_del_postmaster(PGDATA_QA)
    bin_fijado = Path(ctx.datos["postgres_qa"]["bin"]).resolve()
    if postmaster is None or bin_fijado not in postmaster.parents:
        raise EntornoInvalido(
            "el PostgreSQL de QA en marcha no es el binario fijado: detenlo con bash qa/pg-provision.sh stop y relanza",
            {"postmaster": str(postmaster) if postmaster else None},
        )

    version = _psql(ctx, "postgres", "SHOW server_version", "70-version")
    puerto = _psql(ctx, "postgres", "SHOW port", "70-puerto")
    if puerto != str(PUERTO_PG_QA):
        raise EntornoInvalido(f"PostgreSQL de QA escucha en el puerto {puerto}, no en {PUERTO_PG_QA}")
    if version != ctx.datos["postgres_qa"]["postgres"]:
        raise EntornoInvalido(
            "PostgreSQL de QA no tiene la versión fijada",
            {"version": version, "fijada": ctx.datos["postgres_qa"]["postgres"]},
        )
    ctx.manifiesto["POSTGRES_VERSION"] = version

    ktest_creada = False
    conteo = _psql(ctx, "postgres", "SELECT count(*) FROM pg_database WHERE datname = 'ktest'", "70-ktest")
    if conteo == "0":
        rc = _pg_provision(ctx, "mkdb", BASE_DE_PRUEBAS, nombre="70-pg-mkdb-ktest")
        if rc != 0:
            raise EntornoInvalido("no se pudo crear la base ktest")
        ktest_creada = True
        conteo = _psql(ctx, "postgres", "SELECT count(*) FROM pg_database WHERE datname = 'ktest'", "70-ktest-tras-crear")
        if conteo != "1":
            raise EntornoInvalido("la base ktest no existe tras crearla")

    btree = _psql(ctx, "postgres", "SELECT count(*) FROM pg_available_extensions WHERE name = 'btree_gist'", "70-btree-gist")
    if btree != "1":
        raise EntornoInvalido("btree_gist no está disponible en PostgreSQL de QA")

    bases_previas = _psql(ctx, "postgres", "SELECT count(*) FROM pg_database WHERE datname LIKE 'kontrol\\_e2e\\_test\\_%'", "70-bases-previas")
    if bases_previas != "0":
        raise EntornoInvalido("quedan bases de corrida E2E previas: qa/e2e-bases.py listar")

    esquemas_previos = _psql(ctx, "ktest", "SELECT count(*) FROM pg_namespace WHERE nspname LIKE 't\\_%'", "70-esquemas-previos")
    if esquemas_previos != "0":
        raise EntornoInvalido("quedan esquemas t_ en ktest")

    return {"version": version, "ktest_creada": ktest_creada, "btree_gist": True}


CORRIDAS_BACKEND = RAIZ / "qa" / "backend-runs"
SUITE_TIEMPOS = RAIZ / "qa" / "suite_tiempos.py"
MOTORES_BACKEND = (("sqlite", "SQLITE_RESULT"), ("postgres", "POSTGRES_RESULT"))
RUN_DE_SUITE = re.compile(r"^\[suite (\S+)\]", re.MULTILINE)
TIMEOUT_SUITE_S = 7200.0
TIMEOUT_OPENAPI_S = 300.0
TIMEOUT_AUDITORIA_S = 900.0
TIMEOUT_INSTALAR_AUDITORIA_S = 600.0
FUENTES_DE_AUDITORIA = (("pypi", "PIP_AUDIT_PYPI"), ("osv", "PIP_AUDIT_OSV"))
PROGRAMA_DE_OPENAPI = '''import hashlib
import json
import platform

from app.main import create_app

spec = create_app().openapi()
rutas = len(spec["paths"])
operaciones = 0
protegidas = 0
publicas = 0
seguridad_global = spec.get("security", [])
for ruta in spec["paths"].values():
    for metodo in ("get", "post", "put", "patch", "delete"):
        operacion = ruta.get(metodo)
        if operacion is None:
            continue
        operaciones += 1
        seguridad = operacion.get("security", seguridad_global)
        if any("BearerAccessToken" in esquema for esquema in seguridad for esquema in esquema):
            protegidas += 1
        else:
            publicas += 1
huella_paths = "sha256:" + hashlib.sha256(json.dumps(spec["paths"], sort_keys=True).encode()).hexdigest()
version_openapi = spec["openapi"]
python = platform.python_version()
print(json.dumps({
    "version_openapi": version_openapi,
    "rutas": rutas,
    "operaciones": operaciones,
    "protegidas": protegidas,
    "publicas": publicas,
    "huella_paths": huella_paths,
    "python": python,
}))
'''


def leer_referencia() -> dict[str, Any]:
    """Lee y valida la referencia versionada de certificación."""
    try:
        referencia = json.loads(REFERENCIA.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ErrorInterno("referencia versionada incompleta") from exc
    if referencia.get("esquema") != 1:
        raise ErrorInterno("referencia versionada incompleta")
    openapi = referencia.get("openapi")
    if not isinstance(openapi, dict) or set(openapi) != {
        "version_openapi",
        "rutas",
        "operaciones",
        "protegidas",
        "publicas",
        "huella_paths",
    }:
        raise ErrorInterno("referencia versionada incompleta")
    pip_audit = referencia.get("pip_audit")
    if not isinstance(pip_audit, str) or re.fullmatch(r"pip-audit==\d+(\.\d+)*", pip_audit) is None:
        raise ErrorInterno("referencia versionada incompleta")
    return referencia


def run_id_de_suite(salida: str) -> str:
    """Extrae la última identificación de ejecución de la suite."""
    coincidencias = RUN_DE_SUITE.findall(salida)
    if not coincidencias:
        raise FalloDeCertificacion("la suite no informó su run_id")
    return coincidencias[-1]


def resultado_de_suite(manifiesto: Mapping[str, Any], rc: int) -> dict[str, Any]:
    """Valida el manifiesto de la suite y devuelve su resumen."""
    duracion = manifiesto["duracion"]
    pytest = manifiesto["pytest"]
    analizador = manifiesto["analizador"]
    detalle = {
        "run_id": manifiesto.get("run_id"),
        "pytest": pytest,
        "duracion": duracion,
        "analizador": analizador,
    }
    if duracion.get("salto"):
        raise EntornoInvalido("salto de reloj durante la suite backend", detalle)
    if (
        rc != 0
        or pytest.get("rc") != rc
        or not pytest.get("completo")
        or pytest.get("failed") != 0
        or pytest.get("errors") != 0
        or not pytest.get("passed")
        or not analizador.get("habilitado")
    ):
        raise FalloDeCertificacion("suite backend fallida", detalle)
    return {
        "passed": pytest["passed"],
        "failed": pytest["failed"],
        "skipped": pytest["skipped"],
        "errors": pytest["errors"],
        "rc": pytest["rc"],
        "run_id": manifiesto["run_id"],
        "segundos": duracion["monotonica_s"],
        "modo": "IN_PROCESS_CERTIFICATION_OVERLAY",
    }


def firma_comparable(firma: Mapping[str, Any]) -> dict[str, Any]:
    """Reduce una firma OpenAPI a las claves de la referencia."""
    claves = ("version_openapi", "rutas", "operaciones", "protegidas", "publicas", "huella_paths")
    return {clave: firma[clave] for clave in claves}


def hallazgos_de_auditoria(informe: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    """Extrae hallazgos y dependencias omitidas de un informe de pip-audit."""
    dependencias = informe.get("dependencies")
    if not dependencias:
        raise FalloDeCertificacion("pip-audit no auditó ninguna dependencia")
    hallazgos = []
    omitidas = []
    for dependencia in dependencias:
        if "skip_reason" in dependencia:
            omitidas.append(f"{dependencia['name']}: {dependencia['skip_reason']}")
        else:
            for vulnerabilidad in dependencia.get("vulns", []):
                hallazgos.append(f"{dependencia['name']}=={dependencia['version']}: {vulnerabilidad['id']}")
    return sorted(hallazgos), sorted(omitidas)


def _entorno_de_producto(ctx: Contexto) -> dict[str, str]:
    """Construye el entorno de ejecución del producto certificado."""
    return entorno_de_sujeto(
        os.environ,
        {
            **ENTORNO_PIP,
            **ENTORNO_DE_HUMO,
            "KONTROL_SECRET_KEY": secrets.token_urlsafe(48),
            "KONTROL_CENTRAL_DB_URL": f"sqlite:///{ctx.espacio / 'central-humo.db'}",
            "PYTHONPATH": str(RAIZ / "resources" / "backend"),
        },
    )


def etapa_backend(ctx: Contexto) -> dict[str, Any]:
    """Ejecuta la suite de tiempos con SQLite y PostgreSQL en V6C."""
    try:
        py_c = Path(ctx.datos["v6c"]["python"])
    except (KeyError, TypeError) as exc:
        raise ErrorInterno("V6R/V6C no construidos") from exc
    resultados: dict[str, Any] = {}
    for motor, campo in MOTORES_BACKEND:
        sujeto = ejecutar_sujeto(
            ctx,
            "80",
            [str(py_c), str(SUITE_TIEMPOS), "--motor", motor, "--con-analizador"],
            cwd=RAIZ,
            entorno=entorno_de_sujeto(os.environ),
            timeout_s=TIMEOUT_SUITE_S,
            nombre=f"80-suite-{motor}",
        )
        run_id = run_id_de_suite(sujeto.salida)
        try:
            manifiesto = json.loads((CORRIDAS_BACKEND / run_id / "manifest.json").read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise FalloDeCertificacion("la suite no dejó manifiesto") from exc
        resultado = resultado_de_suite(manifiesto, sujeto.rc)
        ctx.manifiesto[campo] = resultado
        resultados[motor] = resultado
    return resultados


def etapa_openapi(ctx: Contexto) -> dict[str, Any]:
    """Compara la OpenAPI de V6R y V6C con la referencia versionada."""
    referencia = leer_referencia()["openapi"]
    programa = ctx.espacio / "openapi_firma.py"
    programa.write_text(PROGRAMA_DE_OPENAPI)
    firmas: dict[str, dict[str, Any]] = {}
    for nombre, clave in (("v6r", "V6R"), ("v6c", "V6C")):
        try:
            interprete = ctx.datos[nombre]["python"]
        except (KeyError, TypeError) as exc:
            raise ErrorInterno("V6R/V6C no construidos") from exc
        sujeto = ejecutar_sujeto(
            ctx,
            "100",
            [interprete, str(programa)],
            cwd=RAIZ / "resources" / "backend",
            entorno=_entorno_de_producto(ctx),
            timeout_s=TIMEOUT_OPENAPI_S,
            nombre=f"100-openapi-{nombre}",
        )
        lineas = [linea for linea in sujeto.salida.splitlines() if linea.strip()]
        if sujeto.rc != 0 or not lineas:
            raise FalloDeCertificacion("no se pudo obtener la OpenAPI", {"interprete": clave})
        try:
            firma = json.loads(lineas[-1])
        except json.JSONDecodeError as exc:
            raise FalloDeCertificacion("no se pudo obtener la OpenAPI", {"interprete": clave}) from exc
        firmas[clave] = firma
    comparable_v6r = firma_comparable(firmas["V6R"])
    comparable_v6c = firma_comparable(firmas["V6C"])
    if comparable_v6r != comparable_v6c or comparable_v6r != referencia:
        resultado = {
            "deriva": 1,
            "V6R": comparable_v6r,
            "V6C": comparable_v6c,
            "referencia": referencia,
        }
        ctx.manifiesto["OPENAPI_RESULT"] = resultado
        raise FalloDeCertificacion("deriva del contrato OpenAPI", resultado)
    resultado = {**comparable_v6r, "deriva": 0, "interpretes": ["V6R", "V6C"]}
    ctx.manifiesto["OPENAPI_RESULT"] = resultado
    return resultado


def etapa_seguridad(ctx: Contexto) -> dict[str, Any]:
    """Audita las dependencias bloqueadas con pip-audit fijado en PyPI y OSV."""
    try:
        py_c = Path(ctx.datos["v6c"]["python"])
    except (KeyError, TypeError) as exc:
        raise ErrorInterno("V6R/V6C no construidos") from exc
    objetivo = ctx.espacio / "pip-audit"
    requisito = leer_referencia()["pip_audit"]
    instalacion = ejecutar_sujeto(
        ctx,
        "110",
        [str(py_c), "-m", "pip", "install", "--no-cache-dir", "--target", str(objetivo), requisito],
        cwd=ctx.espacio,
        entorno=entorno_de_sujeto(os.environ, ENTORNO_PIP),
        timeout_s=TIMEOUT_INSTALAR_AUDITORIA_S,
        nombre="110-pip-audit-instalar",
    )
    if instalacion.rc != 0:
        raise FalloDeCertificacion("no se pudo instalar pip-audit fijado")
    hallazgos_por_fuente: dict[str, list[str]] = {}
    omitidas_por_fuente: dict[str, list[str]] = {}
    totales: dict[str, dict[str, int]] = {}
    for fuente, campo in FUENTES_DE_AUDITORIA:
        hallazgos_por_fuente[fuente] = []
        omitidas_por_fuente[fuente] = []
        totales[fuente] = {}
        for nombre_lock, lock in (("requirements.lock", LOCK_RUNTIME), ("requirements-test.lock", LOCK_CERTIFICACION)):
            informe = ctx.espacio / f"auditoria-{fuente}-{nombre_lock}.json"
            sujeto = ejecutar_sujeto(
                ctx,
                "110",
                [str(py_c), "-m", "pip_audit", "-r", str(lock), "--no-deps", "--disable-pip", "-s", fuente, "-f", "json", "-o", str(informe)],
                cwd=ctx.espacio,
                entorno=entorno_de_sujeto(os.environ, {**ENTORNO_PIP, "PYTHONPATH": str(objetivo)}),
                timeout_s=TIMEOUT_AUDITORIA_S,
                nombre=f"110-pip-audit-{fuente}-{nombre_lock}",
            )
            try:
                datos = json.loads(informe.read_text())
            except (OSError, json.JSONDecodeError) as exc:
                raise FalloDeCertificacion("pip-audit falló", {"fuente": fuente, "lock": nombre_lock, "rc": sujeto.rc}) from exc
            if sujeto.rc not in (0, 1):
                raise FalloDeCertificacion("pip-audit falló", {"fuente": fuente, "lock": nombre_lock, "rc": sujeto.rc})
            hallazgos, omitidas = hallazgos_de_auditoria(datos)
            if sujeto.rc == 1 and not hallazgos:
                raise FalloDeCertificacion("pip-audit incoherente")
            hallazgos_por_fuente[fuente].extend(hallazgos)
            omitidas_por_fuente[fuente].extend(omitidas)
            totales[fuente][nombre_lock] = len(hallazgos)
        total_hallazgos = len(hallazgos_por_fuente[fuente])
        ctx.manifiesto[campo] = total_hallazgos
    todos_hallazgos = [hallazgo for fuente, _ in FUENTES_DE_AUDITORIA for hallazgo in hallazgos_por_fuente[fuente]]
    todas_omitidas = [omitida for fuente, _ in FUENTES_DE_AUDITORIA for omitida in omitidas_por_fuente[fuente]]
    if todos_hallazgos or todas_omitidas:
        raise FalloDeCertificacion(
            "pip-audit con hallazgos o dependencias sin auditar",
            {"hallazgos": todos_hallazgos, "omitidas": todas_omitidas},
        )
    return {"pip_audit": requisito, "pypi": totales["pypi"], "osv": totales["osv"]}


E2E_RUN = RAIZ / "qa" / "e2e-run.py"
CORRIDAS_E2E = RAIZ / "qa" / "e2e-runs"
RUN_DE_E2E = re.compile(r"^\[e2e (\S+)\]", re.MULTILINE)
TIMEOUT_E2E_S = 3600.0
#: Número canónico de workers de Playwright para la E2E de certificación de release.
E2E_WORKERS_CANONICOS = 6
#: Número canónico de reintentos de Playwright para la E2E de certificación de release.
E2E_REINTENTOS_CANONICOS = 0
#: Patrón para extraer el número de workers informado por Playwright en el log de la suite.
PERFIL_DE_LA_SUITE = re.compile(r"^Running \d+ tests? using (\d+) workers?", re.MULTILINE)
MARCAS_DE_PRODUCTO = ("app.main:app", "central_authority.main:app")
#: El tick del planificador lo lanza el ayudante E2E `planificador.ts` con el intérprete de la certificación (V6C).
MARCAS_DE_AYUDANTES = ("rol_sin_permiso.py", "alcance_de_usuario.py", "licencia_firmada.py", "autoridad_central.py", "app.modules.scheduler")
INTERVALO_DE_MUESTREO_S = 0.02
PSWPOUT_MAXIMO_E2E = 200_000
SWAP_ANADIDA_MAXIMA_KB = 1_048_576
SUSPENSION_MAXIMA_S = 5.0
V0_PYTHON = RAIZ / "resources" / "backend" / ".venv" / "bin" / "python"
CLAVES_SIN_EJECUTAR = ("failed", "skipped", "flaky", "did not run")


def sanear_como_e2e(texto: str, entorno: Mapping[str, str]) -> str:
    """Sanea un texto con las mismas raíces que usa la E2E."""
    raices = [(str(RAIZ), "<repo>"), (tempfile.gettempdir(), "<tmp>")]
    home = entorno.get("HOME", "")
    if home:
        raices.append((home, "<home>"))
    for raiz, etiqueta in sorted(raices, key=lambda par: len(par[0]), reverse=True):
        texto = texto.replace(raiz, etiqueta)
    return texto


def argv0_declarado(argumentos: Sequence[str]) -> str | None:
    """Devuelve el elemento siguiente al primer --argv0 de la línea de órdenes."""
    for indice, argumento in enumerate(argumentos):
        if argumento == "--argv0" and indice + 1 < len(argumentos):
            return argumentos[indice + 1]
    return None


def marca_de(linea: str) -> tuple[str, str] | None:
    """Clasifica una línea de órdenes como producto o ayudante según sus marcas."""
    for marca in MARCAS_DE_PRODUCTO:
        if marca in linea:
            return ("producto", marca)
    for marca in MARCAS_DE_AYUDANTES:
        if marca in linea:
            return ("ayudante", marca)
    return None


def clasificar_procedencia(registros: Sequence[Mapping[str, Any]], python_v6r: str, python_v6c: str) -> dict[str, Any]:
    """Resume la procedencia observada y detecta interpretes fuera de lugar."""
    por_marca: dict[str, int] = {}
    fuera_de_lugar: list[str] = []
    producto = 0
    ayudantes = 0
    backend_visto = False
    autoridad_vista = False
    for registro in registros:
        tipo = registro["tipo"]
        marca = registro["marca"]
        argv0 = registro["argv0"]
        python_mapeado = registro["python_mapeado"]
        por_marca[marca] = por_marca.get(marca, 0) + 1
        if tipo == "producto":
            producto += 1
            backend_visto = backend_visto or marca == "app.main:app"
            autoridad_vista = autoridad_vista or marca == "central_authority.main:app"
        else:
            ayudantes += 1
        if (tipo == "producto" and argv0 != python_v6r) or (tipo == "ayudante" and argv0 != python_v6c) or python_mapeado != ["3.13"]:
            fuera_de_lugar.append(f"{tipo} {marca}: argv0={argv0} python={python_mapeado}")
    return {
        "producto": producto,
        "ayudantes": ayudantes,
        "por_marca": por_marca,
        "fuera_de_lugar": fuera_de_lugar,
        "backend_visto": backend_visto,
        "autoridad_vista": autoridad_vista,
    }


def degradacion_del_anfitrion(antes: Mapping[str, float], despues: Mapping[str, float], suspension_s: float) -> dict[str, Any]:
    """Mide incrementos de swap y suspensión durante una corrida."""
    paginas = despues["pswpout"] - antes["pswpout"]
    swap_kb = despues["swap_usada_kb"] - antes["swap_usada_kb"]
    return {
        "pswpout_paginas": paginas,
        "swap_anadida_kb": swap_kb,
        "suspension_s": suspension_s,
        "degradado": paginas > PSWPOUT_MAXIMO_E2E or swap_kb > SWAP_ANADIDA_MAXIMA_KB or suspension_s > SUSPENSION_MAXIMA_S,
    }


def resultado_de_e2e(manifiesto: Mapping[str, Any], rc: int, python_v6r_saneado: str) -> dict[str, Any]:
    """Valida el manifiesto de la E2E y devuelve su resumen."""
    try:
        codigo_de_salida = manifiesto["codigo_de_salida"]
        suite = manifiesto["suite"]
        codigo_suite = suite["codigo"]
        resumen = suite.get("resumen", {})
        interpretes = manifiesto["interpretes"]
        paridad = interpretes["paridad"]
        interprete = manifiesto["interprete_de_producto"]
        limpieza = manifiesto["limpieza"]
        protegidas = manifiesto["protegidas_sin_cambios"]
    except (KeyError, TypeError):
        raise FalloDeCertificacion("manifiesto E2E incompleto") from None
    motivos: list[str] = []
    if rc != 0:
        motivos.append(f"rc={rc}")
    if codigo_de_salida != rc:
        motivos.append(f"codigo_de_salida={codigo_de_salida} != rc={rc}")
    if codigo_suite != 0:
        motivos.append(f"suite.codigo={codigo_suite}")
    if resumen.get("passed", 0) <= 0:
        motivos.append("sin pruebas superadas")
    for clave in CLAVES_SIN_EJECUTAR:
        if resumen.get(clave, 0) > 0:
            motivos.append(f"{clave}={resumen[clave]}")
    if paridad != 1:
        motivos.append(f"interpretes.paridad={paridad}")
    if interprete.get("modo") != "RUNTIME_SEPARADO":
        motivos.append(f"modo={interprete.get('modo')}")
    if interprete.get("herramientas_de_prueba") != []:
        motivos.append("herramientas_de_prueba no vacías")
    if interprete.get("paridad_runtime") != 1:
        motivos.append(f"paridad_runtime={interprete.get('paridad_runtime')}")
    if interprete.get("ejecutable") != python_v6r_saneado:
        motivos.append("ejecutable distinto del producto")
    if interprete.get("autoridad") != python_v6r_saneado:
        motivos.append("autoridad distinta del producto")
    if limpieza.get("resultado") != "LIMPIA":
        motivos.append("limpieza no limpia")
    if protegidas is not True:
        motivos.append("protegidas_sin_cambios no verdadero")
    if motivos:
        raise FalloDeCertificacion("E2E fallida", {"motivos": motivos, "manifiesto": manifiesto})
    return {
        "passed": resumen.get("passed", 0),
        "failed": 0,
        "skipped": 0,
        "flaky": 0,
        "no_ejecutadas": 0,
        "run_id": manifiesto.get("run_id"),
        "segundos": suite.get("segundos"),
    }


class MuestreadorDeProcedencia(threading.Thread):
    """Muestrea una sola vez los procesos con marcas leyendo /proc."""

    def __init__(self, proc: Path = Path("/proc"), intervalo_s: float = INTERVALO_DE_MUESTREO_S) -> None:
        super().__init__(daemon=True)
        self.proc = proc
        self.intervalo_s = intervalo_s
        self.registros: list[dict[str, Any]] = []
        self._vistos: set[int] = set()
        self._parar = threading.Event()

    def run(self) -> None:
        while not self._parar.is_set():
            try:
                entradas = list(self.proc.iterdir())
            except FileNotFoundError:
                entradas = []
            for entrada in entradas:
                if not entrada.name.isdigit():
                    continue
                pid = int(entrada.name)
                if pid in self._vistos:
                    continue
                try:
                    cmdline = (entrada / "cmdline").read_bytes().split(b"\0")
                    argumentos = [parte.decode(errors="replace") for parte in cmdline if parte]
                    marca = marca_de(" ".join(argumentos))
                    if marca is None:
                        # Sin marca todavía: puede ser un fork que aún no ha hecho exec del lanzador.
                        continue
                    maps = (entrada / "maps").read_text(errors="replace")
                    exe = os.path.realpath(entrada / "exe")
                    python_mapeado = sorted({f"3.{m}" for m in re.findall(r"python3\.(\d+)", maps + exe)})
                    if not python_mapeado:
                        continue
                    self._vistos.add(pid)
                    self.registros.append(
                        {
                            "pid": pid,
                            "tipo": marca[0],
                            "marca": marca[1],
                            "argv0": argv0_declarado(argumentos),
                            "python_mapeado": python_mapeado,
                        }
                    )
                except (FileNotFoundError, ProcessLookupError, PermissionError):
                    continue
            self._parar.wait(self.intervalo_s)

    def detener(self) -> None:
        """Detiene el muestreo y espera a que termine el hilo."""
        self._parar.set()
        self.join(timeout=5)


def orden_de_e2e(py_c: str, py_r: str) -> list[str]:
    """Orden canónica de la E2E: perfil fijo (6 workers, 0 reintentos) sea cual sea el anfitrión o `CI`."""
    return [py_c, str(E2E_RUN), "--con-analizador", "--python-de-producto", py_r, "--",
            f"--workers={E2E_WORKERS_CANONICOS}", f"--retries={E2E_REINTENTOS_CANONICOS}"]


def verificar_perfil_e2e(texto: str) -> dict[str, int]:
    """Verifica que la suite E2E informó y usó el perfil canónico de workers y reintentos."""
    encontrado = PERFIL_DE_LA_SUITE.search(texto)
    if encontrado is None:
        raise FalloDeCertificacion("la E2E no informó su número de workers")
    workers = int(encontrado.group(1))
    if workers != E2E_WORKERS_CANONICOS:
        raise FalloDeCertificacion("la E2E no usó el perfil canónico de workers",
                                  {"workers": workers, "esperados": E2E_WORKERS_CANONICOS})
    return {"workers": workers, "retries": E2E_REINTENTOS_CANONICOS}


def etapa_e2e(ctx: Contexto) -> dict[str, Any]:
    """Ejecuta la E2E completa y valida procedencia y salud del anfitrión."""
    try:
        py_r = ctx.datos["v6r"]["python"]
        py_c = ctx.datos["v6c"]["python"]
    except KeyError:
        raise ErrorInterno("V6R/V6C no construidos") from None
    antes = leer_salud()
    muestreador = MuestreadorDeProcedencia()
    muestreador.start()
    try:
        sujeto = ejecutar_sujeto(
            ctx,
            "90",
            orden_de_e2e(py_c, py_r),
            cwd=RAIZ,
            entorno=entorno_de_sujeto(os.environ),
            timeout_s=TIMEOUT_E2E_S,
            nombre="90-e2e",
        )
    finally:
        muestreador.detener()
    despues = leer_salud()
    base_suspension = ctx.datos.get("suspension_base_s", desvio_de_suspension())
    suspension = desvio_de_suspension() - base_suspension
    degradacion = degradacion_del_anfitrion(antes, despues, suspension)
    with (ctx.evidencia / "procedencia.jsonl").open("w", encoding="utf-8") as flujo:
        for registro in muestreador.registros:
            flujo.write(sanear(json.dumps(registro, ensure_ascii=False), ctx.raices) + "\n")
    if degradacion["degradado"]:
        ctx.manifiesto["ENVIRONMENT_VALIDITY"] = "INVALID"
        raise EntornoInvalido("el anfitrión se degradó durante la E2E", degradacion)
    run_ids = RUN_DE_E2E.findall(sujeto.salida)
    if not run_ids:
        raise FalloDeCertificacion("la E2E no informó su run_id")
    run_id = run_ids[-1]
    manifiesto_ruta = CORRIDAS_E2E / run_id / "manifest.json"
    try:
        manifiesto = json.loads(manifiesto_ruta.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        raise FalloDeCertificacion("la E2E no dejó manifiesto") from None
    ctx.manifiesto["ALEMBIC_PARITY"] = 1 if manifiesto.get("interpretes", {}).get("paridad") == 1 else 0
    suite_ruta = CORRIDAS_E2E / run_id / "suite.log"
    try:
        suite_texto = suite_ruta.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        raise FalloDeCertificacion("la E2E no dejó suite.log") from None
    perfil = verificar_perfil_e2e(suite_texto)
    ctx.manifiesto["CANONICAL_E2E_WORKERS"] = perfil["workers"]
    ctx.manifiesto["CANONICAL_E2E_RETRIES"] = perfil["retries"]
    resultado = resultado_de_e2e(manifiesto, sujeto.rc, sanear_como_e2e(py_r, os.environ))
    procedencia = clasificar_procedencia(muestreador.registros, py_r, py_c)
    ctx.manifiesto["E2E_AUTHORITY_PARITY"] = (
        1
        if procedencia["autoridad_vista"]
        and procedencia["backend_visto"]
        and not [f for f in procedencia["fuera_de_lugar"] if f.startswith("producto")]
        else 0
    )
    ctx.manifiesto["E2E_HELPER_PARITY"] = (
        1 if procedencia["ayudantes"] > 0 and not [f for f in procedencia["fuera_de_lugar"] if f.startswith("ayudante")] else 0
    )
    if ctx.manifiesto["E2E_AUTHORITY_PARITY"] == 0 or ctx.manifiesto["E2E_HELPER_PARITY"] == 0 or procedencia["fuera_de_lugar"]:
        raise FalloDeCertificacion("procedencia de intérpretes incorrecta en la E2E", {"procedencia": procedencia})
    ctx.manifiesto["E2E_RESULT"] = resultado
    return {"resultado": resultado, "procedencia": procedencia, "degradacion": degradacion, "perfil": perfil}


def etapa_v0_historico(ctx: Contexto) -> dict[str, Any]:
    """Ejecuta el control histórico V0 sin afectar nunca al veredicto."""
    estado: dict[str, Any] = {"modo": "HISTORICAL_CONTROL", "afecta_veredicto": False}
    if not V0_PYTHON.exists() or not os.access(V0_PYTHON, os.X_OK):
        estado["estado"] = "NO_DISPONIBLE"
        ctx.manifiesto["V0_STATUS"] = estado
        return estado
    for nombre, argv in (
        ("sqlite", [str(V0_PYTHON), str(SUITE_TIEMPOS), "--motor", "sqlite", "--con-analizador"]),
        ("e2e", [str(V0_PYTHON), str(E2E_RUN), "--con-analizador"]),
    ):
        timeout = TIMEOUT_SUITE_S if nombre == "sqlite" else TIMEOUT_E2E_S
        try:
            resultado = ejecutar_sujeto(
                ctx,
                "95",
                argv,
                cwd=RAIZ,
                entorno=entorno_de_sujeto(os.environ),
                timeout_s=timeout,
                nombre=f"95-v0-{nombre}",
            )
            estado[nombre] = {"rc": resultado.rc, "estado": "PASS" if resultado.rc == 0 else "FAIL"}
        except FalloDeEtapa as e:
            estado[nombre] = {"estado": "ERROR", "motivo": e.motivo}
    ctx.manifiesto["V0_STATUS"] = estado
    return estado


ETAPA_V0 = Etapa(95, "V0_HISTORICAL_CONTROL", etapa_v0_historico)


def etapa_residuos(ctx: Contexto) -> dict[str, Any]:
    """Audita residuos: procesos vivos y estado del espacio."""
    restos = terminar_vivos(ctx)
    externos: dict[str, Any] = {"puertos_ocupados": [p for p in PUERTOS_DE_LA_CORRIDA if puerto_ocupado(p)]}
    if "psql" in ctx.datos.get("herramientas", {}):
        externos["bases_de_corrida"] = int(_psql(ctx, "postgres", "SELECT count(*) FROM pg_database WHERE datname LIKE 'kontrol\\_e2e\\_test\\_%'", "120-bases-de-corrida"))
        externos["esquemas_t"] = int(_psql(ctx, "ktest", "SELECT count(*) FROM pg_namespace WHERE nspname LIKE 't\\_%'", "120-esquemas-t"))
    else:
        externos["bases"] = "NO_VERIFICABLE: el preflight no resolvió psql y la corrida no llegó a crear bases"
    if ctx.opciones.conservar_espacio:
        marcar_espacio(ctx.espacio, "CONSERVADA")
        espacio: dict[str, Any] = {"eliminado": False, "motivo": "--conservar-espacio"}
    else:
        marcar_espacio(ctx.espacio, "COMPLETA")
        espacio = eliminar_espacio(ctx.espacio, ctx.home, ctx.run_id)
    sucio = (
        bool(restos)
        or (not ctx.opciones.conservar_espacio and not espacio.get("eliminado"))
        or bool(externos["puertos_ocupados"])
        or externos.get("bases_de_corrida", 0) != 0
        or externos.get("esquemas_t", 0) != 0
    )
    if sucio:
        ctx.manifiesto["RESIDUE_STATUS"] = "DIRTY"
        raise FalloDeCertificacion("quedan residuos de la corrida", {"restos": restos, "espacio": espacio, "externos": externos})
    if ctx.opciones.conservar_espacio:
        ctx.manifiesto["RESIDUE_STATUS"] = "CONSERVED_BY_OPTION"
    else:
        ctx.manifiesto["RESIDUE_STATUS"] = "CLEAN"
    return {"procesos_terminados": restos, "espacio": espacio, "externos": externos}


def etapa_manifiesto(ctx: Contexto) -> dict[str, Any]:
    """Completa el hash canónico de insumos y valida el manifiesto."""
    try:
        base = json.loads(BASE_CERTIFICADA.read_text())
    except (OSError, KeyError, json.JSONDecodeError):
        raise ErrorInterno("falta la base certificada specs/001-fundacion/certified-deployment-base.json") from None
    if not REFERENCIA.exists():
        raise ErrorInterno("falta la referencia versionada qa/certificacion_referencia.json")
    arbol = ctx.manifiesto.get("CERTIFICATION_INPUT_TREE_HASH")
    if ctx.manifiesto["GIT_HEAD"] == "NOT_RUN" or arbol in (None, "NOT_RUN"):
        entrada = None
        ctx.manifiesto["TREE_HASH_BOUND_TO_RUN_INPUT"] = 0
    else:
        recalculado = arbol_certificado(ctx, RAIZ, ctx.espacio / "arbol-cierre")["arbol"]
        if recalculado != arbol:
            ctx.manifiesto["CANONICAL_RUN_INPUT_HASH"] = None
            ctx.manifiesto["TREE_HASH_BOUND_TO_RUN_INPUT"] = 0
            raise FalloDeCertificacion(
                "el árbol certificado cambió durante la corrida",
                {"preflight": arbol, "cierre": recalculado},
            )
        digests = {
            "index": base["base_image"]["index_digest"],
            "amd64": base["base_image"]["platform_manifest_digest"],
            "config": base["base_image"]["config_digest"],
        }
        locks = {
            "requirements.lock": sha256_de_fichero(LOCK_RUNTIME),
            "requirements-test.lock": sha256_de_fichero(LOCK_CERTIFICACION),
        }
        entrada = hash_de_entrada(
            head=ctx.manifiesto["GIT_HEAD"],
            arbol=arbol,
            digests=digests,
            locks=locks,
            plataforma=base["base_image"]["platform"],
            referencia=sha256_de_fichero(REFERENCIA),
            postgres_qa=sha256_de_fichero(POSTGRES_QA),
        )
        ctx.manifiesto["CANONICAL_RUN_INPUT_HASH_VERSION"] = VERSION_HASH_DE_ENTRADA
        ctx.manifiesto["TREE_HASH_BOUND_TO_RUN_INPUT"] = 1
    ctx.manifiesto["CANONICAL_RUN_INPUT_HASH"] = entrada
    if not ctx.fallo_previo and not ctx.opciones.solo_preflight:
        campos = [
            campo
            for campo in CAMPOS_DEL_MANIFIESTO
            if campo not in CAMPOS_DE_CIERRE and ctx.manifiesto[campo] == "NOT_RUN"
        ]
        if campos:
            raise ErrorInterno("campos del manifiesto sin valor", {"campos": campos})
    return {"CANONICAL_RUN_INPUT_HASH": entrada}


def etapa_veredicto(ctx: Contexto) -> dict[str, Any]:
    """Fija el veredicto final y cierra el manifiesto."""
    if ctx.datos.get("interrumpida"):
        veredicto = VEREDICTO_INTERRUMPIDA
        rc = RC_INTERNO
    elif ctx.rc == RC_ENTORNO_INVALIDO:
        veredicto = VEREDICTO_ENTORNO
        rc = ctx.rc
    elif ctx.rc == RC_FALLO_CERTIFICACION:
        veredicto = VEREDICTO_FALLO
        rc = ctx.rc
    elif ctx.rc == RC_INTERNO:
        veredicto = VEREDICTO_INTERNO
        rc = ctx.rc
    elif ctx.rc == RC_PASS and ctx.opciones.solo_preflight:
        veredicto = VEREDICTO_DIAGNOSTICO
        rc = RC_SOLO_DIAGNOSTICO
    elif ctx.rc == RC_PASS:
        veredicto = VEREDICTO_PASS
        rc = RC_PASS
    else:
        veredicto = VEREDICTO_INTERNO
        rc = RC_INTERNO
    ctx.manifiesto["FINAL_VERDICT"] = veredicto
    ctx.manifiesto["RC"] = rc
    ctx.manifiesto["FINISHED_AT"] = ahora_utc()
    ctx.manifiesto["duracion_s"] = round(time.monotonic() - ctx.inicio_monotonico, 1)
    ctx.rc = rc
    return {"FINAL_VERDICT": veredicto, "RC": rc, "FINISHED_AT": ctx.manifiesto["FINISHED_AT"]}


ETAPAS: tuple[Etapa, ...] = (
    Etapa(0, "PREFLIGHT", etapa_preflight),
    Etapa(10, "ENVIRONMENT_VALIDITY", etapa_validez),
    Etapa(20, "DEPENDENCY_INTEGRITY", etapa_dependencias),
    Etapa(30, "V6R_RECONSTRUCTION", etapa_v6r),
    Etapa(40, "V6R_CERTIFICATION", etapa_certificacion_v6r),
    Etapa(50, "V6C_CONSTRUCTION", etapa_v6c),
    Etapa(60, "RUNTIME_SUBSET_EQUALITY", etapa_subconjunto),
    Etapa(70, "POSTGRES_QA_READINESS", etapa_postgres),
    Etapa(80, "BACKEND_CERTIFICATION", etapa_backend),
    Etapa(90, "E2E_CERTIFICATION", etapa_e2e),
    Etapa(100, "OPENAPI", etapa_openapi),
    Etapa(110, "SECURITY", etapa_seguridad),
    Etapa(120, "RESIDUE_AUDIT", etapa_residuos, de_cierre=True),
    Etapa(130, "EVIDENCE_MANIFEST", etapa_manifiesto, de_cierre=True),
    Etapa(140, "FINAL_VERDICT", etapa_veredicto, de_cierre=True),
)


def etapas_de_la_corrida(opciones: argparse.Namespace) -> tuple[Etapa, ...]:
    """Devuelve las etapas que aplican según las opciones."""
    if opciones.solo_preflight:
        return tuple(etapa for etapa in ETAPAS if etapa.codigo in (0, 120, 130, 140))
    etapas = list(ETAPAS)
    if opciones.incluir_v0_historico:
        for indice, etapa in enumerate(etapas):
            if etapa.codigo == 90:
                etapas.insert(indice + 1, ETAPA_V0)
                break
    return tuple(etapas)


def _entero_no_negativo(texto: str) -> int:
    """Convierte un argumento a entero no negativo."""
    try:
        valor = int(texto)
    except ValueError:
        raise argparse.ArgumentTypeError("debe ser un entero") from None
    if valor < 0:
        raise argparse.ArgumentTypeError("debe ser mayor o igual que 0")
    return valor


def construir_parser() -> argparse.ArgumentParser:
    """Construye el parser de argumentos CLI."""
    parser = argparse.ArgumentParser(description="Orden canónica de certificación de release de KONTROL.")
    parser.add_argument(
        "--incluir-v0-historico",
        action="store_true",
        help="control histórico V0, marcado HISTORICAL_CONTROL, nunca cambia el veredicto",
    )
    parser.add_argument(
        "--espera-salud-min",
        type=_entero_no_negativo,
        default=ESPERA_SALUD_MIN_POR_DEFECTO,
        help="espera mínima de salud en minutos (por defecto 30)",
    )
    parser.add_argument("--conservar-espacio", action="store_true", help="no elimina el espacio de corrida")
    parser.add_argument(
        "--solo-preflight",
        action="store_true",
        help="diagnóstico, no certifica, nunca RC 0",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada del orquestador de certificación."""
    argv = sys.argv[1:] if argv is None else argv
    opciones = construir_parser().parse_args(argv)

    anteriores = (
        signal.signal(signal.SIGINT, _al_recibir_senal),
        signal.signal(signal.SIGTERM, _al_recibir_senal),
    )

    ctx: Contexto | None = None
    espacio_creado: Path | None = None
    fd: int | None = None
    try:
        try:
            home = home_de_certificacion()
            fd = tomar_cerrojo(home)
        except FalloDePreflight as e:
            raices = raices_a_sanear(os.environ, Path(HOME_POR_DEFECTO).expanduser())
            print(sanear(e.motivo, raices), file=sys.stderr)
            return RC_INTERNO

        try:
            previos = espacios_previos(home)
            run_id = nuevo_run_id()
            espacio = crear_espacio(home, run_id)
            espacio_creado = espacio
            evidencia = EVIDENCIA / run_id
            evidencia.mkdir(parents=True)

            raices = raices_a_sanear(os.environ, home)
            ctx = Contexto(
                run_id=run_id,
                opciones=opciones,
                home=home,
                espacio=espacio,
                evidencia=evidencia,
                raices=raices,
                manifiesto=manifiesto_inicial(run_id, opciones, argv, previos),
            )
            escribir_manifiesto(ctx)
            rc = ejecutar_etapas(ctx, etapas_de_la_corrida(opciones))
            print(
                f"{ctx.manifiesto['FINAL_VERDICT']} rc={rc} "
                f"manifiesto={sanear(str(evidencia / 'manifest.json'), raices)}"
            )
            return rc
        except FalloDeEtapa as e:
            print(sanear(e.motivo, raices_a_sanear(os.environ, home)), file=sys.stderr)
            return RC_INTERNO
        except OSError as e:
            print(sanear(f"OSError: {e}", raices_a_sanear(os.environ, home)), file=sys.stderr)
            return RC_INTERNO
        except Interrumpida as e:
            print(f"interrumpida: {e}", file=sys.stderr)
            return RC_INTERNO
    finally:
        if ctx is not None:
            terminar_vivos(ctx)
            if not opciones.conservar_espacio:
                eliminar_espacio(ctx.espacio, ctx.home, ctx.run_id)
        elif espacio_creado is not None:
            eliminar_espacio(espacio_creado, home, espacio_creado.name)
        if fd is not None:
            os.close(fd)
        signal.signal(signal.SIGINT, anteriores[0])
        signal.signal(signal.SIGTERM, anteriores[1])
