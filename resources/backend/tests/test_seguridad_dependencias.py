"""SDV · Piso de seguridad de las dependencias directas de autenticación y criptografía (Spec 001, OD-SEC-02).

- SDV-01 los pines de seguridad no bajan del piso y coinciden con el lock;
- SDV-02 el piso documentado coincide con el ratificado y con el pin;
- SDV-03 cada aviso revisado está corregido por el pin o no tiene parche ni aplica;
- SDV-04 no hay exclusiones de avisos en el repositorio;
- SDV-05 el contrato JWT responde 401 y nunca 500;
- SDV-06 la verificación JWT usa una lista explícita de un algoritmo;
- SDV-07 una clave vacía o corta impide arrancar;
- SDV-08 los suelos de seguridad de dependencias transitivas se cumplen sin convertirlas en directas.
"""

from __future__ import annotations

import ast
import base64
import json
import re
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from packaging.version import Version
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.main import create_app
from tests.test_dependencias_lock import BACKEND, RAIZ, SUELOS_CVE, _canonico, _comando_de_cabecera, _pines

PAQUETES_SEGURIDAD = ("pyjwt", "cryptography")
CVE_REVIEW = RAIZ / "docs" / "evidence" / "cve-review.md"
SUJETO = "00000000-0000-0000-0000-000000000000"
CLAVE_AJENA = "clave-sintetica-de-prueba-ajena-" + "x" * 16
PATRONES_EXCLUSION = ("--ignore-vuln", "ignore-vulns", "PIP_AUDIT_IGNORE")
NOMBRES_PROHIBIDOS = frozenset({"PyJWK", "PyJWKClient", "PyJWKSet", "decode_complete", "get_unverified_header", "get_unverified_claims"})

_SUFIJOS_FICHERO = {".yml", ".yaml", ".py", ".sh", ".toml", ".cfg", ".ini"}


def _b64(datos: bytes) -> str:
    """Codifica en base64 urlsafe sin relleno `=`."""
    return base64.urlsafe_b64encode(datos).decode().rstrip("=")


def _tabla(texto: str, titulo: str) -> list[dict[str, str]]:
    """Extrae la primera tabla Markdown posterior al título exacto."""
    lineas = texto.splitlines()
    indice = next((i for i, linea in enumerate(lineas) if linea.strip() == "### " + titulo), None)
    assert indice is not None, f"No se encontró el título {titulo!r}"
    resto = lineas[indice + 1 :]
    indice_cabecera = next((i for i, linea in enumerate(resto) if linea.startswith("|")), None)
    assert indice_cabecera is not None, f"No se encontró la cabecera de la tabla posterior a {titulo!r}"
    cabecera = [celda.strip() for celda in resto[indice_cabecera].strip().strip("|").split("|")]
    assert resto[indice_cabecera + 1].replace("|", "").replace("-", "").strip() == ""
    filas = []
    for linea in resto[indice_cabecera + 2 :]:
        if not linea.startswith("|"):
            break
        celdas = [celda.strip() for celda in linea.strip().strip("|").split("|")]
        filas.append(dict(zip(cabecera, celdas, strict=True)))
    assert filas, f"La tabla posterior a {titulo!r} no tiene filas"
    return filas


def _pines_manifiesto() -> dict[str, str]:
    """Pines exactos del manifiesto de dependencias."""
    return _pines((BACKEND / "requirements.txt").read_text(encoding="utf-8"))


def _pines_lock() -> dict[str, str]:
    """Pines exactos del lock de dependencias."""
    return _pines((BACKEND / "requirements.lock").read_text(encoding="utf-8"))


def _token(**cambios: object) -> str:
    """Crea un token JWT con claims base y los cambios indicados."""
    clave = cambios.pop("clave", get_settings().secret_key)
    algoritmo = cambios.pop("algoritmo", get_settings().jwt_algorithm)
    payload = {"sub": SUJETO, "type": "access", "exp": datetime.now(UTC) + timedelta(minutes=5)}
    payload.update(cambios)
    return jwt.encode(payload, clave, algorithm=algoritmo)


def _sin_firma(alg: str) -> str:
    """Crea un token JWT con la firma vacía y el algoritmo indicado."""
    cabecera = _b64(json.dumps({"alg": alg, "typ": "JWT"}).encode())
    payload = _b64(json.dumps({"sub": SUJETO, "type": "access"}).encode())
    return cabecera + "." + payload + "."


def _llamadas_decode(arbol: ast.AST) -> list[ast.Call]:
    """Devuelve las llamadas a decode sobre jwt o pyjwt."""
    llamadas = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute):
            if nodo.func.attr == "decode" and isinstance(nodo.func.value, ast.Name):
                if nodo.func.value.id in {"jwt", "pyjwt"}:
                    llamadas.append(nodo)
    return llamadas


@pytest.fixture(scope="module")
def cliente() -> Iterator[TestClient]:
    """Cliente de pruebas HTTP sin propagar excepciones del servidor."""
    with TestClient(create_app(), raise_server_exceptions=False) as cliente:
        yield cliente


