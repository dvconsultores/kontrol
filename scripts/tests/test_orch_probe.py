"""`scripts/orch_probe.py`: la sonda certifica solo lo que la traza demuestra."""
import json

import orch_probe as sonda
import pytest

OBJETIVO = "/tmp/kontrol-orchestration-probe/orchestration_probe.txt"
PARCHE_BUENO = f"{OBJETIVO}\n<<<<<<< SEARCH\nbeta=2\n=======\nbeta=20\n>>>>>>> REPLACE"
SALIDA_DEL_EJECUTOR = f"STATUS: PROPOSED\nTASK: ORCH-PROBE-001\n\n{PARCHE_BUENO}\n\n# DEEPSEEK PROPOSAL REPORT\n## Task\n"


def bloque(search: str, replace: str, ruta: str = OBJETIVO) -> list[dict]:
    return [{"ruta": ruta, "search": search, "replace": replace}]


def test_probe01_extrae_el_bloque_tal_como_llega():
    assert sonda.extraer_bloques(SALIDA_DEL_EJECUTOR) == bloque("beta=2", "beta=20")
    assert sonda.extraer_bloques("STATUS: MCP_UNAVAILABLE\nNo se hizo ninguna llamada.") == []


def test_probe02_aprueba_el_cambio_exacto_con_o_sin_lineas_de_contexto():
    assert sonda.auditar(bloque("beta=2", "beta=20"), sonda.ORIGINAL, OBJETIVO)[0] == "AUDIT_PASS"
    con_contexto = bloque("alpha=1\nbeta=2\ngamma=3", "alpha=1\nbeta=20\ngamma=3")
    assert sonda.auditar(con_contexto, sonda.ORIGINAL, OBJETIVO)[0] == "AUDIT_PASS"


@pytest.mark.parametrize("candidato, motivo", [
    (bloque("alpha=1\nbeta=2", "alpha=999\nbeta=20"), "UNAUTHORIZED_EXTRA_CHANGE"),   # el sintético de ORCH-06
    (bloque("beta=2", "beta=20\ndelta=4"), "UNAUTHORIZED_EXTRA_CHANGE"),               # añade una línea
    (bloque("beta=2\ngamma=3", "beta=20"), "UNAUTHORIZED_EXTRA_CHANGE"),               # borra una línea
    (bloque("beta = 2", "beta=20"), "SEARCH_MISMATCH"),                               # no coincide exactamente
    (bloque("", "beta=20"), "SEARCH_MISMATCH"),                                       # SEARCH vacío: crearía, no editaría
    (bloque("beta=2", "beta=20", ruta="resources/backend/app/main.py"), "OUT_OF_SCOPE_FILE"),
    (bloque("beta=2", "beta=20", ruta="/etc/orchestration_probe.txt"), "OUT_OF_SCOPE_FILE"),
    (bloque("beta=2", "beta=2"), "CHANGE_MISSING"),
    (bloque("beta=2", "beta=sk-" + "a" * 32), "SECRET_IN_PATCH"),
    ([], "NOT_A_SINGLE_BLOCK"),
    (bloque("beta=2", "beta=20") * 2, "NOT_A_SINGLE_BLOCK"),
])
def test_probe03_rechaza_todo_parche_no_conforme(candidato, motivo):
    veredicto, por_que = sonda.auditar(candidato, sonda.ORIGINAL, OBJETIVO)
    assert veredicto == "AUDIT_REJECT" and motivo in por_que


