"""CRE · Orden canónico de certificación de release (Spec 054 · CANONICALIZE-CERTIFICATION-ENVIRONMENT).

`qa/certificacion_release.py` orquesta las certificaciones de release. Aquí se prueba el contrato con dobles —funciones falsas, `tmp_path`, `monkeypatch`, tar construidos en memoria y subprocesos triviales con `/bin/sh`— y nunca la red, Docker, PostgreSQL, el registro real ni las suites reales.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import inspect
import io
import json
import os
import re
import sys
import tarfile
import urllib.error
import urllib.request
from email.message import Message
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "qa"))

import certificacion_release as cr  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]


def _contexto(tmp_path: Path, **opciones: object) -> cr.Contexto:
    """Construye un contexto mínimo de certificación sin tocar el registro real."""
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
    ctx = cr.Contexto(
        run_id="RUN1",
        opciones=argparse.Namespace(**opciones_por_defecto),
        home=home,
        espacio=espacio,
        evidencia=evidencia,
        raices=cr.raices_a_sanear(os.environ, home),
        manifiesto=cr.manifiesto_inicial("RUN1", argparse.Namespace(**opciones_por_defecto), [], []),
    )
    return ctx


class _Respuesta:
    """Respuesta falsa usable como context manager con `read`."""

    def __init__(self, cuerpo: bytes) -> None:
        self._cuerpo = io.BytesIO(cuerpo)

    def __enter__(self) -> _Respuesta:
        return self

    def __exit__(self, *_args: object) -> None:
        self._cuerpo.close()

    def read(self, n: int = -1) -> bytes:
        return self._cuerpo.read(n)


def _http_error(url: str, codigo: int, hdrs: dict[str, str] | None = None) -> urllib.error.HTTPError:
    """Crea un HTTPError sintético sin red."""
    mensaje = Message()
    for clave, valor in (hdrs or {}).items():
        mensaje[clave] = valor
    return urllib.error.HTTPError(url, codigo, "sintetico", mensaje, None)


def test_cre_01_entrada_unica_y_contrato_de_salida() -> None:
    """Protege la existencia del lanzador y el contrato de RC documentado (M16)."""
    lanzador = RAIZ / "qa" / "certificar-release.py"
    assert lanzador.exists()
    texto_lanzador = lanzador.read_text(encoding="utf-8")
    assert "certificacion_release" in texto_lanzador
    for rc in ("0", "1", "3", "4", "70"):
        assert rc in texto_lanzador
    gitignore = (RAIZ / ".gitignore").read_text(encoding="utf-8")
    assert "qa/certificaciones/" in gitignore


def test_cre_02_etapas_codigos_y_cierre() -> None:
    """Protege la estabilidad del orden y de las etapas de cierre (M15, M19)."""
    assert [etapa.codigo for etapa in cr.ETAPAS] == [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140]
    assert [etapa.codigo for etapa in cr.ETAPAS if etapa.de_cierre] == [120, 130, 140]
    assert not hasattr(cr, "_etapa_pendiente")
    assert cr.ETAPA_V0.codigo not in [etapa.codigo for etapa in cr.ETAPAS]


def test_cre_03_etapas_de_la_corrida() -> None:
    """Protege la exclusión del control histórico y la selección preflight (M09)."""
    opciones = argparse.Namespace(incluir_v0_historico=False, solo_preflight=False)
    codigos = [etapa.codigo for etapa in cr.etapas_de_la_corrida(opciones)]
    assert 95 not in codigos

    opciones = argparse.Namespace(incluir_v0_historico=True, solo_preflight=False)
    codigos = [etapa.codigo for etapa in cr.etapas_de_la_corrida(opciones)]
    assert codigos[codigos.index(90) + 1] == 95

    opciones = argparse.Namespace(incluir_v0_historico=True, solo_preflight=True)
    assert [etapa.codigo for etapa in cr.etapas_de_la_corrida(opciones)] == [0, 120, 130, 140]


def test_cre_04_ejecutar_etapas_primer_fallo_y_cierre(tmp_path: Path) -> None:
    """Protege la propagación del primer fallo y la ejecución obligatoria del cierre (M06, M16)."""
    ctx = _contexto(tmp_path / "a")
    corridas: list[tuple[int, str]] = []

    def etapa_ok(_ctx: cr.Contexto) -> dict[str, object]:
        corridas.append((10, "ok"))
        return {}

    def etapa_fallo_cert(_ctx: cr.Contexto) -> dict[str, object]:
        corridas.append((20, "cert"))
        raise cr.FalloDeCertificacion("fallo")

    def etapa_entorno(_ctx: cr.Contexto) -> dict[str, object]:
        corridas.append((30, "entorno"))
        raise cr.EntornoInvalido("entorno")

    def etapa_cierre(_ctx: cr.Contexto) -> dict[str, object]:
        corridas.append((99, "cierre"))
        return {}

    etapas = [
        cr.Etapa(10, "OK", etapa_ok),
        cr.Etapa(20, "FALLO_CERT", etapa_fallo_cert),
        cr.Etapa(30, "FALLO_ENTORNO", etapa_entorno),
        cr.Etapa(99, "CIERRE", etapa_cierre, de_cierre=True),
    ]
    assert cr.ejecutar_etapas(ctx, etapas) == cr.RC_FALLO_CERTIFICACION
    assert corridas == [(10, "ok"), (20, "cert"), (99, "cierre")]

    corridas.clear()
    ctx = _contexto(tmp_path / "b")
    etapas = [
        cr.Etapa(10, "FALLO_ENTORNO", etapa_entorno),
        cr.Etapa(20, "FALLO_CERT", etapa_fallo_cert),
        cr.Etapa(99, "CIERRE", etapa_cierre, de_cierre=True),
    ]
    assert cr.ejecutar_etapas(ctx, etapas) == cr.RC_ENTORNO_INVALIDO
    assert corridas == [(30, "entorno"), (99, "cierre")]

    def etapa_interno(_ctx: cr.Contexto) -> dict[str, object]:
        raise cr.ErrorInterno("interno")

    ctx = _contexto(tmp_path / "c")
    assert cr.ejecutar_etapas(ctx, [cr.Etapa(10, "INTERNO", etapa_interno)]) == cr.RC_INTERNO

    def etapa_runtime(_ctx: cr.Contexto) -> dict[str, object]:
        raise RuntimeError("imprevisto")

    ctx = _contexto(tmp_path / "d")
    assert cr.ejecutar_etapas(ctx, [cr.Etapa(10, "RUNTIME", etapa_runtime)]) == cr.RC_INTERNO

    def etapa_interrumpida(_ctx: cr.Contexto) -> dict[str, object]:
        raise cr.Interrumpida()

    ctx = _contexto(tmp_path / "e")
    assert cr.ejecutar_etapas(ctx, [cr.Etapa(10, "INTERRUMPIDA", etapa_interrumpida)]) == cr.RC_INTERNO
    assert ctx.datos["interrumpida"] is True


def test_cre_05_etapa_veredicto_tabla_completa(tmp_path: Path) -> None:
    """Protege la conversión exacta de RCs a estados del veredicto (M16)."""
    cases = [
        (cr.RC_FALLO_CERTIFICACION, cr.VEREDICTO_FALLO, cr.RC_FALLO_CERTIFICACION),
        (cr.RC_ENTORNO_INVALIDO, cr.VEREDICTO_ENTORNO, cr.RC_ENTORNO_INVALIDO),
        (cr.RC_INTERNO, cr.VEREDICTO_INTERNO, cr.RC_INTERNO),
        (cr.RC_PASS, cr.VEREDICTO_PASS, cr.RC_PASS),
    ]
    for i, (rc_entrada, veredicto, rc_salida) in enumerate(cases):
        ctx = _contexto(tmp_path / f"a{i}")
        ctx.rc = rc_entrada
        assert cr.etapa_veredicto(ctx)["FINAL_VERDICT"] == veredicto
        assert ctx.rc == rc_salida

    ctx = _contexto(tmp_path / "b", solo_preflight=True)
    ctx.rc = cr.RC_PASS
    assert cr.etapa_veredicto(ctx)["FINAL_VERDICT"] == cr.VEREDICTO_DIAGNOSTICO
    assert ctx.rc == cr.RC_SOLO_DIAGNOSTICO


def test_cre_06_ejecutar_sujeto_contratos_y_saneado(tmp_path: Path) -> None:
    """Protege la validación de sujetos, el timeout y el saneado de salidas (M10, M16, M17)."""
    ctx = _contexto(tmp_path)

    with pytest.raises(cr.ErrorInterno):
        cr.ejecutar_sujeto(ctx, "unidad", ["python3", "-c", "1"], cwd=ctx.home, entorno={}, timeout_s=1, nombre="mal_ruta")

    with pytest.raises(cr.ErrorInterno):
        cr.ejecutar_sujeto(ctx, "unidad", ["/bin/sh", "-c", "1"], cwd=ctx.home, entorno={}, timeout_s=float("inf"), nombre="mal_timeout")

    with pytest.raises(cr.ErrorInterno):
        cr.ejecutar_sujeto(ctx, "unidad", ["/bin/sh", "-c", "1"], cwd=ctx.home, entorno={}, timeout_s=0, nombre="mal_timeout")

    with pytest.raises(cr.ErrorInterno):
        cr.ejecutar_sujeto(ctx, "unidad", ["/bin/sh", "-c", "1"], cwd=ctx.home, entorno={}, timeout_s=1, nombre="a b")

    resultado = cr.ejecutar_sujeto(ctx, "unidad", ["/bin/sh", "-c", "exit 3"], cwd=ctx.home, entorno={}, timeout_s=5, nombre="rc3")
    assert resultado.rc == 3
    assert ctx.manifiesto["sujetos"][-1]["SUBJECT_RC"] == 3

    with pytest.raises(cr.FalloDeCertificacion):
        cr.ejecutar_sujeto(ctx, "unidad", ["/bin/sh", "-c", "sleep 5"], cwd=ctx.home, entorno={}, timeout_s=0.3, nombre="timeout")
    assert ctx.manifiesto["sujetos"][-1]["SUBJECT_RC"] is None
    assert ctx.vivos == {}

    secreto = "valor-sintetico-123"
    cr.ejecutar_sujeto(ctx, "unidad", ["/bin/sh", "-c", "echo hola"], cwd=ctx.home, entorno={"PATH": "/usr/bin:/bin", "SECRETO_SINTETICO": secreto}, timeout_s=5, nombre="limpio")
    cr.escribir_manifiesto(ctx)
    assert secreto not in (ctx.evidencia / "manifest.json").read_text(encoding="utf-8")
    assert secreto not in (ctx.evidencia / "registros" / "limpio.log").read_text(encoding="utf-8")

    cr.ejecutar_sujeto(ctx, "unidad", ["/bin/sh", "-c", f"echo {ctx.espacio}"], cwd=ctx.home, entorno={}, timeout_s=5, nombre="raiz")
    registro = (ctx.evidencia / "registros" / "raiz.log").read_text(encoding="utf-8")
    assert str(ctx.espacio) not in registro


def test_cre_07_sanear_y_sanear_objeto(tmp_path: Path) -> None:
    """Protege el saneado recursivo de raíces y credenciales en URLs (M17)."""
    raices = {"/a/b": "R1", "/a": "R2"}
    texto = "/a/b/x /a/x postgresql://u:clave@h/d"
    assert cr.sanear(texto, raices) == "R1/x R2/x postgresql://<credenciales>@h/d"
    assert cr.sanear_objeto({"url": "postgresql://u:clave@h/d", "lista": ["/a/x"]}, raices) == {"url": "postgresql://<credenciales>@h/d", "lista": ["R2/x"]}


def test_cre_08_espacio_y_cerrojo(tmp_path: Path) -> None:
    """Protege la exclusividad del espacio y del cerrojo global (M18)."""
    home = tmp_path / "home-run1"
    home.mkdir()
    espacio1 = cr.crear_espacio(home, "RUN1")
    assert espacio1.exists()
    with pytest.raises(cr.ErrorInterno):
        cr.crear_espacio(home, "RUN1")
    assert not cr.es_propio(espacio1, home, "OTRO")

    home2 = tmp_path / "home-ajeno"
    home2.mkdir()
    espacio2 = cr.crear_espacio(home2, "RUN2")
    resultado = cr.eliminar_espacio(espacio2, home, "RUN1")
    assert espacio2.exists()
    assert resultado["eliminado"] is False
    assert cr.eliminar_espacio(espacio1, home, "RUN1")["eliminado"] is True
    assert not espacio1.exists()

    cr.crear_espacio(home, "RUN3")
    huerfano = home / "huerfano"
    huerfano.mkdir()
    completo = cr.crear_espacio(home, "RUN4")
    cr.marcar_espacio(completo, "COMPLETA")

    marcas = {item["estado"] for item in cr.espacios_previos(home)}
    assert "SIN_MARCA" in marcas
    assert "EN_CURSO" in marcas
    assert "COMPLETA" not in marcas

    fd1 = cr.tomar_cerrojo(home)
    try:
        with pytest.raises(cr.FalloDePreflight):
            cr.tomar_cerrojo(home)
    finally:
        os.close(fd1)


def test_cre_09_entorno_de_sujeto() -> None:
    """Protege la eliminación de variables de Python y la preferencia del extra (M10)."""
    base = {"PATH": "/usr/bin", "PYTHONPATH": "/x", "VIRTUAL_ENV": "/v"}
    entorno = cr.entorno_de_sujeto(base)
    assert "PYTHONPATH" not in entorno
    assert "VIRTUAL_ENV" not in entorno
    assert entorno.get("PYTHONDONTWRITEBYTECODE") == "1"
    assert cr.entorno_de_sujeto(base, {"PATH": "/otro"})["PATH"] == "/otro"


def test_cre_10_hash_de_entrada_determinista_y_sensible() -> None:
    """Protege el hash canónico ante cualquier cambio de insumo (M24)."""
    base = {
        "head": "abc",
        "arbol": "t1",
        "digests": {"a": "1"},
        "locks": {"requirements.lock": "2"},
        "plataforma": "linux/amd64",
        "referencia": "r1",
        "postgres_qa": "p1",
    }
    primero = cr.hash_de_entrada(**base)
    assert cr.hash_de_entrada(**base) == primero
    assert cr.hash_de_entrada(**(base | {"head": "otro"})) != primero
    assert cr.hash_de_entrada(**(base | {"arbol": "t2"})) != primero
    assert cr.hash_de_entrada(**(base | {"digests": {"a": "2"}})) != primero
    assert cr.hash_de_entrada(**(base | {"locks": {"requirements.lock": "3"}})) != primero
    assert cr.hash_de_entrada(**(base | {"plataforma": "linux/arm64"})) != primero
    assert cr.hash_de_entrada(**(base | {"referencia": "r2"})) != primero
    assert cr.hash_de_entrada(**(base | {"postgres_qa": "p2"})) != primero


def test_cre_11_pines_diferencias_y_huella() -> None:
    """Protege la canonización de pines y las diferencias de subconjunto (M02, M04, M21)."""
    lock = """# this file was autogenerated
