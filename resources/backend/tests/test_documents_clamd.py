"""O09 · El adaptador `clamd` del análisis documental: INSTREAM real, selección explícita y falso seguro en toda rama
(Spec 046 · OBS-09, opción B de la dueña; apoyo 052 y 054).

El demonio aquí es un doble **de protocolo** en proceso (`ClamdFalso`): habla INSTREAM completo —orden, trozos con longitud
prefijada, trozo final de longitud cero— y después se comporta como se le pide: responde `OK`, `FOUND`, un `ERROR`, basura,
una respuesta truncada, nada (cuelga) o corta la conexión a mitad del flujo. Así se prueba lo que el producto hace con cada
respuesta sin depender del demonio real; el demonio real lo certifica `qa/clamd_qa.py` con el mismo adaptador.
"""

from __future__ import annotations

import ast
import math
import os
import socket
import struct
import threading
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.modules.documents import scanning

BACKEND = Path(__file__).resolve().parents[1]
RAIZ = BACKEND.parents[1]
SCANNING = (BACKEND / "app" / "modules" / "documents" / "scanning.py").read_text(encoding="utf-8")
SERVICIO = (BACKEND / "app" / "modules" / "documents" / "service.py").read_text(encoding="utf-8")
TROZO = scanning.TROZO_INSTREAM
MARCA_DE_CONTENIDO = b"CONTENIDO-SINTETICO-QUE-NUNCA-DEBE-REGISTRARSE-7f3a"


class ClamdFalso:
    """Un demonio de mentira que habla INSTREAM de verdad y luego falla —o no— como se le indique."""

    def __init__(self, modo: str = "ok", firma: str = "Eicar-Test-Signature") -> None:
        self.modo, self.firma = modo, firma
        self.oyente = socket.socket()
        self.oyente.bind(("127.0.0.1", 0))
        self.oyente.listen(8)
        self.oyente.settimeout(0.2)
        self.puerto: int = self.oyente.getsockname()[1]
        self.conexiones = 0
        self.ordenes: list[bytes] = []
        self.trozos: list[int] = []
        self.recibido = b""
        self._parar = threading.Event()
        self._hilo = threading.Thread(target=self._bucle, daemon=True)

    @staticmethod
    def _exacto(conexion: socket.socket, n: int) -> bytes:
        datos = b""
        while len(datos) < n:
            leido = conexion.recv(n - len(datos))
            if not leido:
                raise ConnectionError("cliente cerrado")
            datos += leido
        return datos

    def _atender(self, conexion: socket.socket) -> None:
        with conexion:
            conexion.settimeout(10.0)
            self.conexiones += 1
            if self.modo == "cierra_sin_leer":
                return
            orden = b""
            while not orden.endswith(b"\0"):
                orden += self._exacto(conexion, 1)
            self.ordenes.append(orden)
            while True:
                (largo,) = struct.unpack("!I", self._exacto(conexion, 4))
                if largo == 0:
                    break
                self.trozos.append(largo)
                self.recibido += self._exacto(conexion, largo)
                if self.modo == "corta_el_flujo":
                    conexion.shutdown(socket.SHUT_RDWR)
                    return
            if self.modo == "ok":
                conexion.sendall(b"stream: OK\0")
            elif self.modo == "found":
                conexion.sendall(f"stream: {self.firma} FOUND\0".encode())
            elif self.modo == "error":
                conexion.sendall(b"INSTREAM size limit exceeded. ERROR\0")
            elif self.modo == "basura":
                conexion.sendall(b"<<esto no es del protocolo>>\0")
            elif self.modo == "truncada":
                conexion.sendall(b"stream: O")
            elif self.modo == "larga":
                conexion.sendall(b"x" * (scanning.RESPUESTA_MAXIMA + 10))
            elif self.modo == "cuelga":
                conexion.recv(1)  # no responde; vuelve cuando el cliente agota su tiempo y cierra

    def _bucle(self) -> None:
        while not self._parar.is_set():
            try:
                conexion, _ = self.oyente.accept()
            except TimeoutError:
                continue
            except OSError:
                return
            try:
                self._atender(conexion)
            except (OSError, ConnectionError):
                continue

    def __enter__(self) -> ClamdFalso:
        self._hilo.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.parar()

    def parar(self) -> None:
        self._parar.set()
        self.oyente.close()
        self._hilo.join(timeout=30)


def _fichero(tmp_path: Path, datos: bytes, nombre: str = "doc.bin") -> str:
    ruta = tmp_path / nombre
    ruta.write_bytes(datos)
    return str(ruta)


