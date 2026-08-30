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
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass

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
    """
    global _scanner
    if _scanner is None:
        if os.environ.get("KONTROL_DOCUMENT_SCAN", "on").lower() in ("off", "false", "0"):
            _scanner = DisabledScanner()
        else:
            _scanner = ClamAVScanner()
    return _scanner


def set_scanner(scanner: FileSecurityScanner | None) -> None:
    """Sustituye el analizador. Para pruebas, no para producción."""
    global _scanner
    _scanner = scanner