def traza(*, agente=True, mcp_desde_subagente=True, respuesta=True, argumentos=None, salida=None,
          primer_plano=True, de_deepseek=None):
    """Una traza con la forma real del flujo `stream-json` de Claude Code. El parche apunta
    al fichero de arena de la prueba, como el real apunta al de la sonda. En primer plano el
    informe del subagente llega en `tool_use_result.content` y el texto final va sangrado
    dos espacios; en segundo plano solo hay texto final, sin sangrar."""
    salida = (salida or SALIDA_DEL_EJECUTOR).replace(OBJETIVO, str(sonda.OBJETIVO))
    de_deepseek = (de_deepseek or PARCHE_BUENO).replace(OBJETIVO, str(sonda.OBJETIVO))
    argumentos = argumentos or {"model": sonda.MODELO, "messages": [{"role": "user", "content": sonda.ENCARGO}]}
    eventos = [{"type": "system", "subtype": "init", "agents": ["claude", sonda.SUBAGENTE],
                "mcp_servers": [{"name": "deepseek", "status": "connected"}]}]
    if agente:
        eventos.append({"type": "assistant", "parent_tool_use_id": None, "message": {"content": [
            {"type": "tool_use", "id": "a1", "name": "Agent", "input": {"subagent_type": sonda.SUBAGENTE, "prompt": sonda.ENCARGO}}]}})
    eventos.append({"type": "assistant", "parent_tool_use_id": "a1" if mcp_desde_subagente else None, "message": {"content": [
        {"type": "tool_use", "id": "m1", "name": "mcp__deepseek__deepseek_chat", "input": argumentos}]}})
    if respuesta:
        # La herramienta entrega un JSON en texto; `tool_use_result` llega vacío.
        devuelto = {"content": de_deepseek, "model": "deepseek-flash", "request": {
            "model": "deepseek-flash", "wire_model": sonda.MODELO, "fallback_used": False, "finish_reason": "stop",
            "prompt_tokens": 410, "completion_tokens": 28, "cost_usd": 0.000065}}
        eventos.append({"type": "user", "parent_tool_use_id": "a1", "tool_use_result": None,
                        "message": {"content": [{"type": "tool_result", "tool_use_id": "m1",
                                                 "content": [{"type": "text", "text": json.dumps(devuelto)}]}]}})
    else:
        eventos.append({"type": "user", "parent_tool_use_id": "a1", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "m1", "is_error": True, "content": "No such tool available"}]}})
    sangrada = "\n".join("  " + linea for linea in salida.splitlines())
    if agente and primer_plano:
        eventos.append({"type": "user", "parent_tool_use_id": None,
                        "tool_use_result": {"status": "completed", "content": [{"type": "text", "text": salida}]},
                        "message": {"content": [{"type": "tool_result", "tool_use_id": "a1",
                                                 "content": [{"type": "text", "text": "[Subagent hand-back]\n" + sangrada}]}]}})
    elif agente:
        eventos.append({"type": "user", "parent_tool_use_id": None, "tool_use_result": {"status": "async_launched"},
                        "message": {"content": [{"type": "tool_result", "tool_use_id": "a1", "content": "Async agent launched"}]}})
    eventos.append({"type": "result", "result": sangrada if primer_plano else salida, "total_cost_usd": 0.1})
    return [json.dumps(e) for e in eventos]


@pytest.fixture
def arena(tmp_path, monkeypatch):
    objetivo = tmp_path / "orchestration_probe.txt"
    objetivo.write_text(sonda.ORIGINAL)
    monkeypatch.setattr(sonda, "OBJETIVO", objetivo)
    return objetivo


def fallos(resultados) -> list[str]:
    return [nombre.split()[0] for nombre, bien, _ in resultados if not bien]


def test_probe04_una_cadena_completa_certifica_los_diez_y_aplica_el_parche(arena):
    resultados = sonda.certificar(traza())
    assert fallos(resultados) == []
    assert len(resultados) == 10
    assert arena.read_text() == sonda.ESPERADO
    uso = next(detalle for nombre, _, detalle in resultados if nombre.startswith("ORCH-09"))
    assert "'prompt_tokens': 410" in uso and "'cost_usd': 6.5e-05" in uso


@pytest.mark.parametrize("primer_plano", [True, False])
def test_probe12_certifica_igual_en_primer_y_en_segundo_plano(arena, primer_plano):
    assert fallos(sonda.certificar(traza(primer_plano=primer_plano))) == []
    assert arena.read_text() == sonda.ESPERADO


