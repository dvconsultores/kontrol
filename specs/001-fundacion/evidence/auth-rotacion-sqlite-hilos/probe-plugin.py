"""Sonda de medición (Claude, fuera del repositorio): excepciones no capturadas en hilos, topología de conexiones y
eventos de transacción por hilo, sanitizados (T1/T2, C1/C2). Se activa con -p acs_sonda."""
import os, threading, traceback
from sqlalchemy import event
from sqlalchemy.engine import Engine
SALIDA = os.environ.get("ACS_SONDA_SALIDA", "/dev/stderr")
_hilos: dict[int, str] = {}; _conexiones: dict[int, str] = {}; _lock = threading.Lock()
def _h():
    i = threading.get_ident()
    with _lock:
        if i not in _hilos: _hilos[i] = ("MAIN" if threading.current_thread() is threading.main_thread() else f"T{len(_hilos)}")
        return _hilos[i]
def _c(dbapi):
    with _lock:
        k = id(dbapi)
        if k not in _conexiones: _conexiones[k] = f"C{len(_conexiones)+1}"
        return _conexiones[k]
def _w(linea):
    with open(SALIDA, "a", encoding="utf-8") as fh: fh.write(linea + "\n")
def _excepthook(args):
    _w(f"[EXC] hilo={_h()} tipo={args.exc_type.__name__} msg={str(args.exc_value)[:200]}")
    _w("[EXC-TB] " + " | ".join(l.strip() for l in traceback.format_tb(args.exc_traceback)[-4:])[:900])
threading.excepthook = _excepthook
@event.listens_for(Engine, "checkout")
def _checkout(dbapi, rec, proxy): _w(f"[CHECKOUT] hilo={_h()} conexion={_c(dbapi)}")
@event.listens_for(Engine, "before_cursor_execute")
def _bce(conn, cursor, stmt, params, ctx, many):
    s = " ".join(stmt.split())[:70]
    if s.upper().startswith(("INSERT INTO SESSIONS", "UPDATE SESSIONS", "SELECT SESSIONS", "SAVEPOINT", "RELEASE", "ROLLBACK", "COMMIT", "BEGIN")) or " sessions" in s.lower():
        _w(f"[SQL] hilo={_h()} conexion={_c(conn.connection.dbapi_connection)} {s}")
@event.listens_for(Engine, "commit")
def _commit(conn): _w(f"[COMMIT] hilo={_h()} conexion={_c(conn.connection.dbapi_connection)}")
@event.listens_for(Engine, "rollback")
def _rollback(conn): _w(f"[ROLLBACK] hilo={_h()} conexion={_c(conn.connection.dbapi_connection)}")
@event.listens_for(Engine, "handle_error")
def _err(ctx):
    _w(f"[DBERR] hilo={_h()} tipo={type(ctx.original_exception).__name__} msg={str(ctx.original_exception)[:160]} stmt={' '.join(str(ctx.statement).split())[:60]}")
def pytest_runtest_setup(item):
    if "renovaciones_simultaneas" in item.name: _w(f"===== {item.nodeid.split('::')[-1]} =====")
