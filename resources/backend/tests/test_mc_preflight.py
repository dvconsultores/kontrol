"""Clasificación del backfill multiempresa (ARCH-MC-001, fase N4).

Lo que se fija aquí es que el clasificador **no invente empresas**. Cada caso
representa una forma real del legado, y la prueba más importante no es que
acierte cuando puede, sino que se declare incapaz cuando no puede.

Sobre PostgreSQL real: la clasificación depende de fechas y de claves foráneas,
y ninguna de las dos se comporta igual en SQLite.
"""

from __future__ import annotations

import datetime as dt
import os

import pytest

from app.core.mc.preflight import MC, empresa_unica_en

PG = os.environ.get("KONTROL_TEST_DB_URL", "")
pytestmark = pytest.mark.skipif(
    "postgresql" not in PG,
    reason="La clasificación solo es verificable sobre PostgreSQL (P21)")

HOY = dt.datetime(2026, 8, 31)
A = ("co-a", dt.datetime(2024, 1, 1))
B = ("co-b", dt.datetime(2026, 3, 1))


# ---------------------------------------------------------------- intervalo
def test_tenant_con_una_sola_empresa_siempre_es_determinista():
    assert empresa_unica_en([A], HOY) == "co-a"


def test_antes_de_la_segunda_empresa_es_determinista():
    """El registro de 2025 solo pudo ser de la primera: aún no había otra."""
    assert empresa_unica_en([A, B], dt.datetime(2025, 6, 1)) == "co-a"


def test_despues_de_la_segunda_no_se_deduce():
    """Y el de 2026 podría ser de cualquiera. No se elige."""
    assert empresa_unica_en([A, B], dt.datetime(2026, 6, 1)) is None


def test_la_trampa_del_recuento_actual():
    """El error que esta prueba existe para impedir.

    Un tenant que **hoy** tiene una sola empresa pudo tener dos cuando se creó
    la fila. Rellenar por el recuento de hoy atribuiría facturas a la empresa
    equivocada, y lo haría con toda la apariencia de ser correcto.
    """
    historia = [A, B]                      # hoy podría quedar solo una activa
    assert len(historia) == 2
    assert empresa_unica_en(historia, dt.datetime(2026, 6, 1)) is None


def test_sin_fecha_y_con_dos_empresas_no_se_deduce():
    assert empresa_unica_en([A, B], None) is None


def test_sin_fecha_pero_con_una_sola_empresa_si():
    assert empresa_unica_en([A], None) == "co-a"


def test_el_borde_exacto_cuenta_como_existente():
    """Creada el mismo instante: la empresa ya existe, así que hay dos."""
    assert empresa_unica_en([A, B], B[1]) is None


# ---------------------------------------------------------------- criticidad
def test_los_dominios_criticos_estan_declarados():
    from app.core.mc.preflight import CRITICOS

    assert CRITICOS["fiscal"] == "fiscal"
    assert CRITICOS["treasury"] == "financiero"
    assert CRITICOS["inventory"] == "inventario"
    # Los maestros no son críticos: una empresa mal puesta ahí se corrige;
    # en un libro fiscal, no.
    assert "master_data" not in CRITICOS


def test_las_clases_van_de_mas_a_menos_certeza():
    assert [c.value for c in MC] == ["MC-A", "MC-B", "MC-C", "MC-D", "MC-E", "OK"]


# ---------------------------------------------------------------- autoridades
def test_una_ruta_anulable_no_es_una_ruta():
    """Solo se admiten claves foráneas obligatorias.

    Con una FK anulable la fila puede quedarse sin dueño, y una ruta que puede
    desaparecer no sirve para afirmar nada.
    """
    import sqlalchemy as sa

    from app.core.mc.preflight import autoridades_de

    md = sa.MetaData()
    sa.Table("padre", md, sa.Column("id", sa.String, primary_key=True),
             sa.Column("company_id", sa.String))
    hija = sa.Table(
        "hija", md,
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("obligatoria_id", sa.String, sa.ForeignKey("padre.id"), nullable=False),
        sa.Column("opcional_id", sa.String, sa.ForeignKey("padre.id"), nullable=True))
    rutas = autoridades_de(hija, {"padre"})
    assert [r.columna for r in rutas] == ["obligatoria_id"]


