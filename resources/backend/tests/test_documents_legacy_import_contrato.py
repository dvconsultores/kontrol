"""O10 · contrato estático de `tests/test_documents_legacy_import.py` (OBS-10; Spec 046, apoyo 054).

Una conexión por sesión sobre el mismo datastore (`motor_para_hilos`), y en cada prueba la empresa y el
actor se resuelven por la API **antes** de abrir la sesión de escritura: dentro de esa sesión no hay
peticiones HTTP ni sesiones auxiliares. Las aserciones de negocio del legado no cambian.
"""

from __future__ import annotations

import ast
from pathlib import Path

MODULO = Path(__file__).with_name("test_documents_legacy_import.py")
IMPORTADORAS = {
    "test_binario_localizable_y_verificable_se_importa",
    "test_lo_importado_no_se_entrega_hasta_verificarse",
    "test_una_url_externa_no_se_importa_como_archivo_propio",
    "test_un_archivo_que_no_esta_se_reporta_no_se_inventa",
    "test_una_huella_que_no_coincide_detiene_la_importacion",
    "test_un_hash_suelto_sigue_sin_ser_un_documento",
    "test_una_ruta_heredada_no_autoriza_a_salir_del_volumen",
}
FUERA_DE_LA_SESION = {"_company_id", "_actor", "_headers", "_CLIENT"}


def _funciones() -> dict[str, ast.FunctionDef]:
    arbol = ast.parse(MODULO.read_text(encoding="utf-8"))
    return {n.name: n for n in arbol.body if isinstance(n, ast.FunctionDef)}


def _nombres_llamados(nodo: ast.AST) -> set[str]:
    usados: set[str] = set()
    for sub in ast.walk(nodo):
        if isinstance(sub, ast.Name):
            usados.add(sub.id)
        if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name):
            usados.add(sub.value.id)
    return usados


def test_o10_el_modulo_corre_sobre_una_conexion_por_sesion():
    fuente = MODULO.read_text(encoding="utf-8")
    assert 'with motor_para_hilos("documents-legacy-import") as engine:' in fuente
    assert "= make_engine()" not in fuente
    # Cada petición de la API recibe su propia sesión y la cierra: ninguna sesión se comparte con la prueba.
    assert ("        def _override_get_db():\n            d = factory()\n            try:\n                yield d\n"
            "            finally:\n                d.close()\n") in fuente


def test_o10_la_empresa_y_el_actor_se_resuelven_antes_de_abrir_la_sesion_de_escritura():
    funciones = _funciones()
    for nombre in IMPORTADORAS:
        fn = funciones[nombre]
        cuerpo = fn.body
        apertura = next(i for i, sentencia in enumerate(cuerpo)
                        if isinstance(sentencia, ast.Assign) and ast.unparse(sentencia.value) == "_FACTORY()")
        previo = cuerpo[:apertura]
        assert any(isinstance(st, ast.Assign) and ast.unparse(st.value) == "(_company_id(), _actor())" for st in previo), nombre
        bloque_try = next(st for st in cuerpo[apertura + 1:] if isinstance(st, ast.Try))
        dentro = _nombres_llamados(ast.Module(body=bloque_try.body, type_ignores=[]))
        assert not (dentro & FUERA_DE_LA_SESION), (nombre, dentro & FUERA_DE_LA_SESION)


def test_o10_los_ayudantes_reciben_la_empresa_y_no_llaman_a_la_api():
    funciones = _funciones()
    for ayudante in ("_doc_type", "_reference"):
        fn = funciones[ayudante]
        assert "company" in [a.arg for a in fn.args.args], ayudante
        assert not (_nombres_llamados(fn) & FUERA_DE_LA_SESION), ayudante


def test_o10_las_aserciones_del_legado_no_cambian():
    fuente = MODULO.read_text(encoding="utf-8")
    for aserto in (
        'assert reference.classification == "VALID_MANAGED_FILE"',
        'assert stored.security_status == "PENDING_SCAN"',
        "assert stored.size == len(CONTENT)",
        "assert r.status_code == 409, r.text",
        'assert r.json()["code"] == "FILE_NOT_SCANNED"',
        'assert reference.classification == "MISSING_FILE"',
        'assert excinfo.value.code == "LEGACY_HASH_MISMATCH"',
        'assert reference.classification == "MIGRATION_BLOCKER"',
        'assert "no localizado" in (reference.notes or "")',
        '== b"otro contenido"',
        'assert remaining == ["F-0001.pdf", "F-0002.pdf"]',
    ):
        assert aserto in fuente, aserto
    assert fuente.count("        db.commit()\n") >= 7  # cada importación confirma su propia sesión
    for prohibido in ("pytest.mark.skip", "skipif", "xfail", "sleep(", "retry", "range(", "while ", "Lock(", "set_scanner(",
                      "DisabledScanner(", "KONTROL_DOCUMENT_SCAN", "KONTROL_CLAMSCAN_PATH"):
        assert prohibido not in fuente, prohibido
