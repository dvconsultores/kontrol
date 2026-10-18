"""CLAMD-QA · El QA del servicio de análisis con el demonio real (`qa/clamd_qa.py`; Spec 046 · OBS-09, apoyo 054).

Lo que no necesita el demonio real se prueba con dobles **del aprovisionamiento y del arranque** (descarga, extracción,
un `clamd` de mentira que solo habla PING/VERSION), nunca del análisis: las sondas de análisis real las ejecuta
`python qa/clamd_qa.py certificar` y su informe es la evidencia. El contrato de imagen y composición se comprueba aquí
contra los ficheros reales del repositorio.
"""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "qa"))

import clamav_qa  # noqa: E402
import clamd_qa  # noqa: E402

from app.modules.documents import scanning  # noqa: E402

FUENTE = (RAIZ / "qa" / "clamd_qa.py").read_text(encoding="utf-8")

#: Un `clamd` de mentira: lee `TCPSocket` de su configuración y responde PING y VERSION; nada más.
CLAMD_FALSO = '''#!/usr/bin/env python3
import socket, sys
puerto = next(int(l.split()[1]) for l in open(sys.argv[1].split("=", 1)[1]) if l.startswith("TCPSocket"))
if "--muere" in sys.argv: sys.exit(3)
s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); s.bind(("127.0.0.1", puerto)); s.listen(4)
while True:
    c, _ = s.accept()
    with c:
        orden = b""
        while not orden.endswith(b"\\0"):
            d = c.recv(1)
            if not d: break
            orden += d
        if orden == b"zPING\\0": c.sendall(b"PONG\\0")
        elif orden == b"zVERSION\\0": c.sendall(b"ClamAV 1.4.3/28153/Wed Oct 14 08:24:15 2026\\0")
'''


def _rutas_falsas(home: Path, *, muere: bool = False) -> clamav_qa.Rutas:
    rutas = clamav_qa.Rutas(home)
    rutas.bin.mkdir(parents=True, exist_ok=True)
    rutas.db.mkdir(parents=True, exist_ok=True)
    guion = rutas.bin / "clamd"
    guion.write_text(CLAMD_FALSO if not muere else CLAMD_FALSO.replace('if "--muere" in sys.argv', "if True"), encoding="utf-8")
    guion.chmod(guion.stat().st_mode | stat.S_IXUSR)
    return rutas


def _puerto_libre() -> int:
    import socket

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    puerto = s.getsockname()[1]
    s.close()
    return puerto


# CLAMD-QA-01 · la configuración local es la del despliegue con las directivas locales sustituidas y los límites intactos.
def test_cq_01_la_configuracion_local_conserva_los_limites_del_despliegue(tmp_path: Path) -> None:
    rutas = clamav_qa.Rutas(tmp_path / "home")
    destino = clamd_qa.configuracion_local(rutas, 33123, tmp_path)
    texto = destino.read_text(encoding="utf-8")
    directivas = {linea.split()[0]: linea.split()[1] for linea in texto.splitlines() if linea.strip() and not linea.startswith("#")}
    assert directivas["TCPAddr"] == "127.0.0.1" and directivas["TCPSocket"] == "33123"
    assert directivas["DatabaseDirectory"] == str(rutas.db) and directivas["LogFile"].startswith(str(tmp_path))
    assert "User" not in directivas and "LocalSocket" not in directivas
    assert directivas["StreamMaxLength"] == "60M" and directivas["MaxFileSize"] == "60M" and directivas["MaxScanSize"] == "100M"
    assert directivas["AlertExceedsMax"] == "yes" and directivas["Foreground"] == "yes"
    despliegue = clamd_qa.CONFIGURACION_DEL_DESPLIEGUE.read_text(encoding="utf-8")
    assert "TCPAddr 0.0.0.0" in despliegue and "DatabaseDirectory /var/lib/clamav" in despliegue  # el despliegue no cambia


