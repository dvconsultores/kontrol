"""Análisis antimalware de archivos (Spec 046, F5).

`ESC-046-01` quedó resuelto en implementación: el análisis es **obligatorio por
defecto** y se cierra en falso seguro. Un analizador ausente **no** significa
archivo limpio (§26): significa `SCAN_FAILED`, y un archivo que no está `CLEAN`
no se entrega jamás.

El dominio no conoce ClamAV: habla con `FileSecurityScanner`. El adaptador es
sustituible, y ese desacoplamiento es la razón de que el fabricante no aparezca
en ninguna regla de negocio.
"""

from __future__ import annotations

import os
import re
import shutil
import socket
import struct
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.config import get_settings

#: Resultados posibles. Coinciden con `FILE_SECURITY_STATUSES` del modelo.
PENDING_SCAN = "PENDING_SCAN"
CLEAN = "CLEAN"
INFECTED = "INFECTED"
SCAN_FAILED = "SCAN_FAILED"
SKIPPED = "SKIPPED"


@dataclass(frozen=True)
class ScanResult:
    """Resultado inmutable. Lo que se escribe en la versión no debe poder
    cambiarse después de decidirse."""

    result: str
    scanner: str
    signature: str | None = None
    details: dict[str, object] | None = None

    @property
    def is_clean(self) -> bool:
        return self.result == CLEAN


class FileSecurityScanner(ABC):
    """Contrato del analizador."""

    name: str = "ABSTRACT"

    @abstractmethod
    def scan(self, path: str) -> ScanResult: ...

    @abstractmethod
    def available(self) -> bool: ...


class ClamAVScanner(FileSecurityScanner):
    """Adaptador de ClamAV por línea de órdenes.

    Se usa `clamscan` y no el demonio para que una instalación independiente no
    tenga que mantener un servicio más. El binario y la base de firmas se
    localizan por configuración; si faltan, `available()` es `False` y el
    resultado es `SCAN_FAILED`, nunca `CLEAN`.
    """

    name = "clamav"

    def __init__(self, binary: str | None = None, database: str | None = None,
                 timeout: int = 120) -> None:
        self.binary = binary or os.environ.get("KONTROL_CLAMSCAN_PATH") or shutil.which("clamscan")
        self.database = database or os.environ.get("KONTROL_CLAMAV_DB")
        self.timeout = timeout

    def available(self) -> bool:
        return bool(self.binary) and os.path.exists(self.binary)

    def scan(self, path: str) -> ScanResult:
        if not self.available():
            # **Falso seguro**: sin analizador no se afirma limpieza.
            return ScanResult(SCAN_FAILED, self.name,
                              details={"reason": "scanner_unavailable"})
        command = [self.binary, "--no-summary", "--stdout"]
        if self.database:
            command.append(f"--database={self.database}")
        command.append(path)
        try:
            completed = subprocess.run(command, capture_output=True, text=True,
                                       timeout=self.timeout, check=False)
        except (subprocess.TimeoutExpired, OSError) as exc:
            return ScanResult(SCAN_FAILED, self.name,
                              details={"reason": type(exc).__name__})

        # ClamAV: 0 = limpio · 1 = infectado · 2 = error.
        if completed.returncode == 0:
            return ScanResult(CLEAN, self.name)
        if completed.returncode == 1:
            signature = None
            for line in completed.stdout.splitlines():
                if line.strip().endswith("FOUND"):
                    signature = line.rsplit(":", 1)[-1].replace("FOUND", "").strip()
                    break
            return ScanResult(INFECTED, self.name, signature=signature)
        return ScanResult(SCAN_FAILED, self.name,
                          details={"reason": "scanner_error", "code": completed.returncode})


#: Tamaño de cada trozo del flujo INSTREAM: un documento nunca cabe «en un solo envío».
TROZO_INSTREAM = 64 * 1024
#: Respuesta máxima que se acepta del demonio antes de declararla malformada (las reales miden decenas de bytes).
RESPUESTA_MAXIMA = 4096
_RESPUESTA_FOUND = re.compile(r"^stream: (.+) FOUND$")


class _RespuestaTruncada(Exception):
    """El demonio cerró la conexión sin terminar su respuesta."""


