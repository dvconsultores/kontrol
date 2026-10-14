"""ClamAV real para el QA canónico, sin privilegios (Spec 046 · ENTORNO-SIN-CLAMSCAN, decisión A + A2 de la dueña).

El producto exige un analizador real por defecto y falla cerrado sin él (`SCAN_FAILED`, nunca `CLEAN`; FR-046-072).
Este módulo deja ese analizador disponible para las certificaciones sin `sudo`: descarga los paquetes **oficiales**
de Debian con `apt-get download` (sin instalar), contrasta sus sumas SHA256 con los metadatos firmados de `apt`,
los extrae con `dpkg-deb -x` a un prefijo de usuario y obtiene la base de firmas con `freshclam` en un directorio
propio. Nada se escribe fuera de ese prefijo, nada entra en Git y el producto no cambia: la pila recibe las rutas por
`KONTROL_CLAMSCAN_PATH` y `KONTROL_CLAMAV_DB`, que es como ya las lee `app.modules.documents.scanning`.

Órdenes:

    python qa/clamav_qa.py provisionar [--refrescar]   asegura binario y firmas (idempotente; con caché válida no descarga)
    python qa/clamav_qa.py preflight                    QAC-01…08: arranque, versión, firmas, limpio CLEAN, EICAR INFECTED,
                                                        fallo distinguible de CLEAN; imprime motor y base; sale 1 si algo falla
    python qa/clamav_qa.py entorno                      tras el preflight, imprime las dos `export` para la shell

El prefijo es `KONTROL_QA_CLAMAV_HOME` o `${XDG_CACHE_HOME:-~/.cache}/kontrol-qa/clamav/1.4` (fuera del repositorio).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

#: Versión semántica certificada por la Spec 046 (closeout §7: ClamAV 1.4.3). Se acepta 1.4.x.
VERSION_COMPATIBLE = "1.4."
#: Paquetes oficiales de Debian que se descargan sin instalar.
PAQUETES = ("clamav", "libclamav12", "clamav-freshclam", "clamav-base")
ARQUITECTURA = "x86_64-linux-gnu"
#: Fixture estándar de los antivirus: no es malware. Se ensambla por partes para que este fichero no sea una «muestra».
EICAR = "X5O!P%@AP[4\\PZX54(P^)7CC)7}$" + "EICAR-STANDARD-ANTIVIRUS-TEST-FILE" + "!$H+H*"
PDF_LIMPIO = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n%%EOF\n"
BASES = ("main", "daily", "bytecode")


class AnalizadorNoListo(RuntimeError):
    """El analizador no puede certificar: se dice por qué y no se sigue como si sí."""


@dataclass(frozen=True)
class Rutas:
    home: Path

    @property
    def deb(self) -> Path:
        return self.home / "deb"

    @property
    def prefijo(self) -> Path:
        return self.home / "prefix"

    @property
    def bin(self) -> Path:
        return self.home / "bin"

    @property
    def db(self) -> Path:
        return self.home / "db"

    @property
    def clamscan(self) -> Path:
        return self.bin / "clamscan"

    @property
    def lib(self) -> Path:
        return self.prefijo / "usr" / "lib" / ARQUITECTURA


@dataclass(frozen=True)
class Estado:
    motor: str
    bases: dict[str, dict[str, str]]
    clamscan: str
    db: str


def home_por_defecto(entorno: Mapping[str, str] | None = None) -> Path:
    entorno = os.environ if entorno is None else entorno
    if entorno.get("KONTROL_QA_CLAMAV_HOME"):
        return Path(entorno["KONTROL_QA_CLAMAV_HOME"])
    cache = Path(entorno.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return cache / "kontrol-qa" / "clamav" / VERSION_COMPATIBLE.rstrip(".")


def _correr(orden: list[str], *, cwd: Path | None = None, entorno: Mapping[str, str] | None = None,
            timeout: int = 900) -> subprocess.CompletedProcess[str]:
    return subprocess.run(orden, cwd=cwd, env=dict(entorno) if entorno else None, capture_output=True, text=True,
                          timeout=timeout, check=False)


# ------------------------------------------------------------------ provisión
def _suma_esperada(paquete: str) -> str:
    salida = _correr(["apt-cache", "show", paquete]).stdout
    coincidencia = re.search(r"^SHA256:\s*([0-9a-f]{64})", salida, re.M)
    if not coincidencia:
        raise AnalizadorNoListo(f"apt no publica la suma SHA256 de {paquete}: no se descarga a ciegas")
    return coincidencia.group(1)


def descargar_paquetes(destino: Path) -> list[Path]:
    """`apt-get download` (sin root) y verificación de cada `.deb` contra la suma firmada de apt."""
    destino.mkdir(parents=True, exist_ok=True)
    resultado = _correr(["apt-get", "download", *PAQUETES], cwd=destino)
    if resultado.returncode != 0:
        raise AnalizadorNoListo(f"apt-get download falló: {resultado.stderr.strip()[-300:]}")
    ficheros: list[Path] = []
    for paquete in PAQUETES:
        candidatos = sorted(destino.glob(f"{paquete}_*.deb"))
        if not candidatos:
            raise AnalizadorNoListo(f"no se descargó {paquete}")
        fichero = candidatos[-1]
        real = hashlib.sha256(fichero.read_bytes()).hexdigest()
        if real != _suma_esperada(paquete):
            fichero.unlink()
            raise AnalizadorNoListo(f"la suma SHA256 de {fichero.name} no coincide con la de apt: descartado")
        ficheros.append(fichero)
    return ficheros


def extraer_paquetes(ficheros: list[Path], prefijo: Path) -> None:
    prefijo.mkdir(parents=True, exist_ok=True)
    for fichero in ficheros:
        resultado = _correr(["dpkg-deb", "-x", str(fichero), str(prefijo)])
        if resultado.returncode != 0:
            raise AnalizadorNoListo(f"dpkg-deb -x {fichero.name} falló: {resultado.stderr.strip()[-200:]}")


def escribir_envoltorios(rutas: Rutas) -> None:
    """`bin/<programa>` fija `LD_LIBRARY_PATH` al prefijo y ejecuta el binario real: el producto solo conoce la ruta."""
    rutas.bin.mkdir(parents=True, exist_ok=True)
    for programa in ("clamscan", "freshclam", "sigtool"):
        real = rutas.prefijo / "usr" / "bin" / programa
        if not real.exists():
            raise AnalizadorNoListo(f"el paquete no trae {programa}")
        envoltorio = rutas.bin / programa
        envoltorio.write_text("#!/bin/sh\n"
                              f'export LD_LIBRARY_PATH="{rutas.lib}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"\n'
                              f'exec "{real}" "$@"\n', encoding="utf-8")
        envoltorio.chmod(envoltorio.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def motor_disponible(rutas: Rutas) -> str | None:
    """La versión que imprime el envoltorio, o `None` si no arranca o no es compatible."""
    if not rutas.clamscan.exists():
        return None
    resultado = _correr([str(rutas.clamscan), "--version"], timeout=60)
    version = resultado.stdout.strip().replace("ClamAV ", "", 1) if resultado.returncode == 0 else ""
    return version if version.startswith(VERSION_COMPATIBLE) else None


def _ficheros_de_base(rutas: Rutas) -> dict[str, Path]:
    encontrados: dict[str, Path] = {}
    for nombre in BASES:
        for extension in ("cld", "cvd"):
            candidato = rutas.db / f"{nombre}.{extension}"
            if candidato.exists():
                encontrados[nombre] = candidato
                break
    return encontrados


def refrescar_firmas(rutas: Rutas) -> None:
    """`freshclam` contra los espejos oficiales, escribiendo solo en `db/` (sin root, sin servicio)."""
    rutas.db.mkdir(parents=True, exist_ok=True)
    configuracion = rutas.home / "freshclam.conf"
    configuracion.write_text(f"DatabaseDirectory {rutas.db}\nDatabaseMirror database.clamav.net\n"
                             "LogVerbose no\nCompressLocalDatabase no\n", encoding="utf-8")
    resultado = _correr([str(rutas.bin / "freshclam"), f"--config-file={configuracion}", f"--datadir={rutas.db}",
                         "--no-warnings"], timeout=1800)
    if resultado.returncode != 0:
        raise AnalizadorNoListo(f"freshclam falló: {(resultado.stderr or resultado.stdout).strip()[-300:]}")


def provisionar(home: Path | None = None, *, refrescar: bool = False,
                descargar: Callable[[Path], list[Path]] = descargar_paquetes,
                extraer: Callable[[list[Path], Path], None] = extraer_paquetes,
                firmas: Callable[[Rutas], None] = refrescar_firmas) -> Rutas:
    """Deja binario y firmas en el prefijo de usuario. Idempotente: con caché válida no descarga nada."""
    rutas = Rutas(home or home_por_defecto())
    rutas.home.mkdir(parents=True, exist_ok=True)
    if motor_disponible(rutas) is None:
        extraer(descargar(rutas.deb), rutas.prefijo)
        escribir_envoltorios(rutas)
        if motor_disponible(rutas) is None:
            raise AnalizadorNoListo("el clamscan extraído no arranca o no es 1.4.x")
    if refrescar or len(_ficheros_de_base(rutas)) < len(BASES):
        firmas(rutas)
    return rutas


# ------------------------------------------------------------------ preflight
def _escanear(rutas: Rutas, fichero: Path, db: Path) -> tuple[int, str]:
    resultado = _correr([str(rutas.clamscan), "--no-summary", "--stdout", f"--database={db}", str(fichero)], timeout=300)
    return resultado.returncode, resultado.stdout.strip()


def _info_de_base(rutas: Rutas, fichero: Path) -> dict[str, str]:
    salida = _correr([str(rutas.bin / "sigtool"), f"--info={fichero}"], timeout=120).stdout
    info: dict[str, str] = {"fichero": fichero.name}
    for clave, etiqueta in (("version", "Version"), ("fecha", "Build time"), ("firmas", "Signatures")):
        coincidencia = re.search(rf"^{etiqueta}:\s*(.+)$", salida, re.M)
        if coincidencia:
            info[clave] = coincidencia.group(1).strip()
    return info


def preflight(home: Path | None = None) -> Estado:
    """QAC-01…08. Devuelve el estado certificable o lanza `AnalizadorNoListo` con la causa exacta."""
    rutas = Rutas(home or home_por_defecto())
    motor = motor_disponible(rutas)
    if motor is None:
        raise AnalizadorNoListo("QAC-01/02: clamscan no arranca desde el prefijo o no es 1.4.x; ejecute «provisionar»")
    bases = _ficheros_de_base(rutas)
    if len(bases) < len(BASES):
        raise AnalizadorNoListo(f"QAC-03: faltan firmas en {rutas.db} ({sorted(set(BASES) - set(bases))}); ejecute «provisionar»")
    with tempfile.TemporaryDirectory(prefix="kontrol-qa-clamav-") as temporal:
        carpeta = Path(temporal)
        limpio, eicar, vacia = carpeta / "limpio.pdf", carpeta / "eicar.txt", carpeta / "sin-firmas"
        limpio.write_bytes(PDF_LIMPIO)
        eicar.write_text(EICAR, encoding="ascii")
        vacia.mkdir()
        codigo, salida = _escanear(rutas, limpio, rutas.db)
        if codigo != 0 or not salida.endswith("OK"):
            raise AnalizadorNoListo(f"QAC-03/04: el PDF limpio no se analiza como CLEAN (rc {codigo}: {salida[-120:]})")
        codigo, salida = _escanear(rutas, eicar, rutas.db)
        if codigo != 1 or "FOUND" not in salida:
            raise AnalizadorNoListo(f"QAC-05: EICAR no se detecta como INFECTED (rc {codigo}: {salida[-120:]})")
        codigo, _salida = _escanear(rutas, limpio, vacia)
        if codigo in (0, 1):
            raise AnalizadorNoListo(f"QAC-06: sin firmas el analizador respondió rc {codigo} en vez de error")
    return Estado(motor=motor, bases={nombre: _info_de_base(rutas, fichero) for nombre, fichero in bases.items()},
                  clamscan=str(rutas.clamscan), db=str(rutas.db))


def variables(estado: Estado) -> dict[str, str]:
    """QAC-07: lo que el producto necesita, tal como lo lee `scanning.ClamAVScanner`."""
    return {"KONTROL_CLAMSCAN_PATH": estado.clamscan, "KONTROL_CLAMAV_DB": estado.db}


def asegurar(home: Path | None = None) -> Estado:
    """Provisiona si hace falta y certifica: la única puerta para «el QA tiene analizador»."""
    provisionar(home)
    return preflight(home)


# ------------------------------------------------------------------ orden
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ClamAV real para el QA canónico, sin privilegios (Spec 046).")
    parser.add_argument("accion", choices=("provisionar", "preflight", "entorno"))
    parser.add_argument("--refrescar", action="store_true", help="vuelve a bajar las firmas aunque haya caché")
    parser.add_argument("--home", help="prefijo de usuario (defecto: KONTROL_QA_CLAMAV_HOME o la caché del usuario)")
    args = parser.parse_args(argv)
    home = Path(args.home) if args.home else None
    try:
        if args.accion == "provisionar":
            rutas = provisionar(home, refrescar=args.refrescar)
            estado = preflight(rutas.home)
        else:
            estado = preflight(home)
    except AnalizadorNoListo as exc:
        print(f"[clamav-qa] NO LISTO: {exc}", file=sys.stderr)
        return 1
    if args.accion == "entorno":
        for clave, valor in variables(estado).items():
            print(f"export {clave}={json.dumps(valor)}")
    else:
        print(json.dumps({"motor": estado.motor, "bases": estado.bases, **variables(estado)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
