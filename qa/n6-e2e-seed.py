"""Siembra el mundo multiempresa de N6 en la base sobre la que corre el E2E.

Hasta aquí ese mundo solo existía en la base SQLite que fabrica
`qa/n6-multicompany-bootstrap.py`, de modo que las 25 pruebas de
`n6-multicompany.spec.ts` y `n6-a11y-responsive.spec.ts` buscaban a sus usuarios
en una base distinta de aquella contra la que se ejecutaban, y ni siquiera
llegaban a abrir sesión.

Se ejecuta **después** de `qa/pg-e2e-seed.py` y de `qa/spec047-e2e-seed.py`:
necesita el tenant y la primera empresa. Es idempotente, no borra nada y puede
correr antes de cada suite.

Uso:
    KONTROL_DB_URL=postgresql+psycopg2://... PYTHONPATH=resources/backend \
        resources/backend/.venv/bin/python qa/n6-e2e-seed.py
"""

from __future__ import annotations

import json
import os
import tempfile

os.environ.setdefault("KONTROL_SECRET_KEY", "qa-secret-key-0123456789abcdef0123456789abcdef")
os.environ.setdefault("KONTROL_ENVIRONMENT", "local")
os.environ.setdefault("KONTROL_LOG_JSON", "false")

import n6_world  # noqa: E402  (mismo directorio que este guion)

from app.core.database import get_session_factory, init_models  # noqa: E402

#: Dónde deja los identificadores. Es el mismo sitio del que los lee
#: `n6-multicompany.spec.ts`: la suite no los codifica a mano porque sembrar de
#: nuevo genera otros, y una prueba con ids fijos acabaría pasando por el motivo
#: equivocado —el id ya no existe, así que claro que se rechaza—.
IDS_FILE = os.environ.get(
    "KONTROL_QA_IDS_FILE", os.path.join(tempfile.gettempdir(), "kontrol-n6-ids.json"))


def main() -> None:
    init_models()
    db = get_session_factory()()
    try:
        ids = n6_world.sembrar(db)
    finally:
        db.close()

    with open(IDS_FILE, "w", encoding="utf-8") as fh:
        json.dump(ids, fh)
    print({**ids, "ids_file": IDS_FILE})


if __name__ == "__main__":
    main()
