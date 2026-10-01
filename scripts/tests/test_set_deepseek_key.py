"""`scripts/set_deepseek_key.py`: monta el MCP local sin enseñar nunca la clave."""
import json
import stat

import pytest
import set_deepseek_key as montaje
from conftest import clave_falsa


def entrada_ajena(clave: str) -> dict:
    return {"type": "stdio", "command": "/opt/node/bin/npx", "args": ["-y", montaje.PACKAGE],
            "env": {"PATH": "/opt/node/bin:/usr/bin", "REQUEST_TIMEOUT": "120000", montaje.KEY_NAME: clave}}


def ejecutar(casa, *args) -> None:
    montaje.main(["--project", casa.proyecto, *args])


def test_key01_la_entrada_nueva_fija_la_version_y_usa_el_npx_sin_resolver(casa, monkeypatch):
    casa.escribir({"projects": {}})
    monkeypatch.setenv(montaje.KEY_NAME, clave_falsa())
    ejecutar(casa)
    servidor = casa.servidor()
    assert servidor["args"] == ["-y", f"{montaje.PACKAGE}@{montaje.PACKAGE_VERSION}"]
    # `bin/npx` es un enlace a `lib/npx-cli.js`: resuelto, npx ya no encuentra `node`.
    assert servidor["command"] == casa.npx
    assert servidor["env"]["PATH"].startswith(casa.npx.rsplit("/", 1)[0] + ":")
    assert servidor["env"]["FALLBACK_ENABLED"] == "false"
    assert servidor["type"] == "stdio"


def test_key02_la_version_fijada_es_exacta():
    assert montaje.PACKAGE_VERSION.count(".") == 2
    assert all(parte.isdigit() for parte in montaje.PACKAGE_VERSION.split("."))


@pytest.mark.parametrize("modo", ["entorno", "otro-proyecto", "ya-configurada", "estado"])
def test_key03_la_clave_no_se_imprime_en_ningun_modo(casa, monkeypatch, capsys, modo):
    clave = clave_falsa("b")
    if modo == "entorno":
        casa.escribir({"projects": {}})
        monkeypatch.setenv(montaje.KEY_NAME, clave)
        ejecutar(casa)
    elif modo == "otro-proyecto":
        casa.escribir({"projects": {casa.otro: {"mcpServers": {"deepseek": entrada_ajena(clave)}}}})
        ejecutar(casa, "--reuse-from", casa.otro)
    elif modo == "ya-configurada":
        casa.escribir({"projects": {casa.proyecto: {"mcpServers": {"deepseek": entrada_ajena(clave)}}}})
        ejecutar(casa)
    else:
        casa.escribir({"projects": {casa.proyecto: {"mcpServers": {"deepseek": entrada_ajena(clave)}}}})
        with pytest.raises(SystemExit):
            ejecutar(casa, "--status")
    salida = capsys.readouterr()
    assert clave not in salida.out + salida.err
    assert clave[:8] not in salida.out + salida.err


def test_key04_reutiliza_la_clave_de_otro_proyecto_sin_tocarlo(casa):
    clave = clave_falsa("c")
    casa.escribir({"projects": {casa.otro: {"mcpServers": {"deepseek": entrada_ajena(clave)}}}})
    antes = casa.servidor(casa.otro)
    ejecutar(casa, "--reuse-from", casa.otro)
    assert casa.servidor()["env"][montaje.KEY_NAME] == clave
    assert casa.servidor(casa.otro) == antes


def test_key05_si_el_otro_proyecto_no_tiene_clave_no_se_escribe_nada(casa):
    casa.escribir({"projects": {casa.otro: {"mcpServers": {}}}})
    antes = casa.ruta.read_bytes()
    with pytest.raises(SystemExit) as salida:
        ejecutar(casa, "--reuse-from", casa.otro)
    assert "no tiene una entrada" in str(salida.value)
    assert casa.ruta.read_bytes() == antes
    assert not casa.respaldos.exists()


def test_key06_conserva_todo_lo_que_no_es_suyo(casa, monkeypatch):
    vecino = {"type": "stdio", "command": "/usr/bin/otro", "args": [], "env": {"TOKEN_AJENO": "no-tocar"}}
    casa.escribir({
        "numStartups": 7,
        "projects": {
            casa.otro: {"mcpServers": {"deepseek": entrada_ajena(clave_falsa("d"))}, "allowedTools": ["x"]},
            casa.proyecto: {"mcpServers": {"vecino": vecino}, "hasTrustDialogAccepted": True},
        },
    })
    antes = casa.leer()
    monkeypatch.setenv(montaje.KEY_NAME, clave_falsa("e"))
    ejecutar(casa)
    despues = casa.leer()
    assert despues["numStartups"] == 7
    assert despues["projects"][casa.otro] == antes["projects"][casa.otro]
    assert despues["projects"][casa.proyecto]["mcpServers"]["vecino"] == vecino
    assert despues["projects"][casa.proyecto]["hasTrustDialogAccepted"] is True


