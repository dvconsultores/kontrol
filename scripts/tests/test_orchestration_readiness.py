"""`scripts/orchestration_readiness.py`: la auditoría del montaje distingue lo bueno de lo malo."""
import json
import subprocess

import orchestration_readiness as auditoria
import pytest
import set_deepseek_key as montaje
from conftest import clave_falsa

EJECUTOR_BUENO = "---\nname: deepseek-executor\ntools: Read, Glob, Grep, mcp__deepseek__deepseek_chat\n---\nRETRY_MAX: 2\n"


def repo_con(tmp_path, ficheros: dict[str, str]):
    for relativa, texto in ficheros.items():
        ruta = tmp_path / relativa
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(texto)
    return tmp_path


# Lista escrita aquí, no leída de la auditoría: si alguien la recorta allí, esto lo delata.
@pytest.mark.parametrize("herramienta", ["Edit", "Write", "Bash", "NotebookEdit", "Agent", "Task"])
def test_orch_r01_un_ejecutor_que_puede_editar_o_ejecutar_no_pasa(tmp_path, herramienta):
    malo = EJECUTOR_BUENO.replace("Read, Glob", f"Read, {herramienta}, Glob")
    bien, detalle = auditoria.comprobar_ejecutor(repo_con(tmp_path, {auditoria.EJECUTOR: malo}))
    assert not bien and herramienta in detalle


def test_orch_r02_un_ejecutor_sin_lista_de_herramientas_no_pasa(tmp_path):
    sin_lista = "---\nname: deepseek-executor\n---\ntexto\n"
    bien, detalle = auditoria.comprobar_ejecutor(repo_con(tmp_path, {auditoria.EJECUTOR: sin_lista}))
    assert not bien and "heredaría" in detalle


def test_orch_r03_el_ejecutor_debe_declarar_la_herramienta_real(tmp_path):
    otro_nombre = EJECUTOR_BUENO.replace("mcp__deepseek__deepseek_chat", "mcp__deepseek__chat")
    assert not auditoria.comprobar_ejecutor(repo_con(tmp_path, {auditoria.EJECUTOR: otro_nombre}))[0]
    assert auditoria.comprobar_ejecutor(repo_con(tmp_path, {auditoria.EJECUTOR: EJECUTOR_BUENO}))[0]


@pytest.mark.parametrize("documento", [auditoria.CLAUDE_MD, auditoria.EJECUTOR, auditoria.COORDINADOR, auditoria.POLITICA])
@pytest.mark.parametrize("contenido", ["RETRY_MAX: 3", "RETRY_MAX: 2 y luego RETRY_MAX: 5", "sin tope"])
def test_orch_r04_el_tope_de_reintentos_es_dos_en_todos_los_documentos(tmp_path, documento, contenido):
    ficheros = {d: "RETRY_MAX: 2" for d in (auditoria.CLAUDE_MD, auditoria.EJECUTOR, auditoria.COORDINADOR, auditoria.POLITICA)}
    assert auditoria.comprobar_tope_de_reintentos(repo_con(tmp_path, ficheros))[0]
    ficheros[documento] = contenido
    bien, detalle = auditoria.comprobar_tope_de_reintentos(repo_con(tmp_path, ficheros))
    assert not bien and documento in detalle


def test_orch_r05_el_servidor_con_clave_no_vive_en_el_mcp_versionado(tmp_path):
    assert auditoria.comprobar_mcp_del_repo(repo_con(tmp_path, {".mcp.json": '{"mcpServers": {}}'}))[0]
    con_servidor = json.dumps({"mcpServers": {"deepseek": {"command": "npx"}}})
    assert not auditoria.comprobar_mcp_del_repo(repo_con(tmp_path, {".mcp.json": con_servidor}))[0]
    assert not auditoria.comprobar_mcp_del_repo(repo_con(tmp_path, {".mcp.json": ""}))[0]