def test_el_planificador_excluye_lo_que_no_hay_que_reconstruir():
    """No entran ni las derivadas ni las que ya tienen la empresa correcta."""
    from app.core.mc.runner import planes

    ps = planes()
    nombres = {p.tabla for p in ps}
    # Ya correctas por FK real (Spec 008 / 045 / 046).
    assert "warehouses" not in nombres
    assert "approval_requests" not in nombres
    assert "documents" not in nombres
    # Derivadas: no tienen columna que reconstruir.
    assert "sales_order_lines" not in nombres
    # Y sí entran las que guardan el tenant.
    assert "parties" in nombres
    assert "fiscal_number_series" in nombres


# ---------------------------------------------------- escenarios reales (E2E)
@pytest.fixture(scope="module")
def informe():
    """Preflight real sobre la base legacy sembrada, en PostgreSQL."""
    from app.core.mc.runner import ejecutar

    url = PG.rsplit("/", 1)[0] + "/kontrol_legacy"
    from sqlalchemy import create_engine, text
    try:
        with create_engine(url).connect() as c:
            c.execute(text("select 1 from parties limit 1"))
    except Exception:                                   # noqa: BLE001
        pytest.skip("no hay base legacy sembrada en este entorno")
    return ejecutar(url)


def _clase_de(informe, tabla, fila_id):
    for r in informe["resultados"]:
        if r["tabla"] == tabla:
            return r
    return None


def test_el_preflight_no_escribe_nada(informe):
    """La garantía que permite ejecutarlo contra producción."""
    assert informe["cero_escrituras"]["conteos_iguales"] is True
    assert informe["cero_escrituras"]["alembic_igual"] is True


def test_clasifica_los_cinco_casos_del_legado(informe):
    t = informe["total"]
    assert t["MC-A"] >= 1, "el tenant monoempresa debe ser determinista"
    assert t["MC-B"] >= 1, "el saldo debe derivarse por su almacén"
    assert t["MC-C"] >= 1, "la fila posterior a la segunda empresa es ambigua"
    assert t["MC-E"] >= 1, "una serie fiscal sin empresa deducible es crítica"
    assert t["OK"] >= 1, "la fila que ya tenía empresa no se reclasifica"


def test_una_fila_ya_correcta_no_se_toca(informe):
    r = _clase_de(informe, "parties", None)
    assert r["por_clase"].get("OK", 0) >= 1


def test_el_saldo_se_deriva_por_su_almacen(informe):
    """Prefiere la autoridad del dominio al recuento del tenant.

    El tenant tenía dos empresas, así que por intervalo sería ambiguo. Pero el
    almacén dice inequívocamente cuál es, y esa evidencia pesa más.
    """
    r = _clase_de(informe, "inventory_balances", None)
    assert r["por_clase"].get("MC-B", 0) == 1
    assert r["por_clase"].get("MC-C", 0) == 0


def test_la_serie_fiscal_ambigua_se_marca_critica_no_ambigua(informe):
    """En fiscal no basta con decir «ambiguo»: es MC-E y bloquea."""
    r = _clase_de(informe, "fiscal_number_series", None)
    assert r["por_clase"].get("MC-E", 0) == 1
    assert r["por_clase"].get("MC-A", 0) == 1     # la del tenant monoempresa sí
    assert r["por_clase"].get("MC-C", 0) == 0


def test_ninguna_fila_critica_se_rebaja_de_clase(informe):
    """MC-E sigue siendo MC-E aunque resulte incómodo."""
    criticos = [r for r in informe["resultados"] if r["por_clase"].get("MC-E")]
    for r in criticos:
        assert r["detalle_critico"], f"{r['tabla']}: MC-E sin detalle que lo justifique"
