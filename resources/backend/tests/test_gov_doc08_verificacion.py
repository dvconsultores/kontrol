"""DOC-08 · Pruebas backend de la VERIFICACIÓN de integridad (DV-01..DV-12)."""

import io
import json
import zipfile

from sqlalchemy import select

from app.modules.audit.models import AuditEvent
from tests.test_gov_ctl06_hallazgos import _crear_usuario_con_permisos
from tests.test_gov_doc08_paquete import P, _generar

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.test_gov_doc08_paquete",
)


def _paquete(mundo, escenario) -> tuple[dict, bytes]:
    r = _generar(mundo, escenario["muestra_id"])
    assert r.status_code == 201, r.text
    paquete = r.json()
    datos = mundo.client.get(
        f"/api/v1{P}/{paquete['id']}/descargar",
        headers=mundo.como("ua", mundo.company_a),
    ).content
    assert datos
    return paquete, datos


def _verificar(mundo, datos: bytes, usuario: str = "ua", empresa: str | None = None):
    return mundo.client.post(
        f"/api/v1{P}/verificar",
        headers=mundo.como(usuario, empresa or mundo.company_a),
        files={"archivo": ("paquete.zip", datos, "application/zip")},
    )


def _rehacer(
    datos: bytes,
    cambios: dict[str, bytes | None] | None = None,
    extra: dict[str, bytes] | None = None,
) -> bytes:
    origen = zipfile.ZipFile(io.BytesIO(datos))
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w") as zf:
        for info in origen.infolist():
            if cambios and info.filename in cambios:
                reemplazo = cambios[info.filename]
                if reemplazo is None:
                    continue
                zf.writestr(info, reemplazo)
            else:
                zf.writestr(info, origen.read(info.filename))
        for ruta, contenido in (extra or {}).items():
            zf.writestr(ruta, contenido)
    return salida.getvalue()


def _manifiesto(datos: bytes) -> dict:
    return json.loads(zipfile.ZipFile(io.BytesIO(datos)).read("manifest.json"))


def _ruta_de(datos: bytes, documento_id: str) -> str:
    documentos = _manifiesto(datos)["documentos"]
    return next(
        doc["archivo"] for doc in documentos if doc["id"] == documento_id
    )


def _ultimo_evento(mundo, action: str) -> AuditEvent:
    with mundo.factory() as db:
        return db.scalar(
            select(AuditEvent)
            .where(AuditEvent.action == action)
            .order_by(AuditEvent.event_time.desc())
            .limit(1)
        )


