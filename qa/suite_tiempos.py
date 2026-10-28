"""Certificación backend con telemetría reproducible (Spec 054 · OBS-12 · SUITE-DURATION-VARIABILITY).

Una SQLite completa tardó 2946 s donde las comparables tardan 587–610 s, con el mismo veredicto, y no quedó ninguna
medida del equipo que lo explicara: el QA no distinguía una anomalía del anfitrión de un defecto del arnés. Este
módulo envuelve la **orden canónica** de pytest sin cambiar su colección ni su orden y deja, por corrida, lo que hace
falta para diagnosticar la siguiente anomalía:

- duración **monotónica** (el reloj de pared solo sirve para medir su desvío: un salto de reloj no infla la medida);
- recuentos del resumen de pytest y su código de salida, que es también el de esta orden;
- perfil por prueba (`--durations=0`): las N más lentas con setup, call y teardown;
- telemetría del anfitrión **saneada**, cada 30 s, desde `/proc`: carga, memoria disponible, swap usada y paginación,
  utilización de CPU y E/S de disco; nunca IP, interfaces, túneles, nombre del equipo, usuario ni rutas personales;
- recursos del árbol de pytest (`getrusage`): CPU, RSS máximo, cambios de contexto;
- metadatos del analizador real (motor y firmas) cuando se exige, como hace `qa/e2e-run.py --con-analizador`;
- residuos efímeros del arnés (`kontrol-test-almacen-*`, `kontrol-test-sqlite-*`, `kontrol-test-license-*`), que una
  corrida limpia debe dejar a cero; el antiguo almacén fijo `kontrol-test-storage` (anterior a OBS-06) se anota como
  legado y nunca falla la corrida;
- un indicador de anomalía **no bloqueante**: la razón entre la duración y la mediana de las corridas anteriores del
  mismo motor; sin umbral duro (`HARD_THRESHOLD = NONE`), sin cambiar el veredicto.

Órdenes:

    python qa/suite_tiempos.py --motor sqlite [--con-analizador]      la SQLite completa canónica, instrumentada
    python qa/suite_tiempos.py --motor postgres [--con-analizador]    la PostgreSQL completa canónica (ktest), instrumentada

La evidencia queda en `qa/backend-runs/<run_id>/` (`manifest.json`, `pytest.txt`, `host.csv`), fuera de Git.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import resource
import secrets
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import clamav_qa
import e2e_corrida
import e2e_nombres as nombres

RAIZ = Path(__file__).resolve().parent.parent
BACKEND = RAIZ / "resources" / "backend"
CORRIDAS = RAIZ / "qa" / "backend-runs"
#: La orden canónica de certificación backend (`.claude/CLAUDE.md`) con el perfil por prueba: misma colección y mismo
#: orden que `pytest tests -q -p no:cacheprovider`; `-o addopts=` deja visible el resumen que `--durations` necesita.
ORDEN_PYTEST = ("-m", "pytest", "tests", "-o", "addopts=", "-q", "--durations=0", "-p", "no:cacheprovider")
MOTORES: dict[str, str | None] = {"sqlite": None, "postgres": "postgresql+psycopg2://postgres@localhost:55432/ktest"}
TOP_N = 30
INTERVALO_S = 30.0
#: Almacén fijo del arnés anterior a OBS-06 (2026-10-13 … 2026-10-15): estado legado, ni residuo de esta corrida ni fallo.
ALMACEN_FIJO_LEGADO = "kontrol-test-storage"
#: Raíces que cada proceso de pytest crea y elimina (`tests/conftest.py`): si quedan tras la corrida, son residuo.
PREFIJOS_EFIMEROS = ("kontrol-test-almacen-", "kontrol-test-sqlite-", "kontrol-test-license-")
MODO_DE_ALMACEN = "PROCESS_ISOLATED"
#: El indicador de anomalía necesita referencias; con menos no se pronuncia.
MINIMO_DE_REFERENCIAS = 3
#: Razón duración/mediana desde la que se anota anomalía. Evidencia: las corridas normales con analizador quedaron entre
#: 581 y 692 s (≤ 1,2× entre sí) y la atípica fue 5× (OBS-12). No es un umbral de fallo: no cambia el veredicto.
RAZON_DE_ANOMALIA = 2.0
#: Dispositivos de bloque enteros en `/proc/diskstats` (no particiones).
DISPOSITIVO = re.compile(r"^(nvme\d+n\d+|sd[a-z]+|vd[a-z]+|mmcblk\d+)$")
RESUMEN = re.compile(r"(?:(\d+) failed, )?(\d+) passed(?:, (\d+) skipped)?(?:, (\d+) error(?:s)?)?(?:, [^\n]*?)? in ([\d.]+)s")
DURACION = re.compile(r"^(\d+\.\d+)s (setup|call|teardown)\s+(\S+)$", re.MULTILINE)
Lector = Callable[[], str]


# ---------------------------------------------------------------- lectura de /proc (texto → números; sin red)

def leer_carga(texto: str) -> dict[str, float]:
    """`/proc/loadavg` → load1, load5, load15."""
    partes = texto.split()
    return {"load1": float(partes[0]), "load5": float(partes[1]), "load15": float(partes[2])}


def leer_memoria(texto: str) -> dict[str, int]:
    """`/proc/meminfo` → memoria disponible y swap usada, en MB."""
    valores: dict[str, int] = {}
    for linea in texto.splitlines():
        clave, _, resto = linea.partition(":")
        if clave in ("MemAvailable", "SwapTotal", "SwapFree"):
            valores[clave] = int(resto.split()[0]) // 1024
    return {"mem_disponible_mb": valores["MemAvailable"], "swap_usada_mb": valores["SwapTotal"] - valores["SwapFree"]}


def leer_cpu(texto: str) -> tuple[int, int]:
    """`/proc/stat` → (tiempo total, tiempo ocioso) acumulados de todas las CPU."""
    for linea in texto.splitlines():
        if linea.startswith("cpu "):
            v = [int(x) for x in linea.split()[1:]]
            return sum(v), v[3] + v[4]
    raise ValueError("sin línea cpu")


def leer_disco(texto: str) -> tuple[int, int]:
    """`/proc/diskstats` → sectores leídos y escritos, sumados sobre los dispositivos enteros."""
    leidos = escritos = 0
    for linea in texto.splitlines():
        p = linea.split()
        if len(p) >= 10 and DISPOSITIVO.match(p[2]):
            leidos += int(p[5])
            escritos += int(p[9])
    return leidos, escritos


def leer_paginacion(texto: str) -> tuple[int, int]:
    """`/proc/vmstat` → páginas entradas y salidas de swap, acumuladas."""
    valores: dict[str, int] = {}
    for linea in texto.splitlines():
        clave, _, valor = linea.partition(" ")
        if clave in ("pswpin", "pswpout"):
            valores[clave] = int(valor)
    return valores["pswpin"], valores["pswpout"]


def _fichero(ruta: str) -> Lector:
    def leer() -> str:
        return Path(ruta).read_text(encoding="utf-8")
    return leer


FUENTES_DEL_SISTEMA: dict[str, Lector] = {
    "carga": _fichero("/proc/loadavg"), "memoria": _fichero("/proc/meminfo"), "cpu": _fichero("/proc/stat"),
    "disco": _fichero("/proc/diskstats"), "paginacion": _fichero("/proc/vmstat"),
}
COLUMNAS = ("elapsed_s", "load1", "load5", "load15", "mem_disponible_mb", "swap_usada_mb", "cpu_util_pct",
            "disco_leido_mb", "disco_escrito_mb", "paginacion_entrante", "paginacion_saliente")


class Muestreador:
    """Toma una muestra saneada del anfitrión cada `intervalo` segundos mientras corre la suite.

    Una fuente que falta (otro sistema operativo, `/proc` restringido) deja su columna vacía y queda anotada en
    `disponible`; nunca inventa un valor ni impide la medida de la duración.
    """

    def __init__(self, destino: Path, *, intervalo: float = INTERVALO_S,
                 fuentes: Mapping[str, Lector] | None = None, monotonico: Callable[[], float] = time.monotonic) -> None:
        self.destino = destino
        self.intervalo = intervalo
        self.fuentes = dict(fuentes if fuentes is not None else FUENTES_DEL_SISTEMA)
        self.monotonico = monotonico
        self.disponible = {nombre: True for nombre in ("carga", "memoria", "cpu", "disco", "paginacion")}
        self.filas: list[dict[str, Any]] = []
        self._parar = threading.Event()
        self._hilo = threading.Thread(target=self._bucle, name="suite-tiempos-muestreador", daemon=True)
        self._inicio = 0.0
        self._cpu: tuple[int, int] | None = None
        self._disco: tuple[int, int] | None = None
        self._paginacion: tuple[int, int] | None = None

    def _leer(self, nombre: str, parser: Callable[[str], Any]) -> Any:
        try:
            return parser(self.fuentes[nombre]())
        except (OSError, KeyError, ValueError, IndexError):
            self.disponible[nombre] = False
            return None

    def muestra(self) -> dict[str, Any]:
        """Una fila: deltas de CPU, disco y paginación frente a la muestra anterior; carga y memoria instantáneas."""
        fila: dict[str, Any] = {"elapsed_s": round(self.monotonico() - self._inicio)}
        carga = self._leer("carga", leer_carga)
        fila.update(carga or {"load1": None, "load5": None, "load15": None})
        memoria = self._leer("memoria", leer_memoria)
        fila.update(memoria or {"mem_disponible_mb": None, "swap_usada_mb": None})
        cpu = self._leer("cpu", leer_cpu)
        fila["cpu_util_pct"] = None
        if cpu is not None and self._cpu is not None and cpu[0] > self._cpu[0]:
            fila["cpu_util_pct"] = round(100.0 * (1 - (cpu[1] - self._cpu[1]) / (cpu[0] - self._cpu[0])), 1)
        self._cpu = cpu
        disco = self._leer("disco", leer_disco)
        fila["disco_leido_mb"] = fila["disco_escrito_mb"] = None
        if disco is not None and self._disco is not None:
            fila["disco_leido_mb"] = round((disco[0] - self._disco[0]) * 512 / 1e6, 1)
            fila["disco_escrito_mb"] = round((disco[1] - self._disco[1]) * 512 / 1e6, 1)
        self._disco = disco
        paginacion = self._leer("paginacion", leer_paginacion)
        fila["paginacion_entrante"] = fila["paginacion_saliente"] = None
        if paginacion is not None and self._paginacion is not None:
            fila["paginacion_entrante"] = paginacion[0] - self._paginacion[0]
            fila["paginacion_saliente"] = paginacion[1] - self._paginacion[1]
        self._paginacion = paginacion
        return fila

    def _bucle(self) -> None:
        while not self._parar.wait(self.intervalo):
            self.filas.append(self.muestra())

    def __enter__(self) -> Muestreador:
        self._inicio = self.monotonico()
        self.muestra()  # fija las referencias de los deltas; no se guarda
        self._hilo.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._parar.set()
        self._hilo.join()
        self.filas.append(self.muestra())
        with self.destino.open("w", newline="", encoding="utf-8") as salida:
            escritor = csv.DictWriter(salida, fieldnames=COLUMNAS)
            escritor.writeheader()
            escritor.writerows(self.filas)

    def resumen(self) -> dict[str, Any]:
        def columna(nombre: str) -> list[float]:
            return [float(f[nombre]) for f in self.filas if f.get(nombre) is not None]
        def estadistica(nombre: str, funcion: Callable[[list[float]], float]) -> float | None:
            valores = columna(nombre)
            return round(funcion(valores), 1) if valores else None
        return {
            "intervalo_s": self.intervalo, "muestras": len(self.filas), "disponible": dict(self.disponible),
            "carga": {"load1_media": estadistica("load1", statistics.mean), "load1_max": estadistica("load1", max),
                      "load5_max": estadistica("load5", max)},
            "memoria": {"disponible_min_mb": estadistica("mem_disponible_mb", min),
                        "swap_usada_max_mb": estadistica("swap_usada_mb", max),
                        "paginacion_entrante": estadistica("paginacion_entrante", sum),
                        "paginacion_saliente": estadistica("paginacion_saliente", sum)},
            "cpu": {"util_media_pct": estadistica("cpu_util_pct", statistics.mean),
                    "util_max_pct": estadistica("cpu_util_pct", max)},
            "disco": {"leido_mb": estadistica("disco_leido_mb", sum), "escrito_mb": estadistica("disco_escrito_mb", sum)},
        }


# ---------------------------------------------------------------- salida de pytest → perfil y recuentos

def parsear_duraciones(texto: str) -> list[dict[str, Any]]:
    """Las líneas `12.34s call  tests/x.py::test_y` del informe `--durations`, en el orden en que aparecen."""
    return [{"segundos": float(s), "fase": fase, "nodo": nodo} for s, fase, nodo in DURACION.findall(texto)]


def top_n(duraciones: list[dict[str, Any]], n: int = TOP_N) -> list[dict[str, Any]]:
    """Las `n` pruebas más lentas sumando sus fases; empate resuelto por el nodo (determinista)."""
    por_nodo: dict[str, dict[str, float]] = {}
    for d in duraciones:
        fases = por_nodo.setdefault(d["nodo"], {"setup": 0.0, "call": 0.0, "teardown": 0.0})
        fases[d["fase"]] += d["segundos"]
    filas = [(round(sum(f.values()), 3), nodo, f) for nodo, f in por_nodo.items()]
    filas.sort(key=lambda fila: (-fila[0], fila[1]))
    return [{"nodo": nodo, "segundos": total, **{k: round(v, 3) for k, v in f.items()}} for total, nodo, f in filas[:n]]


def perfil(texto: str, n: int = TOP_N) -> dict[str, Any]:
    duraciones = parsear_duraciones(texto)
    por_fase = {"setup": 0.0, "call": 0.0, "teardown": 0.0}
    for d in duraciones:
        por_fase[d["fase"]] += d["segundos"]
    top = top_n(duraciones, n)
    return {"top_n": top, "n": n, "pruebas_listadas": len({d["nodo"] for d in duraciones}),
            "suma_listada_s": round(sum(por_fase.values()), 1), "por_fase_s": {k: round(v, 1) for k, v in por_fase.items()},
            "top_n_s": round(sum(f["segundos"] for f in top), 1)}


def parsear_resumen(texto: str) -> dict[str, Any]:
    """La última línea `N failed, M passed, K skipped in T s` de pytest; sin ella, recuentos nulos y `completo` falso."""
    coincidencias = RESUMEN.findall(texto)
    if not coincidencias:
        return {"completo": False, "passed": None, "failed": None, "skipped": None, "errors": None, "segundos": None}
    failed, passed, skipped, errors, segundos = coincidencias[-1]
    return {"completo": True, "passed": int(passed), "failed": int(failed or 0), "skipped": int(skipped or 0),
            "errors": int(errors or 0), "segundos": float(segundos)}


# ---------------------------------------------------------------- saneado, residuos y anomalía

def raices_a_sanear(entorno: Mapping[str, str] | None = None) -> dict[str, str]:
    """Rutas que no deben aparecer en la evidencia, de la más específica a la más general."""
    entorno = os.environ if entorno is None else entorno
    raices = {str(RAIZ): "<repo>"}
    cache = entorno.get("KONTROL_QA_CLAMAV_HOME") or entorno.get("XDG_CACHE_HOME")
    if cache:
        raices[cache] = "<qa-cache>"
    raices[tempfile.gettempdir()] = "<tmp>"
    hogar = entorno.get("HOME")
    if hogar:
        raices[hogar] = "<home>"
    return dict(sorted(raices.items(), key=lambda par: -len(par[0])))


def sanear(texto: str, raices: Mapping[str, str]) -> str:
    for ruta, marca in raices.items():
        texto = texto.replace(ruta, marca)
    return texto


def residuos(tmp: Path) -> dict[str, Any]:
    """Directorios efímeros del arnés que una corrida dejó atrás (almacén, SQLite e instalación por proceso); el almacén
    fijo anterior a OBS-06 se anota como legado, aparte."""
    nombres_tmp = sorted(p.name for p in tmp.iterdir()) if tmp.is_dir() else []
    efimeros = [n for n in nombres_tmp if n.startswith(PREFIJOS_EFIMEROS)]
    return {"modo_almacen": MODO_DE_ALMACEN, "efimeros": efimeros, "almacen_por_proceso": [n for n in efimeros if n.startswith("kontrol-test-almacen-")],
            "almacen_fijo_legado_presente": ALMACEN_FIJO_LEGADO in nombres_tmp}


def anomalia(duracion_s: float, referencias: list[float]) -> dict[str, Any]:
    """Indicador no bloqueante: razón entre la duración y la mediana de las corridas previas del mismo motor."""
    base: dict[str, Any] = {"umbral_duro": None, "razon_de_anomalia": RAZON_DE_ANOMALIA, "referencias": len(referencias)}
    if len(referencias) < MINIMO_DE_REFERENCIAS:
        return {**base, "indicador": "SIN_REFERENCIA", "mediana_s": None, "razon": None,
                "motivo": f"hacen falta {MINIMO_DE_REFERENCIAS} corridas previas del mismo motor"}
    mediana = statistics.median(referencias)
    razon = duracion_s / mediana if mediana > 0 else None
    indicador = "ANOMALIA" if razon is not None and razon >= RAZON_DE_ANOMALIA else "NORMAL"
    motivo = (f"duración {duracion_s:.0f} s = {razon:.2f}× la mediana {mediana:.0f} s de {len(referencias)} corridas"
              if razon is not None else "mediana nula")
    return {**base, "indicador": indicador, "mediana_s": round(mediana, 1), "razon": round(razon, 2) if razon is not None else None,
            "motivo": motivo}


def referencias_previas(motor: str, carpeta: Path) -> list[float]:
    """Duraciones monotónicas de las corridas anteriores del mismo motor que terminaron con resumen completo."""
    valores: list[float] = []
    if not carpeta.is_dir():
        return valores
    for manifiesto in sorted(carpeta.glob("*/manifest.json")):
        try:
            datos = json.loads(manifiesto.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if datos.get("motor") == motor and datos.get("pytest", {}).get("completo"):
            valores.append(float(datos["duracion"]["monotonica_s"]))
    return valores


# ---------------------------------------------------------------- la corrida

def entorno_de_pytest(motor: str, *, con_analizador: bool, base: Mapping[str, str] | None = None,
                      asegurar: Callable[[], clamav_qa.Estado] = clamav_qa.asegurar) -> tuple[dict[str, str], dict[str, Any]]:
    """El entorno de la orden canónica para `motor` y lo que se anota del analizador.

    Con `con_analizador`, el analizador real se asegura antes de empezar (como `qa/e2e-run.py --con-analizador`) y sus
    rutas se exportan tal como las lee el producto. Nunca se apaga el analizador para ir más rápido.
    """
    entorno = dict(os.environ if base is None else base)
    entorno.pop("KONTROL_DOCUMENT_SCAN", None)
    entorno["PYTHONDONTWRITEBYTECODE"] = "1"
    url = MOTORES[motor]
    if url is None:
        entorno.pop("KONTROL_TEST_DB_URL", None)
    else:
        entorno["KONTROL_TEST_DB_URL"] = url
    anotacion: dict[str, Any] = {"exigido": con_analizador}
    if con_analizador:
        estado = asegurar()
        entorno.update(clamav_qa.variables(estado))
        anotacion.update({"motor": estado.motor, "bases": estado.bases})
    anotacion["habilitado"] = bool(entorno.get("KONTROL_CLAMSCAN_PATH"))
    return entorno, anotacion


def _recursos(antes: resource.struct_rusage, despues: resource.struct_rusage) -> dict[str, Any]:
    return {"cpu_usuario_s": round(despues.ru_utime - antes.ru_utime, 1), "cpu_sistema_s": round(despues.ru_stime - antes.ru_stime, 1),
            "maxrss_mb": despues.ru_maxrss // 1024, "ctx_voluntarios": despues.ru_nvcsw - antes.ru_nvcsw,
            "ctx_involuntarios": despues.ru_nivcsw - antes.ru_nivcsw, "bloques_leidos": despues.ru_inblock - antes.ru_inblock,
            "bloques_escritos": despues.ru_oublock - antes.ru_oublock}


def ejecutar(motor: str, *, con_analizador: bool = False, carpeta: Path = CORRIDAS, intervalo: float = INTERVALO_S,
             orden: tuple[str, ...] | None = None, cwd: Path = BACKEND, entorno: Mapping[str, str] | None = None,
             fuentes: Mapping[str, Lector] | None = None, monotonico: Callable[[], float] = time.monotonic,
             pared: Callable[[], datetime] = lambda: datetime.now(UTC), tmp: Path | None = None,
             asegurar: Callable[[], clamav_qa.Estado] = clamav_qa.asegurar, decir: Callable[[str], None] = print) -> int:
    """Corre la orden canónica de `motor` con telemetría y devuelve **el código de salida de pytest**."""
    if motor not in MOTORES:
        raise ValueError(f"motor desconocido: {motor!r}")
    env, anotacion_analizador = entorno_de_pytest(motor, con_analizador=con_analizador, base=entorno, asegurar=asegurar)
    run_id = nombres.nuevo_run_id(pared(), os.getpid(), secrets.token_hex(3))
    evidencia = carpeta / run_id
    evidencia.mkdir(parents=True, exist_ok=False)
    raices = raices_a_sanear(env)
    orden_final = (sys.executable, *(orden if orden is not None else ORDEN_PYTEST))
    decir(f"[suite {run_id}] {motor} · {sanear(' '.join(orden_final), raices)}")
    referencias = referencias_previas(motor, carpeta)
    antes = resource.getrusage(resource.RUSAGE_CHILDREN)
    pared_inicio, mono_inicio = pared(), monotonico()
    with (evidencia / "pytest.txt").open("w", encoding="utf-8") as salida, \
            Muestreador(evidencia / "host.csv", intervalo=intervalo, fuentes=fuentes, monotonico=monotonico) as muestreador:
        rc = subprocess.run(list(orden_final), cwd=cwd, env=env, stdout=salida, stderr=subprocess.STDOUT, check=False).returncode
    pared_fin, mono_fin = pared(), monotonico()
    despues = resource.getrusage(resource.RUSAGE_CHILDREN)
    texto = (evidencia / "pytest.txt").read_text(encoding="utf-8")
    (evidencia / "pytest.txt").write_text(sanear(texto, raices), encoding="utf-8")
    duracion = {"monotonica_s": round(mono_fin - mono_inicio, 1), "pared_s": round((pared_fin - pared_inicio).total_seconds(), 1),
                **e2e_corrida.desvio_de_reloj(pared_inicio, mono_inicio, pared_fin, mono_fin)}
    manifiesto: dict[str, Any] = {
        "suite": "backend", "motor": motor, "run_id": run_id, "inicio_utc": pared_inicio.isoformat(timespec="seconds"),
        "orden": [sanear(parte, raices) for parte in orden_final], "duracion": duracion,
        "pytest": {**parsear_resumen(texto), "rc": rc}, "analizador": anotacion_analizador,
        "perfil": perfil(texto), "anfitrion": muestreador.resumen(), "recursos": _recursos(antes, despues),
        "residuos": residuos(tmp if tmp is not None else Path(tempfile.gettempdir())),
        "anomalia": anomalia(duracion["monotonica_s"], referencias),
    }
    (evidencia / "manifest.json").write_text(sanear(json.dumps(manifiesto, ensure_ascii=False, indent=2), raices) + "\n",
                                             encoding="utf-8")
    resumen = manifiesto["pytest"]
    # el salto de reloj se dice explícitamente para que un desvío grande no se lea como normal
    salto = " · salto de reloj: SÍ (suspensión o ajuste del reloj del anfitrión; la duración monotónica sigue siendo válida)" \
        if duracion["salto"] else " · salto de reloj: NO"
    decir(f"[suite {run_id}] pytest rc {rc} · {resumen['passed']}/{resumen['failed']}/{resumen['skipped']} · "
          f"{duracion['monotonica_s']} s monotónicos (desvío de reloj {duracion['desvio_s']} s){salto} · "
          f"anomalía: {manifiesto['anomalia']['indicador']} · evidencia: {sanear(str(evidencia), raices)}")
    return rc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Certificación backend canónica con telemetría reproducible (Spec 054, OBS-12).")
    parser.add_argument("--motor", choices=sorted(MOTORES), required=True)
    parser.add_argument("--con-analizador", action="store_true", help="exige el ClamAV real del QA y anota motor y firmas")
    parser.add_argument("--intervalo", type=float, default=INTERVALO_S, help="segundos entre muestras del anfitrión")
    args = parser.parse_args(argv)
    return ejecutar(args.motor, con_analizador=args.con_analizador, intervalo=args.intervalo)


if __name__ == "__main__":
    sys.exit(main())
