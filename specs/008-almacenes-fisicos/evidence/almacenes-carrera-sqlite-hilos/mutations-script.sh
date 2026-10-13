#!/bin/bash
# Campaña de mutaciones M-01…M-12 (guion de Claude, fuera del repositorio). Copias GOOD en $G; restauración desde la copia, nunca git checkout.
set -u
cd <repo>/resources/backend
export PYTHONDONTWRITEBYTECODE=1
G=<tmp>/acs/good
PY=.venv/bin/python
ACS="tests/test_motor_para_hilos.py"
OBJ="tests/test_warehouse_structure.py::test_concurrencia_de_codigo_resuelta_por_constraint"
purgar() { find tests app -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null; }
correr() { # $1 etiqueta; resto: args de pytest → imprime resumen
  local et="$1"; shift
  local salida; salida=$($PY -m pytest "$@" -q -o addopts="" -p no:cacheprovider 2>&1)
  echo "  [$et] $(echo "$salida" | tail -n 1)"
  echo "$salida" | grep -E "^FAILED" | sed -E 's/ - .*//; s/^/      /'
  echo "$salida" | grep -oE "^E +[A-Za-z]+Error: .{0,100}" | sort | uniq -c | sort -rn | head -3 | sed 's/^/      /'
}
serie_objetivo() { # ×N de la prueba objetivo en SQLite → cuenta fallos
  local n=$1 f=0; for i in $(seq 1 $n); do $PY -m pytest "$OBJ" -q -o addopts="" -p no:cacheprovider 2>&1 | tail -n 1 | grep -q "1 passed" || f=$((f+1)); done; echo "  [objetivo x$n] fallos=$f"
}
mutar() { # $1 fichero; $2 python con SEARCH/REPLACE
  $PY - "$1" "$2" <<'PYEOF'
import sys; p, cambio = sys.argv[1], sys.argv[2]; s = open(p).read(); viejo, nuevo = cambio.split("\n=====\n")
assert s.count(viejo) == 1, f"SEARCH no único/no encontrado en {p}: {s.count(viejo)}"; open(p, "w").write(s.replace(viejo, nuevo))
PYEOF
}
restaurar() { cp $G/conftest.py tests/conftest.py; cp $G/test_warehouse_structure.py tests/test_warehouse_structure.py; cp $G/test_motor_para_hilos.py tests/test_motor_para_hilos.py; purgar; cmp -s $G/conftest.py tests/conftest.py && cmp -s $G/test_warehouse_structure.py tests/test_warehouse_structure.py && cmp -s $G/test_motor_para_hilos.py tests/test_motor_para_hilos.py && echo "  [RESTORED] copias idénticas" || echo "  [RESTORED] ¡DIFIEREN!"; }
limpiar_tmp() { local n; n=$(ls -d /tmp/kontrol-test-sqlite-* 2>/dev/null | wc -l); if [ "$n" != "0" ]; then echo "  [tmp] $n directorio(s) kontrol-test-sqlite-* dejados por la mutación: se eliminan"; rm -rf /tmp/kontrol-test-sqlite-*; fi; }

echo "=== GOOD → PASS ==="; purgar; correr GOOD $ACS "$OBJ"; serie_objetivo 5

m() { # $1 id; $2 fichero; $3 cambio; $4 descripción; resto: args pytest para el detector (opcional: SERIE para ×20 objetivo)
  local id=$1 f=$2 cambio=$3 desc=$4; shift 4
  echo "=== $id · $desc ==="; mutar "$f" "$cambio" || { echo "  [MUTATION] mal formada"; restaurar; return; }; purgar
  if [ "${1:-}" = "SERIE" ]; then shift; serie_objetivo 20; fi
  [ $# -gt 0 ] && correr MUTATED "$@"
  limpiar_tmp; restaurar; correr RESTORED $ACS "$OBJ"
}
CF=tests/conftest.py; WS=tests/test_warehouse_structure.py; MH=tests/test_motor_para_hilos.py
m M-01 $CF $'    if os.environ.get("KONTROL_TEST_DB_URL"):\n        yield make_engine()\n        return\n=====\n    if True:\n        yield make_engine()\n        return' "la primitiva devuelve make_engine() también en SQLite (StaticPool :memory:)" $ACS
m M-02 $CF $'        f"sqlite+pysqlite:///{os.path.join(directorio, \'base.db\')}",\n=====\n        "sqlite+pysqlite:///:memory:",' ":memory: con el pool por defecto (un :memory: privado por conexión)" $ACS
m M-03 $CF $'        connect_args={"check_same_thread": False},\n    )\n=====\n        connect_args={"check_same_thread": False},\n        poolclass=__import__("sqlalchemy.pool", fromlist=["StaticPool"]).StaticPool,\n    )' "StaticPool sobre el fichero" $ACS
m M-04 $CF $'        connect_args={"check_same_thread": False},\n    )\n=====\n    )' "sin check_same_thread=False" SERIE $ACS
m M-05 $CF $'        motor.dispose()\n        shutil.rmtree(directorio)\n=====\n        motor.dispose()' "sin rmtree al salir" $ACS
m M-06 $CF $'        motor.dispose()\n        shutil.rmtree(directorio)\n=====\n        shutil.rmtree(directorio)' "sin dispose al salir" $ACS
m M-07 $CF $'        connect_args={"check_same_thread": False},\n=====\n        connect_args={"check_same_thread": False, "timeout": 60},' "busy timeout inflado a 60 s" $ACS
m M-08 $WS $'    with motor_para_hilos("warehouse-structure") as engine:\n=====\n    with __import__("contextlib").nullcontext(__import__("tests.conftest", fromlist=["make_engine"]).make_engine()) as engine:' "el fixture vuelve a make_engine()" SERIE $ACS
m M-09 $CF $'    try:\n        yield motor\n    finally:\n        motor.dispose()\n        shutil.rmtree(directorio)\n=====\n    yield motor\n    motor.dispose()\n    shutil.rmtree(directorio)' "limpieza fuera del finally (no limpia si falla)" $ACS
m M-10 $MH $'            leido.wait()\n            sesion.rollback()\n            deshecho.wait()\n=====\n            leido.wait()\n            sesion.commit()\n            deshecho.wait()' "ACS-03: rollback → commit (prueba vacía)" $ACS
m M-11 $MH $'        if sentencia.lstrip().upper().startswith("INSERT INTO") and threading.current_thread() is not threading.main_thread():\n            barrera.wait()  # instrumentación: los dos INSERT se ejecutan a la vez\n=====\n        return' "ACS-04 sin barrera (los INSERT ya no coinciden)" $ACS
m M-12 $WS $'    assert sorted(results) == [200, 409], results\n=====\n    assert sorted(results) == [200, 409] or len(results) == 1, results' "aserción de la prueba objetivo debilitada" $ACS "$OBJ"
echo "=== FIN · tmp restantes: $(ls -d /tmp/kontrol-test-sqlite-* 2>/dev/null | wc -l) · git status de tests: ==="; git status --short tests/
