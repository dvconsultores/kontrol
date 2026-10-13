"""SPEC054 · TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO.

Verifica en proceso el gestor de contexto ``volumen_de_instalacion_aislado`` del
conftest de pruebas del backend: que el volumen hijo nace vacío, que los settings
apuntan al volumen del ámbito, que el ámbito no conserva el volumen anterior, que
al salir se restauran variable de entorno y settings, que el volumen desaparece
también si dentro hubo una excepción y que la clave privada sintética nace dentro
del volumen con permisos 0600 y muere con él.

Cubre FR-TV-004, FR-TV-005, FR-TV-008 y FR-TV-011.
"""
from __future__ import annotations

import os
import stat

import pytest
from conftest import RAIZ_DEL_VOLUMEN, VARIABLE_DEL_VOLUMEN, make_engine, volumen_de_instalacion_aislado
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.database import Base, init_models
from app.modules.licensing import service as svc


@pytest.fixture()
def raiz(request: pytest.FixtureRequest) -> str:
    """Devuelve la raíz única del volumen de este proceso de pruebas."""
    return request.config.stash[RAIZ_DEL_VOLUMEN]


def _crear_instalacion() -> None:
    """Crea la instalación sobre una base en memoria usando el volumen del ámbito."""
    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    try:
        with sessionmaker(bind=engine, class_=Session, expire_on_commit=False)() as db:
            svc.get_or_create_installation(db)
    finally:
        engine.dispose()


def test_tv_02b_el_volumen_hijo_empieza_vacio(raiz: str) -> None:
    """El volumen del ámbito nace vacío, es un directorio hijo de la raíz y lleva su prefijo."""
    with volumen_de_instalacion_aislado(raiz, "tv02b") as volumen:
        assert os.listdir(volumen) == []
        assert os.path.isdir(volumen)
        assert os.path.dirname(volumen) == raiz
        assert os.path.basename(volumen).startswith("tv02b-")


def test_tv_05_los_settings_apuntan_al_volumen_del_ambito(raiz: str) -> None:
    """Dentro del ámbito, variable de entorno, settings y ruta de la clave apuntan al volumen."""
    with volumen_de_instalacion_aislado(raiz, "tv05") as volumen:
        assert os.environ[VARIABLE_DEL_VOLUMEN] == volumen
        assert get_settings().installation_volume_path == volumen
        assert svc._private_key_path() == os.path.join(
            volumen, svc.INSTALLATION_PRIVATE_KEY_FILENAME
        )
        assert volumen != raiz


def test_tv_06_al_cambiar_de_ambito_los_settings_no_conservan_el_anterior(raiz: str) -> None:
    """Al cambiar de ámbito, los settings reflejan el nuevo volumen y no el anterior."""
    with volumen_de_instalacion_aislado(raiz, "tv06a") as volumen_a:
        assert get_settings().installation_volume_path == volumen_a
    with volumen_de_instalacion_aislado(raiz, "tv06b") as volumen_b:
        assert get_settings().installation_volume_path == volumen_b
        assert get_settings().installation_volume_path != volumen_a
        with volumen_de_instalacion_aislado(raiz, "tv06c") as a_externo:
            with volumen_de_instalacion_aislado(raiz, "tv06d") as b_interno:
                assert get_settings().installation_volume_path == b_interno
                assert b_interno != a_externo
            assert get_settings().installation_volume_path == a_externo


def test_tv_07_al_salir_la_variable_y_los_settings_vuelven_a_como_estaban(
    raiz: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Al salir del ámbito se restauran la variable de entorno y los settings previos."""
    anterior = os.environ[VARIABLE_DEL_VOLUMEN]
    with volumen_de_instalacion_aislado(raiz, "tv07a") as volumen:
        assert get_settings().installation_volume_path == volumen
    assert os.environ[VARIABLE_DEL_VOLUMEN] == anterior
    assert get_settings().installation_volume_path == anterior

    monkeypatch.delenv(VARIABLE_DEL_VOLUMEN)
    get_settings.cache_clear()
    with volumen_de_instalacion_aislado(raiz, "tv07b"):
        pass
    assert VARIABLE_DEL_VOLUMEN not in os.environ
    get_settings.cache_clear()


def test_tv_08_al_salir_el_volumen_desaparece_tambien_si_dentro_hubo_una_excepcion(
    raiz: str,
) -> None:
    """El volumen se elimina al salir, tanto en salida normal como con excepción."""
    anterior = os.environ.get(VARIABLE_DEL_VOLUMEN)
    with volumen_de_instalacion_aislado(raiz, "tv08a") as volumen:
        assert os.path.isdir(volumen)
    assert not os.path.exists(volumen)

    with pytest.raises(RuntimeError):
        with volumen_de_instalacion_aislado(raiz, "tv08b") as volumen:
            open(os.path.join(volumen, "x"), "w").close()
            raise RuntimeError("fallo dentro del ámbito")
    assert not os.path.exists(volumen)
    assert os.environ.get(VARIABLE_DEL_VOLUMEN) == anterior


def test_tv_10_la_clave_sintetica_nace_dentro_del_volumen_con_0600_y_muere_con_el(
    raiz: str,
) -> None:
    """La clave privada sintética nace dentro del volumen con 0600 y muere con él."""
    with volumen_de_instalacion_aislado(raiz, "tv10") as volumen:
        _crear_instalacion()
        ruta = svc._private_key_path()
        assert os.path.dirname(ruta) == volumen
        assert os.path.exists(ruta)
        assert stat.S_IMODE(os.stat(ruta).st_mode) == 0o600
        assert os.listdir(volumen) == [svc.INSTALLATION_PRIVATE_KEY_FILENAME]
    assert not os.path.exists(ruta)