class ClamdScanner(FileSecurityScanner):
    """Adaptador del demonio `clamd` por el protocolo INSTREAM (OBS-09, opción B de la dueña).

    El backend abre su propio temporal, lo **transmite** en trozos con longitud prefijada y termina con un trozo de
    longitud cero; al demonio nunca le llega una ruta, no monta el almacén documental y no necesita ver el sistema de
    archivos de KONTROL. La respuesta (`stream: OK`, `stream: <firma> FOUND` o un `ERROR`) se traduce aquí y en ningún
    otro sitio: cualquier cosa que no sea exactamente `OK` o `FOUND` —rechazo de conexión, demonio caído, tiempo
    agotado, conexión cortada a mitad del flujo, respuesta truncada o irreconocible, límite de tamaño del demonio— es
    `SCAN_FAILED`, nunca `CLEAN`, y no existe paso alguno a `clamscan` ni a «sin análisis».
    """

    name = "clamd"

    def __init__(self, host: str | None = None, port: int | None = None, timeout: int = 120) -> None:
        if host is None or port is None:
            configuracion = get_settings()
            host = host or configuracion.clamd_host
            port = port or configuracion.clamd_port
        self.host = host
        self.port = int(port)
        self.timeout = timeout

    def available(self) -> bool:
        return bool(self.host) and 0 < int(self.port) < 65536

    def scan(self, path: str) -> ScanResult:
        if not self.available():
            return ScanResult(SCAN_FAILED, self.name, details={"reason": "scanner_unavailable"})
        try:
            with open(path, "rb") as origen, \
                    socket.create_connection((self.host, self.port), timeout=self.timeout) as conexion:
                conexion.settimeout(self.timeout)
                conexion.sendall(b"zINSTREAM\0")
                while True:
                    trozo = origen.read(TROZO_INSTREAM)
                    if not trozo:
                        break
                    conexion.sendall(struct.pack("!I", len(trozo)) + trozo)
                conexion.sendall(struct.pack("!I", 0))
                respuesta = self._leer_respuesta(conexion)
        except TimeoutError:
            return ScanResult(SCAN_FAILED, self.name, details={"reason": "timeout"})
        except ConnectionRefusedError:
            return ScanResult(SCAN_FAILED, self.name, details={"reason": "connection_refused"})
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            return ScanResult(SCAN_FAILED, self.name, details={"reason": "stream_interrupted"})
        except _RespuestaTruncada:
            return ScanResult(SCAN_FAILED, self.name, details={"reason": "truncated_response"})
        except OSError as exc:
            return ScanResult(SCAN_FAILED, self.name, details={"reason": type(exc).__name__})
        return self._traducir(respuesta)

    @staticmethod
    def _leer_respuesta(conexion: socket.socket) -> bytes:
        """Lee hasta el terminador `\0` de la orden `z…`; sin terminador antes del cierre o del límite, está truncada."""
        acumulado = b""
        while b"\0" not in acumulado:
            if len(acumulado) >= RESPUESTA_MAXIMA:
                raise _RespuestaTruncada()
            leido = conexion.recv(RESPUESTA_MAXIMA)
            if not leido:
                raise _RespuestaTruncada()
            acumulado += leido
        return acumulado.split(b"\0", 1)[0]

    def _traducir(self, respuesta: bytes) -> ScanResult:
        texto = respuesta.decode("utf-8", errors="replace").strip()
        if texto == "stream: OK":
            return ScanResult(CLEAN, self.name)
        encontrado = _RESPUESTA_FOUND.match(texto)
        if encontrado:
            return ScanResult(INFECTED, self.name, signature=encontrado.group(1).strip())
        if texto.endswith("ERROR"):
            return ScanResult(SCAN_FAILED, self.name, details={"reason": "scanner_error", "response": texto[:200]})
        return ScanResult(SCAN_FAILED, self.name, details={"reason": "protocol_error", "response": texto[:200]})


class DisabledScanner(FileSecurityScanner):
    """Análisis desactivado **de forma explícita** por configuración.

    Devuelve `SKIPPED`, no `CLEAN`: el estado viaja en la respuesta para que
    nunca se afirme que un archivo fue analizado si no lo fue (FR-046-072).
    Solo un `DocumentType` con `scan_required = false` puede aceptarlo.
    """

    name = "disabled"

    def available(self) -> bool:
        return True

    def scan(self, path: str) -> ScanResult:
        del path
        return ScanResult(SKIPPED, self.name, details={"reason": "scanning_disabled"})


_scanner: FileSecurityScanner | None = None


def get_scanner() -> FileSecurityScanner:
    """Analizador activo.

    Por defecto ClamAV. `KONTROL_DOCUMENT_SCAN=off` lo desactiva de forma
    deliberada y auditable; no existe forma de desactivarlo por accidente.
    Con análisis activo, `Settings.document_scanner` elige **explícitamente**
    el adaptador: `clamd` (demonio del servicio de la composición) o
    `clamscan` (binario local). No hay alternativa implícita: si el elegido
    falla, el resultado es `SCAN_FAILED`.
    """
    global _scanner
    if _scanner is None:
        if os.environ.get("KONTROL_DOCUMENT_SCAN", "on").lower() in ("off", "false", "0"):
            _scanner = DisabledScanner()
        elif get_settings().document_scanner == "clamd":
            _scanner = ClamdScanner()
        else:
            _scanner = ClamAVScanner()
    return _scanner


def set_scanner(scanner: FileSecurityScanner | None) -> None:
    """Sustituye el analizador. Para pruebas, no para producción."""
    global _scanner
    _scanner = scanner