Foo_Bar==1.0
    indentado==2.0
#comentario
"""
    assert cr.pines_de_lock(lock) == {"foo-bar": "1.0"}
    with pytest.raises(cr.FalloDeCertificacion):
        cr.pines_de_lock("name=1\nname==1")
    with pytest.raises(cr.FalloDeCertificacion):
        cr.pines_de_lock("linea-sin-fijar\n")
    with pytest.raises(cr.FalloDeCertificacion):
        cr.pines_de_freeze("-e git+https://ejemplo/x")
    with pytest.raises(cr.FalloDeCertificacion):
        cr.pines_de_freeze("x @ file:///a")
    assert "a: 1 != 2" in cr.diferencias_de_pines({"a": "1", "b": "1"}, {"a": "2"})
    assert "falta b==1" in cr.diferencias_de_pines({"a": "1", "b": "1"}, {"a": "2"})
    assert "sobra b==1" in cr.diferencias_de_pines({"a": "1"}, {"a": "1", "b": "1"})
    assert "a: 1 != 2" in cr.diferencias_de_pines({"a": "1"}, {"a": "2"})
    assert cr.diferencias_de_subconjunto({"a": "1"}, {"a": "2", "b": "1"})
    assert not cr.diferencias_de_subconjunto({"a": "1"}, {"a": "1", "b": "1"})
    assert cr.huella_de_pines({"a": "1", "b": "2"}) == cr.huella_de_pines({"b": "2", "a": "1"})


def test_cre_12_clasificar_estado_git(tmp_path: Path) -> None:
    """Protege la clasificación del estado git y el material de la dueña (M23)."""
    entrada = " M a.py\0?? b.py\0?? requerimientos/x.docx\0R  nuevo.py\0viejo.py"
    clasificacion = cr.clasificar_estado_git(entrada)
    assert "a.py" in clasificacion["modificados"]
    assert "nuevo.py" in clasificacion["modificados"]
    assert clasificacion["no_versionados"] == ["b.py"]
    assert clasificacion["material_de_la_duena"] == ["requerimientos/x.docx"]
    assert "viejo.py" not in clasificacion["modificados"]
    assert cr.clasificar_estado_git("")["limpio"] is True


def test_cre_13_cabeceras_de_lock() -> None:
    """Protege la cabecera canónica y la regeneración byte a byte de locks (M02, M24)."""
    orden = "uv pip compile requirements.txt --python-version 3.13 --python-platform x86_64-unknown-linux-gnu --exclude-newer 2024-01-01T00:00:00Z --upgrade -o requirements.lock"
    assert cr.orden_de_cabecera("# This file was autogenerated by uv via the following command:\n#    uv pip compile requirements.txt --python-version 3.13 --python-platform x86_64-unknown-linux-gnu --exclude-newer 2024-01-01T00:00:00Z --upgrade -o requirements.lock\n") == orden
    with pytest.raises(cr.FalloDePreflight):
        cr.orden_de_cabecera("sin cabecera")
    corte = cr.corte_de_orden(orden)
    assert corte == "2024-01-01T00:00:00Z"
    with pytest.raises(cr.FalloDePreflight):
        cr.corte_de_orden("sin --exclude-newer")
    with pytest.raises(cr.FalloDePreflight):
        cr.corte_de_orden("--exclude-newer 1 --exclude-newer 2")

    argv = cr.orden_de_regeneracion("/x/uv", orden, Path("/e/l.lock"))
    texto = " ".join(argv)
    assert texto.startswith("/x/uv pip compile")
    assert "-o /e/l.lock" in texto
    assert texto.endswith("--custom-compile-command " + orden)
    assert "--no-config" in texto

    with pytest.raises(cr.FalloDePreflight):
        cr.orden_de_regeneracion("/x/uv", "uv pip compile requirements.txt", Path("/e/l.lock"))
    with pytest.raises(cr.FalloDePreflight):
        cr.orden_de_regeneracion("/x/uv", "uv pip compile requirements.txt -o", Path("/e/l.lock"))
    with pytest.raises(cr.FalloDePreflight):
        cr.orden_de_regeneracion("/x/uv", "uv pip compile -o a -o b", Path("/e/l.lock"))
    with pytest.raises(cr.FalloDePreflight):
        cr.orden_de_regeneracion("/x/uv", "python -m compile", Path("/e/l.lock"))

    runtime_texto = cr.LOCK_RUNTIME.read_text(encoding="utf-8")
    cert_texto = cr.LOCK_CERTIFICACION.read_text(encoding="utf-8")
    runtime_orden = cr.orden_de_cabecera(runtime_texto)
    cert_orden = cr.orden_de_cabecera(cert_texto)
    assert cr.corte_de_orden(runtime_orden) == cr.corte_de_orden(cr.ORDEN_LOCK_RUNTIME.format(corte=cr.corte_de_orden(runtime_orden)))
    assert cr.corte_de_orden(cert_orden) == cr.corte_de_orden(cr.ORDEN_LOCK_CERTIFICACION.format(corte=cr.corte_de_orden(cert_orden)))


def test_cre_14_salud_muestras_y_racha(tmp_path: Path) -> None:
    """Protege los umbrales de salud y el reinicio de la racha (M07)."""
    previa = {"load1": 2.0, "mem_disponible_kb": 6_000_000, "pswpin": 100}
    sana = {"load1": 2.0, "mem_disponible_kb": 6_000_000, "pswpin": 1_600}
    assert cr.muestra_sana(previa, sana, 60)
    assert not cr.muestra_sana(previa, {**sana, "load1": 3.0}, 60)
    assert not cr.muestra_sana(previa, {**sana, "mem_disponible_kb": 5_000_000}, 60)
    assert not cr.muestra_sana(previa, {**sana, "pswpin": 2_600}, 60)
    assert not cr.muestra_sana(previa, sana, 0)

    instante = [0.0]

    def dormir(segundos: float) -> None:
        instante[0] += segundos

    def reloj() -> float:
        return instante[0]

    contador = [100]

    def leer_sano() -> dict[str, float]:
        contador[0] += 1_500
        return {"load1": 2.0, "mem_disponible_kb": 6_000_000, "pswpin": contador[0]}

    resultado = cr.esperar_salud(0, leer=leer_sano, dormir=dormir, reloj=reloj)
    assert resultado["valido"] is True
    assert len(resultado["muestras"]) == cr.MUESTRAS_SANAS
    assert resultado["espera_s"] == cr.MUESTRAS_SANAS * cr.INTERVALO_SALUD_S

    instante = [0.0]
    contador = [100]

    def leer_no_sano() -> dict[str, float]:
        contador[0] += 2_500
        return {"load1": 2.0, "mem_disponible_kb": 6_000_000, "pswpin": contador[0]}

    resultado = cr.esperar_salud(0, leer=leer_no_sano, dormir=dormir, reloj=reloj)
    assert resultado["valido"] is False
    assert len(resultado["muestras"]) == 3
    assert resultado["espera_s"] == 180.0

    instante = [0.0]
    contador = [100]
    secuencia = ["base", "sana", "no-sana", "sana", "sana", "sana"]

    def lectura() -> dict[str, float]:
        contador[0] += 2_500 if secuencia.pop(0) == "no-sana" else 1_500
        return {"load1": 2.0, "mem_disponible_kb": 6_000_000, "pswpin": contador[0]}

    resultado = cr.esperar_salud(5, leer=lectura, dormir=dormir, reloj=reloj)
    assert resultado["valido"] is True
    assert len(resultado["muestras"]) == 5
    assert [m["sana"] for m in resultado["muestras"]] == [True, False, True, True, True]


def test_cre_15_degradacion_del_anfitrion(tmp_path: Path) -> None:
    """Protege la detección de degradación por incrementos, no valores absolutos."""
    antes = {"pswpout": 0, "swap_usada_kb": 2_000_000}
    despues = {"pswpout": 100, "swap_usada_kb": 2_100_000}
    assert not cr.degradacion_del_anfitrion(antes, despues, 0)["degradado"]
    assert cr.degradacion_del_anfitrion(antes, {"pswpout": 300_000, "swap_usada_kb": 2_100_000}, 0)["degradado"]
    assert cr.degradacion_del_anfitrion(antes, {"pswpout": 100, "swap_usada_kb": 4_000_000}, 0)["degradado"]
    assert cr.degradacion_del_anfitrion(antes, despues, 10)["degradado"]


def test_cre_16_cliente_de_registro_con_dobles(tmp_path: Path) -> None:
    """Protege la descarga por digest con reintentos y redirección (M03)."""
    cuerpo = b"contenido"
    digest = hashlib.sha256(cuerpo).hexdigest()

    cliente = cr.ClienteDeRegistro("library/sintetico", abrir=lambda _p, _t: _Respuesta(b'{"token": "t"}'), abrir_sin_redireccion=lambda _p, _t: _Respuesta(b""), dormir=lambda _s: None)
    with pytest.raises(cr.ErrorInterno):
        cliente.descargar("manifests/3.13.16-slim-trixie", f"sha256:{digest}", accept=cr.ACEPTA_MANIFIESTOS, timeout=1)

    cliente = cr.ClienteDeRegistro("library/sintetico", abrir=lambda _p, _t: _Respuesta(b'{"token": "t"}'), abrir_sin_redireccion=lambda p, _t: _Respuesta(cuerpo if p.full_url.endswith(digest) else b""), dormir=lambda _s: None)
    assert cliente.descargar(f"blobs/sha256:{digest}", f"sha256:{digest}", accept="capa", timeout=1, destino=None) == cuerpo

    llamadas = 0

    def respuesta_distinta(_p: urllib.request.Request, _t: float) -> _Respuesta:
        nonlocal llamadas
        llamadas += 1
        return _Respuesta(b"otro")

    cliente = cr.ClienteDeRegistro("library/sintetico", abrir=lambda _p, _t: _Respuesta(b'{"token": "t"}'), abrir_sin_redireccion=respuesta_distinta, dormir=lambda _s: None)
    with pytest.raises(cr.FalloDeCertificacion):
        cliente.descargar(f"blobs/sha256:{digest}", f"sha256:{digest}", accept="capa", timeout=1)
    assert llamadas == 1

    def token_401(peticion: urllib.request.Request, _t: float) -> _Respuesta:
        if "auth.docker.io" in peticion.full_url:
            return _Respuesta(b'{"token": "t"}')
        raise AssertionError("petición inesperada")

    respuestas_blob = iter(list[_Respuesta | urllib.error.HTTPError]([_http_error("url", 401), _Respuesta(cuerpo)]))

    def blob_con_401(_p: urllib.request.Request, _t: float) -> _Respuesta:
        siguiente = next(respuestas_blob)
        if isinstance(siguiente, urllib.error.HTTPError):
            raise siguiente
        return siguiente

    cliente = cr.ClienteDeRegistro("library/sintetico", abrir=token_401, abrir_sin_redireccion=blob_con_401, dormir=lambda _s: None)
    assert cliente.descargar(f"blobs/sha256:{digest}", f"sha256:{digest}", accept="capa", timeout=1, destino=None) == cuerpo
    assert cliente.tokens_renovados == 1

    peticiones: list[urllib.request.Request] = []

    def redireccion(peticion: urllib.request.Request, _t: float) -> None:
        raise _http_error(peticion.full_url, 307, {"Location": "https://sintetico.invalid/blob"})

    def abrir_redirigida(peticion: urllib.request.Request, _t: float) -> _Respuesta:
        if "auth.docker.io" in peticion.full_url:
            return _Respuesta(b'{"token": "t"}')
        if peticion.full_url == "https://sintetico.invalid/blob":
            peticiones.append(peticion)
            return _Respuesta(cuerpo)
        raise AssertionError("petición inesperada")

    cliente = cr.ClienteDeRegistro("library/sintetico", abrir=abrir_redirigida, abrir_sin_redireccion=redireccion, dormir=lambda _s: None)
    cliente.descargar(f"blobs/sha256:{digest}", f"sha256:{digest}", accept="capa", timeout=1)
    assert peticiones
    assert peticiones[-1].get_header("Authorization") is None

    esperas: list[float] = []

    def error_red(peticion: urllib.request.Request, _t: float) -> None:
        raise urllib.error.URLError("sin red")

    cliente = cr.ClienteDeRegistro("library/sintetico", abrir=lambda _p, _t: _Respuesta(b'{"token": "t"}'), abrir_sin_redireccion=error_red, dormir=esperas.append)
    with pytest.raises(cr.EntornoInvalido):
        cliente.descargar(f"blobs/sha256:{digest}", f"sha256:{digest}", accept="capa", timeout=1)
    assert esperas == list(cr.ESPERAS_ENTRE_DESCARGAS_S)

    def error_404(peticion: urllib.request.Request, _t: float) -> None:
        raise _http_error(peticion.full_url, 404)

    cliente = cr.ClienteDeRegistro("library/sintetico", abrir=lambda _p, _t: _Respuesta(b'{"token": "t"}'), abrir_sin_redireccion=error_404, dormir=lambda _s: None)
    with pytest.raises(cr.FalloDeCertificacion):
        cliente.descargar(f"blobs/sha256:{digest}", f"sha256:{digest}", accept="capa", timeout=1)

    destino = tmp_path / "salida.blob"
    cliente = cr.ClienteDeRegistro("library/sintetico", abrir=lambda _p, _t: _Respuesta(b'{"token": "t"}'), abrir_sin_redireccion=lambda p, _t: _Respuesta(cuerpo), dormir=lambda _s: None)
    cliente.descargar(f"blobs/sha256:{digest}", f"sha256:{digest}", accept="capa", timeout=1, destino=destino)
    assert destino.exists()
    assert not (tmp_path / "salida.blob.parcial").exists()

    with pytest.raises(cr.ErrorInterno):
        cr.ClienteDeRegistro("library/sintetico", abrir=lambda _p, _t: _Respuesta(b'{"token": "t"}'), abrir_sin_redireccion=lambda _p, _t: _Respuesta(cuerpo), dormir=lambda _s: None).descargar("etiqueta", f"sha256:{digest}", accept="capa", timeout=1)


def test_cre_17_digest_de_plataforma() -> None:
    """Protege la elección canónica de la plataforma amd64 sin variant (M24)."""
    indice = {"manifests": [{"platform": {"architecture": "amd64", "os": "linux"}, "digest": "sha256:a"}]}
    assert cr.digest_de_plataforma(indice, "linux/amd64") == "sha256:a"
    indice = {"manifests": [{"platform": {"architecture": "amd64", "os": "linux", "variant": "v8"}, "digest": "sha256:a"}, {"platform": {"architecture": "amd64", "os": "linux"}, "digest": "sha256:b"}]}
    assert cr.digest_de_plataforma(indice, "linux/amd64") == "sha256:b"
    with pytest.raises(cr.FalloDeCertificacion):
        cr.digest_de_plataforma({"manifests": [{"platform": {"architecture": "amd64", "os": "linux", "variant": "v8"}, "digest": "sha256:a"}]}, "linux/amd64")
    with pytest.raises(cr.FalloDeCertificacion):
        cr.digest_de_plataforma({"manifests": []}, "linux/amd64")


def test_cre_18_rootfs_ruta_dentro_y_capas(tmp_path: Path) -> None:
    """Protege la contención de rutas y los whiteouts de capas OCI."""
    with pytest.raises(cr.FalloDeCertificacion):
        cr.ruta_dentro(tmp_path, "/etc/x")
    with pytest.raises(cr.FalloDeCertificacion):
        cr.ruta_dentro(tmp_path, "../x")
    assert cr.ruta_dentro(tmp_path, "a") == tmp_path / "a"

    rootfs = tmp_path / "rootfs"
    rootfs.mkdir()
    (rootfs / "borrar.txt").write_text("viejo", encoding="utf-8")
    (rootfs / "dir").mkdir()
    (rootfs / "dir" / "viejo.txt").write_text("viejo-dir", encoding="utf-8")

    capa1 = tmp_path / "capa1.tar"
    with tarfile.open(capa1, "w") as tar:
        tar.add(rootfs / "borrar.txt", arcname="borrar.txt")
        tar.add(rootfs / "dir" / "viejo.txt", arcname="dir/viejo.txt")
    cr.aplicar_capa(capa1, rootfs)

    capa2_dir = tmp_path / "capa2"
    capa2_dir.mkdir()
    (capa2_dir / "dir").mkdir()
    (capa2_dir / "dir" / "nuevo.txt").write_text("nuevo-dir", encoding="utf-8")
    (capa2_dir / ".wh.borrar.txt").write_text("", encoding="utf-8")
    (capa2_dir / "dir" / ".wh..wh..opq").write_text("", encoding="utf-8")
    capa2 = tmp_path / "capa2.tar"
    with tarfile.open(capa2, "w") as tar:
        tar.add(capa2_dir / ".wh.borrar.txt", arcname=".wh.borrar.txt")
        tar.add(capa2_dir / "dir" / "nuevo.txt", arcname="dir/nuevo.txt")
        tar.add(capa2_dir / "dir" / ".wh..wh..opq", arcname="dir/.wh..wh..opq")
    cr.aplicar_capa(capa2, rootfs)
    assert not (rootfs / "borrar.txt").exists()
    assert not (rootfs / "dir" / "viejo.txt").exists()
    assert (rootfs / "dir" / "nuevo.txt").read_text(encoding="utf-8") == "nuevo-dir"


def test_cre_19_ca_y_control(tmp_path: Path) -> None:
    """Protege la regeneración del bundle de CA y el parseo de control."""
    rootfs = tmp_path / "rootfs"
    (rootfs / "etc").mkdir(parents=True)
    (rootfs / "usr" / "share" / "ca-certificates").mkdir(parents=True)
    (rootfs / "usr" / "share" / "ca-certificates" / "uno.crt").write_text("cert-uno\n", encoding="utf-8")
    (rootfs / "usr" / "share" / "ca-certificates" / "dos.crt").write_text("cert-dos\n", encoding="utf-8")
    (rootfs / "etc" / "ca-certificates.conf").write_text("!x\n#comentario\nuno.crt\ndos.crt\n", encoding="utf-8")
    presentes = {"v1.crt", "v2.crt", "nuevo.crt"}
    del_paquete = {"v1.crt", "v2.crt"}
    assert cr.crts_a_retirar(presentes, del_paquete) == ["nuevo.crt"]
    assert cr.regenerar_bundle(rootfs) == 2
    bundle = (rootfs / "etc" / "ssl" / "certs" / "ca-certificates.crt").read_text(encoding="utf-8")
    assert bundle == "cert-uno\ncert-dos\n"
    (rootfs / "etc" / "ca-certificates.conf").write_text("#solo comentario\n", encoding="utf-8")
    with pytest.raises(cr.FalloDeCertificacion):
        cr.regenerar_bundle(rootfs)
    assert cr.campos_de_control("Package: a\nVersion: 1:2-3\n") == {"Package": "a", "Version": "1:2-3"}


def test_cre_20_texto_del_lanzador_y_entorno_virtual(tmp_path: Path) -> None:
    """Protege el lanzador con rutas citadas y el pyvenv.cfg reproducible (M10)."""
    texto = cr.texto_del_lanzador(Path("/r x"), Path("/v"), Path("/b"), Path("/m"))
    assert "--argv0 /v/bin/python" in texto
    assert texto.rstrip().endswith("/usr/local/bin/python3.13' \"$@\"")
    assert "'/r x/usr/local/lib:/r x/usr/lib/x86_64-linux-gnu:/r x/lib/x86_64-linux-gnu'" in texto

    venv = tmp_path / "entorno-v6"
    resultado = cr.escribir_entorno_virtual(venv, Path("/r x"), Path("/b"), Path("/m"), "3.13.16")
    assert resultado == venv / "bin" / "python"
    for lanzador in cr.LANZADORES:
        assert (venv / "bin" / lanzador).exists()
        assert os.access(venv / "bin" / lanzador, os.X_OK)
    cfg = (venv / "pyvenv.cfg").read_text(encoding="utf-8")
    assert "include-system-site-packages = false" in cfg


def test_cre_21_base_certificada_real() -> None:
    """Protege la congruencia de la base certificada con el Dockerfile real (M03, M24)."""
    base = cr.leer_base_certificada()
    bi = base["base_image"]
    ca = base["ca_certificates"]
    for clave in ("index_digest", "platform_manifest_digest", "config_digest"):
        assert bi[clave].startswith("sha256:")
        assert len(bi[clave][7:]) == 64
    assert ca["deb_sha256"]
    assert len(ca["deb_sha256"]) == 64
    dockerfile = cr.DOCKERFILE_BACKEND.read_text(encoding="utf-8")
    coincidencias = cr.FROM_CERTIFICADO.findall(dockerfile)
    assert len(coincidencias) == 1
    assert coincidencias[0][2] == bi["index_digest"]


# --- T5b: pruebas por etapa, estructurales y de main ---


def test_cre_41_entorno_invalido_en_cualquier_etapa_marca_el_manifiesto(tmp_path: Path) -> None:
    """Un INVALID_ENVIRONMENT de una etapa que no es la 10 ni la 90 deja ENVIRONMENT_VALIDITY = INVALID."""
    ctx = _contexto(tmp_path / "a")
    ctx.manifiesto["ENVIRONMENT_VALIDITY"] = "VALID"

    def etapa_con_salto(_ctx: cr.Contexto) -> dict[str, object]:
        raise cr.EntornoInvalido("salto de reloj durante la suite backend")

    rc = cr.ejecutar_etapas(ctx, [cr.Etapa(80, "BACKEND_CERTIFICATION", etapa_con_salto)])
    assert rc == cr.RC_ENTORNO_INVALIDO
    assert ctx.manifiesto["ENVIRONMENT_VALIDITY"] == "INVALID"

    ctx = _contexto(tmp_path / "b")
    ctx.manifiesto["ENVIRONMENT_VALIDITY"] = "VALID"

    def etapa_con_fallo(_ctx: cr.Contexto) -> dict[str, object]:
        raise cr.FalloDeCertificacion("fallo de producto")

    assert cr.ejecutar_etapas(ctx, [cr.Etapa(80, "BACKEND_CERTIFICATION", etapa_con_fallo)]) == cr.RC_FALLO_CERTIFICACION
    assert ctx.manifiesto["ENVIRONMENT_VALIDITY"] == "VALID"


def test_cre_40_el_tick_del_planificador_es_un_ayudante_en_v6c() -> None:
    """El tick del planificador lo lanza el ayudante E2E con V6C: es ayudante, no producto."""
    assert cr.marca_de("<rootfs>/ld-linux --argv0 /v6c/bin/python <rootfs>/python3.13 -m app.modules.scheduler tick") == ("ayudante", "app.modules.scheduler")
    registros = [
        {"tipo": "producto", "marca": "app.main:app", "argv0": "/v6r/bin/python", "python_mapeado": ["3.13"]},
        {"tipo": "producto", "marca": "central_authority.main:app", "argv0": "/v6r/bin/python", "python_mapeado": ["3.13"]},
        {"tipo": "ayudante", "marca": "app.modules.scheduler", "argv0": "/v6c/bin/python", "python_mapeado": ["3.13"]},
    ]
    procedencia = cr.clasificar_procedencia(registros, "/v6r/bin/python", "/v6c/bin/python")
    assert procedencia["fuera_de_lugar"] == []
    assert procedencia["ayudantes"] == 1




def test_cre_37_etapa_subconjunto_exige_igualdad_runtime(tmp_path: Path) -> None:
    """Mata M02: la etapa 60 debe fallar ante diferencias entre V6R y V6C."""
    ctx = _contexto(tmp_path / "a")
    ctx.datos["freeze_v6r"] = {"fastapi": "1.0", "pydantic": "2.0"}
    ctx.datos["freeze_v6c"] = {"fastapi": "1.0", "pydantic": "2.1", "pytest": "9.0"}
    with pytest.raises(cr.FalloDeCertificacion):
        cr.etapa_subconjunto(ctx)
    assert ctx.manifiesto["RUNTIME_SUBSET_EQUAL"] == 0

    ctx = _contexto(tmp_path / "b")
    ctx.datos["freeze_v6r"] = {"fastapi": "1.0", "pydantic": "2.0"}
    ctx.datos["freeze_v6c"] = {"fastapi": "1.0", "pydantic": "2.0", "pytest": "9.0"}
    assert cr.etapa_subconjunto(ctx) == {"runtime": 2, "certificacion": 3, "iguales": 2}
    assert ctx.manifiesto["RUNTIME_SUBSET_EQUAL"] == 1

    ctx = _contexto(tmp_path / "c")
    ctx.datos["freeze_v6r"] = {"fastapi": "1.0", "pydantic": "2.0"}
    with pytest.raises(cr.ErrorInterno):
        cr.etapa_subconjunto(ctx)


def test_cre_38_ejecutar_sujeto_rechaza_programa_relativo_existente(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mata M10: ejecutar_sujeto exige ruta absoluta aunque el relativo exista."""
    prog = tmp_path / "prog"
    prog.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    prog.chmod(0o755)
    monkeypatch.chdir(tmp_path)
    ctx = _contexto(tmp_path / "ctx")
    with pytest.raises(cr.ErrorInterno):
        cr.ejecutar_sujeto(
            ctx,
            "00",
            ["prog"],
            cwd=tmp_path,
            entorno={"PATH": "/usr/bin:/bin"},
            timeout_s=5,
            nombre="relativo",
        )
    assert (
        cr.ejecutar_sujeto(
            ctx,
            "00",
            [str(prog)],
            cwd=tmp_path,
            entorno={"PATH": "/usr/bin:/bin"},
            timeout_s=5,
            nombre="absoluto",
        ).rc
        == 0
    )


