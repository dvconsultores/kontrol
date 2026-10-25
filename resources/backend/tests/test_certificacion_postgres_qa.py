"""CRQ · PostgreSQL de QA portable y fijado (Spec 054 · CERTIFICATION-HOST-PORTABILITY, G3)."""

from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import inspect
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import textwrap
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "qa"))
import certificacion_release as cr  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
RUTA_DE_ENTORNO_VIRTUAL = re.compile(r"(?:^|[\\/])\.venv(?:[\\/]|$)")


def _sha256(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def _contexto(tmp_path: Path, **opciones: object) -> cr.Contexto:
    home = tmp_path / "home"
    home.mkdir(parents=True)
    opciones_por_defecto: dict[str, object] = {
        "incluir_v0_historico": False,
        "espera_salud_min": cr.ESPERA_SALUD_MIN_POR_DEFECTO,
        "conservar_espacio": True,
        "solo_preflight": False,
    }
    opciones_por_defecto.update(opciones)
    espacio = cr.crear_espacio(home, "RUN1")
    evidencia = tmp_path / "evidencia"
    evidencia.mkdir(parents=True)
    return cr.Contexto(
        run_id="RUN1",
        opciones=argparse.Namespace(**opciones_por_defecto),
        home=home,
        espacio=espacio,
        evidencia=evidencia,
        raices=cr.raices_a_sanear(os.environ, home),
        manifiesto=cr.manifiesto_inicial("RUN1", argparse.Namespace(**opciones_por_defecto), [], []),
    )


class _RespuestaFalsa:
    def __init__(self, contenido: bytes, url: str = "https://origen.invalido/final") -> None:
        self._contenido = contenido
        self._url = url
        self._pos = 0

    def read(self, n: int = -1) -> bytes:
        if n == -1:
            resultado = self._contenido[self._pos :]
            self._pos = len(self._contenido)
            return resultado
        resultado = self._contenido[self._pos : self._pos + n]
        self._pos += len(resultado)
        return resultado

    def geturl(self) -> str:
        return self._url

    def __enter__(self) -> _RespuestaFalsa:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _abrir_url_falsa(contenido: bytes, url_final: str | None = None) -> object:
    llamadas: list[tuple[str, float]] = []
    url_observada = url_final or "https://origen.invalido/final"

    def abrir(url: str, timeout_s: float) -> _RespuestaFalsa:
        llamadas.append((url, timeout_s))
        return _RespuestaFalsa(contenido, url_observada)

    return abrir, llamadas


def _escribir_record(
    rueda: zipfile.ZipFile,
    miembros: list[tuple[str, bytes, int | None]],
) -> list[tuple[str, bytes, int | None]]:
    lineas: list[str] = []
    for nombre, contenido, modo in miembros:
        modo_final = modo or (0o755 if nombre.endswith((".so", ".so.5", "pg_ctl")) and "/bin/" in nombre else 0o644)
        sha256 = base64.urlsafe_b64encode(hashlib.sha256(contenido).digest()).rstrip(b"=").decode("ascii")
        lineas.append(f"{nombre},sha256={sha256},{len(contenido)}")
        info = zipfile.ZipInfo(nombre)
        info.external_attr = (0o100000 | modo_final) << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        rueda.writestr(info, contenido)
    rueda.writestr("pgserver-0.1.4.dist-info/RECORD", "\n".join(lineas) + "\n")
    return [(nombre, contenido, modo_final) for nombre, contenido, modo in miembros]


def _rueda_falsa(destino: Path) -> Path:
    ruta = destino / "pgserver-0.1.4-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
    miembros: list[tuple[str, bytes, int | None]] = [
        ("pgserver/pginstall/bin/pg_ctl", b"#!/bin/sh\n", 0o755),
        ("pgserver/pginstall/share/postgresql/a.txt", b"hola\n", 0o644),
        ("pgserver.libs/libpq-x.so.5", b"so\n", 0o755),
        ("pgserver/__init__.py", b"", 0o644),
    ]
    with zipfile.ZipFile(ruta, "w") as rueda:
        _escribir_record(rueda, miembros)
    return ruta


def _miembro_ar(nombre: str, contenido: bytes) -> bytes:
    nombre_codificado = nombre.encode("ascii")
    if len(nombre_codificado) > 16:
        raise ValueError("nombre ar demasiado largo")
    cabecera = (
        f"{nombre_codificado.decode('ascii'):<16}{0:<12}{0:<6}{0:<6}{'100644':<8}{len(contenido):<10}`\n".encode("ascii")
    )
    assert len(cabecera) == 60
    return cabecera + contenido + (b"\n" if len(contenido) % 2 == 1 else b"")


def _paquete_deb_falso(destino: Path, incluir_btree_gist: bool = True) -> Path:
    ruta = destino / "postgresql-16_16.2-1.pgdg120+2_amd64.deb"
    miembros: dict[str, bytes] = {
        "./usr/lib/postgresql/16/lib/btree_gist.so": b"btree_gist_binario",
        "./usr/share/postgresql/16/extension/btree_gist.control": b"btree_gist control\n",
        "./usr/share/postgresql/16/extension/btree_gist--1.2.sql": b"CREATE EXTENSION btree_gist;\n",
        "./usr/lib/postgresql/16/bin/postgres": b"no debe aparecer",
    }
    if not incluir_btree_gist:
        del miembros["./usr/lib/postgresql/16/lib/btree_gist.so"]
    data_temporal = destino / "data.tar.xz"
    with tarfile.open(data_temporal, "w:xz") as data:
        for nombre, contenido in miembros.items():
            info = tarfile.TarInfo(name=nombre)
            info.size = len(contenido)
            data.addfile(info, io.BytesIO(contenido))
    data_bytes = data_temporal.read_bytes()
    data_temporal.unlink()
    debian_binary = b"2.0\n"
    control_temporal = destino / "control.tar.xz"
    with tarfile.open(control_temporal, "w:xz") as control:
        info = tarfile.TarInfo(name="./control")
        info.size = 0
        control.addfile(info)
    control_bytes = control_temporal.read_bytes()
    control_temporal.unlink()
    ruta.write_bytes(
        b"!<arch>\n"
        + _miembro_ar("debian-binary", debian_binary)
        + _miembro_ar("control.tar.xz", control_bytes)
        + _miembro_ar("data.tar.xz", data_bytes)
    )
    return ruta


class TestPinPostgresQa:
    """CRQ-01 pin del aprovisionamiento de PostgreSQL."""

    PIN = {
        "esquema": 1,
        "postgres": "16.2",
        "rueda": {
            "fichero": "pgserver-0.1.4-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
            "url": "https://files.pythonhosted.org/packages/91/3f/3d628b09d379c368a589ca2f417e318bed7615e5df175c17d570e623b2f3/pgserver-0.1.4-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
            "sha256": "d595789b47624a3d963aa9aa6359da9be31beb7e61f1a45541953242068b8813",
        },
        "btree_gist": {
            "paquete": "postgresql-16",
            "version": "16.2-1.pgdg120+2",
            "fichero": "postgresql-16_16.2-1.pgdg120+2_amd64.deb",
            "url": "https://apt-archive.postgresql.org/pub/repos/apt/pool/main/p/postgresql-16/postgresql-16_16.2-1.pgdg120%2B2_amd64.deb",
            "sha256": "c9de1cc65e89c24e36b5ce1101396372cd4bee7d635e1debc1a0a25b19bbd699",
        },
    }

    def test_constantes_y_pin(self) -> None:
        assert not hasattr(cr, "PG_BIN")
        assert cr.POSTGRES_QA == cr.RAIZ / "qa" / "postgres_qa.json"
        assert cr.PGDATA_QA == Path("/tmp/kontrol-pgdata-045")
        assert cr.DIRECTORIO_POSTGRES_QA == "postgres-qa"
        assert cr.POSTGRES_QA in cr.REQUERIDOS
        assert (cr.RAIZ / "qa" / "postgres_qa.json").exists()
        pin = json.loads(cr.POSTGRES_QA.read_text())
        assert pin == self.PIN
        for artefacto in (pin["rueda"], pin["btree_gist"]):
            basename_url = Path(artefacto["url"].split("?", 1)[0]).name
            basename_url = basename_url.replace("%2B", "+").replace("%2b", "+")
            assert basename_url == artefacto["fichero"]
            assert len(artefacto["sha256"]) == 64
            assert artefacto["sha256"] == artefacto["sha256"].lower()
            assert "latest" not in artefacto["url"]

    def test_sin_venv_en_rutas_criticas(self) -> None:
        for funcion in (
            cr.etapa_preflight,
            cr.etapa_postgres,
            cr._pg_provision,
            cr.aprovisionar_postgres_qa,
        ):
            fuente = textwrap.dedent(inspect.getsource(funcion))
            literales = [n.value for n in ast.walk(ast.parse(fuente)) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
            assert not any(RUTA_DE_ENTORNO_VIRTUAL.search(texto) for texto in literales)
            assert "PG_BIN" not in inspect.getsource(funcion)


class TestDescargarVerificado:
    """CRQ-02 descargar_verificado sin red y con sha256."""

    def test_descarga_exitosa(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        contenido = b"contenido cierto"
        destino = tmp_path / "salida.bin"
        abrir, llamadas = _abrir_url_falsa(contenido)
        monkeypatch.setattr(cr, "_abrir_url", abrir)
        assert cr.descargar_verificado("https://origen.invalido/a.bin", _sha256(contenido), destino, 3.0) == destino
        assert destino.read_bytes() == contenido
        assert llamadas == [("https://origen.invalido/a.bin", 3.0)]
        assert [p.name for p in tmp_path.iterdir()] == ["salida.bin"]

    def test_sha256_incorrecto_sin_restos(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        abrir, _ = _abrir_url_falsa(b"otro contenido")
        monkeypatch.setattr(cr, "_abrir_url", abrir)
        destino = tmp_path / "salida.bin"
        with pytest.raises(cr.FalloDeCertificacion):
            cr.descargar_verificado("https://origen.invalido/a.bin", _sha256(b"distinto"), destino, 3.0)
        assert not destino.exists()
        assert list(tmp_path.iterdir()) == []

    def test_http_rechazado_sin_abrir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        abrir, llamadas = _abrir_url_falsa(b"")
        monkeypatch.setattr(cr, "_abrir_url", abrir)
        with pytest.raises(cr.ErrorInterno):
            cr.descargar_verificado("http://origen.invalido/a.bin", _sha256(b"x"), tmp_path / "a.bin", 3.0)
        assert llamadas == []
        assert list(tmp_path.iterdir()) == []

    def test_redireccion_a_http_rechazada(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        contenido = b"contenido"
        abrir, _ = _abrir_url_falsa(contenido, "http://origen.invalido/final")
        monkeypatch.setattr(cr, "_abrir_url", abrir)
        with pytest.raises(cr.FalloDeCertificacion):
            cr.descargar_verificado("https://origen.invalido/a.bin", _sha256(contenido), tmp_path / "a.bin", 3.0)
        assert list(tmp_path.iterdir()) == []

    def test_reutiliza_fichero_correcto(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        contenido = b"ya descargado"
        destino = tmp_path / "salida.bin"
        destino.write_bytes(contenido)
        abrir, llamadas = _abrir_url_falsa(contenido)
        monkeypatch.setattr(cr, "_abrir_url", abrir)
        assert cr.descargar_verificado("https://origen.invalido/a.bin", _sha256(contenido), destino, 3.0) == destino
        assert llamadas == []

    def test_reemplaza_fichero_incorrecto(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        contenido = b"nuevo correcto"
        destino = tmp_path / "salida.bin"
        destino.write_bytes(b"viejo incorrecto")
        abrir, llamadas = _abrir_url_falsa(contenido)
        monkeypatch.setattr(cr, "_abrir_url", abrir)
        assert cr.descargar_verificado("https://origen.invalido/a.bin", _sha256(contenido), destino, 3.0) == destino
        assert destino.read_bytes() == contenido
        assert len(llamadas) == 1
        assert [p.name for p in tmp_path.iterdir()] == ["salida.bin"]


class TestExtraerPostgres:
    """CRQ-03 extraccion de la rueda con verificacion contra RECORD."""

    def test_extraccion_y_verificacion(self, tmp_path: Path) -> None:
        rueda = _rueda_falsa(tmp_path)
        destino = tmp_path / "instalacion"
        destino.mkdir()
        assert cr.extraer_postgres_de_la_rueda(rueda, destino) == 3
        assert (destino / "pgserver" / "pginstall" / "bin" / "pg_ctl").read_bytes() == b"#!/bin/sh\n"
        assert (destino / "pgserver" / "pginstall" / "share" / "postgresql" / "a.txt").read_bytes() == b"hola\n"
        assert (destino / "pgserver.libs" / "libpq-x.so.5").read_bytes() == b"so\n"
        assert not (destino / "pgserver" / "__init__.py").exists()
        assert os.access(destino / "pgserver" / "pginstall" / "bin" / "pg_ctl", os.X_OK)
        assert cr.verificar_contra_record(rueda, destino) == []

    def test_detecta_modificacion_y_borrado(self, tmp_path: Path) -> None:
        rueda = _rueda_falsa(tmp_path)
        destino = tmp_path / "instalacion"
        destino.mkdir()
        cr.extraer_postgres_de_la_rueda(rueda, destino)
        (destino / "pgserver" / "pginstall" / "share" / "postgresql" / "a.txt").write_text("cambiado")
        assert cr.verificar_contra_record(rueda, destino) == ["pgserver/pginstall/share/postgresql/a.txt"]
        (destino / "pgserver" / "pginstall" / "bin" / "pg_ctl").unlink()
        assert cr.verificar_contra_record(rueda, destino) == [
            "pgserver/pginstall/bin/pg_ctl",
            "pgserver/pginstall/share/postgresql/a.txt",
        ]

    def test_record_incorrecto(self, tmp_path: Path) -> None:
        ruta = tmp_path / "mala.whl"
        with zipfile.ZipFile(ruta, "w") as rueda:
            info = zipfile.ZipInfo("pgserver/pginstall/bin/pg_ctl")
            info.external_attr = (0o100000 | 0o755) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            rueda.writestr(info, b"#!/bin/sh\n")
            registro = f"pgserver/pginstall/bin/pg_ctl,sha256={base64.urlsafe_b64encode(b'X' * 32).rstrip(b'=').decode()},10\n"
            rueda.writestr("pgserver-0.1.4.dist-info/RECORD", registro)
        destino = tmp_path / "instalacion"
        destino.mkdir()
        with pytest.raises(cr.FalloDeCertificacion):
            cr.extraer_postgres_de_la_rueda(ruta, destino)

    def test_miembro_fuera_de_destino(self, tmp_path: Path) -> None:
        ruta = tmp_path / "mala.whl"
        miembros = [
            ("pgserver/pginstall/../../evil", b"maligno", 0o755),
            ("pgserver/pginstall/bin/pg_ctl", b"#!/bin/sh\n", 0o755),
            ("pgserver.libs/libpq-x.so.5", b"so\n", 0o755),
        ]
        with zipfile.ZipFile(ruta, "w") as rueda:
            _escribir_record(rueda, miembros)
        destino = tmp_path / "instalacion"
        destino.mkdir()
        with pytest.raises(cr.FalloDeCertificacion):
            cr.extraer_postgres_de_la_rueda(ruta, destino)
        assert not (tmp_path / "evil").exists()
        assert not list((tmp_path / "instalacion").rglob("evil"))


class TestFicherosDeBtreeGist:
    """CRQ-04 extraccion de btree_gist desde el paquete Debian."""

    def test_ficheros_esperados(self, tmp_path: Path) -> None:
        deb = _paquete_deb_falso(tmp_path)
        ficheros = cr.ficheros_de_btree_gist(deb)
        assert set(ficheros) == {
            "lib/postgresql/btree_gist.so",
            "share/postgresql/extension/btree_gist.control",
            "share/postgresql/extension/btree_gist--1.2.sql",
        }
        assert ficheros["lib/postgresql/btree_gist.so"] == b"btree_gist_binario"
        assert ficheros["share/postgresql/extension/btree_gist.control"] == b"btree_gist control\n"
        assert ficheros["share/postgresql/extension/btree_gist--1.2.sql"] == b"CREATE EXTENSION btree_gist;\n"

    def test_no_es_ar(self, tmp_path: Path) -> None:
        fichero = tmp_path / "sucio.deb"
        fichero.write_bytes(b"esto no es un archivo ar")
        with pytest.raises(cr.FalloDeCertificacion):
            cr.ficheros_de_btree_gist(fichero)

    def test_sin_btree_gist(self, tmp_path: Path) -> None:
        deb = _paquete_deb_falso(tmp_path, incluir_btree_gist=False)
        with pytest.raises(cr.FalloDeCertificacion):
            cr.ficheros_de_btree_gist(deb)


class TestAprovisionarPostgresQa:
    """CRQ-05 aprovisionamiento portable, reutilizable y verificado."""

    def _preparar_dobles(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ctx: cr.Contexto
    ) -> tuple[dict, Path, Path, list]:
        artefactos = tmp_path / "artefactos"
        artefactos.mkdir(exist_ok=True)
        rueda = _rueda_falsa(artefactos)
        deb = _paquete_deb_falso(artefactos)
        pin = {
            "esquema": 1,
            "postgres": "16.2",
            "rueda": {
                "fichero": rueda.name,
                "url": "https://origen.invalido/rueda.whl",
                "sha256": _sha256(rueda.read_bytes()),
            },
            "btree_gist": {
                "fichero": deb.name,
                "url": "https://origen.invalido/paquete.deb",
                "sha256": _sha256(deb.read_bytes()),
            },
        }
        pin_ruta = tmp_path / "postgres_qa.json"
        pin_ruta.write_text(json.dumps(pin))
        monkeypatch.setattr(cr, "POSTGRES_QA", pin_ruta)
        llamadas: list = []

        def descargar_doble(url: str, sha256: str, destino: Path, timeout_s: float) -> Path:
            llamadas.append((url, sha256, destino, timeout_s))
            artefacto = rueda if destino.suffix == ".whl" else deb
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(artefacto, destino)
            return destino

        monkeypatch.setattr(cr, "descargar_verificado", descargar_doble)
        return pin, rueda, deb, llamadas

    def test_instalacion_fresca(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        ctx = _contexto(tmp_path)
        pin, _, _, _ = self._preparar_dobles(tmp_path, monkeypatch, ctx)
        resultado = cr.aprovisionar_postgres_qa(ctx)
        assert resultado["reutilizada"] is False
        assert resultado["postgres"] == "16.2"
        assert resultado["rueda_sha256"] == pin["rueda"]["sha256"]
        assert resultado["btree_gist_sha256"] == pin["btree_gist"]["sha256"]
        assert resultado["id"] == hashlib.sha256(json.dumps(pin).encode()).hexdigest()[:16]
        instalacion = Path(resultado["bin"]).parent
        instalacion_dir = Path(resultado["bin"]).parent.parent.parent
        assert instalacion == ctx.home / cr.DIRECTORIO_POSTGRES_QA / resultado["id"] / "pgserver" / "pginstall"
        assert instalacion_dir == ctx.home / cr.DIRECTORIO_POSTGRES_QA / resultado["id"]
        assert (instalacion / "bin" / "pg_ctl").exists()
        assert (instalacion / "lib" / "postgresql" / "btree_gist.so").exists()
        assert (instalacion / "share" / "postgresql" / "extension" / "btree_gist.control").exists()
        assert (instalacion_dir / ".completo").exists()
        assert ctx.datos["postgres_qa"] == resultado
        assert ctx.datos["herramientas"]["psql"].endswith("/bin/psql")
        assert ctx.manifiesto["POSTGRES_QA_SOURCE"]["venv_preexistente_requerido"] == 0
        assert ctx.manifiesto["POSTGRES_QA_SOURCE"]["verificada"] == 1
        assert not RUTA_DE_ENTORNO_VIRTUAL.search(resultado["bin"])
        assert resultado["bin"].startswith(str(ctx.home / cr.DIRECTORIO_POSTGRES_QA / resultado["id"]))

    def test_reutilizacion_y_descargas_siempre(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        ctx = _contexto(tmp_path)
        _, _, _, llamadas = self._preparar_dobles(tmp_path, monkeypatch, ctx)
        cr.aprovisionar_postgres_qa(ctx)
        segunda = cr.aprovisionar_postgres_qa(ctx)
        assert segunda["reutilizada"] is True
        assert len(llamadas) == 4
        assert {p.name for _, _, p, _ in llamadas[:2]} == {p.name for _, _, p, _ in llamadas[2:]}

    def test_instalacion_manipulada_invalida(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        ctx = _contexto(tmp_path)
        self._preparar_dobles(tmp_path, monkeypatch, ctx)
        resultado = cr.aprovisionar_postgres_qa(ctx)
        instalacion = Path(resultado["bin"]).parent
        (instalacion / "bin" / "pg_ctl").write_text("manipulado")
        with pytest.raises(cr.EntornoInvalido):
            cr.aprovisionar_postgres_qa(ctx)

    def test_instalacion_incompleta_se_reinstala(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        ctx = _contexto(tmp_path)
        self._preparar_dobles(tmp_path, monkeypatch, ctx)
        resultado = cr.aprovisionar_postgres_qa(ctx)
        instalacion_dir = Path(resultado["bin"]).parent.parent.parent
        (instalacion_dir / ".completo").unlink()
        (instalacion_dir / "basura").write_text("sin verificar")
        reinstalada = cr.aprovisionar_postgres_qa(ctx)
        assert reinstalada["reutilizada"] is False
        assert not (instalacion_dir / "basura").exists()
        assert (instalacion_dir / ".completo").exists()

    def test_espacios_previos_ignora_postgres_qa(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        ctx = _contexto(tmp_path)
        self._preparar_dobles(tmp_path, monkeypatch, ctx)
        cr.aprovisionar_postgres_qa(ctx)
        (ctx.home / "otro_sin_marca").mkdir()
        espacios = cr.espacios_previos(ctx.home)
        nombres = {e["nombre"] for e in espacios}
        assert "otro_sin_marca" in nombres
        assert cr.DIRECTORIO_POSTGRES_QA not in nombres
        assert (ctx.home / cr.DIRECTORIO_POSTGRES_QA).exists()


class TestEjecutableDelPostmaster:
    """CRQ-06 ejecutable_del_postmaster lee el PID y resuelve /proc."""

    def test_proceso_vivo(self, tmp_path: Path) -> None:
        pgdata = tmp_path / "pgdata"
        pgdata.mkdir()
        (pgdata / "postmaster.pid").write_text(f"{os.getpid()}\n")
        assert cr.ejecutable_del_postmaster(pgdata) == Path("/proc/self/exe").resolve()

    def test_fichero_ausente(self, tmp_path: Path) -> None:
        assert cr.ejecutable_del_postmaster(tmp_path / "no_existe") is None

    def test_pid_no_numerico(self, tmp_path: Path) -> None:
        pgdata = tmp_path / "pgdata"
        pgdata.mkdir()
        (pgdata / "postmaster.pid").write_text("abc\n")
        assert cr.ejecutable_del_postmaster(pgdata) is None

    def test_pid_muerto(self, tmp_path: Path) -> None:
        pgdata = tmp_path / "pgdata"
        pgdata.mkdir()
        (pgdata / "postmaster.pid").write_text("999999999\n")
        assert cr.ejecutable_del_postmaster(pgdata) is None


class TestPgProvision:
    """CRQ-07 _pg_provision pasa el binario QA y desactiva la compilacion."""

    def test_argumentos_y_entorno(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        ctx = _contexto(tmp_path)
        bash = shutil.which("bash")
        assert bash is not None
        ctx.datos["herramientas"] = {"bash": bash}
        ctx.datos["postgres_qa"] = {"bin": "/x/bin"}
        capturas: dict = {}

        def ejecutar_sujeto(ctx_local: cr.Contexto, etapa: str, argv: list[str], **kwargs: object) -> cr.ResultadoSujeto:
            capturas["argv"] = argv
            capturas["entorno"] = kwargs["entorno"]
            capturas["cwd"] = kwargs.get("cwd")
            capturas["etapa"] = etapa
            return cr.ResultadoSujeto(rc=0, salida="")

        monkeypatch.setattr(cr, "ejecutar_sujeto", ejecutar_sujeto)
        assert cr._pg_provision(ctx, "status", nombre="estado") == 0
        assert capturas["etapa"] == "70"
        assert capturas["argv"] == [bash, str(cr.PG_PROVISION), "status"]
        entorno = capturas["entorno"]
        assert entorno["KONTROL_PGPORT"] == "55432"
        assert entorno["KONTROL_PGBIN"] == "/x/bin"
        assert entorno["KONTROL_PGDATA"] == str(cr.PGDATA_QA)
        assert entorno["KONTROL_PG_SIN_COMPILAR"] == "1"
        assert capturas["cwd"] == cr.RAIZ


class TestEtapaPostgresProcedencia:
    """CRQ-08 etapa_postgres valida el postmaster, el puerto y la version."""

    def _preparar(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
        ctx = _contexto(tmp_path)
        binario = tmp_path / "bin"
        binario.mkdir()
        postgres = binario / "postgres"
        postgres.write_text("#!/bin/sh\necho postgres\n")
        postgres.chmod(0o755)
        llamadas: list[str] = []
        provision = {"bin": str(binario), "postgres": "16.2", "reutilizada": True}

        def aprovisionar(ctx_local: cr.Contexto) -> dict:
            llamadas.append("aprovisionar")
            ctx_local.datos["postgres_qa"] = provision
            (ctx_local.home / cr.DIRECTORIO_POSTGRES_QA).mkdir(parents=True, exist_ok=True)
            return provision

        def ejecutable_doble(pgdata: Path) -> Path | None:
            return postgres.resolve()

        def pg_provision(ctx_local: cr.Contexto, *argumentos: str, nombre: str) -> int:
            llamadas.append("pg_provision")
            return 0

        monkeypatch.setattr(cr, "aprovisionar_postgres_qa", aprovisionar)
        monkeypatch.setattr(cr, "ejecutable_del_postmaster", ejecutable_doble)
        monkeypatch.setattr(cr, "_pg_provision", pg_provision)
        return {"ctx": ctx, "postgres": postgres, "llamadas": llamadas, "binario": binario}

    def _psql_doble(self, monkeypatch: pytest.MonkeyPatch, version: str = "16.2") -> None:
        def psql(ctx_local: cr.Contexto, db: str, sql: str, nombre: str) -> str:
            if sql == "SHOW server_version":
                return version
            if sql == "SHOW port":
                return "55432"
            if "ktest" in sql:
                return "1"
            if "btree_gist" in sql:
                return "1"
            return "0"

        monkeypatch.setattr(cr, "_psql", psql)

    def test_postmaster_qa_valido(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        preparado = self._preparar(tmp_path, monkeypatch)
        self._psql_doble(monkeypatch)
        cr.etapa_postgres(preparado["ctx"])
        assert preparado["ctx"].manifiesto["POSTGRES_VERSION"] == "16.2"
        assert preparado["llamadas"][0] == "aprovisionar"
        assert "pg_provision" in preparado["llamadas"]

    def test_postmaster_fuera_del_bin_qa(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        preparado = self._preparar(tmp_path, monkeypatch)
        self._psql_doble(monkeypatch)
        externo = tmp_path / "externo"
        externo.mkdir()
        postgres_externo = externo / "postgres"
        postgres_externo.write_text("#!/bin/sh\n")
        postgres_externo.chmod(0o755)
        monkeypatch.setattr(cr, "ejecutable_del_postmaster", lambda _pgdata: postgres_externo.resolve())
        with pytest.raises(cr.EntornoInvalido):
            cr.etapa_postgres(preparado["ctx"])

    def test_postmaster_none(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        preparado = self._preparar(tmp_path, monkeypatch)
        self._psql_doble(monkeypatch)
        monkeypatch.setattr(cr, "ejecutable_del_postmaster", lambda _pgdata: None)
        with pytest.raises(cr.EntornoInvalido):
            cr.etapa_postgres(preparado["ctx"])

    def test_version_distinta(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        preparado = self._preparar(tmp_path, monkeypatch)
        self._psql_doble(monkeypatch, version="16.3")
        with pytest.raises(cr.EntornoInvalido):
            cr.etapa_postgres(preparado["ctx"])


class TestScriptPgProvision:
    """CRQ-09 pg-provision.sh respeta KONTROL_PGBIN y KONTROL_PG_SIN_COMPILAR."""

    def _preparar_script(self, tmp_path: Path) -> tuple[Path, Path, Path, Path, Path, Path]:
        repo = tmp_path / "repo"
        destino_script = repo / "qa" / "pg-provision.sh"
        destino_script.parent.mkdir(parents=True)
        shutil.copy2(cr.PG_PROVISION, destino_script)
        backend = repo / "resources" / "backend"
        backend.mkdir(parents=True)
        texto = destino_script.read_text(encoding="utf-8")
        ruta_relativa = re.search(r'PGBIN="\$\{KONTROL_PGBIN:-\$BACKEND/([^}]+)\}"', texto)
        assert ruta_relativa is not None
        decoy_bin = backend / ruta_relativa.group(1)
        decoy_bin.mkdir(parents=True)
        decoy_share = tmp_path / "share-decoy"
        decoy_share.mkdir()
        extension_decoy = decoy_share / "extension"
        extension_decoy.mkdir()
        (extension_decoy / "btree_gist.control").write_text("decoy\n")
        decoy_pg_ctl = decoy_bin / "pg_ctl"
        decoy_pg_ctl.write_text("#!/bin/sh\necho \"VENV pg_ctl $*\"\n")
        decoy_pg_ctl.chmod(0o755)
        decoy_pg_config = decoy_bin / "pg_config"
        decoy_pg_config.write_text(f"#!/bin/sh\nif [ \"$1\" = \"--sharedir\" ]; then echo {decoy_share}; else echo 'PostgreSQL 16.2'; fi\n")
        decoy_pg_config.chmod(0o755)
        bin_falso = tmp_path / "bin-falso"
        bin_falso.mkdir()
        share = tmp_path / "share"
        share.mkdir()
        pg_ctl = bin_falso / "pg_ctl"
        pg_ctl.write_text("#!/bin/sh\necho \"FAKE pg_ctl $*\"\n")
        pg_ctl.chmod(0o755)
        pg_config = bin_falso / "pg_config"
        pg_config.write_text(f"#!/bin/sh\nif [ \"$1\" = \"--sharedir\" ]; then echo {share}; else echo 'PostgreSQL 16.2'; fi\n")
        pg_config.chmod(0o755)
        bin_herramientas = tmp_path / "bin-herramientas"
        bin_herramientas.mkdir()
        for herramienta in ("curl", "make", "tar"):
            script = bin_herramientas / herramienta
            script.write_text(f"#!/bin/sh\ntouch {tmp_path/'marcador-herramienta'}\n")
            script.chmod(0o755)
        return destino_script, bin_falso, share, tmp_path / "marcador-herramienta", decoy_pg_ctl, decoy_share

    def _entorno_minimo(self, bin_falso: Path, herramientas: Path) -> dict[str, str]:
        dirs = {str(Path(p).parent) for p in (shutil.which("bash"), shutil.which("dirname"), shutil.which("awk"), shutil.which("mkdir")) if p}
        dirs.update({str(bin_falso), str(herramientas)})
        return {"PATH": ":".join(sorted(dirs)), "HOME": "/tmp"}

    def _ejecutar(
        self,
        script: Path,
        entorno: dict[str, str],
        tmp_path: Path,
        *argumentos: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [shutil.which("bash") or "bash", str(script), *argumentos],
            cwd=script.parent.parent,
            env={**os.environ, **entorno},
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_status_con_bin_qa(self, tmp_path: Path) -> None:
        script, bin_falso, _, _, _, _ = self._preparar_script(tmp_path)
        entorno = self._entorno_minimo(bin_falso, tmp_path / "bin-herramientas")
        entorno.update(
            {
                "KONTROL_PGBIN": str(bin_falso),
                "KONTROL_PGDATA": str(tmp_path / "data"),
                "KONTROL_PGPORT": "55497",
                "KONTROL_PGLOG": str(tmp_path / "pg.log"),
            }
        )
        resultado = self._ejecutar(script, entorno, tmp_path, "status")
        assert resultado.returncode == 0
        assert "FAKE pg_ctl -D" in resultado.stdout
        assert "VENV" not in resultado.stdout

    def test_bin_inexistente_falla(self, tmp_path: Path) -> None:
        script, bin_falso, _, _, _, _ = self._preparar_script(tmp_path)
        entorno = self._entorno_minimo(bin_falso, tmp_path / "bin-herramientas")
        entorno.update(
            {
                "KONTROL_PGBIN": str(tmp_path / "no-existe"),
                "KONTROL_PGDATA": str(tmp_path / "data"),
                "KONTROL_PGPORT": "55497",
                "KONTROL_PGLOG": str(tmp_path / "pg.log"),
            }
        )
        resultado = self._ejecutar(script, entorno, tmp_path, "status")
        assert resultado.returncode != 0
        assert "FAKE" not in (resultado.stdout + resultado.stderr)
        assert "VENV" not in (resultado.stdout + resultado.stderr)

    def test_sin_compilar_sin_extension(self, tmp_path: Path) -> None:
        script, bin_falso, _, marcador, _, _ = self._preparar_script(tmp_path)
        herramientas = tmp_path / "bin-herramientas"
        entorno = self._entorno_minimo(bin_falso, herramientas)
        entorno.update(
            {
                "KONTROL_PGBIN": str(bin_falso),
                "KONTROL_PGDATA": str(tmp_path / "data"),
                "KONTROL_PGPORT": "55497",
                "KONTROL_PGLOG": str(tmp_path / "pg.log"),
                "KONTROL_PG_SIN_COMPILAR": "1",
            }
        )
        resultado = self._ejecutar(script, entorno, tmp_path, "start")
        assert resultado.returncode != 0
        assert "KONTROL_PG_SIN_COMPILAR" in (resultado.stdout + resultado.stderr)
        assert not marcador.exists()
        assert "VENV" not in (resultado.stdout + resultado.stderr)
