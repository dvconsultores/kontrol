"""Orden única de certificación de release de KONTROL.

Certifica un release con V6R (runtime de producto reconstruido desde el digest certificado
más `requirements.lock`) y V6C (V6R más `requirements-test.lock`). V0 nunca se ejecuta por
defecto. El orquestador usa solo la biblioteca estándar y se lanza con
`python3 qa/certificar-release.py`; todo proceso certificado corre en V6R o V6C, nunca en
un Python del PATH.

Uso:
    python3 qa/certificar-release.py
    python3 qa/certificar-release.py --incluir-v0-historico
    python3 qa/certificar-release.py --espera-salud-min 0
    python3 qa/certificar-release.py --conservar-espacio
    python3 qa/certificar-release.py --solo-preflight

Códigos de salida: 0 = certificación completa; 1 = fallo de certificación; 3 = entorno
inválido; 4 = diagnóstico (`--solo-preflight`) correcto, no certifica; 70 = preflight,
error interno o interrupción.

La evidencia queda en `qa/certificaciones/<run_id>/manifest.json` (fuera de Git) y el
espacio de trabajo en `${KONTROL_QA_CERT_HOME:-~/.cache/kontrol-qa/certificacion}/<run_id>/`.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import certificacion_release  # noqa: E402

if __name__ == "__main__":
    sys.exit(certificacion_release.main())
