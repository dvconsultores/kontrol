# ruff: noqa: E402, F811, F401, I001
"""ORG-07-EFFECTIVE-AUTHORITY-MATRIX: la matriz proyecta la autoridad efectiva de ORG-04 a la fecha de corte."""

import csv
import io
import uuid

import pytest

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.org04_ayudantes",
)

from tests.org04_ayudantes import (
    ANIO, D, accion, activa, acto_eficaz, crear_funcionario, cuerpo, nuevo_cargo,
)
from tests.test_gov_org04_politica_procesos import _cerrar_vigentes, _comision, _delegacion, _suplencia
from tests.test_gov_org07_autoridad import _crear_usuario_con_permiso

M = f"/api/v1/gobierno/autoridad/{ANIO}"
FIGURAS = ("TITULAR", "ENCARGADURIA", "SUPLENCIA", "COMISION_SERVICIO", "DELEGACION_ATRIBUCIONES", "DELEGACION_FIRMA")


@pytest.fixture(autouse=True)
def _sin_politicas(mundo, gobierno, ocupacion):
    """Las pruebas usan los pisos legales: se cierran las políticas vigentes de cada figura."""
    for figura in FIGURAS:
        _cerrar_vigentes(mundo, figura)


def _matriz(mundo, fecha, usuario="ua", empresa=None, **params):
    resp = mundo.client.get(
        M,
        headers=mundo.como(usuario, empresa or mundo.company_a),
        params={"fecha": fecha.isoformat(), "por_pagina": 200, **params},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _filas(mundo, fecha, cargo_id, usuario="ua", **params):
    return _matriz(mundo, fecha, usuario=usuario, cargo_id=cargo_id, **params)["items"]


def _csv(mundo, fecha, usuario="ua", **params):
    resp = mundo.client.get(
        f"{M}/exportar",
        headers=mundo.como(usuario, mundo.company_a),
        params={"fecha": fecha.isoformat(), **params},
    )
    assert resp.status_code == 200, resp.text
    filas = list(csv.reader(io.StringIO(resp.content.decode("utf-8"))))
    cabecera = filas[0]
    return [dict(zip(cabecera, f, strict=True)) for f in filas[1:]]


def _titular_desde(mundo, ocupacion, cargo_id, desde):
    """Titular del cargo desde una fecha concreta (el ayudante de ORG-04 empieza siempre el 1 de febrero)."""
    funcionario = crear_funcionario(mundo)
    acto_id = acto_eficaz(mundo, ocupacion["cargo_emisor"], fecha=D(1, 2))
    return activa(mundo, cuerpo(funcionario, cargo_id, acto_id, figura="TITULAR", desde=desde.isoformat()))


@pytest.fixture
def delegacion(mundo, gobierno, ocupacion):
    """Delegación de APROBAR/PRESUPUESTO desde el 1 de febrero, sin fin."""
    body = _delegacion(mundo, ocupacion)
    asignacion = activa(mundo, body)
    return {
        "asignacion": asignacion,
        "delegante": body["cargo_id"],
        "delegado_cargo": body["cargo_origen_id"],
        "funcionario": asignacion["funcionario"],
    }


def _delegadas(filas):
    return [f for f in filas if f["origen"] == "DELEGACION_ATRIBUCIONES"]


# ---------------------------------------------------------------- defecto (§28) y delegación (§8)
def test_org07_ea01_defecto_delegacion_visible(mundo, delegacion):
    """Antes (65651eff) la matriz solo daba filas CARGO: el delegado no aparecía."""
    filas = _filas(mundo, D(2, 15), delegacion["delegante"])
    delegadas = _delegadas(filas)
    assert len(delegadas) == 1, filas
    fila = delegadas[0]
    fuente = fila["fuente"]
    assert fuente["persona"]["nombre"] == delegacion["funcionario"]["nombre"]
    assert fuente["persona_reservada"] is False
    assert fuente["asignacion_id"] == delegacion["asignacion"]["id"]
    assert fuente["asignacion_codigo"] == delegacion["asignacion"]["codigo"]
    assert fuente["figura_etiqueta"] == "Delegación de atribuciones"
    assert fuente["desde"] == D(2, 1).isoformat()
    assert fuente["acto"]["id"] == delegacion["asignacion"]["acto"]["id"]
    assert fuente["cargo_origen"]["id"] == delegacion["delegado_cargo"]
    # Solo lo delegado: APROBAR, no FIRMAR, con el límite que guardó ORG-04.
    assert (fila["accion"], fila["materia"]) == ("APROBAR", "PRESUPUESTO")
    assert (fila["tipo_limite"], fila["monto"], fila["moneda"]) == ("MONTO", "1000.00", "VES")
    assert fila["id"] == f"{delegacion['asignacion']['id']}:APROBAR:PRESUPUESTO"


def test_org07_ea02_base_y_delegada_conviven(mundo, delegacion):
    """La autoridad del cargo no se pierde: el delegante conserva la titularidad (§7, §20)."""
    filas = _filas(mundo, D(2, 15), delegacion["delegante"])
    base = [f for f in filas if f["origen"] == "CARGO"]
    assert {(f["accion"], f["materia"]) for f in base} == {("FIRMAR", "PRESUPUESTO"), ("APROBAR", "PRESUPUESTO")}
    assert all(f["fuente"] is None for f in base)  # el cargo delegante está vacante
    ids = [f["id"] for f in filas]
    assert len(ids) == len(set(ids)) == 3
    # La fila del cargo va antes que la delegación de la misma competencia.
    aprobar = [f["origen"] for f in filas if f["accion"] == "APROBAR"]
    assert aprobar == ["CARGO", "DELEGACION_ATRIBUCIONES"]


def test_org07_ea03_delegacion_fuera_de_vigencia(mundo, delegacion):
    assert _delegadas(_filas(mundo, D(1, 15), delegacion["delegante"])) == []


def test_org07_ea04_delegacion_revocada_solo_en_la_historia(mundo, gobierno, ocupacion):
    body = _delegacion(mundo, ocupacion)
    asignacion = activa(mundo, body)
    acto_revocacion = acto_eficaz(mundo, body["cargo_id"], fecha=D(3, 1), medio="GACETA")
    resp = accion(
        mundo,
        asignacion,
        "revocar",
        {"acto_id": acto_revocacion, "fecha": D(3, 1).isoformat(), "motivo": "Revocación de la delegación de prueba"},
    )
    assert resp.status_code == 200, resp.text
    assert len(_delegadas(_filas(mundo, D(2, 15), body["cargo_id"]))) == 1
    assert _delegadas(_filas(mundo, D(3, 15), body["cargo_id"])) == []


def test_org07_ea05_delegacion_de_firma(mundo, gobierno, ocupacion):
    body = _delegacion(
        mundo,
        ocupacion,
        figura="DELEGACION_FIRMA",
        competencias=[{"accion": "FIRMAR", "materia": "PRESUPUESTO"}],
    )
    activa(mundo, body)
    filas = [f for f in _filas(mundo, D(2, 15), body["cargo_id"]) if f["origen"] == "DELEGACION_FIRMA"]
    assert [(f["accion"], f["tipo_limite"]) for f in filas] == [("FIRMAR", "SIN_LIMITE")]


# ---------------------------------------------------------------- suplencia (§9) e historia (§20)
@pytest.fixture
def suplencia(mundo, gobierno, ocupacion):
    """Titular desde el 10 de enero; suplencia del 1 al 20 de febrero."""
    cargo_suplido = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    cargo_suplente = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")
    titular = _titular_desde(mundo, ocupacion, cargo_suplido, D(1, 10))
    suplente = _titular_desde(mundo, ocupacion, cargo_suplente, D(1, 10))
    acto = acto_eficaz(mundo, cargo_suplido)
    asignacion = activa(
        mundo,
        cuerpo(
            suplente["funcionario"],
            cargo_suplido,
            acto,
            figura="SUPLENCIA",
            cargo_origen_id=cargo_suplente,
            desde=D(2, 1).isoformat(),
            hasta=D(2, 20).isoformat(),
        ),
    )
    return {"cargo": cargo_suplido, "titular": titular, "suplente": suplente, "asignacion": asignacion}


def test_org07_ea06_suplencia_sustituye_sin_duplicar(mundo, suplencia):
    filas = _filas(mundo, D(2, 10), suplencia["cargo"])
    assert len(filas) == 2, filas  # una fila por competencia: la suplencia sustituye, no se suma
    for fila in filas:
        assert fila["origen"] == "SUPLENCIA"
        assert fila["fuente"]["persona"]["id"] == suplencia["suplente"]["funcionario"]["id"]
        assert fila["fuente"]["sustituye_a"]["id"] == suplencia["titular"]["funcionario"]["id"]
        assert fila["fuente"]["hasta"] == D(2, 20).isoformat()
        assert fila["fuente"]["asignacion_id"] == suplencia["asignacion"]["id"]


def test_org07_ea07_historia_titular_suplente_titular(mundo, suplencia):
    titular = suplencia["titular"]["funcionario"]["id"]
    suplente = suplencia["suplente"]["funcionario"]["id"]
    esperado = {D(1, 20): ("CARGO", titular), D(2, 10): ("SUPLENCIA", suplente), D(3, 10): ("CARGO", titular)}
    for fecha, (origen, persona) in esperado.items():
        filas = _filas(mundo, fecha, suplencia["cargo"])
        assert {(f["origen"], f["fuente"]["persona"]["id"]) for f in filas} == {(origen, persona)}, fecha
        assert all(f["fuente"]["figura"] == ("TITULAR" if origen == "CARGO" else "SUPLENCIA") for f in filas)


def test_org07_ea08_suplencia_finalizada_antes(mundo, gobierno, ocupacion):
    cargo = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    cargo_suplente = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")
    titular = _titular_desde(mundo, ocupacion, cargo, D(1, 10))
    suplente = _titular_desde(mundo, ocupacion, cargo_suplente, D(1, 10))
    asignacion = activa(
        mundo,
        cuerpo(
            suplente["funcionario"],
            cargo,
            acto_eficaz(mundo, cargo),
            figura="SUPLENCIA",
            cargo_origen_id=cargo_suplente,
            desde=D(2, 1).isoformat(),
            hasta=D(2, 20).isoformat(),
        ),
    )
    resp = accion(mundo, asignacion, "finalizar", {"fecha": D(2, 5).isoformat(), "motivo": "Regreso anticipado del titular"})
    assert resp.status_code == 200, resp.text
    filas = _filas(mundo, D(2, 10), cargo)
    assert {(f["origen"], f["fuente"]["persona"]["id"]) for f in filas} == {("CARGO", titular["funcionario"]["id"])}
    filas = _filas(mundo, D(2, 3), cargo)
    assert {f["origen"] for f in filas} == {"SUPLENCIA"}


# ---------------------------------------------------------------- encargaduría (§10) y otra figura (§11)
def test_org07_ea09_encargaduria(mundo, gobierno, ocupacion):
    cargo = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    encargado = crear_funcionario(mundo)
    asignacion = activa(
        mundo,
        cuerpo(encargado, cargo, acto_eficaz(mundo, ocupacion["cargo_emisor"]), figura="ENCARGADURIA"),
    )
    filas = _filas(mundo, D(2, 15), cargo)
    assert len(filas) == 2
    for fila in filas:
        assert fila["origen"] == "ENCARGADURIA"
        assert fila["fuente"]["persona"]["id"] == encargado["id"]
        assert fila["fuente"]["sustituye_a"] is None
        assert fila["fuente"]["acto"]["id"] == asignacion["acto"]["id"]
    # Antes de la encargaduría el cargo está vacante: autoridad del cargo, sin persona.
    assert {(f["origen"], f["fuente"] is None) for f in _filas(mundo, D(1, 15), cargo)} == {("CARGO", True)}


def test_org07_ea10_comision_de_servicio(mundo, gobierno, ocupacion):
    body = _comision(mundo, ocupacion)
    asignacion = activa(mundo, body)
    filas = _filas(mundo, D(2, 10), body["cargo_id"])
    assert {f["origen"] for f in filas} == {"COMISION_SERVICIO"}
    assert all(f["fuente"]["persona"]["id"] == asignacion["funcionario"]["id"] for f in filas)
    assert all(f["fuente"]["cargo_origen"]["id"] == body["cargo_origen_id"] for f in filas)


# ---------------------------------------------------------------- alcance y filtros (§18, §25)
def test_org07_ea11_alcance_en_la_unidad_del_delegante(mundo, ocupacion, delegacion):
    raiz = _matriz(mundo, D(2, 15), unidad_id=ocupacion["unidad_raiz"])["items"]
    assert any(f["fuente"] and f["fuente"]["asignacion_id"] == delegacion["asignacion"]["id"] for f in raiz)
    # Subunidades: el cargo del delegado (unidad hija) cae bajo la raíz.
    assert any(f["cargo_id"] == delegacion["delegado_cargo"] for f in raiz)
    hija = _matriz(mundo, D(2, 15), unidad_id=ocupacion["unidad_hija"])["items"]
    assert not any(f["fuente"] and f["fuente"]["asignacion_id"] == delegacion["asignacion"]["id"] for f in hija)
    otra = _matriz(mundo, D(2, 15), unidad_id=ocupacion["unidad_otra"])["items"]
    assert not any(f["cargo_id"] == delegacion["delegante"] for f in otra)


def test_org07_ea12_filtros_accion_materia_y_texto(mundo, delegacion):
    cargo = delegacion["delegante"]
    assert _delegadas(_filas(mundo, D(2, 15), cargo, accion="FIRMAR")) == []
    assert len(_delegadas(_filas(mundo, D(2, 15), cargo, accion="APROBAR"))) == 1
    assert len(_delegadas(_filas(mundo, D(2, 15), cargo, materia="PRESUPUESTO"))) == 1
    assert _filas(mundo, D(2, 15), cargo, materia="TESORERIA") == []
    nombre = delegacion["funcionario"]["nombre"]
    por_nombre = _matriz(mundo, D(2, 15), texto=nombre)["items"]
    assert [f["id"] for f in _delegadas(por_nombre)] == [f"{delegacion['asignacion']['id']}:APROBAR:PRESUPUESTO"]


# ---------------------------------------------------------------- OD-EA-01: personas reservadas
@pytest.fixture
def auditor(mundo, gobierno):
    nombre = f"aud_{uuid.uuid4().hex[:6]}"
    _crear_usuario_con_permiso(mundo, nombre, "gobierno_autoridad", "view", mundo.company_a)
    return nombre


def test_org07_ea13_persona_reservada_sin_permiso_de_ocupacion(mundo, delegacion, suplencia, auditor):
    filas = _filas(mundo, D(2, 15), delegacion["delegante"], usuario=auditor)
    fila = _delegadas(filas)[0]
    assert fila["fuente"]["persona"] is None
    assert fila["fuente"]["persona_reservada"] is True
    assert fila["fuente"]["asignacion_codigo"] == delegacion["asignacion"]["codigo"]  # la fuente sí se ve
    sup = _filas(mundo, D(2, 10), suplencia["cargo"], usuario=auditor)[0]["fuente"]
    assert (sup["persona"], sup["persona_reservada"], sup["sustituye_a"], sup["sustituye_reservado"]) == (None, True, None, True)
    # El texto libre no revela a la persona reservada.
    assert _matriz(mundo, D(2, 15), usuario=auditor, texto=delegacion["funcionario"]["nombre"])["items"] == []
    csv_auditor = _csv(mundo, D(2, 15), usuario=auditor, cargo_id=delegacion["delegante"])
    fila_csv = next(f for f in csv_auditor if f["origen"] == "DELEGACION_ATRIBUCIONES")
    assert (fila_csv["persona"], fila_csv["persona_codigo"]) == ("Reservado", "")


# ---------------------------------------------------------------- CSV (§24)
def test_org07_ea14_csv_mismo_universo_que_la_pantalla(mundo, delegacion):
    pantalla = _filas(mundo, D(2, 15), delegacion["delegante"])
    exportado = _csv(mundo, D(2, 15), cargo_id=delegacion["delegante"])
    assert [(f["accion"], f["origen"]) for f in exportado] == [(f["accion"], f["origen"]) for f in pantalla]
    fila = next(f for f in exportado if f["origen"] == "DELEGACION_ATRIBUCIONES")
    assert fila["figura"] == "Delegación de atribuciones"
    assert fila["persona"] == delegacion["funcionario"]["nombre"]
    assert fila["persona_codigo"] == delegacion["funcionario"]["codigo"]
    assert fila["asignacion"] == delegacion["asignacion"]["codigo"]
    assert fila["asignacion_desde"] == D(2, 1).isoformat()
    assert fila["cargo_origen"] != ""
    assert fila["acto"].startswith("RESOLUCION ")
    assert (fila["tipo_limite"], fila["monto"], fila["moneda"]) == ("MONTO", "1000.00", "VES")


# ---------------------------------------------------------------- aislamiento (§29.15-16)
def test_org07_ea15_aislamiento_de_empresa_y_tenant(mundo, delegacion):
    resp = mundo.client.get(
        M,
        headers=mundo.como("ub", mundo.company_b),
        params={"fecha": D(2, 15).isoformat(), "por_pagina": 200},
    )
    assert resp.status_code == 200, resp.text
    assert not any((f.get("fuente") or {}).get("asignacion_id") == delegacion["asignacion"]["id"] for f in resp.json()["items"])
    resp = mundo.client.get(
        M,
        headers=mundo.como("ub", mundo.company_b),
        params={"fecha": D(2, 15).isoformat(), "cargo_id": delegacion["delegante"]},
    )
    assert resp.status_code == 422, resp.text
    resp = mundo.client.get(
        M,
        headers=mundo.como("uc", mundo.company_a, tenant="T2"),
        params={"fecha": D(2, 15).isoformat()},
    )
    assert resp.status_code in (403, 404), resp.text


def test_org07_ea16_sin_duplicados_en_toda_la_matriz(mundo, delegacion, suplencia):
    for fecha in (D(1, 20), D(2, 10), D(3, 10)):
        ids = [f["id"] for f in _matriz(mundo, fecha)["items"]]
        assert len(ids) == len(set(ids)), fecha


# ---------------------------------------------------------------- defecto de ORG-04 destapado por la E2E del ciclo
def test_org07_ea17_activar_delegacion_con_la_sesion_de_la_app(mundo, gobierno, ocupacion):
    """La app usa `autoflush=False`: las competencias delegadas deben quedar escritas mientras la asignación es BORRADOR.

    Antes, `activar` dejaba el INSERT de las competencias para después del UPDATE a ACTIVO y el disparador
    `kontrol_gov_asignacion_competencia_inmutable` lo rechazaba (500 en la app real; las pruebas lo ocultaban con autoflush).
    """
    from app.core.database import get_db

    app = mundo.client.app
    anterior = app.dependency_overrides[get_db]

    def _db_de_la_app():
        d = mundo.factory(autoflush=False)
        try:
            yield d
        finally:
            d.close()

    body = _delegacion(mundo, ocupacion)
    app.dependency_overrides[get_db] = _db_de_la_app
    try:
        asignacion = activa(mundo, body)
    finally:
        app.dependency_overrides[get_db] = anterior
    assert asignacion["status"] == "ACTIVO"
    assert len(_delegadas(_filas(mundo, D(2, 15), body["cargo_id"]))) == 1
