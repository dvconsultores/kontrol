"""Autoridad Central de Licencias **efímera** de una corrida E2E: la real, sobre una base propia.

Uso (desde `resources/backend`, con el entorno de la corrida; la URL de la base del cliente viaja en el
entorno, nunca en la línea de órdenes):
    KONTROL_DB_URL=<base del cliente> KONTROL_E2E_LICENSE_SIGNING_KEY=<estado>/license/qa_license_signing_key.pem \\
    PYTHONPATH=resources/backend python qa/autoridad_central.py emitir (--anio <AAAA> | --periodo <inicio ISO> <fin ISO>)
        [--entitlements <JSON>] [--minimum-version <v>]

Levanta `central_authority` (servicio y migraciones reales) sobre `<estado>/license/central.sqlite`,
el directorio efímero del firmante de la corrida, registra la instalación de la corrida (idempotente,
con la clave pública que el cliente guarda) y emite la **siguiente `revision`** del período pedido,
firmando con la clave sintética de la corrida: la misma cuya pública el cliente declara como ancla
(`KONTROL_LICENSE_PUBLIC_KEY_PEM`). Imprime `{"payload", "signature_hex", "license_id", "revision"}`.
El cliente no asigna revisiones: solo las consume. Solo en entornos de QA; nunca con una clave real.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

os.environ.setdefault("KONTROL_SECRET_KEY", "qa-secret-key-0123456789abcdef0123456789abcdef")
os.environ.setdefault("KONTROL_ENVIRONMENT", "local")
os.environ.setdefault("KONTROL_LOG_JSON", "false")


def _preparar_entorno_central(ruta_firmante: Path) -> None:
    """La configuración de la autoridad, antes de importarla: base y clave propias de la corrida."""
    os.environ["KONTROL_CENTRAL_DB_URL"] = f"sqlite+pysqlite:///{ruta_firmante.parent / 'central.sqlite'}"
    os.environ["KONTROL_CENTRAL_SIGNING_PRIVATE_KEY_PEM"] = ruta_firmante.read_text()
    os.environ.setdefault("KONTROL_CENTRAL_ENVIRONMENT", "qa")
    os.environ.setdefault("KONTROL_CENTRAL_SIGNING_KID", "kontrol-lic-2026-01")
    os.environ.setdefault("KONTROL_CENTRAL_LOG_JSON", "false")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="autoridad_central", description="Autoridad Central efímera de la corrida E2E")
    sub = parser.add_subparsers(dest="orden", required=True)
    p = sub.add_parser("emitir", help="siguiente revisión del período para la instalación de la corrida")
    p.add_argument("--anio", type=int, default=None)
    p.add_argument("--periodo", nargs=2, default=None, metavar=("INICIO", "FIN"))
    p.add_argument("--entitlements", default="{}")
    p.add_argument("--minimum-version", default="1.0.0")
    args = parser.parse_args(argv)

    if os.environ.get("KONTROL_ENVIRONMENT", "local") not in ("local", "dev", "qa"):
        raise RuntimeError("este guion solo emite licencias de prueba en entornos de QA")
    ruta_firmante = os.environ.get("KONTROL_E2E_LICENSE_SIGNING_KEY")
    if not ruta_firmante:
        raise RuntimeError("KONTROL_E2E_LICENSE_SIGNING_KEY es obligatoria: el firmante sintético lo genera la corrida")
    _preparar_entorno_central(Path(ruta_firmante))

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import select

    from app.core.database import get_session_factory, init_models
    from app.modules.organization.models import Installation
    from central_authority import service
    from central_authority.config import get_settings
    from central_authority.database import get_session_factory as central_sessions

    # La instalación de la corrida, tal como la conoce el cliente (identificador y clave pública).
    init_models()
    db = get_session_factory()()
    try:
        instalacion = db.execute(select(Installation).order_by(Installation.created_at).limit(1)).scalars().first()
    finally:
        db.close()
    if instalacion is None:
        raise RuntimeError("la base del cliente no tiene instalación")

    # La autoridad: sus migraciones reales sobre su base efímera (idempotente), y el registro (idempotente).
    backend = Path(__file__).resolve().parents[1] / "resources" / "backend"
    os.chdir(backend)  # `script_location` del ini es relativo a `resources/backend`
    command.upgrade(Config(str(backend / "central_authority" / "alembic.ini")), "head")
    central_db = central_sessions()()
    try:
        service.register_installation(
            central_db, installation_uuid=instalacion.installation_uuid, public_key_pem=instalacion.public_key,
            customer_id="C1", contract_id="C1", company_tax_id="J-12345678-9", operator="e2e")
        if args.anio is not None:
            inicio, fin = service.periodo_anual(args.anio)
        elif args.periodo:
            inicio, fin = datetime.fromisoformat(args.periodo[0]), datetime.fromisoformat(args.periodo[1])
        else:
            parser.error("indique --anio o --periodo")
        emision = service.issue_license(
            central_db, settings=get_settings(), installation_uuid=instalacion.installation_uuid, period_start=inicio, period_end=fin,
            entitlements=json.loads(args.entitlements), minimum_version=args.minimum_version, operator="e2e")
    finally:
        central_db.close()
    print(json.dumps({k: emision[k] for k in ("payload", "signature_hex", "license_id", "revision")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
