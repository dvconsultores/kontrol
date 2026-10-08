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
import json
import os
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any

import e2e_base as base
import e2e_nombres as nombres
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

FRONTEND = base.RAIZ / "resources" / "frontend"
PUERTO_BACKEND = 8000
PUERTO_FRONTEND = 5173
#: La Autoridad Central REAL de la corrida (`central_authority.main:app`), sobre su propia base efímera.
PUERTO_CENTRAL = 8010
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

#: `installations.key_reference` guarda la ruta de la clave de instalación en 120 caracteres.
LARGO_MAXIMO_DE_RUTA = 120
#: Variables que apuntarían a otra base si se heredaran: la corrida las fija o las quita.
VARIABLES_DE_BASE = ("KONTROL_DB_URL", "KONTROL_E2E_DB_URL", "KONTROL_TEST_DB_URL")
#: Nada que parezca una URL con usuario y clave sale por la consola ni entra en el manifiesto.
URL_CON_CREDENCIALES = re.compile(r"://[^/\s:@]+:[^@\s]+@")


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


class Corrida:
    """Una corrida: su identificador, su base, sus procesos y lo que deja escrito."""

    def __init__(self, servidor: base.Servidor, *, orden: list[str] | None = None,
                 argumentos: list[str] | None = None, sin_frontend: bool = False,
                 entorno: Mapping[str, str] | None = None, salida: IO[str] | None = None) -> None:
        self.servidor = servidor
        self.orden = orden
        self.argumentos = list(argumentos or [])
        self.sin_frontend = sin_frontend
        self.entorno = dict(os.environ if entorno is None else entorno)
        self.salida = salida or sys.stdout
        self.run_id = nombres.nuevo_run_id(datetime.now(UTC), os.getpid(), secrets.token_hex(3))
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
            "KONTROL_E2E_PASSWORD": self.entorno.get("KONTROL_E2E_PASSWORD", "Kontrol2026Segura!"),
            "KONTROL_E2E_API": API,
            "KONTROL_E2E_BASE_URL": WEB,
            "KONTROL_API_URL": f"http://127.0.0.1:{PUERTO_BACKEND}",
            # La autoridad de la corrida, para que el cliente sincronice contra ella por HTTP local (solo QA).
            "KONTROL_E2E_CENTRAL_URL": f"http://127.0.0.1:{PUERTO_CENTRAL}",
        })
        return env

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
        ruta_de_clave = self.estado / "license" / "installation_private_key.pem"
        if len(str(ruta_de_clave)) > LARGO_MAXIMO_DE_RUTA:
            raise base.CicloDeBaseRoto(
                f"la ruta de estado es demasiado larga ({len(str(ruta_de_clave))} > {LARGO_MAXIMO_DE_RUTA}): "
                "acórtela con KONTROL_E2E_STATE_DIR")
        ocupados = [puerto for host, puerto in (("127.0.0.1", PUERTO_BACKEND), ("127.0.0.1", PUERTO_CENTRAL), ("localhost", PUERTO_FRONTEND))
                    if (puerto != PUERTO_FRONTEND or not self.sin_frontend) and _puerto_ocupado(host, puerto)]
        if ocupados:
            raise base.CicloDeBaseRoto(
                f"puertos ocupados {ocupados}: hay otra pila en marcha y en esta máquina cabe una corrida a la vez")

    def preparar(self) -> None:
        self.fase("comprobar")
        self.comprobar()
        self.manifiesto["protegidas_antes"] = self.huella_de_protegidas()

        self.fase("crear base")
        base.crear_base(self.servidor, self.run_id, entorno=self.entorno)
        self.creada = True
        self.url = self.servidor.url_de(self.base)
        self.estado.mkdir(parents=True, exist_ok=True)
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
        self.arrancar("backend", [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                                  "--port", str(PUERTO_BACKEND)], base.BACKEND)
        self.esperar_salud("backend", f"{API}/health/ready")

    def arrancar_autoridad(self) -> None:
        """La Autoridad Central real: migra su base efímera y levanta su API en el puerto propio."""
        self.fase("autoridad central")
        entorno = self.entorno_de_la_autoridad()
        registro = open(self.evidencia / "autoridad-migraciones.log", "ab")  # noqa: SIM115 - vive lo que la orden
        try:
            resultado = subprocess.run([str(base.BACKEND / ".venv/bin/alembic"), "-c", "central_authority/alembic.ini", "upgrade", "head"],
                                       cwd=base.BACKEND, env=entorno, stdout=registro, stderr=subprocess.STDOUT, check=False)
        finally:
            registro.close()
        if resultado.returncode != 0:
            raise base.CicloDeBaseRoto("las migraciones de la Autoridad Central fallaron (ver autoridad-migraciones.log)")
        registro = open(self.evidencia / "autoridad.log", "ab")  # noqa: SIM115 - vive lo que el proceso
        proceso = subprocess.Popen([sys.executable, "-m", "uvicorn", "central_authority.main:app", "--host", "127.0.0.1",
                                    "--port", str(PUERTO_CENTRAL)], cwd=base.BACKEND, env=entorno, stdout=registro,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        registro.close()
        self.procesos["autoridad"] = proceso
        self.manifiesto.setdefault("procesos", {})["autoridad"] = proceso.pid
        self.anotar()
        self.esperar_salud("autoridad", f"http://127.0.0.1:{PUERTO_CENTRAL}/health/ready")

    def verificar_backend(self) -> None:
        """El backend que responde es el de esta corrida y escribe en la base de esta corrida.

        Inicia sesión por la API y mira dos cosas: que la sesión aparece en la base de la
        corrida, y que todas las conexiones que llevan el nombre de esta corrida están en ella.
        """
        self.fase("comprobar la base del backend")
        if self.url is None:
            raise base.CicloDeBaseRoto("la base de la corrida todavía no existe")
        antes = self._sesiones()
        cuerpo = json.dumps({"tenant_code": "DEMO", "username": "admin",
                             "password": self.entorno_de_procesos()["KONTROL_E2E_PASSWORD"]}).encode()
        peticion = urllib.request.Request(f"{API}/auth/login", data=cuerpo,
                                          headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(peticion, timeout=30) as respuesta:
                respuesta.read()
        except urllib.error.URLError as error:
            raise base.CicloDeBaseRoto(f"el backend no deja iniciar sesión al usuario de la siembra: {error}") from error
        despues = self._sesiones()
        if despues != antes + 1:
            raise base.CicloDeBaseRoto(
                f"la sesión abierta por la API no está en la base de la corrida ({antes} → {despues}): "
                "el backend escribe en otra base")
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
        self.manifiesto["backend"] = {"base": self.base, "sesiones": despues}

    def _sesiones(self) -> int:
        motor = create_engine(self.url or "", future=True, poolclass=NullPool)
        try:
            with motor.connect() as conn:
                return int(conn.execute(text("select count(*) from sessions")).scalar_one())
        finally:
            motor.dispose()

    def arrancar_frontend(self) -> None:
        self.fase("frontend")
        self.arrancar("frontend", ["node", "node_modules/vite/bin/vite.js", "--host", "localhost", "--port",
                                   str(PUERTO_FRONTEND), "--strictPort"], FRONTEND)
        self.esperar_salud("frontend", f"{WEB}/")

    # ------------------------------------------------------------------- suite
    def orden_de_la_suite(self) -> tuple[list[str], Path]:
        if self.orden is not None:
            return [*self.orden, *self.argumentos], base.RAIZ
        return (["node", "node_modules/@playwright/test/cli.js", "test", "--project=chromium", "--project=licencia-revision", "--project=licencia-sync", "--project=licencia-rotacion",
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
    parser.add_argument("--orden", metavar="PROGRAMA",
                        help="programa que se ejecuta en lugar de Playwright, desde la raíz del repositorio")
    args, resto = parser.parse_known_args(argv)
    if resto[:1] == ["--"]:
        resto = resto[1:]
    corrida = Corrida(base.Servidor.del_entorno(), orden=[args.orden] if args.orden else None,
                      argumentos=resto, sin_frontend=args.sin_frontend)
    return corrida.ejecutar()
