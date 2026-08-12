#!/usr/bin/env python3
"""T-220 · Smoke de rendimiento backend (P50/P95) con TestClient in-process.

Mide latencias de endpoints de lectura representativos por módulo y reporta
percentiles P50/P95 y un umbral máximo por operación. Es un smoke (carga
ligera, ~60 llamadas por ruta), no una prueba de carga.

Uso:
    python qa/perf-smoke.py [--samples N] [--json salida.json]

Salida por defecto en stdout (tabla) y opcional --json para la evidencia.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# Bootstrap idéntico a los tests de integración (BD SQLite en memoria).
# ---------------------------------------------------------------------------
_ENGINE = _FACTORY = None
_CLIENT: TestClient | None = None

# Rutas representativas de lectura por módulo (GET). El orden importa: se
# ejecutan secuencialmente con el mismo token.
READ_ROUTES: list[tuple[str, str]] = [
    ("identidad", "/api/v1/auth/me"),
    ("dashboard", "/api/v1/reporting/dashboard"),
    ("organizacion", "/api/v1/organization/companies"),
    ("maestros", "/api/v1/maestros/terceros"),
    ("inventario", "/api/v1/inventory/balances"),
    ("compras", "/api/v1/purchasing/supplier-invoices"),
    ("ventas", "/api/v1/sales/invoices"),
    ("tesoreria", "/api/v1/treasury/cash-sessions"),
    ("fiscal", "/api/v1/fiscal/control-batches"),
    ("regulatorio", "/api/v1/regulatory/authorities"),
    ("reportes", "/api/v1/reporting/jobs"),
    ("licenciamiento", "/api/v1/license/status"),
]

# Umbrales de latencia (segundos) por ruta (P95). Amplios para CI en sandbox.
THRESHOLD_P95: dict[str, float] = {
    "identidad": 0.5, "dashboard": 0.5, "organizacion": 0.5, "maestros": 0.5,
    "inventario": 0.5, "compras": 0.5, "ventas": 0.5, "tesoreria": 0.5,
    "fiscal": 0.5, "regulatorio": 0.5, "reportes": 0.5, "licenciamiento": 0.5,
}


def _bootstrap() -> TestClient:
    global _ENGINE, _FACTORY, _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True,
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    from app.core.database import Base, get_db, init_models

    init_models()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    import app.core.database as dm

    dm._engine = engine  # type: ignore[attr-defined]
    dm._SessionLocal = factory  # type: ignore[attr-defined]

    db = factory()
    from app.modules.setup.api import SetupRequest, initialize

    initialize(db, SetupRequest(
        tenant_code="DEMO", tenant_name="Empresa Demo", company_code="D1",
        company_legal_name="Demo C.A.", company_rif="J-12345678-9",
        admin_username="admin", admin_password="Kontrol2026Segura!",
    ))
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    pub = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    from app.modules.organization.models import Installation

    inst = db.execute(select(Installation).limit(1)).scalars().first()
    now = datetime.now(UTC)
    payload = {
        "issuer": "K", "license_id": "LIC-PERF", "installation_id": inst.installation_uuid,
        "customer_id": "C1", "contract_id": "C1", "company_tax_id": "J-12345678-9",
        "period_start": (now - timedelta(days=30)).isoformat(),
        "period_end": (now + timedelta(days=120)).isoformat(),
        "critical_warning_start": (now + timedelta(days=180)).isoformat(),
        "read_only_start": (now + timedelta(days=200)).isoformat(),
        "entitlements": {"companies": 1, "users": 25, "modules": ["*"]},
        "minimum_version": "1.0.0", "kid": "k",
    }
    sig = key.sign(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hex()
    os.environ["KONTROL_LICENSE_PUBLIC_KEY_PEM"] = pub
    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        from app.modules.licensing import service as licensing_service

        licensing_service.import_license(db, payload=payload, signature_hex=sig, source="MANUAL")
    finally:
        os.environ.pop("KONTROL_LICENSE_PUBLIC_KEY_PEM", None)
        get_settings.cache_clear()
    db.close()

    from app.main import create_app

    app = create_app()

    def _override_get_db():
        d = factory()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = _override_get_db
    _ENGINE, _FACTORY = engine, factory
    _CLIENT = TestClient(app, raise_server_exceptions=False)
    return _CLIENT


def _login(client: TestClient) -> dict[str, str]:
    r = client.post("/api/v1/auth/login", json={
        "tenant_code": "DEMO", "username": "admin", "password": "Kontrol2026Segura!",
    })
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _percentile(values: list[float], p: float) -> float:
    s = sorted(values)
    k = (len(s) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke de rendimiento backend")
    parser.add_argument("--samples", type=int, default=40)
    parser.add_argument("--json", type=str, default="")
    parser.add_argument("--warmup", type=int, default=3)
    args = parser.parse_args()

    client = _bootstrap()
    headers = _login(client)
    results: dict[str, dict] = {}
    failures: list[str] = []
    overall_ok = True

    for module, route in READ_ROUTES:
        latencies: list[float] = []
        # warm-up
        for _ in range(args.warmup):
            client.get(route, headers=headers)
        for _ in range(args.samples):
            start = time.perf_counter()
            r = client.get(route, headers=headers)
            latencies.append(time.perf_counter() - start)
            if r.status_code >= 400:
                failures.append(f"{module} {route}: {r.status_code} {r.text[:120]}")
                break
        p50 = _percentile(latencies, 0.50)
        p95 = _percentile(latencies, 0.95)
        threshold = THRESHOLD_P95.get(module, 0.5)
        ok = p95 <= threshold and not failures
        overall_ok = overall_ok and ok
        results[module] = {
            "route": route, "samples": len(latencies), "p50_ms": round(p50 * 1000, 1),
            "p95_ms": round(p95 * 1000, 1), "threshold_ms": threshold * 1000, "ok": ok,
        }

    # Tabla
    print(f"{'Módulo':<14}{'P50(ms)':>10}{'P95(ms)':>10}{'Umbral':>10}  Resultado")
    print("-" * 62)
    for module, res in results.items():
        flag = "OK" if res["ok"] else "FAIL"
        print(f"{module:<14}{res['p50_ms']:>10.1f}{res['p95_ms']:>10.1f}"
              f"{res['threshold_ms']:>10.0f}  {flag}")

    if failures:
        print("\nFallos HTTP:")
        for f in failures:
            print("  -", f)

    print(f"\nTotal rutas: {len(results)} · Resultado global: {'OK' if overall_ok else 'FAIL'}")

    if args.json:
        payload = {
            "tool": "T-220 perf-smoke", "generated_at": datetime.now(UTC).isoformat(),
            "overall_ok": overall_ok, "results": results, "failures": failures,
        }
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        print(f"Evidencia escrita en {args.json}")

    return 0 if overall_ok and not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
