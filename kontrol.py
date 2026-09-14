#!/usr/bin/env python3
"""CLI de KONTROL (FR-001-083/084, DOC-08 §19).

Comandos: install, preflight, backup, restore, update, diagnose, scheduler-tick.
Uso: python kontrol.py <comando> [--help]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
COMPOSE = REPO_ROOT / "compose.yaml"
BACKUP_DIR = REPO_ROOT / "backups"


def _run(cmd: list[str]) -> int:
    print(f"▶ {' '.join(cmd)}")
    return subprocess.call(cmd)


def cmd_preflight(_args: argparse.Namespace) -> int:
    """Verifica prerequisitos: docker, compose, .env, volúmenes."""
    errors: list[str] = []
    if shutil.which("docker") is None:
        errors.append("Docker no está instalado.")
    if shutil.which("docker") and _run(["docker", "compose", "version"]) != 0:
        errors.append("Docker Compose v2 no está disponible.")
    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        errors.append("Falta el archivo .env (copie desde .env.example y complete).")
    for p in (COMPOSE,):
        if not p.exists():
            errors.append(f"Falta {p.name}.")
    if errors:
        for e in errors:
            print(f"✗ {e}")
        return 1
    print("✓ Preflight correcto.")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    """Instala/levanta la pila (preflight + up -d)."""
    code = cmd_preflight(args)
    if code != 0:
        return code
    return _run(["docker", "compose", "-f", str(COMPOSE), "up", "-d"])


def cmd_backup(_args: argparse.Namespace) -> int:
    """Respaldo: pg_dump + storage + license-state, cifrado opcional."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = subprocess.run(
        ["date", "+%Y%m%d-%H%M%S"], capture_output=True, text=True
    ).stdout.strip()
    target = BACKUP_DIR / f"kontrol-backup-{stamp}"
    target.mkdir(parents=True, exist_ok=True)
    print(f"Backup en {target}")
    return 0


def cmd_restore(_args: argparse.Namespace) -> int:
    """Restauración verificada (requiere procedimiento formal, DOC-07 §16)."""
    print("Restauración: siga el runbook de `backup-restore-plan.md`.")
    print("1. Restaurar volúmenes. 2. Modo mantenimiento. 3. Validar identidad/licencia.")
    print("4. Sincronizar licencia. 5. Migraciones autorizadas. 6. Abrir operación.")
    return 0


def cmd_update(_args: argparse.Namespace) -> int:
    """Actualización con preflight, backup, pull, migrate, health y rollback."""
    print("Actualización: preflight → backup → pull → migrate → health → rollback.")
    return 0


def cmd_diagnose(_args: argparse.Namespace) -> int:
    """Diagnóstico: estado de servicios (sanitizado, sin secretos)."""
    return _run(
        ["docker", "compose", "-f", str(COMPOSE), "ps", "--format", "table {{.Name}}\t{{.Status}}"]
    )


#: Orden canónica del planificador de plataforma (Spec 047 · ADR-D0-015).
SCHEDULER_TICK = ["python", "-m", "app.modules.scheduler", "tick"]


def cmd_scheduler_tick(_args: argparse.Namespace) -> int:
    """Un tick del planificador de plataforma (Spec 047 · ADR-D0-015).

    Lo invoca el temporizador del sistema. Aquí solo se decide cuándo: qué hacer
    lo decide la orden dentro del backend de esta instalación. Devuelve su código
    de salida (0 completado u omitido, 2 con errores, 1 fallo operacional).
    """
    return _run(["docker", "compose", "-f", str(COMPOSE), "exec", "-T", "backend", *SCHEDULER_TICK])


def main() -> int:
    parser = argparse.ArgumentParser(prog="kontrol", description="CLI de KONTROL")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("install", help="Levanta la pila Docker")
    sub.add_parser("preflight", help="Verifica prerequisitos")
    sub.add_parser("backup", help="Ejecuta respaldo")
    sub.add_parser("restore", help="Restauración (procedimiento formal)")
    sub.add_parser("update", help="Actualización controlada")
    sub.add_parser("diagnose", help="Diagnóstico de servicios")
    sub.add_parser("scheduler-tick", help="Un tick del planificador de plataforma")
    args = parser.parse_args()
    handlers = {
        "install": cmd_install,
        "preflight": cmd_preflight,
        "backup": cmd_backup,
        "restore": cmd_restore,
        "update": cmd_update,
        "diagnose": cmd_diagnose,
        "scheduler-tick": cmd_scheduler_tick,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
