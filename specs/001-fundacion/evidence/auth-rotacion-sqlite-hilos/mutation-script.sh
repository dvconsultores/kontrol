#!/bin/bash
# Campaña de mutaciones M-01…M-14 (guion de Claude, fuera del repositorio). Copias GOOD en $G; restauración desde la copia.
set -u
cd <repo>/resources/backend; export PYTHONDONTWRITEBYTECODE=1
G=<tmp>/ar/good
PY=.venv/bin/python; SA=tests/test_auth_rotacion_atomica.py; ROT=tests/test_auth_session_rotation.py; SRV=app/modules/identity_access/service.py
OBJ="$ROT::test_dos_renovaciones_simultaneas_no_pueden_ganar_las_dos"
purgar() { find tests app -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null; }
correr() { local et="$1"; shift; local salida; salida=$($PY -m pytest "$@" -q -o addopts="" -p no:cacheprovider 2>&1); echo "  [$et] $(echo "$salida" | tail -n 1)"; echo "$salida" | grep -E "^FAILED" | sed -E 's/ - .*//; s/^/      /'; }
serie() { local n=$1 f=0; for i in $(seq 1 $n); do $PY -m pytest "$OBJ" -q -o addopts="" -p no:cacheprovider 2>&1 | tail -n 1 | grep -q "1 passed" || f=$((f+1)); done; echo "  [objetivo x$n] fallos=$f"; }
mutar() { $PY - "$1" "$2" <<'PYEOF'
import sys; p, cambio = sys.argv[1], sys.argv[2]; s = open(p).read(); viejo, nuevo = cambio.split("\n=====\n")
assert s.count(viejo) == 1, f"SEARCH no único/no encontrado en {p}: {s.count(viejo)}"; open(p, "w").write(s.replace(viejo, nuevo))
PYEOF
}
restaurar() { cp $G/service.py $SRV; cp $G/test_auth_session_rotation.py $ROT; cp $G/test_auth_rotacion_atomica.py $SA; purgar; cmp -s $G/service.py $SRV && cmp -s $G/test_auth_session_rotation.py $ROT && cmp -s $G/test_auth_rotacion_atomica.py $SA && echo "  [RESTORED] copias idénticas" || echo "  [RESTORED] ¡DIFIEREN!"; }
echo "=== GOOD → PASS ==="; purgar; correr GOOD $SA $ROT; serie 5
m() { local id=$1 f=$2 cambio=$3 desc=$4; shift 4; echo "=== $id · $desc ==="; mutar "$f" "$cambio" || { echo "  [MUTATION] mal formada"; restaurar; return; }; purgar
  if [ "${1:-}" = "SERIE" ]; then shift; serie 20; fi; [ $# -gt 0 ] && correr MUTATED "$@"; rm -rf /tmp/kontrol-test-sqlite-* 2>/dev/null; restaurar; correr RESTORED $SA $ROT; }
m M-01 $SRV $'        .where(AuthSession.id == session.id, AuthSession.revoked_at.is_(None))\n=====\n        .where(AuthSession.id == session.id)' "sin «revoked_at IS NULL»" SERIE $SA
m M-02 $SRV $'    if revocadas == 0:\n        raise KontrolError(code="SESSION_REVOKED", message="Sesión revocada", status_code=401)\n    if revocadas != 1:\n=====\n    if revocadas != 1 and revocadas != 0:' "ignorar rowcount (0 también sigue)" SERIE $SA
m M-03 $SRV $'    if revocadas == 0:\n        raise KontrolError(code="SESSION_REVOKED", message="Sesión revocada", status_code=401)\n=====\n    if revocadas == 0:\n        revocadas = 1' "rowcount 0 tratado como éxito" SERIE $SA
m M-04 $SRV $'    ahora = _now()\n    revocadas = db.execute(\n=====\n    ahora = _now()\n    new_session, new_refresh = create_session(db, user=user, ip=session.ip, user_agent=session.user_agent)\n    revocadas = db.execute(' "crear la sesión de reemplazo antes de ganar" $SA
m M-05 $SRV $'        select(AuthSession).where(AuthSession.id == payload.get("sid")).with_for_update()\n=====\n        select(AuthSession).where(AuthSession.id == payload.get("sid"))' "sin with_for_update()" $SA
m M-06 $SRV $'    if revocadas == 0:\n        raise KontrolError(code="SESSION_REVOKED", message="Sesión revocada", status_code=401)\n=====\n    if revocadas == 0:\n        return session, refresh_token, user' "rowcount 0 → 200 con el token viejo" $SA
m M-07 $SRV $'        raise KontrolError(code="SESSION_REVOKED", message="Sesión revocada", status_code=401)\n    if revocadas != 1:\n=====\n        raise KontrolError(code="SESSION_INVALID", message="Sesión revocada", status_code=409)\n    if revocadas != 1:' "rowcount 0 → código/status equivocados" $SA
m M-08 $ROT $'    with motor_para_hilos("auth-session-rotation") as engine:\n=====\n    with __import__("contextlib").nullcontext(__import__("tests.conftest", fromlist=["make_engine"]).make_engine()) as engine:' "el fixture vuelve a make_engine()" SERIE $SA
m M-09 $ROT $'    assert resultados.count(200) == 1, f"dos renovaciones prosperaron: {resultados}"\n=====\n    assert resultados.count(200) >= 1, f"dos renovaciones prosperaron: {resultados}"' "«exactamente un ganador» → «al menos uno»" $SA
m M-10 $ROT $'    assert resultados.count(200) == 1, f"dos renovaciones prosperaron: {resultados}"\n    assert 401 in resultados\n=====\n    assert sorted(resultados) in ([200, 401], [200, 200]), resultados' "aceptar [200, 200]" $SA
m M-11 $SA $'        except Exception as exc:  # noqa: BLE001 — se mide exactamente qué mata al hilo\n            errores.append(f"{type(exc).__name__}: {exc}"[:200])\n=====\n        except Exception:  # noqa: BLE001\n            pass' "ocultar la excepción del hilo" "$SA::test_sa_01_02_dos_lecturas_antes_de_la_primera_escritura_dan_un_200_y_un_401_y_una_sola_sesion_nueva" "$SA::test_sa_16_contrato_estatico_de_la_rotacion_y_de_la_prueba_objetivo"
m M-12 $SRV $'    ahora = _now()\n    revocadas = db.execute(\n        update(AuthSession)\n        .where(AuthSession.id == session.id, AuthSession.revoked_at.is_(None))\n        .values(revoked_at=ahora, updated_at=ahora)\n    ).rowcount\n=====\n    ahora = _now()\n    try:\n        revocadas = db.execute(\n            update(AuthSession)\n            .where(AuthSession.id == session.id, AuthSession.revoked_at.is_(None))\n            .values(revoked_at=ahora, updated_at=ahora)\n        ).rowcount\n    except __import__("sqlalchemy.exc", fromlist=["OperationalError"]).OperationalError:\n        raise KontrolError(code="SESSION_REVOKED", message="Sesión revocada", status_code=401) from None' "OperationalError → SESSION_REVOKED" $SA
m M-13 $SRV $'    if revocadas == 0:\n        raise KontrolError(\n=====\n    if revocadas == 0:\n        import time\n        time.sleep(0.01)\n        raise KontrolError(' "sleep antes del 401" $SA
m M-14 $SRV $'    ahora = _now()\n=====\n    ahora = datetime.now()' "reloj local sin zona en vez del canónico" $SA
echo "=== FIN · tmp restantes: $(ls -d /tmp/kontrol-test-sqlite-* 2>/dev/null | wc -l) ==="; git status --short
