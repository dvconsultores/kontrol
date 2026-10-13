"""Ayudante de las sondas de `sesion_de_prueba`: cada prueba cuenta por JSON (`KONTROL_SONDA_INFORME`) qué vio."""
import json
import os

import pg_harness
from sqlalchemy import select, text

from app.modules.organization.models import Installation


def _schema(db):
    return db.execute(text("select current_schema()")).scalar_one() if os.environ.get("KONTROL_TEST_DB_URL") else None


def informar(modulo: str, db, **datos: object) -> None:
    registro = {"modulo": modulo, "pid": os.getpid(), "schema": _schema(db), "motor": id(db.get_bind().engine),
                "instalaciones_al_empezar": sorted(i.id for i in db.execute(select(Installation)).scalars()),
                "schemas_creados": pg_harness.INFORME.schemas_creados,
                "conexiones_cortadas": len(pg_harness.INFORME.conexiones_cortadas), **datos}
    with open(os.environ["KONTROL_SONDA_INFORME"], "a", encoding="utf-8") as fh:
        fh.write(json.dumps(registro) + "\n")


def escribir_y_confirmar(db, marcador: str) -> None:
    db.add(Installation(id=marcador, installation_uuid=f"uuid-{marcador}", state="ACTIVE"))
    db.commit()