def test_sdv_01_los_pines_de_seguridad_no_bajan_del_piso_y_coinciden_con_el_lock() -> None:
    """SDV-01 los pines de seguridad no bajan del piso y coinciden con el lock."""
    manifiesto = _pines_manifiesto()
    lock = _pines_lock()
    for p in PAQUETES_SEGURIDAD:
        assert p in manifiesto, f"Falta {p} en requirements.txt"
        assert p in lock, f"Falta {p} en requirements.lock"
        assert manifiesto[p] == lock[p], f"{p}: manifiesto {manifiesto[p]!r} no coincide con lock {lock[p]!r}"
        assert Version(manifiesto[p]) >= Version(SUELOS_CVE[p]), f"{p} {manifiesto[p]} baja del suelo {SUELOS_CVE[p]}"


def test_sdv_02_el_piso_documentado_coincide_con_el_ratificado_y_con_el_pin() -> None:
    """SDV-02 el piso documentado coincide con el ratificado y con el pin."""
    filas = _tabla(CVE_REVIEW.read_text(encoding="utf-8"), "Piso de seguridad vigente")
    filas_por_paquete = {_canonico(fila["Paquete"]): fila for fila in filas}
    manifiesto = _pines_manifiesto()
    for p in PAQUETES_SEGURIDAD:
        assert p in filas_por_paquete, f"Falta la fila del piso de {p} en cve-review.md"
        fila = filas_por_paquete[p]
        assert fila["Piso de seguridad"] == SUELOS_CVE[p], f"{p}: piso documentado {fila['Piso de seguridad']!r} no coincide con {SUELOS_CVE[p]!r}"
        assert fila["Versión fijada"] == manifiesto[p], f"{p}: versión fijada {fila['Versión fijada']!r} no coincide con {manifiesto[p]!r}"


def test_sdv_03_cada_aviso_revisado_esta_corregido_por_el_pin_o_no_tiene_parche_ni_aplica() -> None:
    """SDV-03 cada aviso revisado está corregido por el pin o no tiene parche ni aplica."""
    filas = _tabla(CVE_REVIEW.read_text(encoding="utf-8"), "Avisos backend revisados")
    avisos = [fila["Aviso"] for fila in filas]
    assert len(avisos) == len(set(avisos)), "Hay avisos duplicados en cve-review.md"
    manifiesto = _pines_manifiesto()
    for p in PAQUETES_SEGURIDAD:
        assert any(_canonico(fila["Paquete"]) == p for fila in filas), f"Falta al menos una fila de avisos de {p}"
    for fila in filas:
        paquete = _canonico(fila["Paquete"])
        assert paquete in manifiesto, f"Paquete de aviso sin pin: {paquete}"
        assert fila["Parche"] in {"sí", "no"}, f"Parche inválido en {fila['Aviso']}"
        assert fila["Aplicable a KONTROL"] in {"sí", "no"}, f"Aplicable inválido en {fila['Aviso']}"
        if fila["Parche"] == "sí":
            assert Version(manifiesto[paquete]) >= Version(fila["Corregida en"]), f"{fila['Aviso']}: {paquete} {manifiesto[paquete]} no alcanza la corregida {fila['Corregida en']}"
        else:
            assert fila["Aplicable a KONTROL"] == "no", f"OWNER_RISK_DECISION_REQUIRED: {fila['Aviso']} no tiene parche y aplica"


def test_sdv_04_no_hay_exclusiones_de_avisos_en_el_repositorio() -> None:
    """SDV-04 no hay exclusiones de avisos en el repositorio."""
    ficheros = [BACKEND / "pyproject.toml", *RAIZ.glob("Dockerfile*")]
    for raiz in (RAIZ / ".github", RAIZ / "qa", BACKEND / "scripts"):
        if not raiz.exists():
            continue
        ficheros.extend(ruta for ruta in raiz.rglob("*") if ruta.is_file() and (ruta.suffix in _SUFIJOS_FICHERO or ruta.name.startswith("Dockerfile")))
    exclusiones = []
    for ruta in ficheros:
        if not ruta.is_file():
            continue
        texto = ruta.read_text(encoding="utf-8", errors="ignore")
        for patron in PATRONES_EXCLUSION:
            if patron in texto:
                exclusiones.append(f"{ruta.relative_to(RAIZ)} contiene {patron!r}")
    assert not exclusiones, "; ".join(exclusiones)