def _escaner(puerto: int, timeout: int = 10) -> scanning.ClamdScanner:
    return scanning.ClamdScanner(host="127.0.0.1", port=puerto, timeout=timeout)


def _puerto_cerrado() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    puerto = s.getsockname()[1]
    s.close()
    return puerto


@pytest.fixture()
def analizador_limpio():
    """Deja el singleton del módulo y la caché de `Settings` como estaban."""
    anterior = scanning._scanner
    yield
    scanning.set_scanner(anterior)
    get_settings.cache_clear()


# ---------------------------------------------------------------- O09-01 … O09-07 · resultados y fallos
def test_o09_01_el_demonio_responde_ok_y_el_resultado_es_clean(tmp_path: Path) -> None:
    with ClamdFalso("ok") as demonio:
        resultado = _escaner(demonio.puerto).scan(_fichero(tmp_path, MARCA_DE_CONTENIDO))
    assert resultado.result == scanning.CLEAN and resultado.scanner == "clamd" and resultado.signature is None
    assert resultado.is_clean is True and demonio.conexiones == 1


def test_o09_02_el_demonio_responde_found_y_el_resultado_es_infected_con_firma(tmp_path: Path) -> None:
    with ClamdFalso("found", firma="Eicar-Test-Signature") as demonio:
        resultado = _escaner(demonio.puerto).scan(_fichero(tmp_path, MARCA_DE_CONTENIDO))
    assert resultado.result == scanning.INFECTED and resultado.signature == "Eicar-Test-Signature"
    assert resultado.is_clean is False


def test_o09_03_la_conexion_rechazada_es_scan_failed(tmp_path: Path) -> None:
    resultado = _escaner(_puerto_cerrado()).scan(_fichero(tmp_path, MARCA_DE_CONTENIDO))
    assert resultado.result == scanning.SCAN_FAILED and resultado.details == {"reason": "connection_refused"}


def test_o09_04_el_demonio_que_desaparece_al_conectar_es_scan_failed(tmp_path: Path) -> None:
    with ClamdFalso("cierra_sin_leer") as demonio:
        resultado = _escaner(demonio.puerto).scan(_fichero(tmp_path, MARCA_DE_CONTENIDO))
    assert resultado.result == scanning.SCAN_FAILED
    assert (resultado.details or {}).get("reason") in {"stream_interrupted", "truncated_response"}


def test_o09_05_el_tiempo_agotado_es_scan_failed_en_el_plazo_del_adaptador(tmp_path: Path) -> None:
    with ClamdFalso("cuelga") as demonio:
        resultado = _escaner(demonio.puerto, timeout=1).scan(_fichero(tmp_path, MARCA_DE_CONTENIDO))
    assert resultado.result == scanning.SCAN_FAILED and resultado.details == {"reason": "timeout"}


def test_o09_06_una_respuesta_fuera_del_protocolo_es_scan_failed(tmp_path: Path) -> None:
    with ClamdFalso("basura") as demonio:
        resultado = _escaner(demonio.puerto).scan(_fichero(tmp_path, MARCA_DE_CONTENIDO))
    assert resultado.result == scanning.SCAN_FAILED
    assert (resultado.details or {}).get("reason") == "protocol_error"
    assert (resultado.details or {}).get("response") == "<<esto no es del protocolo>>"


def test_o09_07_una_respuesta_truncada_o_desbordada_es_scan_failed(tmp_path: Path) -> None:
    with ClamdFalso("truncada") as demonio:
        truncada = _escaner(demonio.puerto).scan(_fichero(tmp_path, MARCA_DE_CONTENIDO))
    with ClamdFalso("larga") as demonio:
        desbordada = _escaner(demonio.puerto).scan(_fichero(tmp_path, MARCA_DE_CONTENIDO))
    assert truncada.result == scanning.SCAN_FAILED and truncada.details == {"reason": "truncated_response"}
    assert desbordada.result == scanning.SCAN_FAILED and desbordada.details == {"reason": "truncated_response"}


# ---------------------------------------------------------------- O09-08 … O09-11 · el flujo
def test_o09_08_el_contenido_viaja_por_instream_y_la_ruta_nunca(tmp_path: Path) -> None:
    ruta = _fichero(tmp_path, MARCA_DE_CONTENIDO * 1000)
    with ClamdFalso("ok") as demonio:
        assert _escaner(demonio.puerto).scan(ruta).result == scanning.CLEAN
    assert demonio.ordenes == [b"zINSTREAM\0"]
    assert demonio.recibido == MARCA_DE_CONTENIDO * 1000
    assert ruta.encode() not in demonio.recibido and str(tmp_path).encode() not in demonio.recibido
    assert all(0 < largo <= TROZO for largo in demonio.trozos)


