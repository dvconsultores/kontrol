"""El demonio clamd real para certificar el contrato del servicio de análisis, sin privilegios (Spec 046 · OBS-09, opción B).

En producción el análisis antimalware lo hace el servicio `clamd` de `compose.yaml` (imagen `Dockerfile.clamd` =
`clamav/clamav:1.4.3` + `deploy/clamd/clamd.conf`) y el backend le transmite cada documento por INSTREAM. Este módulo
certifica ese contrato en el equipo de QA con el **mismo demonio** (paquete oficial `clamav-daemon` de Debian, descargado con
`apt-get download`, verificado con la suma SHA256 firmada de apt y extraído con `dpkg-deb -x` al prefijo de `qa/clamav_qa.py`)
y la **misma configuración** del despliegue adaptada al prefijo (ruta de firmas, 127.0.0.1 y un puerto de QA; los límites de
tamaño se conservan tal cual). Las sondas usan el adaptador real del producto (`ClamdScanner`): CLEAN, EICAR, varios
trozos, el máximo documental de KONTROL, demonio caído, tiempo agotado, error de protocolo, respuesta truncada y flujo
interrumpido deben traducirse exactamente como el producto los traduce. Además verifica, de forma estática, el contrato de
imagen y composición (puerto no publicado, sin almacén documental en clamd, backend sin firmas, límites ≥ 50 MiB).

Órdenes:

    python qa/clamd_qa.py provisionar [--home …]           deja clamd en el prefijo (idempotente; exige firmas de clamav_qa)
    python qa/clamd_qa.py certificar [--puerto N]          arranca el demonio, ejecuta las sondas y las comprobaciones
                                                           estáticas e imprime el informe JSON; sale 1 si algo falla
    python qa/clamd_qa.py estatico                         solo el contrato de imagen y composición (sin demonio)

Lo que no está en este equipo se declara, no se simula: sin `docker`/`podman` la construcción de la imagen y el arranque de
la composición quedan `COMPOSE_RUNTIME_UNAVAILABLE` en el informe.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import clamav_qa
import yaml  # type: ignore[import-untyped]

RAIZ = Path(__file__).resolve().parent.parent
BACKEND = RAIZ / "resources" / "backend"
CONFIGURACION_DEL_DESPLIEGUE = RAIZ / "deploy" / "clamd" / "clamd.conf"
PAQUETE_DEMONIO = "clamav-daemon"
PUERTO_QA = 33100
#: Máximo documental de KONTROL (`GLOBAL_MAX_SIZE` en `documents/service.py`); se contrasta por texto, no se importa el servicio.
MAXIMO_DOCUMENTAL = 50 * 1024 * 1024
TROZO = 64 * 1024
#: Directivas de la configuración del despliegue que el prefijo de usuario sustituye (el resto, límites incluidos, se conserva).
DIRECTIVAS_LOCALES = ("User", "LocalSocket", "TCPSocket", "TCPAddr", "DatabaseDirectory", "LogFile", "PidFile")
VERSION = re.compile(r"^ClamAV (\S+?)/(\d+)/(.+)$")

sys.path.insert(0, str(BACKEND))


class DemonioNoListo(RuntimeError):
    """El demonio no se pudo provisionar, arrancar o certificar; el mensaje dice exactamente qué falló."""


# ------------------------------------------------------------------ provisión

def rutas_del_demonio(home: Path | None = None) -> clamav_qa.Rutas:
    return clamav_qa.Rutas(home or clamav_qa.home_por_defecto())


def clamd_real(rutas: clamav_qa.Rutas) -> Path:
    return rutas.prefijo / "usr" / "sbin" / "clamd"


def descargar_demonio(destino: Path) -> Path:
    """`apt-get download clamav-daemon` (sin root) y verificación contra la suma SHA256 firmada de apt."""
    destino.mkdir(parents=True, exist_ok=True)
    resultado = clamav_qa._correr(["apt-get", "download", PAQUETE_DEMONIO], cwd=destino)
    if resultado.returncode != 0:
        raise DemonioNoListo(f"apt-get download {PAQUETE_DEMONIO} falló: {resultado.stderr.strip()[-300:]}")
    candidatos = sorted(destino.glob(f"{PAQUETE_DEMONIO}_*.deb"))
    if not candidatos:
        raise DemonioNoListo(f"no se descargó {PAQUETE_DEMONIO}")
    fichero = candidatos[-1]
    if hashlib.sha256(fichero.read_bytes()).hexdigest() != clamav_qa._suma_esperada(PAQUETE_DEMONIO):
        fichero.unlink()
        raise DemonioNoListo(f"la suma SHA256 de {fichero.name} no coincide con la de apt: descartado")
    return fichero


def extraer_demonio(fichero: Path, prefijo: Path) -> None:
    resultado = clamav_qa._correr(["dpkg-deb", "-x", str(fichero), str(prefijo)])
    if resultado.returncode != 0:
        raise DemonioNoListo(f"dpkg-deb -x {fichero.name} falló: {resultado.stderr.strip()[-200:]}")


def escribir_envoltorio(rutas: clamav_qa.Rutas) -> Path:
    """`bin/clamd` fija `LD_LIBRARY_PATH` al prefijo y ejecuta el demonio real."""
    real = clamd_real(rutas)
    if not real.exists():
        raise DemonioNoListo("el paquete no trae clamd")
    rutas.bin.mkdir(parents=True, exist_ok=True)
    envoltorio = rutas.bin / "clamd"
    envoltorio.write_text("#!/bin/sh\n"
                          f'export LD_LIBRARY_PATH="{rutas.lib}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"\n'
                          f'exec "{real}" "$@"\n', encoding="utf-8")
    envoltorio.chmod(envoltorio.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return envoltorio


def provisionar(home: Path | None = None, *, descargar: Callable[[Path], Path] = descargar_demonio,
                extraer: Callable[[Path, Path], None] = extraer_demonio) -> clamav_qa.Rutas:
    """Deja `clamd` junto al `clamscan` y las firmas de `clamav_qa`. Idempotente: con el binario presente no descarga."""
    rutas = rutas_del_demonio(home)
    clamav_qa.provisionar(rutas.home)  # motor y firmas: la única puerta para «el QA tiene analizador»
    if not clamd_real(rutas).exists():
        extraer(descargar(rutas.deb), rutas.prefijo)
    escribir_envoltorio(rutas)
    return rutas


# ------------------------------------------------------------------ configuración y demonio

def configuracion_local(rutas: clamav_qa.Rutas, puerto: int, carpeta: Path,
                        despliegue: Path = CONFIGURACION_DEL_DESPLIEGUE) -> Path:
    """La configuración del despliegue, con las directivas locales sustituidas; los límites de tamaño no se tocan."""
    lineas = [linea for linea in despliegue.read_text(encoding="utf-8").splitlines()
              if not linea.split("#", 1)[0].strip().startswith(DIRECTIVAS_LOCALES)]
    lineas += ["TCPAddr 127.0.0.1", f"TCPSocket {puerto}", f"DatabaseDirectory {rutas.db}",
               f"LogFile {carpeta / 'clamd.log'}", f"PidFile {carpeta / 'clamd.pid'}"]
    destino = carpeta / "clamd.conf"
    destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return destino


def limites(configuracion: Path = CONFIGURACION_DEL_DESPLIEGUE) -> dict[str, int]:
    """`StreamMaxLength`, `MaxFileSize`, `MaxScanSize` en bytes, tal como los declara la configuración."""
    valores: dict[str, int] = {}
    for linea in configuracion.read_text(encoding="utf-8").splitlines():
        partes = linea.split("#", 1)[0].split()
        if len(partes) == 2 and partes[0] in ("StreamMaxLength", "MaxFileSize", "MaxScanSize"):
            numero, unidad = re.fullmatch(r"(\d+)([KMG]?)", partes[1]).groups()  # type: ignore[union-attr]
            valores[partes[0]] = int(numero) * {"": 1, "K": 1024, "M": 1024 ** 2, "G": 1024 ** 3}[unidad]
    return valores


def orden(puerto: int, mandato: bytes, host: str = "127.0.0.1", timeout: float = 10.0) -> str:
    """Una orden `z<MANDATO>\\0` al demonio; devuelve la respuesta sin el terminador."""
    with socket.create_connection((host, puerto), timeout=timeout) as conexion:
        conexion.sendall(b"z" + mandato + b"\0")
        acumulado = b""
        while b"\0" not in acumulado:
            leido = conexion.recv(4096)
            if not leido:
                break
            acumulado += leido
    return acumulado.split(b"\0", 1)[0].decode("utf-8", errors="replace")


def version(texto: str) -> dict[str, str]:
    """`ClamAV 1.4.3/28153/Wed Oct 14 08:24:15 2026` → motor, versión de la base diaria y su fecha."""
    coincidencia = VERSION.match(texto.strip())
    if not coincidencia:
        raise DemonioNoListo(f"VERSION irreconocible: {texto[:80]!r}")
    return {"motor": coincidencia.group(1), "firmas_version": coincidencia.group(2), "firmas_fecha": coincidencia.group(3)}


class Demonio:
    """Arranca `clamd` en primer plano sobre el prefijo, espera a que responda `PONG` y lo detiene al salir, pase lo que pase."""

    def __init__(self, rutas: clamav_qa.Rutas, puerto: int = PUERTO_QA, *, limite_s: float = 300.0,
                 despliegue: Path = CONFIGURACION_DEL_DESPLIEGUE) -> None:
        self.rutas, self.puerto, self.limite_s, self.despliegue = rutas, puerto, limite_s, despliegue
        self.carpeta = Path(tempfile.mkdtemp(prefix="kontrol-qa-clamd-"))
        self.proceso: subprocess.Popen[bytes] | None = None
        self.arranque_s = 0.0

    def __enter__(self) -> Demonio:
        configuracion = configuracion_local(self.rutas, self.puerto, self.carpeta, self.despliegue)
        with (self.carpeta / "clamd.out").open("wb") as salida:
            self.proceso = subprocess.Popen([str(self.rutas.bin / "clamd"), f"--config-file={configuracion}"],
                                            stdout=salida, stderr=subprocess.STDOUT)
        inicio = time.monotonic()
        final = inicio + self.limite_s
        while time.monotonic() < final:
            if self.proceso.poll() is not None:
                salida_del_demonio = (self.carpeta / "clamd.out").read_text(errors="replace")[-300:]
                self._limpiar()
                raise DemonioNoListo(f"clamd terminó al arrancar con código {self.proceso.returncode}: {salida_del_demonio}")
            try:
                if orden(self.puerto, b"PING", timeout=2.0) == "PONG":
                    self.arranque_s = round(time.monotonic() - inicio, 1)
                    return self
            except OSError:
                time.sleep(0.25)
        self._limpiar()
        raise DemonioNoListo(f"clamd no respondió PONG en {self.limite_s:.0f} s")

    def parar(self) -> None:
        if self.proceso is not None and self.proceso.poll() is None:
            self.proceso.terminate()
            try:
                self.proceso.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.proceso.kill()
                self.proceso.wait(timeout=30)

    def _limpiar(self) -> None:
        """Detiene el demonio (si sigue) y elimina la carpeta propia: también cuando el arranque falla."""
        self.parar()
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def __exit__(self, *_: object) -> None:
        self._limpiar()


# ------------------------------------------------------------------ servidores de fallo (puros, en proceso)

class ServidorDeFallo:
    """Un oyente TCP que habla INSTREAM hasta donde hace falta y luego se comporta mal de una forma concreta, para probar
    que el adaptador falla cerrado: `cuelga` (consume el flujo y no responde), `basura` (responde algo que no es del
    protocolo), `truncada` (cierra a mitad de la respuesta), `corta_el_flujo` (cierra tras el primer trozo) y `error`
    (responde el ERROR de límite del demonio)."""

    def __init__(self, modo: str) -> None:
        self.modo = modo
        self.oyente = socket.socket()
        self.oyente.bind(("127.0.0.1", 0))
        self.oyente.listen(4)
        self.puerto = self.oyente.getsockname()[1]
        self.recibido = b""
        self._hilo = threading.Thread(target=self._atender, daemon=True)

    @staticmethod
    def _exacto(conexion: socket.socket, n: int) -> bytes:
        datos = b""
        while len(datos) < n:
            leido = conexion.recv(n - len(datos))
            if not leido:
                raise ConnectionError("el cliente cerró a mitad del flujo")
            datos += leido
        return datos

    def _consumir(self, conexion: socket.socket, *, trozos: int | None = None) -> None:
        """Lee la orden `zINSTREAM\0` y los trozos (longitud + datos) hasta el de longitud cero, o hasta `trozos`."""
        orden_recibida = b""
        while not orden_recibida.endswith(b"\0"):
            orden_recibida += self._exacto(conexion, 1)
        self.recibido += orden_recibida
        leidos = 0
        while trozos is None or leidos < trozos:
            (largo,) = struct.unpack("!I", self._exacto(conexion, 4))
            if largo == 0:
                return
            self.recibido += self._exacto(conexion, largo)
            leidos += 1

    def _atender(self) -> None:
        try:
            conexion, _ = self.oyente.accept()
        except OSError:
            return
        with conexion:
            conexion.settimeout(30.0)
            try:
                if self.modo == "corta_el_flujo":
                    self._consumir(conexion, trozos=1)
                    conexion.shutdown(socket.SHUT_RDWR)
                    return
                self._consumir(conexion)
                if self.modo == "cuelga":
                    conexion.recv(1)  # no responde nunca; vuelve cuando el cliente, agotado su tiempo, cierra
                elif self.modo == "basura":
                    conexion.sendall(b"<<<mensaje que no es del protocolo>>>\0")
                elif self.modo == "truncada":
                    conexion.sendall(b"stream: O")
                elif self.modo == "error":
                    conexion.sendall(b"INSTREAM size limit exceeded. ERROR\0")
            except (OSError, ConnectionError):
                return

    def __enter__(self) -> ServidorDeFallo:
        self._hilo.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.oyente.close()
        self._hilo.join(timeout=60)


# ------------------------------------------------------------------ sondas

def _resultado(scanner: Any, datos: bytes, carpeta: Path, nombre: str) -> dict[str, Any]:
    fichero = carpeta / nombre
    fichero.write_bytes(datos)
    inicio = time.monotonic()
    resultado = scanner.scan(str(fichero))
    return {"result": resultado.result, "signature": resultado.signature, "details": resultado.details,
            "bytes": len(datos), "segundos": round(time.monotonic() - inicio, 3)}


def sondas(puerto: int, host: str = "127.0.0.1") -> dict[str, Any]:
    """CLEAN, INFECTED, varios trozos, el máximo documental y las siete formas de fallo, con el adaptador del producto."""
    from app.modules.documents import scanning

    informe: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="kontrol-qa-clamd-sondas-") as temporal:
        carpeta = Path(temporal)
        scanner = scanning.ClamdScanner(host=host, port=puerto)
        informe["limpio"] = _resultado(scanner, clamav_qa.PDF_LIMPIO, carpeta, "limpio.pdf")
        informe["eicar"] = _resultado(scanner, clamav_qa.EICAR.encode("ascii"), carpeta, "eicar.txt")
        informe["varios_trozos"] = _resultado(scanner, os.urandom(3 * 1024 * 1024), carpeta, "tres-mib.bin")
        informe["maximo_documental"] = _resultado(scanner, os.urandom(MAXIMO_DOCUMENTAL), carpeta, "maximo.bin")
        informe["maximo_mas_uno"] = _resultado(scanner, os.urandom(MAXIMO_DOCUMENTAL + 1), carpeta, "maximo-mas-uno.bin")
        por_encima = limites()["StreamMaxLength"] + 1
        informe["por_encima_del_limite_del_demonio"] = _resultado(scanner, os.urandom(por_encima), carpeta, "excede.bin")
        cerrado = socket.socket()
        cerrado.bind(("127.0.0.1", 0))
        libre = cerrado.getsockname()[1]
        cerrado.close()
        informe["demonio_caido"] = _resultado(scanning.ClamdScanner(host=host, port=libre), clamav_qa.PDF_LIMPIO, carpeta, "caido.pdf")
        for modo, clave in (("cuelga", "tiempo_agotado"), ("basura", "error_de_protocolo"), ("truncada", "respuesta_truncada"),
                            ("corta_el_flujo", "flujo_interrumpido"), ("error", "error_del_demonio")):
            with ServidorDeFallo(modo) as servidor:
                sonda = scanning.ClamdScanner(host="127.0.0.1", port=servidor.puerto, timeout=2)
                informe[clave] = _resultado(sonda, os.urandom(3 * TROZO), carpeta, f"{modo}.bin")
                informe[clave]["ruta_enviada_al_demonio"] = str(carpeta).encode() in servidor.recibido
    return informe


def veredicto_de_sondas(informe: dict[str, Any]) -> dict[str, bool]:
    def es(clave: str, resultado: str, motivo: str | None = None) -> bool:
        sonda = informe[clave]
        return sonda["result"] == resultado and (motivo is None or (sonda["details"] or {}).get("reason") == motivo)
    return {
        "CLEAN_RESULT": es("limpio", "CLEAN"),
        "INFECTED_RESULT": es("eicar", "INFECTED") and bool(informe["eicar"]["signature"]),
        "MULTI_CHUNK_STREAM": es("varios_trozos", "CLEAN"),
        "MAX_DOCUMENT_SIZE_CONTRACT": es("maximo_documental", "CLEAN") and es("maximo_mas_uno", "CLEAN"),
        "DAEMON_LIMIT_FAIL_CLOSED": es("por_encima_del_limite_del_demonio", "SCAN_FAILED", "scanner_error"),
        "SCANNER_UNAVAILABLE_FAIL_CLOSED": es("demonio_caido", "SCAN_FAILED", "connection_refused"),
        "SCANNER_TIMEOUT_FAIL_CLOSED": es("tiempo_agotado", "SCAN_FAILED", "timeout"),
        "PROTOCOL_ERROR_FAIL_CLOSED": es("error_de_protocolo", "SCAN_FAILED", "protocol_error"),
        "MALFORMED_RESPONSE_FAIL_CLOSED": es("respuesta_truncada", "SCAN_FAILED", "truncated_response"),
        "STREAM_INTERRUPTED_FAIL_CLOSED": informe["flujo_interrumpido"]["result"] == "SCAN_FAILED",
        "DAEMON_ERROR_FAIL_CLOSED": es("error_del_demonio", "SCAN_FAILED", "scanner_error"),
        "SHARED_FILE_PATH_REQUIRED": any(informe[c]["ruta_enviada_al_demonio"] for c in
                                         ("error_de_protocolo", "respuesta_truncada", "flujo_interrumpido", "error_del_demonio")),
    }


# ------------------------------------------------------------------ contrato de imagen y composición (estático)

def comprobaciones_estaticas(raiz: Path = RAIZ) -> dict[str, Any]:
    composicion = yaml.safe_load((raiz / "compose.yaml").read_text(encoding="utf-8"))
    servicios = composicion["services"]
    clamd = servicios.get("clamd", {})
    backend = servicios["backend"]
    volumenes_clamd = [str(v) for v in clamd.get("volumes", [])]
    entorno = backend.get("environment", {})
    dockerfile_backend = (raiz / "Dockerfile.backend").read_text(encoding="utf-8")
    dockerfile_clamd = (raiz / "Dockerfile.clamd").read_text(encoding="utf-8")
    servicio_py = (BACKEND / "app" / "modules" / "documents" / "service.py").read_text(encoding="utf-8")
    scanning_py = (BACKEND / "app" / "modules" / "documents" / "scanning.py").read_text(encoding="utf-8")
    config_py = (BACKEND / "app" / "core" / "config.py").read_text(encoding="utf-8")
    tope = limites()
    return {
        "CLAMD_SERVICE_PRESENT": bool(clamd),
        "CLAMD_IMAGE": clamd.get("image"),
        "CLAMD_BASE_IMAGE_PINNED": "FROM clamav/clamav:1.4.3" in dockerfile_clamd,
        "CLAMD_HOST_PORT_PUBLISHED": "ports" in clamd,
        "CLAMD_INTERNAL_ONLY": "ports" not in clamd and clamd.get("networks") == ["kontrol-net"],
        "DOCUMENT_STORAGE_MOUNTED_IN_CLAMD": any("storage" in v or "backups" in v or "license" in v for v in volumenes_clamd),
        "CLAMD_VOLUMES": volumenes_clamd,
        "CLAMD_HEALTHCHECK_PRESENT": "healthcheck" in clamd,
        "CLAMD_HEALTHCHECK_MEANINGFUL": "PING" in " ".join(clamd.get("healthcheck", {}).get("test", [])) and "PONG" in " ".join(clamd.get("healthcheck", {}).get("test", [])),
        "FRESHCLAM_IN_SCANNER_DOMAIN": clamd.get("environment", {}).get("CLAMAV_NO_FRESHCLAMD") == "false",
        "BACKEND_SELECTS_CLAMD_EXPLICITLY": entorno.get("KONTROL_DOCUMENT_SCANNER") == "clamd" and entorno.get("KONTROL_CLAMD_HOST") == "clamd",
        "BACKEND_IMAGE_HAS_CLAMSCAN": "clam" in dockerfile_backend.lower(),
        "BACKEND_IMAGE_HAS_SIGNATURE_DATABASE": "freshclam" in dockerfile_backend.lower() or "/var/lib/clamav" in dockerfile_backend,
        "BACKEND_MOUNTS_SIGNATURES": any("clamav" in str(v) for v in backend.get("volumes", [])),
        "STREAM_MAX_LENGTH_BYTES": tope.get("StreamMaxLength"),
        "MAX_FILE_SIZE_BYTES": tope.get("MaxFileSize"),
        "SIZE_CONTRACT_OK": tope.get("StreamMaxLength", 0) >= MAXIMO_DOCUMENTAL and tope.get("MaxFileSize", 0) >= MAXIMO_DOCUMENTAL
                            and tope.get("MaxScanSize", 0) >= tope.get("MaxFileSize", 0),
        "ALERT_EXCEEDS_MAX": any(linea.split() == ["AlertExceedsMax", "yes"] for linea in CONFIGURACION_DEL_DESPLIEGUE.read_text(encoding="utf-8").splitlines()),
        "KONTROL_MAX_DECLARED": f"GLOBAL_MAX_SIZE = {MAXIMO_DOCUMENTAL // (1024 * 1024)} * 1024 * 1024" in servicio_py,
        "IMPLICIT_FALLBACK": "ClamAVScanner()" in scanning_py.split("class ClamdScanner", 1)[1].split("class DisabledScanner", 1)[0],
        "SCANNER_CHOICE_VALIDATED": 'pattern="^(clamscan|clamd)$"' in config_py,
    }


def runtime_de_contenedores() -> dict[str, Any]:
    for nombre in ("docker", "podman", "nerdctl"):
        ruta = shutil.which(nombre)
        if ruta:
            return {"disponible": True, "runtime": nombre}
    return {"disponible": False, "runtime": None, "estado": "COMPOSE_RUNTIME_UNAVAILABLE"}


# ------------------------------------------------------------------ certificación

def certificar(home: Path | None = None, puerto: int = PUERTO_QA) -> dict[str, Any]:
    rutas = provisionar(home)
    informe: dict[str, Any] = {"estatico": comprobaciones_estaticas(), "runtime": runtime_de_contenedores()}
    with Demonio(rutas, puerto) as demonio:
        informe["demonio"] = {"arranque_s": demonio.arranque_s, "ping": orden(puerto, b"PING"), **version(orden(puerto, b"VERSION"))}
        informe["sondas"] = sondas(puerto)
    informe["veredicto"] = veredicto_de_sondas(informe["sondas"])
    return informe


def aprobado(informe: dict[str, Any]) -> bool:
    estatico, veredicto = informe["estatico"], informe["veredicto"]
    exigidos_verdaderos = ("CLAMD_SERVICE_PRESENT", "CLAMD_BASE_IMAGE_PINNED", "CLAMD_INTERNAL_ONLY", "CLAMD_HEALTHCHECK_PRESENT",
                           "CLAMD_HEALTHCHECK_MEANINGFUL", "FRESHCLAM_IN_SCANNER_DOMAIN", "BACKEND_SELECTS_CLAMD_EXPLICITLY",
                           "SIZE_CONTRACT_OK", "ALERT_EXCEEDS_MAX", "KONTROL_MAX_DECLARED", "SCANNER_CHOICE_VALIDATED")
    exigidos_falsos = ("CLAMD_HOST_PORT_PUBLISHED", "DOCUMENT_STORAGE_MOUNTED_IN_CLAMD", "BACKEND_IMAGE_HAS_CLAMSCAN",
                       "BACKEND_IMAGE_HAS_SIGNATURE_DATABASE", "BACKEND_MOUNTS_SIGNATURES", "IMPLICIT_FALLBACK")
    return (all(estatico[c] is True for c in exigidos_verdaderos) and all(estatico[c] is False for c in exigidos_falsos)
            and all(v is True for c, v in veredicto.items() if c != "SHARED_FILE_PATH_REQUIRED")
            and veredicto["SHARED_FILE_PATH_REQUIRED"] is False and informe["demonio"]["ping"] == "PONG")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="clamd real para certificar el servicio de análisis (Spec 046 · OBS-09).")
    parser.add_argument("accion", choices=("provisionar", "certificar", "estatico"))
    parser.add_argument("--home", help="prefijo de usuario (defecto: el de qa/clamav_qa.py)")
    parser.add_argument("--puerto", type=int, default=PUERTO_QA, help="puerto TCP local del demonio de QA")
    args = parser.parse_args(argv)
    home = Path(args.home) if args.home else None
    try:
        if args.accion == "provisionar":
            rutas = provisionar(home)
            print(json.dumps({"clamd": str(rutas.bin / "clamd"), "db": str(rutas.db)}, ensure_ascii=False))
            return 0
        if args.accion == "estatico":
            informe = {"estatico": comprobaciones_estaticas(), "runtime": runtime_de_contenedores()}
            print(json.dumps(informe, ensure_ascii=False, indent=1))
            return 0
        informe = certificar(home, args.puerto)
    except (DemonioNoListo, clamav_qa.AnalizadorNoListo) as exc:
        print(f"[clamd-qa] NO LISTO: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(informe, ensure_ascii=False, indent=1, default=str))
    return 0 if aprobado(informe) else 1


if __name__ == "__main__":
    sys.exit(main())
