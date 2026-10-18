from __future__ import annotations

import json
import sys
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "qa"))
sys.path.insert(0, str(RAIZ / "resources" / "backend"))

import compose_qa  # noqa: E402


class DockerFalso:
    def __init__(self) -> None:
        self.ordenes: list[list[str]] = []
        self.clamd_parado = False
        self.abajo = False
        self.al_bajar: Callable[[], None] | None = None
        self.fallar_en: str | None = None

    def ejecutar(self, orden: list[str]) -> compose_qa.Resultado:
        self.ordenes.append(orden)
        cmd = orden[1:]

        if self.fallar_en and cmd and cmd[0] == self.fallar_en:
            return compose_qa.Resultado(1, "", "error")

        if cmd[:2] == ["compose", "version"]:
            return compose_qa.Resultado(0, "Docker Compose version v2.30.1\n", "")
        if cmd[0] == "--version":
            return compose_qa.Resultado(0, "Docker version 27.3.1, build abc\n", "")
        if cmd[0] == "info":
            return compose_qa.Resultado(0, "27.3.1\n", "")
        if cmd[0] == "build":
            return compose_qa.Resultado(0, "", "")

        if cmd[:2] == ["image", "inspect"] and "--format" in cmd:
            return compose_qa.Resultado(0, "123456\n", "")
        if cmd[:2] == ["image", "inspect"]:
            return compose_qa.Resultado(0, json.dumps([{"Size": 123456}]), "")

        if cmd[:3] == ["run", "--rm", "--entrypoint"]:
            if "kontrol-clamd" in cmd[4]:
                return compose_qa.Resultado(0, "CLAMD=1\nCONF=1\n", "")
            if "con-clamscan" in cmd[4]:
                return compose_qa.Resultado(0, "CLAMSCAN=1\nFIRMAS=1\n", "")
            return compose_qa.Resultado(0, "CLAMSCAN=0\nFIRMAS=0\n", "")

        if cmd[:2] == ["compose", "-p"]:
            args = cmd[cmd.index(str(compose_qa.OVERRIDE)) + 1 :]
            if args[0] == "ps":
                servicio = args[-1]
                if servicio == "clamd":
                    return compose_qa.Resultado(0, "id-clamd\n", "")
                if servicio == "backend":
                    return compose_qa.Resultado(0, "id-backend\n", "")
                return compose_qa.Resultado(0, "id-db\n", "")
            if args[0] == "exec":
                if "clamdscan" in args:
                    return compose_qa.Resultado(
                        0, "ClamAV 1.4.3/28153/Wed Oct 14 08:24:15 2026\n", ""
                    )
                if "grep" in args:
                    return compose_qa.Resultado(
                        0,
                        "StreamMaxLength 60M\nMaxFileSize 60M\nMaxScanSize 100M\nAlertExceedsMax yes\n",
                        "",
                    )
                return compose_qa.Resultado(0, "PONG\n", "")
            if args[0] == "stop" and "clamd" in args:
                self.clamd_parado = True
                return compose_qa.Resultado(0, "", "")
            if args[0] == "start" and "clamd" in args:
                self.clamd_parado = False
                return compose_qa.Resultado(0, "", "")
            if args[0] == "up":
                return compose_qa.Resultado(0, "", "")
            if args[0] == "down":
                self.abajo = True
                if self.al_bajar:
                    self.al_bajar()
                return compose_qa.Resultado(0, "", "")

        if cmd[0] == "inspect" and "--format" not in cmd:
            if not cmd[1]:
                return compose_qa.Resultado(1, "", "error")
            if cmd[1] == "id-clamd":
                return compose_qa.Resultado(
                    0,
                    json.dumps(
                        [
                            {
                                "HostConfig": {"PortBindings": {}},
                                "Mounts": [{"Destination": "/var/lib/clamav"}],
                                "NetworkSettings": {
                                    "Networks": {"kontrol-obs09-obs09-test": {}}
                                },
                                "State": {
                                    "Health": {
                                        "Status": (
                                            "healthy"
                                            if not self.clamd_parado
                                            else "exited"
                                        )
                                    }
                                },
                            }
                        ]
                    ),
                    "",
                )
            if cmd[1] == "id-backend":
                return compose_qa.Resultado(
                    0,
                    json.dumps(
                        [
                            {
                                "HostConfig": {"PortBindings": {}},
                                "Mounts": [{"Destination": "/app/storage"}],
                                "NetworkSettings": {
                                    "Networks": {"kontrol-obs09-obs09-test": {}}
                                },
                                "State": {"Health": {"Status": "healthy"}},
                            }
                        ]
                    ),
                    "",
                )
            return compose_qa.Resultado(
                0,
                json.dumps(
                    [
                        {
                            "HostConfig": {"PortBindings": {}},
                            "Mounts": [{"Destination": "/var/lib/postgresql/data"}],
                            "NetworkSettings": {
                                "Networks": {"kontrol-obs09-obs09-test": {}}
                            },
                            "State": {"Health": {"Status": "healthy"}},
                        }
                    ]
                ),
                "",
            )

        if cmd[0] == "inspect" and "--format" in cmd:
            if self.clamd_parado and cmd[-1] == "id-clamd":
                return compose_qa.Resultado(0, "exited\n", "")
            return compose_qa.Resultado(0, "healthy\n", "")

        if cmd[0] == "ps":
            if self.abajo:
                return compose_qa.Resultado(0, "", "")
            return compose_qa.Resultado(0, "abc\n", "")
        if cmd[0] == "network":
            if self.abajo:
                return compose_qa.Resultado(0, "", "")
            return compose_qa.Resultado(0, "net1\n", "")
        if cmd[0] == "volume":
            if self.abajo:
                return compose_qa.Resultado(0, "", "")
            return compose_qa.Resultado(0, "vol1\n", "")
        if cmd[0] == "images":
            if self.abajo:
                return compose_qa.Resultado(0, "", "")
            return compose_qa.Resultado(0, "img1\n", "")
        if cmd[0] == "image" and cmd[1] == "rm":
            return compose_qa.Resultado(0, "", "")
        return compose_qa.Resultado(0, "", "")


