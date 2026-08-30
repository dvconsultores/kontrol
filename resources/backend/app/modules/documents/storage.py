"""Abstracción de almacenamiento documental (Spec 046, F2).

El binario vive fuera de la base de datos; el código, dentro. Ningún servicio de
negocio conoce el sistema de archivos: hablan con `DocumentStorageProvider`.

La `storage_key` la genera **siempre** el servidor y es opaca: no se deriva del
nombre del archivo, de la empresa ni del tercero, y no se expone en ninguna
respuesta (R-046-3, R-D0-08-2). Eso vuelve irrelevante cualquier intento de
recorrido de rutas: el nombre del usuario nunca toca el sistema de archivos.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import secrets
import unicodedata
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO

from app.core.errors import KontrolError

#: Trozo de lectura. Los archivos se procesan en flujo: no se cargan enteros en
#: memoria (§31).
CHUNK = 1024 * 1024

#: Nombres reservados de Windows: un archivo así puede romper un cliente aunque
#: el servidor lo tolere.
_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


class StorageError(KontrolError):
    """Fallo del almacenamiento. Nunca se confunde con un error funcional."""

    def __init__(self, message: str = "El almacenamiento no está disponible",
                 *, code: str = "STORAGE_FAILURE", status_code: int = 503) -> None:
        super().__init__(code=code, message=message, status_code=status_code)


def sanitize_filename(name: str | None) -> str:
    """Sanea un nombre **solo para mostrarlo y para la cabecera de descarga**.

    Nunca produce una ruta: el resultado no se usa para acceder a nada. Elimina
    separadores, caracteres de control y secuencias de recorrido, y normaliza
    Unicode para que dos nombres visualmente iguales no se comporten distinto.
    """
    if not name:
        return "archivo"
    # NFKC colapsa homoglifos y formas compatibles.
    clean = unicodedata.normalize("NFKC", name)
    # Caracteres de control, incluidos CR y LF: evitan inyección de cabecera.
    clean = "".join(ch for ch in clean if ch.isprintable() and ch not in "\r\n")
    # Solo el último segmento: `../../x.pdf` se convierte en `x.pdf`.
    clean = clean.replace("\\", "/").split("/")[-1]
    clean = clean.replace('"', "").strip().strip(".")
    clean = re.sub(r"\s+", " ", clean)
    if not clean or set(clean) <= {"."}:
        return "archivo"
    stem = clean.rsplit(".", 1)[0]
    if stem.upper() in _RESERVED:
        clean = f"_{clean}"
    return clean[:255]


def safe_extension(name: str | None) -> str | None:
    """Extensión normalizada, o `None`. Nunca es autoridad por sí sola."""
    clean = sanitize_filename(name)
    if "." not in clean:
        return None
    ext = clean.rsplit(".", 1)[1].lower()
    return ext[:16] if ext.isalnum() else None


def generate_storage_key(company_id: str | None) -> str:
    """Clave opaca. Ni el nombre, ni la empresa, ni el tercero aparecen en ella.

    Se agrupa por fecha únicamente para no acumular millones de entradas en un
    solo directorio; la fecha no es información sensible ni identifica a nadie.
    """
    del company_id  # deliberado: la clave no lleva identidad
    today = datetime.now(UTC)
    return f"{today:%Y/%m/%d}/{secrets.token_urlsafe(24)}"


class DocumentStorageProvider(ABC):
    """Contrato del almacenamiento. El dominio no conoce nada más."""

    name: str = "ABSTRACT"

    @abstractmethod
    def put(self, key: str, stream: BinaryIO) -> tuple[int, str]:
        """Escribe y devuelve `(tamaño, sha256)` calculados al escribir."""

    @abstractmethod
    def open(self, key: str) -> BinaryIO: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def size(self, key: str) -> int: ...

    @abstractmethod
    def health(self) -> dict[str, object]: ...

    def verify(self, key: str, expected_sha256: str) -> bool:
        """Relee el objeto y compara su hash. Es lo que convierte «escribí» en
        «está y es el que era» (FR-046-037)."""
        if not self.exists(key):
            return False
        digest = hashlib.sha256()
        with self.open(key) as fh:
            for chunk in iter(lambda: fh.read(CHUNK), b""):
                digest.update(chunk)
        return digest.hexdigest() == expected_sha256


class FilesystemStorageProvider(DocumentStorageProvider):
    """Proveedor por defecto, sobre el volumen ya existente.

    Es el que usarán las instalaciones independientes, y el único con riesgo
    real de recorrido de rutas: cada clave se resuelve y se comprueba que cae
    **dentro** de la raíz antes de tocar el disco.
    """

    name = "FILESYSTEM"

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        """Resuelve la clave dentro de la raíz. Doble red de seguridad: la clave
        ya la generó el servidor, y aun así se comprueba."""
        if not key or key.startswith("/") or "\\" in key:
            raise StorageError(code="STORAGE_INVALID_KEY", message="Clave de almacenamiento inválida",
                               status_code=422)
        target = (self.root / key).resolve()
        if not str(target).startswith(str(self.root) + os.sep):
            raise StorageError(code="STORAGE_INVALID_KEY",
                               message="La clave escapa del almacenamiento", status_code=422)
        return target

    def put(self, key: str, stream: BinaryIO) -> tuple[int, str]:
        target = self._resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        # Se escribe a un temporal y se renombra: un fallo a mitad no deja un
        # objeto parcial con la clave definitiva.
        temporary = target.with_suffix(target.suffix + f".part-{secrets.token_hex(6)}")
        digest = hashlib.sha256()
        size = 0
        try:
            with open(temporary, "wb") as out:
                for chunk in iter(lambda: stream.read(CHUNK), b""):
                    digest.update(chunk)
                    size += len(chunk)
                    out.write(chunk)
                out.flush()
                os.fsync(out.fileno())
            os.replace(temporary, target)
            # Permisos mínimos: legible solo por el propietario del proceso.
            os.chmod(target, 0o600)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise StorageError(f"No se pudo escribir en el almacenamiento: {exc.strerror}") from exc
        return size, digest.hexdigest()

    def open(self, key: str) -> BinaryIO:
        target = self._resolve(key)
        try:
            return open(target, "rb")
        except FileNotFoundError as exc:
            raise StorageError(code="STORAGE_OBJECT_MISSING",
                               message="El archivo no está en el almacenamiento",
                               status_code=500) from exc
        except OSError as exc:
            raise StorageError(f"No se pudo leer: {exc.strerror}") from exc

    def exists(self, key: str) -> bool:
        try:
            return self._resolve(key).is_file()
        except StorageError:
            return False

    def delete(self, key: str) -> None:
        try:
            self._resolve(key).unlink(missing_ok=True)
        except OSError as exc:
            raise StorageError(f"No se pudo borrar: {exc.strerror}") from exc

    def size(self, key: str) -> int:
        target = self._resolve(key)
        if not target.is_file():
            raise StorageError(code="STORAGE_OBJECT_MISSING",
                               message="El archivo no está en el almacenamiento", status_code=500)
        return target.stat().st_size

    def health(self) -> dict[str, object]:
        """Estado del almacenamiento. **No expone la ruta**: solo si funciona."""
        probe = self.root / f".health-{secrets.token_hex(4)}"
        try:
            probe.write_bytes(b"ok")
            readable = probe.read_bytes() == b"ok"
            probe.unlink(missing_ok=True)
            return {"provider": self.name, "writable": True, "readable": readable}
        except OSError as exc:
            return {"provider": self.name, "writable": False, "error": exc.strerror}


class S3CompatibleStorageProvider(DocumentStorageProvider):
    """Proveedor para cualquier servicio con API compatible con S3.

    Se habla el protocolo, no un fabricante: el `endpoint_url` es obligatorio y
    configurable, de modo que sirve igual para MinIO, Ceph o el propio S3
    (FR-046-032). Las credenciales llegan por entorno y **nunca** se guardan en
    base, ni en el frontend, ni se escriben en un registro (FR-046-035).

    El cliente se construye de forma perezosa: una instalación que use el
    sistema de archivos no necesita tener instalado `boto3`.
    """

    name = "S3_COMPATIBLE"

    def __init__(self, *, bucket: str, endpoint_url: str, region: str | None = None,
                 prefix: str = "", client: object | None = None) -> None:
        if not bucket or not endpoint_url:
            raise StorageError(code="STORAGE_MISCONFIGURED",
                               message="El almacenamiento compatible con S3 exige bucket y endpoint",
                               status_code=500)
        self.bucket = bucket
        self.endpoint_url = endpoint_url
        self.region = region
        self.prefix = prefix.strip("/")
        self._client = client

    # -- cliente -----------------------------------------------------------
    @property
    def client(self):  # noqa: ANN201 — el tipo lo aporta boto3, opcional
        if self._client is None:
            try:
                import boto3
            except ImportError as exc:  # pragma: no cover — depende del entorno
                raise StorageError(
                    code="STORAGE_MISCONFIGURED",
                    message="El proveedor compatible con S3 requiere el paquete boto3",
                    status_code=500) from exc
            self._client = boto3.client(
                "s3", endpoint_url=self.endpoint_url, region_name=self.region)
        return self._client

    def _object_key(self, key: str) -> str:
        if not key or key.startswith("/") or ".." in key.split("/"):
            raise StorageError(code="STORAGE_INVALID_KEY",
                               message="Clave de almacenamiento inválida", status_code=422)
        return f"{self.prefix}/{key}" if self.prefix else key

    # -- contrato ----------------------------------------------------------
    def put(self, key: str, stream: BinaryIO) -> tuple[int, str]:
        """Sube el objeto calculando tamaño y hash **al escribir**.

        Se lee a memoria por trozos hasta el búfer y se envía en una sola
        operación: el objeto aparece completo o no aparece, nunca a medias.
        """
        digest = hashlib.sha256()
        size = 0
        buffer = io.BytesIO()
        for chunk in iter(lambda: stream.read(CHUNK), b""):
            digest.update(chunk)
            size += len(chunk)
            buffer.write(chunk)
        buffer.seek(0)
        try:
            self.client.put_object(Bucket=self.bucket, Key=self._object_key(key),
                                   Body=buffer)
        except Exception as exc:  # noqa: BLE001 — la familia de errores la define boto3
            raise StorageError(f"No se pudo escribir en el almacenamiento: {exc}") from exc
        return size, digest.hexdigest()

    def open(self, key: str) -> BinaryIO:
        try:
            response = self.client.get_object(Bucket=self.bucket,
                                              Key=self._object_key(key))
        except Exception as exc:  # noqa: BLE001
            raise StorageError(code="STORAGE_OBJECT_MISSING",
                               message="El archivo no está en el almacenamiento",
                               status_code=500) from exc
        return response["Body"]

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=self._object_key(key))
            return True
        except StorageError:
            return False
        except Exception:  # noqa: BLE001
            return False

    def delete(self, key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=self._object_key(key))
        except Exception as exc:  # noqa: BLE001
            raise StorageError(f"No se pudo borrar: {exc}") from exc

    def size(self, key: str) -> int:
        try:
            head = self.client.head_object(Bucket=self.bucket, Key=self._object_key(key))
        except Exception as exc:  # noqa: BLE001
            raise StorageError(code="STORAGE_OBJECT_MISSING",
                               message="El archivo no está en el almacenamiento",
                               status_code=500) from exc
        return int(head["ContentLength"])

    def health(self) -> dict[str, object]:
        """Estado del depósito. **No expone endpoint, bucket ni credenciales.**"""
        probe = f".health-{secrets.token_hex(4)}"
        try:
            self.put(probe, io.BytesIO(b"ok"))
            readable = self.open(probe).read() == b"ok"
            self.delete(probe)
            return {"provider": self.name, "writable": True, "readable": readable}
        except StorageError as exc:
            return {"provider": self.name, "writable": False, "error": exc.message}


_provider: DocumentStorageProvider | None = None


def get_storage() -> DocumentStorageProvider:
    """Proveedor activo, según configuración.

    El dominio nunca elige: pregunta aquí. Cambiar de sistema de archivos a un
    servicio compatible con S3 no exige tocar un solo servicio de negocio
    (FR-046-030), solo la configuración de la instalación.
    """
    global _provider
    if _provider is None:
        bucket = os.environ.get("KONTROL_S3_BUCKET")
        endpoint = os.environ.get("KONTROL_S3_ENDPOINT")
        if bucket and endpoint:
            _provider = S3CompatibleStorageProvider(
                bucket=bucket, endpoint_url=endpoint,
                region=os.environ.get("KONTROL_S3_REGION"),
                prefix=os.environ.get("KONTROL_S3_PREFIX", ""))
        else:
            from app.core.config import get_settings

            root = Path(get_settings().storage_path) / "documents"
            _provider = FilesystemStorageProvider(root)
    return _provider


def set_storage(provider: DocumentStorageProvider | None) -> None:
    """Sustituye el proveedor. Para pruebas de fallo, no para producción."""
    global _provider
    _provider = provider
