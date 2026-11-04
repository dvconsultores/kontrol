"""DC-01..DC-08: pruebas backend del CONTENIDO del paquete DOC-08."""

from __future__ import annotations

import hashlib
import json
import re
import zipfile

from tests.test_gov_doc08_paquete import P, _abrir_zip, _generar

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.test_gov_doc08_paquete",
)


def _paquete(mundo, escenario) -> tuple[dict, bytes]:
    r = _generar(mundo, escenario["muestra_id"])
    assert r.status_code == 201, r.text
    paquete = r.json()
    d = mundo.client.get(
        f"/api/v1{P}/{paquete['id']}/descargar",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert d.status_code == 200, d.text
    return paquete, d.content


class TestGovDoc08Contenido:
    def test_dc01_descarga_integridad_y_estructura(self, mundo, gobierno, escenario):
        paquete, contenido = _paquete(mundo, escenario)

        r = mundo.client.get(
            f"/api/v1{P}/{paquete['id']}/descargar",
            headers=mundo.como("ua", mundo.company_a),
        )
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/zip")
        assert "no-store" in r.headers["cache-control"]
        assert r.headers["x-content-type-options"] == "nosniff"

        assert hashlib.sha256(contenido).hexdigest() == paquete["huella_paquete"]

        zf = _abrir_zip(contenido)
        esperadas = (
            "manifest.json",
            "SHA256SUMS",
            "INDICE.csv",
            "LEEME.txt",
            "muestra/muestra.json",
        )
        assert zf.namelist()[:5] == list(esperadas)

        prefijos = (
            "manifest.json",
            "SHA256SUMS",
            "INDICE.csv",
            "LEEME.txt",
            "muestra/",
            "eventos/",
            "documentos/",
            "hallazgos/",
        )
        for nombre in zf.namelist():
            assert not nombre.startswith("/")
            assert ".." not in nombre
            assert any(nombre.startswith(prefijo) for prefijo in prefijos)

    def test_dc02_manifiesto(self, mundo, gobierno, escenario):
        paquete, contenido = _paquete(mundo, escenario)
        zf = _abrir_zip(contenido)

        manifiesto = json.loads(zf.read("manifest.json"))
        assert manifiesto["formato"] == "kontrol-gobierno-paquete-auditoria"
        assert manifiesto["version_manifiesto"] == 1
        assert manifiesto["paquete"]["codigo"] == paquete["codigo"]
        assert manifiesto["paquete"]["algoritmo_hash"] == "SHA-256"
        assert (
            "no es una firma electrónica"
            in manifiesto["paquete"]["aviso"]
        )

        assert hashlib.sha256(zf.read("manifest.json")).hexdigest() == paquete[
            "huella_manifiesto"
        ]

        partidas = manifiesto["muestra"]["partidas"]
        assert set(partidas) == {
            escenario["ev_progreso"],
            escenario["ev_creado"],
        }
        assert manifiesto["totales"]["eventos"] == 2

    def test_dc03_huellas_y_sumas(self, mundo, gobierno, escenario):
        paquete, contenido = _paquete(mundo, escenario)
        zf = _abrir_zip(contenido)

        manifiesto = json.loads(zf.read("manifest.json"))
        archivos = manifiesto["archivos"]

        rutas_archivos = [a["ruta"] for a in archivos]
        assert "manifest.json" not in rutas_archivos
        assert "SHA256SUMS" not in rutas_archivos

        for a in archivos:
            datos = zf.read(a["ruta"])
            assert hashlib.sha256(datos).hexdigest() == a["sha256"]
            assert len(datos) == a["bytes"]

        lineas = zf.read("SHA256SUMS").decode("utf-8").splitlines()
        patron = re.compile(r"^[0-9a-f]{64}  \S+$")
        rutas_sumas = []
        for linea in lineas:
            assert patron.match(linea), linea
            hash_sumas, ruta = linea.split("  ", 1)
            rutas_sumas.append(ruta)
            assert hashlib.sha256(zf.read(ruta)).hexdigest() == hash_sumas

        assert set(rutas_sumas) == set(rutas_archivos) | {"manifest.json"}

    def test_dc04_documentos(self, mundo, gobierno, escenario):
        paquete, contenido = _paquete(mundo, escenario)
        zf = _abrir_zip(contenido)

        manifiesto = json.loads(zf.read("manifest.json"))
        documentos = {doc["id"]: doc for doc in manifiesto["documentos"]}

        d1 = documentos[escenario["d1"]]
        assert d1["estado"] == "INCLUIDO"
        assert d1["nombre_original"] == "evidencia-d1.pdf"
        assert zf.read(d1["archivo"]) == escenario["d1_datos"]
        assert zf.getinfo(d1["archivo"]).compress_type == zipfile.ZIP_STORED

        d3 = documentos[escenario["d3"]]
        assert d3["estado"] == "INCLUIDO"
        assert zf.read(d3["archivo"]) == escenario["d3_datos"]

        d2 = documentos[escenario["d2"]]
        assert d2["estado"] == "EXCLUIDO"
        assert d2["motivo"] == "NO_DISPONIBLE"
        for clave in ("archivo", "nombre_original", "sha256"):
            assert clave not in d2
        assert not any(
            nombre.startswith(f"documentos/{escenario['d2']}")
            for nombre in zf.namelist()
        )

    def test_dc05_referencias_cruzadas(self, mundo, gobierno, escenario):
        paquete, contenido = _paquete(mundo, escenario)
        zf = _abrir_zip(contenido)

        manifiesto = json.loads(zf.read("manifest.json"))
        eventos = {e["id"]: e for e in manifiesto["eventos"]}
        documentos = {d["id"]: d for d in manifiesto["documentos"]}

        ev_progreso = eventos[escenario["ev_progreso"]]
        assert escenario["d1"] in ev_progreso["documentos"]
        assert ev_progreso["objeto"] is not None
        assert ev_progreso["objeto"]["tipo"] == "GovernmentFinding"
        assert ev_progreso["objeto"]["id"] == ev_progreso["entidad_id"]

        d1 = documentos[escenario["d1"]]
        assert {"tipo": "evento", "id": escenario["ev_progreso"]} in d1[
            "referencias"
        ]

        d3 = documentos[escenario["d3"]]
        assert {"tipo": "accion_correctiva", "id": escenario["accion_id"]} in d3[
            "referencias"
        ]

        hallazgos = manifiesto["hallazgos"]
        assert len(hallazgos) == 1
        hallazgo = hallazgos[0]
        assert hallazgo["codigo"] == escenario["hallazgo_codigo"]
        assert hallazgo["partidas"] == [escenario["ev_progreso"]]
        assert hallazgo["acciones"] == [escenario["accion_id"]]
        assert hallazgo["archivo"] == (
            f"hallazgos/{escenario['hallazgo_codigo']}.json"
        )

        hallazgo_json = json.loads(zf.read(hallazgo["archivo"]))
        assert len(hallazgo_json["recomendaciones"]) == 1
        cargo = hallazgo_json["acciones"][0]["cargo"]
        assert cargo["codigo"]
        assert isinstance(cargo["ejercicio"], int)

    def test_dc06_indice_y_leeme(self, mundo, gobierno, escenario):
        paquete, contenido = _paquete(mundo, escenario)
        zf = _abrir_zip(contenido)

        indice = zf.read("INDICE.csv")
        assert indice.startswith(b"\xef\xbb\xbf")

        lineas = indice.decode("utf-8-sig").splitlines()
        assert lineas[0] == (
            "ruta;tipo;referencia;descripcion;bytes;sha256"
        )

        manifiesto = json.loads(zf.read("manifest.json"))
        assert len(lineas) - 1 == len(manifiesto["archivos"]) - 1

        leeme = zf.read("LEEME.txt").decode("utf-8")
        assert "sha256sum -c SHA256SUMS" in leeme

    def test_dc07_metadatos_seguros(self, mundo, gobierno, escenario):
        paquete, contenido = _paquete(mundo, escenario)
        zf = _abrir_zip(contenido)

        manifiesto = json.loads(zf.read("manifest.json"))
        eventos = {e["id"]: e for e in manifiesto["eventos"]}

        archivo_evento = eventos[escenario["ev_progreso"]]["archivo"]
        evento_json = json.loads(zf.read(archivo_evento))
        assert "detalle" in evento_json
        assert escenario["d1"] in json.dumps(evento_json["detalle"])

        for nombre in zf.namelist():
            if not nombre.startswith("eventos/"):
                continue
            texto = zf.read(nombre).decode("utf-8")
            for clave in ('"ip"', '"user_agent"', '"session_id"'):
                assert clave not in texto

    def test_dc08_manifiesto_suelto(self, mundo, gobierno, escenario):
        paquete, contenido = _paquete(mundo, escenario)

        r = mundo.client.get(
            f"/api/v1{P}/{paquete['id']}/manifiesto",
            headers=mundo.como("ua", mundo.company_a),
        )
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/json")
        assert hashlib.sha256(r.content).hexdigest() == paquete[
            "huella_manifiesto"
        ]
        assert json.loads(r.content)["paquete"]["codigo"] == paquete["codigo"]
