"""BUD-02 · Jerarquía del clasificador presupuestario (BUD-02-CLASSIFIER-PARENT-LEVEL).

Una partida de nivel N solo puede tener como padre una partida del MISMO clasificador (ejercicio y empresa), del
mismo tipo y del nivel N-1 (BUD12-06). La regla es una sola (`validar_padre_partida`) para el alta y para la
importación CSV todo-o-nada. Se ejecuta sobre PostgreSQL, como el resto de BUD-01/02.
"""

import io
from datetime import date

from sqlalchemy import select

from app.modules.government import service_presupuesto
from app.modules.government.models import GovernmentBudgetClassifierItem
from tests.test_gov_bud01_ejercicio import (
    CABECERA_CSV,
    ONLY_PG,
    P,
    _aprobar,
    _completo,
    _crear,
    _put,
)
from tests.test_gov_ctl06_hallazgos import _post

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")


def _partida(mundo, detalle, tipo, codigo, nivel, padre, *, usuario="ua", empresa=None):
    empresa = empresa or mundo.company_a
    anio = detalle["anio"]
    return _post(
        mundo,
        f"{P}/{detalle['id']}/clasificador/partidas",
        usuario,
        empresa,
        {
            "tipo": tipo,
            "codigo": codigo,
            "denominacion": f"Partida {codigo}",
            "nivel": nivel,
            "codigo_padre": padre,
            "vigente_desde": date(anio, 1, 1).isoformat(),
            "vigente_hasta": date(anio, 12, 31).isoformat(),
        },
        version=detalle["version"],
    )


def _ok(r) -> dict:
    assert r.status_code == 201, r.text
    return r.json()


def _rechazada(r, *fragmentos: str) -> None:
    assert r.status_code == 422, r.text
    cuerpo = r.json()
    assert cuerpo["code"] == "GOV_BUDGET_INVALID", cuerpo
    errores_padre = cuerpo["field_errors"].get("codigo_padre")
    assert errores_padre, cuerpo
    for fragmento in fragmentos:
        assert fragmento in errores_padre[0], errores_padre


def _importar(mundo, detalle, filas: str):
    return mundo.client.post(
        f"/api/v1{P}/{detalle['id']}/clasificador/importar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(detalle["version"])},
        files={"archivo": ("partidas.csv", io.BytesIO((CABECERA_CSV + filas).encode("utf-8")), "text/csv")},
    )


def _fila(anio, tipo, codigo, nivel, padre) -> str:
    return f"{tipo},{codigo},Partida {codigo},{nivel},{padre},{anio}-01-01,{anio}-12-31\n"


