"""IBE · Contrato de etapas de la imagen del backend (Spec 052, OD-CERT-04).

Un build sin `--target` y toda imagen publicada deben ser el runtime de producción; la etapa `dev`
solo se obtiene de forma explícita; la herencia entre etapas se resuelve desde los FROM, no por la última línea.

- IBE-01 el build sin target es la etapa `runtime` y no hereda de `dev`;
- IBE-02 el runtime arranca sin `--reload` y con keep-alive 75;
- IBE-03 el runtime no copia `tests/`;
- IBE-04 el runtime no corre como root;
- IBE-05 el runtime conserva HEALTHCHECK y ENTRYPOINT;
- IBE-06 `dev` existe, hereda de `base` y solo se obtiene explícitamente;
- IBE-07 los workflows que publican el backend eligen `target: runtime`;
- IBE-08 el analizador resuelve la herencia y no confunde una imagen externa con una etapa.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from tests.test_imagen_backend_mime import _cadena_efectiva, _instrucciones

BACKEND = Path(__file__).resolve().parents[1]
RAIZ = BACKEND.parents[1]


def _etapas_completas(texto: str) -> tuple[dict[str, dict], str]:
    """Construye el mapa de etapas y devuelve el nombre de la última etapa declarada.

    IBE-01: la herencia entre etapas debe resolverse desde las instrucciones FROM,
    no desde la última línea ni desde un grep superficial.
    """
    etapas: dict[str, dict] = {}
    etapa_actual: str | None = None
    nombres_declarados: list[str] = []

    for instruccion, argumentos in _instrucciones(texto):
        if instruccion == "FROM":
            partes = re.split(r"\s+AS\s+", argumentos, flags=re.IGNORECASE)
            imagen = partes[0].strip()
            if len(partes) > 1:
                nombre = partes[1].strip()
            else:
                nombre = imagen
            padre = imagen if imagen in nombres_declarados else None
            etapas[nombre] = {"padre": padre, "instrucciones": []}
            nombres_declarados.append(nombre)
            etapa_actual = nombre
        elif etapa_actual is not None:
            etapas[etapa_actual]["instrucciones"].append((instruccion, argumentos))

    return etapas, etapa_actual or ""


def _efectiva(etapas: dict[str, dict], cadena: list[str], instruccion: str) -> str | None:
    """Última aparición efectiva de una instrucción a lo largo de la cadena heredada."""
    resultado: str | None = None
    for nombre in cadena:
        for candidata, argumentos in etapas[nombre]["instrucciones"]:
            if candidata == instruccion:
                resultado = argumentos
    return resultado


def _todas(etapas: dict[str, dict], cadena: list[str], instruccion: str) -> list[str]:
    """Todas las apariciones de una instrucción a lo largo de la cadena heredada."""
    resultados: list[str] = []
    for nombre in cadena:
        for candidata, argumentos in etapas[nombre]["instrucciones"]:
            if candidata == instruccion:
                resultados.append(argumentos)
    return resultados


def _dockerfile_texto() -> str:
    return (RAIZ / "Dockerfile.backend").read_text()


def _etapas_y_final() -> tuple[dict[str, dict], str]:
    return _etapas_completas(_dockerfile_texto())


def _workflow_textos() -> list[tuple[str, dict]]:
    workflows: list[tuple[str, dict]] = []
    for ruta in sorted((RAIZ / ".github" / "workflows").glob("*.yml")):
        workflows.append((ruta.name, yaml.safe_load(ruta.read_text())))
    return workflows


def test_ibe_01_el_build_sin_target_es_el_runtime() -> None:
    etapas, final = _etapas_y_final()
    cadena = _cadena_efectiva(etapas, final)
    assert final == "runtime"
    assert "dev" not in cadena


def test_ibe_02_el_runtime_arranca_sin_reload_y_con_keep_alive_75() -> None:
    etapas, final = _etapas_y_final()
    cadena = _cadena_efectiva(etapas, final)
    cmd = json.loads(_efectiva(etapas, cadena, "CMD") or "")
    assert "app.main:app" in cmd
    assert "--reload" not in cmd
    indice = cmd.index("--timeout-keep-alive")
    assert cmd[indice + 1] == "75"


def test_ibe_03_el_runtime_no_copia_pruebas() -> None:
    etapas, final = _etapas_y_final()
    cadena = _cadena_efectiva(etapas, final)
    patron = re.compile(r"(^|/)tests(/|$)")
    for argumentos in _todas(etapas, cadena, "COPY") + _todas(etapas, cadena, "ADD"):
        for parte in argumentos.split():
            assert not patron.search(parte)


def test_ibe_04_el_runtime_no_corre_como_root() -> None:
    etapas, final = _etapas_y_final()
    cadena = _cadena_efectiva(etapas, final)
    user = _efectiva(etapas, cadena, "USER")
    assert user is not None
    usuario = user.split(":")[0]
    assert usuario not in {"root", "0"}


def test_ibe_05_el_runtime_conserva_healthcheck_y_entrypoint() -> None:
    etapas, final = _etapas_y_final()
    cadena = _cadena_efectiva(etapas, final)
    healthcheck = _efectiva(etapas, cadena, "HEALTHCHECK")
    assert healthcheck is not None
    assert healthcheck.upper() != "NONE"
    assert "health/live" in healthcheck
    entrypoint = _efectiva(etapas, cadena, "ENTRYPOINT")
    assert entrypoint is not None
    assert json.loads(entrypoint) == ["/app/entrypoint.sh"]


def test_ibe_06_dev_solo_se_obtiene_explicitamente() -> None:
    etapas, final = _etapas_y_final()
    assert "dev" in etapas
    assert etapas["dev"]["padre"] == "base"
    assert final != "dev"
    cadena = _cadena_efectiva(etapas, "dev")
    cmd = json.loads(_efectiva(etapas, cadena, "CMD") or "")
    assert "--reload" in cmd


def test_ibe_07_los_workflows_que_publican_el_backend_eligen_runtime() -> None:
    etapas, _ = _etapas_y_final()
    assert "runtime" in etapas

    encontrados_por_workflow: dict[str, int] = {}
    for nombre, workflow in _workflow_textos():
        for job in workflow.get("jobs", {}).values():
            for paso in job.get("steps", []):
                uses = paso.get("uses", "")
                if not uses.startswith("docker/build-push-action"):
                    continue
                with_config = paso.get("with", {})
                if with_config.get("file") != "Dockerfile.backend":
                    continue
                assert with_config.get("target") == "runtime"
                encontrados_por_workflow[nombre] = encontrados_por_workflow.get(nombre, 0) + 1

    assert encontrados_por_workflow.get("build-main.yml", 0) >= 1
    assert encontrados_por_workflow.get("build-dev.yml", 0) >= 1


def test_ibe_08_el_analizador_resuelve_la_herencia() -> None:
    dockerfile_a = """\
FROM python:3.13-slim AS base
USER kontrol
CMD ["uvicorn", "app.main:app", "--timeout-keep-alive", "75"]
FROM base AS dev
CMD ["uvicorn", "app.main:app", "--reload"]
FROM dev AS runtime
"""
    etapas_a, final_a = _etapas_completas(dockerfile_a)
    assert final_a == "runtime"
    cadena_a = _cadena_efectiva(etapas_a, final_a)
    assert cadena_a == ["base", "dev", "runtime"]
    cmd_a = json.loads(_efectiva(etapas_a, cadena_a, "CMD") or "")
    assert "--reload" in cmd_a

    dockerfile_b = """\
FROM imagen-externa:1 AS runtime
CMD ["uvicorn", "app.main:app"]
"""
    etapas_b, final_b = _etapas_completas(dockerfile_b)
    assert final_b == "runtime"
    assert etapas_b["runtime"]["padre"] is None
    assert _cadena_efectiva(etapas_b, final_b) == ["runtime"]