def test_key07_una_entrada_sin_version_se_fija_y_conserva_clave_y_variables(casa):
    clave = clave_falsa("f")
    vieja = entrada_ajena(clave)
    vieja["env"]["MAX_MESSAGE_LENGTH"] = "50000"
    casa.escribir({"projects": {casa.proyecto: {"mcpServers": {"deepseek": vieja}}}})
    ejecutar(casa)  # sin entorno ni --reuse-from: el aviso oculto está prohibido en el arnés
    servidor = casa.servidor()
    assert servidor["args"] == ["-y", montaje.PACKAGE_SPEC]
    assert servidor["command"] == casa.npx
    assert servidor["env"][montaje.KEY_NAME] == clave
    assert servidor["env"]["MAX_MESSAGE_LENGTH"] == "50000"
    assert servidor["env"]["PATH"] == "/opt/node/bin:/usr/bin"


def test_key08_el_fichero_y_el_respaldo_quedan_solo_para_la_duena(casa, monkeypatch):
    casa.escribir({"projects": {}, "marca": "antes"})
    casa.ruta.chmod(0o644)
    monkeypatch.setenv(montaje.KEY_NAME, clave_falsa("g"))
    ejecutar(casa)
    assert stat.S_IMODE(casa.ruta.stat().st_mode) == 0o600
    respaldos = list(casa.respaldos.iterdir())
    assert len(respaldos) == 1
    assert stat.S_IMODE(respaldos[0].stat().st_mode) == 0o600
    assert json.loads(respaldos[0].read_text()) == {"projects": {}, "marca": "antes"}
    assert not casa.ruta.with_suffix(".json.tmp").exists()


def test_key09_estado_no_escribe_y_su_codigo_dice_la_verdad(casa, monkeypatch, capsys):
    casa.escribir({"projects": {}})
    antes = casa.ruta.read_bytes()
    with pytest.raises(SystemExit) as sin_entrada:
        ejecutar(casa, "--status")
    assert sin_entrada.value.code == 1
    assert casa.ruta.read_bytes() == antes

    # Con clave y con una orden que existe: lo único que falta es fijar la versión.
    sin_version = {**entrada_ajena(clave_falsa("h")), "command": casa.npx}
    casa.escribir({"projects": {casa.proyecto: {"mcpServers": {"deepseek": sin_version}}}})
    with pytest.raises(SystemExit) as sin_fijar:
        ejecutar(casa, "--status")
    assert sin_fijar.value.code == 1
    assert "versión fijada ........ NO" in capsys.readouterr().out

    monkeypatch.setenv(montaje.KEY_NAME, clave_falsa("h"))
    ejecutar(casa)
    antes = casa.ruta.read_bytes()
    with pytest.raises(SystemExit) as completo:
        ejecutar(casa, "--status")
    assert completo.value.code == 0
    assert casa.ruta.read_bytes() == antes
    assert "clave configurada ..... sí" in capsys.readouterr().out


def test_key10_una_clave_rechazada_no_se_guarda(casa, monkeypatch):
    casa.escribir({"projects": {}})
    antes = casa.ruta.read_bytes()
    monkeypatch.setenv(montaje.KEY_NAME, clave_falsa("i"))
    monkeypatch.setattr(montaje, "validar", lambda clave: False)
    with pytest.raises(SystemExit):
        ejecutar(casa, "--check")
    assert casa.ruta.read_bytes() == antes
    assert not casa.respaldos.exists()


def test_key11_el_entorno_manda_sobre_el_otro_proyecto(casa, monkeypatch):
    casa.escribir({"projects": {casa.otro: {"mcpServers": {"deepseek": entrada_ajena(clave_falsa("j"))}}}})
    monkeypatch.setenv(montaje.KEY_NAME, clave_falsa("k"))
    ejecutar(casa, "--reuse-from", casa.otro)
    assert casa.servidor()["env"][montaje.KEY_NAME] == clave_falsa("k")


def test_key12_sin_ninguna_fuente_se_pide_por_el_aviso_oculto(casa, monkeypatch):
    casa.escribir({"projects": {}})
    monkeypatch.setattr(montaje.getpass, "getpass", lambda aviso: clave_falsa("m"))
    ejecutar(casa)
    assert casa.servidor()["env"][montaje.KEY_NAME] == clave_falsa("m")
