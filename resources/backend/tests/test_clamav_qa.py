"""CLAM-01…15 · ClamAV real en el QA canónico sin privilegios (`qa/clamav_qa.py`; Spec 046, apoyo 054).

Lo que no necesita el analizador real se prueba con dobles **del aprovisionamiento** (descarga, extracción, firmas),
nunca del análisis: el preflight y los escaneos reales corren cuando `KONTROL_CLAMSCAN_PATH` apunta al analizador
provisionado, con el mismo marcador que ya usan las pruebas EICAR de `test_documents.py`.
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "qa"))

import clamav_qa  # noqa: E402

REAL = os.environ.get("KONTROL_CLAMSCAN_PATH")
con_analizador_real = pytest.mark.skipif(not REAL, reason="Sin analizador real: la Spec no se acepta con simulación")


def _binario_falso(prefijo: Path, version: str = "ClamAV 1.4.3", rc_escaneo: int = 0) -> None:
    """Un `clamscan` de mentira para probar el aprovisionamiento, no el análisis."""
    bin_real = prefijo / "usr" / "bin"
    bin_real.mkdir(parents=True, exist_ok=True)
    (prefijo / "usr" / "lib" / clamav_qa.ARQUITECTURA).mkdir(parents=True, exist_ok=True)
    for programa in ("clamscan", "freshclam", "sigtool"):
        f = bin_real / programa
        f.write_text("#!/bin/sh\n" f'[ "$1" = "--version" ] && {{ echo "{version}"; exit 0; }}\n' f"exit {rc_escaneo}\n", encoding="utf-8")
        f.chmod(f.stat().st_mode | stat.S_IXUSR)


def _firmas_falsas(rutas: clamav_qa.Rutas) -> None:
    rutas.db.mkdir(parents=True, exist_ok=True)
    for nombre in clamav_qa.BASES:
        (rutas.db / f"{nombre}.cvd").write_bytes(b"ClamAV-VDB:fixture")


def _provisionar_con_dobles(home: Path, version: str = "ClamAV 1.4.3", descargas: list | None = None) -> clamav_qa.Rutas:
    descargas = [] if descargas is None else descargas

    def descargar(destino: Path) -> list[Path]:
        descargas.append(destino)
        destino.mkdir(parents=True, exist_ok=True)
        return [destino / "clamav_1.4.3_amd64.deb"]

    def extraer(ficheros: list[Path], prefijo: Path) -> None:
        _binario_falso(prefijo, version)

    return clamav_qa.provisionar(home, descargar=descargar, extraer=extraer, firmas=_firmas_falsas)


# CLAM-01 · el aprovisionamiento no usa sudo ni instala nada en el sistema: todo cae en el prefijo.
def test_clam_01_el_aprovisionamiento_escribe_solo_en_el_prefijo_y_sin_privilegios(tmp_path):
    rutas = _provisionar_con_dobles(tmp_path / "home")
    assert rutas.clamscan.exists() and os.access(rutas.clamscan, os.X_OK)
    assert rutas.home.is_relative_to(tmp_path)
    assert clamav_qa.motor_disponible(rutas) == "1.4.3"
    assert sorted(p.name for p in rutas.db.iterdir()) == ["bytecode.cvd", "daily.cvd", "main.cvd"]


# CLAM-02 · idempotente: con caché válida no se vuelve a descargar.
def test_clam_02_con_cache_valida_no_se_descarga_de_nuevo(tmp_path):
    descargas: list = []
    _provisionar_con_dobles(tmp_path / "home", descargas=descargas)
    _provisionar_con_dobles(tmp_path / "home", descargas=descargas)
    assert len(descargas) == 1


# CLAM-03 · solo se acepta la versión semántica certificada (1.4.x).
def test_clam_03_una_version_distinta_de_la_certificada_no_se_acepta(tmp_path):
    with pytest.raises(clamav_qa.AnalizadorNoListo, match="1.4.x"):
        _provisionar_con_dobles(tmp_path / "home", version="ClamAV 1.5.0")


# CLAM-07 · sin binario, el preflight falla y lo dice.
def test_clam_07_sin_binario_el_preflight_falla(tmp_path):
    with pytest.raises(clamav_qa.AnalizadorNoListo, match="QAC-01/02"):
        clamav_qa.preflight(tmp_path / "vacio")


# CLAM-08 · con binario y sin firmas, el preflight falla y nombra lo que falta.
def test_clam_08_sin_firmas_el_preflight_falla(tmp_path):
    rutas = clamav_qa.Rutas(tmp_path / "home")
    _binario_falso(rutas.prefijo)
    clamav_qa.escribir_envoltorios(rutas)
    with pytest.raises(clamav_qa.AnalizadorNoListo, match="QAC-03: faltan firmas"):
        clamav_qa.preflight(rutas.home)


# CLAM-10c · un analizador que ignora la base de firmas (responde igual con y sin ella) no pasa QAC-06:
# «disponible» no es «existe el ejecutable», es «analiza de verdad contra sus firmas».
def test_clam_10c_un_analizador_que_ignora_las_firmas_no_pasa_el_preflight(tmp_path):
    rutas = clamav_qa.Rutas(tmp_path / "home")
    bin_real = rutas.prefijo / "usr" / "bin"
    bin_real.mkdir(parents=True)
    (rutas.prefijo / "usr" / "lib" / clamav_qa.ARQUITECTURA).mkdir(parents=True)
    for programa in ("clamscan", "freshclam", "sigtool"):
        f = bin_real / programa
        f.write_text('#!/bin/sh\n[ "$1" = "--version" ] && { echo "ClamAV 1.4.3"; exit 0; }\n'
                     'for a in "$@"; do case "$a" in *eicar*) echo "$a: Eicar-Test-Signature FOUND"; exit 1;; esac; done\n'
                     'echo "x: OK"\nexit 0\n', encoding="utf-8")
        f.chmod(f.stat().st_mode | stat.S_IXUSR)
    clamav_qa.escribir_envoltorios(rutas)
    _firmas_falsas(rutas)
    with pytest.raises(clamav_qa.AnalizadorNoListo, match="QAC-06"):
        clamav_qa.preflight(rutas.home)


# DOCENV-03 (estático) · la prueba documental de malware exige exactamente FILE_INFECTED con el analizador real.
def test_docenv_03_la_prueba_de_malware_exige_file_infected_exacto():
    fuente = (RAIZ / "resources" / "backend" / "tests" / "test_documents.py").read_text(encoding="utf-8")
    inicio = fuente.index("def test_archivo_infectado_se_rechaza_y_no_se_almacena")
    bloque = fuente[inicio: fuente.index("\ndef ", inicio + 1)]
    assert 'assert r.json()["code"] == "FILE_INFECTED"' in bloque
    assert "SCAN_FAILED" not in bloque and "CLEAN" not in bloque


# CLAM-10 · un analizador que arranca pero no analiza (rc 2) no pasa el preflight: nunca se confunde con CLEAN.
def test_clam_10_un_analizador_que_falla_al_analizar_no_pasa_el_preflight(tmp_path):
    rutas = clamav_qa.Rutas(tmp_path / "home")
    _binario_falso(rutas.prefijo, rc_escaneo=2)
    clamav_qa.escribir_envoltorios(rutas)
    _firmas_falsas(rutas)
    with pytest.raises(clamav_qa.AnalizadorNoListo, match="QAC-03/04"):
        clamav_qa.preflight(rutas.home)


# CLAM-10b · un analizador que dice «OK» a todo (también a EICAR) tampoco pasa.
def test_clam_10b_un_analizador_que_dice_limpio_a_todo_no_pasa_el_preflight(tmp_path):
    rutas = clamav_qa.Rutas(tmp_path / "home")
    bin_real = rutas.prefijo / "usr" / "bin"
    bin_real.mkdir(parents=True)
    (rutas.prefijo / "usr" / "lib" / clamav_qa.ARQUITECTURA).mkdir(parents=True)
    for programa in ("clamscan", "freshclam", "sigtool"):
        f = bin_real / programa
        f.write_text('#!/bin/sh\n[ "$1" = "--version" ] && { echo "ClamAV 1.4.3"; exit 0; }\necho "x: OK"\nexit 0\n', encoding="utf-8")
        f.chmod(f.stat().st_mode | stat.S_IXUSR)
    clamav_qa.escribir_envoltorios(rutas)
    _firmas_falsas(rutas)
    with pytest.raises(clamav_qa.AnalizadorNoListo, match="QAC-05"):
        clamav_qa.preflight(rutas.home)


# CLAM-11 · las variables exportadas son exactamente las que lee el producto.
def test_clam_11_las_variables_son_las_que_lee_el_producto():
    estado = clamav_qa.Estado(motor="1.4.3", bases={}, clamscan="/x/bin/clamscan", db="/x/db")
    assert clamav_qa.variables(estado) == {"KONTROL_CLAMSCAN_PATH": "/x/bin/clamscan", "KONTROL_CLAMAV_DB": "/x/db"}
    from app.modules.documents import scanning

    fuente = (RAIZ / "resources" / "backend" / "app" / "modules" / "documents" / "scanning.py").read_text(encoding="utf-8")
    assert "KONTROL_CLAMSCAN_PATH" in fuente and "KONTROL_CLAMAV_DB" in fuente
    assert scanning.ClamAVScanner(binary="/x/bin/clamscan", database="/x/db").database == "/x/db"


# CLAM-12 · nada del analizador entra en Git: el prefijo vive fuera del repositorio y el índice no tiene artefactos.
def test_clam_12_el_prefijo_esta_fuera_del_repositorio_y_git_no_rastrea_artefactos():
    assert not clamav_qa.home_por_defecto().is_relative_to(RAIZ)
    assert clamav_qa.home_por_defecto({"KONTROL_QA_CLAMAV_HOME": "/otro/sitio"}) == Path("/otro/sitio")
    rastreados = subprocess.run(["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, check=False).stdout
    assert not [f for f in rastreados.split("\n") if f.endswith((".deb", ".cvd", ".cld"))]


# CLAM-13 · sin sudo ni instalación en el sistema, por contrato del código.
def test_clam_13_el_provisionador_no_usa_sudo_ni_instala_en_el_sistema():
    import ast

    texto = (RAIZ / "qa" / "clamav_qa.py").read_text(encoding="utf-8")
    fuente = texto.replace(ast.get_docstring(ast.parse(texto)) or "", "")  # el código, no la explicación
    for prohibido in ("sudo", "apt-get install", "apt install", "dpkg -i", "pip install", "/usr/local/bin"):
        assert prohibido not in fuente, prohibido
    assert '"apt-get", "download"' in fuente and '"dpkg-deb", "-x"' in fuente
    assert "_suma_esperada" in fuente and "sha256" in fuente  # cada .deb se contrasta con la suma firmada de apt


# CLAM-14/15 · producto y producción intactos: el producto no conoce al provisionador; la imagen no cambia.
def test_clam_14_15_el_producto_y_la_imagen_de_produccion_no_conocen_al_provisionador():
    for fichero in RAIZ.glob("resources/backend/app/**/*.py"):
        assert "clamav_qa" not in fichero.read_text(encoding="utf-8"), fichero
    dockerfile = (RAIZ / "Dockerfile.backend").read_text(encoding="utf-8")
    assert "clamav" not in dockerfile.lower() and "clamav_qa" not in dockerfile


# E2E · el runner canónico tiene un modo que exige el analizador y no empieza sin él.
def test_clam_e2e_el_runner_exige_el_analizador_con_la_opcion_y_no_arranca_sin_el():
    fuente = (RAIZ / "qa" / "e2e_corrida.py").read_text(encoding="utf-8")
    assert 'parser.add_argument("--con-analizador"' in fuente
    assert "clamav_qa.asegurar()" in fuente and "raise base.CicloDeBaseRoto(f\"analizador exigido y no listo" in fuente
    assert "self.entorno.update(clamav_qa.variables(estado))" in fuente
    assert "certificado = self.exigir_analizador() if self.con_analizador else" in fuente


# CLAM-04/05/06/09 · con el analizador real provisionado: versiones legibles, CLEAN, INFECTED y firmas rotas ≠ CLEAN.
@con_analizador_real
def test_clam_04_05_06_el_preflight_real_pasa_y_registra_motor_y_firmas():
    estado = clamav_qa.preflight()
    assert estado.motor.startswith("1.4.")
    assert set(estado.bases) == set(clamav_qa.BASES)
    for info in estado.bases.values():
        assert info.get("version") and info.get("fecha"), info
    assert estado.clamscan == REAL


@con_analizador_real
def test_clam_09_unas_firmas_rotas_no_dan_clean(tmp_path):
    rutas = clamav_qa.Rutas(clamav_qa.home_por_defecto())
    rota = tmp_path / "db-rota"
    rota.mkdir()
    (rota / "main.cvd").write_bytes(b"esto no es una base de firmas")
    limpio = tmp_path / "limpio.pdf"
    limpio.write_bytes(clamav_qa.PDF_LIMPIO)
    codigo, salida = clamav_qa._escanear(rutas, limpio, rota)
    assert codigo not in (0, 1), (codigo, salida)