# CLAMD-QA-02 · los límites del despliegue cubren el máximo documental de KONTROL.
def test_cq_02_los_limites_del_despliegue_cubren_el_maximo_documental() -> None:
    tope = clamd_qa.limites()
    assert tope == {"StreamMaxLength": 60 * 1024 ** 2, "MaxFileSize": 60 * 1024 ** 2, "MaxScanSize": 100 * 1024 ** 2}
    assert clamd_qa.MAXIMO_DOCUMENTAL == 50 * 1024 ** 2 <= tope["StreamMaxLength"] <= tope["MaxScanSize"]
    servicio = (RAIZ / "resources" / "backend" / "app" / "modules" / "documents" / "service.py").read_text(encoding="utf-8")
    assert "GLOBAL_MAX_SIZE = 50 * 1024 * 1024" in servicio


# CLAMD-QA-03 · la versión del demonio se lee del protocolo, no se inventa.
def test_cq_03_version_del_demonio() -> None:
    assert clamd_qa.version("ClamAV 1.4.3/28153/Wed Oct 14 08:24:15 2026") == {
        "motor": "1.4.3", "firmas_version": "28153", "firmas_fecha": "Wed Oct 14 08:24:15 2026"}
    with pytest.raises(clamd_qa.DemonioNoListo):
        clamd_qa.version("PONG")


# CLAMD-QA-04 · el contrato estático de imagen y composición, contra los ficheros reales.
def test_cq_04_contrato_estatico_de_imagen_y_composicion() -> None:
    e = clamd_qa.comprobaciones_estaticas()
    assert e["CLAMD_SERVICE_PRESENT"] is True and e["CLAMD_BASE_IMAGE_PINNED"] is True
    assert e["CLAMD_HOST_PORT_PUBLISHED"] is False and e["CLAMD_INTERNAL_ONLY"] is True
    assert e["DOCUMENT_STORAGE_MOUNTED_IN_CLAMD"] is False and e["CLAMD_VOLUMES"] == ["kontrol-clamav-db:/var/lib/clamav"]
    assert e["CLAMD_HEALTHCHECK_PRESENT"] is True and e["CLAMD_HEALTHCHECK_MEANINGFUL"] is True
    assert e["FRESHCLAM_IN_SCANNER_DOMAIN"] is True and e["BACKEND_SELECTS_CLAMD_EXPLICITLY"] is True
    assert e["BACKEND_IMAGE_HAS_CLAMSCAN"] is False and e["BACKEND_IMAGE_HAS_SIGNATURE_DATABASE"] is False
    assert e["BACKEND_MOUNTS_SIGNATURES"] is False and e["SIZE_CONTRACT_OK"] is True and e["ALERT_EXCEEDS_MAX"] is True
    assert e["KONTROL_MAX_DECLARED"] is True and e["IMPLICIT_FALLBACK"] is False and e["SCANNER_CHOICE_VALIDATED"] is True
    assert e["CLAMD_IMAGE"].endswith("/kontrol-clamd:${KONTROL_IMAGE_TAG:-latest}")


