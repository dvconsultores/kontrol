"""Firma una licencia SINTÉTICA para la instalación de una corrida E2E.

Uso (la URL de la base viaja en el entorno, nunca en la línea de órdenes):
    KONTROL_DB_URL=postgresql+psycopg2://... KONTROL_E2E_LICENSE_SIGNING_KEY=<estado>/license/qa_license_signing_key.pem \\
    PYTHONPATH=resources/backend python qa/licencia_firmada.py <license_id> [--otra-instalacion] [--firma-invalida]
        [--anio <AAAA>] [--periodo <inicio ISO> <fin ISO>] [--revision <json>]
        [--modulos <a,b>] [--kid <kid>] [--sin-kid] [--firmante-b]
    PYTHONPATH=resources/backend python qa/licencia_firmada.py --vigente

`--anio` firma el período anual del contrato (1 abr <AAAA> → 31 mar <AAAA+1>, America/Caracas);
`--periodo` firma exactamente las fechas dadas (p. ej. las del detalle vigente, para una reemisión
del mismo período). Sin ninguna de las dos, el período relativo a hoy de la siembra. `--revision`
añade el claim tal cual (`3`, `999`, `true`, `0`…): revisionadas sintéticas **hostiles**, para probar
conflicto, manipulación y valores inválidos; las revisionadas legítimas las emite
`qa/autoridad_central.py`. `--vigente` imprime el artefacto vigente exacto, tal como está guardado
(carga y firma): la reimportación idempotente. Rotación de clave: `--firmante-b` firma con la segunda
clave sintética de la corrida (`KONTROL_E2E_LICENSE_SIGNING_KEY_B`); `--kid` fija el `kid` del paquete
(por defecto el de A) y `--sin-kid` lo omite: los tres sirven para probar que el cliente elige la clave
exactamente por el `kid` firmado. `--modulos` fija los entitlements firmados; sin la
opción, los de la siembra (Gobierno incluido); `--modulos ""` firma una licencia sin módulos,
solo para pruebas que lo declaren.

Imprime en la salida estándar el JSON `{"payload": {...}, "signature_hex": "..."}` que espera
`POST /api/v1/license/activate`. Firma con el **firmante sintético de la corrida** —el par que
`qa/e2e-run.py` genera y cuya clave pública declara como `KONTROL_LICENSE_PUBLIC_KEY_PEM` del
backend de esa corrida (FR-010-154)—. Nunca con la clave de la instalación: esa identifica a la
instalación y no es ancla de confianza. Solo en entornos de QA.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

os.environ.setdefault("KONTROL_SECRET_KEY", "qa-secret-key-0123456789abcdef0123456789abcdef")
os.environ.setdefault("KONTROL_ENVIRONMENT", "local")
os.environ.setdefault("KONTROL_LOG_JSON", "false")

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.database import get_session_factory, init_models  # noqa: E402
from app.modules.licensing.models import LicenseArtifact, LicenseState  # noqa: E402
from app.modules.organization.models import Installation  # noqa: E402

MODULOS_DE_LA_SIEMBRA: tuple[str, ...] = ("gobierno",)  # los de `qa/pg-e2e-seed.py`


def payload_sintetico(license_id: str, installation_id: str, *, anio: int | None = None,
                      periodo: tuple[str, str] | None = None,
                      modulos: Sequence[str] = MODULOS_DE_LA_SIEMBRA) -> dict[str, object]:
    """Una licencia como la de la siembra E2E (`qa/pg-e2e-seed.py`): mismo `kid`, mismos campos.

    Por defecto, el período relativo a hoy de la siembra. Con `anio`, el período anual del
    contrato (DOC-07 §5.1). Con `periodo`, exactamente ese inicio y fin (reemisión del vigente).
    Conserva los entitlements de la siembra (`modulos` = `MODULOS_DE_LA_SIEMBRA`) salvo que se
    pidan otros explícitamente.
    """
    if periodo is not None:
        inicio, fin = datetime.fromisoformat(periodo[0]), datetime.fromisoformat(periodo[1])
        critico, solo_lectura = fin + timedelta(days=21), fin + timedelta(days=31)
    elif anio is not None:
        inicio = datetime.fromisoformat(f"{anio}-04-01T00:00:00-04:00")
        fin = datetime.fromisoformat(f"{anio + 1}-03-31T23:59:59-04:00")
        critico = datetime.fromisoformat(f"{anio + 1}-04-21T00:00:00-04:00")
        solo_lectura = datetime.fromisoformat(f"{anio + 1}-05-01T00:00:00-04:00")
    else:
        ahora = datetime.now(UTC)
        inicio, fin = ahora - timedelta(days=30), ahora + timedelta(days=300)
        critico, solo_lectura = ahora + timedelta(days=320), ahora + timedelta(days=330)
    return {
        "issuer": "KONTROL-QA", "license_id": license_id, "installation_id": installation_id,
        "customer_id": "C1", "contract_id": "C1", "company_tax_id": "J-12345678-9",
        "period_start": inicio.isoformat(), "period_end": fin.isoformat(),
        "critical_warning_start": critico.isoformat(), "read_only_start": solo_lectura.isoformat(),
        "plan": "MULTI_COMPANY", "minimum_version": "1.0.0", "kid": "kontrol-lic-2026-01",
        "entitlements": {"modules": list(modulos)},
    }


def firmar(payload: dict[str, object], clave: Ed25519PrivateKey) -> str:
    canonico = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return clave.sign(canonico).hex()


def artefacto_vigente() -> dict[str, object]:
    """El artefacto de la licencia vigente, exactamente como se guardó: la última fila aceptada de ese identificador."""
    init_models()
    db = get_session_factory()()
    try:
        estado = db.execute(select(LicenseState)).scalars().first()
        if estado is None:
            raise RuntimeError("la base no tiene licencia vigente")
        fila = db.execute(
            select(LicenseArtifact).where(LicenseArtifact.license_id == estado.license_id)
            .order_by(LicenseArtifact.imported_at.desc(), LicenseArtifact.created_at.desc())
        ).scalars().first()
    finally:
        db.close()
    if fila is None:
        raise RuntimeError("la licencia vigente no tiene artefacto guardado")
    return {"payload": fila.payload, "signature_hex": fila.signature_hex}


def main(argv: list[str]) -> int:
    if argv == ["--vigente"]:
        if os.environ.get("KONTROL_ENVIRONMENT", "local") not in ("local", "dev", "qa"):
            raise RuntimeError("este guion solo lee licencias de prueba en entornos de QA")
        print(json.dumps(artefacto_vigente(), ensure_ascii=False))
        return 0
    if not argv or argv[0].startswith("--"):
        print("uso: licencia_firmada.py <license_id> [--otra-instalacion] [--firma-invalida] [--revision <json>] | --vigente", file=sys.stderr)
        return 2
    if os.environ.get("KONTROL_ENVIRONMENT", "local") not in ("local", "dev", "qa"):
        raise RuntimeError("este guion solo firma licencias de prueba en entornos de QA")
    ruta_firmante = os.environ.get("KONTROL_E2E_LICENSE_SIGNING_KEY_B" if "--firmante-b" in argv else "KONTROL_E2E_LICENSE_SIGNING_KEY")
    if not ruta_firmante:
        raise RuntimeError("KONTROL_E2E_LICENSE_SIGNING_KEY(_B) es obligatoria: los firmantes sintéticos los genera la corrida")
    clave = serialization.load_pem_private_key(Path(ruta_firmante).read_bytes(), password=None)
    if not isinstance(clave, Ed25519PrivateKey):
        raise RuntimeError("el firmante sintético no es Ed25519")

    init_models()
    db = get_session_factory()()
    try:
        instalacion = db.execute(select(Installation).order_by(Installation.created_at).limit(1)).scalars().first()
    finally:
        db.close()
    if instalacion is None:
        raise RuntimeError("la base no tiene instalación")

    destino = "KTL-QA-OTRA-INSTALACION" if "--otra-instalacion" in argv else instalacion.installation_uuid
    anio = int(argv[argv.index("--anio") + 1]) if "--anio" in argv else None
    periodo = (argv[argv.index("--periodo") + 1], argv[argv.index("--periodo") + 2]) if "--periodo" in argv else None
    if "--modulos" in argv:
        crudo = argv[argv.index("--modulos") + 1]
        modulos: tuple[str, ...] = tuple(m.strip() for m in crudo.split(",") if m.strip())
    else:
        modulos = MODULOS_DE_LA_SIEMBRA
    payload = payload_sintetico(argv[0], destino, anio=anio, periodo=periodo, modulos=modulos)
    if "--revision" in argv:
        payload["revision"] = json.loads(argv[argv.index("--revision") + 1])  # tal cual: también valores inválidos, a propósito
    if "--kid" in argv:
        payload["kid"] = argv[argv.index("--kid") + 1]
    if "--sin-kid" in argv:
        payload.pop("kid", None)
    firma = "00" * 64 if "--firma-invalida" in argv else firmar(payload, clave)
    print(json.dumps({"payload": payload, "signature_hex": firma}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
