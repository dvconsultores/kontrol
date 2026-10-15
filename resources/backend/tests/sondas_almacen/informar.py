"""Lo que una sonda cuenta de su almacén: rutas del entorno, de `Settings`, del proveedor documental y de las
exportaciones, y los marcadores sintéticos que ve y escribe. Cada registro es una línea JSON en `KONTROL_SONDA_INFORME`."""
import json
import os
from pathlib import Path

from app.core.config import get_settings
from app.modules.documents.storage import get_storage
from app.modules.reporting.service import _exports_dir

VARIABLE_DEL_ALMACEN, VARIABLE_DE_RESPALDOS = "KONTROL_STORAGE_PATH", "KONTROL_BACKUP_PATH"


def _raiz_documental() -> str:
    """La raíz del proveedor documental activo (el de ficheros guarda su raíz como `Path`)."""
    rutas = [v for v in vars(get_storage()).values() if isinstance(v, Path)]
    return str(rutas[0]) if rutas else ""


def marcadores(raiz: str | None) -> list[str]:
    carpeta = Path(raiz or "") / "sonda"
    return sorted(p.name for p in carpeta.iterdir()) if raiz and carpeta.is_dir() else []


def informar(modulo: str, **datos: object) -> None:
    registro = {"modulo": modulo, "pid": os.getpid(), "storage": os.environ.get(VARIABLE_DEL_ALMACEN),
                "backup": os.environ.get(VARIABLE_DE_RESPALDOS), "settings_storage": get_settings().storage_path,
                "settings_backup": get_settings().backup_path, "documentos": _raiz_documental(), "exports": str(_exports_dir()),
                **datos}
    with open(os.environ["KONTROL_SONDA_INFORME"], "a", encoding="utf-8") as fh:
        fh.write(json.dumps(registro) + "\n")


def escenario(modulo: str) -> None:
    """Lo que hace un proceso real: mira qué hay, escribe su marcador en almacén y respaldos, y lo cuenta."""
    storage, backup = os.environ[VARIABLE_DEL_ALMACEN], os.environ[VARIABLE_DE_RESPALDOS]
    vistos_storage, vistos_backup = marcadores(storage), marcadores(backup)
    for raiz in (storage, backup):
        (Path(raiz) / "sonda").mkdir(parents=True, exist_ok=True)
        (Path(raiz) / "sonda" / f"marcador-{os.getpid()}").write_text("sintetico", encoding="utf-8")
    ajena, raiz_ajena = os.environ.get("KONTROL_SONDA_RUTA_AJENA"), os.environ.get("KONTROL_SONDA_RAIZ_AJENA")
    informar(modulo, vistos_storage=vistos_storage, vistos_backup=vistos_backup,
             marcador=str(Path(storage) / "sonda" / f"marcador-{os.getpid()}"),
             marcador_respaldo=str(Path(backup) / "sonda" / f"marcador-{os.getpid()}"),
             ruta_ajena_visible=bool(ajena) and os.path.exists(ajena),
             raiz_ajena_existe=bool(raiz_ajena) and os.path.isdir(raiz_ajena))


def exportar_con_marca(modulo: str, marca: str) -> None:
    """La fórmula de nombre de `reporting.export_report` (`report-<clave>-<AAAAMMDDhhmmss>`, resolución de un
    segundo) con la marca inyectada: dos procesos que exportan en el mismo segundo producen el mismo nombre."""
    destino = _exports_dir() / f"report-executive_ventas-{marca}.csv"
    existia = destino.exists()
    contenido_previo = destino.read_text(encoding="utf-8") if existia else None
    destino.write_text(f"pid={os.getpid()}", encoding="utf-8")
    informar(modulo, file_ref=destino.name, existia=existia, contenido_previo=contenido_previo,
             contenido=destino.read_text(encoding="utf-8"))
