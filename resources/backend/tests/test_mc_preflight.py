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
    """Las cinco de reconstrucción, más «ya correcta» y las dos anomalías."""
    assert [c.value for c in MC] == [
        "MC-A", "MC-B", "MC-C", "MC-D", "MC-E", "OK",
        "INVALID_LEGACY_SCOPE", "CROSS_TENANT"]


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


def test_el_planificador_ya_no_encuentra_nada_que_reconstruir():
    """Tras N7 el conjunto de trabajo queda vacío, y eso es lo correcto.

    El planificador excluye las tablas cuya `company_id` tiene clave foránea,
    porque su propiedad ya está garantizada por la estructura. Antes de N7 eso
    valía para 17 tablas; después vale para todas, así que no queda nada que
    reconstruir.

    Es el resultado esperado de haber cerrado la ventana a tiempo: `N4 Real
    Backfill` sigue `NOT_APPLICABLE` porque no hay ninguna instalación
    desplegada, y ahora tampoco hay nada que una instalación nueva pudiera
    necesitar reconstruir.

    **Limitación registrada para la Spec 052.** El planificador infiere del
    modelo vigente, no del catálogo de la base destino. Contra una instalación
    heredada anterior a N7 —cuyo esquema sí tiene columnas sin referencia—
    seguiría viendo el modelo actual y devolvería vacío. Cuando exista una
    actualización real desde una versión previa, el planificador tendrá que
    leer el catálogo del destino. No se cambia aquí porque no hay ningún destino
    heredado que leer, y adivinar su forma sería inventar el requisito.
    """
    from app.core.mc.runner import planes

    nombres = {p.tabla for p in planes()}
    assert nombres == set(), (
        f"quedan tablas sin propiedad estructural garantizada: {sorted(nombres)}")


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


# ------------------------------------------------ anomalías y estrategias
def test_un_valor_que_no_es_tenant_ni_empresa_no_es_un_hueco():
    """`INVALID_LEGACY_SCOPE` existe para no confundir roto con incompleto.

    Una fila cuyo `company_id` no corresponde a ningún tenant ni a ninguna
    empresa no está esperando la migración: ya estaba mal. Clasificarla como
    «sin evidencia» la escondería entre las que sí son reconstruibles.
    """
    assert MC.INVALID.value == "INVALID_LEGACY_SCOPE"
    assert MC.CROSS_TENANT.value == "CROSS_TENANT"


def test_un_maestro_compartido_se_clona_no_se_adjudica():
    """La pregunta correcta no es «¿de quién es?» sino «¿cuántas lo usaron?».

    Si dos empresas usaron el mismo maestro, asignárselo a una rompe a la otra.
    """
    from app.core.mc.preflight import MasterStrategy, estrategia_de_maestro

    assert estrategia_de_maestro({"co-a"}) is MasterStrategy.ASSIGN
    assert estrategia_de_maestro({"co-a", "co-b"}) is MasterStrategy.CLONE
    assert estrategia_de_maestro(set()) is MasterStrategy.MANUAL


def test_las_cinco_estrategias_de_maestro_existen():
    from app.core.mc.preflight import MasterStrategy

    assert [m.value for m in MasterStrategy] == [
        "MASTER_ASSIGN", "MASTER_CLONE", "MASTER_DERIVE",
        "MASTER_MANUAL_REVIEW", "MASTER_BLOCKED"]


def test_una_empresa_inactiva_sigue_contando_en_el_intervalo():
    """Desactivada hoy no significa inexistente entonces.

    Si se excluyera, un registro de la época en que operaba se atribuiría a la
    otra empresa: exactamente la clase de invención que esto evita.
    """
    inactiva = ("co-b", dt.datetime(2026, 3, 1))
    assert empresa_unica_en([A, inactiva], dt.datetime(2026, 6, 1)) is None


# ------------------------------------------------ garantías de ejecución
def test_el_preflight_es_repetible(informe):
    """Dos corridas sobre la misma base dan el mismo resultado."""
    from app.core.mc.runner import ejecutar

    url = PG.rsplit("/", 1)[0] + "/kontrol_legacy"
    segunda = ejecutar(url)
    assert segunda["total"] == informe["total"]
    assert segunda["filas"] == informe["filas"]


