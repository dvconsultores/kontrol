"""Pruebas de imagen del backend: detección MIME por contenido (IMB-01…IMB-07)."""

from __future__ import annotations

import ctypes
import ctypes.util
import importlib.metadata
import re
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
RAIZ = BACKEND.parents[1]


def _instrucciones(texto: str) -> list[tuple[str, str]]:
    """Devuelve instrucciones Docker sin comentarios ni líneas vacías, uniendo continuaciones."""
    instrucciones: list[tuple[str, str]] = []
    actual = ""
    for linea in texto.splitlines():
        limpia = linea.strip()
        if not limpia or limpia.startswith("#"):
            continue
        if actual:
            actual = actual + " " + limpia
        else:
            actual = limpia
        if actual.endswith("\\"):
            actual = actual[:-1].rstrip()
            continue
        instruccion, _, argumentos = actual.partition(" ")
        instrucciones.append((instruccion.upper(), argumentos.strip()))
        actual = ""
    if actual:
        instruccion, _, argumentos = actual.partition(" ")
        instrucciones.append((instruccion.upper(), argumentos.strip()))
    return instrucciones


def _etapas(texto: str) -> tuple[dict[str, dict], str]:
    """Registra etapas del Dockerfile y devuelve la información de la última etapa."""
    etapas: dict[str, dict] = {}
    orden_etapas: list[str] = []
    nombres_declarados: set[str] = set()
    for instruccion, argumentos in _instrucciones(texto):
        if instruccion != "FROM":
            if instruccion == "RUN" and orden_etapas:
                etapas[orden_etapas[-1]]["runs"].append(argumentos)
            continue
        partes = re.split(r"\s+AS\s+", argumentos, flags=re.IGNORECASE)
        imagen = partes[0].strip()
        nombre = partes[1].strip() if len(partes) > 1 else imagen
        padre = imagen if imagen in nombres_declarados else None
        etapas[nombre] = {"padre": padre, "runs": []}
        orden_etapas.append(nombre)
        nombres_declarados.add(nombre)
    final = orden_etapas[-1] if orden_etapas else ""
    return etapas, final


def _cadena_efectiva(etapas: dict[str, dict], final: str) -> list[str]:
    """Devuelve la cadena de etapas desde la raíz hasta la etapa final."""
    cadena: list[str] = []
    vistos: set[str] = set()
    etapa: str | None = final
    while etapa is not None:
        if etapa in vistos:
            raise RuntimeError("Ciclo detectado en la cadena de etapas")
        vistos.add(etapa)
        cadena.append(etapa)
        etapa = etapas[etapa].get("padre")
    cadena.reverse()
    return cadena


def _paquetes_apt(run: str) -> set[str]:
    """Devuelve los paquetes instalados con apt-get install o apt install."""
    paquetes: set[str] = set()
    for orden in re.split(r"\s*(?:&&|;)\s*", run):
        if re.match(r"^(?:apt-get\s+install|apt\s+install)\b", orden):
            partes = orden.split()
            for parte in partes[2:]:
                if not parte.startswith("-"):
                    paquetes.add(parte)
    return paquetes


def test_imb_01_python_magic_declarado_y_fijado() -> None:
    """La dependencia python-magic está declarada una única vez y fijada con versión exacta."""
    ruta = BACKEND / "requirements.txt"
    lineas = [
        linea.strip()
        for linea in ruta.read_text().splitlines()
        if linea.strip() and not linea.strip().startswith("#")
    ]
    coincidencias = [
        linea for linea in lineas if re.match(r"^python-magic==\d+\.\d+\.\d+$", linea)
    ]
    assert len(coincidencias) == 1, f"Se esperaba exactamente una declaración fijada, encontradas: {coincidencias}"


def test_imb_02_la_version_instalada_es_la_declarada() -> None:
    """La versión instalada de python-magic coincide con la declarada en requirements.txt."""
    ruta = BACKEND / "requirements.txt"
    declarada = next(
        linea.strip().split("==")[1]
        for linea in ruta.read_text().splitlines()
        if linea.strip() and re.match(r"^python-magic==\d+\.\d+\.\d+$", linea.strip())
    )
    instalada = importlib.metadata.version("python-magic")
    assert instalada == declarada, f"Declarada {declarada}, instalada {instalada}"


def test_imb_03_la_etapa_efectiva_hereda_libmagic() -> None:
    """La cadena efectiva de etapas instala libmagic1t64 y las dependencias Python."""
    dockerfile = RAIZ / "Dockerfile.backend"
    etapas, final = _etapas(dockerfile.read_text())
    cadena = _cadena_efectiva(etapas, final)
    runs = [run for etapa in cadena for run in etapas[etapa]["runs"]]

    run_libmagic = None
    for run in runs:
        if "libmagic1t64" in _paquetes_apt(run):
            run_libmagic = run
            break
    assert run_libmagic is not None, (
        "libmagic1t64 no se instala en la cadena efectiva de etapas; "
        "solo aparece en etapas fuera de la cadena"
    )
    assert "--no-install-recommends" in run_libmagic

    assert any("pip install --no-cache-dir -r /tmp/requirements.txt" in run for run in runs)


def test_imb_04_la_biblioteca_nativa_carga() -> None:
    """La biblioteca nativa libmagic está disponible y cargada por python-magic."""
    assert ctypes.util.find_library("magic") is not None
    import magic

    ruta_magic = Path(magic.__file__)
    assert ruta_magic.exists()
    assert "site-packages" in str(ruta_magic)
    assert isinstance(magic.libmagic, ctypes.CDLL)


def test_imb_05_la_base_de_firmas_responde() -> None:
    """La base de firmas detecta PDF y texto plano por contenido."""
    import magic

    pdf = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    texto = b"texto plano de prueba\n"
    detector = magic.Magic(mime=True)
    assert detector.from_buffer(pdf) == "application/pdf"
    assert detector.from_buffer(texto) == "text/plain"


def test_imb_06_detect_mime_usa_el_contenido_no_la_extension(tmp_path: Path) -> None:
    """detect_mime detecta por contenido, sin depender de la extensión."""
    from app.modules.documents.service import detect_mime

    pdf = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    texto = b"texto plano de prueba\n"
    ruta_pdf = tmp_path / "sin_extension"
    ruta_texto = tmp_path / "otro.bin"
    ruta_pdf.write_bytes(pdf)
    ruta_texto.write_bytes(texto)

    mime_pdf = detect_mime(str(ruta_pdf))
    mime_texto = detect_mime(str(ruta_texto))
    assert mime_pdf == "application/pdf"
    assert mime_texto == "text/plain"
    assert mime_pdf != "application/octet-stream"
    assert mime_texto != "application/octet-stream"


def test_imb_07_pip_check_limpio() -> None:
    """pip check termina correctamente, sin dependencias rotas."""
    resultado = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultado.returncode == 0, f"pip check falló. stdout: {resultado.stdout}"