def test_cre_39_resultado_de_e2e_exige_autoridad_en_v6r() -> None:
    """Mata M12: resultado_de_e2e debe rechazar autoridad distinta del V6R saneado."""
    manifiesto = _manifiesto_e2e_valido()
    mutado = json.loads(json.dumps(manifiesto))
    mutado["interprete_de_producto"]["autoridad"] = "/v6c/bin/python"
    with pytest.raises(cr.FalloDeCertificacion):
        cr.resultado_de_e2e(mutado, 0, "/v6r/bin/python")
    cr.resultado_de_e2e(manifiesto, 0, "/v6r/bin/python")




# CRE-32: etapa_manifiesto (M19)
def test_cre32_etapa_manifiesto_sin_fallo_previo_con_campos_not_run_lanza_error_interno(tmp_path, monkeypatch):
    """Mutación: sin fallo previo y campos en NOT_RUN lanza ErrorInterno."""
    ctx = _contexto(tmp_path / "cre32-a")
    with pytest.raises(cr.ErrorInterno):
        cr.etapa_manifiesto(ctx)


def test_cre32_etapa_manifiesto_con_fallo_previo_genera_hash_canonico(tmp_path, monkeypatch):
    """Mutación: con GIT_HEAD y fallo previo genera hash sha256:."""
    ctx = _contexto(tmp_path / "cre32-b")
    ctx.fallo_previo = True
    ctx.manifiesto["GIT_HEAD"] = "a" * 40
    ctx.manifiesto["CERTIFICATION_INPUT_TREE_HASH"] = "b" * 40
    monkeypatch.setattr(cr, "arbol_certificado", lambda ctx_interno, raiz, trabajo: {"arbol": "b" * 40, "excluidos_con_cambios": []})
    detalle = cr.etapa_manifiesto(ctx)
    assert isinstance(detalle["CANONICAL_RUN_INPUT_HASH"], str)
    assert detalle["CANONICAL_RUN_INPUT_HASH"].startswith("sha256:")
    assert ctx.manifiesto["TREE_HASH_BOUND_TO_RUN_INPUT"] == 1


