"""IBB · Base de despliegue fijada del backend (Spec 052, OD-CERT-06/07/08).

IBB-01: runtime y dev heredan la misma base fijada.
IBB-02: la referencia es patch, distro y digest completo.
IBB-03: el Python coincide con el lock y con la base certificada.
IBB-04: el digest es el del índice registrado.
IBB-05: ca-certificates fijado a la versión corregida.
IBB-06: los analizadores detectan desviaciones.
"""

from __future__ import annotations

import json
import re

from tests.test_dependencias_lock import BACKEND, RAIZ, _comando_de_cabecera
from tests.test_imagen_backend_etapas import _etapas_completas, _todas
from tests.test_imagen_backend_mime import _cadena_efectiva, _instrucciones, _paquetes_apt

FUENTE = RAIZ / "specs" / "001-fundacion" / "certified-deployment-base.json"
REFERENCIA = re.compile(r"^python:(\d+)\.(\d+)\.(\d+)-slim-([a-z]+)@sha256:([0-9a-f]{64})$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


def _fuente() -> dict:
    """Devuelve el contenido del JSON certificado de despliegue."""
    return json.loads(FUENTE.read_text(encoding="utf-8"))


def _dockerfile() -> str:
    """Devuelve el texto del Dockerfile del backend."""
    return (RAIZ / "Dockerfile.backend").read_text(encoding="utf-8")


def _imagenes_from(texto: str) -> dict[str, str]:
    """Mapa etapa -> imagen de todos los FROM."""
    imagenes: dict[str, str] = {}
    for instruccion, argumentos in _instrucciones(texto):
        if instruccion != "FROM":
            continue
        partes = re.split(r"\s+AS\s+", argumentos, flags=re.IGNORECASE)
        imagen = partes[0].strip()
        etapa = partes[1].strip() if len(partes) > 1 else imagen
        imagenes[etapa] = imagen
    return imagenes


def _imagen_raiz(texto: str, final: str) -> str:
    """Imagen del FROM de la etapa raíz de la cadena efectiva hasta final."""
    etapas, _ = _etapas_completas(texto)
    cadena = _cadena_efectiva(etapas, final)
    raiz = cadena[0]
    return _imagenes_from(texto)[raiz]


def _referencia_esperada(fuente: dict) -> str:
    """Referencia completa del Dockerfile a partir de la fuente certificada."""
    base = fuente["base_image"]
    return f'{base["repository"]}:{base["tag"]}@{base["index_digest"]}'


def _orden(c: str) -> int:
    """Orden Debian de un carácter; cadena vacía significa fin de cadena."""
    if c == "":
        return 0
    if c.isdigit():
        return 0
    if c.isascii() and c.isalpha():
        return ord(c)
    if c == "~":
        return -1
    return ord(c) + 256


def _verrevcmp(a: str, b: str) -> int:
    """Compara dos fragmentos de versión Debian según el algoritmo de dpkg."""
    i = 0
    j = 0
    while i < len(a) or j < len(b):
        diferencia = 0
        while (i < len(a) and not a[i].isdigit()) or (j < len(b) and not b[j].isdigit()):
            ca = _orden(a[i] if i < len(a) else "")
            cb = _orden(b[j] if j < len(b) else "")
            if ca != cb:
                return -1 if ca < cb else 1
            i += 1
            j += 1
        while i < len(a) and a[i] == "0":
            i += 1
        while j < len(b) and b[j] == "0":
            j += 1
        while i < len(a) and a[i].isdigit() and j < len(b) and b[j].isdigit():
            if not diferencia:
                diferencia = ord(a[i]) - ord(b[j])
            i += 1
            j += 1
        if i < len(a) and a[i].isdigit():
            return 1
        if j < len(b) and b[j].isdigit():
            return -1
        if diferencia:
            return -1 if diferencia < 0 else 1
    return 0


def _dpkg_cmp(a: str, b: str) -> int:
    """Compara dos versiones Debian completas con epoch, upstream y revisión."""
    if ":" in a:
        epoch_a, resto_a = a.split(":", 1)
    else:
        epoch_a, resto_a = "0", a
    if ":" in b:
        epoch_b, resto_b = b.split(":", 1)
    else:
        epoch_b, resto_b = "0", b

    if "-" in resto_a:
        upstream_a, revision_a = resto_a.rsplit("-", 1)
    else:
        upstream_a, revision_a = resto_a, ""
    if "-" in resto_b:
        upstream_b, revision_b = resto_b.rsplit("-", 1)
    else:
        upstream_b, revision_b = resto_b, ""

    comparacion_epoch = int(epoch_a) - int(epoch_b)
    if comparacion_epoch < 0:
        return -1
    if comparacion_epoch > 0:
        return 1

    comparacion_upstream = _verrevcmp(upstream_a, upstream_b)
    if comparacion_upstream != 0:
        return comparacion_upstream

    return _verrevcmp(revision_a, revision_b)


def _version_pin(run: str, paquete: str) -> list[str]:
    """Tokens apt completos de un paquete, con o sin versión fijada."""
    tokens: list[str] = []
    for token in _paquetes_apt(run):
        if token == paquete or token.startswith(f"{paquete}="):
            tokens.append(token)
    return tokens


def test_ibb_01_runtime_y_dev_heredan_la_misma_base_fijada() -> None:
    """La raíz, y por tanto runtime y dev, usan la referencia esperada."""
    texto = _dockerfile()
    fuente = _fuente()
    _, final = _etapas_completas(texto)
    assert _imagen_raiz(texto, final) == _referencia_esperada(fuente)
    assert _imagen_raiz(texto, "dev") == _imagen_raiz(texto, final)
    assert final == "runtime"


def test_ibb_02_la_referencia_es_patch_distro_y_digest_completo() -> None:
    """La referencia raíz es completa, con distro trixie y sin otra base Python."""
    texto = _dockerfile()
    fuente = _fuente()
    _, final = _etapas_completas(texto)
    referencia = _imagen_raiz(texto, final)
    coincidencia = REFERENCIA.match(referencia)
    assert coincidencia is not None
    distro = coincidencia.group(4)
    assert distro in fuente["base_image"]["distro"]
    assert all("latest" not in imagen for imagen in _imagenes_from(texto).values())
    assert all(imagen == referencia for imagen in _imagenes_from(texto).values() if imagen.startswith("python:"))


def test_ibb_03_el_python_coincide_con_el_lock_y_con_la_base_certificada() -> None:
    """La versión de Python de la imagen casa con lock y fuente certificada."""
    texto = _dockerfile()
    fuente = _fuente()
    _, final = _etapas_completas(texto)
    referencia = _imagen_raiz(texto, final)
    coincidencia = REFERENCIA.match(referencia)
    assert coincidencia is not None
    mayor, menor, parche = coincidencia.group(1), coincidencia.group(2), coincidencia.group(3)
    version_imagen = f"{mayor}.{menor}.{parche}"
    comando = _comando_de_cabecera((BACKEND / "requirements.lock").read_text(encoding="utf-8"))
    version_lock = comando.rsplit("--python-version", 1)[1].strip().split()[0]
    assert f"{mayor}.{menor}" == version_lock
    assert version_imagen == fuente["base_image"]["cpython"]
    assert version_imagen == fuente["deployment_interpreter_baseline"]["cpython"]
    assert referencia.split("@")[0].split(":", 1)[1].startswith(version_imagen + "-")


def test_ibb_04_el_digest_es_el_del_indice_registrado() -> None:
    """El digest del Dockerfile es el índice OCI y no el manifiesto amd64."""
    texto = _dockerfile()
    fuente = _fuente()
    _, final = _etapas_completas(texto)
    referencia = _imagen_raiz(texto, final)
    base = fuente["base_image"]
    digests = [base["index_digest"], base["platform_manifest_digest"], base["config_digest"]]
    assert all(DIGEST.fullmatch(digest) for digest in digests)
    assert base["digest_semantics"] == "oci-image-index"
    assert base["platform"] == "linux/amd64"
    assert referencia.endswith(base["index_digest"])
    assert base["index_digest"] != base["platform_manifest_digest"]


def test_ibb_05_ca_certificates_fijado_a_la_version_corregida() -> None:
    """El RUN raíz fija ca-certificates exactamente a la versión corregida."""
    texto = _dockerfile()
    fuente = _fuente()
    etapas, final = _etapas_completas(texto)
    cadena = _cadena_efectiva(etapas, final)
    runs_raiz = _todas(etapas, [cadena[0]], "RUN")
    run_apt = [run for run in runs_raiz if _version_pin(run, "ca-certificates")]
    assert len(run_apt) == 1
    tokens_ca = _version_pin(run_apt[0], "ca-certificates")
    pinned = fuente["ca_certificates"]["pinned_version"]
    fixed_floor = fuente["ca_certificates"]["fixed_floor"]
    vulnerable = fuente["ca_certificates"]["vulnerable_version"]
    assert tokens_ca == [f"ca-certificates={pinned}"]
    assert _dpkg_cmp(pinned, fixed_floor) >= 0
    assert _dpkg_cmp(pinned, vulnerable) > 0
    assert len(_version_pin(run_apt[0], "libmagic1t64")) == 1
    assert all("=" in token for token in tokens_ca)
    runs_dev = _todas(etapas, _cadena_efectiva(etapas, "dev"), "RUN")
    assert any(run == run_apt[0] for run in runs_dev)


def test_ibb_06_los_analizadores_detectan_desviaciones() -> None:
    """Vectores sintéticos de _dpkg_cmp, REFERENCIA, _imagen_raiz y _version_pin."""
    vectores = [
        ("20250419+deb13u1", "20250419", 1),
        ("20250419", "20250419+deb13u1", -1),
        ("20250419+deb13u10", "20250419+deb13u9", 1),
        ("1.0~rc1", "1.0", -1),
        ("2:1.0", "1:9.9", 1),
        ("1.0-1", "1.0-2", -1),
        ("20250419+deb13u1", "20250419+deb13u1", 0),
    ]
    for a, b, esperado in vectores:
        assert _dpkg_cmp(a, b) == esperado
    invalidas = [
        "python:3.13-slim",
        "python:latest",
        "python:3.13.16-slim",
        "python:3.13.16-slim-trixie@sha256:70729b46",
        "python:3.13.16-trixie@sha256:" + "a" * 64,
    ]
    for referencia in invalidas:
        assert REFERENCIA.match(referencia) is None
    sintetico = "FROM python:3.13.16-slim-trixie@sha256:" + "a" * 64 + " AS base\nFROM python:3.13-slim AS dev\nFROM base AS runtime\n"
    assert _imagen_raiz(sintetico, "dev") != _imagen_raiz(sintetico, "runtime")
    assert _version_pin("apt-get install -y --no-install-recommends curl ca-certificates libmagic1t64", "ca-certificates") == ["ca-certificates"]
