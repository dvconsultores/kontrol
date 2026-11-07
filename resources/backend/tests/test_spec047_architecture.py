"""Spec 047 · guardas de arquitectura del planificador y de los mensajes.

Buscan estructura en el código real, no nombres ni comentarios.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from app.core.database import Base, init_models

BACKEND = pathlib.Path(__file__).resolve().parents[1]
REPO = BACKEND.parents[1]
MODULOS_047 = sorted([*(BACKEND / "app/modules/scheduler").glob("*.py"),
                      *(BACKEND / "app/modules/notifications").glob("*.py")])
COLAS = {"celery", "redis", "rq", "dramatiq", "kafka", "aiokafka", "pika", "kombu", "apscheduler", "huey", "arq"}
PROCESOS = {"threading", "asyncio", "sched", "multiprocessing", "concurrent"}


def _modulos_importados(arbol: ast.AST) -> set[str]:
    nombres: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            nombres |= {a.name.split(".")[0] for a in nodo.names}
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            nombres.add(nodo.module.split(".")[0])
    return nombres


def test_ninguna_libreria_de_cola_entra_en_el_producto():
    culpables = [str(f.relative_to(BACKEND)) for f in (BACKEND / "app").rglob("*.py")
                 if _modulos_importados(ast.parse(f.read_text())) & COLAS]
    assert culpables == []
    requisitos = (BACKEND / "requirements.txt").read_text().lower().splitlines()
    assert [r for r in requisitos if r.split("=")[0].split("[")[0].strip() in COLAS] == []


def test_la_047_no_contiene_proveedores_externos():
    """El adaptador de correo, push o SMS es de la 048 (FR-047-020)."""
    externos = {"smtplib", "email", "httpx", "requests", "aiohttp", "twilio", "boto3", "firebase_admin"}
    culpables = [f.name for f in MODULOS_047 if _modulos_importados(ast.parse(f.read_text())) & externos]
    assert culpables == []


def test_el_planificador_no_duerme_ni_abre_hilos_ni_bucles():
    culpables = []
    for f in MODULOS_047:
        arbol = ast.parse(f.read_text())
        if _modulos_importados(arbol) & PROCESOS:
            culpables.append(f"{f.name}: importa un mecanismo de proceso")
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute) and nodo.func.attr == "sleep":
                culpables.append(f"{f.name}: duerme")
            if isinstance(nodo, ast.While):
                culpables.append(f"{f.name}: bucle while")
            if isinstance(nodo, ast.Name) and nodo.id == "BackgroundTasks":
                culpables.append(f"{f.name}: BackgroundTasks")
    assert culpables == []


def test_el_temporizador_solo_invoca_la_orden_canonica():
    servicio = (REPO / "scripts/scheduler/kontrol-scheduler.service").read_text()
    temporizador = (REPO / "scripts/scheduler/kontrol-scheduler.timer").read_text()
    instalador = (REPO / "scripts/install-scheduler.sh").read_text()
    assert [linea for linea in servicio.splitlines() if linea.startswith("Exec")] == [
        "ExecStart=/usr/bin/env python3 @KONTROL_DIR@/kontrol.py scheduler-tick"]
    assert "OnUnitActiveSec=@INTERVAL@" in temporizador
    assert "KONTROL_SCHEDULER_INTERVAL:?" in instalador
    assert "KONTROL_INSTANCE:?" in instalador, "un temporizador por instalación: la instancia es obligatoria"
    for texto in (servicio, temporizador, instalador):
        codigo = "\n".join(linea for linea in texto.splitlines() if not linea.lstrip().startswith("#")).upper()
        assert not any(p in codigo for p in ("SELECT ", "INSERT ", "UPDATE ", "DELETE ", "PSQL", "CURL", "WGET"))

    kontrol = ast.parse((REPO / "kontrol.py").read_text())
    orden = next(n for n in kontrol.body if isinstance(n, ast.Assign)
                 and any(getattr(t, "id", None) == "SCHEDULER_TICK" for t in n.targets))
    assert ast.literal_eval(orden.value) == ["python", "-m", "app.modules.scheduler", "tick"]
    funcion = next(n for n in kontrol.body if isinstance(n, ast.FunctionDef) and n.name == "cmd_scheduler_tick")
    lista = next(n for n in ast.walk(funcion) if isinstance(n, ast.List))
    constantes = [e.value for e in lista.elts if isinstance(e, ast.Constant)]
    estrellas = [e.value.id for e in lista.elts if isinstance(e, ast.Starred)]
    assert constantes[:2] == ["docker", "compose"]
    assert ["exec", "-T", "-e", "KONTROL_BACKUP_KEY", "backend"] == constantes[-5:]
    assert estrellas == ["SCHEDULER_TICK"] and len(lista.elts) == 10


def test_la_orden_no_acepta_argumentos_que_elijan_trabajo():
    from app.modules.scheduler.__main__ import main

    with pytest.raises(SystemExit):
        main(["tick", "--handler", "approval_step_expiration"])


def test_el_planificador_cita_su_adr_aprobado():
    for nombre in ("service.py", "__main__.py", "models.py"):
        assert "ADR-D0-015" in (BACKEND / "app/modules/scheduler" / nombre).read_text(), nombre
    adr = (REPO / "docs/governance/d0-foundational-decisions/adr/ADR-D0-015-platform-scheduler.md").read_text()
    assert "| Estado | **APPROVED · ACTIVE** |" in adr
    registro = (REPO / "docs/governance/architecture-decision-register.md").read_text()
    assert any(linea.startswith("| ADR-D0-015 |") and "APPROVED · ACTIVE" in linea for linea in registro.splitlines())


def test_el_registro_declara_duena_y_politica_y_el_de_la_045_esta_deshabilitado():
    from app.modules.scheduler.registry import manejadores
    from app.modules.scheduler.service import validar_registro

    registrados = manejadores()
    validar_registro(registrados)
    assert {m.code: (m.owner_spec, m.enabled) for m in registrados}["approval_step_expiration"] == ("045", False)


def test_ningun_error_de_la_047_lleva_texto_escrito_a_mano():
    culpables = []
    for f in MODULOS_047:
        if f.name == "messages.py":
            continue
        for nodo in ast.walk(ast.parse(f.read_text())):
            if isinstance(nodo, ast.keyword) and nodo.arg == "message" \
                    and isinstance(nodo.value, ast.Constant | ast.JoinedStr):
                culpables.append(f"{f.name}:{nodo.value.lineno}")
    assert culpables == []


def test_ninguna_tabla_de_mensajes_guarda_texto_compuesto():
    init_models()
    for tabla in ("notifications", "tasks", "alerts"):
        columnas = set(Base.metadata.tables[tabla].columns.keys())
        assert {"message_key", "message_params"} <= columnas
        assert not columnas & {"text", "title", "body", "message", "rendered_text", "message_text"}, tabla


def test_la_api_de_la_047_no_borra_nada():
    from app.main import create_app

    rutas = create_app().openapi()["paths"]
    borrados = [p for p, ops in rutas.items()
                if p.startswith(("/api/v1/notifications", "/api/v1/tasks", "/api/v1/alerts")) and "delete" in ops]
    assert borrados == []


def test_cada_modulo_de_la_047_declara_su_frontera():
    sin = [f.name for f in MODULOS_047 if f.name != "__init__.py" and "# Spec 047 ·" not in f.read_text()]
    assert sin == []
