"""Cuántos schemas temporales de ESTE proceso existen ahora mismo en el servidor."""
import os

from pg_harness import PREFIJO_DE_MARCA, motor_administrativo
from sqlalchemy import text


def schemas_vivos_de_este_proceso() -> int:
    admin = motor_administrativo(os.environ["KONTROL_TEST_DB_URL"])
    try:
        with admin.connect() as conn:
            return conn.execute(text(
                "select count(*) from pg_namespace where obj_description(oid, 'pg_namespace') like :marca"),
                {"marca": f"{PREFIJO_DE_MARCA}pid={os.getpid()} %"}).scalar_one()
    finally:
        admin.dispose()