def test_cre32_etapa_manifiesto_solo_preflight_no_exige_campos(tmp_path, monkeypatch):
    """Mutación: solo_preflight=True no exige campos."""
    ctx = _contexto(tmp_path / "cre32-c", solo_preflight=True)
    detalle = cr.etapa_manifiesto(ctx)
    assert "CANONICAL_RUN_INPUT_HASH" in detalle


# CRE-33: etapa_v0_historico (M08, M09)
def test_cre33_v0_python_inexistente_no_disponible(tmp_path, monkeypatch):
    """Mutación: V0_PYTHON inexistente produce NO_DISPONIBLE."""
    ctx = _contexto(tmp_path / "cre33-a")
    monkeypatch.setattr(cr, "V0_PYTHON", tmp_path / "no-existe" / "python")
    estado = cr.etapa_v0_historico(ctx)
    assert estado["estado"] == "NO_DISPONIBLE"


def test_cre33_fallo_de_certificacion_anota_error_sin_lanzar(tmp_path, monkeypatch):
    """Mutación: FalloDeCertificacion anota ERROR sin lanzar."""
    ctx = _contexto(tmp_path / "cre33-b")
    monkeypatch.setattr(cr, "V0_PYTHON", Path(sys.executable))

    def _ejecutar_sujeto(*args, **kwargs):
        raise cr.FalloDeCertificacion("x")

    monkeypatch.setattr(cr, "ejecutar_sujeto", _ejecutar_sujeto)
    estado = cr.etapa_v0_historico(ctx)
    assert estado["sqlite"]["estado"] == "ERROR"
    assert estado["e2e"]["estado"] == "ERROR"
    assert ctx.manifiesto["V0_STATUS"]["afecta_veredicto"] is False


def test_cre33_rc_1_anota_fail_sin_lanzar(tmp_path, monkeypatch):
    """Mutación: rc 1 anota FAIL sin lanzar."""
    ctx = _contexto(tmp_path / "cre33-c")
    monkeypatch.setattr(cr, "V0_PYTHON", Path(sys.executable))

    def _ejecutar_sujeto(*args, **kwargs):
        return cr.ResultadoSujeto(rc=1, salida="")

    monkeypatch.setattr(cr, "ejecutar_sujeto", _ejecutar_sujeto)
    estado = cr.etapa_v0_historico(ctx)
    assert estado["sqlite"]["rc"] == 1
    assert estado["sqlite"]["estado"] == "FAIL"
    assert estado["e2e"]["rc"] == 1
    assert estado["e2e"]["estado"] == "FAIL"


# CRE-34: estructurales (M03, M08, M10, M22)
def _fuente_de(funcion) -> str:
    return inspect.getsource(funcion)


def _ast_del_modulo() -> ast.Module:
    return ast.parse(Path(cr.__file__).read_text())


