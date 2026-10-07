"""CLI del propietario (Fase 1): registrar instalaciones, emitir y reemitir licencias, consultar el libro.

Corre dentro del entorno de la Autoridad Central con su configuración (`KONTROL_CENTRAL_*`). Toda
orden exige `--operator`: una etiqueta operativa que queda en el libro y la auditoría; no es
autenticación remota. La salida es JSON; nunca imprime la clave privada.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from central_authority import service
from central_authority.config import get_settings
from central_authority.database import get_session_factory


def _periodo(args: argparse.Namespace) -> tuple[datetime, datetime]:
    if args.anio is not None:
        return service.periodo_anual(args.anio)
    if args.period_start and args.period_end:
        inicio, fin = datetime.fromisoformat(args.period_start), datetime.fromisoformat(args.period_end)
        if inicio.tzinfo is None or fin.tzinfo is None:
            raise service.CentralError("INVALID_PERIOD", "Las fechas del período deben llevar zona horaria.")
        return inicio, fin
    raise service.CentralError("INVALID_PERIOD", "Indique --anio o --period-start y --period-end.")


def _entitlements(texto: str) -> dict[str, Any]:
    try:
        valor = json.loads(texto)
    except json.JSONDecodeError:
        raise service.CentralError("INVALID_ENTITLEMENTS", "Los derechos deben ser un objeto JSON.") from None
    if not isinstance(valor, dict):
        raise service.CentralError("INVALID_ENTITLEMENTS", "Los derechos deben ser un objeto JSON.")
    return valor


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="central_authority", description="Autoridad Central de Licencias de KONTROL — operaciones del propietario")
    sub = parser.add_subparsers(dest="orden", required=True)

    def comun(p: argparse.ArgumentParser) -> None:
        p.add_argument("--operator", required=True, help="etiqueta operativa de quien ejecuta (queda en libro y auditoría)")

    p = sub.add_parser("register-installation", help="alta idempotente de una instalación")
    comun(p)
    p.add_argument("--installation-id", required=True)
    p.add_argument("--public-key-file", required=True, type=Path, help="PEM de la clave pública de la instalación (de su solicitud de activación)")
    p.add_argument("--customer-id", required=True)
    p.add_argument("--contract-id", required=True)
    p.add_argument("--company-tax-id", default=None)

    for nombre, ayuda in (("issue-license", "emite la siguiente revisión del período"), ("reissue-license", "alias de issue-license")):
        p = sub.add_parser(nombre, help=ayuda)
        comun(p)
        p.add_argument("--installation-id", required=True)
        p.add_argument("--anio", type=int, default=None, help="período anual del contrato (1 abr → 31 mar)")
        p.add_argument("--period-start", default=None)
        p.add_argument("--period-end", default=None)
        p.add_argument("--entitlements", default="{}", help="objeto JSON")
        p.add_argument("--minimum-version", default="1.0.0")

    p = sub.add_parser("show-issuance", help="una emisión del libro")
    comun(p)
    p.add_argument("--license-id", required=True)

    p = sub.add_parser("list-issuances", help="emisiones de una instalación")
    comun(p)
    p.add_argument("--installation-id", required=True)
    return parser


def ejecutar(args: argparse.Namespace) -> Any:
    db = get_session_factory()()
    try:
        if args.orden == "register-installation":
            fila = service.register_installation(
                db, installation_uuid=args.installation_id, public_key_pem=args.public_key_file.read_text(),
                customer_id=args.customer_id, contract_id=args.contract_id, company_tax_id=args.company_tax_id, operator=args.operator)
            return {"installation_id": fila.installation_uuid, "customer_id": fila.customer_id, "contract_id": fila.contract_id,
                    "company_tax_id": fila.company_tax_id, "registered_by": fila.registered_by, "created_at": fila.created_at.isoformat()}
        if args.orden in ("issue-license", "reissue-license"):
            inicio, fin = _periodo(args)
            return service.issue_license(
                db, settings=get_settings(), installation_uuid=args.installation_id, period_start=inicio, period_end=fin,
                entitlements=_entitlements(args.entitlements), minimum_version=args.minimum_version, operator=args.operator)
        if args.orden == "show-issuance":
            return service.get_issuance(db, args.license_id)
        if args.orden == "list-issuances":
            return service.list_issuances(db, args.installation_id)
        raise service.CentralError("INVALID_ARGUMENT", "Orden desconocida.")
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    try:
        resultado = ejecutar(args)
    except service.CentralError as exc:
        print(json.dumps({"error": exc.code, "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