@pytest.mark.parametrize(
    "caso,token",
    [
        pytest.param("firma_ajena", lambda: _token(clave=CLAVE_AJENA), id="firma-ajena"),
        pytest.param("algoritmo_distinto", lambda: _token(algoritmo="HS512"), id="algoritmo-distinto"),
        pytest.param("alg_none", lambda: _sin_firma("none"), id="alg-none"),
        pytest.param("alg_NONE", lambda: _sin_firma("NONE"), id="alg-NONE"),
        pytest.param("caducado", lambda: _token(exp=datetime.now(UTC) - timedelta(minutes=1)), id="caducado"),
        pytest.param("malformado", lambda: "no.es.un.token", id="malformado"),
        pytest.param("cabecera_no_objeto", lambda: _b64(b"[]") + "." + ".".join(_token().split(".")[1:]), id="cabecera-no-objeto"),
        pytest.param("refresh_como_access", lambda: _token(type="refresh"), id="refresh-como-access"),
    ],
)
def test_sdv_05_el_contrato_jwt_responde_401_y_nunca_500(caso: str, token: Callable[[], str], cliente: TestClient) -> None:
    """SDV-05 el contrato JWT responde 401 y nunca 500."""
    assert get_settings().jwt_algorithm == "HS256"
    valor = token()
    r = cliente.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {valor}"})
    assert r.status_code == 401, f"{caso}: status {r.status_code}, body {r.text}"
    assert r.json()["code"] == "AUTH_INVALID_TOKEN", f"{caso}: body {r.text}"


def test_sdv_06_la_verificacion_jwt_usa_una_lista_explicita_de_un_algoritmo() -> None:
    """SDV-06 la verificación JWT usa una lista explícita de un algoritmo."""
    llamadas = []
    nombres_prohibidos_encontrados = []
    constantes_prohibidas = []
    palabras_prohibidas = []
    for ruta in (BACKEND / "app").rglob("*.py"):
        arbol = ast.parse(ruta.read_text(encoding="utf-8"))
        llamadas.extend(_llamadas_decode(arbol))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Name) and nodo.id in NOMBRES_PROHIBIDOS:
                nombres_prohibidos_encontrados.append((ruta, nodo.id, nodo.lineno))
            elif isinstance(nodo, ast.Attribute) and nodo.attr in NOMBRES_PROHIBIDOS:
                nombres_prohibidos_encontrados.append((ruta, nodo.attr, nodo.lineno))
            elif isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
                if nodo.value == "verify_signature":
                    constantes_prohibidas.append((ruta, nodo.lineno))
            if isinstance(nodo, ast.keyword) and nodo.arg == "verify_signature":
                palabras_prohibidas.append((ruta, nodo.lineno))
    assert llamadas, "No se encontró ninguna llamada a jwt.decode"
    for llamada in llamadas:
        assert any(k.arg == "algorithms" for k in llamada.keywords), f"Falta algorithms en la llamada a decode (línea {llamada.lineno})"
        algorithms = next(k.value for k in llamada.keywords if k.arg == "algorithms")
        assert isinstance(algorithms, ast.List), "algorithms debe ser una lista literal"
        assert len(algorithms.elts) == 1, "algorithms debe tener exactamente un elemento"
        assert not any(k.arg == "options" for k in llamada.keywords), f"La llamada a decode no debe usar options (línea {llamada.lineno})"
    assert not nombres_prohibidos_encontrados, f"Nombres prohibidos: {nombres_prohibidos_encontrados}"
    assert not constantes_prohibidas, f"Constantes prohibidas: {constantes_prohibidas}"
    assert not palabras_prohibidas, f"Palabras clave prohibidas: {palabras_prohibidas}"
    assert Settings.model_fields["jwt_algorithm"].default == "HS256"


def test_sdv_07_una_clave_vacia_o_corta_impide_arrancar() -> None:
    """SDV-07 una clave vacía o corta impide arrancar."""
    with pytest.raises(ValidationError):
        Settings(secret_key="")
    with pytest.raises(ValidationError):
        Settings(secret_key="k" * 31)
    assert Settings(secret_key="k" * 32).secret_key == "k" * 32


def _instante(texto: str) -> datetime:
    """Instante ISO 8601 con sufijo Z como datetime con zona UTC."""
    return datetime.fromisoformat(texto.replace("Z", "+00:00"))


def test_sdv_08_los_suelos_de_transitivas_se_cumplen_sin_volverlas_directas() -> None:
    """SDV-08 los suelos de seguridad de dependencias transitivas se cumplen sin convertirlas en directas."""
    filas = _tabla(CVE_REVIEW.read_text(encoding="utf-8"), "Avisos de dependencias transitivas")
    assert filas
    lock = _pines_lock()
    manifiesto = _pines_manifiesto()
    comando = _comando_de_cabecera((BACKEND / "requirements.lock").read_text(encoding="utf-8"))
    corte = re.search(r"--exclude-newer (\S+)", comando)
    assert corte is not None
    instante_corte = _instante(corte.group(1))
    for fila in filas:
        paquete = _canonico(fila["Paquete"])
        assert paquete in lock, f"{fila['Aviso']}: {paquete} no está en el lock"
        assert paquete not in manifiesto, f"{paquete} es transitiva con suelo: no debe ser dependencia directa"
        limite = re.search(r"<\s*([0-9][^\s,]*)", fila["Afectadas"])
        assert limite is not None
        corregida = fila["Corregida en"]
        assert Version(corregida) >= Version(limite.group(1)), "la corregida debe quedar fuera del rango afectado"
        assert Version(lock[paquete]) >= Version(corregida), f"{paquete}: lock {lock[paquete]} < suelo {corregida}"
        assert instante_corte > _instante(fila["Publicación de la corregida (UTC)"]), "el corte del lock es anterior a la publicación de la corregida"
