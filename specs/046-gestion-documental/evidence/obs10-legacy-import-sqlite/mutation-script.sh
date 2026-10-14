#!/bin/bash
set -u; cd <repo>/resources/backend; export PYTHONDONTWRITEBYTECODE=1
eval "$(.venv/bin/python ../../qa/clamav_qa.py entorno)"; export KONTROL_CLAMSCAN_PATH KONTROL_CLAMAV_DB
G=<tmp>/o10/good
PY=.venv/bin/python; LEG=tests/test_documents_legacy_import.py; CON=tests/test_documents_legacy_import_contrato.py; CF=tests/conftest.py
purgar() { find tests app -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null; }
correr() { local et="$1"; shift; local salida; salida=$($PY -m pytest "$@" -q -o addopts="" -p no:cacheprovider 2>&1); echo "  [$et] $(echo "$salida" | tail -n 1)"; echo "$salida" | grep -E "^FAILED" | sed -E 's/ - .*//; s/^/      /'; }
mutar() { $PY - "$1" "$2" <<'PYEOF'
import sys; p, cambio = sys.argv[1], sys.argv[2]; s = open(p).read(); viejo, nuevo = cambio.split("\n=====\n")
assert s.count(viejo) >= 1, f"SEARCH no encontrado en {p}"; open(p, "w").write(s.replace(viejo, nuevo, 1))
PYEOF
}
restaurar() { cp $G/test_documents_legacy_import.py $LEG; cp $G/test_documents_legacy_import_contrato.py $CON; cp $G/conftest.py $CF; purgar; cmp -s $G/test_documents_legacy_import.py $LEG && cmp -s $G/test_documents_legacy_import_contrato.py $CON && cmp -s $G/conftest.py $CF && echo "  [RESTORED] copias idénticas" || echo "  [RESTORED] ¡DIFIEREN!"; }
echo "=== GOOD → PASS ==="; purgar; correr GOOD $LEG $CON
m() { local id=$1 f=$2 cambio=$3 desc=$4; shift 4; echo "=== $id · $desc ==="; mutar "$f" "$cambio" || { echo "  [MUTATION] mal formada"; restaurar; return; }; purgar; correr MUTATED "$@"; rm -rf /tmp/kontrol-test-sqlite-* 2>/dev/null; restaurar; correr RESTORED $LEG $CON; }
m M-01 $LEG $'    with motor_para_hilos("documents-legacy-import") as engine:\n=====\n    with __import__("contextlib").nullcontext(__import__("tests.conftest", fromlist=["make_engine"]).make_engine()) as engine:' "volver a make_engine() (conexión compartida)" $LEG $CON
m M-02 $LEG $'    company, actor = _company_id(), _actor()\n    db = _FACTORY()\n    try:\n        doc_type = _doc_type(db, company)\n        reference = _reference(db, company, "9f" * 32,\n=====\n    db = _FACTORY()\n    try:\n        company, actor = _company_id(), _actor()\n        doc_type = _doc_type(db, company)\n        reference = _reference(db, company, "9f" * 32,' "HTTP con la sesión de escritura abierta (caso 5)" $LEG $CON
m M-03 $LEG $'        db.commit()\n        document_id = str(document.id)\n=====\n        document_id = str(document.id)' "omitir el commit antes del GET" $LEG $CON
m M-04 $CF $'        f"sqlite+pysqlite:///{os.path.join(directorio, \'base.db\')}",\n=====\n        "sqlite+pysqlite:///:memory:",' ":memory: privado por conexión" $LEG tests/test_motor_para_hilos.py
m M-05 $LEG $'        def _override_get_db():\n            d = factory()\n            try:\n                yield d\n            finally:\n                d.close()\n=====\n        compartida = factory()\n\n        def _override_get_db():\n            yield compartida' "la API comparte una sola sesión con las pruebas" $LEG $CON
m M-06 $LEG $'    assert r.status_code == 409, r.text\n=====\n    assert r.status_code in (409, 200), r.text' "debilitar el HTTP esperado" $CON
m M-07 $LEG $'        assert reference.classification == "MIGRATION_BLOCKER"\n=====\n        assert reference.classification in ("MIGRATION_BLOCKER", "MISSING_FILE")' "debilitar la clasificación esperada" $CON
m M-10 $LEG $'        document = service.import_legacy_reference(\n            db, reference=reference, search_roots=[_LEGACY], doc_type=doc_type,\n            actor=actor)\n        db.commit()\n        assert document is None\n        assert reference.document_id is None\n=====\n        for _intento in range(3):\n            document = service.import_legacy_reference(\n                db, reference=reference, search_roots=[_LEGACY], doc_type=doc_type,\n                actor=actor)\n        db.commit()\n        assert document is None\n        assert reference.document_id is None' "retry" $CON
m M-11 $LEG $'    company, actor = _company_id(), _actor()\n=====\n    __import__("time").sleep(0.01)\n    company, actor = _company_id(), _actor()' "sleep" $CON
m M-12 $LEG $'def test_un_hash_suelto_sigue_sin_ser_un_documento():\n=====\n@pytest.mark.skipif(True, reason="x")\ndef test_un_hash_suelto_sigue_sin_ser_un_documento():' "skip de una importadora" $CON
m M-13 $LEG $'    set_storage(FilesystemStorageProvider(_ROOT))\n=====\n    set_storage(FilesystemStorageProvider(_ROOT))\n    from app.modules.documents import scanning\n    scanning.set_scanner(scanning.DisabledScanner())' "apagar el analizador en el fixture" $CON
m M-14 $LEG $'def _doc_type(db: Session, company: str) -> DocumentType:\n=====\ndef _doc_type(db: Session, company: str = _company_id()) -> DocumentType:' "el ayudante vuelve a llamar a la API" $CON
echo "=== FIN · tmp: $(ls -d /tmp/kontrol-test-sqlite-* 2>/dev/null | wc -l) ==="; git -C <repo> status --short | grep -vE "specs/"
