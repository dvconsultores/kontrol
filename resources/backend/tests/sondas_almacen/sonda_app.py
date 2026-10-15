"""Sonda de aplicación: la aplicación entera (`create_app` + `TestClient`) y, después, la configuración ven la raíz del proceso."""
from fastapi.testclient import TestClient
from informar import informar

from app.core.config import get_settings
from app.main import create_app


def test_la_app_ve_la_raiz_del_proceso():
    with TestClient(create_app()) as cliente:
        salud = cliente.get("/api/v1/health/live").status_code
    informar(__name__, salud=salud, settings_tras_app=get_settings().storage_path)