def test_o09_09_un_documento_grande_viaja_en_varios_trozos(tmp_path: Path) -> None:
    datos = os.urandom(3 * 1024 * 1024 + 17)
    with ClamdFalso("ok") as demonio:
        assert _escaner(demonio.puerto).scan(_fichero(tmp_path, datos)).result == scanning.CLEAN
    assert len(demonio.trozos) == math.ceil(len(datos) / TROZO) == 49
    assert demonio.trozos[:-1] == [TROZO] * 48 and demonio.trozos[-1] == 17 and sum(demonio.trozos) == len(datos)
    assert demonio.recibido == datos


def test_o09_10_el_maximo_documental_de_kontrol_viaja_entero(tmp_path: Path) -> None:
    maximo = 50 * 1024 * 1024
    assert "GLOBAL_MAX_SIZE = 50 * 1024 * 1024" in SERVICIO
    datos = os.urandom(maximo)
    with ClamdFalso("ok") as demonio:
        assert _escaner(demonio.puerto).scan(_fichero(tmp_path, datos)).result == scanning.CLEAN
    assert sum(demonio.trozos) == maximo and len(demonio.trozos) == maximo // TROZO


def test_o09_11_el_maximo_mas_un_byte_lo_rechaza_kontrol_antes_de_analizar_y_el_adaptador_no_lo_recorta() -> None:
    # La capa funcional corta a 413 antes del análisis (sin cambio en este ciclo): el adaptador nunca decide tamaños.
    assert "max_size = min(doc_type.max_size_bytes or GLOBAL_MAX_SIZE, GLOBAL_MAX_SIZE)" in SERVICIO
    assert 'code="FILE_TOO_LARGE"' in SERVICIO and "status_code=413" in SERVICIO
    orden = SERVICIO.index('code="FILE_TOO_LARGE"') < SERVICIO.index("scanner = scanning.get_scanner()")
    assert orden, "el corte por tamaño precede al análisis"
    clase = SCANNING[SCANNING.index("class ClamdScanner"):SCANNING.index("class DisabledScanner")]
    assert "GLOBAL_MAX_SIZE" not in clase and "max_size" not in clase and "max_upload" not in clase


# ---------------------------------------------------------------- O09-12 … O09-14 · selección explícita, sin alternativa
def test_o09_12_la_seleccion_de_clamd_es_explicita_por_configuracion(monkeypatch, analizador_limpio) -> None:
    monkeypatch.setenv("KONTROL_DOCUMENT_SCANNER", "clamd")
    monkeypatch.setenv("KONTROL_CLAMD_HOST", "analizador-interno")
    monkeypatch.setenv("KONTROL_CLAMD_PORT", "3311")
    monkeypatch.delenv("KONTROL_DOCUMENT_SCAN", raising=False)
    get_settings.cache_clear()
    scanning.set_scanner(None)
    activo = scanning.get_scanner()
    assert isinstance(activo, scanning.ClamdScanner) and activo.name == "clamd"
    assert activo.host == "analizador-interno" and activo.port == 3311 and activo.timeout == 120
    assert scanning.get_scanner() is activo


def test_o09_13_clamscan_sigue_siendo_una_eleccion_explicita_y_la_predeterminada(monkeypatch, analizador_limpio) -> None:
    monkeypatch.setenv("KONTROL_DOCUMENT_SCANNER", "clamscan")
    monkeypatch.delenv("KONTROL_DOCUMENT_SCAN", raising=False)
    get_settings.cache_clear()
    scanning.set_scanner(None)
    assert isinstance(scanning.get_scanner(), scanning.ClamAVScanner)
    monkeypatch.delenv("KONTROL_DOCUMENT_SCANNER")
    get_settings.cache_clear()
    scanning.set_scanner(None)
    assert isinstance(scanning.get_scanner(), scanning.ClamAVScanner) and get_settings().document_scanner == "clamscan"
    monkeypatch.setenv("KONTROL_DOCUMENT_SCAN", "off")
    scanning.set_scanner(None)
    assert isinstance(scanning.get_scanner(), scanning.DisabledScanner)  # el apagado sigue siendo explícito y auditable