def test_probe13_el_marco_de_dos_espacios_se_quita_y_solo_ese():
    enmarcado = "\n".join("  " + linea for linea in SALIDA_DEL_EJECUTOR.splitlines())
    assert sonda.extraer_bloques(enmarcado) == []
    assert sonda.extraer_bloques(sonda.quitar_marco(enmarcado)) == bloque("beta=2", "beta=20")
    sin_marco = "titulo\n  sangrado propio"
    assert sonda.quitar_marco(sin_marco) == sin_marco


def test_probe14_si_el_ejecutor_retoca_lo_que_deepseek_devolvio_no_certifica(arena):
    """El ejecutor devuelve la propuesta literal: no la corrige ni la completa."""
    de_deepseek = PARCHE_BUENO.replace("<<<<<<< SEARCH\nbeta=2", "<<<<<<< SEARCH\nbeta = 2")
    assert "ORCH-04" in fallos(sonda.certificar(traza(de_deepseek=de_deepseek)))


def test_probe05_sin_respuesta_del_mcp_no_se_certifica_ni_se_aplica_nada(arena):
    sin_mcp = traza(respuesta=False, salida="STATUS: MCP_UNAVAILABLE\nTASK: ORCH-PROBE-001")
    assert fallos(sonda.certificar(sin_mcp)) == ["ORCH-02", "ORCH-04", "ORCH-05", "ORCH-07", "ORCH-08", "ORCH-09"]
    assert arena.read_text() == sonda.ORIGINAL


def test_probe06_si_el_orquestador_llama_a_deepseek_sin_pasar_por_el_ejecutor_no_vale(arena):
    assert "ORCH-02" in fallos(sonda.certificar(traza(mcp_desde_subagente=False)))


def test_probe07_si_nadie_invoca_al_ejecutor_orch01_falla(arena):
    assert "ORCH-01" in fallos(sonda.certificar(traza(agente=False)))


@pytest.mark.parametrize("extra", [
    {"session_id": "memoria-entre-llamadas"},
    {"messages": [{"role": "user", "content": "password = hunter2hunter2hunter2"}]},
    {"messages": [{"role": "user", "content": "contenido de resources/backend/.env"}]},
    {"messages": [{"role": "user", "content": "postgresql+psycopg2://kontrol:s3creta@db.interna/kontrol"}]},
])
def test_probe08_una_carga_con_memoria_o_con_secretos_rompe_el_egress(arena, extra):
    argumentos = {"model": sonda.MODELO, "messages": [{"role": "user", "content": sonda.ENCARGO}], **extra}
    assert "ORCH-03" in fallos(sonda.certificar(traza(argumentos=argumentos)))


def test_probe09_un_modelo_distinto_del_pedido_no_certifica(arena):
    argumentos = {"model": "deepseek-v4-pro", "messages": [{"role": "user", "content": sonda.ENCARGO}]}
    assert "ORCH-09" in fallos(sonda.certificar(traza(argumentos=argumentos)))


def test_probe10_un_parche_con_cambio_ajeno_se_rechaza_y_no_se_aplica(arena):
    malo = SALIDA_DEL_EJECUTOR.replace("<<<<<<< SEARCH\nbeta=2\n=======\nbeta=20", "<<<<<<< SEARCH\nalpha=1\nbeta=2\n=======\nalpha=999\nbeta=20")
    de_deepseek = PARCHE_BUENO.replace("<<<<<<< SEARCH\nbeta=2\n=======\nbeta=20", "<<<<<<< SEARCH\nalpha=1\nbeta=2\n=======\nalpha=999\nbeta=20")
    assert fallos(sonda.certificar(traza(salida=malo, de_deepseek=de_deepseek))) == ["ORCH-05", "ORCH-07", "ORCH-08"]
    assert arena.read_text() == sonda.ORIGINAL


def test_probe11_el_encargo_de_la_sonda_no_lleva_secretos_y_es_autocontenido():
    assert not sonda.SECRETO.search(sonda.PETICION)
    for campo in ("TASK:", "TARGET FILES:", "CONTRACT:", "DONE WHEN:", "MODEL: deepseek-v4-flash", "CONTENIDO ACTUAL"):
        assert campo in sonda.ENCARGO
