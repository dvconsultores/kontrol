"""Sonda: una prueba que crea una base entera, como las de migración, y la apunta al arnés."""
import os

from pg_harness import motor_administrativo, registrar_base
from sqlalchemy import text
from sqlalchemy.engine import make_url

NOMBRE = "kontrol_test_sonda_base"


def test_crea_una_base_y_la_registra():
    servidor = make_url(os.environ["KONTROL_TEST_DB_URL"]).set(database="postgres").render_as_string(hide_password=False)
    admin = motor_administrativo(servidor)
    try:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{NOMBRE}" WITH (FORCE)'))
            conn.execute(text(f'CREATE DATABASE "{NOMBRE}"'))
            registrar_base(NOMBRE)
            assert conn.execute(text("select count(*) from pg_database where datname = :n"), {"n": NOMBRE}).scalar_one() == 1
    finally:
        admin.dispose()