def test_la_base_rechaza_una_escritura_aunque_el_codigo_falle():
    """Segunda capa: no basta con que el ejecutor «no deba» escribir.

    Sobre una copia de datos reales, la disciplina del código no es garantía
    suficiente. La transacción se declara de solo lectura y el motor rechaza
    cualquier escritura.
    """
    from sqlalchemy import create_engine, text

    url = PG.rsplit("/", 1)[0] + "/kontrol_legacy"
    e = create_engine(url, future=True)
    try:
        with e.connect() as cx:
            cx.execute(text("SET TRANSACTION READ ONLY"))
            with pytest.raises(Exception) as excinfo:
                cx.execute(text("UPDATE parties SET name = 'X' WHERE 1=0"))
            # Se comprueba el tipo de error de psycopg2, no su mensaje: el
            # mensaje viene traducido y depende de la configuración regional.
            original = getattr(excinfo.value, "orig", excinfo.value)
            assert type(original).__name__ == "ReadOnlySqlTransaction"
    except Exception as exc:                              # noqa: BLE001
        if "does not exist" in str(exc):
            pytest.skip("no hay base legacy en este entorno")
        raise


# ===================================================================== N8 sello
# Evidencia explícita: cada clase con su fila real, su ejecución, cero
# escrituras y resultado repetible. No basta con que el enum exista.


def _clases(informe) -> dict[str, int]:
    return {k: v for k, v in informe["total"].items() if v}


def test_la_semilla_hostil_contiene_los_casos_que_se_van_a_probar(informe):
    """Antes de comprobar clasificaciones, comprobar que hay qué clasificar.

    Este proyecto ya vivió una vez que el fixture estuviera vacío y las pruebas
    pasaran igual. Si el informe no trae filas, todo lo que sigue es aritmética
    sobre la nada.
    """
    assert informe["filas"] > 0, "el preflight no encontró ninguna fila que clasificar"
    assert informe["tenants"] >= 3, "faltan tenants en la semilla"
    assert informe["empresas"] >= 3, "faltan empresas en la semilla"


def test_mc_d_existe_y_no_es_un_cajon_de_sastre(informe):
    """`MC-D` = `NON_RECONSTRUCTIBLE`: sin evidencia, en dominio no crítico.

    La semilla es un tenant **sin ninguna empresa**: no hay intervalo del que
    deducir ni autoridad de la que derivar, y anotarlo es todo lo que se puede
    hacer honestamente.
    """
    t = _clases(informe)
    assert t.get("MC-D", 0) >= 1, f"ninguna fila se clasificó MC-D: {t}"


def test_invalid_no_se_degrada_a_sin_evidencia(informe):
    """Un valor que no es ni tenant ni empresa **ya estaba roto**.

    Clasificarlo como «sin evidencia» lo escondería entre las filas que sí son
    reconstruibles, y su reparación es de otra naturaleza.
    """
    t = _clases(informe)
    assert t.get("INVALID_LEGACY_SCOPE", 0) >= 1, f"no se emitió INVALID: {t}"
    r = _clase_de(informe, "parties", None)
    assert r["por_clase"].get("INVALID_LEGACY_SCOPE", 0) >= 1
    # Y conserva su detalle crítico: no se cuenta y se olvida.
    invalidos = [d for d in r["detalle_critico"]
                 if d["clase"] == "INVALID_LEGACY_SCOPE"]
    assert invalidos, "INVALID se contó pero no dejó detalle"


def test_cross_tenant_no_se_informa_como_correcto(informe):
    """El defecto que este sello destapó.

    Una fila con empresa **real** pero de otro cliente entraba por la primera
    rama —«¿ya tiene empresa? entonces nada que hacer»— y se marcaba `OK`. Una
    integridad rota entre instalaciones se informaba como correcta.
    """
    t = _clases(informe)
    assert t.get("CROSS_TENANT", 0) >= 1, (
        f"no se emitió CROSS_TENANT: una fila que cruza clientes pasó como buena. {t}")
    r = _clase_de(informe, "inventory_balances", None)
    assert r["por_clase"].get("CROSS_TENANT", 0) >= 1
    cruces = [d for d in r["detalle_critico"] if d["clase"] == "CROSS_TENANT"]
    assert cruces and cruces[0]["rutas"], "CROSS_TENANT no explica dónde está el cruce"