class BackendFalso:
    def __init__(self, docker_falso: DockerFalso) -> None:
        self.docker_falso = docker_falso
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), self._manejador(docker_falso)
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]
        self._detenido = False

    def _manejador(self, docker_falso: DockerFalso):
        class Manejador(BaseHTTPRequestHandler):
            def log_message(self, format, *args):  # type: ignore[override]
                pass

            def do_GET(self):  # type: ignore[override]
                if self.path == "/api/v1/health/live":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"{}")
                elif self.path == "/api/v1/setup/status":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(
                        json.dumps({"initialized": True, "company": "comp-1"}).encode()
                    )
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_POST(self):  # type: ignore[override]
                if self.path == "/api/v1/setup/initialize":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"status":"ok"}')
                    return
                if self.path == "/api/v1/auth/login":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"access_token":"token-falso"}')
                    return
                if not self._autenticado():
                    self.send_response(401)
                    self.end_headers()
                    return
                if self.path == "/api/v1/documentos/tipos":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"id":"tipo-1"}')
                elif self.path == "/api/v1/documentos":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"id":"doc-1"}')
                elif "/versiones" in self.path:
                    longitud = int(self.headers.get("Content-Length", 0))
                    cuerpo = self.rfile.read(longitud)
                    if b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE" in cuerpo:
                        self.send_response(422)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(
                            b'{"code":"FILE_INFECTED","message":"Virus","details":{}}'
                        )
                    elif docker_falso.clamd_parado:
                        self.send_response(422)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(
                            b'{"code":"SCAN_FAILED","message":"Timeout","details":{}}'
                        )
                    else:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(
                            b'{"id":"ver-1","file":{"security_status":"CLEAN"}}'
                        )
                else:
                    self.send_response(404)
                    self.end_headers()

            def _autenticado(self) -> bool:
                auth = self.headers.get("Authorization", "")
                company = self.headers.get("X-Kontrol-Company", "")
                return auth == "Bearer token-falso" and company == "comp-1"

        return Manejador

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def detener(self) -> None:
        if self._detenido:
            return
        self._detenido = True
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def backend_falso():
    docker_falso = DockerFalso()
    backend = BackendFalso(docker_falso)
    yield backend
    backend.detener()