class TestGovDoc08Verificacion:
    def test_dv01_copia_identica_es_valida(self, mundo, gobierno, escenario):
        paquete, datos = _paquete(mundo, escenario)
        r = _verificar(mundo, datos)
        assert r.status_code == 200, r.text
        cuerpo = r.json()
        assert cuerpo["resultado"] == "VALIDO"
        assert cuerpo["motivos"] == []
        assert cuerpo["identico"] is True
        assert cuerpo["paquete"]["codigo"] == paquete["codigo"]
        assert cuerpo["verificacion_id"] is not None

        detalle = mundo.client.get(
            f"/api/v1{P}/{paquete['id']}", headers=mundo.como("ua", mundo.company_a)
        )
        assert detalle.status_code == 200
        verificaciones = detalle.json()["verificaciones"]
        assert verificaciones[0]["resultado"] == "VALIDO"
        assert verificaciones[0]["identico"] is True

        evento = _ultimo_evento(mundo, "GOV_AUDIT_PACKAGE_VERIFIED")
        assert evento is not None
        assert str(evento.entity_id) == paquete["id"]
        assert evento.after["resultado"] == "VALIDO"

    def test_dv02_recomprimido_identico_contenido_valido(self, mundo, gobierno, escenario):
        paquete, datos = _paquete(mundo, escenario)
        copia = _rehacer(datos)
        if copia == datos:
            salida = io.BytesIO()
            with zipfile.ZipFile(salida, "w") as zf:
                zf.comment = b"copia"
                for info in zipfile.ZipFile(io.BytesIO(datos)).infolist():
                    zf.writestr(info, zipfile.ZipFile(io.BytesIO(datos)).read(info.filename))
            copia = salida.getvalue()
        r = _verificar(mundo, copia)
        assert r.status_code == 200, r.text
        cuerpo = r.json()
        assert cuerpo["resultado"] == "VALIDO"
        assert cuerpo["identico"] is False

    def test_dv03_documento_sustituido_invalido(self, mundo, gobierno, escenario):
        _, datos = _paquete(mundo, escenario)
        ruta = _ruta_de(datos, escenario["d1"])
        alterado = _rehacer(datos, {ruta: b"alterado"})
        r = _verificar(mundo, alterado)
        assert r.status_code == 200, r.text
        cuerpo = r.json()
        assert cuerpo["resultado"] == "INVALIDO"
        assert {"codigo": "ARCHIVO_ALTERADO", "ruta": ruta} in cuerpo["motivos"]

    def test_dv04_byte_alterado_en_bruto_invalido(self, mundo, gobierno, escenario):
        _, datos = _paquete(mundo, escenario)
        pos = datos.find(escenario["d1_datos"])
        assert pos > 0
        alterado = datos[:pos] + bytes([datos[pos] ^ 0x01]) + datos[pos + 1 :]
        r = _verificar(mundo, alterado)
        assert r.status_code == 200, r.text
        cuerpo = r.json()
        assert cuerpo["resultado"] == "INVALIDO"
        ruta = _ruta_de(datos, escenario["d1"])
        assert {"codigo": "ARCHIVO_ALTERADO", "ruta": ruta} in cuerpo["motivos"]

    def test_dv05_fichero_ausente_incompleto(self, mundo, gobierno, escenario):
        _, datos = _paquete(mundo, escenario)
        alterado = _rehacer(datos, {"LEEME.txt": None})
        r = _verificar(mundo, alterado)
        assert r.status_code == 200, r.text
        cuerpo = r.json()
        assert cuerpo["resultado"] == "INCOMPLETO"
        assert cuerpo["motivos"] == [
            {"codigo": "ARCHIVO_AUSENTE", "ruta": "LEEME.txt"}
        ]

    def test_dv06_fichero_inesperado_invalido(self, mundo, gobierno, escenario):
        _, datos = _paquete(mundo, escenario)
        alterado = _rehacer(datos, extra={"extra/nota.txt": b"x"})
        r = _verificar(mundo, alterado)
        assert r.status_code == 200, r.text
        cuerpo = r.json()
        assert cuerpo["resultado"] == "INVALIDO"
        assert {
            "codigo": "ARCHIVO_INESPERADO",
            "ruta": "extra/nota.txt",
        } in cuerpo["motivos"]

    def test_dv07_manifiesto_alterado_invalido(self, mundo, gobierno, escenario):
        _, datos = _paquete(mundo, escenario)
        m = _manifiesto(datos)
        m["paquete"]["proposito"] = "Propósito manipulado tras la descarga"
        alterado = _rehacer(datos, {"manifest.json": json.dumps(m).encode()})
        r = _verificar(mundo, alterado)
        assert r.status_code == 200, r.text
        cuerpo = r.json()
        assert cuerpo["resultado"] == "INVALIDO"
        assert {
            "codigo": "MANIFIESTO_ALTERADO",
            "ruta": "manifest.json",
        } in cuerpo["motivos"]

    def test_dv08_version_no_soportada(self, mundo, gobierno, escenario):
        _, datos = _paquete(mundo, escenario)
        m = _manifiesto(datos)
        m["version_manifiesto"] = 2
        alterado = _rehacer(datos, {"manifest.json": json.dumps(m).encode()})
        r = _verificar(mundo, alterado)
        assert r.status_code == 200, r.text
        assert r.json()["resultado"] == "VERSION_NO_SOPORTADA"

    def test_dv09_codigo_no_registrado_invalido(self, mundo, gobierno, escenario):
        _, datos = _paquete(mundo, escenario)
        m = _manifiesto(datos)
        m["paquete"]["codigo"] = "PA-1999-9999"
        alterado = _rehacer(datos, {"manifest.json": json.dumps(m).encode()})
        r = _verificar(mundo, alterado)
        assert r.status_code == 200, r.text
        cuerpo = r.json()
        assert cuerpo["resultado"] == "INVALIDO"
        assert cuerpo["motivos"] == [
            {"codigo": "PAQUETE_NO_REGISTRADO", "ruta": None}
        ]
        assert cuerpo["paquete"] is None
        assert cuerpo["verificacion_id"] is None

        evento = _ultimo_evento(mundo, "GOV_AUDIT_PACKAGE_VERIFICATION_FAILED")
        assert evento is not None
        assert evento.after["resultado"] == "INVALIDO"
        assert evento.after["codigo"] is None

    def test_dv10_sin_manifiesto_invalido(self, mundo, gobierno, escenario):
        _, datos = _paquete(mundo, escenario)
        alterado = _rehacer(datos, {"manifest.json": None})
        r = _verificar(mundo, alterado)
        assert r.status_code == 200, r.text
        cuerpo = r.json()
        assert cuerpo["resultado"] == "INVALIDO"
        assert {"codigo": "MANIFIESTO_AUSENTE", "ruta": None} in cuerpo["motivos"]

    def test_dv11_otra_empresa_no_revela_registro(self, mundo, gobierno, escenario):
        _, datos = _paquete(mundo, escenario)
        r = _verificar(mundo, datos, usuario="ub", empresa=mundo.company_b)
        assert r.status_code == 200, r.text
        cuerpo = r.json()
        assert cuerpo["resultado"] == "INVALIDO"
        assert {
            "codigo": "PAQUETE_NO_REGISTRADO",
            "ruta": None,
        } in cuerpo["motivos"]
        assert cuerpo["paquete"] is None

    def test_dv12_archivo_inseguro_o_sin_permiso(self, mundo, gobierno, escenario):
        r = _verificar(mundo, b"esto no es un zip")
        assert r.status_code == 422, r.text
        assert r.json()["code"] == "GOV_PACKAGE_UPLOAD_INVALID"

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("../fuera.txt", b"x")
        r = _verificar(mundo, buf.getvalue())
        assert r.status_code == 422, r.text
        assert r.json()["code"] == "GOV_PACKAGE_UPLOAD_INVALID"

        _crear_usuario_con_permisos(
            mundo, "paq_sin", [("documentos", "view")], mundo.company_a
        )
        _, datos = _paquete(mundo, escenario)
        r = _verificar(mundo, datos, usuario="paq_sin")
        assert r.status_code == 403, r.text
