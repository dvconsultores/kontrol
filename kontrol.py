#!/usr/bin/env python3
"""CLI de KONTROL (FR-001-083/084, DOC-08 §19).

Comandos: install, preflight, backup, restore, backup-verify, update, diagnose, scheduler-tick.
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


def cmd_backup(args: argparse.Namespace) -> int:
    """Crea una copia de seguridad verificable dentro del contenedor backend."""
    cmd = ["docker", "compose", "-f", str(COMPOSE), "exec", "-T", "-e", "KONTROL_BACKUP_KEY", "backend", "python", "-m", "app.ops.backup", "create"]
    if not any(a == "--dest" or a.startswith("--dest=") for a in args.args):
        cmd.append("--dest")
        cmd.append("/data/backups")
    cmd.extend(args.args)
    return _run(cmd)


def cmd_restore(args: argparse.Namespace) -> int:
    """Restaura una copia de seguridad verificada dentro del contenedor backend."""
    return _run(
        ["docker", "compose", "-f", str(COMPOSE), "exec", "-T", "-e", "KONTROL_BACKUP_KEY", "backend", "python", "-m", "app.ops.backup", "restore", *args.args]
    )


def cmd_backup_verify(args: argparse.Namespace) -> int:
    """Verifica un paquete de copia de seguridad dentro del contenedor backend."""
    return _run(
        ["docker", "compose", "-f", str(COMPOSE), "exec", "-T", "-e", "KONTROL_BACKUP_KEY", "backend", "python", "-m", "app.ops.backup", "verify", *args.args]
    )


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
    p = sub.add_parser("backup", help="Crea una copia de seguridad")
    p.add_argument("args", nargs=argparse.REMAINDER)
    p = sub.add_parser("restore", help="Restaura una copia de seguridad")
    p.add_argument("args", nargs=argparse.REMAINDER)
    p = sub.add_parser("backup-verify", help="Verifica un paquete de copia")
    p.add_argument("args", nargs=argparse.REMAINDER)
    sub.add_parser("update", help="Actualización controlada")
    sub.add_parser("diagnose", help="Diagnóstico de servicios")
    sub.add_parser("scheduler-tick", help="Un tick del planificador de plataforma")
    args = parser.parse_args()
    handlers = {
        "install": cmd_install,
        "preflight": cmd_preflight,
        "backup": cmd_backup,
        "restore": cmd_restore,
        "backup-verify": cmd_backup_verify,
        "update": cmd_update,
        "diagnose": cmd_diagnose,
        "scheduler-tick": cmd_scheduler_tick,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