def test_cq2_01_precheck_sin_docker_rc2(monkeypatch, tmp_path):
    docker_falso = DockerFalso()
    docker_falso.fallar_en = "info"
    docker = compose_qa.Docker(ejecutar=docker_falso.ejecutar)
    monkeypatch.setattr(compose_qa, "nuevo_run_id", lambda: "obs09-test")
    datos, rc = compose_qa.certificar(docker, carpeta=tmp_path)
    assert rc == 2
    assert datos["DOCKER_SERVER_REACHABLE"] == 0
    assert not any("build" in " ".join(o) for o in docker_falso.ordenes)


def test_cq2_02_construir_mide_tiempo_y_tamano():
    docker_falso = DockerFalso()
    docker = compose_qa.Docker(ejecutar=docker_falso.ejecutar)
    resultado = compose_qa.construir(docker, "Dockerfile.backend", "img:1")
    assert resultado["segundos"] >= 0
    assert resultado["bytes"] > 0


def test_cq2_03_imagenes_parsean_0_1():
    docker_falso = DockerFalso()
    docker = compose_qa.Docker(ejecutar=docker_falso.ejecutar)
    assert compose_qa.imagen_backend_sin_analizador(
        docker, "kontrol-obs09/kontrol-backend:x"
    ) == {
        "BACKEND_IMAGE_HAS_CLAMSCAN": 0,
        "BACKEND_IMAGE_HAS_SIGNATURE_DATABASE": 0,
    }
    assert compose_qa.imagen_backend_sin_analizador(
        docker, "kontrol-obs09/kontrol-backend-con-clamscan:x"
    ) == {
        "BACKEND_IMAGE_HAS_CLAMSCAN": 1,
        "BACKEND_IMAGE_HAS_SIGNATURE_DATABASE": 1,
    }
    assert compose_qa.imagen_clamd_completa(
        docker, "kontrol-obs09/kontrol-clamd:x"
    ) == {
        "CLAMD_BINARY_PRESENT": 1,
        "CLAMD_CONFIG_PRESENT": 1,
    }


def test_cq2_04_inspeccionar_extrae_datos():
    docker_falso = DockerFalso()
    docker = compose_qa.Docker(ejecutar=docker_falso.ejecutar)
    result = compose_qa.inspeccionar(docker, "id-clamd")
    assert result["puertos_publicados"] == []
    assert "/var/lib/clamav" in result["montajes"]
    assert "kontrol-obs09-obs09-test" in result["redes"]
    assert result["salud"] == "healthy"


def test_cq2_05_veredicto_composicion():
    backend_insp = {
        "puertos_publicados": ["8000/tcp"],
        "montajes": ["/app"],
        "redes": ["kontrol-obs09-test"],
        "salud": "healthy",
    }
    clamd_insp = {
        "puertos_publicados": [],
        "montajes": ["/var/lib/clamav"],
        "redes": ["kontrol-obs09-test"],
        "salud": "healthy",
    }
    v = compose_qa.veredicto_composicion(
        backend_insp, clamd_insp, "kontrol-obs09-test"
    )
    assert v["CLAMD_SERVICE_PRESENT"] == 1
    assert v["CLAMD_INTERNAL_ONLY"] == 1
    assert v["CLAMD_HOST_PORT_PUBLISHED"] == 0
    assert v["DOCUMENT_STORAGE_MOUNTED_IN_CLAMD"] == 0
    assert v["CLAMD_SIGNATURE_VOLUME_PRESENT"] == 1
    clamd_con_puerto = dict(clamd_insp, puertos_publicados=["3310/tcp"])
    v2 = compose_qa.veredicto_composicion(
        backend_insp, clamd_con_puerto, "kontrol-obs09-test"
    )
    assert v2["CLAMD_INTERNAL_ONLY"] == 0
    assert v2["CLAMD_HOST_PORT_PUBLISHED"] == 1