def test_las_clases_criticas_no_se_confunden_entre_si(informe):
    """§7 del encargo: `MC-D` no puede absorber lo que tiene severidad propia."""
    t = _clases(informe)
    assert t.get("INVALID_LEGACY_SCOPE", 0) >= 1
    assert t.get("CROSS_TENANT", 0) >= 1
    assert t.get("MC-E", 0) >= 1
    # Cada una cuenta por su lado: si MC-D las hubiera absorbido, las tres
    # estarían en cero y MC-D inflado.
    assert t.get("MC-D", 0) >= 1


def test_las_estrategias_de_maestro_se_calculan_en_la_corrida(informe):
    """Antes existía la función y nadie la llamaba.

    `MAESTROS` estaba definido y sin usar, así que las cuatro estrategias eran
    nombres en un enum. Ahora el informe las trae por tabla.
    """
    maestros = informe.get("maestros") or {}
    assert maestros, "el informe no trae estrategias de maestro"
    vistas = {e for conteo in maestros.values() for e in conteo}
    for esperada in ("MASTER_ASSIGN", "MASTER_CLONE", "MASTER_DERIVE",
                     "MASTER_MANUAL_REVIEW"):
        assert esperada in vistas, (
            f"{esperada} no apareció en ninguna fila de la corrida: {maestros}")


def test_el_maestro_compartido_se_clona_y_el_propio_se_adjudica(informe):
    """La regla de fondo: si dos empresas lo usaron, asignárselo a una rompe a la otra."""
    maestros = informe.get("maestros") or {}
    total: dict[str, int] = {}
    for conteo in maestros.values():
        for e, n in conteo.items():
            total[e] = total.get(e, 0) + n
    assert total.get("MASTER_ASSIGN", 0) >= 1, f"ninguna fila resultó ASSIGN: {total}"
    assert total.get("MASTER_CLONE", 0) >= 1, (
        f"ningún maestro compartido se propuso clonar: {total}")
    assert total.get("MASTER_DERIVE", 0) >= 1, f"DERIVE no se alcanzó: {total}"
    assert total.get("MASTER_MANUAL_REVIEW", 0) >= 1, f"MANUAL_REVIEW no se alcanzó: {total}"


def test_derive_solo_aparece_cuando_hay_relacion_obligatoria():
    """`DERIVE` no podía devolverse nunca: la función no recibía ese dato.

    El enum lo definía —«se deduce por una relación obligatoria»— y
    `estrategia_de_maestro` solo veía el conjunto de empresas, donde esa
    relación no cabe.
    """
    from app.core.mc.preflight import MasterStrategy, estrategia_de_maestro

    # Sin ninguna evidencia no hay nada que deducir: revisión manual.
    assert estrategia_de_maestro(set(), derivable=True) is MasterStrategy.MANUAL
    assert estrategia_de_maestro(set(), derivable=False) is MasterStrategy.MANUAL
    # Con una empresa: se adjudica si la evidencia es propia, se deduce si llegó
    # por la relación. El dato resultante es el mismo y la confianza no.
    assert estrategia_de_maestro({"co-a"}, derivable=False) is MasterStrategy.ASSIGN
    assert estrategia_de_maestro({"co-a"}, derivable=True) is MasterStrategy.DERIVE
    # Con dos, ninguna de las anteriores sirve: adjudicar rompería a la otra.
    assert estrategia_de_maestro({"co-a", "co-b"}, derivable=True) is MasterStrategy.CLONE


def test_cada_clase_se_repite_identica_en_dos_corridas(informe):
    """Repetibilidad **por clase**, no solo del total.

    Dos corridas que sumaran lo mismo con clases distintas darían el mismo
    número y significarían cosas diferentes.
    """
    from app.core.mc.runner import ejecutar

    url = PG.rsplit("/", 1)[0] + "/kontrol_legacy"
    segunda = ejecutar(url)
    assert _clases(segunda) == _clases(informe), "la clasificación cambió entre corridas"
    assert segunda.get("maestros") == informe.get("maestros"), (
        "las estrategias de maestro cambiaron entre corridas")
    assert segunda["cero_escrituras"]["conteos_iguales"] is True
    assert segunda["cero_escrituras"]["alembic_igual"] is True