def _codigos(mundo, detalle, tipo="EGRESO") -> dict[str, dict]:
    r = mundo.get(f"{P}/{detalle['id']}/clasificador/partidas?tipo={tipo}", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    return {i["codigo"]: i for i in r.json()["items"]}


def _clasificador(mundo, detalle, usuario, empresa) -> dict:
    """Registra solo el clasificador (sin partidas) de un ejercicio en borrador."""
    r = _put(
        mundo,
        f"{P}/{detalle['id']}/clasificador",
        usuario,
        empresa,
        {"edicion": "Clasificador ajeno", "procedencia": "Edición cargada por otro ente"},
        detalle["version"],
    )
    assert r.status_code == 200, r.text
    return r.json()


# --- La regla (unidad) --------------------------------------------------------------------------------------------


def test_bud02_j00_regla_unica_sin_base():
    niveles = {("EGRESO", "4"): 1, ("EGRESO", "4.1"): 2, ("EGRESO", "4.1.1"): 3, ("RECURSO", "3"): 1}
    regla = service_presupuesto.validar_padre_partida
    assert regla("EGRESO", 1, None, niveles) is None
    assert regla("EGRESO", 2, "4", niveles) is None
    assert regla("EGRESO", 3, "4.1", niveles) is None
    assert "nivel 1" in regla("EGRESO", 1, "4", niveles)
    assert "codigo_padre" in regla("EGRESO", 2, None, niveles)
    assert "es de nivel 1" in regla("EGRESO", 3, "4", niveles)
    assert "es de nivel 2" in regla("EGRESO", 2, "4.1", niveles)
    assert "es de nivel 3" in regla("EGRESO", 2, "4.1.1", niveles)
    assert "no existe" in regla("EGRESO", 2, "3", niveles)
    assert "no existe" in regla("EGRESO", 2, "9", niveles)


# --- Alta manual ----------------------------------------------------------------------------------------------------


@ONLY_PG
def test_bud02_j01_defecto_nivel_3_con_padre_de_nivel_1(mundo, gobierno):
    """El defecto: 401 (nivel 1) → 401.01 (nivel 2) y C de nivel 3 con padre 401 se aceptaba."""
    detalle = _completo(mundo, 2091)
    _rechazada(
        _partida(mundo, detalle, "EGRESO", "401.99.01", 3, "401"),
        "«401» es de nivel 1",
        "nivel 3",
        "padre de nivel 2",
    )
    assert "401.99.01" not in _codigos(mundo, detalle)
    # Caso positivo: el mismo hijo con su padre del nivel 2.
    detalle = _ok(_partida(mundo, detalle, "EGRESO", "401.01.01", 3, "401.01"))
    partidas = _codigos(mundo, detalle)
    assert partidas["401.01.01"]["codigo_padre"] == "401.01"
    assert partidas["401.01"]["codigo_padre"] == "401"
    assert partidas["401"]["codigo_padre"] is None


@ONLY_PG
def test_bud02_j02_niveles_raiz_mismo_salto_superior_e_inexistente(mundo, gobierno):
    detalle = _completo(mundo, 2092)
    # Raíz: sin padre se acepta; con padre se rechaza.
    detalle = _ok(_partida(mundo, detalle, "EGRESO", "402", 1, None))
    _rechazada(_partida(mundo, detalle, "EGRESO", "403", 1, "401"), "nivel 1 no puede tener")
    # Nivel 2 sin padre.
    _rechazada(_partida(mundo, detalle, "EGRESO", "402.01", 2, None), "debe indicar codigo_padre")
    detalle = _ok(_partida(mundo, detalle, "EGRESO", "401.01.01", 3, "401.01"))
    # Mismo nivel: nivel 3 con padre de nivel 3; nivel 2 con padre de nivel 2.
    _rechazada(_partida(mundo, detalle, "EGRESO", "401.01.02", 3, "401.01.01"), "es de nivel 3")
    _rechazada(_partida(mundo, detalle, "EGRESO", "401.02", 2, "401.01"), "es de nivel 2")
    # Salto: nivel 4 con padre de nivel 2.
    _rechazada(
        _partida(mundo, detalle, "EGRESO", "401.01.09.01", 4, "401.01"), "es de nivel 2", "padre de nivel 3"
    )
    # Padre de nivel superior: nivel 2 con padre de nivel 3.
    _rechazada(_partida(mundo, detalle, "EGRESO", "401.03", 2, "401.01.01"), "es de nivel 3")
    # Padre inexistente y padre de otro tipo (RECURSO 301 existe, pero no es EGRESO).
    _rechazada(_partida(mundo, detalle, "EGRESO", "499.01", 2, "499"), "no existe")
    _rechazada(_partida(mundo, detalle, "EGRESO", "405", 2, "301"), "no existe", "EGRESO")
    # El código del padre se normaliza igual al validar y al enlazar.
    detalle = _ok(_partida(mundo, detalle, "EGRESO", "402.01", 2, " 402 "))
    partidas = _codigos(mundo, detalle)
    assert partidas["402.01"]["codigo_padre"] == "402"
    assert set(partidas) == {"401", "401.01", "401.01.01", "402", "402.01"}


@ONLY_PG
def test_bud02_j03_padre_de_otro_clasificador_de_la_misma_empresa(mundo, gobierno):
    """Cada ejercicio tiene su propio clasificador: un padre de nivel correcto en otro ejercicio no sirve."""
    otro = _completo(mundo, 2093)
    otro = _ok(_partida(mundo, otro, "EGRESO", "409", 1, None))
    # El ejercicio nuevo solo tiene su clasificador: ningún código coincide con el otro salvo el padre buscado.
    detalle = _clasificador(mundo, _crear(mundo, 2094), "ua", mundo.company_a)
    _rechazada(_partida(mundo, detalle, "EGRESO", "409.01", 2, "409"), "no existe en este clasificador")
    assert "409.01" not in _codigos(mundo, otro)
    assert "409.01" not in _codigos(mundo, detalle)


@ONLY_PG
def test_bud02_j04_padre_de_otra_version_aprobada(mundo, gobierno):
    """Una versión aprobada (congelada) no presta padres a otra, y sigue legible tal cual."""
    historico = _completo(mundo, 2095)
    historico = _ok(_partida(mundo, historico, "EGRESO", "408", 1, None))
    antes = _codigos(mundo, historico)
    historico = _aprobar(mundo, historico)
    assert historico["estado"] != "BORRADOR"
    detalle = _clasificador(mundo, _crear(mundo, 2096), "ua", mundo.company_a)
    _rechazada(_partida(mundo, detalle, "EGRESO", "408.01", 2, "408"), "no existe en este clasificador")
    assert _codigos(mundo, historico) == antes


@ONLY_PG
def test_bud02_j05_padre_de_otra_empresa(mundo, gobierno):
    r = _post(mundo, P, "ub", mundo.company_b, {"anio": 2097})
    assert r.status_code == 201, r.text
    ajeno = _clasificador(mundo, r.json(), "ub", mundo.company_b)
    ajeno = _ok(_partida(mundo, ajeno, "EGRESO", "B-407", 1, None, usuario="ub", empresa=mundo.company_b))
    detalle = _completo(mundo, 2097)
    r = _partida(mundo, detalle, "EGRESO", "B-407.01", 2, "B-407")
    _rechazada(r, "no existe en este clasificador")
    # El mensaje no revela nada del otro ente: solo repite el código que escribió el usuario.
    assert "Partida B-407" not in r.text and ajeno["id"] not in r.text
    with mundo.factory() as db:
        assert db.scalar(
            select(GovernmentBudgetClassifierItem.id).where(GovernmentBudgetClassifierItem.codigo == "B-407.01")
        ) is None


# --- Importación CSV ------------------------------------------------------------------------------------------------


@ONLY_PG
def test_bud02_j06_csv_valido_con_padres_del_lote_y_de_la_base(mundo, gobierno):
    detalle = _completo(mundo, 2098)
    anio = detalle["anio"]
    r = _importar(
        mundo,
        detalle,
        _fila(anio, "EGRESO", "401.01.01", 3, "401.01")  # padre ya en la base
        + _fila(anio, "EGRESO", "410", 1, "")
        + _fila(anio, "EGRESO", "410.01", 2, "410")  # padre del mismo lote
        + _fila(anio, "EGRESO", "410.01.01", 3, "410.01"),
    )
    assert r.status_code == 200, r.text
    partidas = _codigos(mundo, r.json())
    assert partidas["401.01.01"]["codigo_padre"] == "401.01"
    assert partidas["410.01.01"]["codigo_padre"] == "410.01"
    assert partidas["410.01"]["nivel"] == 2


@ONLY_PG
def test_bud02_j07_csv_salto_de_nivel_y_orden_rechazan_todo_el_lote(mundo, gobierno):
    detalle = _completo(mundo, 2099)
    anio = detalle["anio"]
    antes = _codigos(mundo, detalle)
    casos = {
        "salto": (
            _fila(anio, "EGRESO", "411", 1, "")
            + _fila(anio, "EGRESO", "411.01", 2, "411")
            + _fila(anio, "EGRESO", "411.01.01", 3, "411"),  # nivel 3 con padre de nivel 1
            "Fila 4: La partida padre «411» es de nivel 1",
        ),
        "mismo_nivel": (
            _fila(anio, "EGRESO", "412", 1, "") + _fila(anio, "EGRESO", "412.01", 1, "401"),
            "Fila 3: El nivel 1 no puede tener",
        ),
        "padre_de_la_base_a_otro_nivel": (
            _fila(anio, "EGRESO", "413", 1, "") + _fila(anio, "EGRESO", "401.01.07.01", 4, "401.01"),
            "Fila 3: La partida padre «401.01» es de nivel 2",
        ),
        "hijo_antes_que_el_padre": (
            _fila(anio, "EGRESO", "414.01", 2, "414") + _fila(anio, "EGRESO", "414", 1, ""),
            "Fila 2: La partida padre «414» no existe",
        ),
    }
    for nombre, (filas, esperado) in casos.items():
        r = _importar(mundo, detalle, filas)
        assert r.status_code == 422, (nombre, r.text)
        errores = r.json()["field_errors"]["archivo"]
        assert any(esperado in e for e in errores), (nombre, errores)
        # Todo o nada: ni las filas válidas del lote quedan escritas.
        assert _codigos(mundo, detalle) == antes, nombre


@ONLY_PG
def test_bud02_j08_arbol_profundo_hasta_el_nivel_12(mundo, gobierno):
    detalle = _completo(mundo, 2100)
    anio = detalle["anio"]
    filas = _fila(anio, "RECURSO", "R1", 1, "")
    for nivel in range(2, 13):
        filas += _fila(anio, "RECURSO", f"R{nivel}", nivel, f"R{nivel - 1}")
    r = _importar(mundo, detalle, filas)
    assert r.status_code == 200, r.text
    partidas = _codigos(mundo, r.json(), "RECURSO")
    assert partidas["R12"]["nivel"] == 12 and partidas["R12"]["codigo_padre"] == "R11"