def test_cre34_etapas_no_referencian_executables_ni_venv():
    """Mutación: ninguna etapa referencia sys.executable, V0_PYTHON ni .venv."""
    prohibidos = ("sys.executable", "V0_PYTHON")
    ruta_de_entorno = re.compile(r"(?:^|[\\/])\.venv(?:[\\/]|$)")
    for etapa in cr.ETAPAS:
        fuente = _fuente_de(etapa.funcion)
        for token in prohibidos:
            assert token not in fuente, f"{etapa.codigo} referencia {token}"
        literales = [n.value for n in ast.walk(ast.parse(fuente)) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        assert not any(ruta_de_entorno.search(texto) for texto in literales), f"{etapa.codigo} construye una ruta de entorno virtual"


def test_cre34_etapa_v6r_usa_lock_runtime_no_certificacion():
    """Mutación: etapa_v6r usa LOCK_RUNTIME y no LOCK_CERTIFICACION."""
    fuente = _fuente_de(cr.etapa_v6r)
    assert "LOCK_RUNTIME" in fuente
    assert "LOCK_CERTIFICACION" not in fuente


def test_cre34_etapa_v6c_usa_lock_certificacion():
    """Mutación: etapa_v6c usa LOCK_CERTIFICACION."""
    fuente = _fuente_de(cr.etapa_v6c)
    assert "LOCK_CERTIFICACION" in fuente


def test_cre34_etapa_certificacion_v6r_usa_lock_runtime():
    """Mutación: etapa_certificacion_v6r usa LOCK_RUNTIME."""
    fuente = _fuente_de(cr.etapa_certificacion_v6r)
    assert "LOCK_RUNTIME" in fuente


def test_cre34_etapa_v6r_no_referencia_tag():
    """Mutación: etapa_v6r no contiene ["tag"] (M03)."""
    fuente = _fuente_de(cr.etapa_v6r)
    assert '["tag"]' not in fuente


def test_cre34_modulo_no_contiene_shell_true():
    """Mutación: el módulo no contiene shell=True."""
    fuente = Path(cr.__file__).read_text()
    assert "shell=True" not in fuente


def test_cre34_imports_de_nivel_superior_son_stdlib():
    """Mutación: imports de nivel superior son stdlib (__future__ incluido)."""
    arbol = _ast_del_modulo()
    importes = []
    for nodo in arbol.body:
        if isinstance(nodo, ast.Import):
            importes.extend(alias.name.split(".")[0] for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
            importes.append(nodo.module.split(".")[0])
    stdlib = set(sys.stdlib_module_names) | {"__future__"}
    no_stdlib = [nombre for nombre in importes if nombre not in stdlib]
    assert not no_stdlib, f"imports no stdlib: {no_stdlib}"


def test_cre34_except_exception_aparece_exactamente_una_vez():
    """Mutación: 'except Exception' aparece exactamente una vez."""
    modulo = _ast_del_modulo()
    capturas = [
        nodo
        for nodo in ast.walk(modulo)
        if isinstance(nodo, ast.ExceptHandler) and isinstance(nodo.type, ast.Name) and nodo.type.id == "Exception"
    ]
    assert len(capturas) == 1
    funcion = next(
        nodo for nodo in ast.walk(modulo) if isinstance(nodo, ast.FunctionDef) and nodo.name == "ejecutar_etapas"
    )
    assert any(
        isinstance(nodo, ast.ExceptHandler) and isinstance(nodo.type, ast.Name) and nodo.type.id == "Exception"
        for nodo in ast.walk(funcion)
    )


# CRE-35: main de punta a punta (M18, M19)
def _etapa(ctx, resultado=None, excepcion=None, fijar_git_head=False):
    def _funcion(ctx):
        if fijar_git_head:
            ctx.manifiesto["GIT_HEAD"] = "a" * 40
        if excepcion is not None:
            raise excepcion
        return resultado

    return cr.Etapa(0, "FALSA", _funcion)


def _main_con_etapas(tmp_path, etapas_falsas, argv=None):
    home = tmp_path / "cre35-home" / "home"
    evidencia = tmp_path / "cre35-evidencia" / "evidencia"
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("KONTROL_QA_CERT_HOME", str(home))
    monkeypatch.setattr(cr, "EVIDENCIA", evidencia)
    monkeypatch.setattr(cr, "puerto_ocupado", lambda puerto: False)
    cierre = tuple(e for e in cr.ETAPAS if e.codigo in (120, 130, 140))
    monkeypatch.setattr(cr, "ETAPAS", tuple(etapas_falsas) + cierre)
    try:
        return cr.main([] if argv is None else argv)
    finally:
        monkeypatch.undo()


def test_cre35_main_fallo_devuelve_uno_y_manifiesto_certification_failure(tmp_path):
    """Mutación: etapa falsa que falla produce manifiesto CERTIFICATION_FAILURE y RC 1."""
    home = tmp_path / "cre35-a-home" / "home"
    evidencia = tmp_path / "cre35-a-evidencia" / "evidencia"
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("KONTROL_QA_CERT_HOME", str(home))
    monkeypatch.setattr(cr, "EVIDENCIA", evidencia)
    monkeypatch.setattr(cr, "puerto_ocupado", lambda puerto: False)
    cierre = tuple(e for e in cr.ETAPAS if e.codigo in (120, 130, 140))
    etapas = (
        _etapa(None, fijar_git_head=True),
        _etapa(None, excepcion=cr.FalloDeCertificacion("x")),
        *cierre,
    )
    monkeypatch.setattr(cr, "ETAPAS", etapas)
    try:
        rc = cr.main([])
    finally:
        monkeypatch.undo()
    assert rc == 1
    manifiestos = list(evidencia.rglob("manifest.json"))
    assert len(manifiestos) == 1
    manifiesto = json.loads(manifiestos[0].read_text())
    assert manifiesto["FINAL_VERDICT"] == "CERTIFICATION_FAILURE"
    assert manifiesto["RC"] == 1
    for hijo in home.iterdir():
        assert not hijo.is_dir(), f"queda directorio de corrida: {hijo}"


def test_cre35_main_etapas_que_pasan_sin_campos_devuelve_70(tmp_path):
    """Mutación: etapas que pasan sin fijar campos devuelven 70."""
    rc = _main_con_etapas(
        tmp_path,
        (_etapa({"ok": True}),),
    )
    assert rc == 70


def test_cre35_main_solo_preflight_devuelve_4(tmp_path):
    """Mutación: solo-preflight con etapa 0 que pasa devuelve 4."""
    rc = _main_con_etapas(
        tmp_path,
        (_etapa({"ok": True}),),
        argv=["--solo-preflight"],
    )
    assert rc == 4


def test_cre35_main_solo_preflight_nunca_devuelve_cero(tmp_path):
    """Mutación: solo-preflight nunca devuelve 0."""
    rc = _main_con_etapas(
        tmp_path,
        (_etapa({"ok": True}),),
        argv=["--solo-preflight"],
    )
    assert rc != 0


def test_cre35_main_home_relativo_devuelve_70(tmp_path):
    """Mutación: KONTROL_QA_CERT_HOME relativo devuelve 70."""
    evidencia = tmp_path / "cre35-relativo-evidencia" / "evidencia"
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("KONTROL_QA_CERT_HOME", "relativo")
    monkeypatch.setattr(cr, "EVIDENCIA", evidencia)
    monkeypatch.setattr(cr, "puerto_ocupado", lambda puerto: False)
    cierre = tuple(e for e in cr.ETAPAS if e.codigo in (120, 130, 140))
    monkeypatch.setattr(cr, "ETAPAS", (_etapa({"ok": True}), *cierre))
    try:
        rc = cr.main([])
    finally:
        monkeypatch.undo()
    assert rc == 70


# CRE-36: interrupción
def test_cre36_interrupcion_devuelve_70_y_manifiesto_interrupted(tmp_path):
    """Mutación: Interrumpida produce manifiesto INTERRUPTED y RC 70."""
    def _interrumpir(ctx):
        raise cr.Interrumpida("SIGINT")

    etapa_interruptora = cr.Etapa(0, "INTERRUMPE", _interrumpir)
    home = tmp_path / "cre36-home" / "home"
    evidencia = tmp_path / "cre36-evidencia" / "evidencia"
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("KONTROL_QA_CERT_HOME", str(home))
    monkeypatch.setattr(cr, "EVIDENCIA", evidencia)
    monkeypatch.setattr(cr, "puerto_ocupado", lambda puerto: False)
    cierre = tuple(e for e in cr.ETAPAS if e.codigo in (120, 130, 140))
    monkeypatch.setattr(cr, "ETAPAS", (etapa_interruptora, *cierre))
    try:
        rc = cr.main([])
    finally:
        monkeypatch.undo()
    assert rc == 70
    manifiestos = list(evidencia.rglob("manifest.json"))
    assert len(manifiestos) == 1
    manifiesto = json.loads(manifiestos[0].read_text())
    assert manifiesto["FINAL_VERDICT"] == "INTERRUPTED"
def _manifiesto_e2e_valido(run_id: str = "run-1", **mutaciones) -> dict:
    manifiesto = {
        "run_id": run_id,
        "codigo_de_salida": 0,
        "suite": {
            "codigo": 0,
            "resumen": {"passed": 3, "failed": 0, "skipped": 0, "flaky": 0, "did not run": 0},
            "segundos": 12.5,
        },
        "interpretes": {"paridad": 1},
        "interprete_de_producto": {
            "modo": "RUNTIME_SEPARADO",
            "herramientas_de_prueba": [],
            "paridad_runtime": 1,
            "ejecutable": "/v6r/bin/python",
            "autoridad": "/v6r/bin/python",
        },
        "limpieza": {"resultado": "LIMPIA"},
        "protegidas_sin_cambios": True,
    }
    manifiesto.update(mutaciones)
    return manifiesto


def _contexto_e2e(tmp_path: Path) -> cr.Contexto:
    ctx = _contexto(tmp_path / "e2e", solo_preflight=False)
    ctx.datos["v6r"] = {"python": "/v6r/bin/python"}
    ctx.datos["v6c"] = {"python": "/v6c/bin/python"}
    return ctx


def _registro_procedencia(tipo: str, marca: str, argv0: str, python_mapeado: list[str] | None = None) -> dict:
    return {"tipo": tipo, "marca": marca, "argv0": argv0, "python_mapeado": python_mapeado or ["3.13"]}


def test_cre28_resultado_de_e2e_pasa_con_manifiesto_valido():
    """M00: un manifiesto válido pasa sin excepción."""
    resultado = cr.resultado_de_e2e(_manifiesto_e2e_valido(), 0, "/v6r/bin/python")
    assert resultado["passed"] == 3
    assert resultado["run_id"] == "run-1"


@pytest.mark.parametrize(
    "mutacion",
    [
        {"interpretes": {"paridad": 0}},
        {"interprete_de_producto": {"modo": "UN_SOLO_ENTORNO"}},
        {"interprete_de_producto": {"herramientas_de_prueba": ["pytest"]}},
        {"interprete_de_producto": {"paridad_runtime": 0}},
        {"interprete_de_producto": {"ejecutable": "/otro/bin/python"}},
        {"interprete_de_producto": {"autoridad": "/otra/bin/python"}},
        {"suite": {"resumen": {"failed": 1}}},
        {"suite": {"resumen": {"flaky": 1}}},
        {"suite": {"resumen": {"did not run": 1}}},
        {"limpieza": {"resultado": "SUCIA"}},
        {"protegidas_sin_cambios": False},
    ],
)
def test_cre28_resultado_de_e2e_falla_ante_variante(mutacion):
    """M11, M12: cada variante inválida debe fallar con FalloDeCertificacion."""
    with pytest.raises(cr.FalloDeCertificacion):
        cr.resultado_de_e2e(_manifiesto_e2e_valido(**mutacion), 0, "/v6r/bin/python")


def test_cre28_resultado_de_e2e_falla_con_rc_distinto():
    """M00: rc distinto de cero debe fallar."""
    with pytest.raises(cr.FalloDeCertificacion):
        cr.resultado_de_e2e(_manifiesto_e2e_valido(), 1, "/v6r/bin/python")


def test_cre28_resultado_de_e2e_falla_sin_clave_interpretes():
    """M00: sin la clave interpretes debe informar manifiesto incompleto."""
    manifiesto = _manifiesto_e2e_valido()
    del manifiesto["interpretes"]
    with pytest.raises(cr.FalloDeCertificacion) as exc:
        cr.resultado_de_e2e(manifiesto, 0, "/v6r/bin/python")
    assert "manifiesto E2E incompleto" in str(exc.value)


def test_cre29_marca_de_y_argv0_declarado():
    """M00: clasifica marcas de producto, ayudante y argv0 declarado."""
    assert cr.marca_de("python app.main:app") == ("producto", "app.main:app")
    assert cr.marca_de("python central_authority.main:app") == ("producto", "central_authority.main:app")
    assert cr.marca_de("python alcance_de_usuario.py") == ("ayudante", "alcance_de_usuario.py")
    assert cr.marca_de("python otra_cosa.py") is None
    assert cr.argv0_declarado(["--argv0", "/v6c/bin/python", "x"]) == "/v6c/bin/python"
    assert cr.argv0_declarado(["x", "y"]) is None


def test_cre29_clasificar_procedencia_sin_fuera_de_lugar():
    """M00: producto y autoridad en V6R, ayudante en V6C, python 3.13."""
    registros = [
        _registro_procedencia("producto", "app.main:app", "/v6r/bin/python"),
        _registro_procedencia("producto", "central_authority.main:app", "/v6r/bin/python"),
        _registro_procedencia("ayudante", "alcance_de_usuario.py", "/v6c/bin/python"),
    ]
    resumen = cr.clasificar_procedencia(registros, "/v6r/bin/python", "/v6c/bin/python")
    assert resumen["fuera_de_lugar"] == []
    assert resumen["backend_visto"] is True
    assert resumen["autoridad_vista"] is True
    assert resumen["producto"] == 2
    assert resumen["ayudantes"] == 1


def test_cre29_clasificar_procedencia_autoridad_con_argv0_v6c():
    """M12: autoridad con argv0 de V6C queda fuera de lugar."""
    registros = [
        _registro_procedencia("producto", "app.main:app", "/v6r/bin/python"),
        _registro_procedencia("producto", "central_authority.main:app", "/v6c/bin/python"),
        _registro_procedencia("ayudante", "alcance_de_usuario.py", "/v6c/bin/python"),
    ]
    resumen = cr.clasificar_procedencia(registros, "/v6r/bin/python", "/v6c/bin/python")
    assert any("central_authority.main:app" in f for f in resumen["fuera_de_lugar"])


def test_cre29_clasificar_procedencia_ayudante_con_argv0_v6r():
    """M13: ayudante con argv0 de V6R queda fuera de lugar."""
    registros = [
        _registro_procedencia("producto", "app.main:app", "/v6r/bin/python"),
        _registro_procedencia("producto", "central_authority.main:app", "/v6r/bin/python"),
        _registro_procedencia("ayudante", "alcance_de_usuario.py", "/v6r/bin/python"),
    ]
    resumen = cr.clasificar_procedencia(registros, "/v6r/bin/python", "/v6c/bin/python")
    assert any("alcance_de_usuario.py" in f for f in resumen["fuera_de_lugar"])


def test_cre29_clasificar_procedencia_python_mapeado_distinto():
    """M00: python_mapeado distinto de 3.13 queda fuera de lugar."""
    registros = [
        _registro_procedencia("producto", "app.main:app", "/v6r/bin/python", ["3.11"]),
        _registro_procedencia("producto", "central_authority.main:app", "/v6r/bin/python"),
        _registro_procedencia("ayudante", "alcance_de_usuario.py", "/v6c/bin/python"),
    ]
    resumen = cr.clasificar_procedencia(registros, "/v6r/bin/python", "/v6c/bin/python")
    assert any("app.main:app" in f and "3.11" in f for f in resumen["fuera_de_lugar"])


class _MuestreadorFalso:
    def __init__(self, registros):
        self.registros = registros

    def start(self):
        return None

    def detener(self):
        return None


def test_cre30_etapa_e2e_completa_con_exito(tmp_path, monkeypatch):
    """M08, M10: la E2E valida procedencia, paridad y lanza la orden exacta."""
    ctx = _contexto_e2e(tmp_path)
    registros = [
        _registro_procedencia("producto", "app.main:app", "/v6r/bin/python"),
        _registro_procedencia("producto", "central_authority.main:app", "/v6r/bin/python"),
        _registro_procedencia("ayudante", "alcance_de_usuario.py", "/v6c/bin/python"),
    ]
    run_id = "run-cre30"
    manifiesto = _manifiesto_e2e_valido(run_id)
    llamadas: list[list[str]] = []

    def _sujeto_falso(ctx, etapa, argv, *, cwd, entorno, timeout_s, nombre):
        (cr.CORRIDAS_E2E / run_id).mkdir(parents=True)
        (cr.CORRIDAS_E2E / run_id / "manifest.json").write_text(json.dumps(manifiesto), encoding="utf-8")
        (cr.CORRIDAS_E2E / run_id / "suite.log").write_text("Running 3 tests using 6 workers\n", encoding="utf-8")
        llamadas.append(list(argv))
        return cr.ResultadoSujeto(0, f"[e2e {run_id}] 3 pruebas superadas")

    def _leer_salud_falso():
        return {"pswpout": 0, "swap_usada_kb": 0}

    monkeypatch.setattr(cr, "CORRIDAS_E2E", tmp_path / "e2e-runs")
    monkeypatch.setattr(cr, "ejecutar_sujeto", _sujeto_falso)
    monkeypatch.setattr(cr, "MuestreadorDeProcedencia", lambda: _MuestreadorFalso(registros))
    monkeypatch.setattr(cr, "leer_salud", _leer_salud_falso)
    monkeypatch.setattr(cr, "desvio_de_suspension", lambda: 0.0)

    resultado = cr.etapa_e2e(ctx)
    assert ctx.manifiesto["ALEMBIC_PARITY"] == 1
    assert ctx.manifiesto["E2E_AUTHORITY_PARITY"] == 1
    assert ctx.manifiesto["E2E_HELPER_PARITY"] == 1
    assert ctx.manifiesto["E2E_RESULT"]["run_id"] == run_id
    assert isinstance(resultado, dict)
    assert len(llamadas) == 1
    assert llamadas[0] == [
        "/v6c/bin/python",
        str(cr.E2E_RUN),
        "--con-analizador",
        "--python-de-producto",
        "/v6r/bin/python",
        "--",
        "--workers=6",
        "--retries=0",
    ]
    assert ctx.manifiesto["CANONICAL_E2E_WORKERS"] == 6
    assert ctx.manifiesto["CANONICAL_E2E_RETRIES"] == 0


def test_cre30_etapa_e2e_falla_sin_ayudantes(tmp_path, monkeypatch):
    """M13: sin registros de ayudantes falla y E2E_HELPER_PARITY queda a 0."""
    ctx = _contexto_e2e(tmp_path)
    registros = [
        _registro_procedencia("producto", "app.main:app", "/v6r/bin/python"),
        _registro_procedencia("producto", "central_authority.main:app", "/v6r/bin/python"),
    ]
    run_id = "run-cre30-sin-ayudante"
    manifiesto = _manifiesto_e2e_valido(run_id)

    def _sujeto_falso(ctx, etapa, argv, *, cwd, entorno, timeout_s, nombre):
        (cr.CORRIDAS_E2E / run_id).mkdir(parents=True)
        (cr.CORRIDAS_E2E / run_id / "manifest.json").write_text(json.dumps(manifiesto), encoding="utf-8")
        (cr.CORRIDAS_E2E / run_id / "suite.log").write_text("Running 3 tests using 6 workers\n", encoding="utf-8")
        return cr.ResultadoSujeto(0, f"[e2e {run_id}] 3 pruebas superadas")

    monkeypatch.setattr(cr, "CORRIDAS_E2E", tmp_path / "e2e-runs")
    monkeypatch.setattr(cr, "ejecutar_sujeto", _sujeto_falso)
    monkeypatch.setattr(cr, "MuestreadorDeProcedencia", lambda: _MuestreadorFalso(registros))
    monkeypatch.setattr(cr, "leer_salud", lambda: {"pswpout": 0, "swap_usada_kb": 0})
    monkeypatch.setattr(cr, "desvio_de_suspension", lambda: 0.0)

    with pytest.raises(cr.FalloDeCertificacion):
        cr.etapa_e2e(ctx)
    assert ctx.manifiesto["E2E_HELPER_PARITY"] == 0


def test_cre30_etapa_e2e_entorno_invalido_antes_de_manifiesto(tmp_path, monkeypatch):
    """M06: degradación de swap produce EntornoInvalido y ENVIRONMENT_VALIDITY INVALID."""
    ctx = _contexto_e2e(tmp_path)
    registros = [
        _registro_procedencia("producto", "app.main:app", "/v6r/bin/python"),
        _registro_procedencia("producto", "central_authority.main:app", "/v6r/bin/python"),
        _registro_procedencia("ayudante", "alcance_de_usuario.py", "/v6c/bin/python"),
    ]
    run_id = "run-cre30-degradado"
    manifiesto = _manifiesto_e2e_valido(run_id, suite={"codigo": 1, "resumen": {"failed": 1}, "segundos": 1.0})

    def _sujeto_falso(ctx, etapa, argv, *, cwd, entorno, timeout_s, nombre):
        (cr.CORRIDAS_E2E / run_id).mkdir(parents=True)
        (cr.CORRIDAS_E2E / run_id / "manifest.json").write_text(json.dumps(manifiesto), encoding="utf-8")
        return cr.ResultadoSujeto(1, f"[e2e {run_id}] fallo")

    contador = iter([{"pswpout": 0, "swap_usada_kb": 0}, {"pswpout": 400_000, "swap_usada_kb": 0}])
    monkeypatch.setattr(cr, "CORRIDAS_E2E", tmp_path / "e2e-runs")
    monkeypatch.setattr(cr, "ejecutar_sujeto", _sujeto_falso)
    monkeypatch.setattr(cr, "MuestreadorDeProcedencia", lambda: _MuestreadorFalso(registros))
    monkeypatch.setattr(cr, "leer_salud", lambda: next(contador))
    monkeypatch.setattr(cr, "desvio_de_suspension", lambda: 0.0)

    with pytest.raises(cr.EntornoInvalido):
        cr.etapa_e2e(ctx)
    assert ctx.manifiesto["ENVIRONMENT_VALIDITY"] == "INVALID"


def test_cre31_etapa_residuos_puertos_ocupados(tmp_path, monkeypatch):
    """M15: puertos ocupados producen FalloDeCertificacion y RESIDUE_STATUS DIRTY."""
    ctx = _contexto(tmp_path / "residuos-puertos", conservar_espacio=False)
    monkeypatch.setattr(cr, "terminar_vivos", lambda ctx: [])
    monkeypatch.setattr(cr, "puerto_ocupado", lambda puerto: True)
    monkeypatch.setattr(cr, "marcar_espacio", lambda espacio, estado: None)
    monkeypatch.setattr(cr, "eliminar_espacio", lambda espacio, home, run_id: {"eliminado": True})

    with pytest.raises(cr.FalloDeCertificacion):
        cr.etapa_residuos(ctx)
    assert ctx.manifiesto["RESIDUE_STATUS"] == "DIRTY"


def test_cre31_etapa_residuos_bases_de_corrida(tmp_path, monkeypatch):
    """M15: bases de corrida detectadas por psql producen DIRTY."""
    ctx = _contexto(tmp_path / "residuos-psql", conservar_espacio=False)
    ctx.datos["herramientas"] = {"psql": "/x/psql"}
    monkeypatch.setattr(cr, "terminar_vivos", lambda ctx: [])
    monkeypatch.setattr(cr, "puerto_ocupado", lambda puerto: False)
    monkeypatch.setattr(cr, "_psql", lambda ctx, base, consulta, nombre: "1")
    monkeypatch.setattr(cr, "marcar_espacio", lambda espacio, estado: None)
    monkeypatch.setattr(cr, "eliminar_espacio", lambda espacio, home, run_id: {"eliminado": True})

    with pytest.raises(cr.FalloDeCertificacion):
        cr.etapa_residuos(ctx)
    assert ctx.manifiesto["RESIDUE_STATUS"] == "DIRTY"


def test_cre31_etapa_residuos_limpia_elimina_espacio(tmp_path, monkeypatch):
    """M00: sin residuos el estado es CLEAN y el espacio ya no existe."""
    ctx = _contexto(tmp_path / "residuos-limpio", conservar_espacio=False)
    espacio_original = ctx.espacio
    monkeypatch.setattr(cr, "terminar_vivos", lambda ctx: [])
    monkeypatch.setattr(cr, "puerto_ocupado", lambda puerto: False)

    resultado = cr.etapa_residuos(ctx)
    assert ctx.manifiesto["RESIDUE_STATUS"] == "CLEAN"
    assert resultado["espacio"]["eliminado"] is True
    assert not espacio_original.exists()


def test_cre31_etapa_residuos_conservar_espacio(tmp_path, monkeypatch):
    """M00: conservar_espacio deja CONSERVED_BY_OPTION y el espacio existe."""
    ctx = _contexto(tmp_path / "residuos-conservar", conservar_espacio=True)
    espacio_original = ctx.espacio
    monkeypatch.setattr(cr, "terminar_vivos", lambda ctx: [])
    monkeypatch.setattr(cr, "puerto_ocupado", lambda puerto: False)
    monkeypatch.setattr(cr, "marcar_espacio", lambda espacio, estado: None)

    resultado = cr.etapa_residuos(ctx)
    assert ctx.manifiesto["RESIDUE_STATUS"] == "CONSERVED_BY_OPTION"
    assert resultado["espacio"]["motivo"] == "--conservar-espacio"
    assert espacio_original.exists()
def test_cre_22_resultado_de_suite_y_run_id_valido(tmp_path, monkeypatch):
    """CE-22 válido, fallos, salto y última coincidencia."""
    manifiesto = {
        "run_id": "RUN1",
        "pytest": {"rc": 0, "completo": True, "failed": 0, "errors": 0, "passed": 2, "skipped": 1},
        "duracion": {"salto": False, "monotonica_s": 3.5},
        "analizador": {"habilitado": True},
    }
    resultado = cr.resultado_de_suite(manifiesto, 0)
    assert resultado["modo"] == "IN_PROCESS_CERTIFICATION_OVERLAY"

    manifiesto_fallido = {
        "run_id": "RUN1",
        "pytest": {"rc": 1, "completo": True, "failed": 1, "errors": 1, "passed": 1, "skipped": 0},
        "duracion": {"salto": False, "monotonica_s": 3.5},
        "analizador": {"habilitado": False},
    }
    with pytest.raises(cr.FalloDeCertificacion):
        cr.resultado_de_suite(manifiesto_fallido, 1)

    manifiesto_salto = {
        "run_id": "RUN1",
        "pytest": {"rc": 1, "completo": True, "failed": 1, "errors": 1, "passed": 1, "skipped": 0},
        "duracion": {"salto": True, "monotonica_s": 3.5},
        "analizador": {"habilitado": False},
    }
    with pytest.raises(cr.EntornoInvalido):
        cr.resultado_de_suite(manifiesto_salto, 1)

    assert cr.run_id_de_suite("[suite RUN1]\n[suite RUN2]\n") == "RUN2"
    with pytest.raises(cr.FalloDeCertificacion):
        cr.run_id_de_suite("sin run_id")


def test_cre_23_etapa_backend_sqlite_y_postgres(tmp_path, monkeypatch):
    """CE-23 manifiesto, argv motor y aborto si sqlite falla."""
    corridas_backend = tmp_path / "corridas"
    ctx = _contexto(tmp_path, incluir_v0_historico=True)
    ctx.datos["v6c"] = {"python": "/v6c/bin/python"}
    monkeypatch.setattr(cr, "CORRIDAS_BACKEND", corridas_backend)
    llamadas = []

    def doble_ejecutar(ctx, etapa, argv, *, cwd, entorno, timeout_s, nombre):
        llamadas.append((etapa, list(argv), nombre))
        if etapa == "80" and len(llamadas) == 1:
            run_id = "r-sqlite"
            (corridas_backend / run_id).mkdir(parents=True, exist_ok=True)
            (corridas_backend / run_id / "manifest.json").write_text(
                json.dumps({
                    "run_id": run_id,
                    "pytest": {"rc": 0, "completo": True, "failed": 0, "errors": 0, "passed": 1, "skipped": 0},
                    "duracion": {"salto": False, "monotonica_s": 1.0},
                    "analizador": {"habilitado": True},
                })
            )
            return cr.ResultadoSujeto(rc=0, salida=f"[suite {run_id}] salida")
        if etapa == "80" and len(llamadas) == 2:
            return cr.ResultadoSujeto(rc=1, salida="[suite r-postgres] salida")
        raise AssertionError(f"etapa inesperada {etapa}: {argv}")

    monkeypatch.setattr(cr, "ejecutar_sujeto", doble_ejecutar)
    with pytest.raises(cr.FalloDeCertificacion):
        cr.etapa_backend(ctx)
    assert llamadas[0][1][0] == "/v6c/bin/python"
    assert str(cr.SUITE_TIEMPOS) in llamadas[0][1]
    assert "--con-analizador" in llamadas[0][1]

    ctx = _contexto(tmp_path / "otro")
    ctx.datos["v6c"] = {"python": "/v6c/bin/python"}
    llamadas = []

    def doble_ejecutar_exitoso(ctx, etapa, argv, *, cwd, entorno, timeout_s, nombre):
        llamadas.append((etapa, list(argv), nombre))
        run_id = f"r-{'sqlite' if len(llamadas) == 1 else 'postgres'}"
        (corridas_backend / run_id).mkdir(parents=True, exist_ok=True)
        (corridas_backend / run_id / "manifest.json").write_text(
            json.dumps({
                "run_id": run_id,
                "pytest": {"rc": 0, "completo": True, "failed": 0, "errors": 0, "passed": 1, "skipped": 0},
                "duracion": {"salto": False, "monotonica_s": 1.0},
                "analizador": {"habilitado": True},
            })
        )
        return cr.ResultadoSujeto(rc=0, salida=f"[suite {run_id}] salida")

    monkeypatch.setattr(cr, "ejecutar_sujeto", doble_ejecutar_exitoso)
    resultado = cr.etapa_backend(ctx)
    assert set(resultado) == {"sqlite", "postgres"}
    assert ctx.manifiesto["SQLITE_RESULT"]["run_id"] == "r-sqlite"
    assert ctx.manifiesto["POSTGRES_RESULT"]["run_id"] == "r-postgres"


def test_cre_24_etapa_openapi_deriva_cero_y_huella_paths(tmp_path, monkeypatch):
    """CE-24 OpenAPI válida y deriva solo para V6C."""
    referencia = {
        "version_openapi": "3.1.0",
        "rutas": 1,
        "operaciones": 1,
        "protegidas": 1,
        "publicas": 1,
        "huella_paths": "abc",
    }
    monkeypatch.setattr(cr, "leer_referencia", lambda: {"esquema": 1, "openapi": referencia, "pip_audit": "pip-audit==2.9.0"})
    ctx = _contexto(tmp_path)
    ctx.datos["v6r"] = {"python": "/v6r/bin/python"}
    ctx.datos["v6c"] = {"python": "/v6c/bin/python"}
    firma = {**referencia, "python": "3.13.16"}
    llamadas = []

    def doble_ejecutar(ctx, etapa, argv, *, cwd, entorno, timeout_s, nombre):
        llamadas.append((etapa, list(argv), nombre))
        return cr.ResultadoSujeto(rc=0, salida=f"preámbulo\n{json.dumps(firma)}\n")

    monkeypatch.setattr(cr, "ejecutar_sujeto", doble_ejecutar)
    resultado = cr.etapa_openapi(ctx)
    assert resultado["deriva"] == 0
    assert all(argv[0] in ("/v6r/bin/python", "/v6c/bin/python") for _, argv, _ in llamadas)

    # Segunda ejecución con huella_paths distinta solo para V6C.
    llamadas = []
    firma_v6c = {**firma, "huella_paths": "otra"}

    def doble_ejecutar_deriva(ctx, etapa, argv, *, cwd, entorno, timeout_s, nombre):
        llamadas.append((etapa, list(argv), nombre))
        if argv[0] == "/v6c/bin/python":
            return cr.ResultadoSujeto(rc=0, salida=json.dumps(firma_v6c))
        return cr.ResultadoSujeto(rc=0, salida=json.dumps(firma))

    monkeypatch.setattr(cr, "ejecutar_sujeto", doble_ejecutar_deriva)
    with pytest.raises(cr.FalloDeCertificacion):
        cr.etapa_openapi(ctx)
    assert ctx.manifiesto["OPENAPI_RESULT"]["deriva"] == 1


def test_cre_25_etapa_seguridad_y_hallazgos(tmp_path, monkeypatch):
    """CE-25 pip-audit limpio, hallazgo OSV, skip_reason, rc 2, rc 1 sin hallazgos y sin dependencias."""
    ctx = _contexto(tmp_path)
    ctx.datos["v6c"] = {"python": "/v6c/bin/python"}
    ctx.datos["v6r"] = {"python": "/v6r/bin/python"}
    monkeypatch.setattr(cr, "leer_referencia", lambda: {"openapi": {}, "pip_audit": "pip-audit==2.9.0"})
    monkeypatch.setattr(cr, "LOCK_RUNTIME", tmp_path / "runtime.lock")
    monkeypatch.setattr(cr, "LOCK_CERTIFICACION", tmp_path / "test.lock")
    (tmp_path / "runtime.lock").write_text("")
    (tmp_path / "test.lock").write_text("")
    auditorias_escritas = []

    def doble_ejecutar_limpio(ctx, etapa, argv, *, cwd, entorno, timeout_s, nombre):
        if argv[:4] == ["/v6c/bin/python", "-m", "pip", "install"]:
            return cr.ResultadoSujeto(rc=0, salida="")
        if "-o" in argv:
            informe_path = Path(argv[argv.index("-o") + 1])
            auditorias_escritas.append(str(informe_path))
            informe_path.write_text(json.dumps({"dependencies": [{"name": "fastapi", "version": "1.0", "vulns": []}]}))
            return cr.ResultadoSujeto(rc=0, salida="")
        raise AssertionError(f"argv inesperado: {argv}")

    monkeypatch.setattr(cr, "ejecutar_sujeto", doble_ejecutar_limpio)
    resultado = cr.etapa_seguridad(ctx)
    assert resultado["pypi"] == {"requirements.lock": 0, "requirements-test.lock": 0}
    assert resultado["osv"] == {"requirements.lock": 0, "requirements-test.lock": 0}
    assert len(auditorias_escritas) == 4

    # Una vulnerabilidad en osv/requirements.lock con rc 1.
    auditorias_escritas = []

    def doble_ejecutar_vulnerable(ctx, etapa, argv, *, cwd, entorno, timeout_s, nombre):
        if argv[:4] == ["/v6c/bin/python", "-m", "pip", "install"]:
            return cr.ResultadoSujeto(rc=0, salida="")
        if "-o" in argv:
            informe_path = Path(argv[argv.index("-o") + 1])
            auditorias_escritas.append(str(informe_path))
            if "osv" in argv and str(cr.LOCK_RUNTIME) in argv:
                datos = {"dependencies": [{"name": "demo", "version": "1.0.0", "vulns": [{"id": "OSV-1"}]}]}
                informe_path.write_text(json.dumps(datos))
                return cr.ResultadoSujeto(rc=1, salida="")
            informe_path.write_text(json.dumps({"dependencies": [{"name": "fastapi", "version": "1.0", "vulns": []}]}))
            return cr.ResultadoSujeto(rc=0, salida="")
        raise AssertionError(f"argv inesperado: {argv}")

    monkeypatch.setattr(cr, "ejecutar_sujeto", doble_ejecutar_vulnerable)
    with pytest.raises(cr.FalloDeCertificacion):
        cr.etapa_seguridad(ctx)
    assert ctx.manifiesto["PIP_AUDIT_OSV"] == 1

    # skip_reason.
    def doble_ejecutar_skip(ctx, etapa, argv, *, cwd, entorno, timeout_s, nombre):
        if argv[:4] == ["/v6c/bin/python", "-m", "pip", "install"]:
            return cr.ResultadoSujeto(rc=0, salida="")
        if "-o" in argv:
            informe_path = Path(argv[argv.index("-o") + 1])
            informe_path.write_text(json.dumps({"dependencies": [{"name": "demo", "version": "1.0.0", "skip_reason": "sin datos"}]}))
            return cr.ResultadoSujeto(rc=0, salida="")
        raise AssertionError(f"argv inesperado: {argv}")

    monkeypatch.setattr(cr, "ejecutar_sujeto", doble_ejecutar_skip)
    with pytest.raises(cr.FalloDeCertificacion):
        cr.etapa_seguridad(ctx)

    # rc 2.
    def doble_ejecutar_rc2(ctx, etapa, argv, *, cwd, entorno, timeout_s, nombre):
        if argv[:4] == ["/v6c/bin/python", "-m", "pip", "install"]:
            return cr.ResultadoSujeto(rc=0, salida="")
        if "-o" in argv:
            informe_path = Path(argv[argv.index("-o") + 1])
            informe_path.write_text(json.dumps({"dependencies": [{"name": "fastapi", "version": "1.0", "vulns": []}]}))
            return cr.ResultadoSujeto(rc=2, salida="")
        raise AssertionError(f"argv inesperado: {argv}")

    monkeypatch.setattr(cr, "ejecutar_sujeto", doble_ejecutar_rc2)
    with pytest.raises(cr.FalloDeCertificacion):
        cr.etapa_seguridad(ctx)

    # rc 1 sin hallazgos.
    def doble_ejecutar_rc1_sin_hallazgos(ctx, etapa, argv, *, cwd, entorno, timeout_s, nombre):
        if argv[:4] == ["/v6c/bin/python", "-m", "pip", "install"]:
            return cr.ResultadoSujeto(rc=0, salida="")
        if "-o" in argv:
            informe_path = Path(argv[argv.index("-o") + 1])
            informe_path.write_text(json.dumps({"dependencies": [{"name": "fastapi", "version": "1.0", "vulns": []}]}))
            return cr.ResultadoSujeto(rc=1, salida="")
        raise AssertionError(f"argv inesperado: {argv}")

    monkeypatch.setattr(cr, "ejecutar_sujeto", doble_ejecutar_rc1_sin_hallazgos)
    with pytest.raises(cr.FalloDeCertificacion):
        cr.etapa_seguridad(ctx)

    # hallazgos_de_auditoria sin dependencias.
    with pytest.raises(cr.FalloDeCertificacion):
        cr.hallazgos_de_auditoria({"dependencies": []})


def test_cre_26_etapa_postgres_ktest_y_entorno_invalido(tmp_path, monkeypatch):
    """CE-26 status, ktest, btree_gist, bases y esquemas previos."""
    ctx = _contexto(tmp_path)
    bin_fijado = tmp_path / "pg-fijado" / "bin"
    bin_fijado.mkdir(parents=True)
    monkeypatch.setattr(
        cr,
        "aprovisionar_postgres_qa",
        lambda ctx: ctx.datos.update({"postgres_qa": {"bin": str(bin_fijado), "postgres": "16.2"}}) or ctx.datos["postgres_qa"],
    )
    monkeypatch.setattr(cr, "ejecutable_del_postmaster", lambda pgdata: (bin_fijado / "postgres").resolve())
    provisiones = []
    psql_llamadas = []
    ktest_creada = False

    def doble_pg_provision(ctx, *argumentos, nombre):
        nonlocal ktest_creada
        provisiones.append((argumentos, nombre))
        if "mkdb" in argumentos:
            ktest_creada = True
        return 0

    monkeypatch.setattr(cr, "_pg_provision", doble_pg_provision)

    def doble_psql(ctx, base, sql, nombre):
        psql_llamadas.append((base, sql, nombre))
        if "server_version" in sql:
            return "16.2"
        if "SHOW port" in sql:
            return str(cr.PUERTO_PG_QA)
        if "pg_database" in sql and "ktest" in sql and "LIKE" not in sql:
            return "1" if ktest_creada else "0"
        if "btree_gist" in sql:
            return "1"
        if "kontrol\\_e2e" in sql:
            return "0"
        if "nspname" in sql:
            return "0"
        return ""

    monkeypatch.setattr(cr, "_psql", doble_psql)
    resultado = cr.etapa_postgres(ctx)
    assert resultado["ktest_creada"] is True
    assert ctx.manifiesto["POSTGRES_VERSION"] == "16.2"
    assert any("mkdb" in argumentos for argumentos, _ in provisiones)
    assert sum(1 for argumentos, _ in provisiones if "mkdb" in argumentos) == 1

    # status rc 0 evita start (ktest ya existe).
    provisiones = []
    ktest_creada = True

    def doble_pg_provision_sin_arranque(ctx, *argumentos, nombre):
        provisiones.append((argumentos, nombre))
        return 99 if "start" in argumentos else 0

    monkeypatch.setattr(cr, "_pg_provision", doble_pg_provision_sin_arranque)
    resultado = cr.etapa_postgres(ctx)
    assert not any("start" in argumentos for argumentos, _ in provisiones)

    # status rc 3 ejecuta start.
    provisiones = []
    ktest_creada = False

    def doble_pg_provision_con_arranque(ctx, *argumentos, nombre):
        nonlocal ktest_creada
        provisiones.append((argumentos, nombre))
        if "mkdb" in argumentos:
            ktest_creada = True
        return 3 if "status" in argumentos else 0

    monkeypatch.setattr(cr, "_pg_provision", doble_pg_provision_con_arranque)
    cr.etapa_postgres(ctx)
    assert any("start" in argumentos for argumentos, _ in provisiones)

    # ktest existente no crea.
    provisiones = []
    psql_llamadas = []
    ktest_creada = False

    def doble_psql_ktest_existente(ctx, base, sql, nombre):
        if "pg_database" in sql and "ktest" in sql and "LIKE" not in sql:
            return "1"
        if "btree_gist" in sql:
            return "1"
        if "server_version" in sql:
            return "16.2"
        if "SHOW port" in sql:
            return str(cr.PUERTO_PG_QA)
        return "0"

    monkeypatch.setattr(cr, "_psql", doble_psql_ktest_existente)
    cr.etapa_postgres(ctx)
    assert not any("mkdb" in argumentos for argumentos, _ in provisiones)

    # Bases previas.
    def doble_psql_bases_previas(ctx, base, sql, nombre):
        if "kontrol\\_e2e" in sql:
            return "1"
        if "server_version" in sql:
            return "16.2"
        if "SHOW port" in sql:
            return str(cr.PUERTO_PG_QA)
        if "pg_database" in sql and "ktest" in sql and "LIKE" not in sql:
            return "1"
        if "nspname" in sql:
            return "0"
        return "1"

    monkeypatch.setattr(cr, "_psql", doble_psql_bases_previas)
    with pytest.raises(cr.EntornoInvalido):
        cr.etapa_postgres(ctx)

    # Esquemas previos.
    def doble_psql_esquemas_previos(ctx, base, sql, nombre):
        if "nspname" in sql:
            return "2"
        if "server_version" in sql:
            return "16.2"
        if "SHOW port" in sql:
            return str(cr.PUERTO_PG_QA)
        if "pg_database" in sql and "ktest" in sql and "LIKE" not in sql:
            return "1"
        if "btree_gist" in sql:
            return "1"
        if "kontrol\\_e2e" in sql:
            return "0"
        return "1"

    monkeypatch.setattr(cr, "_psql", doble_psql_esquemas_previos)
    with pytest.raises(cr.EntornoInvalido):
        cr.etapa_postgres(ctx)

    # Puerto incorrecto.
    def doble_psql_puerto_incorrecto(ctx, base, sql, nombre):
        if "SHOW port" in sql:
            return "5432"
        if "server_version" in sql:
            return "16.2"
        if "pg_database" in sql and "ktest" in sql and "LIKE" not in sql:
            return "1"
        return "1"

    monkeypatch.setattr(cr, "_psql", doble_psql_puerto_incorrecto)
    with pytest.raises(cr.EntornoInvalido):
        cr.etapa_postgres(ctx)


def test_cre_27_etapa_validez_salud_invalida_y_valida(tmp_path, monkeypatch):
    """CE-27 esperar_salud inválido y válido con suspensión."""
    ctx = _contexto(tmp_path)
    monkeypatch.setattr(cr, "leer_salud", lambda: {"estado": "x"})
    monkeypatch.setattr(cr, "desvio_de_suspension", lambda: 42)
    monkeypatch.setattr(cr, "esperar_salud", lambda _: {"valido": False, "detalle": "descanso"})
    with pytest.raises(cr.EntornoInvalido):
        cr.etapa_validez(ctx)
    assert ctx.manifiesto["ENVIRONMENT_VALIDITY"] == "INVALID"

    ctx = _contexto(tmp_path / "otro")
    monkeypatch.setattr(cr, "esperar_salud", lambda _: {"valido": True, "detalle": "ok"})
    resultado = cr.etapa_validez(ctx)
    assert resultado == {"valido": True, "detalle": "ok"}
    assert ctx.manifiesto["ENVIRONMENT_VALIDITY"] == "VALID"
    assert ctx.datos["suspension_base_s"] == 42
