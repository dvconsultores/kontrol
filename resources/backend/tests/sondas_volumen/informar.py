"""Lo que una sonda cuenta de su volumen: rutas, modos y huellas sha256 truncadas de su clave sintética.
Nunca el contenido de la clave. Cada registro es una línea JSON en el fichero `KONTROL_SONDA_INFORME`."""
import hashlib
import json
import os

from conftest import make_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.database import Base, init_models
from app.modules.licensing import service as svc

CLAVE = "installation_private_key.pem"
VARIABLE = "KONTROL_INSTALLATION_VOLUME_PATH"


def huella(ruta: str) -> str:
    with open(ruta, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


def escribir_clave() -> str:
    """Inicializa una instalación sobre una base en memoria: el producto escribe la clave en el volumen configurado."""
    motor = make_engine()
    init_models()
    Base.metadata.create_all(motor)
    with sessionmaker(bind=motor, class_=Session)() as db:
        svc.get_or_create_installation(db)
    motor.dispose()
    return svc._private_key_path()


def informar(modulo: str, **datos: object) -> None:
    registro = {"modulo": modulo, "pid": os.getpid(), "volumen": os.environ.get(VARIABLE),
                "settings": get_settings().installation_volume_path, **datos}
    with open(os.environ["KONTROL_SONDA_INFORME"], "a", encoding="utf-8") as fh:
        fh.write(json.dumps(registro) + "\n")


def escenario(modulo: str, volumen: str) -> str:
    """Lo que hace un mundo real: mira el volumen, escribe su clave, la relee y lo cuenta."""
    ficheros_al_empezar = sorted(os.listdir(volumen))
    ajena = os.environ.get("KONTROL_SONDA_RUTA_AJENA")
    ruta = escribir_clave()
    informar(modulo, ficheros_al_empezar=ficheros_al_empezar, clave=ruta, clave_dentro=os.path.dirname(ruta) == volumen,
             modo=oct(os.stat(ruta).st_mode & 0o777), huella=huella(ruta),
             ruta_ajena_visible=bool(ajena) and os.path.exists(ajena))
    return ruta
