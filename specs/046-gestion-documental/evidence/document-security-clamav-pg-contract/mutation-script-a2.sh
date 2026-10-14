#!/bin/bash
set -u; cd <repo>/resources/backend; export PYTHONDONTWRITEBYTECODE=1
G=<tmp>/clam/good
PY=.venv/bin/python; QA=../../qa/clamav_qa.py; RUN=../../qa/e2e_corrida.py; T=tests/test_clamav_qa.py; DOC=tests/test_documents.py
purgar() { find tests app ../../qa -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null; }
correr() { local et="$1"; shift; local salida; salida=$($PY -m pytest "$@" -q -o addopts="" -p no:cacheprovider 2>&1); echo "  [$et] $(echo "$salida" | tail -n 1)"; echo "$salida" | grep -E "^FAILED" | sed -E 's/ - .*//; s/^/      /'; }
mutar() { $PY - "$1" "$2" <<'PYEOF'
import sys; p, cambio = sys.argv[1], sys.argv[2]; s = open(p).read(); viejo, nuevo = cambio.split("\n=====\n")
assert s.count(viejo) == 1, f"SEARCH no único/no encontrado en {p}: {s.count(viejo)}"; open(p, "w").write(s.replace(viejo, nuevo))
PYEOF
}
restaurar() { cp $G/clamav_qa.py $QA; cp $G/e2e_corrida.py $RUN; cp $G/test_clamav_qa.py $T; cp $G/test_documents.py $DOC; purgar; cmp -s $G/clamav_qa.py $QA && cmp -s $G/e2e_corrida.py $RUN && cmp -s $G/test_clamav_qa.py $T && cmp -s $G/test_documents.py $DOC && echo "  [RESTORED] copias idénticas" || echo "  [RESTORED] ¡DIFIEREN!"; }
echo "=== GOOD → PASS (con analizador real: KONTROL_CLAMSCAN_PATH=${KONTROL_CLAMSCAN_PATH:-<no>}) ==="; purgar; correr GOOD $T "$DOC::test_archivo_infectado_se_rechaza_y_no_se_almacena"
m() { local id=$1 f=$2 cambio=$3 desc=$4; shift 4; echo "=== $id · $desc ==="; mutar "$f" "$cambio" || { echo "  [MUTATION] mal formada"; restaurar; return; }; purgar; correr MUTATED "$@"; restaurar; correr RESTORED $T; }
m M-01 $QA $'        codigo, salida = _escanear(rutas, limpio, rutas.db)\n        if codigo != 0 or not salida.endswith("OK"):\n            raise AnalizadorNoListo(f"QAC-03/04: el PDF limpio no se analiza como CLEAN (rc {codigo}: {salida[-120:]})")\n        codigo, salida = _escanear(rutas, eicar, rutas.db)\n        if codigo != 1 or "FOUND" not in salida:\n            raise AnalizadorNoListo(f"QAC-05: EICAR no se detecta como INFECTED (rc {codigo}: {salida[-120:]})")\n=====\n        codigo, salida = 0, "OK"' "el preflight solo comprueba que el ejecutable existe (sin escanear)" $T
m M-02 $QA $'        codigo, salida = _escanear(rutas, eicar, rutas.db)\n        if codigo != 1 or "FOUND" not in salida:\n            raise AnalizadorNoListo(f"QAC-05: EICAR no se detecta como INFECTED (rc {codigo}: {salida[-120:]})")\n=====\n        pass' "quitar la verificación de EICAR" $T
m M-03 $QA $'    if len(bases) < len(BASES):\n        raise AnalizadorNoListo(f"QAC-03: faltan firmas en {rutas.db} ({sorted(set(BASES) - set(bases))}); ejecute «provisionar»")\n=====\n    pass' "aceptar que falten firmas" $T
m M-04 $RUN $'        try:\n            estado = clamav_qa.asegurar()\n        except clamav_qa.AnalizadorNoListo as exc:\n            raise base.CicloDeBaseRoto(f"analizador exigido y no listo: {exc}") from exc\n=====\n        try:\n            estado = clamav_qa.asegurar()\n        except clamav_qa.AnalizadorNoListo:\n            self.entorno["KONTROL_E2E_SCANNER_AVAILABLE"] = "true"\n            return {"exigido": True, "motor": "?", "bases": {}}' "marcar el analizador disponible sin preflight" $T
m M-05 $QA $'    return {"KONTROL_CLAMSCAN_PATH": estado.clamscan, "KONTROL_CLAMAV_DB": estado.db}\n=====\n    return {"KONTROL_CLAMSCAN_PATH": estado.clamscan}' "no exportar KONTROL_CLAMAV_DB" $T
m M-06 $QA $'    return {"KONTROL_CLAMSCAN_PATH": estado.clamscan, "KONTROL_CLAMAV_DB": estado.db}\n=====\n    return {"KONTROL_CLAMAV_DB": estado.db}' "no exportar KONTROL_CLAMSCAN_PATH" $T
m M-07 $QA $'    resultado = _correr(["apt-get", "download", *PAQUETES], cwd=destino)\n=====\n    resultado = _correr(["sudo", "apt-get", "install", "-y", *PAQUETES], cwd=destino)' "instalar con sudo" $T
m M-08 $QA $'        codigo, _salida = _escanear(rutas, limpio, vacia)\n        if codigo in (0, 1):\n            raise AnalizadorNoListo(f"QAC-06: sin firmas el analizador respondió rc {codigo} en vez de error")\n=====\n        pass' "no distinguir el error de proceso de CLEAN (QAC-06)" $T
m M-09 $QA $'    if motor_disponible(rutas) is None:\n        extraer(descargar(rutas.deb), rutas.prefijo)\n=====\n    if True:\n        extraer(descargar(rutas.deb), rutas.prefijo)' "sin idempotencia: descarga siempre" $T
m M-10 $QA $'    cache = Path(entorno.get("XDG_CACHE_HOME") or Path.home() / ".cache")\n    return cache / "kontrol-qa" / "clamav" / VERSION_COMPATIBLE.rstrip(".")\n=====\n    return Path(__file__).resolve().parent / "clamav-cache"' "prefijo dentro del repositorio (firmas rastreables)" $T
m M-11 $RUN $'        certificado = self.exigir_analizador() if self.con_analizador else {"exigido": False}\n=====\n        certificado = {"exigido": False}' "el modo canónico vuelve a omitir si falta el analizador" $T
m M-12 $QA $'    if codigo != 1 or "FOUND" not in salida:\n=====\n    if codigo not in (0, 1) or "FOUND" not in salida and codigo != 0:' "EICAR aceptado también como limpio (rc 0)" $T
m M-13 $DOC $'    assert r.json()["code"] == "FILE_INFECTED"\n=====\n    assert r.json()["code"] in ("FILE_INFECTED", "SCAN_FAILED", "CLEAN")' "debilitar el rechazo de EICAR en la prueba documental" $T
m M-14 $QA $'    motor = motor_disponible(rutas)\n    if motor is None:\n        raise AnalizadorNoListo("QAC-01/02: clamscan no arranca desde el prefijo o no es 1.4.x; ejecute «provisionar»")\n=====\n    motor = motor_disponible(rutas) or "1.4.3"' "aceptar un motor que no arranca" $T
echo "=== FIN ==="; git -C <repo> status --short
