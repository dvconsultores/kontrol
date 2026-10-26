"""Prueba de límite de conexión para la carga documental.

Demuestra que, tras el cambio de producto, una carga documental no retiene
conexión de base durante el análisis y que todos los contratos se conservan.

La prueba debe FALLAR contra el producto anterior y PASAR con el nuevo.
"""

from __future__ import annotations

import ast
import io
import os
import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sesion_mfa import login_completo
from sqlalchemy import event, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

import app.core.database as dm
import app.modules.documents.scanning as scanning
from app.core.database import Base, get_db, init_models
from app.main import create_app
from app.modules.audit.models import AuditEvent
from app.modules.documents.models import DocumentVersion
from app.modules.documents.storage import FilesystemStorageProvider, set_storage
from app.modules.setup.api import SetupRequest, initialize
from tests.conftest import make_engine, motor_para_hilos

_PASSWORD = "Kontrol2026Segura!"
_CLIENT: TestClient | None = None
_FACTORY: sessionmaker | None = None
_ROOT: Path | None = None

_EVENTOS: list[tuple[str, str]] = []
_EVENTOS_LOCK = threading.Lock()


def _registrar(evento: str, detalle: str) -> None:
    with _EVENTOS_LOCK:
        _EVENTOS.append((evento, detalle))


def _montar(engine: Engine) -> None:
    global _CLIENT, _FACTORY, _ROOT

    assert isinstance(engine.pool, QueuePool)
    assert engine.pool.size() == 5
    assert engine.pool._max_overflow == 10
    assert engine.pool._timeout == 30

    def _checkout(dbapi_connection, connection_record, connection_proxy) -> None:
        _registrar("checkout", str(engine.pool.checkedout()))

    def _checkin(dbapi_connection, connection_record) -> None:
        _registrar("checkin", str(engine.pool.checkedout()))

    def _begin(conn) -> None:
        _registrar("begin", "")

    def _commit(conn) -> None:
        _registrar("commit", "")

    def _rollback(conn) -> None:
        _registrar("rollback", "")

    def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany) -> None:
        verbo = statement.strip().split(" ", 1)[0].upper()
        if verbo not in {"SELECT", "INSERT", "UPDATE", "DELETE"}:
            verbo = "OTRO"
        _registrar("before_cursor_execute", verbo)

    event.listen(engine, "checkout", _checkout)
    event.listen(engine, "checkin", _checkin)
    event.listen(engine, "begin", _begin)
    event.listen(engine, "commit", _commit)
    event.listen(engine, "rollback", _rollback)
    event.listen(engine, "before_cursor_execute", _before_cursor_execute)

    init_models()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False, autoflush=False)
    dm._engine = engine
    dm._SessionLocal = factory

    set_storage(FilesystemStorageProvider(_ROOT))

    db = factory()
    try:
        initialize(
            db,
            SetupRequest(
                tenant_code="DEMO",
                tenant_name="Empresa Demo",
                company_code="D1",
                company_legal_name="Demo C.A.",
                company_rif="J-12345678-9",
                admin_username="admin",
                admin_password=_PASSWORD,
            ),
        )
        db.commit()
    finally:
        db.close()

    app = create_app()

    def _override_get_db():
        d = factory()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = _override_get_db
    _FACTORY = factory
    _CLIENT = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module", autouse=True)
def _mundo(tmp_path_factory) -> Iterator[None]:
    global _CLIENT, _FACTORY, _ROOT, _EVENTOS

    _EVENTOS.clear()
    _ROOT = tmp_path_factory.mktemp("kontrol-doc-boundary")

    if os.environ.get("KONTROL_TEST_DB_URL"):
        engine = make_engine(pool_pre_ping=True, pool_recycle=1800)
        try:
            _montar(engine)
            yield
        finally:
            engine.dispose()
    else:
        with motor_para_hilos("doc-upload-boundary") as engine:
            _montar(engine)
            yield

    scanning.set_scanner(None)
    set_storage(None)
    _CLIENT = None
    _FACTORY = None
    _ROOT = None