# CLAMD-QA-05 · el aprovisionamiento del demonio reutiliza el prefijo del QA y es idempotente.
def test_cq_05_aprovisionar_el_demonio_sin_privilegios_y_sin_repetir_descargas(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    descargas: list[Path] = []
    monkeypatch.setattr(clamav_qa, "provisionar", lambda h: clamav_qa.Rutas(h))

    def descargar(destino: Path) -> Path:
        descargas.append(destino)
        destino.mkdir(parents=True, exist_ok=True)
        return destino / "clamav-daemon_1.4.3_amd64.deb"

    def extraer(fichero: Path, prefijo: Path) -> None:
        real = prefijo / "usr" / "sbin" / "clamd"
        real.parent.mkdir(parents=True, exist_ok=True)
        real.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        (prefijo / "usr" / "lib" / clamav_qa.ARQUITECTURA).mkdir(parents=True, exist_ok=True)

    rutas = clamd_qa.provisionar(home, descargar=descargar, extraer=extraer)
    envoltorio = rutas.bin / "clamd"
    assert envoltorio.exists() and os.access(envoltorio, os.X_OK) and rutas.home.is_relative_to(tmp_path)
    assert "LD_LIBRARY_PATH" in envoltorio.read_text(encoding="utf-8") and str(rutas.lib) in envoltorio.read_text(encoding="utf-8")
    assert descargas == [rutas.deb]
    clamd_qa.provisionar(home, descargar=descargar, extraer=extraer)
    assert descargas == [rutas.deb]  # idempotente


# CLAMD-QA-06 · el demonio arranca, se espera por PONG (sin plazo arbitrario) y se detiene siempre.
def test_cq_06_el_demonio_se_arranca_se_espera_por_pong_y_se_detiene(tmp_path: Path) -> None:
    rutas = _rutas_falsas(tmp_path / "home")
    puerto = _puerto_libre()
    with clamd_qa.Demonio(rutas, puerto, limite_s=30) as demonio:
        assert demonio.arranque_s >= 0 and demonio.proceso is not None and demonio.proceso.poll() is None
        assert clamd_qa.orden(puerto, b"PING") == "PONG"
        assert clamd_qa.version(clamd_qa.orden(puerto, b"VERSION"))["motor"] == "1.4.3"
        carpeta = demonio.carpeta
        assert (carpeta / "clamd.conf").exists()
    assert demonio.proceso.poll() is not None and not carpeta.exists()
    with pytest.raises(OSError):
        clamd_qa.orden(puerto, b"PING", timeout=1.0)


# CLAMD-QA-07 · un demonio que muere al arrancar se declara, no se espera hasta el plazo.
def test_cq_07_un_demonio_que_muere_al_arrancar_se_declara(tmp_path: Path) -> None:
    rutas = _rutas_falsas(tmp_path / "home", muere=True)
    demonio = clamd_qa.Demonio(rutas, _puerto_libre(), limite_s=30)
    with pytest.raises(clamd_qa.DemonioNoListo, match="terminó al arrancar"):
        with demonio:
            pass
    assert not demonio.carpeta.exists()  # el fallo de arranque tampoco deja residuos


# CLAMD-QA-08 · los servidores de fallo producen exactamente las ramas de falso seguro del adaptador del producto.
@pytest.mark.parametrize("modo, motivo", [("cuelga", "timeout"), ("basura", "protocol_error"), ("truncada", "truncated_response"),
                                          ("error", "scanner_error")])
def test_cq_08_cada_servidor_de_fallo_lleva_a_su_rama_de_scan_failed(tmp_path: Path, modo: str, motivo: str) -> None:
    fichero = tmp_path / "doc.bin"
    fichero.write_bytes(os.urandom(3 * clamd_qa.TROZO))
    with clamd_qa.ServidorDeFallo(modo) as servidor:
        resultado = scanning.ClamdScanner(host="127.0.0.1", port=servidor.puerto, timeout=2).scan(str(fichero))
    assert resultado.result == scanning.SCAN_FAILED and (resultado.details or {}).get("reason") == motivo
    assert str(tmp_path).encode() not in servidor.recibido and len(servidor.recibido) >= 3 * clamd_qa.TROZO


def test_cq_08b_el_corte_del_flujo_es_scan_failed(tmp_path: Path) -> None:
    fichero = tmp_path / "doc.bin"
    fichero.write_bytes(os.urandom(3 * clamd_qa.TROZO))
    with clamd_qa.ServidorDeFallo("corta_el_flujo") as servidor:
        resultado = scanning.ClamdScanner(host="127.0.0.1", port=servidor.puerto, timeout=2).scan(str(fichero))
    assert resultado.result == scanning.SCAN_FAILED
    assert (resultado.details or {}).get("reason") in {"stream_interrupted", "truncated_response"}


# CLAMD-QA-09 · el veredicto exige todas las sondas y el contrato estático; una sola desviación lo tumba.
def test_cq_09_el_veredicto_no_aprueba_con_una_sola_desviacion() -> None:
    def sonda(result: str, reason: str | None = None, signature: str | None = None) -> dict:
        return {"result": result, "signature": signature, "details": {"reason": reason} if reason else None, "ruta_enviada_al_demonio": False}
    sondas = {"limpio": sonda("CLEAN"), "eicar": sonda("INFECTED", signature="Eicar-Test-Signature"), "varios_trozos": sonda("CLEAN"),
              "maximo_documental": sonda("CLEAN"), "maximo_mas_uno": sonda("CLEAN"),
              "por_encima_del_limite_del_demonio": sonda("SCAN_FAILED", "scanner_error"), "demonio_caido": sonda("SCAN_FAILED", "connection_refused"),
              "tiempo_agotado": sonda("SCAN_FAILED", "timeout"), "error_de_protocolo": sonda("SCAN_FAILED", "protocol_error"),
              "respuesta_truncada": sonda("SCAN_FAILED", "truncated_response"), "flujo_interrumpido": sonda("SCAN_FAILED", "stream_interrupted"),
              "error_del_demonio": sonda("SCAN_FAILED", "scanner_error")}
    veredicto = clamd_qa.veredicto_de_sondas(sondas)
    assert all(v is True for c, v in veredicto.items() if c != "SHARED_FILE_PATH_REQUIRED") and veredicto["SHARED_FILE_PATH_REQUIRED"] is False
    informe = {"estatico": clamd_qa.comprobaciones_estaticas(), "veredicto": veredicto, "demonio": {"ping": "PONG"}}
    assert clamd_qa.aprobado(informe) is True
    roto = dict(sondas, limpio=sonda("SCAN_FAILED", "timeout"))
    assert clamd_qa.aprobado({**informe, "veredicto": clamd_qa.veredicto_de_sondas(roto)}) is False
    fail_open = dict(sondas, demonio_caido=sonda("CLEAN"))
    assert clamd_qa.veredicto_de_sondas(fail_open)["SCANNER_UNAVAILABLE_FAIL_CLOSED"] is False
    con_ruta = {k: dict(v, ruta_enviada_al_demonio=True) for k, v in sondas.items()}
    assert clamd_qa.aprobado({**informe, "veredicto": clamd_qa.veredicto_de_sondas(con_ruta)}) is False
    assert clamd_qa.aprobado({**informe, "estatico": dict(informe["estatico"], CLAMD_HOST_PORT_PUBLISHED=True)}) is False
    assert clamd_qa.aprobado({**informe, "demonio": {"ping": ""}}) is False


# CLAMD-QA-10 · lo que no hay se declara: runtime de contenedores y la orden `estatico`.
def test_cq_10_el_runtime_se_declara_y_la_orden_estatica_informa(capsys) -> None:
    runtime = clamd_qa.runtime_de_contenedores()
    assert set(runtime) >= {"disponible", "runtime"} and (runtime["disponible"] or runtime["estado"] == "COMPOSE_RUNTIME_UNAVAILABLE")
    assert clamd_qa.main(["estatico"]) == 0
    informe = json.loads(capsys.readouterr().out)
    assert informe["estatico"]["CLAMD_SERVICE_PRESENT"] is True and "runtime" in informe


# CLAMD-QA-11 · contrato estático del QA: sin esperas arbitrarias, sin apagar el analizador, sin tocar producción.
def test_cq_11_contrato_estatico_del_qa() -> None:
    assert FUENTE.count("time.sleep(") == 1 and "while time.monotonic() < final" in FUENTE  # solo el sondeo de PONG, con plazo monotónico
    for prohibido in ("KONTROL_DOCUMENT_SCAN=", "retry", "pytest.skip", "xfail", "docker run", "ssh ", "globaldv"):
        assert prohibido not in FUENTE, prohibido
    assert "apt-get download" in FUENTE and "sudo" not in FUENTE and "dpkg-deb" in FUENTE
    assert "from app.modules.documents import scanning" in FUENTE  # las sondas usan el adaptador real del producto