def test_cq2_06_clamd_runtime():
    docker_falso = DockerFalso()
    docker = compose_qa.Docker(ejecutar=docker_falso.ejecutar)
    comp = compose_qa.Composicion(docker, "p", "run", 18000, "tag")
    datos = compose_qa.clamd_runtime(comp)
    assert datos["CLAMD_VERSION"] == "1.4.3"
    assert datos["SIGNATURE_DATABASE_VERSION"] == "28153"
    assert datos["SIGNATURE_DATABASE_DATE"] == "Wed Oct 14 08:24:15 2026"
    assert datos["CLAMD_PING_RESULT"] == "PASS"
    assert datos["RUNTIME_STREAM_MAX_LENGTH"] == "60M"
    assert datos["RUNTIME_MAX_FILE_SIZE"] == "60M"
    assert datos["RUNTIME_MAX_SCAN_SIZE"] == "100M"
    assert datos["RUNTIME_ALERT_EXCEEDS_MAX"] == "yes"


def test_cq2_07_bytes_de_limite():
    assert compose_qa.bytes_de_limite("60M") == 60 * 1024 * 1024
    assert compose_qa.bytes_de_limite("100M") == 100 * 1024 * 1024
    assert compose_qa.bytes_de_limite("25M") == 25 * 1024 * 1024
    assert compose_qa.bytes_de_limite("1G") == 1024**3
    assert compose_qa.bytes_de_limite("512K") == 512 * 1024
    assert compose_qa.bytes_de_limite("4096") == 4096
    datos_pass = {
        "RUNTIME_STREAM_MAX_LENGTH": "60M",
        "RUNTIME_MAX_FILE_SIZE": "60M",
        "RUNTIME_MAX_SCAN_SIZE": "100M",
        "RUNTIME_ALERT_EXCEEDS_MAX": "yes",
    }
    assert compose_qa.completar(datos_pass)["MAX_DOCUMENT_SIZE_CONTRACT"] == "PASS"
    datos_fail = dict(datos_pass, RUNTIME_MAX_FILE_SIZE="10M")
    assert compose_qa.completar(datos_fail)["MAX_DOCUMENT_SIZE_CONTRACT"] == "FAIL"


def test_cq2_08_contrato_funcional(backend_falso):
    docker_falso = backend_falso.docker_falso
    docker = compose_qa.Docker(ejecutar=docker_falso.ejecutar)
    comp = compose_qa.Composicion(docker, "p", "run", backend_falso.port, "tag")
    backend = compose_qa.Backend(backend_falso.url)
    backend.inicializar()
    backend.entrar()
    resultados = compose_qa.contrato_funcional(comp, backend)
    assert resultados["F01_RESULT"] == "PASS"
    assert resultados["F02_RESULT"] == "PASS"
    assert resultados["F03_RESULT"] == "PASS"
    assert resultados["F04_RESULT"] == "PASS"
    assert "restart" not in " ".join(" ".join(o) for o in docker_falso.ordenes)
    assert not any("stop backend" in " ".join(o) for o in docker_falso.ordenes)


def test_cq2_09_subidas_autenticadas(backend_falso):
    backend = compose_qa.Backend(backend_falso.url)
    backend.inicializar()
    backend.entrar()
    codigo, _ = backend.subir(
        "doc-1", "x.pdf", compose_qa.PDF_LIMPIO, "application/pdf"
    )
    assert codigo == 200
    backend.token = "malo"
    codigo, _ = backend.subir(
        "doc-1", "x.pdf", compose_qa.PDF_LIMPIO, "application/pdf"
    )
    assert codigo == 401


def test_cq2_10_evidencia_saneada():
    datos = {
        "F01_RESULT": "PASS",
        "F03_RESULT": "PASS",
        "F04_RESULT": "PASS",
        "RUNTIME_STREAM_MAX_LENGTH": "60M",
        "RUNTIME_MAX_FILE_SIZE": "60M",
        "RUNTIME_MAX_SCAN_SIZE": "100M",
        "RUNTIME_ALERT_EXCEEDS_MAX": "yes",
    }
    texto = compose_qa.evidencia(datos)
    lineas = texto.splitlines()
    assert "OBS09_EXTERNAL_DOCKER_EVIDENCE" in lineas[0]
    assert lineas[1] == "REPOSITORY"
    for seccion in compose_qa.SECCIONES_EVIDENCIA:
        assert seccion in lineas
        assert f"[{seccion}]" not in texto
    assert "NOT_MEASURED" in texto
    assert compose_qa.EICAR not in texto
    assert "KONTROL_SECRET_KEY" not in texto
    assert "kontrol-obs09-sintetica" not in texto
    assert "/home/" not in texto


