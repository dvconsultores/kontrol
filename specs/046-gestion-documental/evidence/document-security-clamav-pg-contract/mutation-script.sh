#!/bin/bash
set -u; cd <repo>/resources/backend; export PYTHONDONTWRITEBYTECODE=1
G=<tmp>/de/good
PY=.venv/bin/python; SEC=tests/test_documents_security.py; CON=tests/test_documents_carreras_contrato.py
purgar() { find tests app -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null; }
correr() { local et="$1"; shift; local salida; salida=$($PY -m pytest "$@" -q -o addopts="" -p no:cacheprovider 2>&1); echo "  [$et] $(echo "$salida" | tail -n 1)"; echo "$salida" | grep -E "^FAILED" | sed -E 's/ - .*//; s/^/      /'; }
mutar() { $PY - "$1" "$2" <<'PYEOF'
import sys; p, cambio = sys.argv[1], sys.argv[2]; s = open(p).read(); viejo, nuevo = cambio.split("\n=====\n")
assert s.count(viejo) == 1, f"SEARCH no único/no encontrado en {p}: {s.count(viejo)}"; open(p, "w").write(s.replace(viejo, nuevo))
PYEOF
}
restaurar() { cp $G/test_documents_security.py $SEC; cp $G/test_documents_carreras_contrato.py $CON; purgar; cmp -s $G/test_documents_security.py $SEC && cmp -s $G/test_documents_carreras_contrato.py $CON && echo "  [RESTORED] copias idénticas" || echo "  [RESTORED] ¡DIFIEREN!"; }
echo "=== GOOD → PASS ==="; purgar; correr GOOD $CON
m() { local id=$1 f=$2 cambio=$3 desc=$4; shift 4; echo "=== $id · $desc ==="; mutar "$f" "$cambio" || { echo "  [MUTATION] mal formada"; restaurar; return; }; purgar; correr MUTATED "$@"; restaurar; correr RESTORED $CON; }
m M-0X $SEC $'@solo_postgresql\ndef test_tres_subidas_simultaneas_crean_una_sola_version(\n=====\ndef test_tres_subidas_simultaneas_crean_una_sola_version(' "quitar el marcador a una carrera" $CON
m M-0X $SEC $'@solo_postgresql\n@pytest.mark.parametrize("vuelta", range(3))\n=====\n@pytest.mark.parametrize("vuelta", range(3))' "quitar el marcador a la carrera parametrizada" $CON
m M-0X $SEC $'\ndef test_amz_10_malware_no_se_almacena_ni_se_entrega():\n=====\n\n@solo_postgresql\ndef test_amz_10_malware_no_se_almacena_ni_se_entrega():' "marcar PostgreSQL-only una prueba que no es carrera" $CON
m M-04 $SEC $'    not PG, reason="la carrera de versiones se certifica sobre PostgreSQL (FR-046-115, conc-046; P21)")\n=====\n    not PG, reason="solo PostgreSQL")' "razón sin autoridad" $CON
m M-0X $SEC $'PG = os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql")\n=====\nPG = True' "PG fijo: el marcador nunca omite" $CON
m M-0X $SEC $'solo_postgresql = pytest.mark.skipif(\n    not PG, reason=\n=====\nsolo_postgresql = pytest.mark.skipif(\n    True, reason=' "omitir siempre (también en PostgreSQL)" $CON
m M-07 $SEC $'def test_amz_12_clave_de_almacenamiento_opaca():\n=====\ndef test_amz_12_clave_de_almacenamiento_opaca():\n    _ = carrera' "primitiva PostgreSQL en una prueba sin marcador" $CON
m M-08 $SEC $'    engine = make_engine()\n=====\n    engine = make_engine()\n    scanning.set_scanner(scanning.DisabledScanner())' "apagar el analizador en el fixture" $CON
m M-09 $SEC $'    assert _upload(document, PDF, name="base.pdf").status_code == 200\n    antes = _huella(document)\n\n    primero, segundo = carrera(\n=====\n    assert _upload(document, PDF, name="base.pdf").status_code in (200, 422)\n    antes = _huella(document)\n\n    primero, segundo = carrera(' "aceptar el rechazo del analizador como subida" $CON
m M-10 $SEC $'@solo_postgresql\ndef test_subidas_a_documentos_distintos_no_se_esperan(\n=====\ndef test_subidas_a_documentos_distintos_no_se_esperan(' "quitar el marcador a la séptima carrera (documentos distintos no se esperan)" $CON
echo "=== FIN ==="; git status --short tests/
