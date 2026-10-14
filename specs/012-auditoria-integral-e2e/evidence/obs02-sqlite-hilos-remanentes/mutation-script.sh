#!/bin/bash
set -u; cd <repo>/resources/backend; export PYTHONDONTWRITEBYTECODE=1
G=<tmp>/o2/good
PY=.venv/bin/python; O2=tests/test_uom_concurrencia_hilos.py; UOM=tests/test_uom_conversion.py; CF=tests/conftest.py
OBJ="$UOM::test_concurrencia_una_sola_version_abierta"
purgar() { find tests app -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null; }
correr() { local et="$1"; shift; local salida; salida=$($PY -m pytest "$@" -q -o addopts="" -p no:cacheprovider 2>&1); echo "  [$et] $(echo "$salida" | tail -n 1)"; echo "$salida" | grep -E "^FAILED" | sed -E 's/ - .*//; s/^/      /'; }
mutar() { $PY - "$1" "$2" <<'PYEOF'
import sys; p, cambio = sys.argv[1], sys.argv[2]; s = open(p).read(); viejo, nuevo = cambio.split("\n=====\n")
assert s.count(viejo) == 1, f"SEARCH no único/no encontrado en {p}: {s.count(viejo)}"; open(p, "w").write(s.replace(viejo, nuevo))
PYEOF
}
restaurar() { cp $G/test_uom_conversion.py $UOM; cp $G/test_uom_concurrencia_hilos.py $O2; cp $G/conftest.py $CF; purgar; cmp -s $G/test_uom_conversion.py $UOM && cmp -s $G/test_uom_concurrencia_hilos.py $O2 && cmp -s $G/conftest.py $CF && echo "  [RESTORED] copias idénticas" || echo "  [RESTORED] ¡DIFIEREN!"; }
echo "=== GOOD → PASS ==="; purgar; correr GOOD $O2 "$OBJ"
m() { local id=$1 f=$2 cambio=$3 desc=$4; shift 4; echo "=== $id · $desc ==="; mutar "$f" "$cambio" || { echo "  [MUTATION] mal formada"; restaurar; return; }; purgar; [ $# -gt 0 ] && correr MUTATED "$@"; rm -rf /tmp/kontrol-test-sqlite-* 2>/dev/null; restaurar; correr RESTORED $O2 "$OBJ"; }
m M-11 $O2 $'    def falla() -> None:\n        raise ValueError("fallo sintético del hilo")\n\n    assert _en_hilos(falla, lambda: None) == ["ValueError: fallo sintético del hilo"]\n=====\n    assert _en_hilos(lambda: None, lambda: None) == []' "O2-11 vacía (ya no prueba que la excepción se vea)" $O2
echo "=== FIN · tmp restantes: $(ls -d /tmp/kontrol-test-sqlite-* 2>/dev/null | wc -l) ==="; git status --short tests/