def test_orch_r06_una_clave_incrustada_en_el_repo_se_detecta_y_el_nombre_a_secas_no(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    repo_con(tmp_path, {"doc.md": "La variable DEEPSEEK_API_KEY vive en local.\nEjemplo prohibido: DEEPSEEK_API_KEY=sk-xxxx...\n"})
    assert auditoria.comprobar_sin_clave_en_el_repo(tmp_path)[0]
    repo_con(tmp_path, {"fuga.txt": f"clave = {clave_falsa('9')}\n"})
    bien, detalle = auditoria.comprobar_sin_clave_en_el_repo(tmp_path)
    assert not bien and "fuga.txt" in detalle and clave_falsa("9") not in detalle


def test_orch_r07_los_deny_de_seguridad_no_se_relajan(tmp_path):
    completo = {"permissions": {"deny": [*auditoria.DENY_MINIMO, "Bash(psql *DATABASE_URL_PROD*)"]}}
    assert auditoria.comprobar_settings(repo_con(tmp_path, {".claude/settings.json": json.dumps(completo)}))[0]
    completo["permissions"]["deny"].remove("Read(./.env)")
    assert not auditoria.comprobar_settings(repo_con(tmp_path, {".claude/settings.json": json.dumps(completo)}))[0]
    sin_psql = {"permissions": {"deny": sorted(auditoria.DENY_MINIMO)}}
    assert not auditoria.comprobar_settings(repo_con(tmp_path, {".claude/settings.json": json.dumps(sin_psql)}))[0]


def test_orch_r08_la_entrada_local_exige_ruta_absoluta_y_version_fijada(casa, monkeypatch):
    from pathlib import Path

    repo = Path(casa.proyecto)
    casa.escribir({"projects": {}})
    assert not auditoria.comprobar_entrada_local(repo)[0]

    monkeypatch.setenv(montaje.KEY_NAME, clave_falsa("p"))
    montaje.main(["--project", casa.proyecto])
    assert auditoria.comprobar_entrada_local(repo)[0]

    datos = casa.leer()
    datos["projects"][casa.proyecto]["mcpServers"]["deepseek"]["args"] = ["-y", montaje.PACKAGE]
    casa.escribir(datos)
    bien, detalle = auditoria.comprobar_entrada_local(repo)
    assert not bien and "sin fijar" in detalle

    datos["projects"][casa.proyecto]["mcpServers"]["deepseek"]["args"] = ["-y", montaje.PACKAGE_SPEC]
    datos["projects"][casa.proyecto]["mcpServers"]["deepseek"]["command"] = "npx"
    casa.escribir(datos)
    bien, detalle = auditoria.comprobar_entrada_local(repo)
    assert not bien and "ruta absoluta" in detalle


def test_orch_r09_de_la_clave_solo_se_informa_la_presencia(casa, monkeypatch):
    from pathlib import Path

    repo = Path(casa.proyecto)
    casa.escribir({"projects": {}})
    assert auditoria.comprobar_clave_local(repo) == (False, "PRESENT=NO NONEMPTY=NO")
    clave = clave_falsa("q")
    monkeypatch.setenv(montaje.KEY_NAME, clave)
    montaje.main(["--project", casa.proyecto])
    bien, detalle = auditoria.comprobar_clave_local(repo)
    assert bien and detalle == "PRESENT=YES NONEMPTY=YES"
    datos = casa.leer()
    datos["projects"][casa.proyecto]["mcpServers"]["deepseek"]["env"][montaje.KEY_NAME] = ""
    casa.escribir(datos)
    assert auditoria.comprobar_clave_local(repo) == (False, "PRESENT=YES NONEMPTY=NO")


@pytest.mark.parametrize("comprobacion", [
    auditoria.comprobar_claude_md, auditoria.comprobar_ejecutor, auditoria.comprobar_coordinador,
    auditoria.comprobar_tope_de_reintentos, auditoria.comprobar_modelos_documentados,
    auditoria.comprobar_settings, auditoria.comprobar_spec_kit, auditoria.comprobar_mcp_del_repo,
    auditoria.comprobar_sin_clave_en_el_repo,
])
def test_orch_r10_el_repositorio_real_cumple_lo_que_no_depende_de_la_maquina(comprobacion):
    bien, detalle = comprobacion(auditoria.REPO)
    assert bien, detalle
