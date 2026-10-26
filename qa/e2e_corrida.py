"""Una corrida E2E de principio a fin, con su propia base (FR-054-E2EDB-008..016).

Un solo dueño para todo el ciclo:

    comprobar → crear base → migrar → sembrar → backend → comprobar que usa esa base →
    Vite → suite → medir → parar Vite y backend → eliminar la base → comprobar que no está

Lo que se crea se elimina en un `finally`: falle la migración, la siembra, el arranque o la
suite. El código de salida es el de la suite; limpiar bien no convierte un fallo en un
acierto. Lo único que no cubre un `finally` es una muerte a la fuerza: para eso está
`qa/e2e-bases.py`.

Los puertos son fijos (8000 y 5173): en una máquina cabe una corrida a la vez, y si están
ocupados no se empieza.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.metadata
import json
import os
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any

import clamav_qa
import e2e_base as base
import e2e_nombres as nombres
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

FRONTEND = base.RAIZ / "resources" / "frontend"
PUERTO_BACKEND = 8000
PUERTO_FRONTEND = 5173
#: La Autoridad Central REAL de la corrida (`central_authority.main:app`), sobre su propia base efímera.
PUERTO_CENTRAL = 8010
#: BACKEND-KEEPALIVE-5S: el mismo valor que `Dockerfile.backend`/`Dockerfile.central`; la corrida arranca
#: uvicorn como producción lo arranca, y el cliente de Node (Playwright) conserva sus conexiones 5 s.
KEEP_ALIVE_SEGUNDOS = 75
CAPACIDAD_DE_DESAFIOS_E2E = 40
#: Identificadores de las dos claves sintéticas del propietario de la corrida (A firma; B solo es de confianza).
KID_A = "kontrol-lic-2026-01"
KID_B = "kontrol-lic-2027-01"
API = f"http://127.0.0.1:{PUERTO_BACKEND}/api/v1"
WEB = f"http://localhost:{PUERTO_FRONTEND}"

#: La preparación falló: la suite no llegó a correr.
SALIDA_PREPARACION = 70
#: La suite pasó, pero la corrida no quedó limpia.
SALIDA_LIMPIEZA = 75
#: La corrida se interrumpió desde fuera.
SALIDA_INTERRUMPIDA = 130

#: Prefijos de interfaces de túnel (VPN): su presencia se anota como bandera, nunca con direcciones ni extremos.
TUNELES = ("proton", "tun", "wg", "tap", "ipv6leak", "ppp")
#: Desvío entre el reloj de pared y el monotónico a partir del cual la corrida declara un salto de reloj.
UMBRAL_SALTO_DE_RELOJ_S = 5.0
HERRAMIENTAS_DE_PRUEBA: tuple[str, ...] = ("pytest", "_pytest", "httpx", "httpcore", "certifi", "ruff", "mypy", "mypy_extensions", "packaging", "pygments", "pluggy", "iniconfig")
SONDA_DEL_PRODUCTO: str = (
    "import importlib.metadata, importlib.util, json, os, re, sys; "
    f"h = {json.dumps(list(HERRAMIENTAS_DE_PRUEBA))}; "
    "print(json.dumps({'ejecutable': sys.executable, 'exe_real': os.path.realpath('/proc/self/exe'), "
    "'python': '%d.%d.%d' % sys.version_info[:3], "
    "'herramientas': sorted(n for n in h if importlib.util.find_spec(n) is not None), "
    "'distribuciones': {re.sub(r'[-_.]+', '-', d.metadata['Name']).lower(): d.version for d in importlib.metadata.distributions()}}))"
)
# La sonda se ejecuta con el mismo ejecutable, cwd y entorno que la migración de la autoridad.
#: Programa que mide qué intérprete ejecuta la migración de la Autoridad Central.
SONDA_DEL_INTERPRETE: str = (
    "import json, os, sys, alembic, sqlalchemy; print(json.dumps({"
    "'ejecutable': sys.executable, "
    "'exe_real': os.path.realpath('/proc/self/exe'), "
    "'python': '%d.%d.%d' % sys.version_info[:3], "
    "'implementacion': sys.implementation.name, "
    "'alembic': alembic.__version__, "
    "'alembic_origen': alembic.__file__, "
    "'sqlalchemy': sqlalchemy.__version__, "
    "'sqlalchemy_origen': sqlalchemy.__file__"
    "}))"
)
#: Claves exactas que devuelve la sonda.
CLAVES_DE_LA_SONDA: frozenset[str] = frozenset(
    {"ejecutable", "exe_real", "python", "implementacion", "alembic", "alembic_origen", "sqlalchemy", "sqlalchemy_origen"}
)

#: `installations.key_reference` es `String(120)` y, desde INSTALACION-KEY-REFERENCE-120, guarda una referencia
#: RELATIVA al volumen (el nombre del fichero), no la ruta absoluta: la longitud del estado efímero ya no
#: condiciona la corrida. Lo que sí se comprueba, contra la base, es ese invariante del producto.
LARGO_MAXIMO_DE_REFERENCIA = 120
#: Variables que apuntarían a otra base si se heredaran: la corrida las fija o las quita.
VARIABLES_DE_BASE = ("KONTROL_DB_URL", "KONTROL_E2E_DB_URL", "KONTROL_TEST_DB_URL")
#: Nada que parezca una URL con usuario y clave sale por la consola ni entra en el manifiesto.
URL_CON_CREDENCIALES = re.compile(r"://[^/\s:@]+:[^@\s]+@")
#: Material MFA sintético: jamás puede quedar en la evidencia (OQ-MFA-3).
MARCAS_MFA = (b"manual_key", b"recovery_codes", b"otpauth://")


def lleva_material_mfa(ruta: Path) -> bool:
    """Indica si `ruta` (fichero o carpeta) conserva material MFA sintético."""
    if ruta.is_file():
        ficheros = [ruta]
    else:
        ficheros = [p for p in ruta.rglob("*") if p.is_file()]
    for fichero in ficheros:
        try:
            if fichero.suffix == ".zip":
                try:
                    with zipfile.ZipFile(fichero) as archivo:
                        for miembro in archivo.namelist():
                            contenido = archivo.read(miembro)
                            if any(marca in contenido for marca in MARCAS_MFA):
                                return True
                except zipfile.BadZipFile:
                    contenido = fichero.read_bytes()
                    if any(marca in contenido for marca in MARCAS_MFA):
                        return True
            else:
                contenido = fichero.read_bytes()
                if any(marca in contenido for marca in MARCAS_MFA):
                    return True
        except OSError:
            return True
    return False


class Interrumpida(BaseException):
    """La corrida recibió una señal: se limpia y se sale."""


def _al_recibir_senal(numero: int, _marco: Any) -> None:
    raise Interrumpida(signal.Signals(numero).name)


def _puerto_ocupado(host: str, puerto: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, puerto)) == 0


def _responde(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=5) as respuesta:
            return respuesta.status == 200
    except (urllib.error.URLError, OSError):
        return False


def resumir_red(enlaces: str, direcciones: str) -> dict[str, Any]:
    """El estado de red del equipo **sin datos sensibles**, a partir de `ip -br link` e `ip -br addr`.

    Guarda los nombres y el estado de las interfaces, la bandera de túnel (VPN) y una huella SHA-256
    truncada de la salida de direcciones, que cambia si cambia cualquier dirección o interfaz. Las
    direcciones mismas no se guardan: comparar dos huellas basta para saber si la red cambió en vuelo
    (`E2E-PANTALLA-SIN-PINTAR`: el 2026-10-06 Chromium abortó los módulos con `ERR_NETWORK_CHANGED`).
    """
    interfaces = sorted(f"{partes[0]}:{partes[1]}" for linea in enlaces.splitlines()
                        if len(partes := linea.split()) >= 2)
    return {"interfaces": interfaces,
            "tunel_presente": any(i.split(":", 1)[0].startswith(TUNELES) for i in interfaces),
            "huella": hashlib.sha256(direcciones.encode()).hexdigest()[:12]}


def huella_de_red() -> dict[str, Any]:
    """`resumir_red` sobre el equipo; si `ip` no está, lo dice en vez de inventar."""
    try:
        enlaces = subprocess.run(["ip", "-br", "link"], capture_output=True, text=True, check=False, timeout=5).stdout
        direcciones = subprocess.run(["ip", "-br", "addr"], capture_output=True, text=True, check=False, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return {"disponible": False}
    return {"disponible": True, **resumir_red(enlaces, direcciones)}


def desvio_de_reloj(pared_inicio: datetime, mono_inicio: float, pared_fin: datetime, mono_fin: float) -> dict[str, Any]:
    """Cuánto se alejó el reloj de pared del monotónico entre dos instantes, y si eso es un salto.

    Un salto del reloj del equipo durante la corrida caduca tokens recién emitidos y descoloca las
    marcas de tiempo (visto el 2026-10-06: +5 h 08 min en una suite de 211 s). Se mide, no se corrige.
    """
    desvio = (pared_fin - pared_inicio).total_seconds() - (mono_fin - mono_inicio)
    return {"desvio_s": round(desvio, 1), "salto": abs(desvio) > UMBRAL_SALTO_DE_RELOJ_S}


def raices_a_sanear(entorno: Mapping[str, str]) -> dict[str, str]:
    """Raíces que se reemplazan en el manifiesto, de la más larga a la más corta."""
    raices = {str(base.RAIZ): "<repo>", tempfile.gettempdir(): "<tmp>"}
    if "HOME" in entorno:
        raices[entorno["HOME"]] = "<home>"
    return dict(sorted(raices.items(), key=lambda raiz: len(raiz[0]), reverse=True))


def sanear(texto: str, raices: Mapping[str, str]) -> str:
    """Reemplaza las raíces conocidas en el texto dado."""
    for raiz, marca in raices.items():
        texto = texto.replace(raiz, marca)
    return texto


def paridad_de_runtime(producto: Mapping[str, str], arnes: Mapping[str, str]) -> int:
    """1 si todo paquete del producto está en el arnés con la misma versión (excluyendo pip), 0 si no."""
    for nombre, version in producto.items():
        if nombre == "pip":
            continue
        if arnes.get(nombre) != version:
            return 0
    return 1


def _canonico_pep503(nombre: str) -> str:
    """Canoniza un nombre de distribución según PEP 503."""
    return re.sub(r"[-_.]+", "-", nombre).lower()


def paridad_de_interpretes(arnes: Mapping[str, Any], hijo: Mapping[str, Any]) -> int:
    """1 si coinciden ejecutable, exe_real y python; 0 en caso contrario."""
    coinciden = (
        arnes.get("ejecutable") == hijo.get("ejecutable")
        and arnes.get("exe_real") == hijo.get("exe_real")
        and arnes.get("python") == hijo.get("python")
    )
    return 1 if coinciden else 0


def interprete_del_arnes() -> dict[str, str]:
    """Datos del intérprete que ejecuta el arnés."""
    return {
        "ejecutable": sys.executable,
        "exe_real": os.path.realpath("/proc/self/exe"),
        "python": ".".join(str(parte) for parte in sys.version_info[:3]),
        "implementacion": sys.implementation.name,
    }


class Corrida:
    """Una corrida: su identificador, su base, sus procesos y lo que deja escrito."""

    def __init__(self, servidor: base.Servidor, *, orden: list[str] | None = None,
                 argumentos: list[str] | None = None, sin_frontend: bool = False,
                 con_analizador: bool = False,
                 entorno: Mapping[str, str] | None = None, salida: IO[str] | None = None,
                 python_de_producto: str | None = None) -> None:
        self.servidor = servidor
        self.orden = orden
        self.argumentos = list(argumentos or [])
        self.sin_frontend = sin_frontend
        #: Certificación con analizador real: el preflight de `clamav_qa` tiene que pasar antes de crear nada
        #: y sus rutas van al backend de la corrida; sin esta opción, el comportamiento local de siempre
        #: (las cargas con análisis se omiten con nombre si no hay `clamscan`).
        self.con_analizador = con_analizador
        self.entorno = dict(os.environ if entorno is None else entorno)
        self.salida = salida or sys.stdout
        self.python_de_producto = python_de_producto or sys.executable
        # Sin opción, la corrida es de un solo entorno, como V0; con la opción, el producto corre en el runtime puro.
        self.modo_de_producto = "RUNTIME_SEPARADO" if python_de_producto else "UN_SOLO_ENTORNO"
        self.run_id = nombres.nuevo_run_id(datetime.now(UTC), os.getpid(), secrets.token_hex(3))
        # Clave AES de la corrida (Spec 002), generada en ejecución, solo en
        # memoria y en el entorno de los procesos hijos; el manifiesto no la registra.
        self.claves_mfa = f"e2e{secrets.token_hex(3)}:{base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('=')}"
        self.base = nombres.nombre_de_base(self.run_id)
        self.estado = Path(self.entorno.get("KONTROL_E2E_STATE_DIR", "/tmp/kontrol-e2e")) / self.run_id
        self.evidencia = Path(self.entorno.get("KONTROL_E2E_EVIDENCE_DIR",
                                               str(base.RAIZ / "qa" / "e2e-runs"))) / self.run_id
        self.url: str | None = None
        self.creada = False
        self.procesos: dict[str, subprocess.Popen[bytes]] = {}
        self.manifiesto: dict[str, Any] = {
            "run_id": self.run_id, "base": self.base, "servidor": servidor.destino(),
            "inicio": datetime.now(UTC).isoformat(timespec="seconds"), "fases": [],
        }

    # ------------------------------------------------------------------ salida
    def decir(self, mensaje: str) -> None:
        print(URL_CON_CREDENCIALES.sub("://***@", mensaje), file=self.salida, flush=True)

    def anotar(self) -> None:
        self.evidencia.mkdir(parents=True, exist_ok=True)
        texto = json.dumps(self.manifiesto, ensure_ascii=False, indent=2, default=str)
        (self.evidencia / "manifest.json").write_text(URL_CON_CREDENCIALES.sub("://***@", texto) + "\n")

    def fase(self, nombre: str) -> None:
        self.manifiesto["fases"].append(nombre)
        self.decir(f"[e2e {self.run_id}] {nombre}")
        self.anotar()

    # ---------------------------------------------------------------- entorno
    def entorno_de_procesos(self) -> dict[str, str]:
        """El entorno de todo lo que la corrida arranca: una sola base, la suya."""
        if self.url is None:
            raise base.CicloDeBaseRoto("la base de la corrida todavía no existe")
        env = {clave: valor for clave, valor in self.entorno.items() if clave not in VARIABLES_DE_BASE}
        env.update({
            "KONTROL_DB_URL": self.url,
            "KONTROL_E2E_DB_URL": self.url,
            "KONTROL_E2E_RUN_ID": self.run_id,
            "KONTROL_MFA_KEYS": self.claves_mfa,
            "KONTROL_E2E_MFA_DIR": str(self.estado / "mfa"),
            "KONTROL_ENVIRONMENT": self.entorno.get("KONTROL_ENVIRONMENT", "local"),
            "KONTROL_SECRET_KEY": self.entorno.get(
                "KONTROL_SECRET_KEY", "qa-secret-key-0123456789abcdef0123456789abcdef"),
            "KONTROL_COOKIE_SECURE": "false",
            "KONTROL_LOG_JSON": "false",
            "KONTROL_INSTALLATION_VOLUME_PATH": str(self.estado / "license"),
            # Ancla de confianza de la licencia para ESTA corrida: la clave pública del firmante
            # sintético que la corrida genera; la privada queda en el estado efímero, solo para
            # la siembra y `qa/licencia_firmada.py`. Explícita, nunca la clave de la instalación.
            "KONTROL_LICENSE_PUBLIC_KEY_PEM": self.ancla_publica(),
            "KONTROL_E2E_LICENSE_SIGNING_KEY": str(self.clave_de_firma),
            # Rotación con solapamiento (LICENCIA-SIN-ROTACION-DE-CLAVE): un segundo firmante sintético B por
            # corrida; el backend confía en A (par de una clave) y en B (conjunto `kid → PEM`). La autoridad
            # de la corrida sigue firmando con A: la rotación del activo se certifica en el backend.
            "KONTROL_LICENSE_PUBLIC_KEY_KID": KID_A,
            "KONTROL_LICENSE_TRUST_KEYS": json.dumps({KID_A: self.ancla_publica(), KID_B: self.ancla_publica_b()}),
            "KONTROL_E2E_LICENSE_SIGNING_KEY_B": str(self.clave_de_firma_b),
            "KONTROL_E2E_LICENSE_KID_A": KID_A,
            "KONTROL_E2E_LICENSE_KID_B": KID_B,
            "KONTROL_STORAGE_PATH": str(self.estado / "storage"),
            "KONTROL_BACKUP_PATH": str(self.estado / "backups"),
            "KONTROL_QA_IDS_FILE": str(self.estado / "n6-ids.json"),
            # La identidad con la que la propia corrida comprueba el backend y con la que las suites inician
            # sesión: sin este valor cuarenta pruebas se omitían en toda corrida (E2E-CUARENTA-OMITIDAS).
            "KONTROL_E2E_USER": self.entorno.get("KONTROL_E2E_USER", "admin"),
            "KONTROL_E2E_PASSWORD": self.entorno.get("KONTROL_E2E_PASSWORD", "Kontrol2026Segura!"),
            # Si el backend de la corrida tiene analizador. Sin `clamscan` toda carga con análisis
            # obligatorio termina en SCAN_FAILED (falso seguro, FR-046-072): las pruebas que necesitan
            # una versión cargada se omiten con nombre y causa (ENTORNO-SIN-CLAMSCAN), no fallan a ciegas.
            "KONTROL_E2E_SCANNER_AVAILABLE": "true" if self.analizador() else "false",
            "KONTROL_E2E_API": API,
            "KONTROL_E2E_BASE_URL": WEB,
            "KONTROL_API_URL": f"http://127.0.0.1:{PUERTO_BACKEND}",
            # La autoridad de la corrida, para que el cliente sincronice contra ella por HTTP local (solo QA).
            "KONTROL_E2E_CENTRAL_URL": f"http://127.0.0.1:{PUERTO_CENTRAL}",
            "KONTROL_E2E_CENTRAL_RATE_CAPACITY": str(CAPACIDAD_DE_DESAFIOS_E2E),
            # El intérprete de ESTA certificación; los ayudantes Python de las specs lo usan
            # (E2E-SPECS-PYTHON-HELPERS-VENV-FIXED): nunca el heredado, un `.venv` fijo ni el PATH.
            "KONTROL_E2E_PYTHON": sys.executable,
        })
        return env

    def analizador(self) -> str | None:
        """La ruta del `clamscan` que verá el backend, resuelta como la resuelve él (`KONTROL_CLAMSCAN_PATH`,
        luego el PATH); `None` si no hay binario o si el análisis está apagado (`KONTROL_DOCUMENT_SCAN=off`)."""
        if self.entorno.get("KONTROL_DOCUMENT_SCAN", "on").lower() in ("off", "false", "0"):
            return None
        binario = self.entorno.get("KONTROL_CLAMSCAN_PATH") or shutil.which("clamscan", path=self.entorno.get("PATH"))
        return binario if binario and os.path.exists(binario) else None

    def entorno_de_la_autoridad(self) -> dict[str, str]:
        """El entorno del proceso de la Autoridad Central: base SQLite efímera en el estado de la corrida (la
        misma que usa `qa/autoridad_central.py`) y la clave sintética de la corrida como clave del propietario.
        Nada de esto va al backend ni al frontend."""
        env = self.entorno_de_procesos()
        env.update({
            "KONTROL_CENTRAL_DB_URL": f"sqlite+pysqlite:///{self.estado / 'license' / 'central.sqlite'}",
            "KONTROL_CENTRAL_SIGNING_PRIVATE_KEY_PEM": self.clave_de_firma.read_text(),
            "KONTROL_CENTRAL_ENVIRONMENT": "qa",
            "KONTROL_CENTRAL_SIGNING_KID": "kontrol-lic-2026-01",
            "KONTROL_CENTRAL_LOG_JSON": "false",
            # Límite de tasa del desafío (CENTRAL-SYNC-SIN-LIMITE-DE-TASA): capacidad reducida para que la suite
            # `licencia-tasa` pueda llenar la ventana; holgada para el resto de la corrida (una sincronización = un desafío).
            "KONTROL_CENTRAL_SYNC_CHALLENGE_RATE_LIMIT_CAPACITY": str(CAPACIDAD_DE_DESAFIOS_E2E),
            "KONTROL_CENTRAL_SYNC_CHALLENGE_RATE_LIMIT_WINDOW_SECONDS": "60",
        })
        return env

    # ------------------------------------------------------------- preparación
    @property
    def clave_de_firma(self) -> Path:
        """La clave privada del firmante sintético de la corrida (estado efímero, 0600)."""
        return self.estado / "license" / "qa_license_signing_key.pem"

    @property
    def clave_de_firma_b(self) -> Path:
        """La segunda clave sintética del propietario (B), para la rotación con solapamiento."""
        return self.estado / "license" / "qa_license_signing_key_b.pem"

    def ancla_publica_b(self) -> str:
        self.generar_firmante()
        return self._ancla_b

    def generar_firmante(self) -> None:
        """Un par Ed25519 nuevo por corrida: su pública es el ancla de confianza del backend y de
        la siembra; su privada firma las licencias sintéticas. Nunca sale del estado efímero.
        Una sola vez por corrida: el ancla no cambia a mitad de camino."""
        if getattr(self, "_ancla", None):
            return
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        self.clave_de_firma.parent.mkdir(parents=True, exist_ok=True)
        publicas = []
        for ruta in (self.clave_de_firma, self.clave_de_firma_b):
            privada = Ed25519PrivateKey.generate()
            descriptor = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(descriptor, "wb") as fichero:
                fichero.write(privada.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()))
            publicas.append(privada.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo).decode("utf-8"))
        self._ancla, self._ancla_b = publicas

    def ancla_publica(self) -> str:
        """El ancla de la corrida; si aún no hay firmante, se genera: todo proceso de la corrida
        recibe la misma pública, sea cual sea el orden en que se pida el entorno."""
        self.generar_firmante()
        return self._ancla

    def comprobar(self) -> None:
        """Lo que tiene que ser cierto antes de crear nada."""
        base.exigir_base_e2e(self.base, admin_url=self.servidor.admin_url, entorno=self.entorno)
        if self.modo_de_producto == "RUNTIME_SEPARADO" and (not os.path.isabs(self.python_de_producto) or not os.path.exists(self.python_de_producto) or not os.access(self.python_de_producto, os.X_OK)):
            raise base.CicloDeBaseRoto("el intérprete de producto no es una ruta absoluta ejecutable")
        ocupados = [puerto for host, puerto in (("127.0.0.1", PUERTO_BACKEND), ("127.0.0.1", PUERTO_CENTRAL), ("localhost", PUERTO_FRONTEND))
                    if (puerto != PUERTO_FRONTEND or not self.sin_frontend) and _puerto_ocupado(host, puerto)]
        if ocupados:
            raise base.CicloDeBaseRoto(
                f"puertos ocupados {ocupados}: hay otra pila en marcha y en esta máquina cabe una corrida a la vez")

    def exigir_analizador(self) -> dict[str, Any]:
        """Con `--con-analizador`: ClamAV real provisionado sin privilegios y certificado (CLEAN, EICAR, falso
        seguro) **antes** de la corrida; si no, la corrida no empieza. Las rutas que ve el backend son las suyas."""
        try:
            estado = clamav_qa.asegurar()
        except clamav_qa.AnalizadorNoListo as exc:
            raise base.CicloDeBaseRoto(f"analizador exigido y no listo: {exc}") from exc
        self.entorno.update(clamav_qa.variables(estado))
        return {"motor": estado.motor, "bases": estado.bases, "exigido": True}

    def preparar(self) -> None:
        self.fase("comprobar")
        self.comprobar()
        self.manifiesto["protegidas_antes"] = self.huella_de_protegidas()
        certificado = self.exigir_analizador() if self.con_analizador else {"exigido": False}
        self.manifiesto["analizador"] = {"clamscan": self.analizador(), **certificado}
        detalle = ""
        if certificado["exigido"]:
            firmas = ", ".join(f"{nombre} {info.get('version', '?')}" for nombre, info in certificado["bases"].items())
            detalle = f" · motor {certificado['motor']} · firmas {firmas}"
        self.decir(f"[e2e {self.run_id}] analizador: {self.analizador() or 'ausente (las cargas con análisis se omiten con nombre)'}{detalle}")

        self.fase("crear base")
        base.crear_base(self.servidor, self.run_id, entorno=self.entorno)
        self.creada = True
        self.url = self.servidor.url_de(self.base)
        self.estado.mkdir(parents=True, exist_ok=True)
        # Estado del arnés MFA de los workers, fuera de la evidencia; se borra
        # con el estado al terminar.
        (self.estado / "mfa").mkdir(mode=0o700, exist_ok=True)
        self.generar_firmante()

        self.fase("migrar")
        self.manifiesto["migracion"] = base.migrar(
            self.url, env=self.entorno_de_procesos(), registro=self.evidencia / "migracion.log")

        self.fase("sembrar")
        self.manifiesto["siembra"] = base.sembrar(
            self.url, env=self.entorno_de_procesos(), registro=self.evidencia / "siembra.log")
        self.manifiesto["siembra"]["commit"] = self.commit()

    def commit(self) -> str:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=base.RAIZ, capture_output=True,
                           text=True, check=False)
        return r.stdout.strip() or "desconocido"

    def huella_de_protegidas(self) -> dict[str, dict[str, int] | None]:
        return base.huella(self.servidor, sorted(base.protegidas(self.servidor.admin_url, self.entorno)
                                                  - base.DEL_SISTEMA))

    # ---------------------------------------------------------------- procesos
    def arrancar(self, nombre: str, orden: list[str], cwd: Path) -> subprocess.Popen[bytes]:
        registro = open(self.evidencia / f"{nombre}.log", "ab")  # noqa: SIM115 - vive lo que el proceso
        proceso = subprocess.Popen(orden, cwd=cwd, env=self.entorno_de_procesos(), stdout=registro,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        registro.close()
        self.procesos[nombre] = proceso
        self.manifiesto.setdefault("procesos", {})[nombre] = proceso.pid
        self.anotar()
        return proceso

    def esperar_salud(self, nombre: str, url: str, limite: float = 60.0) -> None:
        proceso = self.procesos[nombre]
        final = time.monotonic() + limite
        while time.monotonic() < final:
            if proceso.poll() is not None:
                raise base.CicloDeBaseRoto(f"{nombre} terminó al arrancar, con código {proceso.returncode} "
                                           f"(ver {nombre}.log)")
            if _responde(url):
                return
            time.sleep(0.25)
        raise base.CicloDeBaseRoto(f"{nombre} no respondió en {limite:.0f} s (ver {nombre}.log)")

    def arrancar_backend(self) -> None:
        self.fase("backend")
        self.anotar_interprete_de_producto()
        self.arrancar("backend", [self.python_de_producto, "-m", "uvicorn", "app.main:app", "--timeout-keep-alive", str(KEEP_ALIVE_SEGUNDOS), "--host", "127.0.0.1",
                                  "--port", str(PUERTO_BACKEND)], base.BACKEND)
        self.esperar_salud("backend", f"{API}/health/ready")

    def anotar_interprete_de_producto(self) -> None:
        raices = raices_a_sanear(self.entorno)
        resultado = subprocess.run([self.python_de_producto, "-c", SONDA_DEL_PRODUCTO], cwd=base.BACKEND,
                                   env=self.entorno_de_procesos(), capture_output=True, text=True, check=False)
        if resultado.returncode != 0:
            raise base.CicloDeBaseRoto("la sonda del intérprete de producto falló")
        try:
            sonda = json.loads(resultado.stdout)
        except (json.JSONDecodeError, ValueError) as error:
            raise base.CicloDeBaseRoto("la sonda del intérprete de producto falló") from error
        if not isinstance(sonda, dict) or set(sonda) != {"ejecutable", "exe_real", "python", "herramientas", "distribuciones"}:
            raise base.CicloDeBaseRoto("la sonda del intérprete de producto falló")
        ejecutable = sonda["ejecutable"]
        exe_real = sonda["exe_real"]
        python = sonda["python"]
        herramientas = sonda["herramientas"]
        distribuciones = sonda["distribuciones"]
        if not isinstance(ejecutable, str) or not isinstance(exe_real, str) or not isinstance(python, str):
            raise base.CicloDeBaseRoto("la sonda del intérprete de producto falló")
        if not isinstance(herramientas, list) or not all(isinstance(item, str) for item in herramientas):
            raise base.CicloDeBaseRoto("la sonda del intérprete de producto falló")
        if not isinstance(distribuciones, dict) or not all(isinstance(clave, str) and isinstance(valor, str) for clave, valor in distribuciones.items()):
            raise base.CicloDeBaseRoto("la sonda del intérprete de producto falló")
        arnes = {_canonico_pep503(d.metadata["Name"]): d.version for d in importlib.metadata.distributions()}
        paridad = paridad_de_runtime(distribuciones, arnes)
        self.manifiesto["interprete_de_producto"] = {
            "modo": self.modo_de_producto,
            "autoridad": sanear(self.python_de_producto, raices),
            "ejecutable": sanear(ejecutable, raices),
            "exe_real": sanear(exe_real, raices),
            "python": python,
            "herramientas_de_prueba": herramientas,
            "paquetes": len(distribuciones),
            "paridad_runtime": paridad,
        }
        self.anotar()
        self.decir(f"[e2e {self.run_id}] producto: {python} · {self.modo_de_producto} · herramientas de prueba: {', '.join(herramientas) or 'ninguna'} · runtime = arnés: {paridad}")


    def anotar_interpretes(self, entorno: dict[str, str]) -> None:
        """Anota en el manifiesto qué intérprete ejecuta el arnés y cuál la migración de la autoridad."""
        arnes_crudo = interprete_del_arnes()
        resultado = subprocess.run([sys.executable, "-c", SONDA_DEL_INTERPRETE], cwd=base.BACKEND, env=entorno,
                                   capture_output=True, text=True, check=False)
        if resultado.returncode != 0:
            raise base.CicloDeBaseRoto("la sonda del intérprete de la Autoridad Central falló")
        try:
            hijo_crudo = json.loads(resultado.stdout)
        except (json.JSONDecodeError, ValueError) as error:
            raise base.CicloDeBaseRoto("la sonda del intérprete de la Autoridad Central falló") from error
        if not isinstance(hijo_crudo, dict) or set(hijo_crudo) != set(CLAVES_DE_LA_SONDA) or not all(
            isinstance(valor, str) for valor in hijo_crudo.values()
        ):
            raise base.CicloDeBaseRoto("la sonda del intérprete de la Autoridad Central falló")
        raices = raices_a_sanear(self.entorno)
        arnes_saneado = {clave: sanear(valor, raices) for clave, valor in arnes_crudo.items()}
        hijo_saneado = {clave: sanear(valor, raices) for clave, valor in hijo_crudo.items()}
        paridad = paridad_de_interpretes(arnes_crudo, hijo_crudo)
        self.manifiesto["interpretes"] = {
            "arnes": arnes_saneado,
            "migracion_autoridad": {
                "orden": [sanear(sys.executable, raices), "-m", "alembic", "-c", "central_authority/alembic.ini", "upgrade", "head"],
                **hijo_saneado,
            },
            "paridad": paridad,
        }
        self.anotar()
        self.decir(f"[e2e {self.run_id}] intérprete: arnés {arnes_crudo['python']} · migración de la autoridad {hijo_crudo['python']} · paridad {paridad}")

    def arrancar_autoridad(self) -> None:
        """La Autoridad Central real: migra su base efímera y levanta su API en el puerto propio."""
        self.fase("autoridad central")
        entorno = self.entorno_de_la_autoridad()
        self.anotar_interpretes(entorno)
        registro = open(self.evidencia / "autoridad-migraciones.log", "ab")  # noqa: SIM115 - vive lo que la orden
        try:
            resultado = subprocess.run([sys.executable, "-m", "alembic", "-c", "central_authority/alembic.ini", "upgrade", "head"],
                                       cwd=base.BACKEND, env=entorno, stdout=registro, stderr=subprocess.STDOUT, check=False)
        finally:
            registro.close()
        if resultado.returncode != 0:
            raise base.CicloDeBaseRoto("las migraciones de la Autoridad Central fallaron (ver autoridad-migraciones.log)")
        registro = open(self.evidencia / "autoridad.log", "ab")  # noqa: SIM115 - vive lo que el proceso
        proceso = subprocess.Popen([self.python_de_producto, "-m", "uvicorn", "central_authority.main:app", "--timeout-keep-alive", str(KEEP_ALIVE_SEGUNDOS), "--host", "127.0.0.1",
                                    "--port", str(PUERTO_CENTRAL)], cwd=base.BACKEND, env=entorno, stdout=registro,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        registro.close()
        self.procesos["autoridad"] = proceso
        self.manifiesto.setdefault("procesos", {})["autoridad"] = proceso.pid
        self.anotar()
        self.esperar_salud("autoridad", f"http://127.0.0.1:{PUERTO_CENTRAL}/health/ready")

    def verificar_backend(self) -> None:
        """El backend que responde es el de esta corrida y escribe en la base de esta corrida.

        Con MFA obligatorio el login no abre sesión: responde 200 con
        `status` `MFA_ENROLLMENT_REQUIRED` o `MFA_REQUIRED` y crea un desafío
        en `mfa_challenges`. Este método comprueba precisamente eso: que el
        desafío aparece en la base y que todas las conexiones de la corrida
        están en ella.
        """
        self.fase("comprobar la base del backend")
        if self.url is None:
            raise base.CicloDeBaseRoto("la base de la corrida todavía no existe")
        antes = self._desafios()
        entorno = self.entorno_de_procesos()
        cuerpo = json.dumps({"tenant_code": "DEMO", "username": entorno["KONTROL_E2E_USER"],
                             "password": entorno["KONTROL_E2E_PASSWORD"]}).encode()
        peticion = urllib.request.Request(f"{API}/auth/login", data=cuerpo,
                                          headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(peticion, timeout=30) as respuesta:
                body = json.loads(respuesta.read().decode())
        except urllib.error.URLError as error:
            raise base.CicloDeBaseRoto(f"el backend no deja iniciar sesión al usuario de la siembra: {error}") from error
        except json.JSONDecodeError as error:
            raise base.CicloDeBaseRoto(f"la respuesta del login no es JSON: {error}") from error
        status = body.get("status")
        if status not in ("MFA_ENROLLMENT_REQUIRED", "MFA_REQUIRED"):
            raise base.CicloDeBaseRoto(f"login no requirió MFA: {status}")
        despues = self._desafios()
        if despues != antes + 1:
            raise base.CicloDeBaseRoto(
                f"el desafío MFA creado por la API no está en la base de la corrida ({antes} → {despues}): "
                "el backend escribe en otra base")
        self.manifiesto["instalacion"] = self.comprobar_referencia_de_clave()
        admin = base.motor_administrativo(self.servidor)
        try:
            with admin.connect() as conn:
                donde = sorted(conn.execute(text(
                    "select distinct datname from pg_stat_activity where application_name = :a"),
                    {"a": nombres.aplicacion(self.run_id)}).scalars().all())
        finally:
            admin.dispose()
        if donde != [self.base]:
            raise base.CicloDeBaseRoto(f"las conexiones de la corrida están en {donde}, no solo en {self.base}")
        self.manifiesto["backend"] = {"base": self.base, "desafios": despues}

    def comprobar_referencia_de_clave(self) -> dict[str, Any]:
        """La instalación de la corrida persiste una referencia de clave relativa al volumen.

        Antes el runner abortaba si la ruta del estado superaba 120 caracteres, porque el producto guardaba
        la ruta absoluta en `String(120)`: la guarda escondía el defecto. Ahora se mira lo que de verdad hay en
        la base: una referencia que no depende de la longitud del volumen (sin separadores, dentro del límite).
        """
        motor = create_engine(self.url or "", future=True, poolclass=NullPool)
        try:
            with motor.connect() as conn:
                referencias = [r for (r,) in conn.execute(text("select key_reference from installations"))]
        finally:
            motor.dispose()
        if len(referencias) != 1:
            raise base.CicloDeBaseRoto(f"la base de la corrida tiene {len(referencias)} instalaciones; debe tener una")
        referencia = referencias[0]
        if referencia is None or os.path.isabs(referencia) or "/" in referencia or len(referencia) > LARGO_MAXIMO_DE_REFERENCIA:
            raise base.CicloDeBaseRoto(
                "la instalación persiste una referencia de clave que depende de la ruta del volumen "
                f"({'nula' if referencia is None else f'{len(referencia)} caracteres, absoluta o con separadores'}): "
                "el producto volvió a guardar la ruta absoluta (INSTALACION-KEY-REFERENCE-120)")
        return {"key_reference": referencia, "relativa": True, "largo_del_volumen": len(str(self.estado / "license"))}

    def _desafios(self) -> int:
        motor = create_engine(self.url or "", future=True, poolclass=NullPool)
        try:
            with motor.connect() as conn:
                return int(conn.execute(text("select count(*) from mfa_challenges")).scalar_one())
        finally:
            motor.dispose()

    def arrancar_frontend(self) -> None:
        self.fase("frontend")
        self.arrancar("frontend", ["node", "node_modules/vite/bin/vite.js", "--host", "localhost", "--port",
                                   str(PUERTO_FRONTEND), "--strictPort"], FRONTEND)
        self.esperar_salud("frontend", f"{WEB}/")

    # ----------------------------------------------------------------- entorno observado
    def anotar_entorno(self, pared_inicio: datetime, mono_inicio: float) -> None:
        """Red y reloj al final de la corrida, comparados con el inicio. Solo observa y avisa: no aborta
        ni invalida (decidir eso es política del arnés y queda para la dueña)."""
        entorno = self.manifiesto["entorno"]
        entorno["red_fin"] = huella_de_red()
        entorno["red_cambio"] = entorno["red_inicio"].get("huella") != entorno["red_fin"].get("huella")
        entorno["reloj"] = desvio_de_reloj(pared_inicio, mono_inicio, datetime.now(UTC), time.monotonic())
        avisos = []
        if entorno["red_cambio"]:
            avisos.append("la red del equipo cambió durante la corrida (ERR_NETWORK_CHANGED posible)")
        if entorno["reloj"]["salto"]:
            avisos.append(f"el reloj del equipo saltó {entorno['reloj']['desvio_s']:+.1f} s respecto al monotónico")
        if entorno["red_inicio"].get("tunel_presente"):
            avisos.append("túnel (VPN) presente")
        self.decir(f"[e2e {self.run_id}] entorno: {' · '.join(avisos) if avisos else 'red sin cambios · reloj coherente · sin túnel'}")

    # ------------------------------------------------------------------- suite
    def orden_de_la_suite(self) -> tuple[list[str], Path]:
        if self.orden is not None:
            return [*self.orden, *self.argumentos], base.RAIZ
        return (["node", "node_modules/@playwright/test/cli.js", "test", "--project=chromium", "--project=licencia-revision", "--project=licencia-sync", "--project=licencia-rotacion",
                 "--project=licencia-tasa",
                 "--output", str(self.evidencia / "test-results"), *self.argumentos], FRONTEND)

    def suite(self) -> int:
        self.fase("suite")
        orden, cwd = self.orden_de_la_suite()
        inicio = time.monotonic()
        proceso = subprocess.Popen(orden, cwd=cwd, env=self.entorno_de_procesos(), stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        self.procesos["suite"] = proceso
        resumen: dict[str, int] = {}

        def copiar() -> None:
            assert proceso.stdout is not None
            with open(self.evidencia / "suite.log", "ab") as registro:
                for linea in proceso.stdout:
                    registro.write(linea)
                    registro.flush()
                    texto_ = linea.decode(errors="replace").rstrip("\n")
                    self.decir(texto_)
                    hallado = re.fullmatch(r"\s+(\d+) (passed|failed|skipped|flaky|did not run)\b.*", texto_)
                    if hallado:
                        resumen[hallado.group(2)] = int(hallado.group(1))

        hilo = threading.Thread(target=copiar, daemon=True)
        hilo.start()
        codigo = proceso.wait()
        hilo.join(timeout=30)
        self.manifiesto["suite"] = {"codigo": codigo, "resumen": resumen,
                                    "segundos": round(time.monotonic() - inicio, 1)}
        return codigo

    # ------------------------------------------------------------------ medidas
    def medir(self) -> None:
        """Lo que la corrida dejó en su base, leído antes de eliminarla."""
        if self.url is None:
            return
        motor = create_engine(self.url, future=True, poolclass=NullPool)
        try:
            with motor.connect() as conn:
                def uno(consulta: str) -> Any:
                    return conn.execute(text(consulta)).scalar_one()

                ticks = [dict(fila._mapping) for fila in conn.execute(text(
                    "select to_char(r.started_at, 'HH24:MI:SS') as inicio, "
                    "round(extract(epoch from (r.finished_at - r.started_at))::numeric, 2) as segundos, "
                    "r.status as estado, r.items_seen as vistos, "
                    "(select count(*) from users u where u.created_at < r.started_at) as usuarios, "
                    "(select count(*) from notification_rules n where n.created_at < r.started_at and n.active)"
                    " as reglas from scheduler_runs r order by r.started_at"))]
                self.manifiesto["medidas"] = {
                    "usuarios": uno("select count(*) from users"),
                    "reglas_de_notificacion": uno("select count(*) from notification_rules"),
                    "almacenes": uno("select count(*) from warehouses"),
                    "megas": uno("select pg_database_size(current_database()) / (1024 * 1024)"),
                    "ticks": len(ticks),
                    "tick_mas_lento": max((float(t["segundos"] or 0) for t in ticks), default=0.0),
                    "serie_de_ticks": ticks,
                }
        except Exception as error:  # noqa: BLE001 - medir no puede cambiar el resultado de la corrida
            self.manifiesto["medidas"] = {"error": f"{type(error).__name__}: {error}"}
        finally:
            motor.dispose()

    # ----------------------------------------------------------------- limpieza
    def detener(self, nombre: str, gracia: float = 15.0) -> str:
        proceso = self.procesos.get(nombre)
        if proceso is None:
            return "no arrancó"
        if proceso.poll() is None:
            try:
                os.killpg(proceso.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proceso.wait(timeout=gracia)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proceso.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proceso.wait(timeout=gracia)
                return "detenido a la fuerza"
        return "detenido"

    def tachar_credenciales(self) -> None:
        """Ningún registro de la corrida conserva una URL con usuario y clave.

        Los escriben procesos ajenos —alembic, la siembra, uvicorn—, y una traza de error
        puede llevar la URL de la base entera.
        """
        for registro in self.evidencia.glob("*.log"):
            try:
                texto_ = registro.read_text(errors="replace")
            except OSError:
                continue
            limpio = URL_CON_CREDENCIALES.sub("://***@", texto_)
            if limpio != texto_:
                registro.write_text(limpio)

    def retirar_material_mfa(self) -> dict[str, Any]:
        """Retira de la evidencia las carpetas con material MFA sintético (OQ-MFA-3)."""
        resultados = self.evidencia / "test-results"
        retirados: list[str] = []
        if resultados.is_dir():
            for hijo in sorted(resultados.iterdir()):
                if hijo.is_dir() and lleva_material_mfa(hijo):
                    shutil.rmtree(hijo, ignore_errors=True)
                    retirados.append(hijo.name)
        quedan = 0
        for fichero in self.evidencia.rglob("*"):
            if fichero.is_file() and fichero.name != "manifest.json" and lleva_material_mfa(fichero):
                quedan += 1
        return {"retirados": retirados, "quedan": quedan}

    def limpiar(self) -> bool:
        """Para lo que se arrancó y elimina lo que se creó. Devuelve si todo quedó limpio."""
        limpieza: dict[str, Any] = {}
        self.manifiesto["limpieza"] = limpieza
        correcto = True
        for nombre in ("suite", "frontend", "autoridad", "backend"):
            try:
                limpieza[nombre] = self.detener(nombre)
            except Exception as error:  # noqa: BLE001 - se intenta limpiar todo y se informa de lo que no se pudo
                limpieza[nombre] = f"ERROR {type(error).__name__}: {error}"
                correcto = False
        if self.creada:
            try:
                limpieza["base"] = base.soltar_base(self.servidor, self.base, entorno=self.entorno)
            except Exception as error:  # noqa: BLE001
                limpieza["base"] = {"estado": f"ERROR {type(error).__name__}: {error}"}
                correcto = False
        else:
            limpieza["base"] = {"estado": "NO_CREADA"}
        try:
            despues = self.huella_de_protegidas()
            self.manifiesto["protegidas_despues"] = despues
            self.manifiesto["protegidas_sin_cambios"] = despues == self.manifiesto.get("protegidas_antes")
        except Exception as error:  # noqa: BLE001
            self.manifiesto["protegidas_despues"] = f"ERROR {type(error).__name__}: {error}"
        self.tachar_credenciales()
        # OQ-MFA-3: las trazas de las pruebas fallidas llevan respuestas del alta.
        try:
            limpieza["material_mfa"] = self.retirar_material_mfa()
        except Exception as error:  # noqa: BLE001
            limpieza["material_mfa"] = {"estado": f"ERROR {type(error).__name__}: {error}"}
        correcto = correcto and limpieza["material_mfa"].get("quedan") == 0
        # El estado efímero lleva la clave de instalación de una base que ya no existe.
        shutil.rmtree(self.estado, ignore_errors=True)
        limpieza["estado"] = "eliminado" if not self.estado.exists() else "QUEDA"
        correcto = correcto and not self.estado.exists()
        limpieza["resultado"] = "LIMPIA" if correcto else "SUCIA"
        return correcto

    # ------------------------------------------------------------------- todo
    def ejecutar(self) -> int:
        codigo = SALIDA_PREPARACION
        anteriores = {s: signal.signal(s, _al_recibir_senal) for s in (signal.SIGTERM, signal.SIGHUP)}
        pared_inicio, mono_inicio = datetime.now(UTC), time.monotonic()
        self.manifiesto["entorno"] = {"red_inicio": huella_de_red()}
        try:
            self.anotar()
            self.preparar()
            self.arrancar_backend()
            self.verificar_backend()
            self.arrancar_autoridad()
            if not self.sin_frontend:
                self.arrancar_frontend()
            codigo = self.suite()
            self.medir()
        except (Interrumpida, KeyboardInterrupt) as error:
            codigo = SALIDA_INTERRUMPIDA
            self.manifiesto["error"] = f"interrumpida: {error}"
            self.decir(f"[e2e {self.run_id}] interrumpida: se limpia y se sale")
        except Exception as error:  # noqa: BLE001 - cualquier fallo de preparación acaba en limpieza y en código de fallo
            self.manifiesto["error"] = f"{type(error).__name__}: {error}"
            self.decir(f"[e2e {self.run_id}] FALLO: {type(error).__name__}: {error}")
            if "suite" in self.manifiesto:
                codigo = self.manifiesto["suite"]["codigo"] or SALIDA_PREPARACION
        finally:
            for s in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
                signal.signal(s, signal.SIG_IGN)
            self.fase("limpiar")
            limpia = self.limpiar()
            self.manifiesto["fin"] = datetime.now(UTC).isoformat(timespec="seconds")
            self.anotar_entorno(pared_inicio, mono_inicio)
            if codigo == 0 and not limpia:
                codigo = SALIDA_LIMPIEZA
            self.manifiesto["codigo_de_salida"] = codigo
            self.anotar()
            for s, anterior in anteriores.items():
                signal.signal(s, anterior)
            signal.signal(signal.SIGINT, signal.default_int_handler)
        suite = self.manifiesto.get("suite", {})
        self.decir(f"[e2e {self.run_id}] suite: {suite.get('resumen', 'no corrió')} · "
                   f"limpieza: {self.manifiesto['limpieza']['resultado']} · salida: {codigo} · "
                   f"evidencia: {self.evidencia}")
        return codigo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Corre la suite E2E contra una base PostgreSQL nueva, que se elimina al terminar.",
        epilog="Lo que sigue a «--» se pasa a Playwright (o a la orden indicada con --orden).")
    parser.add_argument("--sin-frontend", action="store_true", help="no arranca Vite (suites que solo usan la API)")
    parser.add_argument("--con-analizador", action="store_true",
                        help="exige ClamAV real (qa/clamav_qa.py): preflight antes de la corrida y rutas al backend")
    parser.add_argument("--orden", metavar="PROGRAMA",
                        help="programa que se ejecuta en lugar de Playwright, desde la raíz del repositorio")
    parser.add_argument("--python-de-producto", metavar="RUTA",
                        help="intérprete del runtime puro para el backend y la autoridad; sin ella, el del arnés")
    args, resto = parser.parse_known_args(argv)
    if resto[:1] == ["--"]:
        resto = resto[1:]
    corrida = Corrida(base.Servidor.del_entorno(), orden=[args.orden] if args.orden else None,
                      argumentos=resto, sin_frontend=args.sin_frontend, con_analizador=args.con_analizador,
                      python_de_producto=args.python_de_producto)
    return corrida.ejecutar()
