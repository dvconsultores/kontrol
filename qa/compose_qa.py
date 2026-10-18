"""Certificación reproducible de la composición Docker para OBS-09 (Spec 046).

Construye las imágenes del repositorio, levanta una composición aislada con base
PostgreSQL efímera, clamd y backend, ejecuta el contrato funcional F01-F04 a
través del backend, inspecciona los contenedores, mide la versión/firmas/límites
runtime de clamd, limpia todos los recursos propios y emite el bloque de
evidencia ``OBS09_EXTERNAL_DOCKER_EVIDENCE`` saneado.

Uso desde la raíz del repositorio::

    python qa/compose_qa.py [--puerto 18000] [--carpeta qa/compose-runs]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import socket
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[1]
COMPOSE = RAIZ / "compose.yaml"
OVERRIDE = RAIZ / "qa" / "compose.obs09.yaml"
CORRIDAS = RAIZ / "qa" / "compose-runs"
REGISTRO = "kontrol-obs09"
MAXIMO_DOCUMENTAL = 50 * 1024 * 1024
PDF_LIMPIO = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n%%EOF\n"
EICAR = "X5O!P%@AP[4\\PZX54(P^)7CC)7}$" + "EICAR-STANDARD-ANTIVIRUS-TEST-FILE" + "!$H+H*"
PLAZO_CLAMD_S = 420.0
PLAZO_BACKEND_S = 300.0
PLAZO_DB_S = 120.0

SECCIONES_EVIDENCIA: list[str] = [
    "REPOSITORY",
    "DOCKER",
    "BUILD",
    "COMPOSE",
    "CLAMD",
    "FUNCTIONAL",
    "SCANNER",
    "SIZE",
    "SECURITY",
    "CLEANUP",
]

CLAVES_EVIDENCIA: dict[str, list[str]] = {
    "REPOSITORY": ["HEAD", "BRANCH", "WORKTREE"],
    "DOCKER": ["DOCKER_VERSION", "COMPOSE_VERSION", "DOCKER_SERVER_REACHABLE"],
    "BUILD": [
        "BACKEND_IMAGE_BUILD_TIME",
        "CLAMD_IMAGE_BUILD_TIME",
        "BACKEND_IMAGE_SIZE",
        "CLAMD_IMAGE_SIZE",
        "BACKEND_IMAGE_HAS_CLAMSCAN",
        "BACKEND_IMAGE_HAS_SIGNATURE_DATABASE",
        "CLAMD_BINARY_PRESENT",
        "CLAMD_CONFIG_PRESENT",
    ],
    "COMPOSE": [
        "CLAMD_HEALTHY_AFTER_S",
        "BACKEND_READY_AFTER_S",
        "CLAMD_SERVICE_PRESENT",
        "CLAMD_INTERNAL_ONLY",
        "CLAMD_HOST_PORT_PUBLISHED",
        "DOCUMENT_STORAGE_MOUNTED_IN_CLAMD",
        "BACKEND_SIGNATURE_DATABASE_MOUNTED",
        "CLAMD_SIGNATURE_VOLUME_PRESENT",
        "SHARED_DOCUMENT_PATH",
        "BACKEND_AND_CLAMD_SAME_INTERNAL_NETWORK",
        "CLAMD_HEALTHCHECK_PRESENT",
    ],
    "CLAMD": [
        "CLAMD_VERSION",
        "SIGNATURE_DATABASE_VERSION",
        "SIGNATURE_DATABASE_DATE",
        "CLAMD_PING_RESULT",
        "CLAMD_HEALTH_STATUS",
    ],
    "FUNCTIONAL": [
        "F01_STATUS",
        "F01_RESULT",
        "F02_STATUS",
        "F02_ERROR_CODE",
        "F02_RESULT",
        "F03_STATUS",
        "F03_ERROR_CODE",
        "F03_RESULT",
        "F04_STATUS",
        "F04_RESULT",
        "CLAMD_RECOVERY_AFTER_S",
    ],
    "SCANNER": ["RUNTIME_CLAMD_PATH_PROVEN", "RUNTIME_CLAMSCAN_FALLBACK", "IMPLICIT_FALLBACK"],
    "SIZE": [
        "KONTROL_MAX",
        "RUNTIME_STREAM_MAX_LENGTH",
        "RUNTIME_MAX_FILE_SIZE",
        "RUNTIME_MAX_SCAN_SIZE",
        "RUNTIME_ALERT_EXCEEDS_MAX",
        "MAX_DOCUMENT_SIZE_CONTRACT",
    ],
    "SECURITY": [
        "SECRET_EXPOSURE",
        "DOCUMENT_CONTENT_LOGGED",
        "EICAR_FULL_LOGGED",
        "PRODUCTION_TOUCHED",
    ],
    "CLEANUP": [
        "OBS09_CONTAINERS",
        "OBS09_NETWORKS",
        "OBS09_TEMP_IMAGES",
        "OBS09_TEMP_VOLUMES",
        "QA_PORTS_OCCUPIED",
    ],
}

CADENAS_PROHIBIDAS = [
    EICAR,
    "KONTROL_SECRET_KEY",
    "kontrol-obs09-sintetica",
    "/home/",
    "%PDF-1.4",
]

CRITERIOS_APROBADO: dict[str, str] = {
    "CLAMD_SERVICE_PRESENT": "1",
    "CLAMD_INTERNAL_ONLY": "1",
    "CLAMD_HOST_PORT_PUBLISHED": "0",
    "DOCUMENT_STORAGE_MOUNTED_IN_CLAMD": "0",
    "BACKEND_SIGNATURE_DATABASE_MOUNTED": "0",
    "CLAMD_SIGNATURE_VOLUME_PRESENT": "1",
    "SHARED_DOCUMENT_PATH": "0",
    "BACKEND_AND_CLAMD_SAME_INTERNAL_NETWORK": "1",
    "CLAMD_HEALTHCHECK_PRESENT": "1",
    "CLAMD_PING_RESULT": "PASS",
    "CLAMD_HEALTH_STATUS": "healthy",
    "F01_RESULT": "PASS",
    "F02_RESULT": "PASS",
    "F03_RESULT": "PASS",
    "F04_RESULT": "PASS",
    "RUNTIME_CLAMD_PATH_PROVEN": "1",
    "IMPLICIT_FALLBACK": "0",
    "MAX_DOCUMENT_SIZE_CONTRACT": "PASS",
    "BACKEND_IMAGE_HAS_CLAMSCAN": "0",
    "BACKEND_IMAGE_HAS_SIGNATURE_DATABASE": "0",
    "OBS09_CONTAINERS": "0",
    "OBS09_NETWORKS": "0",
    "OBS09_TEMP_IMAGES": "0",
    "OBS09_TEMP_VOLUMES": "0",
    "QA_PORTS_OCCUPIED": "0",
    "SECRET_EXPOSURE": "0",
    "DOCUMENT_CONTENT_LOGGED": "0",
    "EICAR_FULL_LOGGED": "0",
}


class EvidenciaIncompleta(RuntimeError):
    """La condición esperada no se cumplió dentro del plazo."""


@dataclass
class Resultado:
    rc: int
    salida: str
    error: str


@dataclass
class Composicion:
    docker: Docker
    proyecto: str
    run_id: str
    puerto: int
    etiqueta: str

    def ejecutar(self, *args: str) -> Resultado:
        return compose(
            self.docker, self.proyecto, self.run_id, self.puerto, self.etiqueta, *args
        )


class Docker:
    def __init__(
        self, ejecutar: Callable[[list[str]], Resultado] | None = None
    ) -> None:
        self._ejecutar = ejecutar

    def run(
        self,
        *args: str,
        entorno: dict[str, str] | None = None,
    ) -> Resultado:
        orden = ["docker", *args]
        if self._ejecutar is not None:
            return self._ejecutar(orden)
        env = os.environ.copy()
        if entorno:
            env.update(entorno)
        completado = subprocess.run(
            orden,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        return Resultado(completado.returncode, completado.stdout, completado.stderr)


def git(*args: str) -> str:
    try:
        completado = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=False,
            cwd=RAIZ,
        )
        if completado.returncode != 0:
            return ""
        return completado.stdout.strip()
    except OSError:
        return ""


def nuevo_run_id() -> str:
    marca = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"obs09-{marca}-{secrets.token_hex(3)}"


def precheck(docker: Docker) -> dict[str, Any]:
    datos: dict[str, Any] = {
        "DOCKER_AVAILABLE": 0,
        "DOCKER_VERSION": "NOT_MEASURED",
        "COMPOSE_VERSION": "NOT_MEASURED",
        "DOCKER_SERVER_REACHABLE": 0,
    }
    version = docker.run("--version")
    if version.rc == 0 and version.salida.strip():
        datos["DOCKER_AVAILABLE"] = 1
        datos["DOCKER_VERSION"] = version.salida.splitlines()[0].strip()
    compose_version = docker.run("compose", "version")
    if compose_version.rc == 0 and compose_version.salida.strip():
        datos["COMPOSE_VERSION"] = compose_version.salida.splitlines()[0].strip()
    info = docker.run("info", "--format", "{{.ServerVersion}}")
    if info.rc == 0 and info.salida.strip():
        datos["DOCKER_SERVER_REACHABLE"] = 1
    return datos


def construir(docker: Docker, dockerfile: str, etiqueta: str) -> dict[str, Any]:
    ruta_dockerfile = RAIZ / dockerfile
    inicio = time.monotonic()
    build = docker.run(
        "build",
        "-f",
        str(ruta_dockerfile),
        "-t",
        etiqueta,
        str(RAIZ),
    )
    segundos = time.monotonic() - inicio
    if build.rc != 0:
        raise EvidenciaIncompleta(
            f"No se pudo construir {dockerfile}: {build.error.strip()}"
        )
    inspeccion = docker.run(
        "image", "inspect", etiqueta, "--format", "{{.Size}}"
    )
    bytes_imagen = 0
    if inspeccion.rc == 0 and inspeccion.salida.strip():
        try:
            bytes_imagen = int(inspeccion.salida.strip())
        except ValueError:
            bytes_imagen = 0
    return {"segundos": segundos, "bytes": bytes_imagen, "rc": build.rc}


def imagen_backend_sin_analizador(docker: Docker, etiqueta: str) -> dict[str, int]:
    salida = docker.run(
        "run",
        "--rm",
        "--entrypoint",
        "sh",
        etiqueta,
        "-c",
        "command -v clamscan >/dev/null && echo CLAMSCAN=1 || echo CLAMSCAN=0; "
        "[ -d /var/lib/clamav ] && echo FIRMAS=1 || echo FIRMAS=0",
    )
    texto = salida.salida
    return {
        "BACKEND_IMAGE_HAS_CLAMSCAN": 1 if "CLAMSCAN=1" in texto else 0,
        "BACKEND_IMAGE_HAS_SIGNATURE_DATABASE": 1 if "FIRMAS=1" in texto else 0,
    }


def imagen_clamd_completa(docker: Docker, etiqueta: str) -> dict[str, int]:
    salida = docker.run(
        "run",
        "--rm",
        "--entrypoint",
        "sh",
        etiqueta,
        "-c",
        "command -v clamd >/dev/null && echo CLAMD=1 || echo CLAMD=0; "
        "[ -f /etc/clamav/clamd.conf ] && echo CONF=1 || echo CONF=0",
    )
    texto = salida.salida
    return {
        "CLAMD_BINARY_PRESENT": 1 if "CLAMD=1" in texto else 0,
        "CLAMD_CONFIG_PRESENT": 1 if "CONF=1" in texto else 0,
    }


def compose(
    docker: Docker,
    proyecto: str,
    run_id: str,
    puerto: int,
    etiqueta: str,
    *args: str,
) -> Resultado:
    entorno = {
        "KONTROL_IMAGE_REGISTRY": REGISTRO,
        "KONTROL_IMAGE_TAG": etiqueta,
        "OBS09_RUN": run_id,
        "OBS09_BACKEND_PORT": str(puerto),
        "KONTROL_DB_URL": "obs09",
        "KONTROL_SECRET_KEY": "obs09-clave-sintetica-de-qa-0123456789abcdef0123456789",
    }
    return docker.run(
        "compose",
        "-p",
        proyecto,
        "-f",
        str(COMPOSE),
        "-f",
        str(OVERRIDE),
        *args,
        entorno=entorno,
    )


def contenedor(comp: Composicion, servicio: str) -> str:
    resultado = comp.ejecutar("ps", "-q", servicio)
    return resultado.salida.strip() if resultado.rc == 0 else ""


def esperar(
    condicion: Callable[[], bool],
    limite_s: float,
    descripcion: str,
) -> float:
    inicio = time.monotonic()
    final = inicio + limite_s
    while time.monotonic() < final:
        if condicion():
            return time.monotonic() - inicio
        time.sleep(1.0)
    if condicion():
        return time.monotonic() - inicio
    raise EvidenciaIncompleta(f"{descripcion} no se cumplió en {limite_s:.0f} s")


def salud(docker: Docker, id_contenedor: str) -> str:
    if not id_contenedor:
        return "none"
    resultado = docker.run(
        "inspect", "--format", "{{.State.Health.Status}}", id_contenedor
    )
    if resultado.rc != 0 or not resultado.salida.strip():
        return "none"
    return resultado.salida.strip()


def inspeccionar(docker: Docker, id_contenedor: str) -> dict[str, Any]:
    if not id_contenedor:
        return {}
    resultado = docker.run("inspect", id_contenedor)
    if resultado.rc != 0:
        return {}
    try:
        datos = json.loads(resultado.salida)
    except json.JSONDecodeError:
        return {}
    if not isinstance(datos, list) or not datos:
        return {}
    contenedor_data = datos[0]
    puertos_publicados = []
    port_bindings = contenedor_data.get("HostConfig", {}).get("PortBindings", {})
    if isinstance(port_bindings, dict):
        for clave, valor in port_bindings.items():
            if valor:
                puertos_publicados.append(clave)
    montajes = []
    for montaje in contenedor_data.get("Mounts", []):
        destino = montaje.get("Destination")
        if destino:
            montajes.append(destino)
    redes = []
    networks = contenedor_data.get("NetworkSettings", {}).get("Networks", {})
    if isinstance(networks, dict):
        redes = list(networks.keys())
    estado_salud = (
        contenedor_data.get("State", {}).get("Health", {}).get("Status", "none")
    )
    return {
        "puertos_publicados": puertos_publicados,
        "montajes": montajes,
        "redes": redes,
        "salud": estado_salud,
    }


def clamd_runtime(comp: Composicion) -> dict[str, Any]:
    version = comp.ejecutar("exec", "-T", "clamd", "clamdscan", "--version")
    datos: dict[str, Any] = {
        "CLAMD_VERSION": "NOT_MEASURED",
        "SIGNATURE_DATABASE_VERSION": "NOT_MEASURED",
        "SIGNATURE_DATABASE_DATE": "NOT_MEASURED",
    }
    if version.rc == 0 and version.salida.strip():
        m = re.match(r"^ClamAV (\S+?)/(\d+)/(.+)$", version.salida.strip())
        if m:
            datos["CLAMD_VERSION"] = m.group(1)
            datos["SIGNATURE_DATABASE_VERSION"] = m.group(2)
            datos["SIGNATURE_DATABASE_DATE"] = m.group(3).strip()
    ping = comp.ejecutar(
        "exec",
        "-T",
        "clamd",
        "sh",
        "-c",
        "printf 'zPING\\0' | nc -w 5 127.0.0.1 3310",
    )
    datos["CLAMD_PING_RESULT"] = (
        "PASS" if ping.rc == 0 and "PONG" in ping.salida else "FAIL"
    )
    limites = comp.ejecutar(
        "exec",
        "-T",
        "clamd",
        "grep",
        "-E",
        "^(StreamMaxLength|MaxFileSize|MaxScanSize|AlertExceedsMax)",
        "/etc/clamav/clamd.conf",
    )
    for linea in limites.salida.splitlines():
        partes = linea.split()
        if len(partes) != 2:
            continue
        clave, valor = partes
        if clave == "StreamMaxLength":
            datos["RUNTIME_STREAM_MAX_LENGTH"] = valor
        elif clave == "MaxFileSize":
            datos["RUNTIME_MAX_FILE_SIZE"] = valor
        elif clave == "MaxScanSize":
            datos["RUNTIME_MAX_SCAN_SIZE"] = valor
        elif clave == "AlertExceedsMax":
            datos["RUNTIME_ALERT_EXCEEDS_MAX"] = valor
    return datos


def bytes_de_limite(texto: str) -> int:
    m = re.match(r"^(\d+)\s*([KMG])?$", texto.strip(), re.IGNORECASE)
    if not m:
        return 0
    valor = int(m.group(1))
    unidad = (m.group(2) or "").upper()
    multiplicador = {"K": 1024, "M": 1024**2, "G": 1024**3}.get(unidad, 1)
    return valor * multiplicador


class Backend:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = ""
        self.company = ""

    def _peticion(
        self,
        metodo: str,
        ruta: str,
        cuerpo: bytes | None = None,
        cabeceras: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        url = f"{self.base_url}{ruta}"
        cabeceras_final = dict(cabeceras or {})
        peticion = urllib.request.Request(
            url, data=cuerpo, method=metodo, headers=cabeceras_final
        )
        try:
            with urllib.request.urlopen(peticion) as respuesta:
                datos_respuesta = respuesta.read()
                try:
                    contenido = json.loads(datos_respuesta)
                except json.JSONDecodeError:
                    contenido = {}
                return respuesta.status, contenido
        except urllib.error.HTTPError as e:
            cuerpo_respuesta = e.read()
            try:
                contenido = json.loads(cuerpo_respuesta)
            except json.JSONDecodeError:
                contenido = {}
            return e.code, contenido
        except (urllib.error.URLError, OSError):
            return 0, {}

    def vivo(self) -> bool:
        codigo, _ = self._peticion("GET", "/api/v1/health/live")
        return codigo == 200

    def inicializar(self) -> None:
        datos = {
            "tenant_code": "obs09",
            "tenant_name": "OBS-09 QA",
            "company_code": "OBS09",
            "company_legal_name": "OBS-09 QA C.A.",
            "company_rif": "J-00000000-9",
            "admin_username": "admin_obs09",
            "admin_password": "Obs09-Clave-Sintetica-1",
        }
        codigo, _ = self._peticion(
            "POST",
            "/api/v1/setup/initialize",
            cuerpo=json.dumps(datos).encode(),
            cabeceras={"Content-Type": "application/json"},
        )
        if codigo in (200, 201):
            return
        _, estado = self._peticion("GET", "/api/v1/setup/status")
        if estado.get("initialized") is True:
            self.company = str(estado.get("company", ""))
            return
        raise EvidenciaIncompleta("No se pudo inicializar el backend")

    def entrar(self) -> None:
        _, estado = self._peticion("GET", "/api/v1/setup/status")
        self.company = str(estado.get("company", ""))
        datos = {
            "tenant_code": "obs09",
            "username": "admin_obs09",
            "password": "Obs09-Clave-Sintetica-1",
        }
        codigo, respuesta = self._peticion(
            "POST",
            "/api/v1/auth/login",
            cuerpo=json.dumps(datos).encode(),
            cabeceras={"Content-Type": "application/json"},
        )
        if codigo in (200, 201) and respuesta.get("access_token"):
            self.token = str(respuesta["access_token"])
            return
        raise EvidenciaIncompleta("No se pudo iniciar sesión")

    def _cabeceras_autenticadas(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        cabeceras = {
            "Authorization": f"Bearer {self.token}",
            "X-Kontrol-Company": self.company,
        }
        if extra:
            cabeceras.update(extra)
        return cabeceras

    def crear_tipo(self, codigo: str) -> int | str:
        datos = {
            "code": codigo,
            "name": f"Tipo {codigo}",
            "allowed_mime_types": ["application/pdf", "text/plain"],
            "allowed_extensions": ["pdf", "txt"],
            "scan_required": True,
        }
        codigo_http, respuesta = self._peticion(
            "POST",
            "/api/v1/documentos/tipos",
            cuerpo=json.dumps(datos).encode(),
            cabeceras=self._cabeceras_autenticadas(
                {"Content-Type": "application/json"}
            ),
        )
        if codigo_http not in (200, 201):
            raise EvidenciaIncompleta("No se pudo crear el tipo documental")
        return respuesta.get("id", "")

    def crear_documento(self, tipo_id: int | str, titulo: str) -> int | str:
        datos = {"document_type_id": tipo_id, "title": titulo}
        codigo, respuesta = self._peticion(
            "POST",
            "/api/v1/documentos",
            cuerpo=json.dumps(datos).encode(),
            cabeceras=self._cabeceras_autenticadas(
                {"Content-Type": "application/json"}
            ),
        )
        if codigo not in (200, 201):
            raise EvidenciaIncompleta("No se pudo crear el documento")
        return respuesta.get("id", "")

    def subir(
        self,
        documento_id: int | str,
        nombre: str,
        contenido: bytes,
        mime: str,
    ) -> tuple[int, dict[str, Any]]:
        boundary = f"----FormBoundary{secrets.token_hex(16)}"
        cuerpo = bytearray()
        cuerpo.extend(
            f"--{boundary}\r\n".encode()
        )
        cuerpo.extend(
            f'Content-Disposition: form-data; name="file"; filename="{nombre}"\r\n'.encode()
        )
        cuerpo.extend(f"Content-Type: {mime}\r\n\r\n".encode())
        cuerpo.extend(contenido)
        cuerpo.extend(f"\r\n--{boundary}--\r\n".encode())
        codigo, respuesta = self._peticion(
            "POST",
            f"/api/v1/documentos/{documento_id}/versiones",
            cuerpo=bytes(cuerpo),
            cabeceras=self._cabeceras_autenticadas(
                {"Content-Type": f"multipart/form-data; boundary={boundary}"}
            ),
        )
        return codigo, respuesta

    @staticmethod
    def _buscar_clave(obj: Any, clave: str) -> Any:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == clave:
                    return v
                resultado = Backend._buscar_clave(v, clave)
                if resultado is not None:
                    return resultado
        elif isinstance(obj, list):
            for elemento in obj:
                resultado = Backend._buscar_clave(elemento, clave)
                if resultado is not None:
                    return resultado
        return None


def caso(
    status: int,
    cuerpo: dict[str, Any],
    esperado_status: int,
    esperado_codigo: str | None,
    esperado_clean: bool,
) -> dict[str, Any]:
    resultado: dict[str, Any] = {
        "STATUS": status,
        "ERROR_CODE": cuerpo.get("code"),
    }
    if esperado_clean:
        security_status = Backend._buscar_clave(cuerpo, "security_status")
        resultado["RESULT"] = (
            "PASS" if status == 200 and security_status == "CLEAN" else "FAIL"
        )
    else:
        resultado["RESULT"] = (
            "PASS"
            if status == esperado_status and cuerpo.get("code") == esperado_codigo
            else "FAIL"
        )
    return resultado


def contrato_funcional(comp: Composicion, backend: Backend) -> dict[str, Any]:
    backend.inicializar()
    backend.entrar()
    tipo_id = backend.crear_tipo("OBS09")
    doc1 = backend.crear_documento(tipo_id, "OBS-09")
    f01_status, f01_cuerpo = backend.subir(
        doc1, "limpio.pdf", PDF_LIMPIO, "application/pdf"
    )
    f01 = caso(f01_status, f01_cuerpo, 200, None, True)
    doc2 = backend.crear_documento(tipo_id, "OBS-09")
    f02_status, f02_cuerpo = backend.subir(
        doc2, "muestra.txt", EICAR.encode("ascii"), "text/plain"
    )
    f02 = caso(f02_status, f02_cuerpo, 422, "FILE_INFECTED", False)
    comp.ejecutar("stop", "clamd")
    doc3 = backend.crear_documento(tipo_id, "OBS-09")
    f03_status, f03_cuerpo = backend.subir(
        doc3, "limpio.pdf", PDF_LIMPIO, "application/pdf"
    )
    f03 = caso(f03_status, f03_cuerpo, 422, "SCAN_FAILED", False)
    comp.ejecutar("start", "clamd")
    id_clamd = contenedor(comp, "clamd")
    recuperacion = esperar(
        lambda: salud(comp.docker, id_clamd) == "healthy",
        PLAZO_CLAMD_S,
        "clamd healthy tras reanudar",
    )
    doc4 = backend.crear_documento(tipo_id, "OBS-09")
    f04_status, f04_cuerpo = backend.subir(
        doc4, "limpio.pdf", PDF_LIMPIO, "application/pdf"
    )
    f04 = caso(f04_status, f04_cuerpo, 200, None, True)
    return {
        "F01_STATUS": f01["STATUS"],
        "F01_RESULT": f01["RESULT"],
        "F02_STATUS": f02["STATUS"],
        "F02_ERROR_CODE": f02["ERROR_CODE"],
        "F02_RESULT": f02["RESULT"],
        "F03_STATUS": f03["STATUS"],
        "F03_ERROR_CODE": f03["ERROR_CODE"],
        "F03_RESULT": f03["RESULT"],
        "F04_STATUS": f04["STATUS"],
        "F04_RESULT": f04["RESULT"],
        "CLAMD_RECOVERY_AFTER_S": recuperacion,
    }


def veredicto_composicion(
    backend_insp: dict[str, Any],
    clamd_insp: dict[str, Any],
    red_corrida: str,
) -> dict[str, int]:
    clamd_vacio = not clamd_insp
    clamd_puertos = clamd_insp.get("puertos_publicados", [])
    clamd_montajes = clamd_insp.get("montajes", [])
    clamd_redes = clamd_insp.get("redes", [])
    backend_montajes = backend_insp.get("montajes", [])
    backend_redes = backend_insp.get("redes", [])
    montajes_banned = ["storage", "backups", "license-state"]
    clamd_almacen = any(
        any(b in str(m).lower() for b in montajes_banned) for m in clamd_montajes
    )
    backend_clamav = any("clamav" in str(m).lower() for m in backend_montajes)
    clamd_volumen_firmas = "/var/lib/clamav" in clamd_montajes
    backend_montajes_set = set(str(m) for m in backend_montajes)
    clamd_montajes_set = set(str(m) for m in clamd_montajes)
    compartido = bool(backend_montajes_set & clamd_montajes_set)
    backend_redes_set = set(str(r) for r in backend_redes)
    clamd_redes_set = set(str(r) for r in clamd_redes)
    misma_red = bool(backend_redes_set & clamd_redes_set)
    clamd_health = clamd_insp.get("salud", "none")
    return {
        "CLAMD_SERVICE_PRESENT": 0 if clamd_vacio else 1,
        "CLAMD_HOST_PORT_PUBLISHED": 1 if clamd_puertos else 0,
        "CLAMD_INTERNAL_ONLY": (
            1
            if not clamd_puertos
            and len(clamd_redes) == 1
            and clamd_redes
            and clamd_redes[0] == red_corrida
            else 0
        ),
        "DOCUMENT_STORAGE_MOUNTED_IN_CLAMD": 1 if clamd_almacen else 0,
        "BACKEND_SIGNATURE_DATABASE_MOUNTED": 1 if backend_clamav else 0,
        "CLAMD_SIGNATURE_VOLUME_PRESENT": 1 if clamd_volumen_firmas else 0,
        "SHARED_DOCUMENT_PATH": 1 if compartido else 0,
        "BACKEND_AND_CLAMD_SAME_INTERNAL_NETWORK": 1 if misma_red else 0,
        "CLAMD_HEALTHCHECK_PRESENT": 0 if clamd_health == "none" else 1,
    }


def _lineas_no_vacias(texto: str) -> int:
    contador = 0
    for linea in texto.splitlines():
        if linea.strip():
            contador += 1
    return contador


def limpiar(
    comp: Composicion,
    etiquetas_imagen: list[str],
) -> dict[str, int]:
    comp.ejecutar("down", "--volumes", "--remove-orphans")
    for etiqueta in etiquetas_imagen:
        comp.docker.run("image", "rm", "-f", etiqueta)
    contenedores = comp.docker.run(
        "ps", "-aq", "--filter", f"label=com.docker.compose.project={comp.proyecto}"
    )
    redes = comp.docker.run(
        "network", "ls", "-q", "--filter", f"name=kontrol-obs09-{comp.run_id}"
    )
    volumenes = comp.docker.run(
        "volume", "ls", "-q", "--filter", f"label=com.docker.compose.project={comp.proyecto}"
    )
    imagenes_backend = comp.docker.run(
        "images", "-q", f"{REGISTRO}/kontrol-backend:{comp.etiqueta}"
    )
    imagenes_clamd = comp.docker.run(
        "images", "-q", f"{REGISTRO}/kontrol-clamd:{comp.etiqueta}"
    )
    puerto_ocupado = 0
    try:
        with socket.create_connection(("127.0.0.1", comp.puerto), timeout=0.5):
            puerto_ocupado = 1
    except OSError:
        puerto_ocupado = 0
    return {
        "OBS09_CONTAINERS": _lineas_no_vacias(contenedores.salida),
        "OBS09_NETWORKS": _lineas_no_vacias(redes.salida),
        "OBS09_TEMP_VOLUMES": _lineas_no_vacias(volumenes.salida),
        "OBS09_TEMP_IMAGES": _lineas_no_vacias(imagenes_backend.salida)
        + _lineas_no_vacias(imagenes_clamd.salida),
        "QA_PORTS_OCCUPIED": puerto_ocupado,
    }


def completar(datos: dict[str, Any]) -> dict[str, Any]:
    copia = dict(datos)
    f01_pass = str(copia.get("F01_RESULT")) == "PASS"
    f03_pass = str(copia.get("F03_RESULT")) == "PASS"
    f04_pass = str(copia.get("F04_RESULT")) == "PASS"
    copia["RUNTIME_CLAMD_PATH_PROVEN"] = (
        1 if f01_pass and f03_pass and f04_pass else 0
    )
    if f03_pass:
        copia["RUNTIME_CLAMSCAN_FALLBACK"] = 0
        copia["IMPLICIT_FALLBACK"] = 0
    else:
        copia["RUNTIME_CLAMSCAN_FALLBACK"] = 1
        copia["IMPLICIT_FALLBACK"] = 1
    copia["KONTROL_MAX"] = 52428800
    stream = copia.get("RUNTIME_STREAM_MAX_LENGTH")
    max_file = copia.get("RUNTIME_MAX_FILE_SIZE")
    max_scan = copia.get("RUNTIME_MAX_SCAN_SIZE")
    alert = str(copia.get("RUNTIME_ALERT_EXCEEDS_MAX", "")).lower()
    if stream and max_file and max_scan:
        if (
            bytes_de_limite(str(stream)) >= MAXIMO_DOCUMENTAL
            and bytes_de_limite(str(max_file)) >= MAXIMO_DOCUMENTAL
            and bytes_de_limite(str(max_scan)) >= MAXIMO_DOCUMENTAL
            and alert == "yes"
        ):
            copia["MAX_DOCUMENT_SIZE_CONTRACT"] = "PASS"
        else:
            copia["MAX_DOCUMENT_SIZE_CONTRACT"] = "FAIL"
    else:
        copia["MAX_DOCUMENT_SIZE_CONTRACT"] = "NOT_MEASURED"
    copia["PRODUCTION_TOUCHED"] = 0
    texto_completo = " ".join(str(v) for v in copia.values())
    secret_expuesto = 0
    contenido_logueado = 0
    eicar_completo = 0
    for prohibida in CADENAS_PROHIBIDAS:
        if prohibida in texto_completo:
            if prohibida == EICAR:
                eicar_completo = 1
            elif prohibida in ("kontrol-obs09-sintetica", "/home/", "KONTROL_SECRET_KEY"):
                secret_expuesto = 1
            elif prohibida == "%PDF-1.4":
                contenido_logueado = 1
    copia["SECRET_EXPOSURE"] = secret_expuesto
    copia["DOCUMENT_CONTENT_LOGGED"] = contenido_logueado
    copia["EICAR_FULL_LOGGED"] = eicar_completo
    for seccion in SECCIONES_EVIDENCIA:
        for clave in CLAVES_EVIDENCIA[seccion]:
            if clave not in copia or copia[clave] is None:
                copia[clave] = "NOT_MEASURED"
    return copia


def evidencia(datos: dict[str, Any]) -> str:
    datos_completos = completar(datos)
    lineas = ["OBS09_EXTERNAL_DOCKER_EVIDENCE"]
    for seccion in SECCIONES_EVIDENCIA:
        lineas.append(seccion)
        for clave in CLAVES_EVIDENCIA[seccion]:
            valor = datos_completos.get(clave, "NOT_MEASURED")
            for prohibida in CADENAS_PROHIBIDAS:
                if prohibida in str(valor):
                    valor = "[REDACTADO]"
                    break
            lineas.append(f"{clave}={valor}")
    return "\n".join(lineas)


def aprobado(datos: dict[str, Any]) -> bool:
    if "ERROR" in datos and datos["ERROR"]:
        return False
    datos_completos = completar(datos)
    for clave, esperado in CRITERIOS_APROBADO.items():
        actual = str(datos_completos.get(clave, "NOT_MEASURED"))
        if actual != esperado:
            return False
    return True


def certificar(
    docker: Docker,
    *,
    puerto: int = 18000,
    carpeta: Path = CORRIDAS,
    backend: Backend | None = None,
) -> tuple[dict[str, Any], int]:
    run_id = nuevo_run_id()
    carpeta_corrida = carpeta / run_id
    carpeta_corrida.mkdir(parents=True, exist_ok=True)
    datos: dict[str, Any] = {
        "HEAD": git("rev-parse", "--short", "HEAD") or "NOT_MEASURED",
        "BRANCH": git("branch", "--show-current") or "NOT_MEASURED",
        "WORKTREE": (
            "clean"
            if not git("status", "--short")
            else "dirty"
        ),
    }
    datos.update(precheck(docker))
    if datos["DOCKER_SERVER_REACHABLE"] != 1:
        _escribir_evidencia(carpeta_corrida, datos)
        return datos, 2
    comp = Composicion(
        docker=docker,
        proyecto=run_id,
        run_id=run_id,
        puerto=puerto,
        etiqueta=run_id,
    )
    etiqueta_backend = f"{REGISTRO}/kontrol-backend:{run_id}"
    etiqueta_clamd = f"{REGISTRO}/kontrol-clamd:{run_id}"
    etiquetas = [etiqueta_backend, etiqueta_clamd]
    try:
        backend_build = construir(docker, "Dockerfile.backend", etiqueta_backend)
        clamd_build = construir(docker, "Dockerfile.clamd", etiqueta_clamd)
        datos["BACKEND_IMAGE_BUILD_TIME"] = backend_build["segundos"]
        datos["CLAMD_IMAGE_BUILD_TIME"] = clamd_build["segundos"]
        datos["BACKEND_IMAGE_SIZE"] = backend_build["bytes"]
        datos["CLAMD_IMAGE_SIZE"] = clamd_build["bytes"]
        datos.update(imagen_backend_sin_analizador(docker, etiqueta_backend))
        datos.update(imagen_clamd_completa(docker, etiqueta_clamd))
        up = comp.ejecutar("up", "-d", "db", "clamd", "backend")
        if up.rc != 0:
            raise EvidenciaIncompleta(f"compose up falló: {up.error.strip()}")
        id_db = contenedor(comp, "db")
        esperar(
            lambda: salud(docker, id_db) == "healthy",
            PLAZO_DB_S,
            "db healthy",
        )
        id_clamd = contenedor(comp, "clamd")
        datos["CLAMD_HEALTHY_AFTER_S"] = esperar(
            lambda: salud(docker, id_clamd) == "healthy",
            PLAZO_CLAMD_S,
            "clamd healthy",
        )
        backend_cliente = backend or Backend(f"http://127.0.0.1:{puerto}")
        datos["BACKEND_READY_AFTER_S"] = esperar(
            backend_cliente.vivo,
            PLAZO_BACKEND_S,
            "backend vivo",
        )
        backend_insp = inspeccionar(docker, contenedor(comp, "backend"))
        clamd_insp = inspeccionar(docker, id_clamd)
        datos.update(
            veredicto_composicion(
                backend_insp, clamd_insp, f"kontrol-obs09-{run_id}"
            )
        )
        datos.update(clamd_runtime(comp))
        datos["CLAMD_HEALTH_STATUS"] = salud(docker, id_clamd)
        datos.update(contrato_funcional(comp, backend_cliente))
    except (EvidenciaIncompleta, OSError, ValueError) as exc:
        datos["ERROR"] = str(exc).replace("/home/", "[REDACTADO]")
    finally:
        datos.update(limpiar(comp, etiquetas))
    _escribir_evidencia(carpeta_corrida, datos)
    rc = 0 if aprobado(datos) else 1
    print(evidencia(datos))
    return datos, rc


def _escribir_evidencia(carpeta: Path, datos: dict[str, Any]) -> None:
    texto = evidencia(datos)
    (carpeta / "evidencia.txt").write_text(texto, encoding="utf-8")
    (carpeta / "evidencia.json").write_text(
        json.dumps(completar(datos), indent=2, default=str),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Certificación OBS-09 con Docker")
    parser.add_argument("--puerto", type=int, default=18000)
    parser.add_argument("--carpeta", type=Path, default=CORRIDAS)
    args = parser.parse_args(argv)
    docker = Docker()
    _, rc = certificar(docker, puerto=args.puerto, carpeta=args.carpeta)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