def _headers() -> dict:
    assert _CLIENT is not None
    r = login_completo(
        _CLIENT,
        "/api/v1/auth/login",
        json={"tenant_code": "DEMO", "username": "admin", "password": _PASSWORD},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _company_id() -> str:
    assert _CLIENT is not None
    return _CLIENT.get("/api/v1/organization/companies", headers=_headers()).json()["items"][0]["id"]


_N = {"i": 0}


def _doc_type(code: str | None = None, **overrides) -> dict:
    _N["i"] += 1
    assert _CLIENT is not None
    body = {
        "company_id": _company_id(),
        "code": code or f"TIPO{_N['i']}",
        "name": "Tipo de prueba",
        "allowed_mime_types": ["application/pdf"],
        "scan_required": True,
        **overrides,
    }
    r = _CLIENT.post("/api/v1/documentos/tipos", headers=_headers(), json=body)
    assert r.status_code == 200, r.text
    return r.json()


def _document(type_id: str, **overrides) -> dict:
    _N["i"] += 1
    assert _CLIENT is not None
    body = {
        "company_id": _company_id(),
        "document_type_id": type_id,
        "title": f"Documento {_N['i']}",
        **overrides,
    }
    r = _CLIENT.post("/api/v1/documentos", headers=_headers(), json=body)
    assert r.status_code == 200, r.text
    return r.json()


def _upload(
    document_id: str,
    content: bytes,
    headers: dict,
    name: str = "archivo.pdf",
    mime: str = "application/pdf",
    extra_headers: dict | None = None,
    **kwargs,
):
    assert _CLIENT is not None
    return _CLIENT.post(
        f"/api/v1/documentos/{document_id}/versiones",
        headers={**headers, **(extra_headers or {})},
        files={"file": (name, io.BytesIO(content), mime)},
        **kwargs,
    )


class _Controlado(scanning.FileSecurityScanner):
    name = "CONTROLADO"

    def __init__(self) -> None:
        self.entro = threading.Event()
        self.soltar = threading.Event()
        self.resultado = scanning.CLEAN
        self.llamadas = 0

    def available(self) -> bool:
        return True

    def scan(self, path: str) -> scanning.ScanResult:
        self.llamadas += 1
        engine = dm._engine
        assert engine is not None
        with _EVENTOS_LOCK:
            _EVENTOS.append(("scan_start", str(engine.pool.checkedout())))
        self.entro.set()
        assert self.soltar.wait(timeout=60)
        with _EVENTOS_LOCK:
            _EVENTOS.append(("scan_end", str(engine.pool.checkedout())))
        return scanning.ScanResult(result=self.resultado, scanner="CONTROLADO")


class _RealEnvoltorio(scanning.FileSecurityScanner):
    name = "REAL_ENVOLTORIO"

    def __init__(self) -> None:
        self._interno = scanning.ClamAVScanner()

    def available(self) -> bool:
        return self._interno.available()

    def scan(self, path: str) -> scanning.ScanResult:
        engine = dm._engine
        assert engine is not None
        with _EVENTOS_LOCK:
            _EVENTOS.append(("scan_real_start", str(engine.pool.checkedout())))
        resultado = self._interno.scan(path)
        with _EVENTOS_LOCK:
            _EVENTOS.append(("scan_real_end", str(engine.pool.checkedout())))
        return resultado


def _marcar_inicio() -> int:
    with _EVENTOS_LOCK:
        return len(_EVENTOS)


def _eventos_desde(inicio: int) -> list[tuple[str, str]]:
    with _EVENTOS_LOCK:
        return list(_EVENTOS[inicio:])


def _indice_evento(eventos: list[tuple[str, str]], nombre: str, desde: int = 0) -> int:
    for i in range(desde, len(eventos)):
        if eventos[i][0] == nombre:
            return i
    return -1


def _contar_versiones_db(document_id: str) -> int:
    assert _FACTORY is not None
    db = _FACTORY()
    try:
        total = db.scalar(
            select(func.count())
            .select_from(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
        )
        return int(total or 0)
    finally:
        db.close()


def _contar_ficheros(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(1 for p in root.rglob("*") if p.is_file())


def test_b01_no_retiene_conexion_durante_analisis() -> None:
    assert _CLIENT is not None
    assert _FACTORY is not None
    assert _ROOT is not None

    engine = dm._engine
    assert engine is not None

    tipo = _doc_type(scan_required=True, allowed_mime_types=["application/pdf"])
    documento = _document(tipo["id"])
    h = _headers()
    inicio = _marcar_inicio()

    analizador = _Controlado()
    analizador.resultado = scanning.CLEAN
    scanning.set_scanner(analizador)
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            fut = executor.submit(_upload, documento["id"], b"%PDF-1.4 contenido", h)
            assert analizador.entro.wait(timeout=60)
            eventos_hasta_scan = _eventos_desde(inicio)
            assert engine.pool.checkedout() == 0

            idx_scan_start = _indice_evento(eventos_hasta_scan, "scan_start")
            assert idx_scan_start > 0

            ultimo_commit = -1
            for i in range(idx_scan_start - 1, -1, -1):
                if eventos_hasta_scan[i][0] == "commit":
                    ultimo_commit = i
                    break
            assert ultimo_commit >= 0

            segmento = eventos_hasta_scan[ultimo_commit + 1 : idx_scan_start]
            assert all(ev[0] != "checkout" for ev in segmento)

            analizador.soltar.set()
            respuesta = fut.result(timeout=60)

        assert respuesta.status_code == 200, respuesta.text
        assert _contar_versiones_db(documento["id"]) == 1

        db = _FACTORY()
        try:
            audit = db.query(AuditEvent).filter_by(
                action="DOCUMENT_FILE_UPLOADED", entity_id=documento["id"]
            ).all()
            assert len(audit) == 1
        finally:
            db.close()

        eventos_finales = _eventos_desde(inicio)
        checkout = sum(1 for ev in eventos_finales if ev[0] == "checkout")
        checkin = sum(1 for ev in eventos_finales if ev[0] == "checkin")
        assert checkout == checkin
        assert engine.pool.checkedout() == 0
    finally:
        scanning.set_scanner(None)


def test_b02_solo_lecturas_antes_del_analisis() -> None:
    assert _CLIENT is not None
    assert _FACTORY is not None
    assert _ROOT is not None

    engine = dm._engine
    assert engine is not None

    tipo = _doc_type(scan_required=True, allowed_mime_types=["application/pdf"])
    documento = _document(tipo["id"])
    h = _headers()
    inicio = _marcar_inicio()

    analizador = _Controlado()
    analizador.resultado = scanning.CLEAN
    scanning.set_scanner(analizador)
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            fut = executor.submit(_upload, documento["id"], b"%PDF-1.4 contenido", h)
            assert analizador.entro.wait(timeout=60)

            eventos = _eventos_desde(inicio)
            idx_scan_start = _indice_evento(eventos, "scan_start")
            assert idx_scan_start > 0
            verbos_previos = [
                ev[1] for ev in eventos[:idx_scan_start]
                if ev[0] == "before_cursor_execute"
            ]
            assert "INSERT" not in verbos_previos
            assert "UPDATE" not in verbos_previos
            assert "DELETE" not in verbos_previos

            analizador.soltar.set()
            fut.result(timeout=60)
    finally:
        scanning.set_scanner(None)


def test_b03_escrituras_atomicas_despues_del_analisis() -> None:
    assert _CLIENT is not None
    assert _FACTORY is not None
    assert _ROOT is not None

    engine = dm._engine
    assert engine is not None

    tipo = _doc_type(scan_required=True, allowed_mime_types=["application/pdf"])
    documento = _document(tipo["id"])
    h = _headers()
    inicio = _marcar_inicio()

    analizador = _Controlado()
    analizador.resultado = scanning.CLEAN
    scanning.set_scanner(analizador)
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            fut = executor.submit(_upload, documento["id"], b"%PDF-1.4 contenido", h)
            assert analizador.entro.wait(timeout=60)
            analizador.soltar.set()
            fut.result(timeout=60)

        eventos = _eventos_desde(inicio)
        idx_scan_end = _indice_evento(eventos, "scan_end")
        assert idx_scan_end > 0

        posteriores = eventos[idx_scan_end + 1 :]
        escrituras = [
            i
            for i, ev in enumerate(posteriores)
            if ev[0] == "before_cursor_execute" and ev[1] in {"INSERT", "UPDATE", "DELETE"}
        ]
        assert escrituras, "se esperaban escrituras después del análisis"

        commits_posteriores = [i for i, ev in enumerate(posteriores) if ev[0] == "commit"]
        assert len(commits_posteriores) == 1
        commit_idx = commits_posteriores[0]
        assert all(i < commit_idx for i in escrituras)

        primera_escritura = min(escrituras)
        begins_previos = [i for i, ev in enumerate(posteriores) if ev[0] == "begin" and i < primera_escritura]
        assert begins_previos, "se esperaba un begin antes de las escrituras posteriores al análisis"
        begin_idx = begins_previos[-1]
        assert not any(ev[0] == "commit" for ev in posteriores[begin_idx:primera_escritura])
        assert begin_idx < commit_idx
    finally:
        scanning.set_scanner(None)


def test_b04_analizador_real_no_retiene_conexion() -> None:
    assert _CLIENT is not None
    assert _FACTORY is not None
    assert _ROOT is not None

    engine = dm._engine
    assert engine is not None

    tipo = _doc_type(scan_required=True, allowed_mime_types=["application/pdf"])
    documento = _document(tipo["id"])
    h = _headers()
    inicio = _marcar_inicio()

    envoltorio = _RealEnvoltorio()
    scanning.set_scanner(envoltorio)
    try:
        respuesta = _upload(documento["id"], b"%PDF-1.4 contenido", h)
        assert respuesta.status_code == 200, respuesta.text
        assert _contar_versiones_db(documento["id"]) == 1

        eventos = _eventos_desde(inicio)
        real_start = [ev for ev in eventos if ev[0] == "scan_real_start"]
        real_end = [ev for ev in eventos if ev[0] == "scan_real_end"]
        assert real_start and real_end
        assert all(ev[1] == "0" for ev in real_start)
        assert all(ev[1] == "0" for ev in real_end)
    finally:
        scanning.set_scanner(None)


def test_b05_infectado_sin_persistencia() -> None:
    assert _CLIENT is not None
    assert _FACTORY is not None
    assert _ROOT is not None

    tipo = _doc_type(scan_required=True, allowed_mime_types=["application/pdf"])
    documento = _document(tipo["id"])
    h = _headers()
    antes = _contar_ficheros(_ROOT)

    analizador = _Controlado()
    analizador.resultado = scanning.INFECTED
    scanning.set_scanner(analizador)
    analizador.soltar.set()
    try:
        respuesta = _upload(documento["id"], b"%PDF-1.4 contenido", h)
        assert respuesta.status_code == 422, respuesta.text
        assert respuesta.json()["code"] == "FILE_INFECTED"
        assert _contar_versiones_db(documento["id"]) == 0
        assert _contar_ficheros(_ROOT) == antes
    finally:
        scanning.set_scanner(None)


def test_b06_scan_failed_sin_persistencia() -> None:
    assert _CLIENT is not None
    assert _FACTORY is not None
    assert _ROOT is not None

    tipo = _doc_type(scan_required=True, allowed_mime_types=["application/pdf"])
    documento = _document(tipo["id"])
    h = _headers()
    antes = _contar_ficheros(_ROOT)

    analizador = _Controlado()
    analizador.resultado = scanning.SCAN_FAILED
    scanning.set_scanner(analizador)
    analizador.soltar.set()
    try:
        respuesta = _upload(documento["id"], b"%PDF-1.4 contenido", h)
        assert respuesta.status_code == 422, respuesta.text
        assert respuesta.json()["code"] == "SCAN_FAILED"
        assert _contar_versiones_db(documento["id"]) == 0
        assert _contar_ficheros(_ROOT) == antes
    finally:
        scanning.set_scanner(None)


def test_b07_idempotencia_llama_una_sola_vez() -> None:
    assert _CLIENT is not None
    assert _FACTORY is not None
    assert _ROOT is not None

    tipo = _doc_type(scan_required=True, allowed_mime_types=["application/pdf"])
    documento = _document(tipo["id"])
    h = _headers()

    analizador = _Controlado()
    analizador.resultado = scanning.CLEAN
    scanning.set_scanner(analizador)
    try:
        clave = "clave-idempotente-1"
        with ThreadPoolExecutor(max_workers=1) as executor:
            fut1 = executor.submit(
                _upload,
                documento["id"],
                b"%PDF-1.4 contenido",
                h,
                "archivo.pdf",
                "application/pdf",
                {"Idempotency-Key": clave},
            )
            assert analizador.entro.wait(timeout=60)
            analizador.soltar.set()
            respuesta1 = fut1.result(timeout=60)

        respuesta2 = _upload(
            documento["id"],
            b"%PDF-1.4 contenido",
            h,
            "archivo.pdf",
            "application/pdf",
            {"Idempotency-Key": clave},
        )

        assert respuesta1.status_code == 200, respuesta1.text
        assert respuesta2.status_code == 200, respuesta2.text
        assert respuesta2.json().get("idempotent_hit") is True
        assert respuesta1.json()["id"] == respuesta2.json()["id"]
        assert analizador.llamadas == 1
        assert _contar_versiones_db(documento["id"]) == 1
    finally:
        scanning.set_scanner(None)


def test_b08_escritura_pendiente_rechaza_todo(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _CLIENT is not None
    assert _FACTORY is not None
    assert _ROOT is not None

    tipo = _doc_type(scan_required=True, allowed_mime_types=["application/pdf"])
    documento = _document(tipo["id"])
    h = _headers()
    antes = _contar_ficheros(_ROOT)

    import app.modules.documents.api as documents_api

    original = documents_api._get_type

    def _get_type_con_escritura(db, ctx, doc_type_id):
        resultado = original(db, ctx, doc_type_id)
        db.add(
            AuditEvent(
                action="PRUEBA_ESCRITURA_PENDIENTE",
                entity_type="DOCUMENT_TYPE",
                entity_id=str(doc_type_id),
                event_time=datetime.now(UTC),
            )
        )
        return resultado

    monkeypatch.setattr(documents_api, "_get_type", _get_type_con_escritura)

    analizador = _Controlado()
    analizador.resultado = scanning.CLEAN
    scanning.set_scanner(analizador)
    analizador.soltar.set()
    try:
        respuesta = _upload(documento["id"], b"%PDF-1.4 contenido", h)
        assert respuesta.status_code == 500, respuesta.text
        assert respuesta.json()["code"] == "INTERNAL_ERROR"
        assert analizador.llamadas == 0

        db = _FACTORY()
        try:
            audit = db.query(AuditEvent).filter_by(
                action="PRUEBA_ESCRITURA_PENDIENTE"
            ).all()
            assert len(audit) == 0
        finally:
            db.close()

        assert _contar_versiones_db(documento["id"]) == 0
        assert _contar_ficheros(_ROOT) == antes
    finally:
        scanning.set_scanner(None)


def test_b09_contrato_ast_commit_antes_del_analisis() -> None:
    ruta = Path(__file__).resolve().parents[1] / "app" / "modules" / "documents" / "api.py"
    assert ruta.exists(), f"No existe {ruta}"
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))

    funcion = None
    for nodo in arbol.body:
        if isinstance(nodo, ast.FunctionDef) and nodo.name == "upload_version":
            funcion = nodo
            break
    assert funcion is not None, "No existe la función upload_version"

    sentencias = funcion.body
    idx_doc_type = None
    idx_idempotencia = None
    for i, sentencia in enumerate(sentencias):
        if isinstance(sentencia, ast.Assign):
            for objetivo in sentencia.targets:
                if isinstance(objetivo, ast.Name) and objetivo.id == "doc_type":
                    idx_doc_type = i
        if isinstance(sentencia, ast.If):
            test = sentencia.test
            if isinstance(test, ast.Name) and test.id == "idempotency_key":
                if idx_idempotencia is None:
                    idx_idempotencia = i

    assert idx_doc_type is not None
    assert idx_idempotencia is not None
    assert idx_doc_type < idx_idempotencia

    idx_if_guard = None
    idx_commit = None
    idx_try = None
    for i, sentencia in enumerate(sentencias):
        if isinstance(sentencia, ast.If):
            test = sentencia.test
            if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.Or):
                nombres = {
                    valor.attr
                    for valor in test.values
                    if isinstance(valor, ast.Attribute)
                    and isinstance(valor.value, ast.Name)
                    and valor.value.id == "db"
                }
                if nombres == {"new", "dirty", "deleted"}:
                    idx_if_guard = i
                    assert len(sentencia.body) == 1
                    assert isinstance(sentencia.body[0], ast.Raise)
                    assert isinstance(sentencia.body[0].exc, ast.Call)
                    assert getattr(sentencia.body[0].exc.func, "id", None) == "RuntimeError"
        if isinstance(sentencia, ast.Expr):
            if (
                isinstance(sentencia.value, ast.Call)
                and isinstance(sentencia.value.func, ast.Attribute)
                and sentencia.value.func.attr == "commit"
                and isinstance(sentencia.value.func.value, ast.Name)
                and sentencia.value.func.value.id == "db"
            ):
                if idx_commit is None:
                    idx_commit = i
        if isinstance(sentencia, ast.Try):
            if idx_try is None:
                idx_try = i

    assert idx_if_guard is not None, "No existe el If con la disyunción db.new/db.dirty/db.deleted"
    assert idx_commit is not None, "No existe db.commit()"
    assert idx_try is not None, "No existe el Try de service.upload_version"

    assert idx_idempotencia < idx_if_guard
    assert idx_commit == idx_if_guard + 1
    assert idx_commit < idx_try

    assert _try_contiene_upload_version(sentencias[idx_try])


def _try_contiene_upload_version(try_nodo: ast.Try) -> bool:
    for nodo in ast.walk(try_nodo):
        if (
            isinstance(nodo, ast.Call)
            and isinstance(nodo.func, ast.Attribute)
            and nodo.func.attr == "upload_version"
            and isinstance(nodo.func.value, ast.Name)
            and nodo.func.value.id == "service"
        ):
            return True
    return False