def test_cq2_11_esperar_sin_dormir():
    assert compose_qa.esperar(lambda: True, 10.0, "test") >= 0
    assert (
        compose_qa.esperar(lambda: True, 0.0, "test") >= 0
    )  # con plazo 0 la condición cumplida también vale
    with pytest.raises(compose_qa.EvidenciaIncompleta):
        compose_qa.esperar(lambda: False, 0.0, "test")


def test_cq2_12_certificar_limpia_si_contrato_falla(monkeypatch, tmp_path):
    docker_falso = DockerFalso()
    docker = compose_qa.Docker(ejecutar=docker_falso.ejecutar)
    monkeypatch.setattr(compose_qa, "nuevo_run_id", lambda: "obs09-test")
    backend_falso = BackendFalso(docker_falso)
    monkeypatch.setattr(
        compose_qa,
        "contrato_funcional",
        lambda comp, b: (_ for _ in ()).throw(compose_qa.EvidenciaIncompleta("fallo")),
    )
    datos, rc = compose_qa.certificar(
        docker, puerto=backend_falso.port, carpeta=tmp_path
    )
    backend_falso.detener()
    assert rc == 1
    assert "ERROR" in datos
    assert any("down" in " ".join(o) for o in docker_falso.ordenes)
    assert [
        "docker",
        "image",
        "rm",
        "-f",
        "kontrol-obs09/kontrol-backend:obs09-test",
    ] in docker_falso.ordenes
    assert [
        "docker",
        "image",
        "rm",
        "-f",
        "kontrol-obs09/kontrol-clamd:obs09-test",
    ] in docker_falso.ordenes


def test_cq2_13_certificar_completo(monkeypatch, tmp_path):
    docker_falso = DockerFalso()
    backend_falso = BackendFalso(docker_falso)
    docker_falso.al_bajar = backend_falso.detener
    docker = compose_qa.Docker(ejecutar=docker_falso.ejecutar)
    monkeypatch.setattr(compose_qa, "nuevo_run_id", lambda: "obs09-test")
    monkeypatch.setattr(
        compose_qa,
        "git",
        lambda *args: {"rev-parse": "abc", "branch": "main", "status": ""}.get(
            args[-1], ""
        ),
    )
    backend = compose_qa.Backend(backend_falso.url)
    datos, rc = compose_qa.certificar(
        docker, puerto=backend_falso.port, carpeta=tmp_path, backend=backend
    )
    backend_falso.detener()
    assert rc == 0
    assert compose_qa.aprobado(datos)
    assert (tmp_path / "obs09-test" / "evidencia.txt").exists()
    assert [
        "docker",
        "image",
        "rm",
        "-f",
        "kontrol-obs09/kontrol-backend:obs09-test",
    ] in docker_falso.ordenes
    assert [
        "docker",
        "image",
        "rm",
        "-f",
        "kontrol-obs09/kontrol-clamd:obs09-test",
    ] in docker_falso.ordenes


def test_cq2_14_contrato_estatico():
    texto = (RAIZ / "qa" / "compose_qa.py").read_text(encoding="utf-8")
    assert texto.count("time.sleep(") == 1
    assert "while time.monotonic() < final" in texto
    assert "shell=True" not in texto
    assert "retry" not in texto
    assert "pytest.skip" not in texto
    assert "xfail" not in texto
    assert "import yaml" not in texto
    assert "requests" not in texto
    assert "globaldv" not in texto
    eicar_completo = (
        "X5O!P%@AP[4\\PZX54(P^)7CC)7}$"
        + "EICAR-STANDARD-ANTIVIRUS-TEST-FILE"
        + "!$H+H*"
    )
    assert eicar_completo not in texto
    assert (
        '"X5O!P%@AP[4\\\\PZX54(P^)7CC)7}$" + "EICAR-STANDARD-ANTIVIRUS-TEST-FILE"'
        in texto
    )
    evidencia_vacia = compose_qa.evidencia({})
    lineas = evidencia_vacia.splitlines()
    assert "[REPOSITORY]" not in evidencia_vacia
    assert lineas[1] == "REPOSITORY"