def test_o09_14_no_hay_alternativa_implicita_cuando_clamd_falla(monkeypatch, analizador_limpio, tmp_path: Path) -> None:
    monkeypatch.setenv("KONTROL_DOCUMENT_SCANNER", "clamd")
    monkeypatch.setenv("KONTROL_CLAMD_HOST", "127.0.0.1")
    monkeypatch.setenv("KONTROL_CLAMD_PORT", str(_puerto_cerrado()))
    monkeypatch.delenv("KONTROL_DOCUMENT_SCAN", raising=False)
    get_settings.cache_clear()
    scanning.set_scanner(None)
    activo = scanning.get_scanner()
    resultado = activo.scan(_fichero(tmp_path, MARCA_DE_CONTENIDO))
    assert isinstance(activo, scanning.ClamdScanner) and resultado.result == scanning.SCAN_FAILED
    assert isinstance(scanning.get_scanner(), scanning.ClamdScanner)  # sigue siendo clamd: nada cayó en clamscan ni en «off»
    arbol = ast.parse(SCANNING)
    seleccion = next(n for n in arbol.body if isinstance(n, ast.FunctionDef) and n.name == "get_scanner")
    assert not any(isinstance(n, ast.Try) for n in ast.walk(seleccion))
    clase = SCANNING[SCANNING.index("class ClamdScanner"):SCANNING.index("class DisabledScanner")]
    codigo = clase[clase.index('name = "clamd"'):]  # el cuerpo, sin el docstring que explica la regla
    for prohibido in ("ClamAVScanner(", "DisabledScanner(", "KONTROL_DOCUMENT_SCAN", "SKIPPED", "clamscan", "subprocess"):
        assert prohibido not in codigo, prohibido


# ---------------------------------------------------------------- O09-15 … O09-19 · falso seguro, independencia, configuración
def test_o09_15_todo_lo_que_no_es_ok_o_found_es_scan_failed_y_el_servicio_solo_acepta_clean(tmp_path: Path) -> None:
    resultados = {}
    for modo in ("error", "basura", "truncada", "larga", "cierra_sin_leer", "corta_el_flujo"):
        with ClamdFalso(modo) as demonio:
            resultados[modo] = _escaner(demonio.puerto).scan(_fichero(tmp_path, MARCA_DE_CONTENIDO * 10000))
    assert {r.result for r in resultados.values()} == {scanning.SCAN_FAILED}
    assert resultados["corta_el_flujo"].details is not None and resultados["corta_el_flujo"].details["reason"] in {"stream_interrupted", "truncated_response"}
    assert "if doc_type.scan_required and scan.result != scanning.CLEAN:" in SERVICIO
    assert 'code = "FILE_INFECTED" if scan.result == scanning.INFECTED else "SCAN_FAILED"' in SERVICIO


def test_o09_16_el_adaptador_no_conoce_el_almacen_documental() -> None:
    clase = SCANNING[SCANNING.index("class ClamdScanner"):SCANNING.index("class DisabledScanner")]
    for prohibido in ("storage", "get_storage", "STORAGE_PATH", "/data/", "Path("):
        assert prohibido not in clase, prohibido
    assert "get_storage" not in SCANNING and "from app.modules.documents.storage" not in SCANNING


def test_o09_17_el_host_del_demonio_se_configura_y_no_lleva_ip_fija(monkeypatch) -> None:
    monkeypatch.setenv("KONTROL_CLAMD_HOST", "analizador.interno")
    get_settings.cache_clear()
    try:
        assert scanning.ClamdScanner().host == "analizador.interno"
        assert scanning.ClamdScanner(port=4000).host == "analizador.interno"
    finally:
        get_settings.cache_clear()
    assert Settings.model_fields["clamd_host"].default == "clamd"  # el nombre del servicio de la composición, no una IP
    assert "127.0.0.1" not in SCANNING and "0.0.0.0" not in SCANNING
    with pytest.raises(ValidationError):
        Settings(clamd_host="")


@pytest.mark.parametrize("puerto", [0, -1, 65536, 70000, "abc"])
def test_o09_18_un_puerto_invalido_no_configura(puerto) -> None:
    with pytest.raises(ValidationError):
        Settings(clamd_port=puerto)
    assert Settings(clamd_port=3310).clamd_port == 3310 and Settings(clamd_port="3311").clamd_port == 3311


def test_o09_19_el_contenido_del_documento_no_se_registra_en_ninguna_rama(tmp_path: Path) -> None:
    for modo in ("ok", "found", "error", "basura", "truncada", "cuelga"):
        with ClamdFalso(modo) as demonio:
            resultado = _escaner(demonio.puerto, timeout=1).scan(_fichero(tmp_path, MARCA_DE_CONTENIDO * 100))
        assert MARCA_DE_CONTENIDO.decode() not in repr(resultado)
        assert len(repr(resultado.details)) < 400
    assert "logging" not in SCANNING and "print(" not in SCANNING and "logger" not in SCANNING


# ---------------------------------------------------------------- O09-20 … O09-22 · traducción exacta de la respuesta
def test_o09_20_la_respuesta_found_se_traduce_a_infected_con_la_firma() -> None:
    traducir = _escaner(1)._traducir
    assert traducir(b"stream: Win.Test.EICAR_HDB-1 FOUND") == scanning.ScanResult(scanning.INFECTED, "clamd", signature="Win.Test.EICAR_HDB-1")
    assert traducir(b"stream: Eicar-Test-Signature FOUND\n").signature == "Eicar-Test-Signature"
    assert traducir(b"stream: Heuristics.Limits.Exceeded FOUND").result == scanning.INFECTED  # AlertExceedsMax: nunca limpio


def test_o09_21_solo_stream_ok_exacto_es_clean() -> None:
    traducir = _escaner(1)._traducir
    assert traducir(b"stream: OK") == scanning.ScanResult(scanning.CLEAN, "clamd")
    assert traducir(b"stream: OK\n").result == scanning.CLEAN
    for casi in (b"stream: OKAY", b"OK", b"stream: ok", b"stream:OK", b""):
        resultado = traducir(casi)
        assert resultado.result == scanning.SCAN_FAILED, casi
        assert (resultado.details or {}).get("reason") == "protocol_error"
    assert traducir(b"stream: OK FOUND").result == scanning.INFECTED  # un FOUND nunca se lee como limpio, diga lo que diga la firma


def test_o09_22_los_errores_del_demonio_y_lo_irreconocible_son_scan_failed() -> None:
    traducir = _escaner(1)._traducir
    limite = traducir(b"INSTREAM size limit exceeded. ERROR")
    assert limite.result == scanning.SCAN_FAILED and limite.details == {"reason": "scanner_error", "response": "INSTREAM size limit exceeded. ERROR"}
    assert traducir(b"stream: Can't open file ERROR").details == {"reason": "scanner_error", "response": "stream: Can't open file ERROR"}
    desconocida = traducir(b"UNKNOWN COMMAND")
    assert desconocida.result == scanning.SCAN_FAILED and desconocida.details == {"reason": "protocol_error", "response": "UNKNOWN COMMAND"}
    assert traducir(b"\xff\xfe stream: OK?").result == scanning.SCAN_FAILED  # bytes irreconocibles no rompen ni limpian
    assert len(traducir(b"x" * 1000 + b" ERROR").details["response"]) == 200  # type: ignore[index]


# ---------------------------------------------------------------- O09-23 … O09-25 · configuración inválida, firmas, caída posterior
def test_o09_23_una_eleccion_de_analizador_invalida_falla_al_construir_la_configuracion() -> None:
    for invalido in ("clamav", "CLAMD", "off", "", "clamd;clamscan"):
        with pytest.raises(ValidationError):
            Settings(document_scanner=invalido)
    assert Settings(document_scanner="clamd").document_scanner == "clamd"
    assert Settings(document_scanner="clamscan").document_scanner == "clamscan"


def test_o09_24_el_backend_no_necesita_firmas_ni_binario_con_clamd() -> None:
    clase = SCANNING[SCANNING.index("class ClamdScanner"):SCANNING.index("class DisabledScanner")]
    for prohibido in ("KONTROL_CLAMAV_DB", "KONTROL_CLAMSCAN_PATH", "database", "freshclam", "shutil.which"):
        assert prohibido not in clase, prohibido
    assert not hasattr(_escaner(1), "database")
    dockerfile = (RAIZ / "Dockerfile.backend").read_text(encoding="utf-8").lower()
    assert "clam" not in dockerfile and "freshclam" not in dockerfile
    with ClamdFalso("ok") as demonio:
        assert _escaner(demonio.puerto).available() is True
    assert _escaner(_puerto_cerrado()).available() is True  # «disponible» no promete nada: la conexión decide, y falla cerrado


def test_o09_25_si_el_demonio_cae_despues_de_arrancar_la_subida_falla_cerrada(tmp_path: Path) -> None:
    demonio = ClamdFalso("ok").__enter__()
    escaner = _escaner(demonio.puerto)
    assert escaner.scan(_fichero(tmp_path, MARCA_DE_CONTENIDO)).result == scanning.CLEAN
    demonio.parar()
    caido = escaner.scan(_fichero(tmp_path, MARCA_DE_CONTENIDO))
    assert caido.result == scanning.SCAN_FAILED and caido.details == {"reason": "connection_refused"}
    assert escaner.scan(_fichero(tmp_path, MARCA_DE_CONTENIDO)).result == scanning.SCAN_FAILED  # y sigue así: sin reintento, sin alternativa
